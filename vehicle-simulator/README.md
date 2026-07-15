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

Tests are **integration tests** — the Databroker and `src/main.py` must both
already be running before you run them, since the test reads whatever is
currently published rather than publishing its own data.

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
│   └── test_kuksa_publication.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Known Limitations

- Fault mode is currently a single on/off flag (`INJECT_FAULT`), not per-fault-type scenarios.
- Only one wheel's tire pressure is simulated.
