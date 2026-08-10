"""
uprotocol/transport.py

In-process Protobuf-based transport for vehicle events. Not a real
network transport (no MQTT/Zenoh broker) - messages are serialized and
deserialized exactly as they would be over a real wire, but delivered
via a direct in-process call.

Extended for Iteration 3: carries schema_version, trace_id, action_id,
and event_type on every message, and supports the correlated-fault and
diagnostic-action event types in addition to the original
VehicleStatusUpdated.
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
import vehicle_fault_pb2
import vehicle_diagnostic_pb2

SCHEMA_VERSION = "1.0.0"


class DeliveryTracker:
    """Tracks published/received events for reliability reporting.
    Type-agnostic: works the same for any event type, since it only
    keys on event_id."""

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


def _now():
    return datetime.now(timezone.utc).isoformat()


def _build_metadata(vehicle_id, event_type, trace_id=None, action_id=None):
    """Shared metadata builder for every event type. trace_id defaults
    to a new UUID if not given (matches the contract: trace_id must
    always be present). action_id is left unset (proto3 optional) when
    not given - e.g. for normal telemetry with no diagnostic request."""
    kwargs = dict(
        schema_version=SCHEMA_VERSION,
        event_id=str(uuid.uuid4()),
        trace_id=trace_id or str(uuid.uuid4()),
        vehicle_id=vehicle_id,
        event_type=event_type,
        source_timestamp=_now(),
        publication_timestamp=_now(),
    )
    if action_id is not None:
        kwargs["action_id"] = action_id
    return common_pb2.EventMetadata(**kwargs)


def _finish_publish(event_id, log_label, extra=""):
    tracker.record_published(event_id)
    print(f"[uProtocol Publisher] {log_label} eventId={event_id} {extra}")


def _finish_receive(metadata, log_label, extra=""):
    if not metadata.event_id or not metadata.vehicle_id:
        tracker.record_invalid()
        raise InvalidMessageError("Parsed event is missing required metadata fields")
    reception_timestamp = _now()
    is_first = tracker.record_received(metadata.event_id, reception_timestamp)
    print(f"[uProtocol Receiver] {log_label} eventId={metadata.event_id} "
          f"receptionTimestamp={reception_timestamp} {extra} "
          f"{'' if is_first else '(DUPLICATE)'}")


def _parse_or_invalid(message_cls, serialized):
    message = message_cls()
    try:
        message.ParseFromString(serialized)
    except Exception as e:
        tracker.record_invalid()
        raise InvalidMessageError(f"Failed to parse event: {e}") from e
    return message


# --- VehicleStatusUpdated ---

def publish_vehicle_status(
        vehicle_id, speed_kph, battery_percent, temperature_celsius,
        coolant_pressure_kpa, tire_pressure_psi,
        trace_id=None, action_id=None):
    metadata = _build_metadata(vehicle_id, common_pb2.VEHICLE_STATUS_UPDATED,
                                trace_id=trace_id, action_id=action_id)
    event = vehicle_status_pb2.VehicleStatusUpdated(
        metadata=metadata,
        signals=vehicle_status_pb2.VehicleSignals(
            speed_kph=speed_kph,
            battery_percent=battery_percent,
            temperature_celsius=temperature_celsius,
            coolant_pressure_kpa=coolant_pressure_kpa,
            tire_pressure_psi=vehicle_status_pb2.TirePressure(
                front_left=tire_pressure_psi,
                front_right=tire_pressure_psi,
                rear_left=tire_pressure_psi,
                rear_right=tire_pressure_psi,
            ),
        ),
    )
    serialized = event.SerializeToString()
    _finish_publish(metadata.event_id, "VehicleStatusUpdated", f"bytes={len(serialized)}")
    return serialized


def receive_vehicle_status(serialized):
    event = _parse_or_invalid(vehicle_status_pb2.VehicleStatusUpdated, serialized)
    _finish_receive(event.metadata, "VehicleStatusUpdated",
                     f"battery={event.signals.battery_percent}")
    return event


# --- CorrelatedFaultDetected / Cleared ---

def publish_correlated_fault_detected(
        vehicle_id, fault_code, description, severity,
        affected_signals, observed_values, activation_thresholds,
        trace_id=None, action_id=None):
    metadata = _build_metadata(vehicle_id, common_pb2.CORRELATED_FAULT_DETECTED,
                                trace_id=trace_id, action_id=action_id)
    event = vehicle_diagnostic_pb2.CorrelatedFaultDetected(
        metadata=metadata,
        fault_code=fault_code,
        description=description,
        severity=severity,
        affected_signals=affected_signals,
        observed_values=observed_values,
        activation_thresholds=activation_thresholds,
        detected_at=metadata.source_timestamp,
    )
    serialized = event.SerializeToString()
    _finish_publish(metadata.event_id, "CorrelatedFaultDetected",
                     f"faultCode={vehicle_diagnostic_pb2.CorrelatedFaultCode.Name(fault_code)}")
    return serialized, metadata.event_id


def receive_correlated_fault_detected(serialized):
    event = _parse_or_invalid(vehicle_diagnostic_pb2.CorrelatedFaultDetected, serialized)
    _finish_receive(event.metadata, "CorrelatedFaultDetected")
    return event


def publish_correlated_fault_cleared(
        vehicle_id, fault_code, affected_signals, observed_values,
        recovery_thresholds, trace_id=None, action_id=None):
    metadata = _build_metadata(vehicle_id, common_pb2.CORRELATED_FAULT_CLEARED,
                                trace_id=trace_id, action_id=action_id)
    event = vehicle_diagnostic_pb2.CorrelatedFaultCleared(
        metadata=metadata,
        fault_code=fault_code,
        affected_signals=affected_signals,
        observed_values=observed_values,
        recovery_thresholds=recovery_thresholds,
        cleared_at=metadata.source_timestamp,
    )
    serialized = event.SerializeToString()
    _finish_publish(metadata.event_id, "CorrelatedFaultCleared",
                     f"faultCode={vehicle_diagnostic_pb2.CorrelatedFaultCode.Name(fault_code)}")
    return serialized


def receive_correlated_fault_cleared(serialized):
    event = _parse_or_invalid(vehicle_diagnostic_pb2.CorrelatedFaultCleared, serialized)
    _finish_receive(event.metadata, "CorrelatedFaultCleared")
    return event


# --- DiagnosticActionRequested / Accepted ---

def publish_diagnostic_action_requested(
        vehicle_id, action, scenario, action_id, trace_id=None):
    metadata = _build_metadata(vehicle_id, common_pb2.DIAGNOSTIC_ACTION_REQUESTED,
                                trace_id=trace_id, action_id=action_id)
    event = vehicle_diagnostic_pb2.DiagnosticActionRequested(
        metadata=metadata, action=action, scenario=scenario,
    )
    serialized = event.SerializeToString()
    _finish_publish(metadata.event_id, "DiagnosticActionRequested",
                     f"action={vehicle_diagnostic_pb2.DiagnosticAction.Name(action)}")
    return serialized


def receive_diagnostic_action_requested(serialized):
    event = _parse_or_invalid(vehicle_diagnostic_pb2.DiagnosticActionRequested, serialized)
    _finish_receive(event.metadata, "DiagnosticActionRequested")
    return event


def publish_diagnostic_action_accepted(
        vehicle_id, action, scenario, status, action_id, trace_id=None):
    metadata = _build_metadata(vehicle_id, common_pb2.DIAGNOSTIC_ACTION_ACCEPTED,
                                trace_id=trace_id, action_id=action_id)
    event = vehicle_diagnostic_pb2.DiagnosticActionAccepted(
        metadata=metadata, action=action, scenario=scenario, status=status,
    )
    serialized = event.SerializeToString()
    _finish_publish(metadata.event_id, "DiagnosticActionAccepted",
                     f"status={vehicle_diagnostic_pb2.DiagnosticActionStatus.Name(status)}")
    return serialized


def receive_diagnostic_action_accepted(serialized):
    event = _parse_or_invalid(vehicle_diagnostic_pb2.DiagnosticActionAccepted, serialized)
    _finish_receive(event.metadata, "DiagnosticActionAccepted")
    return event


def get_delivery_stats():
    return tracker.get_stats()
