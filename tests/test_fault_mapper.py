import unittest

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


if __name__ == "__main__":
    unittest.main()
    