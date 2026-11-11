# E1 — Two-vehicle edge publication (V1-01)

**Status:** Edge publication verified live on November 11, 2026. Twin, API and dashboard integration (V1-02 to V1-04, V1-08) are pending and outside E1.

| Field | Recorded evidence |
|---|---|
| Task / acceptance | E1 · V1-01 (supports V1-02, V1-03, V1-05, V1-09) |
| Branch / revision | `emmanuel/feature/v1-two-vehicle-edge`. Live run at `a0b8e05`; app and Compose code unchanged since (`430d914` changes only test skipping). |
| Spec and plan | [design](../../docs/superpowers/specs/2026-11-11-v1-two-vehicle-edge-design.md), [plan](../../docs/superpowers/plans/2026-11-11-v1-two-vehicle-edge.md). Contract: [v1-interface-contracts.md](../../docs/v1-interface-contracts.md) 1.0.0 (C1–C5, C9). |
| Environment | macOS arm64 host, Docker 29.9.2, Docker Compose 5.6.1. Images: `kuksa-databroker:0.7.0`, `eclipse-mosquitto:2`, local provider and Velocitas builds (app image Python 3.10.12, `velocitas-sdk` 0.15.7, `kuksa_client` 0.5.1). Test runner: Python 3.12 container. |
| Deployment | [docker-compose.v1.yml](../../vehicle-simulator/docker-compose.v1.yml), Compose project `qa-sdv-v1`: `provider-001/002` (8091/8092), `kuksa-001/002` (55556/55557), `app-001/002`, shared `mqtt` (18883). |

## What was checked

| Check | Kind | Command | Observed result |
|---|---|---|---|
| v1 event and gate unit tests | Unit | `python -m pytest velocitas-app/app/tests -q` | 42 passed: C4 boundaries 10.01/10.0/5.01/5.0 m, sensor-failure priority, every built event accepted by `scripts.v1_dev.contract.validate_event`, `null` distance for a failed sensor, invalid distance types rejected, naive timestamps rejected, gate priming/retry/replacement/ordering. |
| Compose configuration | Static | `python -m pytest tests/test_v1_edge_compose.py -q` | 4 passed on the host: each vehicle uses only its own broker, default host ports {18883, 55556, 55557, 8091, 8092} with no collisions, apps restart and depend on their own broker and MQTT, project name `qa-sdv-v1`. These skip where the Compose v2 plugin is missing. |
| Two-vehicle live publication | **Live** | `docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build`, then `python3 -B -m scripts.v1_dev.mqtt capture --host <host> --port 18883 --timeout 60` (run from a `python:3.12-slim` + `mosquitto-clients` container) | Exit 0. 24 events accepted by the capture validator, 12 on `sdv/vehicle-001/health` and 12 on `sdv/vehicle-002/health`. All event IDs unique, none rejected. Raw output: [e1-capture-20261111T194542Z.jsonl](e1-capture-20261111T194542Z.jsonl). `cycleComplete: false` is expected: no fault was injected (E2). |
| Isolation | **Live** | `docker compose ... stop provider-002`, capture 20 s; `start provider-002`, capture 20 s | 19:47:04–19:47:24Z with provider-002 stopped: 4 vehicle-001 events, 0 vehicle-002 events. 19:47:29–19:47:49Z after restart: 4 events from each vehicle. app-002 logged no errors. |
| Baseline regression | **Live** | `SIMULATED_VEHICLE_ID=vehicle-001 bash scripts/run-autonomous-mvp-demo.sh` | "MVP demonstration completed successfully". `sdv/autonomy/status` showed HEALTHY (19:43:35Z) → EMERGENCY_BRAKING (19:44:16Z) → HEALTHY (19:44:32Z). The same app also published v1 events on `sdv/vehicle-001/health` during the demo. |
| Full Python suite | Unit/mock | `python -m pytest -q -ra -m "not integration"` | 192 passed, 4 skipped (compose plugin absent in the test container), 9 deselected integration tests. |
| Baseline files unchanged | Static | `git diff --stat main -- vehicle-simulator/docker-compose.yml vehicle-simulator/src vehicle-simulator/config .github` | No output. |

The capture validator under `scripts/v1_dev` labels its own output `"mockTool": true` because it is a development tool. The events it validated were published by the real providers, KUKSA brokers and Velocitas apps above.

## Sample event (from the capture)

```json
{"schemaVersion":"1.0.0","eventId":"vehicle-002-0f69d34b1cdb43a088ca00d78a2d55f5","vehicleId":"vehicle-002","sourceTimestamp":"2026-11-11T19:45:44.462377Z","health":"HEALTHY","faults":[],"lidar":{"distanceMeters":35.36275863647461,"sensorAvailable":true}}
```

## Source timestamp finding

KUKSA Databroker 0.7.0 overwrites provider-supplied timestamps. A value written with `2026-01-01T00:00:00Z` read back with the broker's receive time. `sourceTimestamp` is therefore the broker timestamp of the LiDAR reading (the later of the distance and `IsHealthy` datapoints). The synthetic provider writes both in the same call right after generating them, so this is the observation time, not the app's poll or publish time. When a provider stops, the timestamp stops advancing and the app publishes nothing new, which the isolation run confirms.

## Limitations

- **Publisher QoS:** the Velocitas SDK's `publish_event(topic, data)` calls paho `publish` without a QoS argument, so events leave the app at QoS 0 (retain false). Contract C3 asks for QoS 1. A failed publish (non-zero result code or exception) keeps the event pending and retries it with the same `eventId`.
- **Restart behaviour:** after an app restart, the first reading found in KUKSA only primes the app, and the next new reading is published. This avoids re-sending a reading that ingress has already applied, but delays the first event by up to one provider interval (5 s).
- **Not in E1:**
  - deterministic vehicle-002 obstruction/recovery and provider identity enforcement (E2)
  - the tire-pressure kPa/psi defect (separate fix branch)
  - CI changes (to propose to Ankit)
  - live Ditto/backend integration
- **Both files can't run together:** the baseline and v1 Compose files both bind host port 55556.
- **Host note:** `run-autonomous-mvp-demo.sh` requires a `python` command. This host has only `python3`, so the demo ran with a virtualenv on `PATH`.
