# uProtocol Component

Defines the alert messages (events) the system uses to report vehicle
status and problems.

## Contents

```
uprotocol/
|-- README.md
|-- pom.xml                 <- Maven build config
|-- proto/                  <- message blueprints (Protobuf, not code)
|   |-- common.proto        <- shared fields (vehicle ID, event ID, timestamps)
|   |-- vehicle_status.proto
|   |-- health_status.proto
|   `-- vehicle_fault.proto
`-- demo/
    `-- demo_uprotocol_pipeline.py   <- Python test proving the blueprints work
```

## The four events

1. **VehicleStatusUpdated** — current speed, battery, temperature, tire pressure. Sent on every signal reading.
2. **HealthStatusChanged** — overall health changed (e.g. Healthy → Warning). Sent only on change.
3. **FaultDetected** — a specific problem was found (low battery, overheating, low tire pressure).
4. **FaultCleared** — that problem is fixed. Correlates back to the original `FaultDetected` via `event_id`.

## Note

- `.proto` files are message templates (Protobuf), not a programming language. Code gets generated from them.
- `pom.xml` is Maven's build config — dependencies only, no logic.
- `demo_uprotocol_pipeline.py` is Python, used only to quickly verify the message blueprints work (build -> send -> receive, no data loss). It is **not** the final implementation.
- Final implementation will be Java, using `up-java`.
