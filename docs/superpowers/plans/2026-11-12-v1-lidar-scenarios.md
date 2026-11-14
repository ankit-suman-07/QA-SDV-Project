# V1 E2 Deterministic LiDAR Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the vehicle-002 LiDAR obstruction cycle repeatable on the E1 edge stack, and make each provider reject requests for any vehicle other than its own.

**Architecture:**
- A new pure `lidar_trajectory` module holds a fixed distance ladder. `signal_generator` advances along it one rung per tick.
- `ScenarioController` gets an optional allowed vehicle ID, and `main.py` always sets it. The control server turns a mismatch into HTTP 409.
- A POSIX shell script drives one inject/clear cycle against the running E1 stack and passes or fails it with the team's capture oracle.

**Tech Stack:**
- Python 3.10+ (provider image) with pytest.
- POSIX `sh`, `curl` and Docker Compose for the cycle script.
- The capture oracle `scripts/v1_dev/mqtt.py` (dev tool only).

**Spec:** [docs/superpowers/specs/2026-11-11-v1-lidar-scenarios-design.md](../specs/2026-11-11-v1-lidar-scenarios-design.md) (`2df2826`)

## Global Constraints

- The ladder is exactly `(35.0, 20.0, 8.0, 3.0)`. Idle LiDAR distance is exactly `35.0`. There is one rung per provider tick.
- The provider never emits a health value. Health is decided only in Velocitas, from distance (C4: ≤10 m WARNING, ≤5 m CRITICAL).
- A wrong vehicle ID gets HTTP **409** with body `{"error": "provider serves <configured>, not <requested>"}` and changes no state. The check applies to the POST and to the context GET. The comparison is exact (no strip).
- Leave these unchanged:
  - the success body: `vehicleId`, `scenario`, `active`, `actionId`, `traceId`, `action`
  - 400 for a blank ID, an unsupported action or scenario, and a malformed body
  - cooling and `LIDAR_SENSOR_FAILURE` support
  - the ≤10 m / ≤5 m rules for `obstacle_warning` and `autonomous_braking`
- Existing tests in `vehicle-simulator/tests/` stay unmodified and keep passing.
- Production code must not import `scripts/v1_dev` (C9).
- Run tests the way E1 did: `python -m pytest ...` from the repo root, in the Python 3.12 test environment (venv or `python:3.12-slim` container with `requirements-test.txt` / `vehicle-simulator/requirements.txt`).
- Commits have no Claude attribution trailer (owner's global rule). Never push.

## Review Focus

1. **A `vehicleId` that is not a string** (number, `null`, list) → 400, never 409 or 500. Test in Task 3.
2. **A URL-encoded padded ID on the context GET** (`/api/v1/vehicles/%20vehicle-002/...`) → 409, never the real state. Test in Task 4.
3. **Inject while `LIDAR_SENSOR_FAILURE` is active.** The rung does not move during the failure. After the failure clears, the ladder climbs from where it was. Test in Task 2.
4. **The cycle script is interrupted** (Ctrl+C or a failed step) after the inject → an exit trap sends CLEAR, so vehicle-002 is not left obstructed. Checked in Task 5.
5. **The cycle script runs while the stack is down** → it fails before any injection, with a message naming the compose command. Checked in Task 5.

---

### Task 1: `lidar_trajectory` module

**Files:**
- Create: `vehicle-simulator/src/lidar_trajectory.py`
- Test: `vehicle-simulator/tests/test_lidar_trajectory.py` (use the same `sys.path` insert of `../src` as the other simulator tests)

**Interfaces:**
- Produces:
  - `LADDER: tuple[float, ...] = (35.0, 20.0, 8.0, 3.0)`
  - `HOLD_STEP: int = 3`
  - `next_step(step: int, obstructed: bool) -> int`
  - `distance(step: int) -> float`

- [ ] **Step 1: Write the failing tests**

```python
def test_ladder_values_are_fixed():
    assert LADDER == (35.0, 20.0, 8.0, 3.0)
    assert HOLD_STEP == 3

def test_obstruction_climbs_one_rung_per_tick_and_holds():
    assert [next_step(s, True) for s in (0, 1, 2, 3)] == [1, 2, 3, 3]

def test_clear_descends_one_rung_per_tick_and_stops_at_zero():
    assert [next_step(s, False) for s in (3, 2, 1, 0)] == [2, 1, 0, 0]

def test_full_cycle_distance_sequence():
    step, seen = 0, [distance(0)]
    for obstructed in [True] * 4 + [False] * 3:
        step = next_step(step, obstructed)
        seen.append(distance(step))
    assert seen == [35.0, 20.0, 8.0, 3.0, 3.0, 8.0, 20.0, 35.0]

def test_reversal_mid_climb():
    step = next_step(next_step(0, True), True)   # 8 m
    assert distance(next_step(step, False)) == 20.0
```

- [ ] **Step 2: Run, expect FAIL**

Run: `python -m pytest vehicle-simulator/tests/test_lidar_trajectory.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'lidar_trajectory'`.

- [ ] **Step 3: Implement the module.** It is pure and imports nothing. Clamp with `min`/`max` as the spec states.

- [ ] **Step 4: Run, expect PASS**

Run: the same command. Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add vehicle-simulator/src/lidar_trajectory.py vehicle-simulator/tests/test_lidar_trajectory.py
git commit -m "feat(simulator): add fixed LiDAR distance ladder"
```

### Task 2: Generator uses the ladder

**Files:**
- Modify: `vehicle-simulator/src/signal_generator.py`
  - `initial_state()` (add `"lidar_step": 0`)
  - `_next_lidar_state`
  - `next_state` (carry `lidar_step` through)
- Test: `vehicle-simulator/tests/test_signal_generator.py` (append only)

**Interfaces:**
- Consumes: `next_step`, `distance` from Task 1.
- Produces: `next_state(...)` return dict gains the `lidar_step: int` key. All other keys are unchanged.

- [ ] **Step 1: Write the failing tests** (appended)

```python
def test_idle_lidar_distance_is_exactly_35():
    state = initial_state()
    for _ in range(50):
        state = next_state(state)
        assert state["lidar_distance_m"] == 35.0
        assert state["lidar_step"] == 0

def test_obstruction_cycle_publishes_exact_distances():
    state, seen = initial_state(), []
    for obstructed in [True] * 4 + [False] * 3:
        state = next_state(state, obstacle=obstructed)
        seen.append(state["lidar_distance_m"])
    assert seen == [20.0, 8.0, 3.0, 3.0, 8.0, 20.0, 35.0]

def test_flags_follow_ladder_thresholds():
    state = initial_state()
    flags = []
    for _ in range(3):
        state = next_state(state, obstacle=True)
        flags.append((state["obstacle_warning"], state["autonomous_braking"]))
    assert flags == [(False, False), (True, False), (True, True)]

def test_sensor_failure_keeps_rung_and_resumes():
    state = next_state(next_state(initial_state(), obstacle=True), obstacle=True)  # 8 m, step 2
    failed = next_state(state, obstacle=True, lidar_failure=True)
    assert failed["lidar_distance_m"] == 0.0
    assert failed["lidar_sensor_healthy"] is False
    assert failed["lidar_step"] == 2
    assert next_state(failed, obstacle=True)["lidar_distance_m"] == 3.0

def test_inject_during_sensor_failure_climbs_after_failure_clears():   # Review Focus 3
    state = initial_state()
    for _ in range(3):
        state = next_state(state, obstacle=True, lidar_failure=True)
    assert state["lidar_step"] == 0
    assert next_state(state, obstacle=True)["lidar_distance_m"] == 20.0
```

- [ ] **Step 2: Run, expect FAIL**

Run: `python -m pytest vehicle-simulator/tests/test_signal_generator.py -q`
Expected: the new tests fail (`KeyError: 'lidar_step'` or random distances). The existing tests still pass.

- [ ] **Step 3: Implement.**
  - `_next_lidar_state` reads `state.get("lidar_step", 0)`.
  - On failure, it returns `0.0`/unhealthy with the step unchanged.
  - Otherwise it returns `distance(next_step(step, obstacle))`.
  - It returns the step as a fifth tuple element.
  - The random LiDAR branches are removed. `NORMAL_LIDAR_DISTANCE_M` stays at `35.0`, and the `NORMAL_RANGES["lidar_distance_m"]` entry stays (35 is inside it).

- [ ] **Step 4: Run, expect PASS**

Run: `python -m pytest vehicle-simulator/tests -q`
Expected: all pass. The integration-marked KUKSA tests are deselected.

- [ ] **Step 5: Commit**

```bash
git add vehicle-simulator/src/signal_generator.py vehicle-simulator/tests/test_signal_generator.py
git commit -m "feat(simulator): drive LiDAR distance from the fixed ladder"
```

### Task 3: Controller identity check

**Files:**
- Modify: `vehicle-simulator/src/scenario_controller.py`
- Test: `vehicle-simulator/tests/test_scenario_controller.py` (append only)

**Interfaces:**
- Produces:
  - `class WrongVehicleError(ValueError)`
  - `ScenarioController(allowed_vehicle_id: str | None = None)`
  - `controller.allowed_vehicle_id` (read-only property)
  - `execute`, `is_active` and `get_state` raise `WrongVehicleError` on a mismatch. Its message is exactly `provider serves <allowed>, not <requested>`.

- [ ] **Step 1: Write the failing tests** (appended; `ALLOWED = "vehicle-002"`)

```python
def test_wrong_vehicle_is_rejected_without_state_change():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(WrongVehicleError, match="provider serves vehicle-002, not vehicle-001"):
        controller.execute(vehicle_id="vehicle-001", action="INJECT_SCENARIO",
                           scenario="LIDAR_OBSTRUCTION", action_id="a", trace_id="t")
    assert controller.get_state(ALLOWED, "LIDAR_OBSTRUCTION")["actionId"] is None
    with pytest.raises(WrongVehicleError):
        controller.is_active("vehicle-001", "LIDAR_OBSTRUCTION")
    with pytest.raises(WrongVehicleError):
        controller.get_state("vehicle-001", "LIDAR_OBSTRUCTION")

def test_padded_vehicle_id_is_rejected():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(WrongVehicleError):
        controller.is_active(" vehicle-002", "LIDAR_OBSTRUCTION")

@pytest.mark.parametrize("bad", ["", "   ", None, 2, ["vehicle-002"]])   # Review Focus 1
def test_blank_or_non_string_id_is_plain_value_error(bad):
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(ValueError) as error:
        controller.is_active(bad, "LIDAR_OBSTRUCTION")
    assert not isinstance(error.value, WrongVehicleError)

def test_allowed_vehicle_executes_normally():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    state = controller.execute(vehicle_id=ALLOWED, action="INJECT_SCENARIO",
                               scenario="LIDAR_OBSTRUCTION", action_id="a", trace_id="t")
    assert state["active"] is True
```

- [ ] **Step 2: Run, expect FAIL**

Run: `python -m pytest vehicle-simulator/tests/test_scenario_controller.py -q`
Expected: `ImportError: cannot import name 'WrongVehicleError'`.

- [ ] **Step 3: Implement.**
  - `_validate_vehicle_id` keeps its blank/non-string `ValueError`.
  - When `allowed_vehicle_id` is set, it compares the **unstripped** value with `allowed_vehicle_id` and raises `WrongVehicleError` on a mismatch.
  - When it is `None`, it keeps today's strip behaviour.
  - Validation runs before the lock and before any state change.

- [ ] **Step 4: Run, expect PASS**

Run: `python -m pytest vehicle-simulator/tests -q`
Expected: all pass, including the unchanged legacy multi-vehicle test.

- [ ] **Step 5: Commit**

```bash
git add vehicle-simulator/src/scenario_controller.py vehicle-simulator/tests/test_scenario_controller.py
git commit -m "feat(simulator): reject scenario requests for another vehicle"
```

### Task 4: HTTP 409 and production wiring

**Files:**
- Modify: `vehicle-simulator/src/control_server.py` (`do_GET` context branch, `do_POST`)
- Modify: `vehicle-simulator/src/main.py` (`create_scenario_controller`)
- Test: `vehicle-simulator/tests/test_control_server.py` (append only)
- Create test: `vehicle-simulator/tests/test_provider_main.py`

**Interfaces:**
- Consumes: `WrongVehicleError` and `ScenarioController(allowed_vehicle_id=...)` from Task 3.
- Produces: 409 JSON `{"error": str(exception)}` on both routes. Each 409 prints `[Control] rejected vehicle=<requested> configured=<allowed>`.

- [ ] **Step 1: Write the failing tests.**
  - In `test_control_server.py`, add two things:
    - an `identity_server` fixture, built like the existing server fixture but with `ScenarioController(allowed_vehicle_id="vehicle-002")`, yielding its base URL
    - a helper `expect_http_error(base_url, method, path, body=None) -> tuple[int, dict]`, which sends the request with `urllib` and returns `(error.code, json.load(error))` from the `HTTPError`. It fails the test if no error is raised.

```python
def test_post_for_other_vehicle_returns_409(identity_server):
    status, body = expect_http_error(identity_server, "POST", "/api/v1/scenarios/actions",
        {"vehicleId": "vehicle-001", "action": "INJECT_SCENARIO",
         "scenario": "LIDAR_OBSTRUCTION", "actionId": "a", "traceId": "t"})
    assert status == 409
    assert body == {"error": "provider serves vehicle-002, not vehicle-001"}

def test_context_get_for_other_vehicle_returns_409(identity_server):
    status, _ = expect_http_error(identity_server, "GET",
        "/api/v1/vehicles/vehicle-001/scenarios/LIDAR_OBSTRUCTION")
    assert status == 409

def test_context_get_for_url_encoded_padded_id_returns_409(identity_server):   # Review Focus 2
    status, _ = expect_http_error(identity_server, "GET",
        "/api/v1/vehicles/%20vehicle-002/scenarios/LIDAR_OBSTRUCTION")
    assert status == 409

def test_non_string_vehicle_id_returns_400(identity_server):
    status, _ = expect_http_error(identity_server, "POST", "/api/v1/scenarios/actions",
        {"vehicleId": 2, "action": "INJECT_SCENARIO", "scenario": "LIDAR_OBSTRUCTION",
         "actionId": "a", "traceId": "t"})
    assert status == 400
```

  - `test_provider_main.py`:
    - set `SIMULATED_VEHICLE_ID=vehicle-002` and clear `INJECT_FAULT` with `monkeypatch` before `importlib.import_module("main")`
    - drop `sys.modules["main"]` first and afterwards
    - `create_scenario_controller()` rejects `vehicle-001` with `WrongVehicleError` and accepts `vehicle-002`
    - `"lidar_step" not in main.SIGNAL_PATHS`

- [ ] **Step 2: Run, expect FAIL**

Run: `python -m pytest vehicle-simulator/tests/test_control_server.py vehicle-simulator/tests/test_provider_main.py -q`
Expected: the new control-server tests get 400 instead of 409, and the main test accepts `vehicle-001`.

- [ ] **Step 3: Implement.**
  - In both handlers, catch `WrongVehicleError` before `ValueError`, print the rejection line, and write 409.
  - `create_scenario_controller()` builds `ScenarioController(allowed_vehicle_id=SIMULATED_VEHICLE_ID)`. The `INJECT_FAULT` startup path is unchanged.

- [ ] **Step 4: Run, expect PASS**

Run: `python -m pytest vehicle-simulator/tests -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add vehicle-simulator/src/control_server.py vehicle-simulator/src/main.py vehicle-simulator/tests/test_control_server.py vehicle-simulator/tests/test_provider_main.py
git commit -m "feat(simulator): return 409 for other vehicles and enforce provider identity"
```

### Task 5: Threshold cross-check and cycle script

**Files:**
- Test: `velocitas-app/app/tests/test_v1_event.py` (append)
- Create: `scripts/run-v1-lidar-cycle.sh` (executable, POSIX `sh`, `set -eu`, same `REPOSITORY_ROOT` pattern as `run-autonomous-mvp-demo.sh`)

**Interfaces:**
- Consumes:
  - `build_v1_event` from E1
  - provider HTTP on `localhost:8092`
  - the compose project `qa-sdv-v1` and its network `qa-sdv-v1_default`
  - MQTT service `mqtt:1883`

- [ ] **Step 1: Write the cross-check test.**
  - It is a characterisation test across components, so it is expected to pass at once. If it fails, the ladder and the C4 thresholds disagree and that is a real finding.
  - The ladder is written as literals because Velocitas must not import the simulator.

```python
def test_provider_ladder_maps_to_expected_health():
    ladder = {35.0: "HEALTHY", 20.0: "HEALTHY", 8.0: "WARNING", 3.0: "CRITICAL"}
    for distance, health in ladder.items():
        event = build_v1_event("vehicle-002", T0, distance, True, "id")
        assert event["health"] == health
        assert event["faults"] == ([] if health == "HEALTHY" else ["LIDAR_OBSTRUCTION"])
```

- [ ] **Step 2: Run it.**

Run: `python -m pytest velocitas-app/app/tests/test_v1_event.py -q`
Expected: all pass.

- [ ] **Step 3: Write `scripts/run-v1-lidar-cycle.sh`.**
  - `TICK=${PUBLISH_INTERVAL_SECONDS:-5}` and `PROVIDER=${PROVIDER_002_URL:-http://localhost:8092}`.
  - **Preflight (Review Focus 5):**
    - `docker compose -f vehicle-simulator/docker-compose.v1.yml ps --status running --services` must list `mqtt`, `provider-001`, `provider-002`, `app-001` and `app-002`
    - `curl -fsS $PROVIDER/health` must succeed
    - otherwise print `Start the stack first: docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build` and exit 1
  - **Capture:**
    - `docker run --rm --network qa-sdv-v1_default -v "$REPOSITORY_ROOT:/repo:ro" -w /repo python:3.12-slim sh -c 'apt-get update -qq && apt-get install -y -qq mosquitto-clients >/dev/null && python -B -m scripts.v1_dev.mqtt capture --host mqtt --port 1883 --expect-cycle --timeout <T>'`
    - run it in the background, with its output written to a temp file
    - `T = 12 * TICK + 30`
  - **Readiness** (replaces the spec's fixed "2 ticks + 2 s" wait, which can't account for the variable apt install time):
    - wait up to 120 s until the capture file has a line containing `"vehicleId": "vehicle-002"` and `"health": "HEALTHY"`
    - fail and exit 1 if it never appears
  - **Inject:**
    - POST an inject (`actionId`/`traceId` = `e2-cycle-inject`) and require HTTP 200 with `"active": true`
    - set `SCENARIO_ACTIVE=1`
    - **(Review Focus 4)** `trap` on `EXIT INT TERM` POSTs a clear (`e2-cycle-clear-trap`) while `SCENARIO_ACTIVE=1`
  - **Hold, then clear:**
    - sleep `4 * TICK`
    - GET the context and print it
    - POST a clear (`e2-cycle-clear`), require 200 and `"active": false`, then set `SCENARIO_ACTIVE=0`
    - sleep `4 * TICK`
  - **Identity check:** POST `vehicleId: vehicle-001` to provider-002 and require status `409` (from `curl -o /dev/null -w '%{http_code}'`).
  - **Result:**
    - wait for the capture container to exit
    - print its last line
    - exit 0 only if the container exited 0 and the last line has `"cycleComplete": true`
  - **Evidence copy:** if `E2_CAPTURE_OUT` is set, copy the capture output there.

- [ ] **Step 4: Static check.**

Run: `sh -n scripts/run-v1-lidar-cycle.sh && echo ok`
Expected: `ok`.

  - With the stack down, run `scripts/run-v1-lidar-cycle.sh; echo $?`. Expected: the "Start the stack first" message and `1`, with no curl POST issued.

- [ ] **Step 5: Commit**

```bash
git add velocitas-app/app/tests/test_v1_event.py scripts/run-v1-lidar-cycle.sh
git commit -m "feat(scripts): add rerunnable V1 LiDAR fault and recovery cycle"
```

### Task 6: Live cycle run and evidence

**Files:**
- Create: `evidence/v1/E2-lidar-cycle.md`
- Create: `evidence/v1/e2-capture-<UTC timestamp>.jsonl`
- Modify: `evidence/README.md` (V1-03 row)

- [ ] **Step 1: Bring up the stack from this branch.**

Run: `docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build`
Expected: 7 services running.

  - Wait at least 2 ticks before the next step.

- [ ] **Step 2: Run the cycle.**

Run: `E2_CAPTURE_OUT=evidence/v1/e2-capture-<ts>.jsonl scripts/run-v1-lidar-cycle.sh`
Expected:
  - exit 0, last line `"cycleComplete": true`
  - vehicle-002 events go HEALTHY → (WARNING) → CRITICAL `LIDAR_OBSTRUCTION` → (WARNING) → HEALTHY with distances from the ladder
  - every vehicle-001 event is HEALTHY

- [ ] **Step 3: Run it a second time.** This shows repeatability. Expected: exit 0 and the same distance sequence.

- [ ] **Step 4: Check that the interrupt trap works (Review Focus 4).**
  - Start the script, press Ctrl+C after the inject, then GET the context. Expected: `"active": false`.
  - Run `provider-002` logs. Expected: they show the 409 rejection line.

- [ ] **Step 5: Run the full suite and the baseline check.**
  - Run `python -m pytest -q -ra -m "not integration"`. Expected: all pass (compose tests may skip where the plugin is missing).
  - Run `git diff --stat main -- vehicle-simulator/docker-compose.yml .github`. Expected: no output.

- [ ] **Step 6: Write `evidence/v1/E2-lidar-cycle.md`.** Follow the layout of `E1-two-vehicle-edge.md`. It holds:
  - the revision, tick and ladder (expected values), kept separate from what was observed
  - both runs' results
  - the raw capture link
  - inject, clear, context and 409 request/response examples (**for Ankit**)
  - one healthy, one fault and one recovered event (**for Bayan**)
  - limitations: QoS 0, no Spring Boot/Ditto, the mock-tool label on the oracle

  In `evidence/README.md`, set V1-03 to "Edge cycle verified (E2); backend/Ditto/UI run pending" and link the record.

- [ ] **Step 7: Tear down and commit**

Run: `docker compose -f vehicle-simulator/docker-compose.v1.yml down --volumes`

```bash
git add evidence/v1/E2-lidar-cycle.md evidence/v1/e2-capture-*.jsonl evidence/README.md
git commit -m "docs(evidence): record V1-03 edge LiDAR fault and recovery cycle"
```
