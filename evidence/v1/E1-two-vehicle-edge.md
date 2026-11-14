# E1 — Two-vehicle edge publication (V1-01)

**Status:** Edge publication verified live on November 11, 2026. Twin, API and dashboard integration (V1-02 to V1-04, V1-08) are pending and outside E1.

| Field | Recorded evidence |
|---|---|
| Task / acceptance | E1 · V1-01 (supports V1-02, V1-03, V1-05, V1-09) |
| Branch / revision | `emmanuel/feature/v1-two-vehicle-edge`. The checks in **What was checked** ran at `a0b8e05`. After that run, app code changed twice: `1a6f50d` (KUKSA reconnect and skip-reason logging, unit-tested only) and the QoS 1 fix `a3e20c1` from `emmanuel/fix/v1-qos1-publication`, which was re-checked live (see **QoS 1 re-check**). |
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

## QoS 1 re-check (November 14, 2026, at `a3e20c1`)

PR #33's review found that events left the app at QoS 0. The merged ingress (`ditto/mqtt_subscriber.py`) rejects those with `INVALID_MQTT_DELIVERY`, so no twin was ever updated. The fix publishes v1 events through paho on the SDK's own publisher connection with `qos=1, retain=False`. An event leaves the pending state only after the broker acknowledges it (PUBACK).

| Check | Kind | Observed result |
|---|---|---|
| Unit tests | Unit | `velocitas-app/app/tests/test_v1_publisher.py`: 10 passed. They check `qos=1` and `retain=False`, that a missing acknowledgement, error return code or exception counts as a failure, that a failed delivery keeps the same `eventId` and `sourceTimestamp`, and that a missing SDK publisher gives a clear error. In the real app image (velocitas-sdk 0.15.7) the SDK pin test also passes: 11 passed. |
| Transport to ingress | Integration, real Mosquitto | `test_v1_publisher_integration.py`: 2 passed. A v1 event published through the adapter reached the real `ditto.mqtt_subscriber.Subscriber` at QoS 1, retain false, and was processed. The QoS 0 negative control was delivered at QoS 0 and never processed. |
| Both edges into the ingress | **Live** | Full stack built from `a3e20c1`, with the real `Subscriber` and a recording ingress in place of the Ditto writer, for 35 s: 15 deliveries, all `(qos 1, retain false)`. 15 processed (8 vehicle-001, 7 vehicle-002), 15 unique IDs, no rejections. Over the same window, `mosquitto_sub -q 1 -F '%q %r %t %p'` recorded 16 messages, all QoS 1, retain 0: [e1-qos-capture-20261114T0308Z.txt](e1-qos-capture-20261114T0308Z.txt). |
| Broker outage | **Live** | MQTT was stopped for 12 s, then started. app-002 logged `publish not queued (MQTT_ERR_NO_CONN)` and `will retry eventId=<same id>` on each poll while the reading stayed the same. A newer reading replaced the pending event, as designed. After the broker came back, the newest pending event was published (`sourceTimestamp` 03:10:28Z) and publishing continued. No tracebacks; vehicle-001 also resumed. |

The isolation run and the baseline demo in **What was checked** were not repeated after these changes, and their raw logs are not attached. Restart and source-silence checks against the backend's availability view (A2) belong to the joint V1-03 run.

## Sample event (from the capture)

```json
{"schemaVersion":"1.0.0","eventId":"vehicle-002-0f69d34b1cdb43a088ca00d78a2d55f5","vehicleId":"vehicle-002","sourceTimestamp":"2026-11-11T19:45:44.462377Z","health":"HEALTHY","faults":[],"lidar":{"distanceMeters":35.36275863647461,"sensorAvailable":true}}
```

## Source timestamp finding

KUKSA Databroker 0.7.0 overwrites provider-supplied timestamps. A value written with `2026-01-01T00:00:00Z` read back with the broker's receive time. `sourceTimestamp` is therefore the broker timestamp of the LiDAR reading (the later of the distance and `IsHealthy` datapoints). The synthetic provider writes both in the same call right after generating them, so this is the observation time, not the app's poll or publish time. When a provider stops, the timestamp stops advancing and the app publishes nothing new, which the isolation run confirms.

## Limitations

- **Publisher QoS:** fixed in `a3e20c1`. v1 events are published at QoS 1, retain false (see **QoS 1 re-check**). The fix depends on the SDK's private `MqttClient._pub_client`, which is pinned by a test against velocitas-sdk 0.15.7. The legacy `sdv/autonomy/status` topic is still published at QoS 0, unchanged. The 24-event capture above recorded no QoS metadata.
- **Restart behaviour:** after an app restart, the first reading found in KUKSA only primes the app, and the next new reading is published. This avoids re-sending a reading that ingress has already applied, but delays the first event. The delay is typically one provider interval (5 s) plus up to one app poll (2 s), plus startup and connection time. It has not been measured end to end and is not a guaranteed bound. While waiting, the vehicle can correctly show as stale or unavailable (C5).
- **Not in E1:**
  - deterministic vehicle-002 obstruction/recovery and provider identity enforcement (E2)
  - the tire-pressure kPa/psi defect (separate fix branch)
  - CI changes (to propose to Ankit)
  - live Ditto/backend integration
- **Both files can't run together:** the baseline and v1 Compose files both bind host port 55556.
- **Host note:** `run-autonomous-mvp-demo.sh` requires a `python` command. This host has only `python3`, so the demo ran with a virtualenv on `PATH`.
