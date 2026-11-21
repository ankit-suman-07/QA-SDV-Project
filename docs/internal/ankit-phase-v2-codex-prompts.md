# Ankit — Phase V2 copyable Codex prompts

Eight focused branches and PRs for Ankit's assigned work. Copy **one entire prompt** at a time. These prompts extend the existing project; they do not authorize merging, tagging or submitting.

Use the current repository documents if they differ from this planning snapshot. The contracts supplied for preparation were `2.0.0-prep.1`; proposed defaults require affected-owner review. Existing PRs may already satisfy portions: inspect and reuse rather than duplicate.

## Suggested order and dependencies

| Prompt | Depends on |
|---|---|
| 1 | Current shared preparation and source documents. |
| 2 | Agreed observation/companion boundary; fixtures allow independent mapping work. |
| 3 | Stable V2 contracts/individual-twin fixtures; real twins needed later. |
| 4 | Stable action/executor interfaces; project substitutes enable independent work. |
| 5 | Prompt 3/4 route contracts; reviewed implementations before joined UI acceptance. |
| 6 | Real owner components and runtime; missing components remain blocked gates. |
| 7 | Defined measurement method and an available verified runtime for live results. |
| 8 | Final implementation/evidence and explicit disposition of outstanding items. |

Recommended merge sequence: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**, subject to actual dependencies and required reviews. Prompts 2–4 can develop independently against frozen contracts, but do not silently import unmerged branches. Start each new branch from current main containing its required predecessors. A task may need multiple sessions on its **same branch/PR**; there is no guaranteed token or quota percentage.

Each prompt includes scope, Git authorization, verification and a stopping point. No extra generic prompt is needed. Keep report/video drafting in prompt 8 separate if it becomes substantial.

## 1. Contracts, baseline and customized skills

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/docs/v2-contracts-and-skill-baseline
PR TITLE: docs: align v2 contracts and ankit skill evaluation baseline
READ: docs/v2-independent-development.md, docs/v2-interface-contracts.md C1–C7, docs/v2-native-diagnostic-feasibility.md and the current V2 task/decision documents.

TASK:
Complete only the remaining Ankit preparation work; the shared prep package already exists, so inspect and reuse it.

1. Record current main SHA and the actual verified V1 reference, distinguishing historical implementation evidence from approvals. Reconcile ownership and source-index references with the current V2 plan. Do not alter historical V1 evidence.
2. Identify unresolved versus already specified decisions. Review observation identities/session registration, CARLA-time/UTC mapping, 10 Hz cadence/0.5 s gap defaults, dropout/recovery fields, freshness and diagnostic budgets against actual fixtures. These are prep defaults for review, not a license to invent approvals.
3. Propose and document one live observation-companion delivery binding for Ankit's adapter and Bayan's health consumer. Specify delivery/ordering/reconnect/silence behavior, configuration and matching KUKSA observation identity. Do not rely on cached value polling to prove fresh input. Use the existing allowed stream/file or versioned observation-MQTT boundary and affected-owner review rules; do not invent VSS paths.
4. Reuse the diagnostic project handoff while Bayan resolves native transport/provider bindings. Record required request/result mappings, permissions and deadlines; do not implement her native spikes or guess their APIs.
5. Before evaluated feature work, preserve original relevant skills/source/license, prepare justified Ankit customizations with actual course references, version/diff them, and define one small comparable original/customized evaluation case. If course material or a binding decision is missing, record the exact gap; do not fabricate it or restart all preparation.
6. Change contract, literal expected fixtures and substitute checks together only for a necessary authorized change. Run the existing offline preparation checks and relevant contract/link checks. No production services/builds are needed.

Deliver a concise decision/baseline record, versioned skill evaluation setup and precise pending owner decisions. Shared proposed bindings remain pending approval before dependent production integration. Finish unaffected work and open a reviewable PR rather than claiming every decision is closed.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 2. CARLA-observation to KUKSA adapter

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/feature/v2-observation-kuksa-adapter
PR TITLE: feat: publish validated v2 observations to per-vehicle kuksa
READ: docs/v2-interface-contracts.md C1–C4 and C7, docs/v2-independent-development.md and the reviewed companion-binding decision from prompt 1.

TASK:
Implement Ankit's publication adapter using Emmanuel's compact observations and shared replay fixtures. Do not build CARLA actors, LiDAR extraction or Velocitas health logic.

1. Inspect existing provider/publication code and fixture schemas. Add the smallest configurable ingestion/publication boundary for the three registered vehicle-to-broker mappings.
2. Validate complete observation shape, identity, session generation/registration expectations, ordering, source timestamp and processing time before side effects. Preserve source/event/frame/session context; never make replayed/cached input fresh by replacing source time with now.
3. Publish only the intended vehicle's VSS signals, respecting broker metadata/types. LiDAR distance is metres; invalid sensor input sets validity false without fabricated healthy distance. Speed comes from the agreed actual motion input in km/h; if velocity/speed is not in the current handoff, document and request the missing contract rather than invent a field. Battery %, temperature Celsius and uint16 whole-kPa tire pressure may remain explicitly SYNTHETIC; retain the existing legacy psi conversion where required.
4. Deliver the agreed observation companion so health code can associate new observations with KUKSA values. Specify publication order/partial failure behavior; do not imply atomic multi-channel writes without proof. Suppress false-new events on silence, reconnect or retry.
5. Test identities, units/types, malformed/nonfinite inputs, session/time errors, duplicate/retry behavior, cross-vehicle isolation, broker failure and companion failure. Use fake clients/replay and controlled clocks first.
6. Provide exact configuration and input/output examples for Emmanuel and Bayan. If an isolated real broker already exists, perform one scoped publication check; otherwise leave it pending for joined integration rather than installing CARLA.

Prerequisite: shared companion binding must be settled before dependent production wiring. Stop and identify that precise blocker if unresolved; pure validation/mapping work may still proceed. Do not claim live CARLA acceptance from fixture tests.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 3. Three-vehicle backend and fleet

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/feature/v2-backend-fleet
PR TITLE: feat: add three-vehicle v2 state and fleet projections
READ: docs/v2-interface-contracts.md C5–C7, docs/v2-independent-development.md and existing backend/read/fleet implementation.

TASK:
Implement backend production behavior against shared individual-twin fixtures/HTTP substitutes; the mock preview API is not the backend under test.

1. Add explicit V2 vehicle/state/fleet routes and registration for vehicle-001/002/003 as contracted. Preserve V1 endpoints, fixtures and the existing fleet-v1 migration boundary.
2. Read/validate actual individual V2 Thing state with configurable Ditto clients. Preserve source/session/event identity, health, recovery, faults and sourceSilent fields. Missing/untrusted known state returns explicit unavailable/null projection; unknown vehicle returns 404. No production mock fallback.
3. Evaluate source-derived freshness with injected clock and exact agreed boundaries. Keep stale last-known data labelled; sensor validity, health, silence and availability remain distinct.
4. Extend the sole Spring Boot aggregator/materializer to sdv:fleet-v2. Use one generatedAt and one derived summary for the fleet API and materialized snapshot. Always retain three sorted registered entries; availability counts sum to three and health counts include only AVAILABLE vehicles. Recovering entries retain fault severity.
5. Preserve individual/API reads on materialization failure. Do not add a second fleet engine, dual-write migration or modify Bayan's ingress/history.
6. Add focused Java/API tests for all three identities, healthy/fault/recovering/stale/unavailable cases, exact clock boundaries, malformed/read failure, counts and failed persistence. Keep existing HTTP compatibility and authentication safety regressions.

Use fixture-backed/component verification here; real twin/fleet agreement belongs to joined integration. Hand off concrete backend route/projection examples for the dashboard. Do not implement action tracking or UI in this PR.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 4. Diagnostic action tracking and adapters

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/feature/v2-diagnostic-action-tracking
PR TITLE: feat: track targeted v2 diagnostic action lifecycles
READ: docs/v2-interface-contracts.md C6–C7, docs/v2-native-diagnostic-feasibility.md, diagnostic fixtures and existing V1 scenario routing.

TASK:
Implement the backend action lifecycle independently using agreed executor interfaces and diagnostic substitutes. Reuse correct V1 routing.

1. Add the contracted V2 create/read-action routes with vehicleId/actionId/traceId, request validation and selected-target isolation. Identical action-ID retries return the existing record; conflicting reuse returns 409.
2. Route obstruction inject/clear only to the intended scenario provider. Route RESTART_APP only through an actual lifecycle-executor boundary, never a simulator endpoint that cannot restart an app. Provide a configurable adapter and fixture implementation if the live executor is unavailable; production mode fails explicitly instead of falling back.
3. Track ACCEPTED, EXECUTING and immutable SUCCEEDED/FAILED/TIMED_OUT outcomes using correlated executor evidence. Reject mismatched vehicle/action/trace results. Use the contract's bounded transport/execution budgets and record timeout uncertainty/late-result evidence without overwriting terminal outcomes.
4. Persist authoritative bounded action history/restart state as required by the contract; provide the agreed correlated history projection to Bayan. Avoid storing privileged credentials or building her independent-twin history implementation.
5. Keep clear-execution success separate from observed two-second health recovery. Restart success requires real lifecycle and a fresh post-start observation; an HTTP acknowledgement alone is insufficient.
6. Wire to the agreed callable health/fault diagnostic interfaces. Use project substitutes until Bayan supplies native implementations; do not invent native SDK operations or claim native exchanges.
7. Test accepted/executing/terminal states, ID reuse, malformed/unknown targets, rejection/unavailable/timeout, late/mismatched results, retention/restart and failed persistence with injected clocks. Document exact result/handoff contracts and production prerequisites.

Do not start CARLA/Kanto to validate pure lifecycle state logic. Live executor/native verification is a later gate and must remain explicit.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 5. Dashboard V2 integration

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/feature/v2-dashboard
PR TITLE: feat: display three-vehicle v2 health recovery and diagnostics
READ: docs/v2-interface-contracts.md C6, the merged backend/action route handoffs and existing frontend component/test conventions.

TASK:
Extend the current dashboard without a redesign.

1. Configure the explicit V2 backend base/routes and display exactly three registered vehicles, including missing/unavailable ones.
2. Display health, availability, faults, recovery state, source/event identity and required supporting telemetry/history according to the agreed API. Label synthetic provenance and stale values. Never render missing data as zero/healthy.
3. Show the backend fleet counts; do not create an independent client-side health/fleet decision engine. Handle independently sampled updates using the documented event/generatedAt boundaries.
4. Add selected-vehicle obstruction inject/clear and managed-restart controls through backend action routes. Render ACCEPTED/EXECUTING/terminal status and relevant failure messages; do not show success on dispatch alone. Keep clear action success distinct from observed health recovery.
5. Cover loading, unavailable/error, recovering, timeout/rejection and rapid selection changes so responses for one vehicle cannot overwrite another. Keep privileged Ditto/broker credentials out of the browser.
6. Add focused frontend tests with shared API fixtures/substitutes and one component/browser smoke when available. The real backend must be used for any claimed joined smoke; label mock preview screenshots clearly.

Depend on reviewed backend/action contracts; use their substitutes for independent development while implementation PRs are pending. Do not change backend schemas incidentally or implement native services. Preserve existing usable flows and provide a short manual click sequence for final integration.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 6. Joined integration and CI

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/test/v2-three-vehicle-integration
PR TITLE: test: verify real v2 pipeline and preserve regression ci
READ: docs/v2-independent-development.md, C1–C7, existing acceptance tooling, relevant component handoffs and runtime prerequisites.

TASK:
Integrate reviewed owner implementations. First inspect prerequisite PRs/components and existing environments; do not repeatedly build missing stacks or silently cherry-pick unfinished work.

1. Prepare a reproducible isolated/local configuration with pinned source/image versions, three mappings, configurable endpoints, secret handling and scoped cleanup. Coordinate LAN/TLS/clock assumptions if CARLA runs on another host. Preserve unrelated services and volumes.
2. Prove one real CARLA actor through adapter→KUKSA→Velocitas→MQTT→ingress→Ditto→Spring Boot→dashboard before expanding to all three. Distinguish unsupported/missing prerequisites from assertion failures.
3. Verify targeted obstruction/clear, two-second recovery, inter-vehicle isolation, dropout/silence, stale/unavailable behavior, input/order/session rejection, persisted-watermark restart and denied/failed writes. Compare source/event identities at documented observation boundaries; do not assume asynchronously sampled timestamps are equal.
4. Verify action success/failure/timeout with real executors, one actual native uProtocol health exchange and supported OpenSOVD fault read from Bayan's handoff. Serialization/mocks do not close these gates.
5. Coordinate Bayan's CARLA-backed Kanto evidence. Reuse valid exact-implementation evidence where applicable; run a new lifecycle check when integrated changes invalidate it. Verify no duplicate publisher and unaffected other vehicles; managed restart does not prove crash auto-restart.
6. Retain deterministic synthetic offline regression CI. Add the smallest relevant contract/component jobs. Resource-heavy CARLA/native acceptance may be a documented manual/explicit runner gate; never pretend hosted CI has unprovided GPU/runtime/secrets.
7. Save exact revisions, configuration, actual exits/results, selected raw correlated artifacts, browser checks and final service state. Report BLOCKED/SKIPPED/FAILED separately.

This PR owns integration tooling/tests, not a rewrite of teammates' components. If a defect is necessary to fix, keep it bounded and documented; split a substantial production change into an explicitly proposed follow-up instead of expanding indefinitely. Finish a reviewable harness/evidence PR even when some external gates remain truthfully blocked.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 7. Measurements, stage comparison and skill impact

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/test/v2-measurements-comparison
PR TITLE: test: record reproducible v2 measurements and stage comparison
READ: existing MVP/V1 baselines, docs/findings stage comparison, V2 acceptance evidence and Ankit skill evaluation records.

TASK:
Build on the verified integration harness; do not repeat all functional acceptance just to create tables.

1. Define measurement boundaries for source detection, propagation, observed recovery, delivery/update success and CPU/memory. Record workloads, three-vehicle scenario configuration, sampling/trial procedure, clock mapping/uncertainty and tested SHA.
2. Add only missing instrumentation/collection, preserving original source times and independent ground truth. Distinguish polling/scenario delays from pure transport latency. Count delivered/accepted/observed updates with defined denominators; QoS1 duplicates are not new observations.
3. Run a bounded set of repeated trials on an available agreed environment; retain raw values, failures/timeouts, sample counts and variability. State sample limits; do not report unsupported P95/P99 or infer speedups from unlike scenarios. Record CPU/memory measurement method and tool availability.
4. Create/update a concise MVP–V1–V2 comparison in docs/findings, linking durable evidence. Compare features, architecture and verification scope even when old timings are incomparable. Missing historical data remains missing; do not rerun a modern build and label it the original MVP.
5. Complete Ankit's planned original/customized skill evaluation on comparable starting code/tasks/acceptance. Preserve actual versions, model/tool settings, human intervention, outputs, corrections and defects caught. If a baseline run was not captured, record the limitation or perform a clearly dated bounded comparison now; never manufacture historical skill usage.
6. Store reviewed, secret-free raw data and calculation procedure; use tables/plots only when supported by actual measurements. Supply a rerun command and limitations.

If real runtime is unavailable, finish the collector/procedure and mark measurements pending. Do not substitute synthetic results for live performance or run open-ended benchmarking. Stop after this measurement/comparison PR; no release/tag.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

## 8. Final documentation and delivery readiness

```text
Read root AGENTS.md and docs/SOURCE-OF-TRUTH.md first, then only the relevant task/contract/code sections below. Preserve V1 and other owners' boundaries. Follow the current repository precedence if a documented decision changed; identify actual conflicts rather than silently choosing incompatible behavior.

GIT: Inspect status/branch and existing local/remote task branch and PR. Preserve unrelated changes. For new work: fetch origin, update main with --ff-only, create the branch named below and record starting SHA. For continuation, reuse its branch/PR. Check required predecessors; never force-push/reset main or import unmerged teammate commits. If main cannot update safely, report the precise blocker. Make logical checkpoint commits; push and create/update ONE draft PR against main using the title below. Use the repo PR template, actual checks/evidence and dependencies. No merge/tag/release/submission.

EFFICIENCY: Implement only this prompt. Reuse documented design, fixtures, skills and existing code; no unrelated refactor/upgrades. Use focused searches/log excerpts and tests first, plus required broader checks for affected code. Do not rerun unchanged exact-revision checks unnecessarily or start heavy services for offline work. Use relevant versioned customized skills and record actual usage. No extra agents unless explicitly requested. Do not skip necessary verification to save credits.

BRANCH: ankit/docs/v2-final-delivery
PR TITLE: docs: consolidate v2 delivery evidence and release readiness
READ: current source index, V2 task acceptance, merged implementation/evidence, current setup/README and report requirements.

TASK:
Consolidate final delivery from actual evidence without inventing completion.

1. Update the acceptance/traceability matrix and evidence index with exact implementation/tested SHAs, PRs, CI run/artifact references, limitations and real versus substituted boundaries. Check current main implementation equivalence after merges; rerun only invalidated or required gates.
2. Update concise README/architecture/setup/scenario instructions for the actual supported local deployment. Clearly distinguish Windows/macOS component development from Linux Kanto and real CARLA host requirements. Reuse existing documentation rather than create competing guides.
3. Consolidate actual contribution statements, affected-owner decisions/reviews, authentication/timing/LAN qualifications and customized-skill evidence. Do not infer approval from merged PRs.
4. Prepare an editable final report draft and a timed demo/voiceover checklist referencing real features/evidence, according to recorded assignment requirements. Produce a document format only if requested/required and supported; do not install large tooling merely to convert an otherwise usable Markdown draft. Leave missing human narrative, video link or approval explicitly marked. Do not claim a video was recorded/uploaded or submit anything.
5. Provide a release-readiness checklist identifying completed, blocked and human-required items. Recommend a candidate SHA/tag only after checking required fixes/evidence; do not create the tag/release or merge this PR.
6. Run link/format/diff checks and review artifact secrets. No CARLA/full-suite rerun for documentation-only changes unless evidence is stale or a required release check is unresolved.

Finish with the exact remaining human actions and a concise handoff. A documentation PR does not itself establish full V2 acceptance. Do not alter historical MVP/V1 results or erase failed runs.

FINISH: Record focused secret-free evidence using the existing evidence layout (prefer evidence/v2/ankit/<task>/README.md if none exists), exact tested revision, commands/results and limitations. Distinguish mocks/replay/component/live results; skipped or blocked is not passed. Run git diff --check and required checks, self-review, then push/open or update the draft PR. Keep the PR body in a file with --body-file when using gh. If GitHub/auth/network blocks this, retain commits and exact next commands; do not claim a PR exists.

Stop after this task. Return branch, head SHA, PR link, concise changes, executed checks and pending gates. If the session must end earlier, save a small persistent handoff with completed work, next steps and owned services left running, and keep unfinished work draft. Do not proceed to the next prompt automatically.
```

