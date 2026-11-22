# SYNTHETIC V2 fixtures

All data here is **SYNTHETIC**, never recorded CARLA. Version 2.0.0-prep.1.
Expected values are committed JSON, independent of the development oracle.
Production owners must feed these inputs into their own component and compare
against these outputs; passing the reference tools alone proves no production feature.

| Input → expected result | Contract |
|---|---|
| [observation cases](observations/cases.json): boundaries, invalid/unknown/mismatched identity, malformed JSON, front frames → each case.expected | V2-C2/C3/C4 |
| [recovery](sequences/recovery.json): fault → progress → healthy at 2 s | V2-C4 |
| [interrupted](sequences/interrupted.json): renewed warning and >0.5 s gap restart window | V2-C2/C4 |
| [cached/order](sequences/cached-and-ordering.json): repeat/equal/late rejection, successor accepted | V2-C5 |
| [sessions](sequences/sessions.json): unauthorized restart rejected, registered successor, retired-session rejection | V2-C5 |
| [source silence](sequences/source-silence.json): clock-only ticks reset recovery, no fabricated observation | V2-C2/C4 |
| [dropout/clock](sequences/dropout-and-clock.json): invalid sensor, stale/future input reset recovery | V2-C2/C4 |
| [optional motion](observations/vehicle-001-motion.json): 3, -4, 0 m/s → 18 km/h | V2-C2/C4 |
| [session manifest](observations/session-manifest.json): synthetic actor/broker/provider/twin and simulation origin mapping | V2-C1/C2 |
| observations/vehicle-001.json through vehicle-003.json → corresponding health-events/ and twins/ files | V2-C1/C5 |
| [fleet cases](twins/fleet-cases.json): missing vehicles retained, counts in expected order below | V2-C6 |
| [diagnostic cases](diagnostics/cases.json): acceptance/execution, success/failure/timeout and mismatch | V2-C6 |
| [fault mappings](diagnostics/faults.json): independent project-level examples, not native SOVD wire schema | V2-C6 |

References: [full contract](../../../docs/v2-interface-contracts.md).
Fleet count array order: total, available, stale, unavailable, healthy, warning,
critical. Sequence steps embed input, evaluation clock and literal expected
health/recovery pair or rejection code. Observation cases embed requirement IDs.
Source silence is evaluated at >0.5 s; availability ages separately at 5/30 s.
No repeated cached observation may clear a fault.

Fixed epoch 2026-01-01T00:00:00Z. Use replay `--anchor` to shift every UTC timestamp
by one offset (including explicit evaluation times); simulation values and offsets
remain unchanged. Explicit stale/future vectors stay stale/future. Feed evaluationTime
to an injected clock; immediate replay into a wall-clock component is not a timing
acceptance test. Negative sequences intentionally contain rejected deliveries.
