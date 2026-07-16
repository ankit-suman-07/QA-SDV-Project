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
|-- demo/
|   |-- demo_uprotocol_pipeline.py   <- enter signal values, auto-detects
|   |                                   faults and fires the correct events
|   `-- uprotocol_demo_log.log       <- example run output (evidence)
`-- src/main/java/com/sdv/uprotocol/
    `-- EventPublisher.java          <- bridge to the backend's health engine
```

## The four events

1. **VehicleStatusUpdated** — current speed, battery, temperature, tire pressure. Sent on every signal reading.
2. **HealthStatusChanged** — overall health changed (e.g. Healthy → Warning). Sent only on change.
3. **FaultDetected** — a specific problem was found (low battery, overheating, low tire pressure).
4. **FaultCleared** — that problem is fixed. Correlates back to the original `FaultDetected` via `event_id`.

## Key facts

- `.proto` files are message templates (Protobuf), not a programming language. Code gets generated from them.
- `pom.xml` is Maven's build config — dependencies only, no logic.
- `demo_uprotocol_pipeline.py` is Python, used only to verify the message blueprints and fault-detection logic work correctly (build -> evaluate against real fault thresholds -> send -> receive, no data loss). It automatically determines whether a fault/health-change should fire based on the values you enter - it does not ask redundant questions. It is **not** the final implementation.
- Final implementation will be Java, using `up-java`.

## How to Run

### 1. Set up the Python environment
Requires Python 3 and the Protobuf compiler (`protoc`).
```
pip install protobuf grpcio-tools
```

### 2. Generate Python classes from the proto schemas
```
python -m grpc_tools.protoc -I proto --python_out=generated proto/common.proto proto/vehicle_status.proto proto/health_status.proto proto/vehicle_fault.proto
```

### 3. Run the demo
```
cd demo
python3 demo_uprotocol_pipeline.py
```
You'll be asked for 7 signal values (speed, battery, temperature, 4 tire
pressures). The script automatically evaluates them against the
project's real fault thresholds (battery < 20%, temperature > 105C,
tire pressure < 28 psi) and only fires HealthStatusChanged/FaultDetected
events if a rule was actually triggered - no need to answer redundant
questions about faults separately.

Expect a summary at the end showing how many events fired and which
faults (if any) were triggered by your input. See `uprotocol_demo_log.log`
for an example run.

### 4. Compile and test EventPublisher.java standalone
Requires a JDK (Java 17+).
```
cd src/main/java
javac com/sdv/uprotocol/EventPublisher.java
```
This compiles with no external dependencies. To see it run, write a
small test class that calls its public methods (see
docs/evidence/eventpublisher-java-test-output.log for an example run
and its output).

### 5. Backend integration (in progress)
`EventPublisher.java` is not yet called by the backend. Integration
point: wherever the backend compares the previous health status to a
newly evaluated one, add a call to
`EventPublisher.publishHealthStatusChanged(...)`. See Known
Limitations below.

## Status

- [x] Schemas designed
- [x] Schemas verified (demo + evidence log)
- [x] Fault-detection logic verified against real thresholds
- [x] EventPublisher.java compiles and runs standalone
- [ ] Connected to real backend/simulator data
