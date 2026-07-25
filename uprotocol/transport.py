"""
uprotocol/transport.py

In-process Protobuf-based transport for vehicle events. Not a real
network transport (no MQTT/Zenoh broker) - messages are serialized and
deserialized exactly as they would be over a real wire, but delivered
via a direct in-process call.
"""
import sys
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_GENERATED_PROTO_PATH = _THIS_DIR / "generated"
if str(_GENERATED_PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(_GENERATED_PROTO_PATH))

import common_pb2
import vehicle_status_pb2


class DeliveryTracker:
    """Tracks published/received events for reliability reporting."""

    def __init__(self):
        self._lock = threading.Lock()
        self._published_ids = []
        self._received_ids = set()
        self._duplicate_count = 0
        self._invalid_count = 0
        self._reception_timestamps = {}

    def record_published(self, event_id):
        with self._lock:
            self._published_ids.append(event_id)

    def record_received(self, event_id, reception_timestamp):
        with self._lock:
            if event_id in self._received_ids:
                self._duplicate_count += 1
                return False
            self._received_ids.add(event_id)
            self._reception_timestamps[event_id] = reception_timestamp
            return True

    def record_invalid(self):
        with self._lock:
            self._invalid_count += 1

    def get_stats(self):
        with self._lock:
            published_set = set(self._published_ids)
            missing = published_set - self._received_ids
            return {
                "published_count": len(self._published_ids),
                "received_count": len(self._received_ids),
                "duplicate_count": self._duplicate_count,
                "missing_count": len(missing),
                "missing_event_ids": sorted(missing),
                "invalid_count": self._invalid_count,
            }

    def reset(self):
        with self._lock:
            self._published_ids.clear()
            self._received_ids.clear()
            self._duplicate_count = 0
            self._invalid_count = 0
            self._reception_timestamps.clear()


tracker = DeliveryTracker()


class InvalidMessageError(Exception):
    pass


def publish_vehicle_status(
        vehicle_id,
        speed_kph,
        battery_percent,
        temperature_celsius,
        tire_pressure_psi):
    timestamp = datetime.now(timezone.utc).isoformat()
    metadata = common_pb2.EventMetadata(
        vehicle_id=vehicle_id,
        event_id=str(uuid.uuid4()),
        source_timestamp=timestamp,
        event_timestamp=timestamp
    )
    event = vehicle_status_pb2.VehicleStatusUpdated(
        metadata=metadata,
        speed_kph=speed_kph,
        battery_percent=battery_percent,
        temperature_celsius=temperature_celsius,
        tire_pressure_psi=vehicle_status_pb2.TirePressure(
            front_left=tire_pressure_psi,
            front_right=tire_pressure_psi,
            rear_left=tire_pressure_psi,
            rear_right=tire_pressure_psi
        )
    )
    serialized_event = event.SerializeToString()
    tracker.record_published(metadata.event_id)
    print(
        f"[uProtocol Publisher] eventId={metadata.event_id} "
        f"vehicleId={vehicle_id} bytes={len(serialized_event)} "
        f"publicationTimestamp={timestamp}"
    )
    return serialized_event


def receive_vehicle_status(serialized_event):
    event = vehicle_status_pb2.VehicleStatusUpdated()
    try:
        event.ParseFromString(serialized_event)
    except Exception as e:
        tracker.record_invalid()
        raise InvalidMessageError(f"Failed to parse event: {e}") from e

    if not event.metadata.event_id or not event.metadata.vehicle_id:
        tracker.record_invalid()
        raise InvalidMessageError("Parsed event is missing required metadata fields")

    reception_timestamp = datetime.now(timezone.utc).isoformat()
    is_first_delivery = tracker.record_received(event.metadata.event_id, reception_timestamp)

    print(
        f"[uProtocol Receiver] eventId={event.metadata.event_id} "
        f"vehicleId={event.metadata.vehicle_id} "
        f"battery={event.battery_percent} "
        f"receptionTimestamp={reception_timestamp} "
        f"{'' if is_first_delivery else '(DUPLICATE)'}"
    )
    return event


def get_delivery_stats():
    return tracker.get_stats()
