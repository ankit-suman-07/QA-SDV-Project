# SDV fleet enhancement — Detailed task distribution

Phase V1 is due **November 16, 2026** and covers approximately 60% of remaining effort with two synthetic vehicles. Phase V2 is due **December 5, 2026** and covers the remaining 40%, including three CARLA vehicles with front LiDAR. Task IDs below map to acceptance criteria in [08-project-scope-and-acceptance.md](08-project-scope-and-acceptance.md). For tasks moved earlier, use the phase assignments in this document. Runtime flows are in [09-architecture-diagrams.md](09-architecture-diagrams.md).


## Contract-first V1 development baseline

Updated November 11, 2026 at the project owner's request. [V1 interface contracts](v1-interface-contracts.md) version 1.0.0 is **proposed for affected-owner review**, with runnable development fixtures/mocks. See [independent development](v1-independent-development.md) for setup, exact commands and environment verification status. The formerly planned `docs/interface-contracts.md` is missing; the new V1 document fills that role. The scope's historical approval provenance is still unconfirmed; this document does not claim approval or feature completion.

**Explicit responsibility adjustment:** Ankit owns fleet aggregation in Spring Boot and writes the same derived summary to the required fleet twin under A5. Bayan's B3 retains its task ID and becomes individual-twin consistency plus aggregation handoff. There is one aggregation implementation. This supersedes earlier B3 ownership, preserves the fleet-twin scope requirement and does not remove any V1 acceptance criterion.

Every V1 component can be implemented and verified against the shared fixtures and local tools without another developer's unmerged branch or running service. Contract review is a shared prerequisite; live integration is a later team activity. “Independently ready” below means component implementation plus mock-based verification, **not** live V1 acceptance or merged completion. Kanto runtime evidence, actual skill use, baseline regression, fleet CI, tagged release, report and video remain required.

| Developer | Develop real components against | Substitute supplied here |
|---|---|---|
| Ankit | Ditto reads, two provider targets, API/UI contracts | HTTP Ditto/provider mocks and backend preview, fixed test clock, fleet fixtures |
| Bayan | MQTT input and individual-twin schemas | MQTT fixture publisher, negative replay, Ditto fixtures and own local Ditto or feature-write mock |
| Emmanuel | Synthetic providers, KUKSA and Velocitas | MQTT capture/validation oracle, cycle expectations and deterministic observations |

No networked uProtocol or V2 CARLA work is a V1 dependency. Production files are assigned below; the preparation PR changes none of their behavior. All owners retain responsibility for actual use of pre-prepared skills, component tests, affected-consumer review and evidence.

## Ankit — Architecture, Spring Boot integration and quality

| Task | Work | Done when |
|---|---|---|
| A1 · Phase V1 contracts | Lead agreement on vehicle-to-provider/broker/twin mappings, event payloads, health states, API responses and fault/clear requests. Give both teammates sample payloads and expected results. | The team approves examples for normal, fault and recovery states and can develop against them independently. |
| A2 · Phase V1 live state API | Add or connect the Ditto client and expose vehicle-specific health through Spring Boot. Use source timestamps to distinguish fresh, stale and missing state. | API responses match live Ditto for both vehicles, including a stale or unavailable source case. Covers V1-04. |
| A3 · Phase V1 scenario routing | Route inject/clear requests by registered vehicle ID to Emmanuel’s provider endpoints. Validate unsupported vehicles/actions and surface failures. | A request for vehicle-002 reaches only its provider. Rejection and provider failure have observable outcomes. Supports V1-03. |
| A4 · Phase V1 integration and submission | Assemble the local stack with both owners. Run the baseline regression and add a repeatable two-vehicle fault/clear check to CI. Capture API responses, twin state and correlated events. Tag Phase V1 and coordinate the video and report. | Vehicle-002 changes healthy → fault → healthy. Vehicle-001 stays healthy. Record the exact commands, revision and test/CI results. Covers V1-03, V1-05 and V1-07. |
| A5 · Phase V1 fleet views | Own the sole fleet aggregation implementation in Spring Boot, its fleet-twin materialization, fleet API and basic dashboard. Show health, availability and active faults. | Dashboard, API and materialized fleet twin agree with both live individual twins during fault and recovery. Covers V1-08. |
| A6 · Phase V2 diagnostic backend | Define the request/result contract with Bayan. Validate dashboard requests, route to the agreed diagnostic service and correlate acceptance, execution result, timeout and failure using vehicle/action/trace IDs. | A selected action reaches the correct vehicle, produces observable execution evidence and shows its outcome on the dashboard. Covers V2-04. |
| A7 · Phase V2 evaluation and release | Own system integration, CI and repeatable measurements. Collect detection, propagation and recovery timings and resource use under recorded workloads. Compare MVP, Phase V1 and Phase V2 and consolidate the report. | A clean local rerun reproduces the demo and recorded measurements. Tests and reports label synthetic, mocked and live evidence. Covers V2-08. |

## Bayan — Messaging, Ditto and edge deployment

| Task | Work | Done when |
|---|---|---|
| B1 · Phase V1 MQTT ingress | Subscribe to Velocitas events through Mosquitto. Validate identity and required fields and preserve event ID and source time. Coordinate sample events with Emmanuel. | A valid event reaches the bridge. Malformed events and unknown IDs cannot alter either twin. |
| B2 · Phase V1 twin routing | Provision two live Ditto twins. Map vehicle IDs to twin IDs and write the agreed health/fault fields. Give Ankit twin IDs, read examples and startup instructions. | Events for both vehicles land in their respective twins. A vehicle-002 fault and clear update only its fault state. Covers V1-02 and supports V1-03. |
| B3 · Phase V1 twin consistency and aggregation handoff | Verify both individual twins with replayed events and hand their schemas/read examples to Ankit. Ankit owns aggregation under A5; do not build a second aggregator. | Individual twin isolation/freshness/ordering checks pass independently; Ankit can consume their fixtures and read contract. Supports V1-02, V1-04 and V1-08. |
| B6 · Phase V2 fleet extension | Provision the third individual twin, add fault history and handle duplicate and out-of-order events. Hand the third twin to Ankit for extension of the single Spring Boot aggregator. | Three individual twins and fleet counts agree. Duplicate and late events preserve newer state. Supports V2-03. |
| B4 · Phase V2 diagnostics integration | With Ankit, select one real uProtocol exchange and one supported OpenSOVD operation. Document addressing, request/result mapping and correlation. Capture runtime evidence for each. | Both agreed operations execute against their selected implementations. Record exact operations, failure handling and any adapter limitations. Covers V2-06. |
| B5 · Phase V1 Kanto pilot | Launch and restart the vehicle-002 Velocitas app with Kanto on Bayan’s Linux device. Connect it to KUKSA and Mosquitto using the main host’s LAN address. | A fresh event reaches the correct Ditto twin after restart. Save Kanto and twin evidence. |
| B7 · Phase V2 Kanto validation | Repeat deployment and restart verification with the CARLA-backed fleet. | A fresh post-restart event reaches the selected CARLA vehicle twin. Covers V2-05. |

## Emmanuel — Simulation, LiDAR and Velocitas

| Task | Work | Done when |
|---|---|---|
| E1 · Phase V1 two-vehicle edge | Configure two synthetic providers, two KUKSA brokers and two Velocitas apps. Assign unique IDs and non-conflicting endpoints. Document the signal fields and units. | Both edge instances publish independently and their events carry the agreed vehicle IDs. Covers V1-01. |
| E2 · Phase V1 fault and clear | Supply a deterministic LiDAR fault/clear scenario for vehicle-002 and give Ankit the provider command contract. Give Bayan examples of the healthy, fault and recovery events. | The scenario can be rerun locally. Vehicle-002 emits the expected transitions and vehicle-001 receives no injected fault. Supports V1-03. |
| E3 · Phase V2 CARLA adapter | Set up CARLA and its Python adapter on a separate GPU-capable host if available. Validate one actor first, then connect three actors with front LiDAR to their respective edge instances. Preserve actor/vehicle mapping, source timestamps, units and labelled injection timing. Document startup and cleanup. | All three vehicles publish identifiable LiDAR observations through their correct brokers. A reproducible configuration and runtime evidence cover V2-01. |
| E4 · Phase V2 sensor diagnosis | Implement controlled degradation and dropout scenarios. In Velocitas, evaluate observation age and agreed health thresholds, then apply the recovery window once valid input resumes. | Labelled runs and boundary tests establish when a fault is raised and cleared, with other vehicles unaffected. Covers V2-02. |
| E5 · Phase V2 runtime handoff | Give Bayan the app build/configuration and Ankit the scenario commands, ground truth and runtime observations. Keep the synthetic scenario available for CI and comparison. | Both teammates can reproduce a fault and recovery with documented inputs and identify the source of each measured transition. |

## Real integration order and reviews

1. **Phase V1 contracts first.** Ankit coordinates. Emmanuel supplies publisher and simulator examples. Bayan supplies twin IDs and a representative read response. Agree the command, event and state fields before connecting services.
2. **Phase V1 build independently.** Emmanuel uses capture, Bayan uses fixture replay and Ankit uses HTTP mocks; no member waits for a teammate service. Component PRs are reviewed against the same contract. Then substitute real endpoints and run the live fault/clear scenario before recording. Bayan can validate the Kanto pilot in parallel. Preserve the core two-vehicle demo if the Linux or LAN setup blocks the pilot.
3. **Phase V2 validate the runtime early.** Emmanuel verifies CARLA and LiDAR acquisition. Bayan reuses the Phase V1 Kanto deployment and identifies supported diagnostic operations. Ankit freezes backend contracts once those interfaces are clear.
4. **Phase V2 integrate telemetry before actions.** Prove three-vehicle telemetry and fleet views, then verify targeted diagnostic outcomes and Kanto restart. Run measurement trials after the integrated workflow is repeatable.
5. **Review at handoffs.** Bayan reviews Emmanuel’s event contract, Ankit reviews Bayan’s twin/diagnostic interface, and Emmanuel reviews Ankit’s scenario targeting. Each owner verifies their component. Ankit coordinates cross-system acceptance.

## Evidence and spec-driven development

Save evidence under `evidence/v1/` and `evidence/v2/`. Each owner adds a short entry with the task/acceptance ID, PR or commit, reproduction command, expected and observed result, and a log, CI or demo link. Use [evidence/README.md](../evidence/README.md) as the index. Ankit consolidates the reports and records gaps or partial results explicitly.

For Phase V1, each teammate records an actual use of a pre-prepared skill, its source/version, the acceptance criteria, and how they reviewed and verified the output. For Phase V2, record a customized skill diff, course concept and comparable original/customized evaluation. Track which checks caught meaningful defects or changed the result. These entries support V1-06 and V2-07.

The exact uProtocol exchange and OpenSOVD operation are Phase V2 contract decisions. Report synthetic fallback and Docker-only runs as partial evidence for CARLA and Kanto respectively. Beam remains optional.

## V1 task cards — independently executable

Each card uses only the merged contract package, the owner’s own code and listed local substitutes for individual implementation/verification. Paths containing `...` name existing backend package areas, not literal directories. Commands and availability limitations are in the development guide.

### A1 — Shared contract coordination and backend contracts

- **Owner:** Ankit
- **Objective:** Shared contract coordination and backend contracts
- **Files/components likely involved:** docs/v1-interface-contracts.md; docs/SOURCE-OF-TRUTH.md; shared fixtures and contract tests
- **Inputs required:** Current specifications, audit, user decisions; fixture epoch and expected transitions
- **Shared contract references:** C1–C10
- **Mock or fixture to use:** All tests/fixtures/v1 JSON; scripts/v1_dev/contract.py
- **Independent implementation steps:** Review identity/units/health/error examples; record approved revision and unresolved proposals; freeze sample envelopes and backend DTOs with affected-owner review.
- **Independent tests:** Run test_v1_contracts.py and documentation checks; verify negative fixtures and every V1 card.
- **Completion criteria:** All owners can develop from one reviewed contract and fixtures; pending approvals are explicit.
- **Evidence to capture:** Spec revision, reviewers, actual skill source/version/use, rejected assumptions and requirement→test mapping.
- **Real integration handoff:** Publish reviewed contract in merged preparation PR; no runtime service needed for review.
- **Acceptance criteria mapping:** V1-01–V1-09 (coordination); V1-06

### A2 — Read live Ditto state through vehicle APIs with truthful freshness

- **Owner:** Ankit
- **Objective:** Read live Ditto state through vehicle APIs with truthful freshness
- **Files/components likely involved:** backend/.../adapter/ditto; provider; service; controller; DTO/configuration and tests
- **Inputs required:** C6 twin fixtures, configurable mock Ditto URL and injected UTC clock
- **Shared contract references:** C2, C5–C7, C9
- **Mock or fixture to use:** HTTP mock Ditto on 19080; ditto-vehicle-001.json, ditto-vehicle-002.json; /_mock state/clock controls
- **Independent implementation steps:** Implement explicit live/mock profiles and identity-checked reads; preserve source time; add v1 projections while retaining legacy APIs; reject unsupported live mode and remove any silent healthy fallback.
- **Independent tests:** Use MockRestServiceServer plus whole-Thing fixtures; test stale/missing/503/wrong identity and vehicle independence; run test_v1_contracts.py.
- **Completion criteria:** Mock cases pass and live adapter is ready for endpoint substitution; full acceptance still requires comparison with real twins.
- **Evidence to capture:** Mock/live labels, API samples for all availability states, test command/results and clock settings.
- **Real integration handoff:** Replace mock base URL with Bayan’s configured shared Ditto; compare both views and disconnect one source.
- **Acceptance criteria mapping:** V1-04; supports V1-03 and V1-08

### A3 — Vehicle-specific scenario dispatch and honest failure reporting

- **Owner:** Ankit
- **Objective:** Vehicle-specific scenario dispatch and honest failure reporting
- **Files/components likely involved:** backend/.../adapter/simulator; registry/configuration; diagnostic DTO/service/controller; tests
- **Inputs required:** Provider mapping and C8 request/response/error examples
- **Shared contract references:** C2, C8–C9
- **Mock or fixture to use:** Two HTTP provider mocks on 19091/19092; scenario-inject-request.json and scenario-clear-request.json
- **Independent implementation steps:** Add LiDAR scenario without removing cooling; route by allowlisted vehicle; verify provider response identity; distinguish local validation, rejection, failure and timeout; retain action/trace IDs and failed dispatch records.
- **Independent tests:** Exercise each provider separately; rejection/timeout/disconnect plus an unused port; assert only vehicle-002 receives its action and vehicle-001 stays healthy.
- **Completion criteria:** All independent routing/failure tests pass; 202 never implies a fault or completed execution.
- **Evidence to capture:** Target URLs without secrets, action/trace IDs, dispatch outcomes, isolated request logs and test results.
- **Real integration handoff:** Swap mappings to Emmanuel’s two providers; verify context GET and observed telemetry after inject/clear.
- **Acceptance criteria mapping:** V1-03; supports V1-04 and V1-05

### A4 — Integration harness, fleet CI and V1 submission

- **Owner:** Ankit
- **Objective:** Integration harness, fleet CI and V1 submission
- **Files/components likely involved:** scripts/ acceptance harness; .github/workflows; evidence/v1; release/report instructions
- **Inputs required:** Reviewed contracts, canned MQTT capture, mock HTTP endpoints; no teammate branch required to author harness
- **Shared contract references:** C1–C10
- **Mock or fixture to use:** cycle replay/render/check; HTTP mocks; all fixture states and negative cases
- **Independent implementation steps:** Author harness assertions and CI steps against deterministic substitutes first; keep mock and live jobs/results separate; preserve single-vehicle baseline; prepare release/video/report/evidence checklist.
- **Independent tests:** Run standard-library suite and offline cycle; dry-run mock HTTP acceptance logic; test that intentional cross-vehicle corruption fails; validate CI configuration.
- **Completion criteria:** Harness and submission scaffolding independently ready; live acceptance/CI/tag/video/report still required before V1 completion.
- **Evidence to capture:** Exact Git revision, dependency coverage table, commands/exits, transition timeline, CI URLs, actual skill reviews and contributions.
- **Real integration handoff:** After component PRs are ready, run real two-vehicle scenario plus baseline and all V1 criteria; coordinate tag/submission.
- **Acceptance criteria mapping:** V1-03, V1-05, V1-06, V1-07; coordinate V1-08/V1-09

### A5 — Single Spring Boot fleet aggregator, fleet twin and dashboard

- **Owner:** Ankit
- **Objective:** Single Spring Boot fleet aggregator, fleet twin and dashboard
- **Files/components likely involved:** backend fleet service/controller/DTO/configuration; frontend API/config/dashboard; fleet-twin provisioning
- **Inputs required:** Two whole-Thing fixtures, C7 counting rules and preview API; injected clock
- **Shared contract references:** C1–C2, C5–C7, C9
- **Mock or fixture to use:** fleet-summary.json; HTTP mocks; mock backend preview on 19082 for UI scaffolding
- **Independent implementation steps:** Implement one aggregate from both individual reads using one evaluation time; keep missing vehicles in denominator; materialize same summary to sdv:fleet-v1; add fleet/selection/availability UI without a second aggregation implementation.
- **Independent tests:** Test all-health combinations, stale/unknown/failure counts, independent outages and materialization failures; develop UI with preview before own backend is ready.
- **Completion criteria:** Mock API/UI/counting checks pass, fleet writer is ready; real dashboard/API/individual and fleet twin agreement remains pending.
- **Evidence to capture:** Count invariants, screenshots clearly labelled mock, fleet-twin payload and failure logs.
- **Real integration handoff:** Replace preview with own Spring Boot and mock Ditto with real twins; compare API/UI/fleet twin in fault and recovery.
- **Acceptance criteria mapping:** V1-08; supports V1-03, V1-04 and V1-05

### B1 — MQTT ingress validation and ordered ingestion

- **Owner:** Bayan
- **Objective:** MQTT ingress validation and ordered ingestion
- **Files/components likely involved:** New MQTT ingress module under ditto/; contract tests; local configuration
- **Inputs required:** C3 topics/schema/negative cases and C4 classification; own broker only
- **Shared contract references:** C2–C6, C9
- **Mock or fixture to use:** scripts/v1_dev/mqtt.py publish; healthy/cycle/malformed/unknown/out-of-order replay
- **Independent implementation steps:** Subscribe with allowlist validation; preserve event/source IDs; reject before mutation; serialize per vehicle; reconnect safely; load per-vehicle watermark from existing twin and advance only on successful write.
- **Independent tests:** Replay positive/negative events using own broker and stub twin writer; assert no writes on malformed/unknown/duplicate/late input and one vehicle continues during another failure.
- **Completion criteria:** Ingress independently ready from replayed events; no Emmanuel pipeline required; live event-to-twin proof remains pending.
- **Evidence to capture:** Sample accepted/rejected payloads, codes, ordering/reconnect logs, fixture IDs and mocked dependency table.
- **Real integration handoff:** Replace replay with Emmanuel’s v1 publisher on same topics; verify live twin invariance for invalid inputs.
- **Acceptance criteria mapping:** V1-02; supports V1-03 and V1-05

### B2 — Two individually isolated Ditto twins and atomic feature updates

- **Owner:** Bayan
- **Objective:** Two individually isolated Ditto twins and atomic feature updates
- **Files/components likely involved:** ditto/config; MQTT writer/HTTP adapter; twin tests and provisioning instructions
- **Inputs required:** C6 Thing IDs/property paths and event/twin fixtures; own local Ditto or mock feature writer
- **Shared contract references:** C2–C3, C5–C6, C9
- **Mock or fixture to use:** ditto-vehicle-001.json / ditto-vehicle-002.json; MQTT cycle replay; HTTP mock feature PUT/GET
- **Independent implementation steps:** Provision own policies/twins; map vehicle→Thing; write one v1 feature snapshot per event without overwriting legacy features; preserve source/context; implement bounded failure/restart behavior.
- **Independent tests:** Use fixture replay with mock writer first, then own Ditto; compare both twins after every event, failed write and restart; validate current event ordering and identity.
- **Completion criteria:** Twin provisioning/writer tests independently pass; real pipeline acceptance separately recorded.
- **Evidence to capture:** Whole-Thing reads, atomic write payloads, policy setup, source/event/context IDs and failed-write results.
- **Real integration handoff:** Provide Ankit exact read URL/schema/auth configuration without secrets and Emmanuel event-validation feedback.
- **Acceptance criteria mapping:** V1-02; supports V1-03, V1-04 and V1-08

### B3 — Individual-twin consistency and aggregation handoff, without duplicate aggregation

- **Owner:** Bayan
- **Objective:** Individual-twin consistency and aggregation handoff, without duplicate aggregation
- **Files/components likely involved:** ditto/scripts/verify-vehicle-state.py; twin verifier tests; ditto legacy bridge/context caller; docs handoff
- **Inputs required:** Twin fixtures, controllable clock, C3/C5 ordering/freshness and audit defect examples
- **Shared contract references:** C3, C5–C7, C9
- **Mock or fixture to use:** HTTP mock twin states; stale fixture; malformed/out-of-order replay; legacy verifier fixtures
- **Independent implementation steps:** Repair verifier partial-recovery/timezone/source-freshness defects in owned PR; fix legacy unscoped scenario-context caller; verify individual twin invariants; supply agreed reads to Ankit; do not implement a fleet aggregator.
- **Independent tests:** Test valid partial cooling recovery, missing/invalid/naive/future timestamps, fresh processing with old source, unknown/mismatched identity and unchanged other twin.
- **Completion criteria:** Individual consistency and handoff checks pass independently; Ankit consumes the same fixtures and owns counting/materialization.
- **Evidence to capture:** Regression reproduction, verifier output, fixture/read examples, source clock and requirement-to-test links.
- **Real integration handoff:** Compare verifier with real twin snapshots; review Ankit’s A2/A5 consumption and clock semantics.
- **Acceptance criteria mapping:** V1-02, V1-04; supports V1-05 and V1-08

### B5 — Kanto vehicle-002 Linux pilot and fresh post-restart event evidence

- **Owner:** Bayan
- **Objective:** Kanto vehicle-002 Linux pilot and fresh post-restart event evidence
- **Files/components likely involved:** velocitas-app/kanto descriptor/deploy script and static tests; local endpoint configuration
- **Inputs required:** C2 endpoint mapping, app image/config, own Linux/Kanto host; no teammate service needed for preparation
- **Shared contract references:** C2–C5, C9–C10
- **Mock or fixture to use:** MQTT capture; replayed cycle for oracle rehearsal; own isolated KUKSA/Mosquitto and deterministic signal feeder when testing Kanto locally
- **Independent implementation steps:** Parameterize descriptor for vehicle-002 and configured LAN endpoints; prepare restart/capture instructions and static tests without a teammate deployment; rehearse observer against replay; test own Linux runtime when available.
- **Independent tests:** Run descriptor tests and capture checks; validate image/vehicle/host-port settings; on own Linux verify restart emits a new source timestamp/event ID.
- **Completion criteria:** Config/oracle can be independently ready; Linux restart→fresh MQTT→live twin evidence is still required, separately tracked if blocked.
- **Evidence to capture:** Linux/Kanto/image versions, descriptor, launch/restart logs, before/after IDs/source times and eventual twin update.
- **Real integration handoff:** Run app-002 against real mapped broker/MQTT; Bayan’s ingress must update sdv:vehicle-002 after restart while vehicle-001 stays isolated.
- **Acceptance criteria mapping:** V1-09; supports V1-01, V1-02 and V1-07

### E1 — Two independent providers, brokers and Velocitas v1 publications

- **Owner:** Emmanuel
- **Objective:** Two independent providers, brokers and Velocitas v1 publications
- **Files/components likely involved:** vehicle-simulator/docker-compose.yml; src/config/tests; velocitas-app/app/src, manifest/config/tests
- **Inputs required:** C2 mappings, C3 envelope, preserved C4 thresholds and capture oracle
- **Shared contract references:** C1–C5, C9
- **Mock or fixture to use:** Mock MQTT subscriber/capture and event fixtures; isolated development broker; no Ditto/backend required
- **Independent implementation steps:** Add two configurable edge instances without port collisions; retain existing baseline; publish versioned per-vehicle events with original observation time and unique IDs; Velocitas classifies observations; fix owned source-time and VSS/provider unit boundaries.
- **Independent tests:** Run own simulator/KUKSA/app tests; capture both topics; test threshold boundaries, identity, unit conversion, unavailable sensor and preserved source time rather than poll time.
- **Completion criteria:** Both edge stacks independently publish contract-valid observations/events; captured mock-tool evidence alone does not satisfy live twin/API acceptance.
- **Evidence to capture:** Deployment/config versions, nine-signal checks, units, raw observations/event IDs/timestamps and capture logs.
- **Real integration handoff:** Connect publications to Bayan’s consumer on shared broker without changing topic/schema; give Ankit provider mappings.
- **Acceptance criteria mapping:** V1-01; supports V1-02, V1-03, V1-05 and V1-09

### E2 — Deterministic vehicle-002 LiDAR obstruction and recovery

- **Owner:** Emmanuel
- **Objective:** Deterministic vehicle-002 LiDAR obstruction and recovery
- **Files/components likely involved:** vehicle-simulator scenario_controller/control_server/signal_generator and tests; Velocitas health tests
- **Inputs required:** C8 existing provider routes, scenario fixtures, controlled source clock/seed and capture oracle
- **Shared contract references:** C2–C5, C8–C9
- **Mock or fixture to use:** scenario-inject/clear JSON; MQTT capture --expect-cycle; known healthy/fault/recovery observations
- **Independent implementation steps:** Enforce provider configured identity; implement deterministic input progression or fixed seed; retain tested 10 m/5 m boundaries; preserve context IDs and correct vehicle-specific context GET; ensure clear restores valid observations; never use scenario label as health ground truth.
- **Independent tests:** Inject/clear own provider directly with action/trace IDs; capture vehicle-002 healthy→critical obstruction→healthy; verify vehicle-001 remains healthy; reject wrong vehicle and unsupported action.
- **Completion criteria:** Repeatable isolated edge cycle passes without Spring Boot or Ditto; acceptance later repeats through backend control entry point.
- **Evidence to capture:** Seed/timing/ground truth separate from observations, provider responses/context, captured transitions and unaffected vehicle-001.
- **Real integration handoff:** Give Ankit provider command/read examples; give Bayan captured v1 events; jointly run Spring Boot-driven scenario.
- **Acceptance criteria mapping:** V1-03; supports V1-01, V1-02 and V1-05

## Baseline defect ownership

These are assigned implementation tasks, not fixes delivered by the contract package. Preserve legacy tests while adding regressions.

| Defect | Accountable owner/task | Boundary and independent verification |
|---|---|---|
| Broken scenario-context API integration | Bayan B3: legacy Python caller; Emmanuel E2: provider route; Ankit A3: Java mapping | Use actual vehicle-specific context GET, fixed action/trace IDs and local HTTP mocks; do not restore the obsolete unscoped route silently. |
| Tire-pressure units mismatch | Emmanuel E1: VSS/provider; Bayan B2/B3: legacy psi conversion/mapper agreement | VSS declares kPa; explicit boundary conversion and reviewed threshold units; deterministic tests independent of another branch. |
| Source timestamps and freshness | Emmanuel E1/E2: observation source; Bayan B1/B2: preservation; Ankit A2/A5: evaluation clock/counting | Rebased fixtures and fixed clock; missing/stale/failed sources never count healthy. |
| Verifier correctness | Bayan B3 | Partial recovery, naive/invalid timestamps and old source/fresh processing regressions with fixtures. |
| Vehicle-to-provider routing and identity | Ankit A3: mapping; Emmanuel E2: provider allowlist | Separate provider mocks and wrong-target rejection; never acknowledge phantom execution. |

## Branches, reviews and V2 preservation

After this contract PR is reviewed and merged, all three developers branch from the **same updated main revision**. Each uses the mocks/fixtures from that revision; no cherry-picking or waiting for another developer’s feature branch. Suggested focused branches/PRs and file ownership are in [the guide](v1-independent-development.md). A shared contract change requires affected-owner review and synchronized fixtures/tests.

A6–A7, B4/B6/B7 and E3–E5 remain Phase V2 with their objectives and acceptance criteria intact. V2 extends these boundaries through a reviewed contract revision: CARLA actor/vehicle mapping, observation freshness and recovery windows, third twin, diagnostic outcomes, one real uProtocol exchange and supported OpenSOVD operation, CARLA-backed Kanto, skill comparison and final evaluation. B6 supplies the third individual twin to Ankit’s single aggregator; it does not create a competing fleet implementation. No V2 functionality is implemented by this preparation package.
