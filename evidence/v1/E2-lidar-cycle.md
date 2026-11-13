# E2: Deterministic vehicle-002 LiDAR fault and recovery (V1-03, edge part)

**Status:** The edge cycle was verified live on November 13, 2026 (UTC). It passed twice and gave the same distances both times. The full V1-03 run through Spring Boot, Ditto, the API and the UI is still pending, because it needs Ankit's routing and Bayan's ingress.

| Field | Recorded evidence |
|---|---|
| Task and acceptance | E2, V1-03 (edge part). Supports V1-01, V1-02 and V1-05. |
| Branch and revision | `emmanuel/feature/v1-lidar-scenarios`. The live runs used `3d54600`. The only later change is `b41e0bb`, which is test-only. |
| Spec and plan | [design](../../docs/superpowers/specs/2026-11-11-v1-lidar-scenarios-design.md), [plan](../../docs/superpowers/plans/2026-11-12-v1-lidar-scenarios.md). Contract: [v1-interface-contracts.md](../../docs/v1-interface-contracts.md) 1.0.0, sections C2, C4, C5, C8 and C9. |
| Environment | macOS arm64, Docker 29.9.2, Docker Compose 5.6.1. Stack: [docker-compose.v1.yml](../../vehicle-simulator/docker-compose.v1.yml) (project `qa-sdv-v1`) with `PUBLISH_INTERVAL_SECONDS=5`. The capture ran in `python:3.12-slim` with `mosquitto-clients`. |
| Command | `E2_CAPTURE_OUT=evidence/v1/e2-capture-20261113T045301Z.jsonl scripts/run-v1-lidar-cycle.sh` |

## Expected values (set before the run)

The provider follows a fixed ladder, [lidar_trajectory.py](../../vehicle-simulator/src/lidar_trajectory.py): `35 → 20 → 8 → 3` m, one rung per 5 s tick. Inject climbs to 3 m and holds there; clear steps back down to 35 m. When no scenario is active the distance is exactly 35.0 m. Health is decided only by the Velocitas app, using the C4 thresholds (≤10 m WARNING, ≤5 m CRITICAL). The provider never sends a health value. The provider log prints the ladder position for each tick, which lets you check the expected values against the run, for example:

```
[2026-11-13T04:53:10.837666] vehicle=vehicle-002 mode=LIDAR_OBSTRUCTION ... lidar_distance_m=20.0 lidar_step=1.0 lidar_sensor_healthy=true obstacle_warning=false autonomous_braking=false
```

Expected vehicle-002 sequence for one cycle (4 ticks held, then cleared):

```
35 HEALTHY, 20 HEALTHY, 8 WARNING, 3 CRITICAL, 3 CRITICAL, 8 WARNING, 20 HEALTHY, 35 HEALTHY
```

## Observed results

| Check | Observed |
|---|---|
| Run 1 (04:53:05–04:54:31Z) | Exit 0. `{"mockTool": true, "accepted": 36, "cycleComplete": true}`: 18 events per vehicle, all accepted. vehicle-002 distances were 35, 20, 8, 3, 3, 8, 20, 35, then 35 until the end, with health HEALTHY, HEALTHY, WARNING, CRITICAL, CRITICAL, WARNING, HEALTHY, HEALTHY. All 18 vehicle-001 events were HEALTHY at 35.0 m. Raw output: [e2-capture-20261113T045301Z.jsonl](e2-capture-20261113T045301Z.jsonl). |
| Run 2 (04:54:51–04:56:16Z) | Exit 0, 36 events accepted, `cycleComplete: true`. vehicle-002 had the same sequence `35, 20, 8, 3, 3, 8, 20, 35`. vehicle-001 was always HEALTHY. |
| Wrong vehicle | Provider-002 answered 409 `{"error": "provider serves vehicle-002, not vehicle-001"}` and logged `[Control] rejected vehicle='vehicle-001' configured=vehicle-002`. Its state did not change. |
| Interrupt | Sending SIGTERM to the script after the inject made its exit trap send a clear (`e2-cycle-clear-trap`). The context read back `"active": false`, and the capture container was removed. Ctrl+C uses the same trap. |
| Stack down | The script printed `Service mqtt is not running.` and the start command, exited 1, and sent no request. |
| Unit tests | `python -m pytest vehicle-simulator/tests -q` gave 53 passed. The full suite `python -m pytest -q -ra -m "not integration"`, after generating protobuf as CI does, gave 220 passed and 4 skipped (Compose tests, because the test container has no Compose plugin). |
| Baseline files | `git diff --stat main -- vehicle-simulator/docker-compose.yml .github` printed nothing. |

The vehicle-002 recovery is seen in the observed readings (distances back above 10 m), not taken from the provider's acknowledgement, as C4 requires. The raw capture contains one non-JSON line, `Timed out`. That is `mosquitto_sub` reporting the end of its listening window.

## Commands for Ankit (provider routes, contract C8)

Inject (provider-002, `localhost:8092`, container port 8090):

```bash
curl -X POST http://localhost:8092/api/v1/scenarios/actions -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION","actionId":"e2-cycle-inject","traceId":"e2-cycle-inject"}'
```

```json
{"vehicleId": "vehicle-002", "scenario": "LIDAR_OBSTRUCTION", "active": true, "actionId": "e2-cycle-inject", "traceId": "e2-cycle-inject", "action": "INJECT_SCENARIO"}
```

Context read: `GET http://localhost:8092/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION`

```json
{"vehicleId": "vehicle-002", "scenario": "LIDAR_OBSTRUCTION", "active": true, "actionId": "e2-cycle-inject", "traceId": "e2-cycle-inject", "action": "INJECT_SCENARIO"}
```

Clear (same body with `"action":"CLEAR_SCENARIO"`):

```json
{"vehicleId": "vehicle-002", "scenario": "LIDAR_OBSTRUCTION", "active": false, "actionId": "e2-cycle-clear", "traceId": "e2-cycle-clear", "action": "CLEAR_SCENARIO"}
```

Requests that are rejected:

| Request | Status | Body |
|---|---|---|
| `vehicleId` for another vehicle, or a padded one such as `" vehicle-002"`. POST or context GET. | 409 | `{"error": "provider serves vehicle-002, not vehicle-001"}` |
| Blank or non-string `vehicleId`, unsupported action or scenario, malformed JSON | 400 | `{"error": "..."}` |

Under C8, the backend maps a provider 4xx to `502 PROVIDER_REJECTED`. Repeated inject and clear calls are idempotent.

## Events for Bayan (from run 1)

Healthy:

```json
{"schemaVersion":"1.0.0","eventId":"vehicle-002-d2a937bece4e4feb8aaa55854d518778","vehicleId":"vehicle-002","sourceTimestamp":"2026-11-13T04:53:05.827806Z","health":"HEALTHY","faults":[],"lidar":{"distanceMeters":35.0,"sensorAvailable":true}}
```

Fault:

```json
{"schemaVersion":"1.0.0","eventId":"vehicle-002-a68ad740f04c4f4fbb9f0d2a3c3fb632","vehicleId":"vehicle-002","sourceTimestamp":"2026-11-13T04:53:20.858717Z","health":"CRITICAL","faults":["LIDAR_OBSTRUCTION"],"lidar":{"distanceMeters":3.0,"sensorAvailable":true}}
```

Recovered:

```json
{"schemaVersion":"1.0.0","eventId":"vehicle-002-1e5ff4332c514d699dc099e3f76da0b8","vehicleId":"vehicle-002","sourceTimestamp":"2026-11-13T04:53:40.898056Z","health":"HEALTHY","faults":[],"lidar":{"distanceMeters":35.0,"sensorAvailable":true}}
```

The run also includes WARNING events (`faults: ["LIDAR_OBSTRUCTION"]`, distance 8.0) on the way to the fault and on the way back.

## Limitations

- **Not tested here:**
  - the Spring Boot control entry point, Ditto twins, the API or the UI. The full V1-03 run repeats this cycle through `POST /api/v1/diagnostics/actions`.
  - `LIDAR_SENSOR_FAILURE` and cooling. Both are still supported and covered by unit tests, but neither was run live.
- **Dev tool:** the capture oracle in `scripts/v1_dev` labels its own output `mockTool: true`. The events it checked were published by the real providers, KUKSA brokers and Velocitas apps.
- **Publisher QoS is still 0**, the same open question as in E1.
- **Timing:** each ladder step lasts one 5 s tick and the app polls every 2 s, so a short WARNING step could in principle be missed. CRITICAL is held for as long as the scenario is active, so the cycle check does not depend on catching WARNING.
