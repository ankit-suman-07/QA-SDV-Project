# SDV fleet enhancement — Scope, work distribution and acceptance

Proposed team agreement · November 6, 2026

## Objective and delivery stages

Develop and evaluate a reproducible local SDV platform for three simulated vehicles that monitors LiDAR health, maintains isolated individual digital twins and one fleet twin, and supports traceable remote diagnosis and recovery using the selected Eclipse components.

| Stage | Commitment |
|---|---|
| Previous-term MVP | Preserve the single-vehicle baseline and its reproducible workflow. |
| Phase V1 · November 16 | Target approximately 60% of remaining effort. Deliver two synthetic vehicles, live Ditto and Spring Boot, fleet aggregation, a basic dashboard, fleet CI, and a one-vehicle Kanto pilot using pre-prepared vendor skills. Submit video and report. |
| Phase V2 · December 5 | Target the remaining 40%. Extend Phase V1 to three CARLA vehicles with front LiDAR, complete diagnostic action tracking, validate Kanto with the CARLA fleet, demonstrate the agreed uProtocol and OpenSOVD operations, and evaluate customized skills. Submit the product and report with demonstration evidence. |

Charter V2 names the enhancement charter. Phase V1 and Phase V2 name this term’s submission milestones. The 60/40 split estimates effort. The acceptance criteria define milestone completion.

## Product scope and architecture

Run services locally or in containers. Use one KUKSA broker and one vehicle application instance per vehicle as the initial isolation model.

| Component | Responsibility |
|---|---|
| Python simulator in V1, CARLA adapter in V2 | Generate vehicle observations, attach identity and source timestamps, and record controlled fault injection. |
| Eclipse KUKSA | Expose telemetry and compact LiDAR observations through agreed signal paths. |
| Eclipse Velocitas | Read observations, classify LiDAR health and publish vehicle-specific health/fault/recovery events. |
| Mosquitto and twin bridge | Deliver status events, validate their contracts and route each update to its vehicle twin. |
| Eclipse Ditto | Maintain individual vehicle state, fault/history features and the aggregated fleet twin. |
| Spring Boot and dashboard | Expose live fleet and vehicle state, validate and route diagnostic actions, track outcomes and display availability. |
| Eclipse Kanto | Manage the vehicle application on Linux and demonstrate launch and restart with observable results. |
| uProtocol and OpenSOVD | Provide bounded, demonstrated service communication and diagnostic operations. Freeze exact operations and implementation choices before dependent V2 work. |

Operational flow follows simulator → KUKSA → Velocitas → Mosquitto → twin bridge → Ditto → Spring Boot → dashboard. The fleet aggregator derives the fleet twin from individual vehicle states. Diagnostic requests follow dashboard → backend → selected diagnostic/edge target → execution result. Preserve action and trace identifiers through this control path. Document where uProtocol carries the agreed exchange and where OpenSOVD handles the selected diagnostic operation.

The adapter supplies observations and separate labelled ground truth. Velocitas owns health decisions. Record source freshness independently of event publication time. Keep raw LiDAR point clouds outside Ditto.

## Work distribution

This adapts the component responsibilities in `05-work-distribution.md`, with Ankit owning backend integration and major cross-system work, and Emmanuel owning CARLA in V2.

| Member | Phase V1 | Phase V2 and continuing responsibility |
|---|---|---|
| **Ankit — Architecture, backend integration and quality lead** | Freeze shared contracts with the team. Connect Spring Boot to live twin state and expose per-vehicle APIs. Route inject/clear requests to the correct provider. Expose fleet state in the basic dashboard. Own system integration, fleet CI, end-to-end verification and submission coordination. | Own backend integration across twins, fleet queries and diagnostic services. Extend fleet/vehicle APIs and dashboard with diagnostic action status and history. Lead architecture decisions, CI/CD, measurement harness, final integration, stage comparison and evaluation/report consolidation. |
| **Bayan — Messaging, twins and edge deployment lead** | Implement MQTT ingestion and vehicle-aware twin routing. Provision two twins, preserve event identity and source time, and test routing and malformed-input handling. Provide Ankit with twin schemas and read interfaces. Aggregate both twins and run the one-vehicle Kanto pilot on Linux. | Extend fleet aggregation to three twins and add history and duplicate/out-of-order handling. Repeat Kanto validation against the CARLA-backed fleet. Own the agreed uProtocol/OpenSOVD integration, coordinating backend command/result contracts with Ankit. |
| **Emmanuel — Simulation, sensors and vehicle application lead** | Run two isolated synthetic providers, brokers and Velocitas apps. Supply targeted fault/clear scenarios and valid status events. Verify signal publication and per-vehicle independence. | Own CARLA setup, actor-to-vehicle mapping, front LiDAR observations, controlled degradation/dropout and reproducible scenarios for three vehicles. Extend Velocitas detection and recovery rules, and verify adapter units, freshness and sensor behavior. Supply runtime ground truth and component evidence. |
| **All members** | Use pre-prepared skills, review another member’s work, test owned components and contribute video/report evidence. | Customize skills using course concepts, evaluate them on comparable cases, review PRs, participate in integrated runs and document actual contributions and limitations. |

Ankit coordinates quality while each component owner supplies its tests and runtime evidence. Each owner requests review from the member consuming the interface. Agree shared Compose, schema and backend changes before implementation.

## Phase V1 acceptance

| ID | Required outcome | Evidence |
|---|---|---|
| V1-01 | Two synthetic vehicles run through separate brokers/apps and publish uniquely identified observations and events. | Deployment configuration, publication checks and runtime logs. |
| V1-02 | MQTT events update two live Ditto twins. A malformed event or unknown vehicle cannot overwrite either twin. | Event contract, representative inputs and live integration assertions. |
| V1-03 | A targeted LiDAR fault/clear request reaches vehicle-002. Its state changes healthy → fault → healthy in Ditto and the backend API. Vehicle-001 stays healthy with no corresponding fault. | Repeatable script, API responses, correlated logs and isolation assertions. |
| V1-04 | Backend reads reflect live twin data. Missing or stale readings are identifiable and use preserved source timestamps. | Backend tests, a disconnected-source check and sample responses. |
| V1-05 | The existing baseline and relevant unit/integration checks pass, including a repeatable two-vehicle fault/clear CI check. The actual dependencies used by each test are labelled. | CI run or recorded local results and mocked/live coverage table. |
| V1-06 | Pre-prepared vendor skills guide actual tasks, with human review and requirement-to-test traceability. | Skill source/version, rationale, reviewed examples, spec/PR history and traceability table. |
| V1-07 | The tagged V1 can be rerun, demonstrated and explained by the team. | Video, report, startup/scenario instructions and contribution statements. |
| V1-08 | The fleet summary and basic dashboard reflect both live twins during fault and recovery. | Compare live Ditto state with the fleet API and dashboard. |
| V1-09 | On Bayan’s Linux device, Kanto launches and restarts the vehicle-002 Velocitas app and a fresh event reaches its Ditto twin. | Kanto logs and correlated MQTT/twin evidence. Track separately from the core demo if the Linux or LAN setup blocks the pilot. |

## Phase V2 acceptance

| ID | Required outcome | Evidence |
|---|---|---|
| V2-01 | Three CARLA vehicles publish front LiDAR observations through the correct brokers/apps. | Actor mapping, pinned run configuration, adapter tests and live three-vehicle run. |
| V2-02 | Controlled degradation/dropout produces the specified warning/failure state. Restored valid frames clear it after the recovery window. | Labelled fault timeline, threshold-boundary tests and repeated detection/recovery results. |
| V2-03 | Individual twins, fleet counts and dashboard agree for healthy, faulty, recovering and unavailable vehicles. Other vehicles receive no injected fault. | Cross-view assertions, fleet aggregation tests and recorded demonstration. |
| V2-04 | A dashboard diagnostic action is validated, targeted and tracked to a verifiable outcome. Unknown targets, unavailable services and timeout/failure outcomes are handled. | API tests, action/trace logs and live execution evidence. |
| V2-05 | Kanto launches and restarts the selected CARLA-backed app on Linux. Fresh post-restart events update its vehicle twin. | Linux/Kanto/image versions, status and correlated runtime events. An upstream suppressed sensor stream must be restored separately. |
| V2-06 | The agreed uProtocol exchange and OpenSOVD operation execute against the selected implementations. | Exact supported operations, pinned versions, sender/receiver or request/response traces and failure-case checks. Compatible custom adapters are labelled accurately if full integration remains pending. |
| V2-07 | Customized skills contain actionable changes grounded in cited course concepts and are evaluated against their originals on comparable tasks. | Original/customized diffs, versions, changelog, references, reviewed outputs and comparison results. |
| V2-08 | Final code, specs, skills, tests, measurements and contributions are reproducible and traceable. | Release reference, report, demonstration, CI, raw results, rerun steps and individual explanations. |

Freeze numeric freshness thresholds, persistence/recovery windows, update budgets and command timeouts in versioned contracts before dependent work. Select values from baseline observations and record the rationale.

## Evidence and measurement required by the rubric

| Criterion | Marks | Submission evidence |
|---|---:|---|
| Product functionality and package integration | 35 | Feature demos, architecture/package diagrams, requirement → spec → PR/implementation → test → runtime evidence mapping, and architectural decisions. |
| Data platform and pipeline | 10 | Mosquitto pub/sub, correct transformation and live Ditto storage, pipeline diagram, schemas, deployment instructions and reproducible input. Beam is optional. Confirm acceptance of local MQTT as the rubric’s pub/sub interpretation. |
| Selection/use of vendor skills | 10 | Source and original versions, selection rationale, use examples, critical review, corrections, tests and limitations. |
| Customization using course concepts | 20 | Skill diffs, textbook references, versions/changelog, justification and matched evaluation cases showing measured effects. |
| Verification, validation and quality | 10 | Relevant unit, integration, end-to-end and negative tests, independent checks, CI and explicit mocked/live distinctions. |
| DevOps, measurement and stage comparison | 10 | MVP/V1/V2 references, versioned specs/skills, CI, development/runtime measurements, reproducible procedures and honest stage comparisons. |
| Portfolio and accountability | 5 | Contributions linked to work, reviewed issues/PRs, decisions, lessons learned, final demonstration and individual checks. |

Measure detection delay, fault-to-twin propagation, restored-input-to-stable-health recovery, delivery/update success, vehicle isolation and CPU/memory under recorded workloads. Separate action/restart timing from restoration of sensor input. Use repeated trials and report sample counts and variability. Preserve timestamps and specify clock handling.

For skill comparisons, keep task, starting code, acceptance criteria and evaluation procedure comparable. Record model/tool settings and human interventions. Compare requirement coverage, missed defects and review corrections. Separate skill effects from added product features and mark unavailable historical measurements as unmeasured.

## Boundaries and delivery controls

Required delivery uses local services and repeatable inputs. Optional work includes Apache Beam, CANought, a second sensor, fourth/fifth vehicles and larger replay workloads. Autonomous route planning, production safety certification and raw point-cloud storage in Ditto are outside this scope.

Keep the Python synthetic demo available for CI and fallback evidence. A synthetic fallback or Docker-only run must be reported against the CARLA or Kanto criterion as partial until runtime validation passes. Record open issues and prioritize the required integrated workflow before optional work.

This is a proposed full-project scope incorporating the agreed V1 direction. The detailed ownership allocation and bounded uProtocol/OpenSOVD commitment are proposed for team review. It defines intended acceptance, and current completion must be recorded separately against each criterion.
