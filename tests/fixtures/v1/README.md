# V1 deterministic contract fixtures

Development/test data for [contract 1.0.0](../../../docs/v1-interface-contracts.md), proposed for review. These are not live vehicle observations. All files are syntactically valid JSON; negative fixtures are semantically invalid on purpose.

Use one clock: epoch `2026-01-01T00:00:00Z`, evaluation time `2026-01-01T00:00:04Z`. Rebase every source timestamp by the same offset for current-time runs. `scripts.v1_dev.contract.rebase_event` and MQTT replay implement this; do not independently stamp each fixture with now. Event IDs are deterministic; replay appends `--run-id` (default `replay-1`). Use a new run ID and a later anchor for another run against an existing watermark.

| Fixture | Intended use / expected result |
|---|---|
| vehicle-001-healthy.json | Vehicle 001 healthy; AVAILABLE at test clock; remains unaffected throughout cycle |
| vehicle-002-healthy.json | Vehicle 002 initial healthy; source epoch |
| vehicle-002-fault.json | Vehicle 002 CRITICAL, LIDAR_OBSTRUCTION at 3 m; source epoch+1 s |
| vehicle-002-recovered.json | Vehicle 002 healthy after clear; source epoch+2 s |
| vehicle-002-stale.json | Valid event, source epoch−2 s; STALE at evaluation time (age 6 s) |
| vehicle-unknown.json | UNKNOWN_VEHICLE; no twin mutation |
| event-malformed.json | Valid JSON but missing sourceTimestamp → MISSING_FIELD; also contains invalid string sensorAvailable. Restore timestamp to test INVALID_TYPE independently. |
| event-out-of-order.json | Valid event alone; OUT_OF_ORDER after vehicle-002-healthy or fault; no watermark/twin mutation |
| ditto-vehicle-001.json | Whole-Thing healthy vehicle 001; v1 feature; all identity locations agree |
| ditto-vehicle-002.json | Whole-Thing healthy vehicle 002; separate identity/features |
| fleet-summary.json | Both AVAILABLE and healthy at fixed clock; denominator 2; source timestamps retained |
| scenario-inject-request.json | Public backend request targeting vehicle-002; add backend-generated actionId/traceId only at provider dispatch boundary |
| scenario-clear-request.json | Public clear request for vehicle-002; acceptance is not recovery evidence |

Malformed JSON bytes, duplicate keys, wrong topic/type/version, missing/invalid timestamp, sensor failure, numeric boundaries, unavailable/missing twins and future clock data are constructed in tests rather than committed as syntactically invalid JSON. Thus repository-wide JSON validation remains useful. Provider rejection/timeout/disconnect are explicit HTTP mock controls, not alternate production payloads.
