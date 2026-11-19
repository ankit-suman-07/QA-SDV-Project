# V2-C3 front-LiDAR extraction: owner review

**Reviewer:** Emmanuel (extraction owner) · **Date:** 2026-11-18 ·
**Contract:** `docs/v2-interface-contracts.md` 2.0.0-prep.1 at `2680bf6` ·
**For:** Ankit (contract owner), Bayan (health consumer)

This is a review of the proposed extraction defaults, not approval of the whole
contract. Live checks used the local CARLA install (Windows build under Wine on
macOS arm64) with a review-only probe:
[`evidence/v2/c3-extraction-review/c3_region_probe.py`](../../evidence/v2/c3-extraction-review/c3_region_probe.py).
The probe uses `sensor.lidar.ray_cast_semantic` only to label which surface each
point hit; production extraction stays on `sensor.lidar.ray_cast` as the contract
requires.

## Method

For every spawn point on a map: spawn one car, mount a LiDAR at the front centre
(x = bounding-box half-length, z = 1.5 m, zero rotation), 32 channels, range 50 m,
10 Hz rotation, synchronous 0.1 s ticks. Take one full scan after 5 ticks, apply
the V2-C3 region (`0 < x <= 50`, `|y| <= 1.5`, `-1.0 <= z <= 1.0`) and record
the class of the nearest selected point. A road, road-line, sidewalk, ground or
terrain hit is a false obstacle. Static cars only; no other traffic spawned.

## Results

| Map | Spawn points | Nothing ahead (NO_FRONT_HIT) | Real object | False obstacle (road) | False obstacle ≤ 10 m |
|---|---:|---:|---:|---:|---:|
| Town10HD_Opt | 155 | 130 | 25 | **0** | **0** |
| Town03_Opt (hilly), z ≥ −1.0 | 265 | 218 | 33 | **14** (5.3%) | **6** |
| Town03_Opt, z ≥ −0.5 (comparison) | 265 | 225 | 33 | 7 | 2 |

On Town03, uphill spawns put the road inside the region at the distance the
geometry predicts: at a 3.3° grade the road reached z = −0.96 m at 7.9 m
(predicted 0.5 m / tan 3.3° ≈ 8.7 m). Two level spawns also hit the road at
2.9 m and 3.8 m where the road ahead rises. Each of the six hits within 10 m
would be classified WARNING or CRITICAL with no obstacle present.

## Findings

1. **Road surface becomes an obstacle on slopes (Important).** The region's lower
   bound sits 0.5 m above a flat road. Any rising road ahead enters it. Raising the
   bound to −0.5 m halves the false hits but does not remove them, so no fixed
   z band fixes hills. **Proposal:** keep the band, pin acceptance and replay runs
   to `Town10HD_Opt` (0/155 false hits), and require scenario spawn points to pass
   this probe. Record "flat-road assumption" as a known limitation in V2-C3.
2. **`reason` has no field (Important).** V2-C3 names `INVALID_FRAME` and
   `NO_FRONT_HIT`, but the V2-C2 observation schema has no reason field and the
   `extract` fixtures expect only `[distance, available]`. Decide whether the
   reason travels in the observation (new optional field) or only in logs; until
   then consumers can't tell a censored 50 m from a measured 50 m.
3. **Sensor attributes are unpinned (Minor).** Channels, `points_per_second`,
   `upper_fov` and `lower_fov` change what is detectable at range. Proposal: pin
   them in the run manifest (probe used 32 / 320000 / +10° / −30°) and state that
   `lower_fov` must reach the road within range, otherwise an open-road frame can
   legitimately be empty and would be misreported as `INVALID_FRAME`.
4. **Full 10 Hz scan needs the tick pinned (Minor).** A complete scan per
   observation needs `rotation_frequency = 10` with `fixed_delta_seconds = 0.1`
   (or `sensor_tick = 0.1`). State this in V2-C3 so partial scans can't occur.
5. **One bad point voids the frame (Note).** Deterministic and safe; with the
   default noise-free sensor it was never triggered. No change proposed.

## Not covered

Moving vehicles, vehicle pitch under braking, other maps, LiDAR noise settings,
and the full 3-vehicle 10 Hz runner. Those belong to the CARLA fleet runner task.
