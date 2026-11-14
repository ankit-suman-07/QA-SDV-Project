import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests

MODULE_PATH = Path(__file__).resolve().parents[1] / "ditto" / "scripts" / "verify-vehicle-state.py"
SPEC = importlib.util.spec_from_file_location("verify_vehicle_state", MODULE_PATH)
vvs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vvs)


def make_thing(status="HEALTHY", active_faults=None, processed_ts=None, overrides=None):
    now = processed_ts or datetime.now(timezone.utc).isoformat()
    thing = {
        "thingId": "sdv:vehicle-001",
        "attributes": {"vehicleId": "vehicle-001"},
        "features": {
            "signals": {
                "properties": {
                    "speedKph": 60.0, "batteryPercent": 80.0, "temperatureCelsius": 89.0,
                    "coolantPressureKpa": 200.0,
                    "tirePressurePsi": {"frontLeft": 32, "frontRight": 32, "rearLeft": 31, "rearRight": 32},
                    "sourceTimestamp": now,
                }
            },
            "health": {
                "properties": {
                    "status": status, "activeFaults": active_faults or [],
                    "faultCount": len(active_faults or []), "processedTimestamp": now,
                }
            },
        }
    }
    if overrides:
        thing["features"]["signals"]["properties"].update(overrides.get("signals", {}))
        thing["features"]["health"]["properties"].update(overrides.get("health", {}))
    return thing


class VerifyVehicleStateTest(unittest.TestCase):

    def test_partial_recovery_requires_both_conditions(self):
        for temperature, pressure in [(99, 160), (103, 185), (103, 165)]:
            thing = make_thing(status='CRITICAL', active_faults=['COOLING_SYSTEM_FAILURE'],
                               overrides={'signals': {'temperatureCelsius': temperature,
                                                     'coolantPressureKpa': pressure}})
            result = vvs.VerificationResult(ok=True)
            vvs.validate_correlated_faults(thing, result)
            self.assertTrue(result.ok, result.errors)

    def test_source_and_processing_freshness_use_injected_clock(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for field in ('sourceTimestamp', 'processedTimestamp'):
            for value in [None, '', 'bad', '2026-01-01T00:00:00',
                          '0001-01-01T00:00:00+01:00',
                          (now + timedelta(seconds=2)).isoformat(),
                          (now - timedelta(seconds=31)).isoformat()]:
                thing = make_thing(processed_ts=now.isoformat())
                feature = 'signals' if field == 'sourceTimestamp' else 'health'
                thing['features'][feature]['properties'][field] = value
                with self.subTest(field=field, value=value), patch.object(vvs, 'fetch_thing', return_value=thing):
                    result = vvs.verify_vehicle_state(clock=lambda: now)
                    self.assertFalse(result.ok)
                    self.assertTrue(any(field in error for error in result.errors), result.errors)

    def test_wrong_or_missing_identity_fails(self):
        for identity in ['sdv:vehicle-002', None]:
            thing = make_thing()
            thing['thingId'] = identity
            with patch.object(vvs, 'fetch_thing', return_value=thing):
                self.assertFalse(vvs.verify_vehicle_state().ok)

    def test_malformed_nested_structures_return_errors(self):
        cases = [None, [], {'features': []}, {'features': {'signals': []}},
                 {'features': {'signals': {'properties': []}}}]
        for thing in cases:
            with self.subTest(thing=thing), patch.object(vvs, 'fetch_thing', return_value=thing):
                self.assertFalse(vvs.verify_vehicle_state().ok)

    def test_invalid_health_and_fault_detail_structures_fail_without_crashing(self):
        for key, value in [('status', []), ('activeFaults', None), ('activeFaults', [None]),
                           ('faultCount', True), ('faultCount', -1)]:
            thing = make_thing(overrides={'health': {key: value}})
            with self.subTest(key=key), patch.object(vvs, 'fetch_thing', return_value=thing):
                self.assertFalse(vvs.verify_vehicle_state().ok)

    def test_fault_detail_future_and_naive_timestamps_are_rejected(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for field in ('detectedAt', 'clearedAt'):
            for value in ['2026-01-01T00:00:00', 'bad', '2026-01-01T00:00:02Z']:
                thing = make_thing(processed_ts=now.isoformat())
                thing['features']['diagnostics'] = {'properties': {'activeFaultDetails': [{field: value}]}}
                with self.subTest(field=field, value=value), patch.object(vvs, 'fetch_thing', return_value=thing):
                    result = vvs.verify_vehicle_state(clock=lambda: now)
                    self.assertFalse(result.ok)
                    self.assertTrue(any(field in error for error in result.errors), result.errors)

    def test_offset_timestamps_and_future_tolerance_preserve_legacy_compatibility(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        thing = make_thing(processed_ts='2025-12-31T19:00:00-05:00')
        thing['features']['signals']['properties']['sourceTimestamp'] = '2026-01-01T00:00:01Z'
        with patch.object(vvs, 'fetch_thing', return_value=thing):
            self.assertTrue(vvs.verify_vehicle_state(clock=lambda: now).ok)
        self.assertEqual(30, vvs.compute_max_age_seconds())

    def test_full_recovery_exact_threshold_is_inconsistent_with_active_fault(self):
        thing = make_thing(status='CRITICAL', active_faults=['COOLING_SYSTEM_FAILURE'],
                           overrides={'signals': {'temperatureCelsius': 100, 'coolantPressureKpa': 180}})
        result = vvs.VerificationResult(ok=True)
        vvs.validate_correlated_faults(thing, result)
        self.assertFalse(result.ok)

    def test_invalid_clock_and_freshness_configuration_are_reported(self):
        for clock_value in [datetime(2026, 1, 1), 'not a datetime']:
            with patch.object(vvs, 'fetch_thing', return_value=make_thing()):
                self.assertFalse(vvs.verify_vehicle_state(clock=lambda: clock_value).ok)
        for value in [0, -1, float('nan'), float('inf'), True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                vvs.compute_max_age_seconds(explicit_max_age_seconds=value)

    def test_correct_vehicle_002_identity_is_supported(self):
        thing = make_thing()
        thing.update(thingId='sdv:vehicle-002', attributes={'vehicleId': 'vehicle-002'})
        with patch.object(vvs, 'fetch_thing', return_value=thing):
            self.assertTrue(vvs.verify_vehicle_state(thing_id='sdv:vehicle-002').ok)

    @patch("requests.get")
    def test_valid_fresh_thing_passes(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: make_thing())
        result = vvs.verify_vehicle_state(max_age_seconds=30)
        self.assertTrue(result.ok, result.errors)

    @patch("requests.get")
    def test_missing_signal_field_fails(self, mock_get):
        thing = make_thing()
        del thing["features"]["signals"]["properties"]["speedKph"]
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("speedKph" in e for e in result.errors))

    @patch("requests.get")
    def test_missing_tire_wheel_fails(self, mock_get):
        thing = make_thing()
        del thing["features"]["signals"]["properties"]["tirePressurePsi"]["rearRight"]
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("rearRight" in e for e in result.errors))

    @patch("requests.get")
    def test_missing_processed_timestamp_fails(self, mock_get):
        thing = make_thing(overrides={"health": {"processedTimestamp": None}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("processedTimestamp" in e for e in result.errors))

    @patch("requests.get")
    def test_invalid_health_status_fails(self, mock_get):
        thing = make_thing(status="BROKEN")
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)

    @patch("requests.get")
    def test_warning_without_active_faults_fails(self, mock_get):
        thing = make_thing(status="WARNING", active_faults=[])
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)

    @patch("requests.get")
    def test_fault_count_mismatch_fails(self, mock_get):
        thing = make_thing(status="WARNING", active_faults=["BATTERY_LOW"],
                            overrides={"health": {"faultCount": 0}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("faultCount" in e for e in result.errors))

    @patch("requests.get")
    def test_stale_timestamp_fails(self, mock_get):
        old_ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        thing = make_thing(processed_ts=old_ts)
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state(max_age_seconds=30)
        self.assertFalse(result.ok)
        self.assertTrue(any("Stale" in e for e in result.errors))

    @patch("requests.get")
    def test_ditto_unreachable_fails(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("connection refused")
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("Failed to query Ditto" in e for e in result.errors))

    def test_compute_max_age_uses_contract_formula(self):
        self.assertEqual(5.0, vvs.compute_max_age_seconds(publication_interval_seconds=1.0))
        self.assertEqual(5.0, vvs.compute_max_age_seconds(publication_interval_seconds=0.2))
        self.assertEqual(15.0, vvs.compute_max_age_seconds(publication_interval_seconds=5.0))

    def test_explicit_max_age_overrides_interval(self):
        self.assertEqual(99.0, vvs.compute_max_age_seconds(
            publication_interval_seconds=1.0, explicit_max_age_seconds=99.0))

    @patch("requests.get")
    def test_missing_coolant_pressure_fails(self, mock_get):
        thing = make_thing()
        del thing["features"]["signals"]["properties"]["coolantPressureKpa"]
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("coolantPressureKpa" in e for e in result.errors))

    @patch("requests.get")
    def test_boolean_signal_value_fails(self, mock_get):
        thing = make_thing(overrides={"signals": {"batteryPercent": True}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("batteryPercent" in e and "not a valid finite number" in e for e in result.errors))

    @patch("requests.get")
    def test_non_finite_signal_value_fails(self, mock_get):
        thing = make_thing(overrides={"signals": {"temperatureCelsius": float("inf")}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("temperatureCelsius" in e for e in result.errors))

    @patch("requests.get")
    def test_invalid_source_timestamp_fails(self, mock_get):
        thing = make_thing(overrides={"signals": {"sourceTimestamp": "not-a-timestamp"}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("sourceTimestamp" in e for e in result.errors))

    @patch("requests.get")
    def test_correlated_fault_active_with_justifying_signals_passes(self, mock_get):
        thing = make_thing(status="CRITICAL", active_faults=["COOLING_SYSTEM_FAILURE"],
                            overrides={"signals": {"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
                                       "health": {"faultCount": 1}})
        thing["features"]["diagnostics"] = {"properties": {"activeFaultDetails": [{
            "code": "COOLING_SYSTEM_FAILURE", "description": "x", "severity": "CRITICAL", "status": "ACTIVE",
            "affectedSignals": ["temperatureCelsius", "coolantPressureKpa"],
            "observedValues": {"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
            "activationThresholds": {"temperatureCelsius": 105.0, "coolantPressureKpa": 150.0},
            "recoveryThresholds": {"temperatureCelsius": 100.0, "coolantPressureKpa": 180.0},
            "detectedAt": "2026-08-03T15:00:01.200Z",
        }]}}
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        correlated_errors = [e for e in result.errors if "COOLING_SYSTEM_FAILURE" in e]
        self.assertEqual([], correlated_errors, result.errors)

    @patch("requests.get")
    def test_correlated_fault_active_without_justifying_signals_fails(self, mock_get):
        thing = make_thing(status="CRITICAL", active_faults=["COOLING_SYSTEM_FAILURE"],
                            overrides={"signals": {"temperatureCelsius": 90.0, "coolantPressureKpa": 200.0},
                                       "health": {"faultCount": 1}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("COOLING_SYSTEM_FAILURE" in e and "temperatureCelsius" in e for e in result.errors))
        self.assertTrue(any("COOLING_SYSTEM_FAILURE" in e and "coolantPressureKpa" in e for e in result.errors))

    @patch("requests.get")
    def test_correlated_fault_active_missing_detail_record_fails(self, mock_get):
        thing = make_thing(status="CRITICAL", active_faults=["COOLING_SYSTEM_FAILURE"],
                            overrides={"signals": {"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
                                       "health": {"faultCount": 1}})
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("no matching entry" in e for e in result.errors))

    @patch("requests.get")
    def test_correlated_fault_detail_missing_required_field_fails(self, mock_get):
        thing = make_thing(status="CRITICAL", active_faults=["COOLING_SYSTEM_FAILURE"],
                            overrides={"signals": {"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
                                       "health": {"faultCount": 1}})
        thing["features"]["diagnostics"] = {"properties": {"activeFaultDetails": [{
            "code": "COOLING_SYSTEM_FAILURE", "status": "ACTIVE",
        }]}}
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        self.assertFalse(result.ok)
        self.assertTrue(any("detectedAt" in e for e in result.errors))

    @patch("requests.get")
    def test_hysteresis_zone_does_not_fail_while_fault_active(self, mock_get):
        thing = make_thing(status="CRITICAL", active_faults=["COOLING_SYSTEM_FAILURE"],
                            overrides={"signals": {"temperatureCelsius": 103.0, "coolantPressureKpa": 165.0},
                                       "health": {"faultCount": 1}})
        thing["features"]["diagnostics"] = {"properties": {"activeFaultDetails": [{
            "code": "COOLING_SYSTEM_FAILURE", "description": "x", "severity": "CRITICAL", "status": "ACTIVE",
            "affectedSignals": ["temperatureCelsius", "coolantPressureKpa"],
            "observedValues": {"temperatureCelsius": 103.0, "coolantPressureKpa": 165.0},
            "activationThresholds": {"temperatureCelsius": 105.0, "coolantPressureKpa": 150.0},
            "recoveryThresholds": {"temperatureCelsius": 100.0, "coolantPressureKpa": 180.0},
            "detectedAt": "2026-08-03T15:00:01.200Z",
        }]}}
        mock_get.return_value = MagicMock(json=lambda: thing)
        result = vvs.verify_vehicle_state()
        correlated_errors = [e for e in result.errors if "COOLING_SYSTEM_FAILURE" in e]
        self.assertEqual([], correlated_errors, result.errors)


if __name__ == "__main__":
    unittest.main()
