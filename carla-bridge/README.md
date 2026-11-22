# carla-bridge: CARLA fleet and front-LiDAR observations (V2)

Emmanuel's V2 source side: three CARLA vehicles with front LiDAR, extraction
per [V2-C3](../docs/v2-interface-contracts.md#v2-c3-front-lidar-extraction) and
observation envelopes per V2-C2. Health is decided downstream by Velocitas,
never here. Publication to KUKSA/MQTT is Ankit's
`scripts.v2_dev.observation_publisher`, which reads the JSONL files written here.

| File | Role | Needs CARLA |
|---|---|---|
| `src/front_lidar.py` | Raw `sensor.lidar.ray_cast` bytes → nearest front distance, availability, reason | no |
| `src/carla_observation.py` | V2-C2 envelope and compact JSON line | no |
| `src/run_manifest.py` | Session manifest: vehicle ↔ actor/sensor IDs, clock origins, settings | no |
| `src/vehicle_stream.py` | Per-vehicle sequencing, missing/stale frames, real-time pacing | no |
| `src/fleet_runner.py` | CARLA layer: spawn, LiDAR, synchronous 10 Hz loop, cleanup | yes |

## Run

Prerequisites: CARLA 0.9.15 listening on port 2000 with `Town10HD_Opt` loaded
(the [V2-C3 review](../docs/findings/2026-11-18-v2-c3-extraction-review.md)
found road false-obstacles on hilly maps), and Docker. The CARLA Python client
only exists for x86_64, so it runs in a `linux/amd64` container.

```bash
DURATION_SECONDS=30 DRIVE=1 sh carla-bridge/run-fleet.sh
```

| Variable | Default | Meaning |
|---|---|---|
| `DURATION_SECONDS` | 30 | simulated seconds to record |
| `DRIVE` | 0 | 1 = Traffic Manager autopilot, 0 = parked |
| `SPAWN_POINTS` | 1,2,3 | map spawn-point indices for vehicle-001..003 |
| `SEED` | 7 | Traffic Manager seed |
| `EXPECT_MAP` | Town10HD_Opt | refuses to run on another map |

Output goes to `carla-bridge/runs/<UTC time>/` (git-ignored):
`manifest.json`, `vehicle-00N.jsonl` (publisher input), `run-log.jsonl`
(per-frame reason codes) and `summary.json` (counts, lag, cleanup).

## Behaviour

- Synchronous mode, 0.1 s ticks, LiDAR at 10 Hz rotation: one full scan per observation.
- Sensor at the vehicle's front centre, 1.5 m up, zero rotation; attributes are pinned in `LIDAR_ATTRIBUTES` and recorded in the manifest.
- Pacing waits before each tick so simulation time never passes the wall clock; source time is always at or before processing time.
- A missing frame yields no observation (logged `NO_SENSOR_DATA`); a repeated or older frame is dropped (`STALE_FRAME`).
- Cleanup destroys only the six actors this run spawned and restores the world settings.

## Tests

```bash
python -m pytest -q carla-bridge/tests
```

43 tests, CARLA-free, including round trips through Ankit's `prepare_observation`.
Live verification: [evidence/v2/emmanuel/carla-fleet-runner](../evidence/v2/emmanuel/carla-fleet-runner/README.md).
