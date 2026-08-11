import unittest

from ditto.fault_details import (
    build_active_fault_detail,
    is_activation_condition,
    is_recovery_condition,
)


class FaultDetailsTest(unittest.TestCase):

    def test_should_build_complete_active_fault_record(self):
        detail = build_active_fault_detail(
            temperature_celsius=108.0,
            coolant_pressure_kpa=140.0,
            detected_at="2026-08-03T15:00:01.200Z",
            event_id="event-001",
            trace_id="trace-001",
            action_id="action-001",
        )

        self.assertEqual(
            "COOLING_SYSTEM_FAILURE",
            detail["code"],
        )
        self.assertEqual(
            "High temperature correlated with "
            "low coolant pressure",
            detail["description"],
        )
        self.assertEqual(
            "CRITICAL",
            detail["severity"],
        )
        self.assertEqual(
            "ACTIVE",
            detail["status"],
        )
        self.assertEqual(
            [
                "temperatureCelsius",
                "coolantPressureKpa",
            ],
            detail["affectedSignals"],
        )
        self.assertEqual(
            {
                "temperatureCelsius": 108.0,
                "coolantPressureKpa": 140.0,
            },
            detail["observedValues"],
        )
        self.assertEqual(
            {
                "temperatureCelsius": 105.0,
                "coolantPressureKpa": 150.0,
            },
            detail["activationThresholds"],
        )
        self.assertEqual(
            {
                "temperatureCelsius": 100.0,
                "coolantPressureKpa": 180.0,
            },
            detail["recoveryThresholds"],
        )
        self.assertEqual(
            "2026-08-03T15:00:01.200Z",
            detail["detectedAt"],
        )
        self.assertIsNone(detail["clearedAt"])
        self.assertEqual(
            "event-001",
            detail["eventId"],
        )
        self.assertEqual(
            "trace-001",
            detail["traceId"],
        )
        self.assertEqual(
            "action-001",
            detail["actionId"],
        )

    def test_should_activate_only_when_both_signals_fail(
        self,
    ):
        self.assertTrue(
            is_activation_condition(
                temperature_celsius=105.0,
                coolant_pressure_kpa=150.0,
            )
        )

        self.assertFalse(
            is_activation_condition(
                temperature_celsius=104.9,
                coolant_pressure_kpa=140.0,
            )
        )

        self.assertFalse(
            is_activation_condition(
                temperature_celsius=108.0,
                coolant_pressure_kpa=150.1,
            )
        )

    def test_should_recover_only_when_both_signals_recover(
        self,
    ):
        self.assertTrue(
            is_recovery_condition(
                temperature_celsius=100.0,
                coolant_pressure_kpa=180.0,
            )
        )

        self.assertFalse(
            is_recovery_condition(
                temperature_celsius=100.1,
                coolant_pressure_kpa=190.0,
            )
        )

        self.assertFalse(
            is_recovery_condition(
                temperature_celsius=95.0,
                coolant_pressure_kpa=179.9,
            )
        )


if __name__ == "__main__":
    unittest.main()