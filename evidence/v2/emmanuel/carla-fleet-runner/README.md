# CARLA fleet runner: live verification

**Owner:** Emmanuel · **Date:** 2026-11-22 (UTC) · **Provenance:** live CARLA
**Host:** macOS arm64 (MacBook Air), CARLA 0.9.15 Windows build under Wine,
client 0.9.15 in a `linux/amd64` container · **Map:** Town10HD_Opt

Code: `carla-bridge/` on `emmanuel/feature/v2-carla-fleet-runner`.

## Runs

| Run | Mode | Duration | Observations per vehicle | Missing / stale | Cleanup |
|---|---|---|---|---|---|
| live-1 | parked | 20 s | 199 / 199 / 199 | 0 / 0 | 6 owned actors, 0 errors |
| live-2 | autopilot (`DRIVE=1`) | 20 s | 199 / 199 / 199 | 0 / 0 | 6 owned actors, 0 errors |

Files for live-2: [manifest](live-2/manifest.json), [summary](live-2/summary.json),
the first 20 observations per vehicle (`vehicle-00N.sample.jsonl`) and the first
30 run-log lines. Full run output stays local (`carla-bridge/runs/`, git-ignored).

## Checks on every observation

Each vehicle's full JSONL was replayed in order through Ankit's
`scripts.v2_dev.observation_mapping.prepare_observation`, with the previous
envelope as watermark and the observation's processing time as `now`.

| Check | live-1 | live-2 |
|---|---|---|
| Accepted by `prepare_observation` | 597 / 597 | 597 / 597 |
| Simulation-time step | exactly 0.1 s | exactly 0.1 s |
| Processing − source time | −95 to −42 ms ✗ | **+13 to +36 ms** |
| Distances | all 50 m `NO_FRONT_HIT` (open road ahead) | 67–137 readings per vehicle below 50 m, nearest 14.1 m |
| Speed from velocity | 0 km/h | up to 31.1 km/h |

live-1 exposed a pacing bug: the runner slept after each tick, so simulation
time ran up to one tick ahead of the wall clock and source timestamps were
later than processing timestamps. Pacing now waits before each tick; live-2
shows the fix.

## Not covered yet

No obstruction, degradation or dropout scenario and no separate ground truth
(next task). No run longer than 20 s, no Velocitas or MQTT consumer in the
loop, and the 1.5 m mount was not checked against vehicle pitch while braking.

## Generation, streaming and clock uncertainty (2026-11-25)

Code at `916887d` on `emmanuel/feature/v2-carla-fleet-runner-v2` (rebased on `main`
after #66 merged). Two consecutive 20 s autopilot runs on Town10HD_Opt, same host
and CARLA build as above, with a fresh `carla-bridge/state/`.

| Run | Generation | Observations per vehicle | Missing / stale | Clock uncertainty | Max wall lag | Cleanup |
|---|---:|---|---|---:|---:|---|
| live-3 | 1 | 199 / 199 / 199 | 0 / 0 | 0.63 ms | 0.028 s | 6 owned, 0 errors |
| live-4 | 2 | 199 / 199 / 199 | 0 / 0 | 0.90 ms | 0.091 s | 6 owned, 0 errors |

- **Generation:** the runs claimed 1 and then 2 from the persisted state file.
- **Publisher:** for each vehicle, both runs went in order through
  `scripts.v2_dev.observation_publisher.Publisher` with one state database, so the
  session rolled over from generation 1 to 2. The KUKSA and MQTT clients were
  recording stubs, with the clock set to each line's processing time. Result:
  398/398 published per vehicle.
- **Streaming:** during live-4 a reader of `vehicle-001.jsonl` saw 10, 40, 71 and
  101 lines at 3 s intervals, before `summary.json` existed.
- **Clock uncertainty:** the value is the window in which the simulation origin and
  UTC anchor were read. It excludes the host clock's offset from true UTC.

Samples: [live-3](live-3/manifest.json), [live-4](live-4/manifest.json); first 5
observations per vehicle. Not covered: a real KUKSA or MQTT broker, Velocitas in
the loop, and runs longer than 20 s.
