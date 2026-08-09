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
        "features": {
            "signals": {
                "properties": {
                    "speedKph": 60.0, "batteryPercent": 80.0, "temperatureCelsius": 89.0,
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


if __name__ == "__main__":
    unittest.main()