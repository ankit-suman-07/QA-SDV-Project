Software-Defined Vehicle Health Monitoring and Diagnostic System
Project Overview
This project implements a Software-Defined Vehicle (SDV) data pipeline for one simulated vehicle, vehicle-001.
The system generates vehicle telemetry, publishes it to Eclipse Kuksa, transfers the normalized state through a Protobuf-based communication layer, evaluates a basic vehicle-health rule, and synchronizes the resulting state with an Eclipse Ditto digital twin.
Iteration 1 built and proved out the baseline end-to-end pipeline at a single, fixed publication rate: the simulator generates telemetry for one vehicle (vehicle-001), publishes it to a real Eclipse Kuksa Databroker, and the bridge reads those signals, wraps them in a serialized Protobuf VehicleStatusUpdated event, evaluates the battery-health rule, and synchronizes the result to a real Eclipse Ditto digital twin over its REST API. This was validated with real running instances of Kuksa and Ditto rather than mocks — policy and Thing creation, single-property updates, and full-state verification were all exercised against a live Ditto container, confirming that partial state updates apply correctly without disturbing unrelated fields. Iteration 1 also proved a repeatable fault scenario end to end: injecting a low-battery condition in the simulator visibly propagates through the bridge's health rule into WARNING/BATTERY_LOW on the live twin, and clearing it visibly recovers the twin to HEALTHY. An early mock integration with Eclipse OpenSOVD (gateway topology and component discovery) was also demonstrated, though OpenSOVD is not yet part of the main pipeline. See docs/evidence/integration-tests/ditto-kuksa/ for the full evidence, including exact commands and responses.
Iteration 2 extends this baseline with a configurable signal publication rate, message-delivery tracking, automated digital-twin validation, and latency/throughput measurement across multiple publication rates.
Demonstrated in Iteration 1:
•	Simulated vehicle telemetry generation
•	Eclipse Kuksa signal publication and retrieval
•	Protobuf event serialization and reception
•	Eclipse Ditto digital-twin synchronization, including verified partial-state updates
•	A repeatable low-battery fault scenario, trigger and recovery
•	Automated verification of the message flow
•	An early mock OpenSOVD integration (gateway topology, component discovery)
Added in Iteration 2:
•	Automated verification of the Ditto digital twin itself (field completeness, freshness, health-state consistency) complete
•	Configurable publication rate with latency/throughput measurement 
A Spring Boot backend skeleton also exists under backend/ with pluggable adapters for Kuksa, Ditto, uProtocol, and OpenSOVD. It currently runs only in development mode against mocked adapter implementations and is not yet part of the demonstrated pipeline below — see Known Limitations.
Implemented Architecture
flowchart TD
    A["Vehicle Simulator<br/>Python"] -->|"Publishes VSS signals"| B["Eclipse Kuksa Databroker<br/>gRPC"]
    B -->|"Reads current values"| C["Ditto Bridge<br/>Python integration service"]
    C -->|"VehicleStatusUpdated"| D["Protobuf Publisher<br/>Serialize to bytes"]
    D -->|"In-process delivery"| E["Protobuf Receiver<br/>Deserialize event"]
    E -->|"Received vehicle state"| F["Battery Health Rule"]
    F -->|"Signals and health state"| G["Eclipse Ditto<br/>vehicle-001"]
    G -->|"REST API"| H["Verification<br/>ditto/scripts/verify-vehicle-state.py"]
This diagram is unchanged from Iteration 1: the demonstrated pipeline still runs through the Python bridge rather than the backend skeleton. It will be updated once the backend adapters are connected to real components.
Component Roles
Component	Role
Vehicle Simulator	Generates speed, battery, temperature, and tire-pressure values at a configurable publication rate and supports repeatable fault injection.
Eclipse Kuksa	Receives and exposes vehicle signals using VSS paths.
Ditto Bridge	Reads Kuksa signals and coordinates message processing, health evaluation, and Ditto synchronization.
Protobuf Communication Layer	Serializes VehicleStatusUpdated events into bytes and deserializes them at the receiver.
Health Rule	Produces WARNING and BATTERY_LOW when battery level is below 20%.
Eclipse Ditto	Store the latest signals and calculated health state for vehicle-001.
State Verifier	Independently validates the live Ditto twin: required fields present, health status internally consistent, and twin freshness within max(3 x publication interval, 5s).
Current Communication-Layer Scope
The pipeline uses Protobuf serialization with an in-process uProtocol-compatible publisher and receiver. It demonstrates observable message creation, byte serialization, delivery, deserialization, and event-ID traceability.
This baseline is not a production uProtocol transport. A distributed uProtocol transport and additional event types are planned for later iterations.
Repository Structure
QA-SDV-Project/
├── backend/                       
├── docs/
│   └── evidence/
│       └── iteration-2/
│           ├── functional-validation/  
│           ├── publication-rate/       
│           ├── transport/               
│           └── results/                 
├── ditto/
│   ├── config/
│   │   ├── vehicle-001-thing.json
│   │   └── vehicle-policy.json
│   ├── scripts/
│   │   ├── interim-kuksa-to-ditto-bridge.py
│   │   └── verify-vehicle-state.py
│   └── README.md
├── frontend/                      
├── tests/
│   ├── test_uprotocol_transport.py
│   ├── test_verify_vehicle_state.py
│   └── performance/
│       ├── process_results.py     
│       └── results/                
├── uprotocol/
│   ├── proto/                     
│   └── generated/                 
└── vehicle-simulator/
    ├── src/
    ├── Dockerfile
    └── docker-compose.yml
Ditto configuration and scripts now live under ditto/.

Vehicle Signals
Signal	Kuksa/VSS path
Speed	Vehicle.Speed
Battery level	Vehicle.Powertrain.TractionBattery.StateOfCharge.Current
Engine temperature	Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature
Front-left tire pressure	Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure
Prerequisites
•	Git
•	Docker Desktop with Docker Compose
•	At least 4 GB of memory allocated to Docker Desktop
•	Python 3.10 or newer
•	curl
1. Clone the Project
git clone https://github.com/ankit-suman-07/QA-SDV-Project.git
cd QA-SDV-Project
2. Create the Python Environment
python3 -m venv .venv
source .venv/bin/activate       
python -m pip install --upgrade pip
python -m pip install kuksa_client requests python-dotenv
The generated Protobuf Python classes are included under uprotocol/generated, so protoc is not required merely to run the demonstrated pipeline.
3. Start Eclipse Ditto
Clone the official Ditto runtime into a location outside this repository — it is not, and should not be, committed here:
git clone --depth 1 https://github.com/eclipse-ditto/ditto.git ../eclipse-ditto-runtime
cd ../eclipse-ditto-runtime/deployment/docker
docker compose up -d
Wait for initialization, then confirm the API responds:
docker compose ps
curl -i -u ditto:ditto http://localhost:8080/api/2/things
Return to the project root before continuing.
4. Create the Ditto Policy and Vehicle Thing
From the project root:
curl -i -u ditto:ditto -X PUT -H "Content-Type: application/json" \
  --data-binary @ditto/config/vehicle-policy.json \
  http://localhost:8080/api/2/policies/sdv:vehicle-001-policy

curl -i -u ditto:ditto -X PUT -H "Content-Type: application/json" \
  --data-binary @ditto/config/vehicle-001-thing.json \
  http://localhost:8080/api/2/things/sdv:vehicle-001
Verify:
curl -s -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001 | python3 -m json.tool
5. Start Eclipse Kuksa and the Vehicle Simulator
The Kuksa Databroker is exposed on host port 55556 (mapped from 55555 inside Docker) to avoid local port conflicts.
Ensure normal mode in vehicle-simulator/docker-compose.yml:
- INJECT_FAULT=0
Start and verify:
docker compose -f vehicle-simulator/docker-compose.yml up --build -d
docker compose -f vehicle-simulator/docker-compose.yml ps
docker compose -f vehicle-simulator/docker-compose.yml logs --tail=20 provider
Expected log line:
[normal] speed=60.1 battery=82.1 engine_temp=90.1 tire_pressure=32.2
Publication-rate configuration 
The simulator currently publishes on a fixed 5-second interval (time.sleep(5) in vehicle-simulator/src/main.py). A PUBLISH_INTERVAL_SECONDS environment variable is planned so the interval can be set per experiment condition:
Target usage landed:
PUBLISH_INTERVAL_SECONDS=1.0 python vehicle-simulator/src/main.py
Target experiment conditions:
Condition	PUBLISH_INTERVAL_SECONDS
Baseline	5.0
Medium load	1.0
High load	0.2
6. Start the Ditto Bridge
python ditto/scripts/interim-kuksa-to-ditto-bridge.py
Expected repeating output:
[uProtocol Publisher] eventId=... vehicleId=vehicle-001 bytes=...
[uProtocol Receiver] eventId=... vehicleId=vehicle-001 battery=...
[Ditto] speed=... battery=... temp=... tireFL=... health=HEALTHY
Ditto can be validated directly via its REST API and ditto/scripts/verify-vehicle-state.py, as shown in step 7.
7. Verify the Ditto Digital Twin
With the bridge running, either inspect the twin directly:
curl -s -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001 | python3 -m json.tool
or use the automated verifier, which checks required fields, health-state consistency, and twin freshness in one command:
python ditto/scripts/verify-vehicle-state.py
Expected success:
OK: sdv:vehicle-001 is valid and fresh (<= 30.0s old)
On failure, it prints each specific problem, e.g. a missing field or a stale twin, and exits with status 1.
8. Reproduce the Low-Battery Fault
Stop the normal provider:
docker compose -f vehicle-simulator/docker-compose.yml stop provider
Run the simulator locally in fault mode while keeping Kuksa running:
INJECT_FAULT=1 DATABROKER_HOST=127.0.0.1 DATABROKER_PORT=55556 python vehicle-simulator/src/main.py
Expected simulator output: [FAULT] speed=... battery=14.4 ...
The bridge should report [Rule] battery=14.4 < 20 -> WARNING, BATTERY_LOW followed by [Ditto] ... health=WARNING. Confirm with either the curl command above or:
python ditto/scripts/verify-vehicle-state.py
The verifier does not treat an active fault as an error — a WARNING status with a populated activeFaults list is valid. It only flags missing fields, stale twins, or an internally inconsistent state (e.g. WARNING with no listed fault).
Stop the locally running fault simulator with Control + C.
9. Run the Automated Tests
python -m unittest discover -s tests -p "test_*.py" -v
This runs:
•	tests/test_uprotocol_transport.py
•	tests/test_verify_vehicle_state.py (10 mocked unit tests covering the verifier's validation logic, including the freshness formula)
•	vehicle-simulator/tests/test_kuksa_publication.py (integration test — requires the Databroker and simulator already running)
Expected result: OK.
10. Run the Publication-Rate Experiment 
Each of the three conditions (5.0, 1.0, 0.2 second intervals) will be run for a fixed number of messages, with per-event measurements written to tests/performance/results/.
11. Generate the Results Table and Chart
  --python tests/performance/process_results.py \
  --input-dir tests/performance/results \
  --output-dir docs/evidence/iteration-2/results
This produces comparison-table.md, comparison-table.csv, and publication-rate-vs-latency-throughput.png in the output directory.
To dry-run the script itself before real data exists:
python tests/performance/process_results.py --sample-data \
  --input-dir /tmp/sample_results --output-dir /tmp/sample_output
Stopping the System
docker compose -f vehicle-simulator/docker-compose.yml down
cd ../eclipse-ditto-runtime/deployment/docker
docker compose down
Troubleshooting
Port 55555 is already in use
The repository exposes Kuksa on host port 55556. Confirm vehicle-simulator/docker-compose.yml maps "55556:55555", and that anything connecting from the host (including the bridge) targets 55556.
Ditto returns 502 Bad Gateway
The Ditto cluster is still initializing. Run docker compose ps and wait until the API responds successfully.
Bridge script fails to start (import error / wrong Kuksa port)
Known issue, already flagged to the team — see the note at the top of this README. Ditto can still be validated directly via its REST API and ditto/scripts/verify-vehicle-state.py in the meantime.
Protobuf generated-code/runtime mismatch
Use the generated files committed under uprotocol/generated with the installed project dependencies rather than regenerating with an unrelated Protobuf compiler version.
Docker Hub returns 429 Too Many Requests
A registry rate limit, not a project-code failure. Reuse already-built images or wait before rebuilding.
Iteration 2 Evidence
Organized under docs/evidence/iteration-2/ — see that folder's own README.md for what belongs where and current status per section. Iteration 1 fault-lifecycle evidence remains at docs/evidence/integration-tests/ditto-kuksa/.
Known Limitations
•	The current message transport is in-process rather than distributed.
•	Only the front-left tire-pressure signal is currently read from Kuksa.
•	The health rule covers the low-battery scenario only.
•	The Spring Boot backend skeleton (backend/) runs only against mocked development adapters and is not yet connected to real Kuksa/Ditto/uProtocol/OpenSOVD components.
•	OpenSOVD integration and the final dashboard remain future work.
License and External Components
Eclipse Kuksa, Eclipse Ditto, and Eclipse uProtocol are external Eclipse Foundation projects and remain subject to their respective licenses. This repository contains the team's integration code, configuration, tests, documentation, and project-specific models.

