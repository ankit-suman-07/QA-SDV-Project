import unittest

from uprotocol.transport import (
    publish_vehicle_status,
    receive_vehicle_status,
)


class UProtocolTransportTest(unittest.TestCase):

    def test_should_serialize_and_receive_vehicle_status(
        self,
    ):
        payload = publish_vehicle_status(
            vehicle_id="vehicle-001",
            speed_kph=60.0,
            battery_percent=15.0,
            temperature_celsius=90.0,
            coolant_pressure_kpa=200.0,
            tire_pressure_psi=32.0,
        )

        event = receive_vehicle_status(payload)

        self.assertIsInstance(payload, bytes)
        self.assertGreater(len(payload), 0)

        self.assertEqual(
            "vehicle-001",
            event.metadata.vehicle_id,
        )
        self.assertTrue(event.metadata.event_id)
        self.assertTrue(event.metadata.trace_id)

        self.assertEqual(
            60.0,
            event.signals.speed_kph,
        )
        self.assertEqual(
            15.0,
            event.signals.battery_percent,
        )
        self.assertEqual(
            90.0,
            event.signals.temperature_celsius,
        )
        self.assertEqual(
            200.0,
            event.signals.coolant_pressure_kpa,
        )
        self.assertEqual(
            32.0,
            event.signals
            .tire_pressure_psi
            .front_left,
        )


if __name__ == "__main__":
    unittest.main()