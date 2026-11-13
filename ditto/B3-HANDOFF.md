# B3 individual-twin consistency and Ankit handoff

Baseline: `8b3143aaa1631ee81b18042e6fb1aa34d50484dc` on
`bayan/fix/v1-twin-verifier`. Development requirements are
[contract v1.0.0](../docs/v1-interface-contracts.md), C3/C5/C6/C7/C9, and
[B3 task allocation](../docs/10-detailed-task-distribution.md).
The contract remains proposed for affected-owner review. This branch imports no
production code from unmerged PR #30 and implements no fleet aggregation.

## Legacy verifier repairs

`scripts/verify-vehicle-state.py` preserves its existing CLI flags, HTTP defaults,
30-second default maximum age, explicit override and publication-interval formula
`max(3 * interval, 5)`. Invalid/nonpositive/nonfinite configuration is reported.
The accepted individual identities are `sdv:vehicle-001` / `sdv:vehicle-002` with
matching `attributes.vehicleId`; missing or wrong identity is an error. Updated
test fixtures now represent those actual Ditto identity fields.

An active `COOLING_SYSTEM_FAILURE` is inconsistent with recovery only when both
temperature <=100 C and coolant pressure >=180 kPa. Partial recovery and the
hysteresis zone remain valid active-fault states. Activation rules and runtime
cooling behavior are unchanged.

Source and processing timestamps are independently parsed and checked against one
injected evaluation clock. Missing/invalid/naive values and dates more than one
second in the future produce validation errors instead of exceptions. Legacy
timezone-aware offsets are normalized to UTC. Historical detection/clear times
may be old, but must be timezone-aware and not beyond the future tolerance when
present. Full recovery, malformed feature containers, fault lists/counts and
required detail structures also produce errors.

`verify_vehicle_state(..., clock=lambda: fixed_aware_datetime)` supports deterministic
tests. Without a clock it captures current UTC once. The verifier performs GETs
only; it never modifies a Thing.

## V1 read-only API and read contract

Ankit reads each registered individual Thing independently:

| vehicleId | Whole-Thing GET path |
|---|---|
| vehicle-001 | `/api/2/things/sdv:vehicle-001` |
| vehicle-002 | `/api/2/things/sdv:vehicle-002` |

Use `Accept: application/json` and deployment-configured authentication, never
credentials embedded in URLs or committed examples. The existing canonical
[001](../tests/fixtures/v1/ditto-vehicle-001.json) and
[002](../tests/fixtures/v1/ditto-vehicle-002.json) fixtures define whole-Thing shape.
The live base URL/credentials remain deployment configuration, not invented here.

`twin_consistency.py` accepts decoded snapshots and has no network/write dependency:

- `inspect_v1_twin(vehicle_id, thing, now=aware_datetime)` validates `thingId`,
  `attributes.vehicleId`, `features.v1.properties.vehicleId`, exact schema 1.0.0,
  nonblank lastEventId/context IDs, strict UTC source timestamps and C4 LiDAR /
  health / canonical fault consistency. Boolean distances, negative/nonfinite
  values, bad nested shapes, missing fields and inconsistent classifications fail.
  NaN, Infinity and -Infinity are rejected anywhere within V1 properties,
  including nested extension dictionaries and arrays, with NON_FINITE_VALUE.
  This check runs before accepting a snapshot or updating a sequence. Finite
  extensions remain intact; no MQTT wire-size limit or JSON reserialization is
  applied to persisted-state verification.
- It returns copied `properties` and source-derived `availability`: age <=5 s is
  AVAILABLE, >5 through 30 s is STALE, and >30 s is UNAVAILABLE. Both thresholds
  are configurable and must satisfy `0 < stale < unavailable`. Source >1 s in the
  future raises `ConsistencyError('FUTURE_TIMESTAMP')`; invalid/untrusted state
  must be treated as unavailable by the consuming backend. It never invents
  HEALTHY state or changes source timestamps.
- `TwinSequence.observe(vehicle_id, thing, now=...)` returns INITIAL, UPDATED or
  DUPLICATE_EVENT for an unchanged repeated snapshot. Changed content under the
  same latest event ID raises CONFLICTING_EVENT; older/equal source time under a
  different ID raises OUT_OF_ORDER. Comparisons preserve submicrosecond source
  precision. Rejected snapshots leave prior observations intact, per vehicle.
- `verify_isolation(before, after, target='vehicle-002', now=...)` validates both
  mapped individual snapshots and requires the non-target whole Thing to be
  unchanged. Use it for a controlled target-only replay/write check. Independent
  live publishers may legitimately advance vehicle-001 telemetry; during that
  scenario separately require vehicle-001 to stay HEALTHY without injected faults
  and check its own sequence, rather than demanding an identical whole Thing.

Example using only a deterministic fixture:

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from ditto.twin_consistency import inspect_v1_twin, TwinSequence

thing = json.loads(Path('tests/fixtures/v1/ditto-vehicle-001.json').read_text())
now = datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc)
view = inspect_v1_twin('vehicle-001', thing, now=now)
assert view['availability'] == 'AVAILABLE'
sequence = TwinSequence()
assert sequence.observe('vehicle-001', thing, now=now) == 'INITIAL'
assert sequence.observe('vehicle-001', thing, now=now) == 'DUPLICATE_EVENT'
```

These are observation checks, not a second ingress/writer. They neither prevent
production writes nor persist restart watermarks. B1/B2 owns write ordering and
restart persistence. Ankit A2/A5 owns live HTTP outcomes, evaluation clock,
availability/counting, API projections and the sole fleet-twin materialization.
No counts, fleet Thing, dashboard or Spring Boot changes are included here.

## Legacy scenario-context repair

`scenario_context.py` reuses `ditto_http.get_json_with_retry` (three attempts,
two-second timeout, 0.2-second retry delay) and calls:

`GET {SIMULATOR_CONTROL_URL}/api/v1/vehicles/vehicle-001/scenarios/COOLING_SYSTEM_FAILURE`

The legacy bridge still handles vehicle-001 and cooling. The import-safe helper
also supports vehicle-002 when explicitly requested by a caller. Matching vehicle
and scenario plus boolean `active` are required. Supplied command IDs must be
nonblank strings; the provider's initial inactive state may legitimately have
null IDs. HTTP errors, exhausted timeout/connection retries, malformed JSON and
wrong identities return no trusted context (`{}`). No obsolete-route fallback is
added. Existing cooling processing and its telemetry-context fallback remain;
that fallback must not be presented as proof of executing a diagnostic command.

Tests inject HTTP responses and compile only the bridge's caller function to
exercise its real wiring, without importing its KUKSA/Protobuf startup loop.
The complete legacy bridge still requires those runtime dependencies for execution.

## Tire-pressure decision: explicitly pending Emmanuel

**Runtime unit conversion is NOT changed in B3.** The user requires Emmanuel's
confirmation of upstream semantics first.

- VSS declares `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` in kPa.
- The current generator supplies approximately 30-34, and the bridge passes the
  observation unchanged to legacy Protobuf `tire_pressure_psi` / Ditto
  `signals.tirePressurePsi`.
- The mapper labels that field psi and uses warning <=28 / critical <=24 psi.
  New tests pin this behavior and explicitly verify the upstream kPa declaration.
  Passing those tests documents compatibility, not correct end-to-end units.

Proposed boundary, after Emmanuel confirms the actual published unit and corrects
any generator/VSS mismatch: convert a validated kPa KUKSA observation to psi in
Bayan's legacy bridge **before** `publish_vehicle_status(tire_pressure_psi=...)`.
Protobuf, the legacy Thing and mapper would then agree on psi without a second
conversion in the mapper. Add reviewed paired-unit fixtures and threshold-boundary
tests at that time. Do not infer units from a value near 32, relabel VSS, alter
mapper thresholds or modify Emmanuel's simulator in this branch.

## Evidence, limitations and review checklist

Focused Python 3.12 command from the repository root:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_verify_vehicle_state.py tests/test_twin_consistency.py tests/test_scenario_context.py tests/test_fault_mapper.py tests/test_fault_details.py tests/test_ditto_http.py
```

Tests are **mock/component-only**. No shared service is modified and no live
Mosquitto, Ditto, provider, KUKSA, fleet or OpenSOVD acceptance is claimed.
Local Python 3.12.10 verification: 79 focused tests and 82 subtests passed;
178 available regression tests and 300 subtests passed with the four modules
below explicitly excluded. Existing temporary-file tests required execution
outside the filesystem sandbox. CLI help, Python syntax, whitespace checks and
inspection for forbidden PR #30/development-mock imports passed. No code or
environment was staged, committed or pushed.
The legacy source timestamp is still generated by upstream Protobuf serialization;
checking source age cannot recover an original observation timestamp already lost
before reaching Ditto. Upstream preservation requires owner-coordinated follow-up.

Full regression collection is still blocked by generated `common_pb2` imports in
`tests/test_uprotocol_transport.py`, `uprotocol/tests/test_extended_transport.py`
and `uprotocol/tests/test_transport.py`; `vehicle-simulator/tests/test_kuksa_publication.py`
also imports unavailable `kuksa_client` before its integration marker can deselect
it. Actual publication tests need live KUKSA. Run full CI on a compatible Python
3.12 dependency/build environment before claiming complete baseline regression.

Repository TDD and verification-before-completion instructions were used for this
work: failing regression checks preceded fixes, followed by focused and available
regression runs. The source versions are the files under `skills/` at this branch's
baseline. `.venv-b1/` is a local, untracked test environment; keep it unstaged.

For Ankit:

- [ ] Review individual identities, V1 fields and GET examples against A2/A5.
- [ ] Review fixed-clock source freshness / future tolerance and repeated-poll semantics.
- [ ] Compare real snapshots through healthy -> vehicle-002 fault -> recovery;
  record exact revision, source/event/context IDs and vehicle-001 isolation.
- [ ] Validate real provider context routing and capture command correlation.
- [ ] Obtain Emmanuel's unit confirmation before any runtime tire conversion.
- [ ] Keep aggregate counting and fleet Thing writes exclusively under A5.
- [ ] Keep mock results separate from live evidence; rerun blocked regressions in CI.


## PR31-F01 correction review (November 12, 2026)

Authoritative documentation was read from fetched `origin/main` at
`8e9566e` without merging or rebasing this independent PR branch. Contract
1.0.0 remains proposed for affected-owner review; Ankit still exclusively owns A5.

The confirmed failure was recursive `copy.deepcopy` after iterative finite-value
validation. Copying of V1 properties (including the second sequence copy) and
snapshot equality now use explicit stacks. Duplicate/conflict and whole-Thing
isolation comparisons no longer recurse through extension containers. No shared
depth limit has been invented: finite JSON arrays/dictionaries at depths 599,
600, 601 and 1500 are covered. There is no MQTT wire-size check on persisted
snapshots. Resource exhaustion for arbitrarily large input is not a guarantee
this in-memory verifier can provide; HTTP/JSON parser limits remain the caller's
responsibility. Cycles, non-string object keys and non-JSON extension types are
controlled invalid snapshots (INVALID_STRUCTURE / INVALID_TYPE), not additional
supported JSON forms. Rejection leaves observation state unchanged.

Unicode is preserved, including valid non-ASCII and non-BMP text. The current
contract does not explicitly settle lone surrogate code points in already-decoded
persisted snapshots. Their existing acceptance is deliberately unchanged and
tested, including dictionary keys: this is NOT a claim of safe unescaped UTF-8
serialization. Ankit and affected owners must agree the consumer/ingress Unicode
policy before integration; an unescaped UTF-8 serializer can reject these strings.
No production serializer or PR #30 implementation is imported here.

Fresh Python 3.12.10 mock/component checks:

- The added regression tests failed before the fix with deep-copy RecursionError
  and acceptance of cyclic non-JSON input, then passed after correction.
- The six-module focused command above: **83 passed, 92 subtests passed**.
- Full repository pytest was attempted: collection stopped at the same four
  dependency-blocked modules listed above (common_pb2 / kuksa_client missing).
- Available regressions with those four modules explicitly ignored and
  `-m "not integration"`: **182 passed, 310 subtests passed**.
- Python AST syntax and `git diff --check` passed. No live services were started,
  no dependencies installed, and no staging, commit or push was performed.

The three actual repository skill sources used were systematic-debugging,
test-driven-development and verification-before-completion under `skills/`.
The referenced writing-good-tests and debugging supporting files are absent;
no use of those missing files or a separate code-review skill is claimed.
Fresh GitHub Actions and live twin/provider verification remain pending.
