# uProtocol Component

Event schemas and in-process transport for vehicle status/health/fault/diagnostic events.

## Contents

```
uprotocol/
|-- README.md
|-- pom.xml
|-- __init__.py
|-- transport.py
|-- proto/
|   |-- common.proto
|   |-- vehicle_status.proto
|   |-- health_status.proto
|   |-- vehicle_fault.proto
|   `-- vehicle_diagnostic.proto
|-- generated/
|-- tests/
|   |-- test_transport.py
|   `-- verify_contract_match.py
|-- demo/
`-- src/main/java/com/sdv/uprotocol/
    `-- EventPublisher.java
```

## Schema versioning

`schema_version` is set to `"1.0.0"` per the Iteration 3 Shared Integration
Contract. Breaking changes to shared fields require incrementing this
value and updating the contract document.

## Event types

| Event | File | Purpose |
|---|---|---|
| `VehicleStatusUpdated` | vehicle_status.proto | Signal snapshot, sent on every reading |
| `HealthStatusChanged` | health_status.proto | Health transition (Healthy/Warning/Critical) |
| `FaultDetected` / `FaultCleared` | vehicle_fault.proto | Single-signal fault lifecycle |
| `CorrelatedFaultDetected` / `CorrelatedFaultCleared` | vehicle_diagnostic.proto | Multi-signal fault lifecycle (e.g. temperature + coolant pressure) |
| `DiagnosticActionRequested` / `DiagnosticActionAccepted` | vehicle_diagnostic.proto | Diagnostic action lifecycle (inject/clear scenario) |

## Key contract details

- `action_id` uses proto3 explicit field presence (`optional`). It is
  genuinely absent for normal telemetry, not just an empty string.
- `trace_id` and `action_id` are separate fields but may hold the same
  value, per the contract.
- Correlated faults carry `affected_signals` (repeated) and
  `observed_values`/`activation_thresholds`/`recovery_thresholds` as
  maps, supporting more than two correlated signals if needed later.
- `reception_timestamp` is not a wire field - it cannot be known by the
  publisher. It is recorded by transport.py at receive time.

## Confirmed enums

`DiagnosticAction`: `INJECT_SCENARIO`, `CLEAR_SCENARIO` (status querying
is a separate GET operation, not part of this enum).

`DiagnosticActionStatus`: `ACCEPTED`, `IN_PROGRESS`, `COMPLETED`,
`FAILED`, `REJECTED`. Legal transitions:
```
ACCEPTED -> IN_PROGRESS -> COMPLETED
ACCEPTED -> IN_PROGRESS -> FAILED
ACCEPTED -> FAILED
REJECTED (terminal, no prior state)
```

## Open items

- Coolant pressure's Kuksa/VSS path is `TO_BE_CONFIRMED` in the
  contract itself - project-wide blocker, not schema-specific.

## Tests

| Test | Checks |
|---|---|
| `test_serialization_and_deserialization_round_trip` | No data lost converting a message to bytes and back |
| `test_matching_event_ids` | Published event ID matches received event ID |
| `test_unique_event_ids_across_multiple_publishes` | No duplicate IDs across 20 publishes |
| `test_timestamp_preservation` | Timestamp unchanged after the wire round-trip |
| `test_corrupted_message_is_rejected_not_crashed` | Broken bytes raise a clean error, not a crash |
| `test_message_missing_required_fields_is_rejected` | A message with no vehicle/event ID is rejected |
| `test_duplicate_detection` | Same message delivered twice counts as 1 delivery + 1 duplicate |
| `test_missing_event_detection` | A published-but-undelivered message is correctly flagged missing |
| `test_delivery_stats_exposed_and_accumulate` | `get_delivery_stats()` returns accurate counts |
| `verify_contract_match.py` | Schemas produce correct output against the contract's own example data (action_id presence, correlated fault fields, diagnostic action enums) |

## How to Run

```
pip install protobuf grpcio-tools pytest
python -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated uprotocol/proto/common.proto uprotocol/proto/vehicle_status.proto uprotocol/proto/health_status.proto uprotocol/proto/vehicle_fault.proto uprotocol/proto/vehicle_diagnostic.proto
python3 -m pytest uprotocol/tests/test_transport.py -v
python3 uprotocol/tests/verify_contract_match.py
```
Expect `9 passed` and `ALL 4 VERIFICATION TESTS PASSED`.

Query stats:
```python
from uprotocol.transport import get_delivery_stats
print(get_delivery_stats())
```

## Status

- [x] Iteration 1-2 schemas designed and verified
- [x] transport.py located at uprotocol/, bridge import updated
- [x] Delivery tracking: published, received, duplicate, missing, invalid
- [x] Transport tests passing (9/9)
- [x] EventPublisher.java compiles, JUnit tests passing (7/7)
- [x] Iteration 3 schemas (coolant pressure, correlated fault, diagnostic actions) verified against the shared contract (4/4)
- [ ] transport.py extended to carry Iteration 3 fields (trace_id, action_id, event_type, schema_version)
- [ ] Delivery tracking extended for new event types
- [ ] Real network transport (MQTT/Zenoh)
- [ ] Full live backend connection
