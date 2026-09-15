# Iteration 3 Task Distribution and Implementation Roadmap

## Objective

Iteration 3 will extend the existing Software-Defined Vehicle Health Monitoring and Diagnostic System with one complete and testable scenario:

> A diagnostic action triggers a simulated cooling-system failure. The simulator produces high temperature and low coolant pressure, the pipeline detects the correlated condition, Eclipse Ditto stores the resulting `CRITICAL` fault, OpenSOVD exposes the diagnostic result, and the system records stage-by-stage latency.

The goal is to deliver a meaningful functional extension together with stronger functional, integration, system, and non-functional testing.

## Agreed Scope

Iteration 3 includes:

- A new coolant-pressure signal.
- Dynamic diagnostic actions for injecting, clearing, and querying a scenario.
- A correlated health rule using temperature and coolant pressure.
- Spring Boot integration for diagnostic action APIs.
- Extended uProtocol/Protobuf messages and traceability.
- Extended Eclipse Ditto state and verification.
- OpenSOVD-compatible diagnostic action and fault mapping.
- Dashboard controls and diagnostic visualization.
- Full-pipeline, stage-by-stage latency profiling.
- Repeated performance experiments and stronger automated testing.

### Proposed Simulation Rules

The following values are project simulation thresholds and must not be presented as production-vehicle safety thresholds:

| Condition | Temperature | Coolant Pressure | Expected State |
|---|---:|---:|---|
| Normal | Below `105°C` | Above `150 kPa` | `HEALTHY` |
| Activate correlated fault | At least `105°C` | At most `150 kPa` | `CRITICAL` with `COOLING_SYSTEM_FAILURE` |
| Recover from fault | At most `100°C` | At least `180 kPa` | `HEALTHY` |

The separate activation and recovery thresholds provide hysteresis and reduce rapid switching between healthy and faulty states.

---

## Team Work Distribution

### Ankit Suman

**Role:** Integration, Backend, Testing, and Evaluation Lead

#### Tasks

1. Finalize the shared contracts for:
   - Coolant-pressure field, unit, data type, and signal path.
   - Diagnostic action request and response.
   - Correlated fault structure.
   - Error-response structure.
   - Trace, event, and stage-timestamp fields.
2. Integrate Spring Boot into the active runtime pipeline.
3. Implement the following diagnostic APIs:
   - `POST /api/v1/diagnostics/actions`
   - `GET /api/v1/diagnostics/actions/{actionId}`
4. Support actions such as:
   - `INJECT_SCENARIO`
   - `CLEAR_SCENARIO`
   - `GET_SCENARIO_STATUS`
5. Generate and preserve an `actionId` or `traceId` for every diagnostic request.
6. Forward valid diagnostic actions to the simulator control interface.
7. Implement the correlated health rule:
   - High temperature alone must not activate the correlated fault.
   - Low coolant pressure alone must not activate the correlated fault.
   - Both conditions together must activate `COOLING_SYSTEM_FAILURE`.
   - Recovery must follow the agreed recovery thresholds.
8. Integrate:
   - Spring Boot
   - Vehicle simulator
   - Eclipse Kuksa
   - uProtocol/Protobuf
   - Health evaluation
   - Eclipse Ditto
   - OpenSOVD mapping
9. Implement stage-by-stage profiling for:
   - Simulator generation
   - Kuksa retrieval
   - uProtocol publication
   - uProtocol reception
   - Health-rule completion
   - Ditto update completion
   - Diagnostic response completion
10. Implement automated:
    - Backend unit tests
    - Integration tests
    - End-to-end tests
    - Negative and failure tests
11. Conduct repeated performance experiments.
12. Calculate:
    - Minimum, average, median, p95, and maximum latency
    - Standard deviation
    - Throughput
    - Success rate
    - Missing and duplicate event counts
    - Latency for each pipeline stage
13. Review and integrate all team pull requests.
14. Prepare final results, charts, regression evidence, and technical analysis.

#### Deliverables

- Updated shared contracts.
- Spring Boot diagnostic APIs.
- Diagnostic action service.
- Correlated health-rule engine.
- Full-pipeline profiler.
- Backend unit and integration tests.
- End-to-end test suite.
- Raw experiment CSV files.
- Statistical summaries and performance charts.
- Final integrated branch.

#### Dependencies and Handoffs

- Provide approved contracts to all members before implementation.
- Receive the simulator control API from Emmanuel.
- Receive schemas and transport updates from Benjamin.
- Receive Ditto and OpenSOVD extensions from Atharva.
- Receive dashboard and API validation from Mehtaj.

#### Acceptance Criteria

- Valid actions return an action ID and accepted status.
- Invalid requests produce meaningful `4xx` responses.
- The correlated fault requires both abnormal signals.
- Recovery follows the agreed recovery thresholds.
- Every successful event includes the required profiling timestamps.
- Automated backend and integration tests pass.
- The complete diagnostic-action-to-diagnostic-result scenario works end to end.

---

### Emmanuel Adegboye

**Role:** Eclipse Kuksa, Vehicle Simulation, and Fault-Injection Lead

#### Tasks

1. Add `coolantPressureKpa` to the vehicle simulator.
2. Identify an appropriate VSS/Kuksa path.
3. If no suitable standard path exists:
   - Propose a custom path.
   - Document it.
   - Request approval before implementation.
4. Generate changing coolant-pressure values during normal operation.
5. Implement a repeatable `COOLING_SYSTEM_FAILURE` scenario.
6. During the fault scenario:
   - Gradually increase vehicle temperature.
   - Gradually decrease coolant pressure.
   - Continue until the correlated thresholds are satisfied.
7. Implement recovery behaviour that gradually returns both signals to normal values.
8. Implement a simulator control interface for:
   - Activating the cooling-system failure.
   - Clearing the cooling-system failure.
   - Querying the current scenario.
9. Suggested simulator operations:
   - `POST /scenarios/cooling-system-failure`
   - `DELETE /scenarios/cooling-system-failure`
   - `GET /scenarios/status`
10. Add a signal-generation timestamp for full-pipeline profiling.
11. Publish coolant pressure and its timestamp to Kuksa.
12. Test:
    - Normal signal generation
    - Fault activation
    - Fault recovery
    - Repeated action requests
    - Invalid publication intervals
    - Kuksa publication accuracy
13. Update the simulator README and usage examples.

#### Deliverables

- Coolant-pressure simulation.
- Documented Kuksa/VSS signal mapping.
- Dynamic scenario-control interface.
- Signal-generation timestamp support.
- Simulator and Kuksa publication tests.
- Updated simulator README.
- Evidence of normal, fault, and recovery behaviour.

#### Dependencies and Handoffs

- Requires the signal contract and thresholds from Ankit.
- Provide control-interface details to Ankit.
- Provide signal name, path, type, and unit to Benjamin, Atharva, and Mehtaj.

#### Acceptance Criteria

- Coolant pressure is available through Kuksa.
- Normal mode remains outside the correlated-fault thresholds.
- Fault mode eventually satisfies both correlation conditions.
- Clearing the scenario restores normal operating conditions.
- Repeated requests do not corrupt simulator state.
- Simulator tests pass independently.

---

### Benjamin Emeshili

**Role:** uProtocol Messaging and Traceability Lead

#### Tasks

1. Extend the Protobuf vehicle-status schema with coolant pressure.
2. Preserve backward compatibility where practical.
3. Define the required diagnostic lifecycle events, such as:
   - `DiagnosticActionRequested`
   - `DiagnosticActionAccepted`
   - `CorrelatedFaultDetected`
   - `CorrelatedFaultCleared`
4. Add traceability fields:
   - `eventId`
   - `traceId` or `actionId`
   - `vehicleId`
   - Event type
   - Source timestamp
   - Publication timestamp
   - Reception timestamp
   - Schema version
5. Regenerate the Protobuf source files.
6. Update transport logic to preserve identifiers and timestamps.
7. Extend delivery accounting for:
   - Published events
   - Received events
   - Missing events
   - Duplicate events
   - Invalid events
8. Implement negative tests for:
   - Missing IDs
   - Missing coolant pressure
   - Malformed messages
   - Unknown event types
   - Duplicate events
   - Invalid timestamps
9. Document the event schemas and traceability flow.

#### Deliverables

- Updated `.proto` files.
- Regenerated message classes.
- Updated uProtocol transport.
- Delivery-accounting logic.
- Unit and negative tests.
- Event-flow documentation.
- Example valid and invalid payloads.

#### Dependencies and Handoffs

- Requires the shared event contract from Ankit.
- Requires coolant-pressure details from Emmanuel.
- Provide generated schemas and transport instructions to Ankit and Atharva.

#### Acceptance Criteria

- Coolant pressure serializes and deserializes correctly.
- Publisher and receiver preserve the same event and trace identifiers.
- Invalid and duplicate messages are detected.
- Existing Iteration 2 messaging tests continue to pass.
- Delivery statistics are available for the final evaluation.

---

### Atharva Rajadhyaksha

**Role:** Eclipse Ditto and OpenSOVD Diagnostics Lead

#### Tasks

1. Extend the Ditto vehicle model with:
   - Coolant pressure
   - Diagnostic action status
   - Correlated-fault details
   - Stage timestamps
2. Define `COOLING_SYSTEM_FAILURE` with:
   - Fault code
   - Description
   - Severity
   - Status
   - Affected signals
   - Observed temperature
   - Observed coolant pressure
   - Activation thresholds
   - Detection timestamp
   - Clear timestamp
3. Extend the Ditto verifier to check:
   - Coolant-pressure presence and type
   - Required correlated-fault fields
   - Health and fault consistency
   - `faultCount` accuracy
   - Valid timestamps
   - Data freshness
4. Extend the OpenSOVD-compatible fault mapper.
5. Map the correlated fault into a diagnostic resource containing both contributing signals.
6. Define mappings for:
   - Injecting the scenario
   - Clearing the scenario
   - Querying action status
7. If the available OpenSOVD gateway remains read-only:
   - Implement an action adapter that forwards requests to Spring Boot.
   - Clearly document this limitation and integration approach.
8. Implement structured error responses for:
   - Unsupported actions
   - Invalid parameters
   - Unknown vehicles
   - Unavailable services
9. Test:
   - Fault mapping
   - Valid and invalid actions
   - Fault activation
   - Fault clearing
   - Missing fields
   - Ditto state consistency
   - Stale state
10. Update Ditto and OpenSOVD documentation.

#### Deliverables

- Updated Ditto thing and policy configuration.
- Extended Ditto verifier.
- Correlated-fault diagnostic mapper.
- OpenSOVD-compatible action adapter.
- Verifier and mapper tests.
- Example diagnostic requests and responses.
- Updated component documentation.

#### Dependencies and Handoffs

- Requires the shared contract from Ankit.
- Requires signal details from Emmanuel.
- Requires message structures from Benjamin.
- Provide diagnostic endpoints and response formats to Ankit and Mehtaj.

#### Acceptance Criteria

- Ditto stores coolant pressure and correlated-fault information.
- `faultCount` remains consistent with `activeFaults`.
- The verifier detects missing, inconsistent, or stale state.
- Diagnostic mapping exposes both contributing signals.
- Inject, clear, and status operations return structured responses.
- Ditto and OpenSOVD tests pass independently.

---

### Hasin Anzum Mehtaj

**Role:** Dashboard and API/System Validation Lead

#### Tasks

1. Add dashboard controls for:
   - Injecting the cooling-system failure.
   - Clearing the cooling-system failure.
   - Querying the current action status.
2. Display:
   - Action ID
   - Request status
   - Current scenario
   - Completion status
   - Error messages
3. Add coolant pressure with its unit and last-update timestamp.
4. Display the correlated fault, including:
   - `COOLING_SYSTEM_FAILURE`
   - Severity
   - Temperature
   - Coolant pressure
   - Diagnostic description
5. Display total pipeline latency.
6. If practical, display stage-by-stage timing.
7. Handle the following UI states:
   - Loading
   - Accepted
   - Active
   - Cleared
   - Failed
   - Timeout
   - Backend unavailable
8. Update Postman collections for:
   - Valid injection
   - Valid clearing
   - Status query
   - Invalid actions
   - Invalid parameters
   - Recovery
   - Unavailable backend
9. Execute and document user-level system tests.
10. Update dashboard setup and demonstration instructions.

#### Deliverables

- Updated dashboard.
- Diagnostic action controls.
- Coolant-pressure visualization.
- Correlated-fault visualization.
- Action-state and error handling.
- Updated Postman collection.
- Frontend/API validation checklist.
- Screenshots for normal, fault, recovery, and error states.

#### Dependencies and Handoffs

- Requires the Spring Boot API from Ankit.
- Requires the diagnostic response structure from Atharva.
- Provide system-test results and demonstration evidence to Ankit.

#### Acceptance Criteria

- A user can inject and clear the scenario from the dashboard.
- Action progress and final state are displayed.
- Coolant pressure and correlated-fault data display correctly.
- Backend errors do not crash the dashboard.
- Postman tests and documented system scenarios pass.

---

## Implementation Order

| Order | Work | Responsible Members | Completion Requirement |
|---:|---|---|---|
| 1 | Finalize signal, action, fault, error, and timestamp contracts | Ankit, reviewed by the team | No field names, thresholds, or APIs remain ambiguous. |
| 2 | Implement coolant-pressure simulation and message schemas | Emmanuel and Benjamin | Coolant pressure publishes to Kuksa and passes through uProtocol. |
| 3 | Extend Ditto and OpenSOVD models | Atharva | New signal and correlated-fault state pass independent verification. |
| 4 | Implement Spring Boot actions and correlated health rules | Ankit | APIs and rules pass tests using mocks before full integration. |
| 5 | Integrate the diagnostic-action-to-fault pipeline | Ankit with Emmanuel, Benjamin, and Atharva | Injection and clearing work without depending on the dashboard. |
| 6 | Integrate the dashboard | Mehtaj | Dashboard communicates with the tested Spring Boot API. |
| 7 | Run complete automated and system testing | Entire team, led by Ankit | Existing regression tests and new Iteration 3 tests pass. |
| 8 | Conduct repeated performance experiments | Ankit | Raw results, summaries, and charts are reproducible. |
| 9 | Finalize documentation and demonstration | Entire team | README, report, evidence, repository, and video match the implemented system. |

---

## Pull Request Requirements

Every pull request must include:

- Implementation code.
- Automated tests.
- Documentation or usage instructions.
- Example request, response, log, or screenshot evidence.
- A clear description of dependencies.
- Known limitations.
- Proof that relevant existing tests still pass.
- No unrelated files.
- No temporary files, environment folders, secrets, or operating-system metadata.

## Review Checklist

Before requesting review, each member must confirm:

- [ ] The implementation follows the approved shared contract.
- [ ] New functionality is covered by automated tests.
- [ ] Relevant existing tests still pass.
- [ ] Error and invalid-input behaviour has been tested.
- [ ] Setup or usage documentation has been updated.
- [ ] Evidence of successful execution has been included.
- [ ] No credentials, local paths, generated result noise, or unrelated files are committed.
- [ ] The PR description explains the implementation, tests, dependencies, and limitations.

## Integration Policy

A component must not be merged only because it starts successfully. It should be merged only after:

1. Its acceptance criteria are satisfied.
2. Its automated tests pass.
3. Its contract matches the other components.
4. Its documentation is complete.
5. Its integration impact has been reviewed.

Ankit will coordinate final integration and may request changes when a contribution does not satisfy the agreed contract or acceptance criteria.

## Definition of Done

Iteration 3 is complete when:

- A diagnostic action can dynamically inject and clear the cooling-system scenario.
- The simulator publishes temperature and coolant-pressure changes through Kuksa.
- uProtocol events preserve the required identifiers and timestamps.
- The health engine activates the fault only when both correlated conditions are true.
- Ditto stores a complete and consistent correlated-fault state.
- OpenSOVD-compatible diagnostics expose the correlated fault.
- The dashboard can control and display the scenario.
- Full-pipeline and stage-level latency are recorded.
- Unit, integration, system, negative, recovery, and regression tests pass.
- Repeated performance experiments and their raw results are documented.
- The repository README, final report, evidence, and demonstration video reflect the completed implementation.
