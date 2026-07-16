import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DITTO_COMPONENT = PROJECT_ROOT / "eclipse-components" / "ditto"

sys.path.insert(0, str(DITTO_COMPONENT))

from uprotocol_transport import (
    publish_vehicle_status,
    receive_vehicle_status,
)


class UProtocolTransportTest(unittest.TestCase):

    def test_should_serialize_and_receive_vehicle_status(self):
        payload = publish_vehicle_status(
            vehicle_id="vehicle-001",
            speed_kph=60.0,
            battery_percent=15.0,
            temperature_celsius=90.0,
            tire_pressure_psi=32.0,
        )

        event = receive_vehicle_status(payload)

        self.assertIsInstance(payload, bytes)
        self.assertGreater(len(payload), 0)
        self.assertEqual("vehicle-001", event.metadata.vehicle_id)
        self.assertTrue(event.metadata.event_id)
        self.assertEqual(60.0, event.speed_kph)
        self.assertEqual(15.0, event.battery_percent)
        self.assertEqual(90.0, event.temperature_celsius)
        self.assertEqual(
            32.0,
            event.tire_pressure_psi.front_left
        )


if __name__ == "__main__":
    unittest.main()