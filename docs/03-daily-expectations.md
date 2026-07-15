# SDV Health Monitoring System — Concise 24-Day Task Expectations

## Purpose

This roadmap provides the high-level objective for each team member on every project day. At the beginning of each day, the applicable row should be expanded into detailed task cards using the project’s actual repository state, completed work, test results, blockers, and component versions.

Testing follows a TDD-oriented approach from Day 2 onward: define expected behaviour and tests first, implement the minimum required code, run the tests, and refactor after they pass.

## Team Roles

| Member | Primary Role |
|---|---|
| **Ankit Suman** | Backend Integration, Test Architecture and Quality Lead |
| **Emmanuel Adegboye** | Eclipse Kuksa and Vehicle Simulation Lead |
| **Benjamin Emeshili** | Eclipse uProtocol, OpenSOVD Support and CI Lead |
| **Atharva Rajadhyaksha** | Eclipse Ditto and Diagnostics Lead |
| **Mehtaj** | Frontend Dashboard and UI Quality Lead |

## 24-Day Roadmap

| Day | Daily Milestone | Ankit | Emmanuel | Benjamin | Atharva | Mehtaj | Dependencies / Expected Outcome |
|---:|---|---|---|---|---|---|---|
| **1** | Feasibility research | Draft scope, initial architecture, backend responsibilities, integration risks, and success criteria. | Research Kuksa setup, VSS paths, publishing, reading, and simulation options. | Research uProtocol libraries, Protobuf workflow, transport options, and fallback approach. | Research Ditto APIs, twin creation, OpenSOVD setup, and diagnostic mapping options. | Research dashboard update options and prepare a basic wireframe. | Each member brings verified findings, official references, risks, and a recommended approach to the Day 2 meeting. |
| **2** | Architecture, contracts, and test design | Lead the design meeting; finalize architecture, scope, health rules, test strategy, API contracts, acceptance criteria, and fallbacks. | Finalize signal paths, types, units, ranges, thresholds, and simulator inputs. | Finalize events, common message fields, publishers/consumers, and event test cases. | Finalize twin structure, diagnostic scope, mappings, and component test cases. | Finalize dashboard fields, update method, UI states, and frontend acceptance tests. | Shared data/API/event contracts, TDD expectations, risks, and ownership are approved before implementation. |
| **3** | Repository and test skeletons | Create Spring Boot skeleton, DTOs, failing backend test skeletons, and Git/PR guidelines. | Create Kuksa/simulator structure and failing signal publication/readback test skeletons. | Create Protobuf module and failing serialization/event test skeletons. | Create Ditto/OpenSOVD configuration and failing API/state test skeletons. | Create dashboard skeleton, mock contract data, and frontend test checklist/skeletons. | Every workstream has a committed structure, initial tests, and documented startup approach. |
| **4** | Minimum component proof | Implement mock backend state/health endpoints to satisfy initial tests. | Run Kuksa and prove one signal can be published and read. | Implement and test one VehicleStatusUpdated message. | Create vehicle-001 and update/read one twin property; continue OpenSOVD setup. | Connect dashboard to backend mock endpoint and test loading/error states. | Each component demonstrates a minimum input/output; temperature contract is validated across workstreams. |
| **5** | Four-signal foundations | Complete shared VehicleState DTO validation and backend unit tests. | Configure and validate speed, battery, temperature, and four tire values in Kuksa. | Extend status schema/tests to all signal fields and outline Jenkins stages. | Extend the twin with all signals and health placeholders. | Build all signal cards and missing-value handling using mock/available APIs. | All components use identical signal fields, types, units, and timestamps. |
| **6** | Normal-operation path | Define Kuksa/Ditto adapter interfaces, configuration, and tests using mocks. | Implement a repeatable normal-driving simulation with timestamps. | Define and test HealthStatusChanged. | Verify repeated Ditto updates and document authentication/API usage. | Add health banner, fault list, diagnostic placeholders, and UI acceptance checks. | Normal state is reproducible and component interfaces are stable enough for integration. |
| **7** | Fault and diagnostic contract | Finalize health thresholds, fault codes, recovery rules, diagnostic DTOs, and failing rule tests. | Implement and test low-battery injection and recovery. | Define and test FaultDetected and FaultCleared schemas. | Extend twin health/fault fields and finalize OpenSOVD mappings. | Update UI models/tests to the final health and diagnostic contracts. | Every fault has agreed activation, severity, clearing, event, twin, diagnostic, and UI behaviour. |
| **8** | Health engine and all fault sources | Implement health rules until unit tests pass; refactor after passing. | Implement and validate overheating and low-pressure scenarios. | Demonstrate event publisher/consumer or approved bounded adapter. | Produce the first manual OpenSOVD vehicle/fault diagnostic response. | Implement polling/SSE/WebSocket client behaviour and prevent stale/duplicate rendering. | Three repeatable fault inputs exist; health engine and event/diagnostic minimums are demonstrable. |
| **9** | Independent readiness review | Demonstrate backend APIs, health tests, mock adapters, and integration checklist. | Demonstrate clean Kuksa startup, normal simulation, and three faults. | Demonstrate all schemas, generated artifacts, and event tests. | Demonstrate Ditto twin operations and minimum OpenSOVD query. | Demonstrate all dashboard states against contract-compliant mock APIs. | Every component passes its readiness criteria before real integration begins. |
| **10** | First vertical integration | Implement real Kuksa temperature adapter and state endpoint with integration tests. | Publish changing temperature and support backend connectivity. | Provide integration-ready temperature status-event adapter. | Provide verified Ditto temperature update API/configuration. | Display real backend temperature while retaining safe fallbacks. | Temperature flows from simulator through Kuksa and Spring Boot to the dashboard. |
| **11** | Complete real signal ingestion | Extend Kuksa adapter/tests to all agreed signals. | Run stable normal simulation for all signals. | Extend status-event implementation/tests to all signals. | Verify full-state twin update structure. | Replace remaining mock signals with the real state endpoint. | Backend and dashboard receive all signal categories correctly. |
| **12** | Ditto synchronization | Implement/test automatic backend-to-Ditto synchronization and error handling. | Run repeated normal updates for synchronization testing. | Complete callable event adapter for the backend. | Validate repeated updates, timestamps, and preservation of unrelated properties. | Display twin synchronization state and timestamps. | Kuksa-derived state automatically appears in the Ditto twin without corruption. |
| **13** | Health integration | Run real signals through the health engine, expose combined health API, and synchronize health to Ditto. | Execute each fault and record expected versus actual results. | Connect health/fault event generation to real health transitions. | Validate healthStatus, activeFaults, and faultCount in Ditto. | Connect health and fault UI to real backend responses. | Normal and faulty inputs produce correct backend, twin, event, and dashboard states. |
| **14** | Fault recovery and consistency | Complete recovery margins, fault clearing, stale-signal behaviour, and related tests. | Run activation/recovery sequences for all faults with timestamps. | Validate ordered detected/status-changed/cleared event sequences. | Verify twin consistency and removal/clearing of stale faults. | Verify active, recovered, cleared, disconnected, and error UI states. | All three fault lifecycles activate and clear consistently without stale state. |
| **15** | OpenSOVD integration | Implement/test diagnostic adapter and expose backend diagnostic API. | Provide repeatable diagnostic test scenario and timestamps. | Assist OpenSOVD integration and validate event-to-diagnostic mappings. | Configure and test vehicle-information and active-fault diagnostic queries. | Connect the diagnostic panel to the real backend endpoint. | At least one injected fault is available through the implemented diagnostic flow and dashboard. |
| **16** | uProtocol runtime integration | Integrate uProtocol event publication with correlation IDs and tests. | Generate traceable normal and faulty inputs. | Complete runtime transport/bounded adapter and subscriber assertions. | Ensure event integration does not duplicate twin or diagnostic updates. | Run frontend regression; add recent-event view only if already approved. | Published events are received and matched by ID without corrupting other state. |
| **17** | First full end-to-end run | Coordinate/debug the complete pipeline and create the defect list. | Execute the documented overheating demonstration. | Validate event content, order, timestamps, and duplicates. | Validate Ditto and OpenSOVD through activation and clearing. | Validate healthy → faulty → recovered dashboard flow. | One fault traverses every required component and clears successfully. |
| **18** | Complete all faults and freeze features | Verify/fix all three E2E fault lifecycles and declare feature freeze. | Finalize one repeatable sequence covering all fault scenarios. | Complete event regression for all fault lifecycles. | Complete twin/diagnostic regression for all faults. | Complete UI regression for all supported states. | All committed functional behaviour works; no new features are added afterward. |
| **19** | Automated integration and API testing | Complete backend, API-contract, integration, and E2E automation; maintain Postman/Newman. | Automate simulator-to-Kuksa accuracy and invalid-input checks. | Add event tests and begin full Jenkins test execution. | Automate/repeat Ditto and OpenSOVD API tests. | Complete frontend tests and support frontend-facing API assertions. | Automated suites validate normal, invalid, active-fault, and cleared-fault behaviour. |
| **20** | Performance and reliability measurement | Instrument pipeline timestamps and analyze latency, consistency, reliability, and coverage. | Run at least 30 controlled fault injections with event IDs/timestamps. | Measure published/received/missing/duplicate events and event timing. | Record correlated Ditto and diagnostic availability times. | Record dashboard receipt/render times and verify request frequency. | A traceable dataset supports latency percentiles, delivery rate, and state-consistency results. |
| **21** | Docker and CI stabilization | Remove hard-coded settings and validate backend health/startup configuration. | Stabilize Kuksa/simulator Docker Compose configuration. | Finalize Jenkins build, test, package, and reporting stages. | Stabilize Ditto/OpenSOVD startup, health checks, and initialization. | Stabilize frontend startup and external backend configuration. | The shared environment starts reproducibly and CI runs the required automated tests. |
| **22** | Full regression and critical fixes | Lead clean-start regression, prioritize defects, review fixes, and reject scope growth. | Run all scenarios twice and fix simulator reliability defects. | Run CI/event regression and resolve failures. | Run twin/diagnostic regression and resolve stale/initialization issues. | Run UI/Postman regression and fix display/API issues. | No critical defect remains; two consecutive end-to-end cycles succeed. |
| **23** | Documentation, results, and presentation | Complete architecture, backend, testing, measurement, results, limitations, and presentation narrative. | Document Kuksa/simulator setup and prepare the fault-injection demo segment. | Document uProtocol/CI and prepare event/CI presentation evidence. | Document Ditto/OpenSOVD and prepare twin/diagnostic demo segment. | Document dashboard/Postman and prepare UI demo plus backup media. | Technical documentation matches the implementation; presentation and demo materials are complete. |
| **24** | Final validation and submission | Run final review, tag release, coordinate rehearsals, verify contributions, and submit. | Run final Kuksa/simulator smoke test and rehearse injection. | Run final CI/uProtocol tests and save evidence. | Run final Ditto/OpenSOVD smoke tests and rehearse diagnostics. | Run final dashboard/Postman smoke tests and verify backup media. | Tagged version builds, tests pass, report/slides/demo are validated, and submission requirements are satisfied. |

## Daily Detailed Task Card Template

Use this template each morning for every member after reviewing the previous day’s actual progress.

| Field | Details |
|---|---|
| **Day / Task Title** | Day number, member, and specific task name |
| **Team Member** | Person accountable for completion |
| **Daily Goal** | One clear outcome to achieve that day |
| **Task Instructions** | Numbered implementation and testing steps based on the current repository and component versions |
| **Expected Deliverable** | Exact code, test, configuration, pull request, document, or evidence expected |
| **Dependencies / Inputs** | Required completed tasks, APIs, schemas, configuration, documentation, or teammate input |
| **Handoff To** | Person who requires the output next |
| **Acceptance Criteria** | Observable conditions and tests that must pass before completion |
| **Estimated Effort** | Expected time for the task based on its current complexity |
| **Status** | Not Started, In Progress, Blocked, In Review, or Completed |
| **Notes / Blockers** | Error details, attempted fixes, required help, fallback, and decision deadline |

## Information Required Before Expanding a Daily Row

Before generating detailed instructions for a day, collect:

- Tasks completed during the previous day
- Incomplete work and current blockers
- Relevant pull requests, commits, and test results
- Current repository structure and affected files
- Actual component and library versions
- Errors, logs, or unexpected behaviour
- Changed dependencies or team availability
- Decisions that modify the original architecture or scope

Exact technical commands and APIs should be verified against the installed versions and official component documentation before they are assigned.

## Operating Rules

1. Tests and acceptance criteria are designed before implementation.
2. Each component owner writes and maintains component-level tests.
3. Ankit owns test architecture, backend tests, API automation, integration tests, end-to-end tests, and quality analysis.
4. A task is complete only when its acceptance criteria and required tests pass.
5. A blocker lasting more than one planned work session must be escalated.
6. Contract changes require team approval and updates to affected tests and documentation.
7. No new features are added after Day 18 without explicit team agreement.
8. Days 22–24 are reserved for regression, fixes, documentation, evaluation, rehearsal, and submission.