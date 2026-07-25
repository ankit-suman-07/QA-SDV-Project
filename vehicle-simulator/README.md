# Vehicle Simulator (Eclipse Kuksa)

Simulates real-time vehicle sensor data and publishes it to the Eclipse Kuksa Databroker,
including a fault injection mode for testing downstream diagnostics.

## Signals Published

| Signal | VSS Path |
|---|---|
| Speed | `Vehicle.Speed` |
| Battery State of Charge | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` |
| Engine Coolant Temperature | `Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature` |
| Tire Pressure (front left) | `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` |

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `INJECT_FAULT` | `0` | Set to `1` to enable fault injection mode |
| `PUBLISH_INTERVAL_SECONDS` | `5.0` | How often (in seconds) signals are published. Must be a positive number; invalid values (non-numeric, zero, negative) are rejected at startup. |

## Prerequisites

- Docker Desktop
- Python 3.10+
- (Windows) PowerShell or Git Bash

## Option A: Run everything with Docker Compose (recommended)

```bash
cd vehicle-simulator
docker-compose up --build
```

This starts both the Kuksa Databroker and the simulator provider together.
Databroker is exposed on `localhost:55555`.

To run in fault injection mode, edit `INJECT_FAULT=1` under the `provider`
service's `environment:` block in `docker-compose.yml`, then rerun.

## Option B: Run manually (for local development/debugging)

**1. Start the Databroker:**
```bash
docker run -it --rm -p 55555:55555 ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0 --insecure
```

**2. Set up the Python environment (first time only):**
```bash
cd vehicle-simulator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Run the simulator:**
```bash
venv\Scripts\activate
python src/main.py
```

**4. Run in fault injection mode:**
```powershell
$env:INJECT_FAULT = "1"
python src/main.py
```
```bash
# Git Bash / cmd equivalent
set INJECT_FAULT=1
python src/main.py
```

## Running at Different Publish Rates (Experiments)

The simulator supports configurable publish rates for throughput/latency experiments.
Tested rates: `5.0`, `1.0`, and `0.2` seconds.

**Manual run:**
```powershell
$env:PUBLISH_INTERVAL_SECONDS = "0.2"
python src/main.py
```

**Via Docker Compose:** edit `PUBLISH_INTERVAL_SECONDS` under the `provider` service's
`environment:` block in `docker-compose.yml`, then:
```bash
docker-compose up --build
```

Each published line is timestamped, so log output can be used to measure the actual
inter-publish interval achieved at each configured rate:
```
[2026-07-25T09:54:10.877146] mode=FAULT interval=5.0 speed=60.0 battery=14.1 engine_temp=91.2 tire_pressure=31.8
```

## Verifying Signals Manually

With the Databroker running, use the CLI to inspect published values:
```bash
docker run -it --rm ghcr.io/eclipse-kuksa/kuksa-databroker-cli:0.7.0 --server host.docker.internal:55555
```
Then inside the CLI:
```
get Vehicle.Speed
get Vehicle.Powertrain.TractionBattery.StateOfCharge.Current
get Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature
get Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure
```

## Running Tests

Two test files exist:
- `tests/test_signal_generator.py` — pure unit tests (interval parsing, normal/fault signal
  generation). No Databroker required.
- `tests/test_kuksa_publication.py` — integration test. Requires the Databroker and
  `src/main.py` running first.

```bash
venv\Scripts\activate
pip install pytest  # if not already installed
pytest tests/
```

## Project Structure

```
vehicle-simulator/
├── src/
│   ├── main.py               # entry point / publish loop
│   ├── get_kuksa_client.py   # Databroker connection
│   └── signal_generator.py   # signal state transitions (normal + fault)
├── tests/
│   ├── test_kuksa_publication.py
│   └── test_signal_generator.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Known Limitations

- Fault mode is currently a single on/off flag (`INJECT_FAULT`), not per-fault-type scenarios.
- Only one wheel's tire pressure is simulated.

## Screenshots: Full Fault Lifecycle Walkthrough

### 01-simulator-normal-startup.png
`docker-compose up --build` output showing the Kuksa Databroker (v0.7.0)
starting cleanly (`Listening on 0.0.0.0:55555`) alongside Emmanuel's
simulator publishing normal signals — e.g. `speed=83.0 battery=82.9
engine_temp=88.9 tire_pressure=32.1`.

### 02-simulator-fault-injection.png
Simulator log after setting `INJECT_FAULT=1` and restarting. Shows the
`[FAULT]` tag active, with `battery` already at 0.0 and `tire_pressure`
draining from ~4.4 down to 0.0 over successive readings — confirms the
fault condition is real and progressive, not an instant flag flip.

### 03-bridge-fault-detected.png
`vehicle_pipeline.py` console output during the same fault window. Shows
the rule firing: `[Rule] battery=0.0 < 20 -> WARNING, BATTERY_LOW`,
followed by repeated `[Ditto] ... health=WARNING` lines confirming the
health state was written to Ditto continuously while the fault was active.

### 04-bridge-healthy-sync.png
`vehicle_pipeline.py` console output during normal (non-fault) operation.
Shows live-changing values (`speed` varies each line, `battery≈82-83`,
`temp≈89`, `tireFL=32`) with `health=HEALTHY` throughout — confirms the
bridge tracks the simulator continuously rather than reading a single
static value.

