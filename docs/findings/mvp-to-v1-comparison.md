# MVP → Phase V1 progress comparison

**Stop checkpoint after d8c1f40:** earlier combined PASS is for candidate6a6badc,
before the final bounded-cleanup-join correction. Targeted app checks pass; final
combined verification and latest shutdown-head CI remain pending. See the current
release-readiness handoff; no prior result is relabelled as a final-main pass.


## Latest follow-up — November 15, 2026: unmerged engineering candidate

The [dated release-readiness assessment](v1-release-readiness.md) and
[candidate evidence](../../evidence/v1/release-candidate-20261115/README.md)
supersede earlier pending/blocked statements where explicitly identified. Merged
PR #43 passes same-device V1-09. Independent draft #44/#45/#46 fix clean feature
initialization, real HTTP compatibility and shutdown; exact-head CI and a combined
unmerged clean deployment passed. Python540 +386 subtests, Java209, frontend7;
two Python skips/nine integration deselections retained. Five actual fault/clear
trials reached real MQTT/twins/API/fleet/dashboard, with negative/freshness/recovery
checks. Three affected actual Kanto cycles now exit0. No remote-LAN/crash automatic
restart, full V1 acceptance, verified-main release or matched MVP speedup claimed.
Historical findings, prepared-deployment workarounds, failures and original
attribution below remain intact. Human approvals, final merged-main checks,
provenance qualifications and release/submission gates remain open. Report/video
creation/recording/submission are excluded and pending.


## Purpose and assessment boundary

Assessed **November 14, 2026 UTC / November 13, 2026 America/Toronto**, against fetched main **`3561c00cce1a96d18b5b97e1f8d9948e673643bb`**, also the local HEAD. This compares recorded single-vehicle MVP evidence with implemented Phase V1 components and their verification. It does **not** certify complete Phase V1 acceptance.

Authority starts at [SOURCE-OF-TRUTH](../SOURCE-OF-TRUTH.md), then the [scope](../08-project-scope-and-acceptance.md), [latest task distribution](../10-detailed-task-distribution.md), [architecture](../09-architecture-diagrams.md), [interface contracts](../v1-interface-contracts.md) and [independent-development guide](../v1-independent-development.md). The task distribution and C1 supersede older ownership wording: Bayan owns individual-twin ingress/consistency; **Ankit owns the sole fleet aggregation implementation and fleet-twin writer**. Phase V1 has **two vehicles total**, vehicle-001 and vehicle-002. The three-vehicle target belongs to Phase V2.

Contract 1.0.0 remains **proposed for affected-owner review**. Merged code demonstrates adoption of a development baseline, not formal approval of every shared decision. Approval provenance, the proposed 30-second unavailable threshold, propagation/dispatch budgets, deployed credentials/endpoints, clock handling and cross-consumer Unicode/nesting policy remain documented review items. November 11 preparation documents describe their starting state; their “implementation still required” wording is not the current implementation inventory.

No applicable AGENTS.md was found. The repository's [verification-before-completion instructions](../../skills/verification-before-completion.md) guided source checking and final documentation verification. No services, experiments or application tests were launched for this task. Historical results below are attributed to their records, not claimed as fresh executions.

| Status | Meaning |
|---|---|
| IMPLEMENTED | Relevant code/configuration exists on assessed main; this alone proves no runtime acceptance. |
| MOCK-VERIFIED | Recorded checks use fake/injected or mock HTTP dependencies. Real Java/browser execution may still be mock-backed. |
| LIVE-VERIFIED | A recorded run used the stated actual components, at the stated revision and boundary. It does not extend to untested downstream components. |
| PENDING | Required approval, implementation, integration or acceptance evidence remains outstanding. |
| NOT RECORDED | Inspected evidence does not establish the fact; this does not mean the capability never existed. |

## Sources and merged implementation

Sources inspected: [evidence index](../../evidence/README.md), [MVP baseline](../../evidence/v1/baseline.md), [revision marker](../../evidence/v1/mvp-revision.txt), [timing CSV](../../evidence/v1/mvp-timings-20261108T010116457743Z.csv), [A2](../../evidence/v1/live-twin-api.md), [A3](../../evidence/v1/scenario-routing.md), [A5](../../evidence/v1/fleet-dashboard.md), [E1](../../evidence/v1/E1-two-vehicle-edge.md), [E2](../../evidence/v1/E2-lidar-cycle.md), [skill usage](../../evidence/v1/skill-sources.md), their linked artifacts and relevant source/history. The artifact audit below qualifies missing evidence.

Git history confirms all these PRs are merged:

| Area | PR | Merge commit | Implementation present |
|---|---|---|---|
| Shared preparation | [#29](https://github.com/ankit-suman-07/QA-SDV-Project/pull/29) | `8b3143a` | Contracts, fixtures and independent substitutes. |
| A2 | [#34](https://github.com/ankit-suman-07/QA-SDV-Project/pull/34) | `9ef82a9` | HTTP individual-twin reader and versioned vehicle APIs. |
| A3 | [#35](https://github.com/ankit-suman-07/QA-SDV-Project/pull/35) | `2803429` | Vehicle-specific scenario dispatch, acknowledgement validation and failure handling. |
| A5 | [#36](https://github.com/ankit-suman-07/QA-SDV-Project/pull/36) | `8e9566e` | Fleet API, dashboard, provisioning and sole fleet writer. |
| B3 | [#31](https://github.com/ankit-suman-07/QA-SDV-Project/pull/31) | `36460f0` | Consistency verifier and vehicle-specific legacy context caller repair. |
| B1/B2 | [#30](https://github.com/ankit-suman-07/QA-SDV-Project/pull/30) | `fa65329` | Validated ordered ingress, atomic individual feature writes and safe provisioning. |
| B5 preparation | [#32](https://github.com/ankit-suman-07/QA-SDV-Project/pull/32) | `80a781f` | Static configuration/rendering preparation, not a completed runtime pilot. |
| E1 | [#33](https://github.com/ankit-suman-07/QA-SDV-Project/pull/33) | `5115168` | Two isolated edges, including QoS 1 correction `a3e20c1`. |
| E2 | [#37](https://github.com/ankit-suman-07/QA-SDV-Project/pull/37) | `3561c00` | Deterministic trajectory, provider identity enforcement and edge-cycle script. |

## MVP baseline and revision discrepancy

The November 7 baseline record describes a real single-vehicle simulator → KUKSA 0.7.0 → Velocitas → Mosquitto run on a MacBook Pro. Vehicle-001's legacy `sdv/autonomy/status` events changed HEALTHY → EMERGENCY_BRAKING → HEALTHY after direct simulator inject/clear commands. This is **LIVE-VERIFIED as reported historically**, qualified by the missing console log. It does not establish two-vehicle isolation, MQTT-to-Ditto propagation, live Spring Boot reads or fleet/dashboard agreement.

The older repository also contained a separate legacy KUKSA-to-Ditto bridge, backend/UI code and historical twin evidence. The [repository audit](2026-11-11-repository-audit.md) explains these disconnected paths. Their existence cannot be combined with the MQTT demo to invent one integrated MVP acceptance run. Development-generated backend values are not live telemetry evidence.

| Reference | History establishes | Remaining uncertainty |
|---|---|---|
| `098fd2ebf4fe04b08f0e965e494e03415b2aa673` in baseline.md | November 7, 01:39:13 −0500, “evidence folder created.” Direct child of `f06aa95`; adds evidence scaffolding only. The later baseline record identifies it as tested. | Original run log and clean-tree output are absent, preventing independent corroboration of that run SHA. |
| `f06aa9583d23d1aee0ff87313186d1398f05fe7a` in mvp-revision.txt | November 7, 01:06:47 −0500, “docs: add updated project documents.” The marker was created in `098fd2e` containing its parent's SHA, and has not changed since. | This explains the different references, but not whether the marker intended an official submission or simply then-current main. |
| Difference between those revisions | `git diff --name-only f06aa95 098fd2e` lists only evidence files. Their implementation code is identical. | This reduces implementation ambiguity; it does not make their run-provenance claims interchangeable. Both references are preserved. |
| `7736b6efbc94f855a61f9da1b9e8d28f6f1c8a54` | October 26 merge of #27, adding pipeline integration CI; baseline.md names it as a historical candidate. | Exact previous-term submission revision remains unresolved. |
| Timing CSV and `00984852c112535ef24530a1411f5ca536103019` | November 7, 20:21:47 −0500 commit adds the timing script, CSV and expanded baseline record together. Filename indicates November 8, 01:01:16 UTC. | Storage/commit time is not the tested revision. CSV contains no SHA, image digest or clean-tree record. Its tested revision is **NOT RECORDED**; assign none of these SHAs to it. |

The existing `v1.0.0-iteration3` tag points to `9b931d6b6aafd581789b22cc086d6175b8030ae5` (September 25). Its name does not establish a Phase V1 release or resolve the November rerun provenance.

## Capability comparison

| Dimension | Recorded MVP | Phase V1 at assessed main | Status and limitation |
|---|---|---|---|
| Functionality | Direct obstruction inject/clear with observed legacy braking/recovery for one vehicle. | Fixed vehicle-002 ladder `35 → 20 → 8 → 3 m`, observed warning/critical/recovery; provider identity rejection. | MVP LIVE-VERIFIED as reported, log missing. Phase V1 IMPLEMENTED + LIVE-VERIFIED at edge boundary; full V1-03 PENDING. |
| Vehicle count | One running synthetic edge. Registry/configuration extensibility did not prove multiple live edges. | Exactly two providers, KUKSA brokers and apps with separate identities/topics; shared MQTT. | IMPLEMENTED + LIVE-VERIFIED in E1/E2 captures. No third Phase V1 vehicle claimed. |
| Architecture | Real edge-to-MQTT path; separate legacy twin bridge and development-backed backend/UI paths. | Explicit edge → MQTT → validated ingress → Ditto → Spring Boot → fleet/dashboard boundaries with separate individual/fleet ownership. | Components IMPLEMENTED; joined live architecture PENDING. |
| Component integration | KUKSA/Velocitas/Mosquitto demonstrated together; this baseline rerun records no full twin/API chain. | E1 QoS 1 reaches actual subscriber with recording ingress; B1/B2 HTTP writes tested with substitutes; A2/A3/A5 use mock dependencies. | LIVE-VERIFIED edge/subscriber transport + MOCK-VERIFIED downstream boundaries; actual end-to-end persistence PENDING. PUBACK is not a Ditto commit. |
| APIs/dashboard | Legacy backend/pages existed, without this MQTT rerun proving their live data source. | Versioned vehicle state/health/list APIs, A3 action POST/lookup, fleet API/materialization and UI. | IMPLEMENTED + MOCK-VERIFIED with actual Java/browser; live twin/API/dashboard agreement PENDING. |
| Reliability | Reported baseline sequence and five passing timing trials, not a general reliability rate. | Schema/topic checks, isolated ordered writes, duplicate/late rejection, restart watermarks, bounded failures, source-age availability, PUBACK handling and reconnect paths. | IMPLEMENTED + MOCK-VERIFIED broadly; E1 records live broker outage recovery and provider-stop isolation. Real Ditto/session/backend outage acceptance PENDING. |
| Tests/CI | #27 added single-vehicle healthy/braking/recovery and nine live KUKSA signal checks; historical results separately reported. | Python/Java/configuration/image CI and preserved baseline pipeline pass on assessed main; E2 has an edge-cycle tool. | IMPLEMENTED; baseline CI LIVE-VERIFIED within that boundary; two-vehicle MQTT→Ditto→API/UI CI PENDING. Test-count changes prove neither causation nor quality improvement. |
| Specifications/skills | Older contracts/plans existed; comparable historical skill invocation evidence is NOT RECORDED. | Versioned C1–C10 development baseline, fixtures, substitutes, E1/E2 designs/plans and recorded red/green/review examples. | IMPLEMENTED + recorded use; complete provenance/owner review and V1-06 evidence PENDING. Customized-skill evaluation is not complete. |
| Performance | Five command-to-observed-MQTT fault/recovery completion trials, including scenario progression. | Edge captures and mock API/browser artifacts, without matched comparative timings or a live command-to-twin/API/dashboard dataset. | MVP recalculated below; Phase V1 comparative latency NOT MEASURED and existing observations NOT DIRECTLY COMPARABLE. |
| Deployment/release | Baseline instructions and reported local demo; exact previous-term submission unresolved. | Isolated Compose project, configurable endpoints and B5 static preparation. | IMPLEMENTED + static/MOCK-VERIFIED preparation; live Kanto V1-09 and tagged Phase V1 submission PENDING. CARLA/other Phase V2 delivery is not claimed. |

## Acceptance-to-evidence traceability

| Acceptance | Implementation | Evidence/status | Remaining gap |
|---|---|---|---|
| V1-01 | E1 #33; E2 #37 | IMPLEMENTED + LIVE-VERIFIED at recorded edge revisions: E1 24 events, later 16-message QoS capture, E2 36-event cycle. | Capture final integrated revision/configuration and downstream preservation of identity/source semantics. |
| V1-02 | #30/#31; QoS fix `a3e20c1` | IMPLEMENTED + MOCK-VERIFIED: [ingress](../../ditto/MQTT-INGRESS.md), [writer/provisioning](../../ditto/V1-TWINS.md), [B3](../../ditto/B3-HANDOFF.md). Actual subscriber transport has recording ingress, not real twin persistence. | PENDING: policies/authentication, two live twin writes, invalid-input invariance, failed-write acknowledgements and restart/session replay. |
| V1-03 | E2 #37 + A3 #35 + #30 + A2 #34 | LIVE-VERIFIED edge recovery; MOCK-VERIFIED Java dispatch/failures and twin projections. | PENDING: Spring Boot → actual providers → MQTT → twins → API/UI, with intermediate vehicle-001 isolation. Acceptance of dispatch is not recovery. |
| V1-04 | A2 #34; A5 #36 | IMPLEMENTED + MOCK-VERIFIED source age, missing/invalid/failed reads and no generated fallback. | PENDING: actual Ditto reads, disconnected-source/clock cases and source/event identity readback. |
| V1-05 | #25/#27 CI; component tests #30–#37 | Current-main CI and baseline pipeline green; historical records identify dependencies and partial runs. | PENDING: two-vehicle live acceptance CI. Deselected or dependency-blocked checks are not passes. |
| V1-06 | #29; A2/A3/A5 and E1/E2 records | Recorded requirement-driven red/green/review examples below. | PENDING: original-skill revision/license provenance, human affected-owner review and consolidated team traceability. |
| V1-07 | Setup guides, scripts and evidence | IMPLEMENTED reproduction material; earlier iteration tag exists. | PENDING: final Phase V1 SHA/tag, rerun evidence, report/video and contributions. |
| V1-08 | A5 #36 + A2 #34 + #30 | IMPLEMENTED + MOCK-VERIFIED fleet counts/UI/writer/failure recovery; result JSON and screenshot committed. | PENDING: real individual twins, materialized `sdv:fleet-v1`, API and dashboard agreeing through one live timeline. |
| V1-09 | B5 #32 + compatible E1 image | IMPLEMENTED + static/MOCK-VERIFIED [pilot preparation](../../velocitas-app/kanto/V1-PILOT.md). | PENDING: Linux/Kanto launch/restart and fresh source/event pair updating vehicle-002's live twin, with vehicle-001 isolated. |

Current-main [CI](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43555276190) and [pipeline integration](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43555276067) were observed successful for `3561c00`. Image publication also has successful runs; skipped publication triggers are not failed application tests. Workflow inspection shows the integration job still runs the single-vehicle demo and nine KUKSA checks, not full two-vehicle Ditto/backend/fleet acceptance.

## Performance: recalculation and comparison limits

All five CSV rows identify vehicle-001, contain fault/recovery values, have `result=pass` and empty errors. Values below divide milliseconds by 1000 and include every sample, including the first, slowest fault trial.

| Metric: command → observed MQTT completion | Samples | Median (s) | Minimum (s) | Maximum (s) | Recorded success |
|---|---:|---:|---:|---:|---|
| Inject obstruction → EMERGENCY_BRAKING | 5 | 12.075315 | 8.034951 | 42.426514 | 5/5 trials, 100% |
| Clear obstruction → HEALTHY | 5 | 10.063235 | 10.043413 | 16.097173 | 5/5 trials, 100% |

These are **command-to-observed-MQTT fault/recovery completion times, including scenario progression**, not pure transport latency. The committed [measurement script](../../scripts/run-autonomous-mvp-demo-measure.sh) starts one host monotonic clock immediately before the provider HTTP request and stops at receipt of a matching vehicle/status event. It includes scenario evolution, publication and observation delay; it measures no Ditto/API/dashboard completion. The sample success rate is not a fleet delivery-success estimate, and the CSV establishes no cause for the 42.426514-second trial.

The CSV lacks a tested revision, image digests and a complete environment/interval manifest. The separate baseline demo's MacBook description cannot supply all timing-run metadata. Storing script and CSV in `0098485` does not identify the working tree used for measurement.

| Desired comparison | Available Phase V1 data | Conclusion |
|---|---|---|
| Matched command→MQTT fault/recovery | No raw command-send/receive timing trials. E2 uses a fixed ladder instead of older randomized distance progression; vehicle count/publication contract differ. | **NOT MEASURED / NOT DIRECTLY COMPARABLE**; no numerical speedup/regression is justified. |
| New command→individual twin/API/dashboard completion | No joint live completion-time dataset. | **NOT MEASURED**; collect separately from comparative MQTT measurements. |
| Source→twin propagation, loss, freshness and CPU/memory under load | Component timeout assertions and configured intervals are not workload benchmarks. | **NOT MEASURED** for the integrated deployment. |

Event counts, capture duration, source-timestamp gaps, screenshots and configured 2/5-second intervals cannot substitute for end-to-end timing. Even the MVP CSV measures status completion rather than causal action-ID matching in MQTT; controlled comparisons must exclude unrelated publishers/actions. No historical result or causal improvement is inferred from larger test counts.

## How specifications and pre-prepared skills controlled development

The independent-development guide supplied canonical fixtures, fixed/rebased clocks, MQTT replay/capture and explicit HTTP substitutes. Owners could implement separate boundaries without importing unmerged teammate code. Checks using those substitutes remain MOCK-VERIFIED.

- **A2 / C5–C7:** [A2 evidence](../../evidence/v1/live-twin-api.md) records failing absent-route, invalid-calendar and configuration tests before correction. Final recorded verification: 124 Java tests and 12 packaged-Java→mock smoke checks. Local skill source SHA-256 values are recorded; upstream original commit/license equivalence is not claimed.
- **A3 / C8:** [A3 evidence](../../evidence/v1/scenario-routing.md) records a stalled-body timeout mapping defect and a mock provider rejecting streamed requests without Content-Length. Regressions preceded whole-exchange deadline and fixed-length-body fixes. Final recorded results: 183 Java tests and 13 Java→prepared-provider smoke checks. Acknowledged dispatch is explicitly separated from health completion.
- **A5 / C5–C7:** [A5 evidence](../../evidence/v1/fleet-dashboard.md) records a failing heartbeat test exposing synchronous fleet writes blocking legacy scheduling. Moving work to the owned executor was followed by nine passing focused scheduler/materializer tests. Final recorded results: 208 Java tests, seven frontend tests, 12 mock API/writer checks and nine Chrome checks.
- **E1 / C3:** [earlier #33 review](pr-33-review.md) demonstrated SDK QoS 0 rejection by ingress. The record then identifies test-first correction `a3e20c1`, QoS 1/retain false, PUBACK gating and positive/negative transport controls. [E1 design](../superpowers/specs/2026-11-11-v1-two-vehicle-edge-design.md) and [plan](../superpowers/plans/2026-11-11-v1-two-vehicle-edge.md) connect identity/classification requirements to tests.
- **E2 / C4/C8:** [E2 design](../superpowers/specs/2026-11-11-v1-lidar-scenarios-design.md), [plan](../superpowers/plans/2026-11-12-v1-lidar-scenarios.md) and evidence separate expected ladder values from observed events. Review exposed cleanup missing a possibly applied injection; `1b58120` corrected it, followed by bounded requests/clearer failures in `6ad55b4`.

[Skill usage](../../evidence/v1/skill-sources.md) attributes E1/E2 to Superpowers 6.4.2 and records owner design decisions, but says its exact upstream commit remains unpinned. A5 records repository copies at `2803429`. Missing `writing-good-tests.md` and debugging support files are explicitly not claimed as used. The global candidate table does not summarize every later per-task entry. Customized skills and matched original/customized evaluation are Phase V2 work, not completed results. These examples show recorded development controls, not a controlled causal estimate of skill effectiveness.

## Artifact audit and evidence limitations

Local link targets in the evidence index and all `evidence/v1` Markdown files were checked. The sole missing local Markdown target in that set is **`evidence/v1/mvp-demo.log`**. A filesystem search and `git log --all -- evidence/v1/mvp-demo.log` found no copy/tracked history at that path. The `*.log` ignore rule could explain an untracked log, but does not establish why it is missing. Historical “uploaded log” assertions are preserved, not independently verified console output.

- The index formerly named `09-project-scope-and-acceptance.md`; the actual file is [docs/08-project-scope-and-acceptance.md](../08-project-scope-and-acceptance.md). The architecture document retains its own pre-existing broken `09-project-scope-and-acceptance.md` link, flagged here rather than edited outside minimal index corrections. The old planned `docs/interface-contracts.md` is absent and explicitly replaced by the V1 contract.
- The October report's ChatGPT Library link is external, not an independently inspected repository artifact in this task. Its reported checks are not fresh verification.
- [E1 JSONL](../../evidence/v1/e1-capture-20261111T194542Z.jsonl) has 24 unique healthy events, 12 per vehicle, without QoS metadata. [Later QoS capture](../../evidence/v1/e1-qos-capture-20261114T0308Z.txt) has 16 messages, eight per vehicle, all QoS 1/retain 0. E1 separately reports 15 subscriber deliveries in an overlapping window; different observation boundaries do not prove 16 persisted writes.
- [E2 JSONL](../../evidence/v1/e2-capture-20261113T045301Z.jsonl) has 36 events, 18 per vehicle: 32 HEALTHY, two WARNING and two CRITICAL; vehicle-001 is always healthy. Its one `Timed out` diagnostic is documented and is not an event. Original runs were QoS 0; later QoS 1 reruns are described in the record, not encoded in this original capture. Other rerun/isolation/outage logs are not attached.
- [A5 API/writer JSON](../../evidence/v1/fleet-dashboard/mock-api-writer-result.json), [browser JSON](../../evidence/v1/fleet-dashboard/browser-result.json) and [screenshot](../../evidence/v1/fleet-dashboard/mock-fault.png) exist. The screenshot shows two available vehicles, one critical at 3 m, and a `mock-vehicle-002-*` event ID. They support MOCK-VERIFIED behavior, not real Ditto persistence. JSON records enumerate 12 API/writer checks and nine browser checks with no page errors.
- A2/A3 runtime logs/results and many A5 logs are referenced under `/tmp`, not committed. Their continued availability is NOT RECORDED; these are not durable release artifacts. Historical dependency-blocked runs remain partial even though later supported-host CI is green.
- The earlier #33 report assesses an old head's QoS defect; current main includes its correction. Do not treat that historical request-changes verdict as current code state. Conversely, merging the fix does not prove the joint live acceptance run occurred.

## Remaining Phase V1 acceptance work

1. Record affected-owner decisions and final source SHA, image digests, versions, identity/port mappings, clock assumptions and secret-free authentication subject mapping. Resolve the inherited tire-pressure kPa/legacy psi boundary with its owners; it remains a separate uncompleted fix, not proof of LiDAR failure.
2. Run the real two-edge → MQTT → ingress → Ditto → A2/A5 → dashboard chain, using Spring Boot for inject/clear. Capture healthy/fault/recovery intermediates and vehicle-001 isolation, not just a final healthy screenshot. Preserve known context and distinguish absent context from demonstrated command correlation.
3. Demonstrate malformed/unknown-input invariance, duplicate/equal/late handling, failed/uncertain-write acknowledgements, persisted watermarks, session recovery, source silence and truthful stale/unavailable views. Compare fleet Thing/API at a controlled evaluation boundary; verify the sole fleet writer.
4. Add/record repeatable two-vehicle live acceptance CI and baseline regression at the final revision, identifying actual dependencies, skips, failures and artifacts.
5. Complete separately tracked Linux/Kanto app-002 restart→fresh-event→live-twin evidence. Static descriptors or RUNNING state do not satisfy V1-09; avoid an unintended duplicate app-002 in the two-vehicle deployment.
6. Complete original-skill provenance, human review, a Phase V1 release tag, report/video and contributions. Recover the MVP log and clarify historical revisions if possible; otherwise preserve the limitations.
7. Collect matched command→MQTT trials only when a defensible comparison is possible. Separately measure new command→twin/API/dashboard completion and resource usage, retaining failures and raw samples. Do not invent historical metadata.

## Updating after the final live integrated run

1. Record assessment time, `git rev-parse HEAD`, clean/dirty state, image digests, versions, scenario/target/intervals and clocks. Save the approved contract/deployment manifest without credentials.
2. Add a dated run record and immutable raw files under existing `evidence/v1/`: commands/exit codes, command-send times, event/source IDs, contexts, individual/fleet Things, API responses, logs and screenshots/video. Mark mocks; preserve older CSVs/results.
3. For comparative MQTT timing, use one monotonic clock from immediately before command submission to observed status receipt. Document scenario/status/environment differences and every trial/failure. Instrument twin/API/dashboard completion separately; retain NOT DIRECTLY COMPARABLE when boundaries differ materially.
4. Recalculate statistics from raw data, correlate the timeline and map each criterion to exact files/revisions and dependencies. Update this report/index with dated notes. Promote only the verified boundary to LIVE-VERIFIED.
5. Check Markdown tables/fences and local links; run `git diff --check`. Keep unresolved provenance and historical missing/partial evidence visible.

Offline recalculation, from repository root (no experiment is run):

```bash
python3 -B - <<'PY'
import csv
from decimal import Decimal
from statistics import median
from pathlib import Path

path = Path('evidence/v1/mvp-timings-20261108T010116457743Z.csv')
rows = list(csv.DictReader(path.open()))
for field in ('fault_ms', 'recovery_ms'):
    values = [Decimal(row[field]) / 1000 for row in rows if row[field]]
    print(field, 'n=', len(values), 'median=', median(values),
          'min=', min(values), 'max=', max(values))
passed = sum(row['result'] == 'pass' for row in rows)
print('recorded trial success:', passed, '/', len(rows),
      '=', Decimal(passed) * 100 / len(rows), '%')
PY
```

This documentation task used Git/history/evidence inspection, offline CSV/capture/artifact analysis, local-link/Markdown checks and diff validation. No implementation files changed, services launched, experiments rerun, commits created or remote writes performed.
