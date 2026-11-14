import unittest
import json
from pathlib import Path

from opensovd.fault_mapper import map_fault_to_opensovd, map_all_active_faults


def make_thing(battery=15, temperature=89, tire_fl=32, active_faults=None, processed_ts="2026-07-25T18:00:00Z", source_ts="2026-07-25T17:59:58Z"):
    return {
        "features": {
            "signals": {
                "properties": {
                    "speedKph": 60, "batteryPercent": battery, "temperatureCelsius": temperature,
                    "tirePressurePsi": {"frontLeft": tire_fl, "frontRight": 32, "rearLeft": 31, "rearRight": 32},
                    "sourceTimestamp": source_ts,
                }
            },
            "health": {
                "properties": {
                    "status": "WARNING" if active_faults else "HEALTHY",
                    "activeFaults": active_faults or [],
                    "faultCount": len(active_faults or []),
                    "processedTimestamp": processed_ts,
                }
            },
        }
    }


class FaultMapperTest(unittest.TestCase):

    def test_legacy_tire_unit_and_thresholds_remain_psi(self):
        for pressure, severity, threshold in [(28, 'WARNING', 28), (24.01, 'WARNING', 28), (24, 'CRITICAL', 24)]:
            thing = make_thing(tire_fl=pressure, active_faults=['TIRE_PRESSURE_LOW_FRONT_LEFT'])
            mapped = map_fault_to_opensovd('TIRE_PRESSURE_LOW_FRONT_LEFT', thing)
            self.assertEqual(('psi', pressure, severity, threshold),
                             (mapped['unit'], mapped['observedValue'], mapped['severity'], mapped['threshold']))

    def test_declared_kpa_upstream_and_legacy_psi_boundary_are_explicit(self):
        config = json.loads((Path(__file__).parents[1] / 'vehicle-simulator/config/vss-with-autonomous-sensors.json').read_text())
        node = config['Vehicle']
        for part in 'Chassis.Axle.Row1.Wheel.Left.Tire.Pressure'.split('.'):
            node = node['children'][part]
        self.assertEqual('kPa', node['unit'])
        mapped = map_fault_to_opensovd('TIRE_PRESSURE_LOW_FRONT_LEFT',
                                       make_thing(tire_fl=32, active_faults=['TIRE_PRESSURE_LOW_FRONT_LEFT']))
        self.assertEqual('psi', mapped['unit'])
        self.assertEqual(32, mapped['observedValue'])  # mapper receives already-converted legacy psi

    def test_battery_low_maps_correctly(self):
        thing = make_thing(battery=15, active_faults=["BATTERY_LOW"])
        result = map_fault_to_opensovd("BATTERY_LOW", thing)

        self.assertEqual("BATTERY_LOW", result["code"])
        self.assertEqual("batteryPercent", result["affectedSignal"])
        self.assertEqual(15, result["observedValue"])
        self.assertEqual("%", result["unit"])
        self.assertEqual("ACTIVE", result["status"])
        self.assertEqual("WARNING", result["severity"])
        self.assertEqual(20, result["threshold"])

    def test_battery_critical_severity(self):
        thing = make_thing(battery=8, active_faults=["BATTERY_LOW"])
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertEqual("CRITICAL", result["severity"])
        self.assertEqual(10, result["threshold"])

    def test_temperature_high_maps_correctly(self):
        thing = make_thing(temperature=95, active_faults=["TEMPERATURE_HIGH"])
        result = map_fault_to_opensovd("TEMPERATURE_HIGH", thing)
        self.assertEqual("temperatureCelsius", result["affectedSignal"])
        self.assertEqual(95, result["observedValue"])
        self.assertEqual("WARNING", result["severity"])

    def test_tire_pressure_fault_uses_correct_wheel(self):
        thing = make_thing(tire_fl=25, active_faults=["TIRE_PRESSURE_LOW_FRONT_LEFT"])
        result = map_fault_to_opensovd("TIRE_PRESSURE_LOW_FRONT_LEFT", thing)
        self.assertEqual("tirePressurePsi.frontLeft", result["affectedSignal"])
        self.assertEqual(25, result["observedValue"])

    def test_status_is_cleared_when_not_in_active_faults(self):
        thing = make_thing(battery=27, active_faults=[])
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertEqual("CLEARED", result["status"])

    def test_unknown_fault_code_raises(self):
        thing = make_thing()
        with self.assertRaises(ValueError):
            map_fault_to_opensovd("NOT_A_REAL_FAULT", thing)

    def test_unimplemented_fields_are_none(self):
        thing = make_thing(battery=15, active_faults=["BATTERY_LOW"])
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertIsNone(result["faultId"])
        self.assertIsNone(result["detectedTimestamp"])
        self.assertIsNone(result["clearedTimestamp"])
        self.assertIsNone(result["correlationId"])

    def test_timestamps_pulled_from_ditto(self):
        thing = make_thing(active_faults=["BATTERY_LOW"], source_ts="2026-07-25T17:59:58Z", processed_ts="2026-07-25T18:00:00Z")
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertEqual("2026-07-25T17:59:58Z", result["sourceTimestamp"])
        self.assertEqual("2026-07-25T18:00:00Z", result["lastUpdatedTimestamp"])

    def test_map_all_active_faults_returns_one_per_fault(self):
        thing = make_thing(battery=15, temperature=95, active_faults=["BATTERY_LOW", "TEMPERATURE_HIGH"])
        results = map_all_active_faults(thing)
        self.assertEqual(2, len(results))
        codes = {r["code"] for r in results}
        self.assertEqual({"BATTERY_LOW", "TEMPERATURE_HIGH"}, codes)

    def test_map_all_active_faults_empty_when_healthy(self):
        thing = make_thing(active_faults=[])
        self.assertEqual([], map_all_active_faults(thing))

    def test_correlated_fault_maps_both_signals(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 108.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 140.0

        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)

        self.assertEqual("CRITICAL", result["severity"])
        self.assertEqual("ACTIVE", result["status"])
        self.assertEqual(["temperatureCelsius", "coolantPressureKpa"], result["affectedSignals"])
        self.assertEqual(108.0, result["observedValues"]["temperatureCelsius"])
        self.assertEqual(140.0, result["observedValues"]["coolantPressureKpa"])
        self.assertEqual(105.0, result["activationThresholds"]["temperatureCelsius"])
        self.assertEqual(150.0, result["activationThresholds"]["coolantPressureKpa"])
        self.assertEqual(100.0, result["recoveryThresholds"]["temperatureCelsius"])
        self.assertEqual(180.0, result["recoveryThresholds"]["coolantPressureKpa"])

    def test_correlated_fault_status_cleared_when_not_active(self):
        thing = make_thing(active_faults=[])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 95.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 200.0

        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        self.assertEqual("CLEARED", result["status"])

    def test_correlated_fault_unknown_code_raises(self):
        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        with self.assertRaises(ValueError):
            map_correlated_fault_to_opensovd("NOT_A_REAL_CORRELATED_FAULT", make_thing())

    def test_correlated_fault_pulls_detail_when_present(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        thing["features"]["diagnostics"] = {
            "properties": {
                "activeFaultDetails": [
                    {
                        "code": "COOLING_SYSTEM_FAILURE",
                        "detectedAt": "2026-08-03T15:00:01.200Z",
                        "clearedAt": None,
                        "eventId": "event-123",
                        "traceId": "trace-123",
                        "actionId": "action-123",
                    }
                ]
            }
        }
        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        self.assertEqual("2026-08-03T15:00:01.200Z", result["detectedAt"])
        self.assertEqual("trace-123", result["traceId"])
        self.assertEqual("action-123", result["actionId"])

    def test_correlated_fault_detail_absent_returns_none(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        self.assertIsNone(result["detectedAt"])
        self.assertIsNone(result["traceId"])
        self.assertIsNone(result["actionId"])

    def test_map_all_active_faults_dispatches_correlated_correctly(self):
        thing = make_thing(battery=15, active_faults=["BATTERY_LOW", "COOLING_SYSTEM_FAILURE"])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 108.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 140.0

        results = map_all_active_faults(thing)
        self.assertEqual(2, len(results))

        battery_result = next(r for r in results if r["code"] == "BATTERY_LOW")
        cooling_result = next(r for r in results if r["code"] == "COOLING_SYSTEM_FAILURE")
        self.assertIn("affectedSignal", battery_result)       # single-signal shape
        self.assertIn("affectedSignals", cooling_result)      # correlated shape

    def test_build_diagnostic_resource_wraps_correlated_fault(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 108.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 140.0

        from opensovd.fault_mapper import map_correlated_fault_to_opensovd, build_diagnostic_resource
        fault = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        resource = build_diagnostic_resource(fault)

        self.assertEqual("vehicle-001", resource["vehicleId"])
        self.assertEqual("diagnosticFault", resource["resourceType"])
        self.assertEqual(fault, resource["fault"])

    def test_source_is_active_faults_when_no_detail_present(self):
        thing = make_thing(battery=15, active_faults=["BATTERY_LOW"])
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertEqual("activeFaults", result["source"])

    def test_source_is_active_fault_details_when_detail_present(self):
        thing = make_thing(battery=15, active_faults=["BATTERY_LOW"])
        thing["features"]["diagnostics"] = {"properties": {"activeFaultDetails": [
            {"code": "BATTERY_LOW", "faultId": "f-1"}
        ]}}
        result = map_fault_to_opensovd("BATTERY_LOW", thing)
        self.assertEqual("activeFaultDetails", result["source"])

    def test_correlated_source_is_active_faults_when_no_detail_present(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 108.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 140.0

        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        self.assertEqual("activeFaults", result["source"])

    def test_correlated_source_is_active_fault_details_when_detail_present(self):
        thing = make_thing(active_faults=["COOLING_SYSTEM_FAILURE"])
        thing["features"]["signals"]["properties"]["temperatureCelsius"] = 108.0
        thing["features"]["signals"]["properties"]["coolantPressureKpa"] = 140.0
        thing["features"]["diagnostics"] = {"properties": {"activeFaultDetails": [
            {"code": "COOLING_SYSTEM_FAILURE", "detectedAt": "2026-08-03T15:00:01.200Z"}
        ]}}

        from opensovd.fault_mapper import map_correlated_fault_to_opensovd
        result = map_correlated_fault_to_opensovd("COOLING_SYSTEM_FAILURE", thing)
        self.assertEqual("activeFaultDetails", result["source"])


if __name__ == "__main__":
    unittest.main()
