# PR #31 — V1 twin verification and legacy fixes

## Review metadata

| Field | Reviewed value |
| --- | --- |
| PR | [#31 — fix: verify individual twin consistency and repair legacy context routing](https://github.com/ankit-suman-07/QA-SDV-Project/pull/31) |
| Author | Bayan Sayyadifar (`sayadifarbayan-lgtm`) |
| Head branch | `bayan/fix/v1-twin-verifier` |
| Base branch | `main` |
| Head SHA | `61560cb2ba37f5cfd055ffaaba7058185a00ad69` |
| Base SHA and merge base | `8b3143aaa1631ee81b18042e6fb1aa34d50484dc` |
| Review date | November 11, 2026 |
| Task | B3 individual-twin consistency and aggregation handoff, plus assigned legacy repairs |
| Acceptance | V1-02/V1-04; supports V1-03/V1-05/V1-08 |
| Recommendation | **REQUEST CHANGES** |

Fresh fetch confirms one commit directly parented by the base SHA. The branch does not contain/import #30 or #32's production code. All line references are to the reviewed head. The primary worktree stayed on `main`.

## Executive summary

This PR repairs partial cooling recovery verification, checks source freshness separately from processing time, improves malformed-state handling, fixes the vehicle-specific legacy scenario-context route, and provides an independent V1 read-only snapshot/sequence checker. It implements no fleet aggregation or twin writer. Its focused tests and full non-integration suite pass with pinned dependencies and generated Protobuf modules.

The previously reported deep-extension crash remains reproducible in its new V1 inspector. Its iterative finite-number traversal accepts data that the following recursive copy cannot handle. This is an uncontrolled exception in a verification component, not #30's infinite MQTT retry loop. Unicode acceptance also needs explicit alignment with downstream consumers; the observed risk is described separately rather than counted as an additional demonstrated runtime defect.

## Source-of-truth and scope

Read [SOURCE-OF-TRUTH.md](../SOURCE-OF-TRUTH.md) at its actual `docs/` location, [V1 contract](../v1-interface-contracts.md) v1.0.0, [task distribution](../10-detailed-task-distribution.md), [scope](../08-project-scope-and-acceptance.md), [architecture](../09-architecture-diagrams.md) and [independent development](../v1-independent-development.md). The contract is still **proposed for affected-owner review**. Older scope/diagram ownership is superseded by the latest allocation: Ankit alone owns fleet aggregation. V1 targets two synthetic vehicles by November 16, 2026; V2 is excluded.

## Findings summary

| ID | Severity | Status | Issue | File and lines at reviewed head |
| --- | --- | --- | --- | --- |
| PR31-F01 | P2 — Medium | Confirmed | Deep snapshot extensions escape as `RecursionError` during copying | `ditto/twin_consistency.py:105`, also `118`/`125` |

Counts: P0 0, P1 0, P2 1, P3 0. The checker is new in this PR; this is not attributed to inherited `main` code. Historical deep-copy evidence was independently rerun at the freshly fetched head.

## PR31-F01 — Deep snapshot causes an uncontrolled exception

- **Severity/status:** P2 — Medium; Confirmed.
- **Location:** [`ditto/twin_consistency.py:105`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/61560cb2ba37f5cfd055ffaaba7058185a00ad69/ditto/twin_consistency.py#L105). `TwinSequence.observe` calls inspection at line 118 and copies again at line 125.
- **Affected behavior:** Safe validation of individual snapshots and sequence observations.
- **Root cause:** `_reject_nonfinite` uses an iterative traversal and accepts deep finite extensions. The later `copy.deepcopy(props)` uses recursive copying and can exceed Python's recursion limit. No conversion to `ConsistencyError` occurs. Sequence clients expecting controlled invalid-state errors receive an unrelated runtime exception.
- **Reproduction:** Load `tests/fixtures/v1/ditto-vehicle-002.json`, set `features.v1.properties.extension` to `json.loads('[' * 600 + '0' + ']' * 600)`, and call `inspect_v1_twin('vehicle-002', thing, now=datetime(2026,1,1,0,0,4,tzinfo=timezone.utc))`. It raises `RecursionError`. The same snapshot passed to `TwinSequence.observe` raises the same exception. After catching it, a valid unchanged prior snapshot still returns `DUPLICATE_EVENT`; sequence state was not corrupted in this reproduction.
- **Expected:** Safely accept the compatible finite extension or return a controlled invalid-snapshot error that a consumer can treat as unavailable. A checker must not terminate a verification run on a modest JSON input merely because its copy path has a lower effective nesting limit than validation.
- **Actual:** `RecursionError: maximum recursion depth exceeded` escapes from both entry points.
- **Impact:** A real decoded snapshot can abort a verification/integration run or an unguarded future consumer. No twin mutation occurs and no subscriber retry loop exists in #31; those stronger effects must not be attributed here.
- **Minimum required correction:** Guarantee safe copy/comparison for accepted snapshot shapes or reject unsupported nesting through `ConsistencyError` before those operations. Cover the second sequence copy and equality operations too. Do not impose MQTT's 64-KiB wire limit on persisted snapshots. Coordinate any structural limit with #30 and the shared interface owners.
- **Regression tests:** Deep arrays/dictionaries near the chosen boundary; `inspect_v1_twin` and `TwinSequence.observe`; prior state unchanged after rejection; subsequent valid observations progress for both vehicles; result copies remain independent of caller objects; allowed nested snapshots remain safe through duplicate/conflict comparison.
- **Contract/acceptance:** C3 compatible extensions/validation; C5 unusable snapshots; C6 schema; B3 and V1-02/V1-04/V1-05.
- **Definition of done:** Both entry points safely accept or consistently reject the reproduction, retain valid state, and support the next valid observation without an uncontrolled recursion failure.

Self-contained reproduction, run from this PR's root:

```python
import json
from datetime import datetime, timezone
from ditto.twin_consistency import inspect_v1_twin, TwinSequence

thing = json.load(open('tests/fixtures/v1/ditto-vehicle-002.json'))
thing['features']['v1']['properties']['extension'] = json.loads('['*600+'0'+']'*600)
now = datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc)
for check in [lambda: inspect_v1_twin('vehicle-002', thing, now=now),
              lambda: TwinSequence().observe('vehicle-002', thing, now=now)]:
    try:
        check()
    except Exception as error:
        print(type(error).__name__, str(error))
```

## Unicode compatibility observation — not a separate counted defect

With the same fixture, `extension='\ud800'` is accepted by `inspect_v1_twin`. Encoding its returned view using `json.dumps(view, ensure_ascii=False).encode('utf-8')` raises `UnicodeEncodeError`. Default ASCII-escaped JSON serialization can represent the Python string; therefore this is not proof that every downstream consumer fails. #31 contains no such production UTF-8 serializer or MQTT retry loop, and no actual backend failure was demonstrated.

Before integration, agree whether decoded snapshots may contain lone surrogates. Prefer shared Unicode scalar validation of values/keys and controlled errors if they are unusable at the supported consumer boundary. Test lone high/low surrogates, surrogate keys, valid Unicode and non-BMP characters against #30 and Ankit's actual adapter. Do not claim accepted snapshots are universally safe for UTF-8 serialization. This observation confirms the historical acceptance behavior without inflating it into a second observed service failure.

## Verification

Environment: Linux x86_64, CPython **3.12.16**, pytest **9.1.1**, requests **2.32.5**, grpcio **1.82.1**, grpcio-tools **1.68.0**, protobuf **5.29.6**, kuksa_client **0.5.1**. A shared temporary environment also included Paho **2.1.0** from #30; #31 does not import or require it. `PYTHONDONTWRITEBYTECODE=1` was set. `PY=/tmp/bayan-review-ndC62A/venv/bin/python`; cwd `/tmp/bayan-review-ndC62A/pr31`.

```bash
mkdir -p uprotocol/generated
$PY -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated \
  uprotocol/proto/common.proto uprotocol/proto/health_status.proto \
  uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto \
  uprotocol/proto/vehicle_diagnostic.proto
$PY -B -m pytest -q -ra -p no:cacheprovider tests/test_verify_vehicle_state.py tests/test_twin_consistency.py tests/test_scenario_context.py tests/test_fault_mapper.py tests/test_fault_details.py tests/test_ditto_http.py
$PY -B -m pytest -q -ra -p no:cacheprovider
PYTHONPATH=. $PY /tmp/bayan-review-ndC62A/reproduce31.py
git diff --check 8b3143a...HEAD
```

| Check | Exit | Passed | Failed | Skipped / deselected | Scope |
| --- | --- | --- | --- | --- | --- |
| Protobuf generation | 0 | N/A | 0 | N/A | Temporary files only |
| Focused tests | 0 | 79 + 82 subtests | 0 | 0 / 0 | Legacy and V1 mocked/component checks |
| Full non-integration pytest | 0 | 188 + 300 subtests | 0 | 0 / 9 | Previously dependency-blocked transport modules now collect |
| Deep/Unicode reproductions | 0 | N/A | N/A | N/A | Script reports observed failures/acceptance, not a passing implementation regression |
| Changed Python AST / tracked JSON parsing | 0 | 8 / 28 files | 0 | N/A | Static validation |
| Diff whitespace | 0 | N/A | 0 | N/A | Passed |

The temporary reproduction output was: `nested RecursionError`, `sequence uncontrolled RecursionError`, `prior state preserved DUPLICATE_EVENT`, `surrogate inspection accepted`, followed by `surrogate UnicodeEncodeError`. The minimal snippet above preserves the nesting reproduction independently of the temporary script.

Unchanged base passed 158 tests and 218 subtests, with 9 integration tests deselected. All six refreshed GitHub checks passed: [CI](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43076375687), [synthetic baseline integration](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43076375679). These are CI observations, not locally executed Java/image/live runs. Existing synthetic pipeline CI does not validate the entire V1 two-vehicle flow.

No real Ditto/provider/KUKSA session was exercised locally. Scenario-context tests inject HTTP responses, and the bridge-caller test compiles its function rather than executing the complete startup loop. Protobuf generation resolves collection, not live source-time or unit semantics.

## Contract compliance and legacy regression assessment

| Boundary | Assessment |
| --- | --- |
| Three V1 identity locations, required fields, schema and C4 classification | Implemented; identity/missing/type/threshold tests pass. |
| C5 freshness | Uses original source timestamp, configurable 5/30-second boundaries and injected aware clock; rejects >1-second future snapshots. Fresh sensor failure remains transport-available/health-critical. |
| UTC and ordering | V1 requires UTC text; legacy parser accepts aware offsets and normalizes UTC. V1 ordering preserves submicrosecond precision, rejects equal/older source times with new IDs, and distinguishes unchanged repeated polls from conflicting ID reuse. |
| Copying and malformed data | Broad type/non-finite validation; F01 leaves a structural crash path. Unicode consumer policy remains an integration question described above. |
| Cooling partial recovery | Correctly requires BOTH temperature <=100 C and pressure >=180 kPa before flagging a still-active fault as fully recovered. Existing hysteresis and activation behavior are preserved. |
| Source versus processing freshness | Checked separately in legacy verification; old source cannot appear fresh merely because processing time advances. |
| Legacy context route | New helper calls `/api/v1/vehicles/{vehicleId}/scenarios/COOLING_SYSTEM_FAILURE`, validates returned identity/scenario/boolean state and context-ID types, and returns no trusted context on injected invalid responses. Defaults retain vehicle-001 cooling. No obsolete route fallback. |
| Ownership | No fleet aggregate/counting/materialization, no second ingress and no V2 diagnostics implementation. |
| Security | New helper rejects URL credentials/query/fragment and unsupported vehicle/scenario; mock error tests pass. Hard-coded legacy Ditto defaults/auth and raw legacy HTTP retry logging predate this PR and were not introduced here. Live authorization remains unverified. |

**Inherited limitations, not new PR findings:** the legacy Protobuf helper generates source time during serialization; this verifier cannot reconstruct observation time already lost upstream. Tire VSS kPa versus legacy psi mismatch is unchanged and explicitly documented pending Emmanuel's confirmation. The legacy checker is not a complete proof of every fault activation rule; untouched baseline limitations are not reclassified as new defects. Real full-bridge startup, command correlation and unit correctness still require runtime evidence.

## Cross-PR compatibility and recommendation

#30 and #31 agree on ordinary fixtures, required fields, invalid timestamp formats, both identities, C4 thresholds and out-of-order rejection in a 20-test temporary compatibility suite. Differences are intentional: ingress rejects duplicate messages; the observation checker recognizes unchanged repeated polls; ingress preserves future/old source observations for backend evaluation, whereas the checker derives freshness/rejects untrusted future snapshots. Do not force these distinct responsibilities into identical return codes.

Both new implementations independently have deep-copy weaknesses. #30's failure also traps a subscriber retry; #31's does not. A `ditto/README.md` conflict between these PRs was confirmed by temporary merge-tree (exit 1); other changed files do not overlap. No resolution or code fix was applied. #32 does not import this verifier and can prepare independently.

**REQUEST CHANGES:** fix F01, retain the passing legacy regressions, add safe-depth/sequence tests, and settle Unicode consumer behavior at the handoff. Obtain affected-owner review of the proposed contract. Corrected #31 may merge before #30, supplying independent verification; full V1 completion still requires real source-time, provider and twin evidence.

Review used [systematic debugging](../../skills/systematic-debugging.md) and [verification before completion](../../skills/verification-before-completion.md) at `8b3143a`. No production or existing test changes were made.
