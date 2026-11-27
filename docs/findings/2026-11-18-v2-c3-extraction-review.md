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

> **Qualified 2026-11-25.** These are the 2026-11-18 run's numbers. The
> "Spawn points" column is the map's spawn-point count, not a count of verified
> scans: that probe did not record spawn failures, missing callbacks or frame
> IDs, so it cannot show that every row came from a valid scan of the intended
> frame. See the revisions below for the verified 2026-11-25 results.

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

## Revision 2026-11-25: scan coverage verified

Review of this finding found that the original probe could overstate coverage:
it skipped failed spawns without counting them, and a spawn whose LiDAR callback
never arrived fell through to `NO_FRONT_HIT`. It also used the last callback
received rather than the scan for the final tick. The original probe and the
results above are kept unchanged as the 2026-11-18 record.

[`c3_region_probe_v2.py`](../../evidence/v2/c3-extraction-review/c3_region_probe_v2.py)
gives every spawn point exactly one outcome. It waits up to 2 s for the scan of
the final tick, and reports `SPAWN_FAILED`, `MISSING_SCAN` and `EMPTY_SCAN`
separately. A missing scan never counts as clear. Same sensor, mount, region and
CARLA host as above; client 0.9.15 in the `linux/amd64` container. One JSON line
per spawn point is committed next to the probe.

| Map, lower z bound | Spawn points | Spawn failed | Missing scan | Empty scan | Delivered scans (v2) | Nothing ahead | Real object | False obstacle (road) | False ≤ 10 m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Town10HD_Opt, −1.0 | 155 | 0 | 0 | 0 | 155 | 130 | 25 | **0** | **0** |
| Town03_Opt, −1.0 | 265 | 0 | 0 | 0 | 265 | 221 | 32 | **12** (4.5%) | **5** |
| Town03_Opt, −0.5 | 265 | 0 | 0 | 0 | 265 | 226 | 32 | 7 | 1 |

Raw output: [Town10](../../evidence/v2/c3-extraction-review/town10-v2-2026-11-25.jsonl),
[Town03 −1.0](../../evidence/v2/c3-extraction-review/town03-zmin-1.0-v2-2026-11-25.jsonl),
[Town03 −0.5](../../evidence/v2/c3-extraction-review/town03-zmin-0.5-v2-2026-11-25.jsonl).

**Town10HD_Opt: confirmed.** The 0/155 result stands. All 155 spawns produced a
valid, non-empty scan for the final tick, so none of the 130 clear results comes
from a missing callback.

**Town03_Opt: corrected.** The rerun finds 12 false obstacles (5 within 10 m), not
14 (6), and at −0.5 m 1 within 10 m, not 2. The nearest is 3.8 m (spawn 10). The
2.9 m level-spawn hit reported above did not reproduce. It most likely came from
a scan other than the final tick's, but the original run kept no per-spawn output,
so this cannot be confirmed. Finding 1 still holds: the road enters the region on
rising roads, and raising the bound reduces but does not remove false hits.

Not checked: repeatability across CARLA restarts (each configuration was run once),
other maps, and moving vehicles.

## Revision 2026-11-25 (2): exact frames and audit limits

A second review of this PR found three gaps in the v2 probe above: it accepted a
later frame when the requested one had not arrived, it counted `EMPTY_SCAN` among
valid scans, and it did not record frame IDs. The v2 probe and its outputs are
kept unchanged; their column is renamed "Delivered scans (v2)" because it
includes empty scans by definition (there were none).

[`c3_region_probe_v3.py`](../../evidence/v2/c3-extraction-review/c3_region_probe_v3.py)
uses only the scan whose frame equals the final tick's frame. Older scans are
discarded; a later frame first is recorded as `FRAME_MISMATCH`, never used.
`validScans` counts only `NO_FRONT_HIT`, `OBJECT` and `FALSE_SURFACE`. Every row
records `requestedFrame` and `receivedFrame`. The frame and accounting logic is
covered without CARLA by
[`tests/test_c3_region_probe_v3.py`](../../tests/test_c3_region_probe_v3.py)
(8 checks, including a later frame not substituting and empty scans being invalid).

| Map, lower z bound | Spawn points | Spawn failed | Missing | Frame mismatch | Empty | Valid scans | Frame matched | Nothing ahead | Real object | False obstacle | False ≤ 10 m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Town10HD_Opt, −1.0 | 155 | 0 | 0 | 0 | 0 | 155 | 155 | 130 | 25 | **0** | **0** |
| Town03_Opt, −1.0 | 265 | 0 | 0 | 0 | 0 | 265 | 265 | 221 | 32 | **12** | **5** |
| Town03_Opt, −0.5 | 265 | 0 | 0 | 0 | 0 | 265 | 265 | 226 | 32 | 7 | 1 |

Raw output: [Town10](../../evidence/v2/c3-extraction-review/town10-v3-2026-11-25.jsonl),
[Town03 −1.0](../../evidence/v2/c3-extraction-review/town03-zmin-1.0-v3-2026-11-25.jsonl),
[Town03 −0.5](../../evidence/v2/c3-extraction-review/town03-zmin-0.5-v3-2026-11-25.jsonl).
On both Town03 settings the per-spawn outcome and distance are identical to the
v2 output.

**Conclusion.** The verified result is the v3 run: on Town10HD_Opt, 155 of 155
spawn points produced a valid scan of the requested frame and none showed a false
road obstacle. Town03_Opt has 12 false obstacles (5 within 10 m) at the contract
bound. Finding 1 and its proposal are unchanged.

**Audit limits of the kept artifacts.**

| Artifact | What it can support | What it cannot |
|---|---|---|
| 2026-11-18 probe and table | The road-on-slope mechanism and approximate rates | Per-spawn outcomes, spawn failures, missing scans, or which frame was used; no raw output was kept |
| v2 probe and JSONL (2026-11-25) | Per-spawn outcomes; spawn failures and missing scans | Which frame each scan came from; a later frame could have been used |
| v3 probe and JSONL (2026-11-25) | Per-spawn outcomes from the requested frame, with frame IDs | Repeatability: each configuration ran once on one CARLA host |
