"""
Run: python3 -m pytest uprotocol/tests/test_transport.py -v
"""
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from uprotocol.transport import (
    publish_vehicle_status,
    receive_vehicle_status,
    get_delivery_stats,
    InvalidMessageError,
    tracker,
)


class TransportTests(unittest.TestCase):

    def setUp(self):
        tracker.reset()

    def test_serialization_and_deserialization_round_trip(self):
        serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
        event = receive_vehicle_status(serialized)
        self.assertEqual(event.metadata.vehicle_id, "vehicle-001")
        self.assertEqual(event.signals.speed_kph, 60.0)
        self.assertEqual(event.signals.battery_percent, 74.0)
        self.assertEqual(event.signals.temperature_celsius, 88.0)
        self.assertEqual(event.signals.coolant_pressure_kpa, 200.0)
        self.assertEqual(event.signals.tire_pressure_psi.front_left, 32.0)

    def test_matching_event_ids(self):
        serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
        published_id = tracker._published_ids[-1]
        event = receive_vehicle_status(serialized)
        self.assertEqual(event.metadata.event_id, published_id)

    def test_unique_event_ids_across_multiple_publishes(self):
        ids = []
        for _ in range(20):
            serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
            event = receive_vehicle_status(serialized)
            ids.append(event.metadata.event_id)
        self.assertEqual(len(ids), len(set(ids)))

    def test_timestamp_preservation(self):
        serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
        import uprotocol.transport as t
        event_before = t.vehicle_status_pb2.VehicleStatusUpdated()
        event_before.ParseFromString(serialized)
        published_ts = event_before.metadata.source_timestamp

        event_after = receive_vehicle_status(serialized)
        self.assertEqual(event_after.metadata.source_timestamp, published_ts)

    def test_corrupted_message_is_rejected_not_crashed(self):
        garbage = b"\xff\xfe\x00\x01this-is-not-a-valid-protobuf-message\x00\xff"
        with self.assertRaises(InvalidMessageError):
            receive_vehicle_status(garbage)
        stats = get_delivery_stats()
        self.assertEqual(stats["invalid_count"], 1)

    def test_message_missing_required_fields_is_rejected(self):
        import uprotocol.transport as t
        empty_event = t.vehicle_status_pb2.VehicleStatusUpdated(
            signals=t.vehicle_status_pb2.VehicleSignals(speed_kph=10.0)
        )
        serialized = empty_event.SerializeToString()
        with self.assertRaises(InvalidMessageError):
            receive_vehicle_status(serialized)

    def test_duplicate_detection(self):
        serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
        receive_vehicle_status(serialized)
        receive_vehicle_status(serialized)
        stats = get_delivery_stats()
        self.assertEqual(stats["received_count"], 1)
        self.assertEqual(stats["duplicate_count"], 1)

    def test_missing_event_detection(self):
        serialized_1 = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
        _ = publish_vehicle_status("vehicle-001", 61.0, 73.5, 89.0, 195.0, 31.9)
        receive_vehicle_status(serialized_1)
        stats = get_delivery_stats()
        self.assertEqual(stats["published_count"], 2)
        self.assertEqual(stats["received_count"], 1)
        self.assertEqual(stats["missing_count"], 1)

    def test_delivery_stats_exposed_and_accumulate(self):
        for _ in range(5):
            serialized = publish_vehicle_status("vehicle-001", 60.0, 74.0, 88.0, 200.0, 32.0)
            receive_vehicle_status(serialized)
        stats = get_delivery_stats()
        self.assertEqual(stats["published_count"], 5)
        self.assertEqual(stats["received_count"], 5)
        self.assertEqual(stats["duplicate_count"], 0)
        self.assertEqual(stats["missing_count"], 0)
        self.assertEqual(stats["invalid_count"], 0)


if __name__ == "__main__":
    unittest.main()
