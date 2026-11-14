# V1 E1 — Two-vehicle edge with v1 health events: design

Date: November 11, 2026 · Owner: Emmanuel · Branch: `emmanuel/feature/v1-two-vehicle-edge` (from `main` at `8b3143a`)

Task: **E1** in [10-detailed-task-distribution.md](../../10-detailed-task-distribution.md). Acceptance: **V1-01**; supports V1-02, V1-03, V1-05 and V1-09.
Contract: [v1-interface-contracts.md](../../v1-interface-contracts.md) 1.0.0, sections C1–C5 and C9.

## Goal

Run two isolated synthetic vehicle edges (`vehicle-001`, `vehicle-002`), each with its own provider, KUKSA broker and Velocitas app. Each app publishes contract-valid v1 health events on its own topic. The Velocitas app classifies health itself, and the existing single-vehicle baseline keeps working unchanged.

## Scope

In scope:

- A new Compose file with two edge stacks and one shared Mosquitto broker.
- A v1 event publisher in the Velocitas app, with C4 classification done in the app.
- Unit, configuration and runtime verification, plus a V1-01 evidence record.

Out of scope, each handled separately:

| Item | Where |
|---|---|
| Deterministic vehicle-002 obstruction/recovery, provider identity enforcement, scenario context route | E2, branch `emmanuel/feature/v1-lidar-scenarios` |
| Tire-pressure kPa/psi defect | Its own fix branch, e.g. `emmanuel/fix/tire-pressure-units` |
| CI workflow changes | Proposed to Ankit in the PR, not edited here |
| Changes to `vehicle-simulator/docker-compose.yml`, provider code, VSS file | None |

## Decisions

1. **E1 only on this branch.** E2 builds on it in a separate branch and PR.
2. **New Compose file**, `vehicle-simulator/docker-compose.v1.yml`. The existing `docker-compose.yml`, used by CI and `scripts/run-autonomous-mvp-demo.sh`, is untouched.
3. **Velocitas builds the v1 event (approach A).** A legacy-topic translator was rejected because the decision would still come from simulator flags. App-side poll time was rejected because the contract requires the original observation time.
4. **`sourceTimestamp` is the KUKSA broker timestamp of the LiDAR reading.** Probe result (November 11, `kuksa-databroker:0.7.0`, `kuksa_client 0.5.1`): a value written with an explicit timestamp of `2026-01-01T00:00:00Z` read back with the broker's receive time (`2026-11-11 15:36:43Z`). The broker overwrites provider timestamps. For the synthetic provider, the receive time is milliseconds after the reading is generated, because generation and write happen in the same loop iteration. So it is the observation time, not the app's poll time. A custom VSS signal carrying the provider clock is deferred to V2, where CARLA simulation time may need it.

## Architecture and data flow

```text
provider-00N ──(LiDAR distance + IsHealthy, one write per reading)──> kuksa-00N
app-00N: every poll → read both values + broker timestamps from kuksa-00N
         ├─ observation time not newer than last published, and nothing pending → publish nothing
         ├─ pending event from a failed publish → retry it unchanged
         └─ newer observation → classify (C4) → v1 event → mqtt sdv/vehicle-00N/health (QoS 1, retain=false)
         legacy event → mqtt sdv/autonomy/status (unchanged, every poll as today)
```

### Deployment: `vehicle-simulator/docker-compose.v1.yml`

| Service | Image/build | Container port | Default host port (env override) | Key environment |
|---|---|---|---|---|
| `mqtt` | `eclipse-mosquitto:2`, existing `config/mosquitto.conf` | 1883 | 18883 (`V1_MQTT_PORT`) | — |
| `kuksa-001` | `kuksa-databroker:0.7.0`, existing VSS JSON | 55555 | 55556 (`V1_KUKSA_001_PORT`) | — |
| `kuksa-002` | same | 55555 | 55557 (`V1_KUKSA_002_PORT`) | — |
| `provider-001` | build `vehicle-simulator/` | 8090 | 8091 (`V1_PROVIDER_001_PORT`) | `SIMULATED_VEHICLE_ID=vehicle-001`, `DATABROKER_HOST=kuksa-001`, `DATABROKER_PORT=55555` |
| `provider-002` | same | 8090 | 8092 (`V1_PROVIDER_002_PORT`) | `vehicle-002`, `kuksa-002` |
| `app-001` | build `velocitas-app/app/Dockerfile` | — | — | `SIMULATED_VEHICLE_ID=vehicle-001`, `DATABROKER_HOST=kuksa-001`, `SDV_VEHICLEDATABROKER_ADDRESS=grpc://kuksa-001:55555`, `SDV_MQTT_ADDRESS=mqtt://mqtt:1883` |
| `app-002` | same | — | — | `vehicle-002`, `kuksa-002` |

Identity reaches each app and provider only through its configured vehicle ID and its own broker. No VSS identity field is added. Because both files bind host port 55556 for vehicle-001's broker, the v1 file and the baseline file cannot run at the same time; this is documented in the file header and the evidence record.

### App units

| Unit | Responsibility | Depends on |
|---|---|---|
| `velocitas-app/app/src/v1_event.py` (new) | Pure functions, no SDK imports. `classify(distance, sensor_available)` follows C4. `build_v1_event(vehicle_id, observed_at, distance, sensor_available, event_id)` builds the C3 object. `topic(vehicle_id)` returns `sdv/<vehicleId>/health`. `ObservationGate` decides, per poll, whether to publish a new event, retry the pending one, or do nothing. | Standard library |
| `velocitas-app/app/src/main.py` | Reads distance, `IsHealthy` and their timestamps alongside the existing paths. Asks `ObservationGate` what to publish, publishes v1 JSON, and marks it published only after success. Keeps the legacy event and topic. Reconnects to KUKSA after a read error. | `v1_event`, Velocitas SDK, `kuksa_client` |
| `velocitas-app/app/AppManifest.json` | Adds the v1 topic pattern to pubsub `writes`. | — |

### C4 classification (implemented in `v1_event.classify`)

| Observation | health | faults |
|---|---|---|
| `sensorAvailable=false` | CRITICAL | `[LIDAR_SENSOR_FAILURE]` |
| available, distance ≤ 5.0 m | CRITICAL | `[LIDAR_OBSTRUCTION]` |
| available, 5.0 m < distance ≤ 10.0 m | WARNING | `[LIDAR_OBSTRUCTION]` |
| available, distance > 10.0 m | HEALTHY | `[]` |

There is no persistence or recovery window in V1; each new observation is classified on its own.

Production code never imports `scripts/v1_dev` (contract C9). `v1_event.py` implements topic, classification and serialization itself. Only the tests use `scripts.v1_dev.contract` as an independent check.

## Error handling

| Situation | Behaviour |
|---|---|
| A KUKSA value or timestamp is missing (startup) | Publish nothing and log it. Missing telemetry is unknown health, never HEALTHY. |
| `IsHealthy=false` | CRITICAL/`LIDAR_SENSOR_FAILURE`, with `lidar.distanceMeters: null`. Sensor failure has priority over obstruction. |
| Distance invalid while the sensor is available (negative, NaN, infinite, non-numeric, boolean) | Skip the observation and log it; never publish a contract-invalid event. |
| Observation time | The later of the distance and `IsHealthy` broker timestamps, converted to UTC ISO 8601 ending in `Z`. New only if strictly later than the last published observation. |
| MQTT publish raises or fails | Log it and keep the event pending. The next poll retries it with the same `eventId` and `sourceTimestamp`. A newer observation replaces a pending one, because ingress would reject the older one after the newer is applied anyway. |
| KUKSA read error or disconnect | Log, reconnect on the next poll, keep looping. The other vehicle is unaffected. |
| Legacy publication | Unchanged, and independent of v1 success or failure. |

Payloads are compact JSON (`separators=(",", ":")`, `allow_nan=False`), QoS 1, retain=false. `eventId` is `"<vehicleId>-" + uuid4().hex`.

## Testing and verification

TDD order: write the failing unit test, implement, then re-run.

1. **Unit tests** in `velocitas-app/app/tests/test_v1_event.py`:
   - Boundaries: 10.01 → HEALTHY, 10.0 → WARNING, 5.01 → WARNING, 5.0 → CRITICAL obstruction. Unavailable with any distance → CRITICAL sensor failure.
   - Every built event passes `scripts.v1_dev.contract.validate_event` for its own topic. A `null` distance appears only when the sensor is unavailable. Timestamps end in `Z`. Event IDs are unique.
   - `ObservationGate`: repeated identical observation → nothing; newer → new event; failed publish → retried with identical ID; newer while pending → replaces it; missing or invalid input → nothing.
2. **Configuration:** `docker compose -f vehicle-simulator/docker-compose.v1.yml config --quiet` exits 0. A test parses the file and asserts, per vehicle, that the app's vehicle ID, broker host and provider broker host match, and that no host ports collide.
3. **Runtime (live, V1-01):** start the v1 stack, then run `python3 -B -m scripts.v1_dev.mqtt capture --host 127.0.0.1 --port 18883 --timeout 60`. Pass means events from both vehicles, each on its own topic, accepted with zero errors and no duplicates.
4. **Regression:** the full `pytest -m "not integration"` suite passes, and `scripts/run-autonomous-mvp-demo.sh` passes, because the baseline uses the same app image.
5. **Evidence:** `evidence/v1/E1-two-vehicle-edge.md` records the revision, commands, observed output, the KUKSA timestamp probe and limitations. It keeps mock-tool checks separate from live checks.

## Done when

- Both edges publish contract-valid v1 events with the right vehicle IDs on their own topics, shown by the live capture.
- All unit, config and regression checks above pass on this branch.
- The evidence record exists. The PR requests Bayan's review for topics and schema and Ankit's for provider mappings.

## Risks and open items

- **Baseline image change:** `main.py` changes affect the baseline app image. This is mitigated by keeping the legacy path intact and re-running the baseline demo.
- **SDK publish result:** the Velocitas SDK's MQTT publish result may not expose broker acknowledgement. A raised exception is treated as failure; silent loss is not detectable in V1. This is recorded as a limitation.
- **Clock handling:** container clocks follow the Docker VM clock. Clock synchronization for Kanto and LAN hosts is outside E1.
- **Skill-usage record:** an entry in `evidence/v1/skill-sources.md` for V1-06 is optional and added only if the owner wants it.
