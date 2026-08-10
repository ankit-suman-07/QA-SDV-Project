import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from uprotocol import transport
from uprotocol.transport import (
    publish_vehicle_status, receive_vehicle_status,
    publish_correlated_fault_detected, receive_correlated_fault_detected,
    publish_correlated_fault_cleared, receive_correlated_fault_cleared,
    publish_diagnostic_action_requested, receive_diagnostic_action_requested,
    publish_diagnostic_action_accepted, receive_diagnostic_action_accepted,
    get_delivery_stats, tracker,
)
sys.path.insert(0, str(Path(__file__).resolve().parent / "uprotocol" / "generated"))
import vehicle_diagnostic_pb2
import vehicle_fault_pb2

tracker.reset()

print("=== 1. VehicleStatusUpdated (with coolant pressure) ===")
serialized = publish_vehicle_status(
    "vehicle-001", 60.0, 75.0, 108.0, 140.0, 32.0
)
event = receive_vehicle_status(serialized)
assert event.signals.coolant_pressure_kpa == 140.0
assert event.metadata.schema_version == "1.0.0"
assert event.metadata.HasField("action_id") == False
print("[OK] coolant pressure and schema_version correct, action_id absent\n")

print("=== 2. Full diagnostic action + correlated fault flow, same trace_id ===")
action_id = "action-001"
trace_id = "trace-001"

req_bytes = publish_diagnostic_action_requested(
    "vehicle-001", vehicle_diagnostic_pb2.INJECT_SCENARIO,
    vehicle_diagnostic_pb2.SCENARIO_COOLING_SYSTEM_FAILURE,
    action_id, trace_id=trace_id,
)
req_event = receive_diagnostic_action_requested(req_bytes)
assert req_event.metadata.action_id == action_id
assert req_event.metadata.trace_id == trace_id
print("[OK] DiagnosticActionRequested carries correct action_id/trace_id")

acc_bytes = publish_diagnostic_action_accepted(
    "vehicle-001", vehicle_diagnostic_pb2.INJECT_SCENARIO,
    vehicle_diagnostic_pb2.SCENARIO_COOLING_SYSTEM_FAILURE,
    vehicle_diagnostic_pb2.ACCEPTED, action_id, trace_id=trace_id,
)
acc_event = receive_diagnostic_action_accepted(acc_bytes)
assert acc_event.status == vehicle_diagnostic_pb2.ACCEPTED
print("[OK] DiagnosticActionAccepted status correct")

fault_bytes, fault_event_id = publish_correlated_fault_detected(
    "vehicle-001",
    vehicle_diagnostic_pb2.COOLING_SYSTEM_FAILURE,
    "High temperature correlated with low coolant pressure",
    vehicle_fault_pb2.FAULT_CRITICAL,
    ["temperatureCelsius", "coolantPressureKpa"],
    {"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
    {"temperatureCelsius": 105.0, "coolantPressureKpa": 150.0},
    trace_id=trace_id, action_id=action_id,
)
fault_event = receive_correlated_fault_detected(fault_bytes)
assert fault_event.metadata.trace_id == trace_id, "fault event must share the same trace_id as the action"
assert fault_event.observed_values["coolantPressureKpa"] == 140.0
print("[OK] CorrelatedFaultDetected shares trace_id with the triggering action, values correct")

cleared_bytes = publish_correlated_fault_cleared(
    "vehicle-001", vehicle_diagnostic_pb2.COOLING_SYSTEM_FAILURE,
    ["temperatureCelsius", "coolantPressureKpa"],
    {"temperatureCelsius": 98.0, "coolantPressureKpa": 190.0},
    {"temperatureCelsius": 100.0, "coolantPressureKpa": 180.0},
    trace_id=trace_id, action_id=action_id,
)
cleared_event = receive_correlated_fault_cleared(cleared_bytes)
assert cleared_event.metadata.trace_id == trace_id
print("[OK] CorrelatedFaultCleared shares trace_id\n")

print("=== 3. Delivery stats now cover all 5 event types ===")
stats = get_delivery_stats()
print(stats)
assert stats["published_count"] == 5
assert stats["received_count"] == 5
assert stats["duplicate_count"] == 0
assert stats["missing_count"] == 0
assert stats["invalid_count"] == 0
print("[OK] DeliveryTracker correctly counted all 5 event types (vehicle status, "
      "action requested, action accepted, fault detected, fault cleared)\n")

print("=" * 50)
print("ALL TRANSPORT.PY EXTENSION TESTS PASSED")
print("=" * 50)
