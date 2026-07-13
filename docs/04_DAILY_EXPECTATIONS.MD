# SDV Health Monitoring System — 25-Day Task and Expectations Plan

## Purpose

This plan assigns a concrete daily goal to every member of the five-person team. Each task includes an expected deliverable, dependencies or handoffs, and acceptance criteria. The plan assumes approximately one to two hours of work per member per day, with longer sessions when integration requires them.

## Team

| Member | Primary ownership |
|---|---|
| Ankit Suman | Backend Integration and Quality Lead |
| Emmanuel Adegboye | Eclipse Kuksa and Vehicle Simulation Lead |
| Benjamin Emeshili | Eclipse uProtocol, OpenSOVD Support, and CI Lead |
| Atharva Rajadhyaksha | Eclipse Ditto and Diagnostics Lead |
| Mehtaj | Frontend Dashboard and API Validation Lead |

## Status Values

- Not Started
- In Progress
- Blocked
- In Review
- Completed

---

## Day 1 — Feasibility Research and Initial Direction

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Draft the problem statement, MVP scope, initial runtime architecture, proposed health rules, and backend responsibilities. Identify the minimum APIs and integration adapters likely required. | Initial project-overview and architecture notes. | Share with all members before Day 2. | Scope identifies one simulated vehicle, four signal categories, three faults, selected components, and measurable evaluation. | Not Started |
| Emmanuel | Research how to run Kuksa, publish/read VSS signals, and simulate the agreed vehicle values. Prove at least one sample signal can be written or identify the exact setup steps. | Kuksa feasibility note with versions, commands, API/port, signal example, risks, and fallback. | Provide findings to Ankit for the Day 2 design meeting. | Note contains an actionable setup approach and official references, not only a general summary. | Not Started |
| Benjamin | Research the available uProtocol implementation, Java/Protobuf workflow, transport options, and realistic event scope. Build or locate a minimal serialization example. | uProtocol feasibility note and minimal event approach. | Provide constraints to Ankit and Atharva. | Recommended approach identifies what can realistically be completed in 25 days and a bounded fallback. | Not Started |
| Atharva | Research Ditto startup, thing creation/update APIs, and OpenSOVD setup and diagnostic resources. Identify how backend health data could map to both components. | Ditto/OpenSOVD feasibility note, API examples, risks, and fallback. | Share API requirements with Ankit and Benjamin. | Note shows a credible path for creating one twin and exposing at least vehicle information and active faults. | Not Started |
| Mehtaj | Research a simple dashboard architecture and compare polling, Server-Sent Events, and WebSockets. Sketch the essential healthy, warning, critical, loading, and disconnected states. | Frontend feasibility note and low-fidelity wireframe. | Share required response fields with Ankit. | Wireframe covers live signals, health, diagnostics, timestamps, and errors without unnecessary features. | Not Started |

## Day 2 — In-Person Architecture and Contract Meeting

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Lead the 2–3 hour meeting. Finalize scope, runtime flow, component boundaries, health-engine location, API approach, Git workflow, milestones, risks, and fallback rules. Record decisions and unresolved actions. | Approved architecture, meeting record, scope, and decision log. | Requires Day 1 findings from everyone. Hand final decisions to all owners. | Every component has defined inputs, outputs, owner, integration path, and fallback; unresolved items have owners and deadlines. | Not Started |
| Emmanuel | Present verified Kuksa findings. Propose exact VSS/Kuksa paths, types, units, normal ranges, and publish frequency for speed, battery, temperature, and four tire values. | Approved Kuksa signal mapping. | Depends on Day 1 research. Hands paths to Ankit, Benjamin, Atharva, and Mehtaj. | All four signal categories have agreed paths, types, units, and sample values. | Not Started |
| Benjamin | Present the uProtocol implementation and transport recommendation. Finalize event names, publishers, consumers, common headers, and minimum Protobuf fields. | Approved uProtocol event outline and fallback. | Uses shared fields and architecture decisions. | Team agrees on VehicleStatusUpdated, HealthStatusChanged, FaultDetected, and FaultCleared or documents approved changes. | Not Started |
| Atharva | Present Ditto/OpenSOVD findings. Finalize the twin structure, update mechanism, diagnostic scope, and mappings from health faults. | Approved twin and diagnostic outline. | Uses signal and fault contracts. Hands mappings to Ankit. | The team can explain where state is persisted and how diagnostic information becomes queryable. | Not Started |
| Mehtaj | Present the dashboard wireframe and recommended update method. Confirm the fields and endpoints needed from the backend. | Approved dashboard scope and frontend API requirements. | Depends on backend and diagnostic decisions. | Dashboard MVP is limited to signals, health, faults, diagnostics, timestamps, loading, and errors. | Not Started |

## Day 3 — Repository, Contracts, and Component Skeletons

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Create or finalize the monorepo structure, branch/PR rules, shared vehicle-data contract, backend Spring Boot skeleton, DTO package, and initial API specification. | Repository structure, backend application that builds, data contract, and API draft. | Requires Day 2 decisions. Hands DTO/API details to all owners. | Maven build passes; documents use identical field names, types, units, timestamps, and vehicle ID. | Not Started |
| Emmanuel | Create the Kuksa/simulator directories and configuration skeleton. Document prerequisites and add a basic simulator entry point or configuration. | Kuksa and simulator project skeleton. | Uses approved signal paths. | Files are committed on a feature branch and include startup instructions. | Not Started |
| Benjamin | Create the uProtocol/Protobuf directory, package naming, build configuration, and initial event-schema files. | uProtocol module skeleton that can generate or compile classes. | Uses approved events and shared fields. | Schema/build command runs or the exact remaining blocker is recorded with evidence. | Not Started |
| Atharva | Create Ditto and OpenSOVD configuration directories. Add an initial vehicle-001 twin JSON model and placeholder diagnostic mappings. | Twin model and diagnostic configuration skeleton. | Uses shared vehicle and fault fields. | JSON is valid and contains the agreed raw state, health, faults, and timestamps. | Not Started |
| Mehtaj | Create the frontend directory and base page structure. Implement layout placeholders using the agreed wireframe and a mock data file matching the shared contract. | Runnable dashboard skeleton with mock data. | Requires Ankit’s API/data contract. | Page loads without errors and visibly reserves areas for signals, health, faults, diagnostics, and errors. | Not Started |

## Day 4 — Minimum Component Setup

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Implement `/api/vehicles/vehicle-001/state` and `/health` mock endpoints using the shared DTO. Add validation and one controller test. | Backend endpoints returning contract-compliant sample data. | Depends on the Day 3 Spring Boot skeleton. Hands endpoint details to Mehtaj. | Application starts, responses match the contract, and the controller test passes. | Not Started |
| Emmanuel | Run Kuksa locally or through Docker. Prove that one agreed signal can be written and read back. Record exact commands, ports, and credentials. | Working one-signal Kuksa demonstration. | Depends on environment setup. Hands connection details to Ankit. | Published value and retrieved value match, with screenshot or command output as evidence. | Not Started |
| Benjamin | Define the shared event envelope and complete VehicleStatusUpdated for one signal. Add a serialization/deserialization test. | First valid Protobuf event and passing test. | Uses the shared contract. Hands generated class/schema to Ankit. | Round-trip test preserves vehicle ID, event ID, timestamp, and signal value. | Not Started |
| Atharva | Start Ditto and create vehicle-001. Update and retrieve one temperature property using the API. Continue minimum OpenSOVD setup separately. | Running twin with verified one-property update. | Uses Ditto configuration and model. Hands working request to Ankit. | GET returns the same property value sent through the update request. | Not Started |
| Mehtaj | Connect the page to Ankit’s mock state endpoint. Add loading, successful, and API-error states. | Dashboard reading real backend mock endpoint. | Requires Ankit’s endpoint and CORS settings. | Values render from the API; stopping the backend produces a clear error state. | Not Started |

## Day 5 — Four-Signal Foundations

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Complete VehicleState DTOs for speed, battery, temperature, and four tire-pressure values. Add validation rules and service tests. Draft Jenkins stages with Benjamin. | Stable vehicle-state model and tests. | Uses finalized signal contract. Hands response examples to all owners. | Valid payload passes; missing, invalid, or out-of-range values produce documented behaviour. | Not Started |
| Emmanuel | Add all agreed signal paths to Kuksa and prove each can be published and read. Create a configuration file for values and publish frequency. | Four-category Kuksa publication/readback demonstration. | Depends on approved paths and units. Hands sample readings to Ankit. | Every agreed signal updates correctly and uses the approved type and unit. | Not Started |
| Benjamin | Extend VehicleStatusUpdated to all signal fields. Add negative and missing-field tests where supported. Draft Jenkinsfile stages. | Complete status event and CI outline. | Uses Ankit’s stable model and Emmanuel’s units. | Event round-trip preserves all fields; CI design names actual build/test commands. | Not Started |
| Atharva | Extend vehicle-001 with all signal properties and health placeholders. Verify partial updates do not remove unrelated properties. | Complete base Ditto twin model. | Uses the shared contract. Hands property paths to Ankit. | Repeated partial updates preserve all non-updated properties. | Not Started |
| Mehtaj | Build cards for all signals and last-update time using backend mock data. Ensure missing values do not break the page. | Complete signal overview section. | Uses Ankit’s DTO response. | All signal categories display with units; null or missing data has a safe placeholder. | Not Started |

## Day 6 — Normal Simulation and Component APIs

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Create Kuksa and Ditto client interfaces with temporary/mock implementations. Document configuration properties and errors expected from external systems. | Adapter interfaces and configuration structure. | Requires connection details from Emmanuel and Atharva. | Backend can switch between mocks and real adapters through configuration. | Not Started |
| Emmanuel | Implement a normal-driving scenario with predictable changes over at least five minutes. Add timestamps and a single start command. | Repeatable normal simulation. | Requires working signal publication. Hands scenario timing to Ankit. | Scenario stays within normal ranges and produces observable periodic updates. | Not Started |
| Benjamin | Define HealthStatusChanged with vehicle ID, previous/current status, reason, and timestamp. Add tests and generated artifacts. | Valid health-status event schema. | Requires agreed health classifications. | Event correctly represents HEALTHY, WARNING, and CRITICAL transitions. | Not Started |
| Atharva | Document and test Ditto authentication, update, and retrieval requests. Identify the minimum OpenSOVD resources required for vehicle information and faults. | Verified Ditto API guide and diagnostic resource list. | Uses running Ditto/OpenSOVD environment. | Another member can repeat the twin operations from the guide. | Not Started |
| Mehtaj | Add health banner, active-fault list, and diagnostic placeholders using mock responses. Apply consistent healthy/warning/critical presentation. | Mock health and diagnostic UI. | Uses Ankit’s proposed health response. | All three health states are distinguishable and accessible without relying only on colour. | Not Started |

## Day 7 — Fault and Diagnostic Contracts

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Finalize thresholds, severity aggregation, fault codes, activation rules, recovery margins, and diagnostic response DTOs. Add a decision record explaining rule choices. | Approved health and diagnostic specification. | Review with Emmanuel and Atharva. Hands fault contract to all owners. | Every fault has warning/critical conditions, clearing rule, code, severity, and example payload. | Not Started |
| Emmanuel | Implement configurable low-battery fault injection and recovery. Record injected value and timestamp. | First repeatable fault scenario. | Uses Ankit’s threshold and clearing rule. | One command activates the expected low-battery state and another restores normal values. | Not Started |
| Benjamin | Define FaultDetected and FaultCleared schemas using the approved fault contract. Add round-trip tests. | Fault-lifecycle event schemas and tests. | Depends on Ankit’s fault specification. | Events include code, severity, affected signal, observed value, threshold, and timestamp. | Not Started |
| Atharva | Extend the Ditto twin with healthStatus, activeFaults, faultCount, lastSourceTimestamp, and lastDiagnosticTimestamp. Draft OpenSOVD field mappings. | Extended twin and diagnostic mapping table. | Uses Ankit’s fault DTOs. Hands mappings to Ankit and Benjamin. | Twin can represent healthy, active-fault, and cleared-fault examples without ambiguity. | Not Started |
| Mehtaj | Update UI models and sample data for the finalized health and diagnostic contracts. Add fault details and recovered/cleared presentation. | Contract-compliant health UI mock. | Requires Ankit’s finalized response. | UI shows code, severity, description, timestamp, status, and affected signal. | Not Started |

## Day 8 — Health Engine and Additional Faults

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Implement the rule-based health engine for all three faults. Add JUnit tests for normal, warning, critical, boundary, simultaneous, and recovery conditions. | Health engine with comprehensive unit tests. | Uses Day 7 rules. Hands stable outputs to Atharva, Benjamin, and Mehtaj. | All documented rule cases pass and health aggregation is deterministic. | Not Started |
| Emmanuel | Add high-temperature and low-tire-pressure fault injection and recovery. Keep all scenarios independently configurable. | Three complete fault scenarios. | Uses Day 7 thresholds and Day 6 simulator. | Each fault triggers only its expected condition and can be cleared without restarting Kuksa. | Not Started |
| Benjamin | Complete all four event schemas and create a sample publisher/consumer or adapter demonstration. | Minimum uProtocol event flow. | Uses generated classes and shared fault data. | One event is created, transmitted or passed through the bounded adapter, decoded, and matched by event ID. | Not Started |
| Atharva | Configure the minimum OpenSOVD resources or service structure for vehicle information and active faults. Test a manual sample fault. | First diagnostic query response. | Uses approved diagnostic mapping. Hands endpoint/query to Ankit. | Query returns vehicle ID and one structured active fault. | Not Started |
| Mehtaj | Add a configurable polling or live-update service and connect it to mock endpoints. Prevent duplicate rendering and stale timers. | Frontend update mechanism. | Uses the agreed real-time approach. | Values refresh at the intended interval and stop cleanly on navigation/error. | Not Started |

## Day 9 — Independent Component Readiness Review

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Demonstrate backend build, APIs, DTO validation, health engine, mock adapters, and test suite. Publish the Day 10 integration checklist and resolve contract changes. | Backend readiness evidence and integration checklist. | Requires stable contracts from all owners. | Maven tests pass and each real adapter has verified connection information. | Not Started |
| Emmanuel | Demonstrate Kuksa, normal simulation, all four signal categories, and three repeatable fault scenarios from a clean start. | Kuksa/simulator readiness evidence. | Uses final configuration. Hands startup and fault commands to team. | Another member can reproduce normal and faulty values from the documentation. | Not Started |
| Benjamin | Demonstrate all schemas, generated artifacts, serialization tests, and the minimum event publisher/consumer or adapter. | uProtocol readiness evidence. | Uses final contracts. Hands integration method to Ankit. | All event tests pass and backend invocation steps are documented. | Not Started |
| Atharva | Demonstrate vehicle-001 creation/update/retrieval and the minimum diagnostic query. Document initialization order. | Ditto/OpenSOVD readiness evidence. | Uses final twin and diagnostic model. Hands endpoints/credentials to Ankit. | Twin and diagnostic examples work from a clean or documented initialized state. | Not Started |
| Mehtaj | Demonstrate dashboard with mock backend data for normal, warning, critical, cleared, loading, and error states. | Frontend readiness evidence. | Uses finalized API contracts. | No core view depends on an undefined field; backend URL is configurable. | Not Started |

## Day 10 — First Integration: Kuksa to Backend

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Implement the real Spring Boot Kuksa adapter for temperature, map it into VehicleState, and expose it through the state API. Add unavailable-data logging. | Backend endpoint returning Kuksa temperature. | Requires Emmanuel’s Kuksa details. Hands endpoint to Mehtaj. | Backend value equals the value published to Kuksa. | Not Started |
| Emmanuel | Run Kuksa and publish changing temperature values. Support Ankit’s connection testing and correct configuration issues. | Stable temperature source and connection evidence. | Requires Day 9 configuration. | External client and backend can both read the current value. | Not Started |
| Benjamin | Finalize VehicleStatusUpdated for temperature and provide the generated class/adapter to Ankit. | Integration-ready event implementation. | Uses backend language/package details. | A backend-compatible example builds and passes serialization tests. | Not Started |
| Atharva | Keep Ditto running with vehicle-001 and verify manual temperature updates. Provide final API headers and request body. | Integration-ready Ditto temperature update. | Requires initialized twin. | Manual update and retrieval work repeatedly. | Not Started |
| Mehtaj | Replace mock temperature with Ankit’s real endpoint while keeping other signals mocked. | Dashboard showing real temperature. | Requires Ankit’s API and CORS. | Displayed value tracks Kuksa changes and errors are handled. | Not Started |

## Day 11 — Complete Kuksa Signal Ingestion

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Extend the Kuksa adapter to speed, battery, temperature, and all tire values. Validate missing/invalid data and return one VehicleState response. | Complete real vehicle-state endpoint. | Requires Emmanuel’s paths. Hands response to Mehtaj and Atharva. | One response contains all signals with correct names, types, units, and timestamp. | Not Started |
| Emmanuel | Publish all signals through the normal scenario and confirm source timestamps and configured frequency. | Stable four-category source stream. | Requires working simulator. | All values update predictably and remain in normal ranges. | Not Started |
| Benjamin | Extend status events to all fields and regenerate artifacts. | Complete VehicleStatusUpdated implementation. | Depends on stable DTO fields. | All fields survive serialization with no unit/type mismatch. | Not Started |
| Atharva | Confirm the twin model accepts all signal fields and timestamps. | Verified full-state twin update example. | Uses Ankit’s response structure. | Ditto stores and returns every agreed signal. | Not Started |
| Mehtaj | Replace remaining mock signal values with the real vehicle-state endpoint. | Fully live signal overview. | Requires Ankit’s endpoint. | Every card displays live data and safely handles missing fields. | Not Started |

## Day 12 — Backend to Ditto Synchronization

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Implement the real Ditto client. Send normalized Kuksa state after each accepted update and handle timeout/error responses. | Automatic Kuksa-to-Ditto synchronization. | Requires Atharva’s API and twin model. | A Kuksa change appears in Ditto without manual action. | Not Started |
| Emmanuel | Run a five-minute normal scenario for repeated synchronization testing. | Repeatable normal integration run. | Requires Kuksa-to-backend connection. | Scenario completes without malformed or missing source values. | Not Started |
| Benjamin | Implement the callable status-event adapter used by the backend. | Backend-ready event adapter. | Requires generated artifacts. Hands usage to Ankit. | Sample VehicleState produces a valid event. | Not Started |
| Atharva | Monitor repeated twin updates and confirm partial updates preserve unrelated health properties. | Ditto synchronization results. | Requires Ankit’s client. | At least 20 updates complete without state corruption. | Not Started |
| Mehtaj | Add twin synchronization state and timestamps from the backend. | Digital-twin status panel. | Requires Ankit’s combined or twin-status endpoint. | UI distinguishes source time from twin synchronization time. | Not Started |

## Day 13 — Health Engine Integration

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Run real Kuksa values through the health engine and expose combined state, health, and active faults. Persist health output to Ditto. | Integrated health-processing endpoint. | Requires Days 11–12. Hands response to Mehtaj. | Normal values produce HEALTHY and the same state appears in Ditto. | Not Started |
| Emmanuel | Run all three faults separately against the integrated health engine and record actual vs expected classification. | Initial fault-validation report. | Requires Ankit’s integrated rules. | Every scenario triggers its intended fault and severity. | Not Started |
| Benjamin | Connect HealthStatusChanged and FaultDetected generation to health-engine transitions. | Health-event integration. | Requires Ankit’s transition output. | Events occur on actual transitions, not every repeated sample. | Not Started |
| Atharva | Verify healthStatus, activeFaults, and faultCount updates in Ditto. | Twin health-validation evidence. | Requires Ankit’s synchronization. | Twin matches backend for healthy and active-fault examples. | Not Started |
| Mehtaj | Replace mock health/fault data with the combined real endpoint. | Live health dashboard. | Requires stable response contract. | UI transitions from healthy to warning/critical without page reload. | Not Started |

## Day 14 — Fault Clearing and State Consistency

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Complete fault-clearing, recovery margins, stale-signal behaviour, and Ditto removal/update logic. Expand tests. | Stable fault lifecycle implementation. | Requires Emmanuel’s recovery scenarios. | Fault activates, persists appropriately, clears only after recovery, and leaves no stale active entry. | Not Started |
| Emmanuel | Run activation and clearing sequences for each fault and record timestamps. | Three repeatable fault lifecycle runs. | Requires final clearing thresholds. | Each scenario returns all affected signals to a documented normal state. | Not Started |
| Benjamin | Generate FaultCleared and verify ordered event sequences for all fault lifecycles. | Event lifecycle test results. | Requires Ankit’s clearing transitions. | Expected sequence is detected → status changed as needed → cleared, with no duplicates. | Not Started |
| Atharva | Verify twin consistency during activation and recovery. | Ditto fault-lifecycle validation. | Requires integrated pipeline. | Cleared faults are removed or marked cleared exactly as specified. | Not Started |
| Mehtaj | Show active, recovered, and cleared states without stale UI entries. | Completed fault lifecycle presentation. | Requires backend clearing response. | UI clears the active fault and records recovery correctly. | Not Started |

## Day 15 — OpenSOVD Diagnostic Integration

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Implement the diagnostic adapter mapping health-engine faults to the agreed OpenSOVD representation. Expose a backend diagnostic endpoint. | Initial backend-to-diagnostics flow. | Requires Atharva’s setup/mapping. Hands endpoint to Mehtaj. | At least one injected fault is queryable through the diagnostic endpoint. | Not Started |
| Emmanuel | Run a repeatable overheating scenario with activation and clearing timestamps. | Diagnostic integration test input. | Requires integrated backend. | Scenario consistently produces the agreed temperature fault. | Not Started |
| Benjamin | Assist Atharva with OpenSOVD and verify event-to-diagnostic field mappings. | Final mapping and support fixes. | Uses fault schemas and diagnostic resources. | Every diagnostic field has an identified source and type. | Not Started |
| Atharva | Configure vehicle information, health, and active-fault diagnostic queries. | Working minimum OpenSOVD queries. | Requires backend health fields. | OpenSOVD returns vehicle information and at least one active fault. | Not Started |
| Mehtaj | Connect the diagnostic panel to Ankit’s real endpoint. | Live diagnostic dashboard section. | Requires diagnostic response contract. | Code, description, severity, time, and status display correctly. | Not Started |

## Day 16 — uProtocol Runtime Integration

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Integrate the uProtocol adapter and publish status/fault events at agreed transition points. Add correlation IDs to logs. | Backend publishing traceable events. | Requires Benjamin’s adapter. | Normal update and fault lifecycle produce expected event types and IDs. | Not Started |
| Emmanuel | Generate normal and faulty data with source timestamps for event tracing. | Event-propagation input set. | Requires integrated backend. | Each injected change can be matched to an event ID/timestamp. | Not Started |
| Benjamin | Complete the chosen transport or bounded adapter and a subscriber/test consumer. Add logging and delivery assertions. | Working event publisher/consumer demonstration. | Requires Ankit’s integration. | Published event is received, decoded, and matched by event ID. | Not Started |
| Atharva | Confirm enabling the event flow does not duplicate or corrupt twin/diagnostic updates. | Cross-component compatibility report. | Requires uProtocol-enabled backend. | Twin and diagnostic outputs remain correct and singular. | Not Started |
| Mehtaj | Add recent events only if the endpoint is in the approved MVP; otherwise run UI regression. | Recent-events view or regression evidence. | Depends on Ankit’s API decision. | No unapproved feature delays core dashboard work. | Not Started |

## Day 17 — First Complete End-to-End Demonstration

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Run and debug the full pipeline. Trace one overheating event across logs, twin, diagnostics, and dashboard. | First complete E2E build and defect list. | Requires all services. Assign defects to owners. | One fault travels from simulator to every required output and then clears. | Not Started |
| Emmanuel | Execute the documented overheating demo from a clean normal state. | Repeatable demo script. | Requires complete pipeline. | Another member can run it from instructions alone. | Not Started |
| Benjamin | Monitor and validate event content, ordering, and timestamps. | uProtocol E2E validation. | Requires full run. | Every expected event is received once and decodes correctly. | Not Started |
| Atharva | Monitor Ditto and OpenSOVD through activation and clearing. | Twin/diagnostic E2E validation. | Requires full run. | Both systems match the backend state throughout the lifecycle. | Not Started |
| Mehtaj | Validate the complete user flow and correct live update/error issues. | Demo-ready dashboard for one full fault. | Requires stable endpoints. | Audience can observe healthy → faulty → recovered without manual refresh. | Not Started |

## Day 18 — All Fault Scenarios and Feature Freeze

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Verify all three fault lifecycles end to end, fix rule issues, and declare feature freeze. | Stable core feature set and freeze record. | Requires all fault scenarios. | Three scenarios activate and clear correctly across required components. | Not Started |
| Emmanuel | Create one command/script or documented sequence that runs each fault and restores normal state. | Complete fault-injection suite. | Requires final thresholds. | Faults run independently and predictably. | Not Started |
| Benjamin | Validate detected, changed, and cleared event sequences for all faults. | Complete event regression results. | Requires all scenarios. | No missing or duplicate lifecycle event remains. | Not Started |
| Atharva | Validate Ditto and diagnostic state for all fault lifecycles. | Complete twin/diagnostic regression results. | Requires integrated scenarios. | No stale active fault remains after recovery. | Not Started |
| Mehtaj | Test all supported health/fault/error states and stop adding features. | Feature-frozen dashboard. | Requires stable backend. | Dashboard correctly represents every committed scenario. | Not Started |

## Day 19 — Automated API and Integration Testing

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Add integration tests for state, health, and diagnostics APIs. Mock externals where appropriate and document live-service tests. | Automated backend integration suite. | Requires stable endpoints. Hands commands to Benjamin. | Maven runs normal, invalid, and fault API tests successfully. | Not Started |
| Emmanuel | Automate comparison of simulator values with Kuksa readback and test invalid/out-of-range inputs. | Kuksa accuracy tests. | Requires stable configuration. | Tests identify missing, rejected, or mismatched values. | Not Started |
| Benjamin | Add event propagation tests and incorporate runnable tests into Jenkins. | uProtocol tests and CI test stages. | Requires commands from all owners. | Jenkins reports clear pass/fail results. | Not Started |
| Atharva | Create repeatable API tests for Ditto and OpenSOVD healthy, fault, and cleared states. | Twin/diagnostic test collection. | Requires stable endpoints. | Assertions verify status codes, fields, and expected state. | Not Started |
| Mehtaj | Complete Postman collection and environment for state, health, diagnostics, and errors. | Shareable Postman/Newman suite. | Requires final APIs. Hands collection to Ankit/Benjamin. | Collection runs without manual URL edits and includes assertions. | Not Started |

## Day 20 — Latency and Reliability Measurement

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Instrument receipt, detection, event, twin, diagnostic, and dashboard publication timestamps. Define analysis calculations. | Trace logs and measurement method. | Requires common UTC timestamps/event IDs. | One event’s stage and total latency can be calculated. | Not Started |
| Emmanuel | Run at least 30 controlled injections across three faults and save injection time/event ID. | Measurement input dataset. | Requires instrumentation. Hands data to Ankit. | At least 30 valid runs have complete source records. | Not Started |
| Benjamin | Count published, received, missing, and duplicate events and measure event processing/delivery time. | uProtocol metric results. | Uses controlled runs. | Results include sample count, latency summary, and delivery rate. | Not Started |
| Atharva | Record when events become visible in Ditto and diagnostics and match them to IDs. | Twin/diagnostic timing results. | Requires common IDs. Hands results to Ankit. | Each valid run can be correlated across systems. | Not Started |
| Mehtaj | Record dashboard receipt/render time and inspect request frequency. | Dashboard timing results. | Requires backend timestamps. | Dashboard latency can be computed for the measurement runs. | Not Started |

## Day 21 — Docker Compose and Jenkins Stabilization

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Remove hard-coded backend values, verify environment variables, startup dependencies, health endpoints, and logs. | Container-ready backend. | Requires service settings from all owners. | Backend starts from documented configuration and exposes health status. | Not Started |
| Emmanuel | Add Kuksa and simulator services/configuration to the shared startup workflow. | Reproducible Kuksa/simulator startup. | Requires Compose file. | Clean environment starts and publishes signals from documented commands. | Not Started |
| Benjamin | Finalize Jenkins checkout, build, test, package, and reporting stages; assist with Compose integration. | Passing CI pipeline. | Requires all build/test commands. | A commit triggers a pipeline with understandable failure output. | Not Started |
| Atharva | Add/document Ditto and OpenSOVD startup, health checks, and initialization. | Reproducible twin/diagnostics startup. | Requires Compose approach. | Required resources initialize consistently from documentation. | Not Started |
| Mehtaj | Containerize or document frontend startup and configure backend URL externally. | Portable frontend startup. | Requires backend service name/port. | Dashboard connects correctly in the shared environment. | Not Started |

## Day 22 — Full Regression and Critical Defect Fixing

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Coordinate clean-start regression, prioritize defects, merge reviewed fixes, and reject new features. | Prioritized defect list and integration fixes. | Requires all services/tests. | No critical startup, propagation, logic, or test defect remains. | Not Started |
| Emmanuel | Run normal and all fault scenarios twice from a clean start and fix simulator issues. | Stable simulator regression. | Requires integrated environment. | Two consecutive runs succeed without manual correction. | Not Started |
| Benjamin | Run CI and event regression after fixes. Resolve pipeline/event failures. | Passing CI and event evidence. | Requires integration branch. | Required pipeline stages pass. | Not Started |
| Atharva | Regression-test twin synchronization and diagnostics for two full cycles. | Stable Ditto/OpenSOVD evidence. | Requires clean startup and scenarios. | State remains correct across both cycles. | Not Started |
| Mehtaj | Run UI and Postman regression; fix stale state, errors, and layout problems. | Stable dashboard and API collection. | Requires stable backend. | Core API assertions pass and demo flow works. | Not Started |

## Day 23 — Documentation and Results

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Write architecture, backend, health engine, integration, testing, measurement, and result sections. Update runtime diagram. | Main technical report content and results summary. | Requires all measurements. | Text matches actual implementation and distinguishes results from targets. | Not Started |
| Emmanuel | Document Kuksa setup, paths, simulator, scenarios, commands, and validation. | Kuksa/simulation guide. | Requires final implementation. | Another person can reproduce normal/fault data. | Not Started |
| Benjamin | Document event schemas, transport/adapter, tests, limitations, and Jenkins. | uProtocol/CI guide. | Requires final implementation. | Full and fallback behaviours are disclosed accurately. | Not Started |
| Atharva | Document twin model, synchronization, OpenSOVD setup, mappings, queries, and results. | Twin/diagnostic guide. | Requires final resources. | Examples match implemented requests/responses. | Not Started |
| Mehtaj | Document dashboard setup, API use, screenshots, user flow, and Postman execution. | Frontend/API guide. | Requires final UI/APIs. | Instructions cover every committed view and validation step. | Not Started |

## Day 24 — Presentation and Demonstration Rehearsal

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Finalize architecture, backend, testing, and results slides; coordinate timing and complete two rehearsals. | Final presentation and timed runbook. | Requires all content/results. | Presentation fits the limit and tells one coherent technical story. | Not Started |
| Emmanuel | Prepare and rehearse Kuksa/simulator and fault-injection segment. | Reliable live injection segment. | Requires stable environment. | Works in two consecutive rehearsals. | Not Started |
| Benjamin | Prepare concise uProtocol/CI explanation and evidence. | Event/CI presentation segment. | Requires final schemas and pipeline. | Explains modification and evidence within assigned time. | Not Started |
| Atharva | Prepare Ditto/OpenSOVD live demonstration and explanation. | Twin/diagnostic segment. | Requires injected fault. | State and diagnostics update correctly in two rehearsals. | Not Started |
| Mehtaj | Prepare dashboard demonstration at presentation resolution and backup screenshots/video. | Presentation-ready UI and backup. | Requires stable demo. | Audience can clearly see healthy, faulty, and recovered states. | Not Started |

## Day 25 — Final Validation and Submission

| Member | Task instructions | Expected deliverable | Dependencies / handoff | Acceptance criteria | Status |
|---|---|---|---|---|---|
| Ankit | Review repository, report, tests, results, limitations, contributions, and submission files. Tag the final release and coordinate submission. | Validated release and submission package. | Requires final work from everyone. | Tagged version builds, required files open, and submission requirements are met. | Not Started |
| Emmanuel | Run final Kuksa/simulator smoke test and verify committed scripts/configuration. | Final source-side validation. | Requires release candidate. | Normal and faulty data publish from a clean start. | Not Started |
| Benjamin | Run final Jenkins pipeline and uProtocol tests; save successful evidence. | Final CI/event validation. | Requires release candidate. | Required pipeline stages pass on submitted commit. | Not Started |
| Atharva | Run final Ditto/OpenSOVD smoke tests and confirm initialization/query documentation. | Final twin/diagnostic validation. | Requires release candidate and simulator. | Healthy and faulty states return correctly. | Not Started |
| Mehtaj | Run final dashboard and Postman smoke tests; verify links, screenshots, and presentation files. | Final frontend/API validation. | Requires final backend. | Dashboard loads and all core Postman requests pass. | Not Started |

---

## Mandatory Milestones

| Deadline | Required outcome |
|---|---|
| End of Day 2 | Scope, architecture, shared data contract, API/event outline, risks, and fallbacks agreed |
| End of Day 4 | Each workstream has a runnable skeleton or minimum component proof |
| End of Day 9 | Every component demonstrates minimum input/output independently |
| End of Day 10 | Temperature flows from Kuksa to Spring Boot and the dashboard |
| End of Day 12 | All committed signals flow through the backend and synchronize with Ditto |
| End of Day 14 | Health engine activates and clears faults and keeps Ditto consistent |
| End of Day 17 | One fault completes the full end-to-end pipeline, including uProtocol and diagnostics |
| End of Day 18 | All three fault lifecycles work; feature freeze begins |
| End of Day 21 | Automated tests, measurements, Docker Compose, and Jenkins are operational |
| End of Day 22 | No critical defect remains |
| End of Day 24 | Presentation and demo succeed in two rehearsals |
| End of Day 25 | Release is validated and ready for submission |

## Daily Progress Update Template

```text
Date:
Member:

Completed:
- What was finished since the previous update

Today:
- The task and deliverable planned today

Blockers:
- Exact issue or error
- What has already been attempted
- Person or dependency needed
- Next action and decision deadline

Evidence:
- GitHub issue, commit, pull request, test result, log, or screenshot
```

## Team Operating Rules

1. Every task must have one accountable owner.
2. A task is complete only when its acceptance criteria are satisfied.
3. Code work must link to a GitHub issue, commit, or pull request.
4. Each member updates their task status and blocker notes daily.
5. A blocker lasting longer than one planned work session must be escalated to Ankit.
6. Component owners must provide documented inputs, outputs, configuration, and tests during handoff.
7. Contract changes require team approval and immediate updates to affected tasks and documentation.
8. No new feature may be added after Day 18 without explicit team agreement.
9. Days 22–25 are reserved for defect fixes, validation, results, documentation, and presentation.
10. Any fallback implementation must be disclosed accurately in the report and presentation.


