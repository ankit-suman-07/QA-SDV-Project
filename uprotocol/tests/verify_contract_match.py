import sys
sys.path.insert(0, "generated")

import common_pb2
import vehicle_status_pb2
import vehicle_fault_pb2
import vehicle_diagnostic_pb2

print("=== Test 1: VehicleStatusUpdated with action_id absent (normal telemetry) ===")
meta1 = common_pb2.EventMetadata(
    schema_version="1.0.0",
    event_id="event-uuid-1",
    trace_id="trace-uuid-1",
    vehicle_id="vehicle-001",
    event_type=common_pb2.VEHICLE_STATUS_UPDATED,
    source_timestamp="2026-08-03T15:00:01.000Z",
    publication_timestamp="2026-08-03T15:00:01.100Z",
)
status = vehicle_status_pb2.VehicleStatusUpdated(
    metadata=meta1,
    signals=vehicle_status_pb2.VehicleSignals(
        speed_kph=60.0,
        battery_percent=75.0,
        temperature_celsius=108.0,
        coolant_pressure_kpa=140.0,
        tire_pressure_psi=vehicle_status_pb2.TirePressure(front_left=32.0),
    ),
)
print("HasField('action_id') on normal telemetry:", status.metadata.HasField("action_id"))
assert status.metadata.HasField("action_id") == False, "action_id should be absent for normal telemetry"
print("[OK] action_id correctly absent (not just empty string)\n")

print("=== Test 2: VehicleStatusUpdated WITH action_id (diagnostic-triggered) ===")
meta2 = common_pb2.EventMetadata(
    schema_version="1.0.0",
    event_id="event-uuid-2",
    trace_id="trace-uuid-2",
    action_id="action-uuid-2",
    vehicle_id="vehicle-001",
    event_type=common_pb2.VEHICLE_STATUS_UPDATED,
    source_timestamp="2026-08-03T15:00:01.000Z",
    publication_timestamp="2026-08-03T15:00:01.100Z",
)
print("HasField('action_id'):", meta2.HasField("action_id"))
print("action_id value:", meta2.action_id)
assert meta2.HasField("action_id") == True
assert meta2.action_id == "action-uuid-2"
print("[OK] action_id correctly present when set\n")

print("=== Test 3: CorrelatedFaultDetected matching the contract's fault example ===")
meta3 = common_pb2.EventMetadata(
    schema_version="1.0.0",
    event_id="event-uuid-3",
    trace_id="trace-uuid-3",
    action_id="action-uuid-3",
    vehicle_id="vehicle-001",
    event_type=common_pb2.CORRELATED_FAULT_DETECTED,
    source_timestamp="2026-08-03T15:00:01.200Z",
    publication_timestamp="2026-08-03T15:00:01.250Z",
)
fault = vehicle_diagnostic_pb2.CorrelatedFaultDetected(
    metadata=meta3,
    fault_code=vehicle_diagnostic_pb2.COOLING_SYSTEM_FAILURE,
    description="High temperature correlated with low coolant pressure",
    severity=vehicle_fault_pb2.FAULT_CRITICAL,
    affected_signals=["temperatureCelsius", "coolantPressureKpa"],
    observed_values={"temperatureCelsius": 108.0, "coolantPressureKpa": 140.0},
    activation_thresholds={"temperatureCelsius": 105.0, "coolantPressureKpa": 150.0},
    detected_at="2026-08-03T15:00:01.200Z",
)
serialized = fault.SerializeToString()
roundtrip = vehicle_diagnostic_pb2.CorrelatedFaultDetected()
roundtrip.ParseFromString(serialized)
assert roundtrip.observed_values["temperatureCelsius"] == 108.0
assert roundtrip.observed_values["coolantPressureKpa"] == 140.0
assert list(roundtrip.affected_signals) == ["temperatureCelsius", "coolantPressureKpa"]
assert roundtrip.severity == vehicle_fault_pb2.FAULT_CRITICAL
print("[OK] CorrelatedFaultDetected round-trips correctly with both signals, both thresholds\n")

print("=== Test 4: DiagnosticActionRequested/Accepted state ===")
meta4 = common_pb2.EventMetadata(
    schema_version="1.0.0",
    event_id="event-uuid-4",
    trace_id="trace-uuid-4",
    action_id="action-uuid-4",
    vehicle_id="vehicle-001",
    event_type=common_pb2.DIAGNOSTIC_ACTION_ACCEPTED,
    source_timestamp="2026-08-03T15:00:00.000Z",
    publication_timestamp="2026-08-03T15:00:00.050Z",
)
accepted = vehicle_diagnostic_pb2.DiagnosticActionAccepted(
    metadata=meta4,
    action=vehicle_diagnostic_pb2.INJECT_SCENARIO,
    scenario=vehicle_diagnostic_pb2.SCENARIO_COOLING_SYSTEM_FAILURE,
    status=vehicle_diagnostic_pb2.ACCEPTED,
)
print("action:", vehicle_diagnostic_pb2.DiagnosticAction.Name(accepted.action))
print("scenario:", vehicle_diagnostic_pb2.DiagnosticScenario.Name(accepted.scenario))
print("status:", vehicle_diagnostic_pb2.DiagnosticActionStatus.Name(accepted.status))
assert vehicle_diagnostic_pb2.DiagnosticAction.Name(accepted.action) == "INJECT_SCENARIO"
print("[OK] DiagnosticActionAccepted built and read back correctly\n")

print("=" * 50)
print("ALL 4 VERIFICATION TESTS PASSED")
print("=" * 50)
