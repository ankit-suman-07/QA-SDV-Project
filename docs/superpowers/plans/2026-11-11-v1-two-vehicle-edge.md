# V1 E1 Two-Vehicle Edge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run two isolated provider/KUKSA/Velocitas edges whose apps publish contract-valid v1 health events on `sdv/vehicle-00N/health`, without changing the single-vehicle baseline.

**Architecture:** A new pure module, `velocitas-app/app/src/v1_event.py`, handles C4 classification, C3 event building and serialization, and a publish gate that decides new / retry / nothing per poll. `main.py` reads LiDAR values and their KUKSA broker timestamps, uses the gate and publishes through the Velocitas SDK, while keeping the legacy publication. A new `vehicle-simulator/docker-compose.v1.yml` runs both edges and a shared Mosquitto.

**Tech Stack:** Python 3 (Velocitas SDK 0.15.7, `kuksa_client` 0.5.1), pytest, Docker Compose, `kuksa-databroker:0.7.0`, `eclipse-mosquitto:2`.

**Spec:** `docs/superpowers/specs/2026-11-11-v1-two-vehicle-edge-design.md` (contract `docs/v1-interface-contracts.md` 1.0.0, C1–C5, C9)

## Global Constraints

- Topic: `sdv/<vehicleId>/health`; vehicle IDs exactly `vehicle-001`, `vehicle-002`.
- `schemaVersion` exactly `"1.0.0"`; `eventId` = `"<vehicleId>-" + uuid4().hex`.
- `sourceTimestamp`: UTC ISO 8601 ending in `Z`, taken as the **later** of the distance and `IsHealthy` KUKSA datapoint timestamps. Never the poll or publish time.
- C4: unavailable → `CRITICAL` `["LIDAR_SENSOR_FAILURE"]`, distance `null`; ≤ 5.0 m → `CRITICAL` `["LIDAR_OBSTRUCTION"]`; 5.0 m < d ≤ 10.0 m → `WARNING` `["LIDAR_OBSTRUCTION"]`; > 10.0 m → `HEALTHY` `[]`.
- Payload: compact JSON (`separators=(",", ":")`, `allow_nan=False`), retain=false, QoS 1 where the SDK allows it.
- Production code never imports `scripts/v1_dev` (C9); tests may.
- Do not modify `vehicle-simulator/docker-compose.yml`, provider code, the VSS file, CI workflows or anything under `backend/`, `ditto/`, `frontend/`, `carla-bridge/`.
- Legacy `sdv/autonomy/status` publication stays byte-for-byte compatible (same `build_status_event`, every poll).
- Host ports (env-overridable): MQTT 18883 (`V1_MQTT_PORT`), KUKSA 55556/55557 (`V1_KUKSA_001_PORT`/`V1_KUKSA_002_PORT`), providers 8091/8092 (`V1_PROVIDER_001_PORT`/`V1_PROVIDER_002_PORT`).
- Commits: no Claude attribution or `Co-Authored-By` trailer. Do not push.

## Review Focus

1. **App restart republishes the last reading.** After a restart, the app must not publish the reading it finds already in KUKSA, because ingress would reject it as out of order. Expected: the first observation after start only primes the gate, and the next strictly newer write is published. Test: `test_gate_primes_on_first_observation_without_publishing` (Task 2).
2. **Broker clock steps backwards.** An observation older than the last published one must never be published. Test: `test_gate_ignores_observation_older_than_last_published` (Task 2).
3. **Non-numeric distance types.** KUKSA could return `True`, a string or `NaN` while the sensor is available. Expected: skipped, no event. Tests: `test_build_rejects_bool_string_nan_and_negative_distance` (Task 1) and `test_gate_skips_invalid_observation_but_keeps_pending` (Task 2).
4. **Naive timestamp from a client.** A datapoint timestamp without a timezone must not be silently treated as UTC. Expected: `ValueError`, and the observation is skipped. Test: `test_format_timestamp_rejects_naive_datetime` (Task 1).
5. **MQTT or KUKSA not ready when an app starts.** The apps must recover without manual restarts. Expected: the app service restarts until the broker is reachable, and each app depends on its own KUKSA and MQTT. Test: `test_apps_restart_and_depend_on_own_broker_and_mqtt` (Task 4).

---

### Task 1: Pure v1 event functions

**Files:**
- Create: `velocitas-app/app/src/v1_event.py`
- Test: `velocitas-app/app/tests/test_v1_event.py`

**Interfaces:**
- Produces (all in `v1_event.py`; start the file with `from __future__ import annotations`; standard library only):
  - `SCHEMA_VERSION: str = "1.0.0"`, `WARNING_DISTANCE_M = 10.0`, `CRITICAL_DISTANCE_M = 5.0`
  - `topic(vehicle_id: str) -> str`
  - `classify(distance: float | None, sensor_available: bool) -> tuple[str, list[str]]`
  - `format_timestamp(value: datetime) -> str`: raises `ValueError` for a naive datetime; converts any aware datetime to UTC and returns `...Z`, keeping microseconds if present.
  - `new_event_id(vehicle_id: str) -> str`
  - `build_v1_event(vehicle_id: str, observed_at: datetime, distance: object, sensor_available: object, event_id: str) -> dict`: raises `ValueError` when `sensor_available` is not a `bool`, or when it is `True` and `distance` is not a finite, nonnegative `int`/`float` (bool excluded). When the sensor is unavailable, `lidar.distanceMeters` is `None`. Field order: schemaVersion, eventId, vehicleId, sourceTimestamp, health, faults, lidar.
  - `serialize(event: dict) -> str`

- [ ] **Step 1: Write the failing tests.** Test-file header: insert `../src` like `test_health_logic.py`, and also insert the repository root (`Path(__file__).resolve().parents[3]`) so that `from scripts.v1_dev import contract` works. Tests:

```python
@pytest.mark.parametrize("distance,expected", [
    (10.01, ("HEALTHY", [])), (10.0, ("WARNING", ["LIDAR_OBSTRUCTION"])),
    (5.01, ("WARNING", ["LIDAR_OBSTRUCTION"])), (5.0, ("CRITICAL", ["LIDAR_OBSTRUCTION"])),
    (0.0, ("CRITICAL", ["LIDAR_OBSTRUCTION"]))])
def test_classify_boundaries(distance, expected): assert classify(distance, True) == expected

def test_sensor_failure_has_priority(): assert classify(3.0, False) == ("CRITICAL", ["LIDAR_SENSOR_FAILURE"])

def test_topic(): assert topic("vehicle-002") == "sdv/vehicle-002/health"

def test_format_timestamp_converts_to_utc_z():
    t = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    assert format_timestamp(t) == "2026-01-01T00:00:00Z"

def test_format_timestamp_rejects_naive_datetime():
    with pytest.raises(ValueError): format_timestamp(datetime(2026, 1, 1))

@pytest.mark.parametrize("vehicle,distance,available", [
    ("vehicle-001", 35.0, True), ("vehicle-002", 7.5, True), ("vehicle-002", 3.0, True),
    ("vehicle-001", 12.0, False)])
def test_built_events_pass_shared_contract_oracle(vehicle, distance, available):
    event = build_v1_event(vehicle, T0, distance, available, "e-1")
    assert contract.validate_event(topic(vehicle), contract.decode_event(serialize(event)))

def test_unavailable_sensor_publishes_null_distance():
    assert build_v1_event("vehicle-001", T0, 12.0, False, "e")["lidar"] == {"distanceMeters": None, "sensorAvailable": False}

@pytest.mark.parametrize("bad", [True, "3.0", float("nan"), float("inf"), -0.1, None])
def test_build_rejects_bool_string_nan_and_negative_distance(bad):
    with pytest.raises(ValueError): build_v1_event("vehicle-001", T0, bad, True, "e")

def test_build_rejects_non_bool_sensor_flag():
    with pytest.raises(ValueError): build_v1_event("vehicle-001", T0, 3.0, 1, "e")

def test_serialize_is_compact_and_rejects_nan():
    assert " " not in serialize({"a": 1, "b": [1, 2]})
    with pytest.raises(ValueError): serialize({"a": float("nan")})

def test_event_ids_unique_and_prefixed():
    ids = {new_event_id("vehicle-001") for _ in range(100)}
    assert len(ids) == 100 and all(i.startswith("vehicle-001-") for i in ids)
```

`T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)`.

- [ ] **Step 2: Run and verify the tests fail.** Run: `python -m pytest velocitas-app/app/tests/test_v1_event.py -q`. Expected: collection error `ModuleNotFoundError: No module named 'v1_event'`.
- [ ] **Step 3: Implement the functions in `v1_event.py`** with the signatures above.
- [ ] **Step 4: Run and verify the tests pass.** Run the same command. Expected: all pass. Then run `python -m pytest -q -m "not integration"` (after the CI protobuf generation step from `.github/workflows/ci.yml`). Expected: no new failures.
- [ ] **Step 5: Commit.** `git add velocitas-app/app/src/v1_event.py velocitas-app/app/tests/test_v1_event.py && git commit -m "feat(velocitas): add v1 health event classification and serialization"`

### Task 2: Observation gate

**Files:**
- Modify: `velocitas-app/app/src/v1_event.py`
- Test: `velocitas-app/app/tests/test_v1_gate.py`

**Interfaces:**
- Consumes: `build_v1_event`, `new_event_id`, `format_timestamp` (Task 1).
- Produces:
  - `@dataclass(frozen=True) class Observation: distance: object; sensor_available: object; observed_at: datetime | None`
  - `observation_from_datapoints(distance_dp, health_dp) -> Observation`: duck-typed objects with `.value` and `.timestamp`. Either argument may be `None`. `observed_at` = the later of the two non-`None` timestamps, or `None` if either is missing.
  - `class ObservationGate(vehicle_id: str, id_factory: Callable[[str], str] = new_event_id)`
    - `next_event(observation: Observation) -> dict | None`: returns the event to publish now: either a new event for a strictly newer valid observation, or the unchanged pending event. Returns `None` otherwise.
    - `mark_published(event: dict) -> None`: records the event's observation time as published and clears it if it is the pending event.
  - Rules: the **first** valid observation seen only primes the gate (it returns `None` and records that time as the last-seen time). An invalid observation (missing time, or `build_v1_event` raising `ValueError`) is never published but does not drop a pending event. A newer valid observation replaces a pending one.

- [ ] **Step 1: Write the failing tests** (with a `FakeDp(value, timestamp)` helper and `ids = iter(["id-1", "id-2", "id-3"])` passed as `id_factory=lambda v: next(ids)`):
  - `test_observation_time_is_later_of_two_timestamps`: distance at T0+1 s, health at T0+2 s → `observed_at == T0+2 s`; with either datapoint `None` → `observed_at is None`.
  - `test_gate_primes_on_first_observation_without_publishing`: the first `next_event(obs@T0)` is `None`; then `next_event(obs@T0+1)` returns an event with `eventId == "id-1"` and `sourceTimestamp == "2026-01-01T00:00:01Z"`.
  - `test_gate_repeated_observation_returns_nothing_after_publish`: prime, get the event @T1, `mark_published(it)`, then `next_event(obs@T1)` is `None`.
  - `test_gate_retries_pending_event_unchanged`: prime, get the event @T1 and don't mark it; `next_event(obs@T1)` returns an equal dict with the same `eventId`.
  - `test_gate_newer_observation_replaces_pending`: prime, event @T1 unpublished, `next_event(obs@T2)` has `eventId == "id-2"` and the T2 timestamp.
  - `test_gate_ignores_observation_older_than_last_published`: prime @T0, publish @T2, `next_event(obs@T1)` is `None`.
  - `test_gate_skips_invalid_observation_but_keeps_pending`: prime, event @T1 pending; `next_event(Observation(True, True, T2))` returns the T1 pending event; `next_event(Observation(5.0, True, None))` also returns it.
- [ ] **Step 2: Run and verify the tests fail.** Run: `python -m pytest velocitas-app/app/tests/test_v1_gate.py -q`. Expected: `ImportError` for `Observation`.
- [ ] **Step 3: Implement** `Observation`, `observation_from_datapoints` and `ObservationGate` in `v1_event.py`.
- [ ] **Step 4: Run and verify both test files pass.** Run: `python -m pytest velocitas-app/app/tests -q`. Expected: all pass, including the existing `test_health_logic.py` and `test_kanto_deployment.py`.
- [ ] **Step 5: Commit.** `git commit -m "feat(velocitas): gate v1 publications on new KUKSA observations"` (add both files).

### Task 3: Wire v1 publishing into the app

**Files:**
- Modify: `velocitas-app/app/src/main.py`
- Modify: `velocitas-app/app/AppManifest.json` (pubsub `writes`: add `"sdv/+/health"` next to `"sdv/autonomy/status"`)
- Test: `velocitas-app/app/tests/test_kanto_deployment.py` (add a manifest assertion)

**Interfaces:**
- Consumes: `topic`, `serialize`, `observation_from_datapoints`, `ObservationGate` (Tasks 1–2).

- [ ] **Step 1: Write the failing test.** `test_manifest_declares_v1_and_legacy_topics`: load `AppManifest.json`, find the `pubsub` interface, and assert `"sdv/autonomy/status"` and `"sdv/+/health"` are both in `config.writes`.
- [ ] **Step 2: Run and verify it fails.** Run: `python -m pytest velocitas-app/app/tests/test_kanto_deployment.py -q`. Expected: one failure, with `sdv/+/health` missing.
- [ ] **Step 3: Check the SDK's publish options in the built image.** Run: `docker compose -f vehicle-simulator/docker-compose.yml build autonomous-health-app && docker run --rm --entrypoint python3 qa-sdv-autonomous-health-app:local -c "import inspect, velocitas_sdk.vehicle_app as v; print(inspect.signature(v.VehicleApp.publish_event))"`. Record the printed signature for the evidence (Task 5). If it has no QoS parameter, publish with the SDK anyway and record "publisher QoS is the SDK default" as a limitation. Do not bypass the SDK.
- [ ] **Step 4: Change `main.py`** and update the manifest:
  - Read with `get_current_values` and keep the `Datapoint` objects for `LIDAR_DISTANCE_PATH` and `LIDAR_HEALTH_PATH`. `read_signals` returns `(values_by_path, datapoints_by_path)`.
  - Create `self._gate = ObservationGate(VEHICLE_ID)` and `self._v1_topic = topic(VEHICLE_ID)` in `__init__`.
  - After the unchanged legacy publish, call `publish_v1(datapoints)`: build the observation, get `event = self._gate.next_event(...)`, and if there is one, `await self.publish_event(self._v1_topic, serialize(event))` then `self._gate.mark_published(event)`. Log and swallow publish exceptions, so the event stays pending for retry.
  - Run the v1 path inside its own `try`, so a v1 error never blocks the legacy publication and vice versa.
  - After a KUKSA read exception, set a flag and call `self._kuksa_client.connect()` (in `asyncio.to_thread`) at the start of the next poll; log failures.
  - Log each v1 publication with topic, eventId, health and sourceTimestamp at INFO.
- [ ] **Step 5: Run the tests and verify they pass.** Run: `python -m pytest velocitas-app/app/tests -q`. Expected: all pass.
- [ ] **Step 6: Run the baseline regression.** Start Docker, then run: `SIMULATED_VEHICLE_ID=vehicle-001 bash scripts/run-autonomous-mvp-demo.sh`. Expected: the script's success message, with MQTT showing `HEALTHY` → `EMERGENCY_BRAKING` → `HEALTHY` on `sdv/autonomy/status`. Save the console output to the scratchpad for Task 5.
- [ ] **Step 7: Commit.** `git commit -m "feat(velocitas): publish v1 health events alongside legacy status"` (add `main.py`, `AppManifest.json` and the test).

### Task 4: Two-edge Compose deployment

**Files:**
- Create: `vehicle-simulator/docker-compose.v1.yml`
- Test: `tests/test_v1_edge_compose.py`

**Interfaces:**
- Consumes: the app image from Task 3 (build context `../velocitas-app`, dockerfile `app/Dockerfile`), and the provider build `.`.
- Produces: services `mqtt`, `kuksa-001`, `kuksa-002`, `provider-001`, `provider-002`, `app-001`, `app-002`, with the exact ports and environment in the spec's deployment table. Each `app-00N` has `depends_on: [kuksa-00N, mqtt, provider-00N]` and `restart: unless-stopped`. Providers keep `PUBLISH_INTERVAL_SECONDS` defaulting to `"5.0"` and `INJECT_FAULT` `"0"`. The file header comment says it cannot run alongside `docker-compose.yml`, because both use host port 55556.

- [ ] **Step 1: Write the failing tests.** In `tests/test_v1_edge_compose.py`, load `docker compose -f vehicle-simulator/docker-compose.v1.yml config --format json` through `subprocess`, and `pytest.skip` when `docker` isn't on `PATH`. Tests:
  - `test_each_vehicle_uses_only_its_own_broker`: for N in 001/002, `app-N` and `provider-N` have `SIMULATED_VEHICLE_ID == "vehicle-N"` and `DATABROKER_HOST == "kuksa-N"`, and `app-N` has `SDV_VEHICLEDATABROKER_ADDRESS == "grpc://kuksa-N:55555"` and `SDV_MQTT_ADDRESS == "mqtt://mqtt:1883"`.
  - `test_default_host_ports_match_contract_and_do_not_collide`: published host ports are exactly {18883, 55556, 55557, 8091, 8092}, with no duplicates.
  - `test_apps_restart_and_depend_on_own_broker_and_mqtt`: each app has `restart == "unless-stopped"` and `depends_on` containing `kuksa-N` and `mqtt`, and not the other vehicle's broker.
  (That the baseline file is unchanged is checked in Task 5 with `git diff --stat main -- vehicle-simulator/docker-compose.yml`, not as a test, because CI's shallow checkout has no `main` ref.)
- [ ] **Step 2: Run and verify they fail.** Run: `python -m pytest tests/test_v1_edge_compose.py -q`. Expected: failures because the file doesn't exist (`docker compose` returns non-zero).
- [ ] **Step 3: Write `docker-compose.v1.yml`.**
- [ ] **Step 4: Run and verify they pass.** Run the same command, plus `docker compose -f vehicle-simulator/docker-compose.v1.yml config --quiet`. Expected: tests pass, and the config command exits 0 with no output.
- [ ] **Step 5: Commit.** `git commit -m "feat(simulator): add two-vehicle V1 edge Compose deployment"` (add both files).

### Task 5: Live capture, regression and evidence

**Files:**
- Create: `evidence/v1/E1-two-vehicle-edge.md`
- Create: `evidence/v1/e1-capture-<UTC timestamp>.jsonl` (raw capture output)
- Modify: `evidence/README.md` (V1-01 row: status and links)

- [ ] **Step 1: Run the live check.** Run: `docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build`, wait until both apps log a v1 publication, then run `python3 -B -m scripts.v1_dev.mqtt capture --host 127.0.0.1 --port 18883 --timeout 60 | tee evidence/v1/e1-capture-<ts>.jsonl`. Expected: exit 0, accepted events from both `vehicle-001` and `vehicle-002`, each on its own topic, with no error lines. If it fails, use superpowers:systematic-debugging before changing code.
- [ ] **Step 2: Check isolation.** Run `docker compose -f vehicle-simulator/docker-compose.v1.yml stop provider-002`, wait 20 s, and capture again for 20 s. Expected: vehicle-001 events continue and vehicle-002 publishes nothing new. Then start `provider-002` again and confirm vehicle-002 events resume. Record the timestamps.
- [ ] **Step 3: Tear down and run the full regression.** Run `docker compose -f vehicle-simulator/docker-compose.v1.yml down --volumes`. Confirm `git diff --stat main -- vehicle-simulator/docker-compose.yml vehicle-simulator/src vehicle-simulator/config .github` prints nothing. Then run the full `python -m pytest -q -ra -m "not integration"` (after the CI protobuf step). Expected: all pass. Cite the Task 3 baseline-demo output.
- [ ] **Step 4: Write `E1-two-vehicle-edge.md`.** Include:
  - the revision
  - the environment (Docker version, image tags)
  - the exact commands
  - observed results, with each check labelled live or mock-tool
  - the KUKSA timestamp probe result from the spec
  - the SDK publish signature from Task 3 and any QoS limitation
  - the isolation timeline
  - limitations: QoS, clock handling, E2 not included, tire-pressure defect deferred to `emmanuel/fix/tire-pressure-units`

  Then set the V1-01 row in `evidence/README.md` to "Edge publication verified live (E1); twin/API integration pending", with links.
- [ ] **Step 5: Commit.** `git commit -m "docs(evidence): record V1-01 two-vehicle edge verification"` (add the evidence files and README).
