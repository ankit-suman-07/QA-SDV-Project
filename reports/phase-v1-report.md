# SDV Health Monitoring and Diagnostic System — Phase V1 Report

**Team:** Ankit, Bayan, Emmanuel [CONFIRM FULL NAMES] · **Submission:** [ADD SUBMISSION DATE]  
**Assessed revision:** [e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3](https://github.com/ankit-suman-07/QA-SDV-Project/commit/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3) · **Video:** [ADD VIDEO LINK]

## Part A — Project and progress

### Objective and deployment

The project develops a reproducible open-source platform for monitoring simulated vehicle sensors, maintaining digital twins and demonstrating targeted diagnosis and recovery. It evaluates the health-monitoring pipeline, not a complete autonomous-driving system. Phase V1 contains **exactly two vehicles**, vehicle-001 and vehicle-002; the wider fleet/CARLA objectives are staged for Phase V2. The scope, architecture and task allocation are linked from the repository’s source of truth [1].

Each vehicle has a synthetic provider, a dedicated KUKSA signal broker and a Velocitas application. Velocitas classifies observations and publishes vehicle-specific health events through shared Mosquitto. Validated ingress preserves identity, event ID and source time while updating the corresponding Ditto Thing. Spring Boot reads the individual twins, routes diagnostic requests to the selected provider and owns the sole fleet aggregation/materialization implementation. The fleet API derives state from individuals; a fleet Thing stores the same derived summary, and the dashboard displays availability and health. Kanto manages the vehicle-002 application in the same-device pilot.

Services use local processes and Docker/Compose, with separate vehicle identities and persistent runtime/evidence storage. The interactive launcher reuses a **prepared** deployment and may start its packaged backend/dashboard; it does not install or provision the complete system [6].

### Recorded MVP → V1 progress

| Area | Recorded MVP boundary | Phase V1 improvement |
|---|---|---|
| Vehicle scope | Historical single-vehicle run: simulator → KUKSA → Velocitas → MQTT. | Two isolated provider/broker/app pipelines, individual topics and twins. |
| Diagnosis | Direct simulator inject/clear; MQTT health/braking transitions. | Backend-routed vehicle-002 LiDAR obstruction and clear, observed through twins, APIs and fleet/dashboard. |
| Integration | Existing bridge/backend/UI paths did not establish one joint live acceptance run. | Actual Ditto reads, sole Spring fleet writer, source-aware views and observed vehicle-001 isolation. |
| Runtime control | Baseline record does not establish a Kanto restart. | Managed Kanto stop/start with clean exits and fresh MQTT/twin correlation. |

The November 7 MVP description is historical evidence, not a newly repeated experiment. Its missing console log and differing revision markers limit provenance. MVP and V1 timing boundaries/scenarios differ; **no numerical performance improvement is claimed** [2].

### Contributions

Recorded merged work attributes the two-vehicle edge, deterministic LiDAR scenarios and QoS correction to Emmanuel; individual ingress/twin routing, consistency and Kanto preparation to Bayan; and contracts, backend routing, fleet/dashboard, integration, subsequent remediation and runtime verification to Ankit. The latest ownership update assigns remaining V1 work to Ankit without erasing historical contributions [1, 5]. This is contribution attribution, not a claim that all required team reviews are complete.

<!-- PAGE BREAK -->

## Part A — Verification and limits

### Evidence boundaries

The report assesses current main at **e406e36**, which includes merged initialization, HTTP compatibility, shutdown, readiness and launcher work. Results below retain their actual tested revisions. No services, experiments or application suites were rerun to write this report.

| Check | Recorded result | Tested boundary / qualification |
|---|---|---|
| Automated regression | 541 Python tests plus 386 subtests; 209 Java tests; 7 frontend tests; both Compose checks passed. | Merged main **4afbbd8**. Python: 2 explicit skips and 9 integration deselections; these are not passes [3]. |
| Clean real-service integration | Four selected gates passed: readiness; healthy individual/fleet/dashboard state; one routed fault/clear with isolation; persisted-watermark restart controls. | **4afbbd8**; isolated real resources, V1 features absent before observations, freshly packaged Spring clients through upstream nginx [3]. |
| Kanto managed lifecycle | Three restart cycles and final cleanup exited 0; 174 final vehicle-001 twin samples stayed healthy. | Main-image **4afbbd8**; exact fresh MQTT/full twin properties, old sampled processes absent [3]. |
| Interactive demo | Healthy → fault → recovery → managed restart passed; 101 MQTT observations, including 51 healthy vehicle-001 messages. | Working copy based on **6fee175**, retained in launcher commit **48ba62c**. Final hardening had focused-test coverage, not another full live run [6]. |
| Current-main CI | Standard CI, baseline pipeline integration and real two-vehicle acceptance workflows completed successfully. | Exact assessed head **e406e36**; automated coverage does not imply human acceptance approval [7]. |

For fault/clear, a backend acknowledgement means dispatch was accepted, not that recovery occurred. Recorded observations separately establish vehicle-002’s fault and recovery while vehicle-001 remains healthy. The Kanto check requires a new event ID and a source observation strictly newer than the previous source, start request and Kanto-reported runtime start; the same event/source must reach real MQTT and Ditto. A running container alone is insufficient [3, 6].

### Corrections, limitations and next phase

Clean-deployment initialization and Spring HTTP-header compatibility are **fixed and merged**, not current blockers. The former creates absent V1 state only from a validated observation; the latter removes the need for the historical nginx workaround. Shutdown now performs orderly bounded cleanup and preserves nonzero failure when cleanup is incomplete [3, 4].

Evidence remains qualified. The original live-wrapper aggregate FAIL/exit 1 is retained: independent review confirmed the four selected gates passed after correcting a summary-count error. An evidence-JSON redaction error was also corrected with its failed CI and hash history preserved. Broader five-trial/outage/freshness results remain explicitly historical candidate evidence, not newly executed current-main tests [3].

Remote-LAN operation and automatic crash recovery were not verified. Same-host clock assumptions, sample sizes and polling boundaries prevent general reliability, scalability or latency claims. Contract C1–C10 approvals, production subjects/permissions/TLS, freshness/timing decisions, historical skill-provenance review and final submission/release disposition remain open in the records. This report does not certify full V1 acceptance. Phase V2 extends toward three CARLA vehicles, broader diagnostic/runtime validation, agreed uProtocol/OpenSOVD operations and evaluated customized skills [1, 5].

<!-- PAGE BREAK -->

## Part B — Specifications and skills as development controls

### How SDD controlled the output

Specification-driven development (SDD) supplied expected behavior before implementation: the source-of-truth hierarchy set phase scope; acceptance IDs defined observable outcomes; and contract 1.0.0 specified identity, MQTT delivery, source-time preservation, twin/API structures and targeted actions. Fixtures, replay cases and explicitly labelled substitutes let components develop independently. A mock pass remained component evidence until real transport, persistence and runtime checks supported a wider claim. The contract remains proposed for affected-owner review; code adoption is not formal approval [1, 5].

Three pre-prepared skills suited the platform’s boundary-heavy failures. **TDD** translated requirements into failing behavioral regressions before correction. **Systematic debugging** required tracing observations across SDK, transport, ingress and persistence rather than patching the visible symptom. **Verification before completion** required commands, exits and raw results before declaring success. These controls narrowed what generated work could legitimately claim; they did not replace specifications or human judgement [5].

### Concrete requirement → correction examples

| Specification / issue detected | Skill or review control | Correction | Verification boundary |
|---|---|---|---|
| C3 requires QoS 1. SDK publication used QoS 0 and real ingress rejected it. | E1 review checked the actual delivery boundary; a test-first correction followed. | Publish QoS 1/non-retained and gate progress on acknowledgement instead of assuming a publish call proves delivery. | Emmanuel’s **a3e20c1** correction; real edge/ingress recheck and transport controls recorded in E1 [4, 5]. |
| V1-02 requires valid observations to reach the right twin. Absent V1 features failed on clean resources; a failed read must not permit replacement. | TDD first reproduced missing-parent behavior. Debugging compared substitutes with actual Ditto subresources and conditional writes. | Initialize only absent state from a validated real observation; preserve legacy/context/watermark state; use conditional updates and advance acknowledgement only on valid persistence outcomes. | PR **#44**: four initial regression failures, then real namespaced resource/restart verification; clean-start recheck on **4afbbd8** [3, 4]. |
| V1-09 requires reliable managed stop/start. Abrupt loop stop caused exit 1; a timed-out worker join could still hang interpreter shutdown. | Logs/pinned-client lifecycle inspection and a failing stalled-join subprocess regression challenged apparent cleanup success. | Cancel/await owned work, close clients and bound cleanup. Incomplete cleanup stays a nonzero error; no forced-success exit. | PR **#46**, source **d8c1f40**: 214 targeted tests, 2 skips; five Docker cases. Main **4afbbd8**: three actual Kanto cycles exited 0 [3, 4]. |

These examples show concrete control: a contract rejected incompatible delivery, a regression prevented unsafe state initialization, and a runtime failure invalidated an apparently bounded shutdown. Unit tests and real observations addressed different risks. Passing more tests alone would not establish the required system behavior.

<!-- PAGE BREAK -->

## Part B — Critical review and evidence

### Generated work was checked, not accepted on authority

Recorded reviews include corrections and rejected suspicions. E1 questioned whether the SDK returned publication status; inspection of pinned Velocitas SDK 0.15.7 showed it returned Paho’s message information, so that suspicion was refuted. The QoS mismatch remained a real defect. E2 review also found that interrupt cleanup could miss an injection already applied; the recorded test-first correction addressed that failure [5].

Later remediation checked generated test substitutes themselves: a permissive in-memory HTTP model did not represent real Ditto feature paths and conditional headers. Correcting the substitute preserved the production validation/acknowledgement requirements instead of weakening them to obtain green tests. Live Spring/JDK/nginx probes likewise exposed a duplicate Accept-Encoding issue that simpler clients had missed. The correction was placed at the actual client boundary, with authentication, decompression, bounds and timeouts retained [4].

Independent raw-result review also corrected the verification wrapper’s misleading aggregate result and retained the original failure. The lesson is to inspect what an assertion and its dependency model actually establish, rather than accepting generated prose, a success label or a container’s running state [3].

### Provenance and limits of the skill evidence

The recorded source is **Superpowers v6.4.2, MIT**. A later investigation resolved the tag to commit **8ca22dba**: current TDD and verification copies match; the repository debugging copy differs in two secret-redaction example lines. The licence and comparison are retained. This establishes current source comparison, not the exact historical installed bytes or invocation versions of every E1/E2 session. Missing supporting testing/debugging files are **not claimed as used** [5].

Owner design choices and implementation/review histories provide specific examples, but affected-owner/rubric review remains qualified. There was no controlled study isolating the effect of skills, so quality or productivity gains cannot be attributed causally to them. Observed benefits are narrower: defects were exposed, contrary assumptions were rejected, and unsupported completion claims were constrained. Customized skills and matched original-versus-customized evaluation remain **Phase V2 work**.

### Evidence and reproduction

Links below use the assessed repository revision for durable records; their contents identify the actual tested revisions. The raw logs, measurements and detailed traceability are linked there rather than reproduced here.

- **[1]** [Source of truth, scope, architecture and task allocation](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/docs/SOURCE-OF-TRUTH.md).
- **[2]** [MVP–V1 comparison and historical baseline qualifications](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/docs/findings/mvp-to-v1-comparison.md).
- **[3]** [Merged-main verification: commands, raw results, images and lifecycle evidence](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/evidence/v1/merged-main-20261115/README.md).
- **[4]** [Evidence index: E1 and initialization, HTTP and shutdown remediation](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/evidence/README.md).
- **[5]** [Skill use, provenance/licence and review records](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/evidence/v1/skill-sources.md); [contracts and acceptance interfaces](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/docs/v1-interface-contracts.md).
- **[6]** [Demo rehearsal, focused controls and coverage limits](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/evidence/v1/demo-launcher-development-20261115/README.md); [startup/usage guide](https://github.com/ankit-suman-07/QA-SDV-Project/blob/e406e36bc38ad6f7abe3e6b5a450e33e3d4643c3/velocitas-app/kanto/LINUX-RUNTIME.md).
- **[7]** Assessed-head [standard CI](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43777912849), [baseline pipeline](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43777912883) and [real two-vehicle workflow](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43777912959).

On a prepared authorized deployment, run **bash scripts/run-v1-demo.sh** and follow the guide. Private credentials and normal terminal sudo are required; retain the dated secret-free demo evidence. This report introduces no new runtime measurements. Complete the metadata placeholders and video link before submission.
