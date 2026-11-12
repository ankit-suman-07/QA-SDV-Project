# V1 E2: deterministic vehicle-002 LiDAR obstruction and recovery

- **Date:** 2026-11-11
- **Owner:** Emmanuel
- **Branch:** `emmanuel/feature/v1-lidar-scenarios`, cut from `emmanuel/feature/v1-two-vehicle-edge` (E1). Rebase onto `main` once the E1 PR merges.
- **Acceptance:** V1-03. Supports V1-01, V1-02 and V1-05.
- **Contract:** [v1-interface-contracts.md](../../v1-interface-contracts.md) 1.0.0. Sections:
  - C2: identity
  - C4: thresholds, plus the rule that the scenario label is never used as health ground truth
  - C5: the capture oracle
  - C8: provider routes and response fields
  - C9: no production imports of `scripts/v1_dev`
- **Task text:** [10-detailed-task-distribution.md](../../10-detailed-task-distribution.md), E2.

## Goal

Make the vehicle-002 obstruction cycle repeatable. In the cycle, vehicle-002 goes HEALTHY → CRITICAL `LIDAR_OBSTRUCTION` → HEALTHY while vehicle-001 stays HEALTHY. It must run on the E1 edge stack without Spring Boot or Ditto, and give the same LiDAR values on every run.

Each provider must also reject commands and context reads for any vehicle other than its own.

## Decisions (approved during brainstorming)

| Topic | Decision |
|---|---|
| Trajectory | Fixed ladder `35 → 20 → 8 → 3` m, one rung per provider tick. Inject climbs to 3 m and holds there. Clear descends back to 35 m. |
| Idle LiDAR | Exactly 35.0 m when no LiDAR scenario is active, matching `tests/fixtures/v1/vehicle-002-recovered.json`. Other signals (speed, battery and so on) stay random. |
| Structure | Approach A: a new pure module `lidar_trajectory.py`, plus an identity check in `ScenarioController`. |
| Wrong vehicle | HTTP 409, no state change. Applies to the POST and the context GET. |

## Components

### `vehicle-simulator/src/lidar_trajectory.py` (new, pure)

- `LADDER = (35.0, 20.0, 8.0, 3.0)`. Index 0 is clear road and index 3 is the obstruction hold.
- `next_step(step: int, obstructed: bool) -> int`:
  - returns `min(step + 1, 3)` when obstructed
  - otherwise returns `max(step - 1, 0)`
- `distance(step: int) -> float` returns `LADDER[step]`.

### `vehicle-simulator/src/signal_generator.py`

- `initial_state()` adds `lidar_step: 0`. `lidar_distance_m` starts at 35.0.
- `_next_lidar_state`:
  - **No sensor failure:** `lidar_step = next_step(lidar_step, obstacle)`, `lidar_distance_m = distance(lidar_step)`, and the sensor is healthy.
  - **Sensor failure:** `lidar_distance_m = 0.0` and the sensor is unhealthy. `lidar_step` is **not** changed, so after the failure clears the distance resumes from the same rung.
- `obstacle_warning` (≤10 m or unhealthy) and `autonomous_braking` (≤5 m or unhealthy) keep their current rules, so the legacy `sdv/autonomy/status` demo is unchanged.
- `lidar_step` is internal state. `main.py` publishes only the keys in `SIGNAL_PATHS`, so it never reaches KUKSA. It is printed in the provider's log line as the expected value.

A full cycle with the default 5 s tick:

| Tick | Input | Distance (m) | v1 health from Velocitas |
|---|---|---|---|
| idle | none | 35 | HEALTHY |
| inject +1 | obstruction | 20 | HEALTHY |
| inject +2 | obstruction | 8 | WARNING |
| inject +3 and later | obstruction | 3 | CRITICAL `LIDAR_OBSTRUCTION` |
| clear +1 | none | 8 | WARNING |
| clear +2 | none | 20 | HEALTHY |
| clear +3 and later | none | 35 | HEALTHY |

Health is classified only by the Velocitas app from the observed distance (C4). The provider never sends a health value.

### `vehicle-simulator/src/scenario_controller.py`

- `ScenarioController(allowed_vehicle_id: str | None = None)`.
- `WrongVehicleError(ValueError)` (new).
- When `allowed_vehicle_id` is set:
  - `execute`, `is_active` and `get_state` raise `WrongVehicleError` for any `vehicle_id` that is a non-blank string but not exactly equal to it. The comparison happens before stripping, so a padded ID such as `" vehicle-002"` is rejected.
  - A blank or non-string ID still raises the existing plain `ValueError`.
  - A rejected call changes no state.
- When `allowed_vehicle_id` is `None`, today's behaviour stays: IDs are stripped and any vehicle is allowed. This exists only so the existing legacy tests keep passing unchanged.
- `main.create_scenario_controller()` passes `SIMULATED_VEHICLE_ID`.

### `vehicle-simulator/src/control_server.py`

- `WrongVehicleError` → `409 {"error": "provider serves <configured>, not <requested>"}`, on both `POST /api/v1/scenarios/actions` and `GET /api/v1/vehicles/{id}/scenarios/{scenario}`. It is caught before the existing `ValueError` → 400 handler.
- Each 409 is logged with the requested and configured IDs.
- These are unchanged:
  - the success response: `vehicleId`, `action`, `scenario`, `actionId`, `traceId`, `active`
  - idempotent repeats of inject and clear
  - 400 for an unsupported action, unsupported scenario or malformed body
  - cooling and `LIDAR_SENSOR_FAILURE` support

## Rerunnable cycle: `scripts/run-v1-lidar-cycle.sh` (new)

1. Check that the E1 stack (`docker-compose.v1.yml`, project `qa-sdv-v1`) is running.
2. Start `python -B -m scripts.v1_dev.mqtt capture --expect-cycle` in a throwaway `python:3.12-slim` container with `mosquitto-clients`, attached to the stack's network. Nothing needs to be installed on the host.
3. `POST` an inject of `LIDAR_OBSTRUCTION` for `vehicle-002` to provider-002 (`localhost:8092`), with fixed `actionId`/`traceId` values. Wait 4 ticks. Then send a clear and wait another 4 ticks. Tick length comes from `PUBLISH_INTERVAL_SECONDS` (default 5).
4. `POST` an inject with `vehicleId: vehicle-001` to provider-002 and require HTTP 409.
5. Exit 0 only if the capture exits 0 with `cycleComplete: true`. The oracle also fails if vehicle-001 ever leaves HEALTHY.

## Testing

All tests are written first and watched fail (TDD).

- **`vehicle-simulator/tests/test_lidar_trajectory.py`:**
  - the ladder going up and down, with its caps at 3 and 0
  - a reversal in the middle of the ramp
  - a full cycle produces exactly `35, 20, 8, 3, 3, 8, 20, 35`
- **`test_signal_generator.py`** (added to):
  - idle distance is exactly 35.0 across many ticks
  - a sensor failure publishes 0.0 and unhealthy, keeps the rung, and resumes from it
  - the warning and braking flags flip at 10 m and 5 m
- **`test_scenario_controller.py`** (added to):
  - a wrong or padded ID raises `WrongVehicleError` and changes no state
  - a blank ID still raises `ValueError`
  - the existing tests are unchanged
- **`test_control_server.py`** (added to):
  - 409 on the POST and on the context GET for the wrong vehicle
  - the success path is unchanged
- **Wiring:**
  - `main.create_scenario_controller()` rejects other vehicles
  - the cooling startup fault still works
- **Cross-check:** every ladder distance passed through E1's `v1_event.build_v1_event` gives HEALTHY, HEALTHY, WARNING and CRITICAL respectively. This is checked by a test in `velocitas-app/app/tests`. The ladder values are written out as literals there, because the Velocitas package does not import the simulator.

## Evidence and handoffs

`evidence/v1/E2-lidar-cycle.md` records:

- revision, interval and ladder (the expected values), kept separate from what was observed
- the raw capture `.jsonl`
- the provider's inject, clear, context-GET and 409 responses, as command examples for Ankit
- healthy, fault and recovered events, as examples for Bayan
- vehicle-001 staying HEALTHY

The V1-03 row in `evidence/README.md` is updated. The full run through Spring Boot, Ditto and the UI is still pending.

## Out of scope

- Spring Boot routing (Ankit A3)
- Ditto ingress (Bayan)
- CI changes
- the tire-pressure units fix (its own branch)
- MQTT QoS (decision in the E1 PR)
- time-based trajectories
- V2 recovery windows

## Risks

- **The capture may miss a short state.** Each rung lasts one tick and the Velocitas app polls every 2 s. The oracle only needs HEALTHY → CRITICAL → HEALTHY, and CRITICAL is held for as long as the scenario is active, so a missed WARNING is harmless.
- **The oracle needs a HEALTHY vehicle-002 event before the fault.** A newly started app also skips its first reading (E1 behaviour). So after starting the capture, the script waits 2 ticks plus 2 s before injecting, which lets the capture record at least one HEALTHY vehicle-002 event.
