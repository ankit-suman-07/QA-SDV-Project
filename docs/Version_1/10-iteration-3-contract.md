# Iteration 3 Shared Integration Contract

## Purpose

This document defines the shared data, API, fault, traceability, and validation contracts for Iteration 3 of the Software-Defined Vehicle Health Monitoring and Diagnostic System.

All component owners must use these field names, units, states, and behaviours unless a change is reviewed and approved by the team. The objective is to allow the Java backend, Python services, JavaScript frontend, Eclipse Kuksa, uProtocol/Protobuf, Eclipse Ditto, and OpenSOVD-compatible adapter to integrate through stable interfaces.

## Iteration 3 Scenario

Iteration 3 implements one complete diagnostic scenario:

1. A user or diagnostic client requests `COOLING_SYSTEM_FAILURE` injection.
2. Spring Boot validates the request and generates an action identifier.
3. The vehicle simulator raises temperature and lowers coolant pressure.
4. The simulator publishes the signals to Eclipse Kuksa.
5. The integration pipeline reads the current Kuksa values.
6. uProtocol/Protobuf transports a traceable vehicle-status event.
7. The health engine evaluates the correlated signals.
8. Eclipse Ditto receives the signals, calculated health status, active fault, and timestamps.
9. The OpenSOVD-compatible adapter exposes the diagnostic result.
10. The frontend displays the action state, vehicle state, fault, and latency.

## Contract Version

| Field | Value |
|---|---|
| Contract version | `1.0.0` |
| Iteration | `3` |
| Vehicle | `vehicle-001` |
| Scenario | `COOLING_SYSTEM_FAILURE` |

Every message that supports schema metadata should include `schemaVersion: "1.0.0"`.

---

## Vehicle Identity

| Field | Type | Required | Value or Rule |
|---|---|---:|---|
| `vehicleId` | String | Yes | Must equal `vehicle-001` for the current project scope. |

Requests containing a missing, blank, or unsupported vehicle ID must be rejected.

---

## Vehicle Signal Contract

| Logical Field | Type | Unit | Required | Description |
|---|---|---|---:|---|
| `speedKph` | Number | km/h | Yes | Current simulated vehicle speed. |
| `batteryPercent` | Number | % | Yes | Current traction-battery state of charge. |
| `temperatureCelsius` | Number | °C | Yes | Current simulated engine or coolant temperature. |
| `coolantPressureKpa` | Number | kPa | Yes | Current simulated engine-coolant pressure. |
| `tirePressurePsi.frontLeft` | Number | psi | Yes | Current front-left tire pressure. |

### Existing Kuksa Paths

| Logical Field | Kuksa/VSS Path |
|---|---|
| `speedKph` | `Vehicle.Speed` |
| `batteryPercent` | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` |
| `temperatureCelsius` | `Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature` |
| `tirePressurePsi.frontLeft` | `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` |

### Coolant-Pressure Path

The Kuksa owner must confirm a suitable standard VSS path for coolant pressure before implementation.

If no suitable path is available, the team must:

1. Propose a clearly named custom path.
2. Record the path in this document.
3. Obtain team approval.
4. Use the approved path consistently in the simulator, backend, messages, Ditto, tests, and documentation.

**Approved coolant-pressure path:** `TO_BE_CONFIRMED`

No component should silently invent a different path.

### Signal Validation Rules

- All signal values must be numeric.
- Boolean values must not be accepted as numeric signal values.
- Missing values must be reported rather than silently converted into valid measurements.
- Units must not change between components.
- Non-finite values such as `NaN` or infinity must be rejected.
- Every signal snapshot must include a source timestamp.

---

## Correlated Health Rule

The new fault must be based on the correlation of temperature and coolant pressure. A single abnormal value must not activate the correlated fault.

### Activation Rule

Activate `COOLING_SYSTEM_FAILURE` when both conditions are true:

```text
temperatureCelsius >= 105.0
AND
coolantPressureKpa <= 150.0
```

Expected result:

```text
healthStatus = CRITICAL
activeFaults contains COOLING_SYSTEM_FAILURE
```

### Recovery Rule

Clear `COOLING_SYSTEM_FAILURE` only when both recovery conditions are true:

```text
temperatureCelsius <= 100.0
AND
coolantPressureKpa >= 180.0
```

Expected result when no other fault is active:

```text
healthStatus = HEALTHY
activeFaults does not contain COOLING_SYSTEM_FAILURE
```

### Hysteresis

The separate activation and recovery thresholds provide hysteresis. After activation, values between the activation and recovery boundaries must not repeatedly activate and clear the fault.

### Important Threshold Disclaimer

These are controlled simulation thresholds selected for repeatable project testing. They must not be presented as production-vehicle engineering or safety limits.

### Required Rule Test Cases

| Temperature | Coolant Pressure | Previous State | Expected Result |
|---:|---:|---|---|
| `90°C` | `220 kPa` | Healthy | `HEALTHY` |
| `108°C` | `220 kPa` | Healthy | No correlated fault |
| `90°C` | `140 kPa` | Healthy | No correlated fault |
| `108°C` | `140 kPa` | Healthy | Activate `COOLING_SYSTEM_FAILURE` and return `CRITICAL` |
| `103°C` | `165 kPa` | Active | Keep fault active because recovery is incomplete |
| `99°C` | `190 kPa` | Active | Clear fault and return `HEALTHY` if no other fault exists |

---

## Diagnostic Action API

### Base Path

```text
/api/v1/diagnostics/actions
```

### Supported Operations

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/diagnostics/actions` | Submit an inject or clear action. |
| `GET` | `/api/v1/diagnostics/actions/{actionId}` | Retrieve the state of a submitted action. |

### Supported Actions

| Action | Scenario | Meaning |
|---|---|---|
| `INJECT_SCENARIO` | `COOLING_SYSTEM_FAILURE` | Start the controlled cooling-system failure. |
| `CLEAR_SCENARIO` | `COOLING_SYSTEM_FAILURE` | Stop the failure and begin signal recovery. |

Scenario status can be obtained through the action-status endpoint or a separately approved simulator-status endpoint.

### Diagnostic Action Request

```json
{
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE"
}
```

### Request Validation

- `vehicleId` is required and must equal `vehicle-001`.
- `action` is required and must be supported.
- `scenario` is required and must equal `COOLING_SYSTEM_FAILURE`.
- Unknown fields may be rejected if strict validation is enabled.
- Blank strings must be treated as invalid values.
- Repeated injection or clearing must be handled idempotently or return a clear conflict response.

### Accepted Action Response

Recommended HTTP status: `202 Accepted`

```json
{
  "actionId": "550e8400-e29b-41d4-a716-446655440000",
  "traceId": "550e8400-e29b-41d4-a716-446655440000",
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE",
  "status": "ACCEPTED",
  "requestedAt": "2026-08-03T15:00:00Z"
}
```

The initial implementation may use the same UUID for `actionId` and `traceId`. If separate values are introduced later, their relationship must be retained.

### Action Status Response

```json
{
  "actionId": "550e8400-e29b-41d4-a716-446655440000",
  "traceId": "550e8400-e29b-41d4-a716-446655440000",
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE",
  "status": "COMPLETED",
  "requestedAt": "2026-08-03T15:00:00Z",
  "completedAt": "2026-08-03T15:00:02Z",
  "message": "Cooling-system failure scenario is active"
}
```

### Action States

| State | Meaning |
|---|---|
| `ACCEPTED` | Request passed initial validation. |
| `IN_PROGRESS` | The simulator or pipeline is processing the request. |
| `COMPLETED` | The requested action completed successfully. |
| `FAILED` | Processing failed. |
| `REJECTED` | The request was invalid or unsupported. |

### Permitted State Transitions

```text
ACCEPTED -> IN_PROGRESS -> COMPLETED
ACCEPTED -> IN_PROGRESS -> FAILED
ACCEPTED -> FAILED
REJECTED
```

---

## Simulator Control Interface

The simulator owner may implement equivalent routes, but Spring Boot and the simulator must agree on one stable interface.

Suggested interface:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/scenarios/cooling-system-failure` | Activate the scenario. |
| `DELETE` | `/scenarios/cooling-system-failure` | Clear the scenario. |
| `GET` | `/scenarios/status` | Retrieve the current scenario state. |

### Simulator Activation Request

```json
{
  "vehicleId": "vehicle-001",
  "actionId": "550e8400-e29b-41d4-a716-446655440000",
  "traceId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Simulator Response

```json
{
  "vehicleId": "vehicle-001",
  "scenario": "COOLING_SYSTEM_FAILURE",
  "status": "ACTIVE",
  "actionId": "550e8400-e29b-41d4-a716-446655440000",
  "updatedAt": "2026-08-03T15:00:01Z"
}
```

### Simulator Scenario States

- `INACTIVE`
- `ACTIVATING`
- `ACTIVE`
- `RECOVERING`
- `FAILED`

---

## Vehicle-Status Event Contract

The exact Protobuf structure is owned by the uProtocol owner, but it must logically represent the following data:

```json
{
  "schemaVersion": "1.0.0",
  "eventId": "event-uuid",
  "traceId": "trace-uuid",
  "actionId": "action-uuid-or-null",
  "vehicleId": "vehicle-001",
  "eventType": "VEHICLE_STATUS_UPDATED",
  "signals": {
    "speedKph": 60.0,
    "batteryPercent": 75.0,
    "temperatureCelsius": 108.0,
    "coolantPressureKpa": 140.0,
    "tirePressurePsi": {
      "frontLeft": 32.0
    }
  },
  "timestamps": {
    "sourceTimestamp": "2026-08-03T15:00:01.000Z",
    "publicationTimestamp": "2026-08-03T15:00:01.100Z",
    "receptionTimestamp": "2026-08-03T15:00:01.120Z"
  }
}
```

### Messaging Requirements

- `eventId` must uniquely identify one event.
- Publisher and receiver must preserve the same `eventId`.
- `traceId` must connect related stages of the same flow.
- `actionId` may be null for normal telemetry without a diagnostic request.
- Missing required metadata must cause validation failure.
- Duplicate event IDs must be detected and counted.
- Invalid events must not be treated as successful deliveries.

---

## Fault Contract

### Correlated Fault Representation

```json
{
  "code": "COOLING_SYSTEM_FAILURE",
  "description": "High temperature correlated with low coolant pressure",
  "severity": "CRITICAL",
  "status": "ACTIVE",
  "affectedSignals": [
    "temperatureCelsius",
    "coolantPressureKpa"
  ],
  "observedValues": {
    "temperatureCelsius": 108.0,
    "coolantPressureKpa": 140.0
  },
  "activationThresholds": {
    "temperatureCelsius": 105.0,
    "coolantPressureKpa": 150.0
  },
  "recoveryThresholds": {
    "temperatureCelsius": 100.0,
    "coolantPressureKpa": 180.0
  },
  "detectedAt": "2026-08-03T15:00:01.200Z",
  "clearedAt": null,
  "eventId": "event-uuid",
  "traceId": "trace-uuid",
  "actionId": "action-uuid"
}
```

### Fault Status Values

- `ACTIVE`
- `CLEARED`

### Fault Consistency Rules

- An active correlated fault must appear in `activeFaults`.
- A cleared correlated fault must not remain in `activeFaults`.
- `faultCount` must equal the number of entries in `activeFaults`.
- `CRITICAL` must be used while `COOLING_SYSTEM_FAILURE` is active.
- `detectedAt` is required for an active fault.
- `clearedAt` is required after the fault is cleared.
- Both observed signal values and both thresholds must be included.

---

## Ditto Digital-Twin Contract

The Ditto thing for `sdv:vehicle-001` must expose the following logical structure:

```json
{
  "thingId": "sdv:vehicle-001",
  "attributes": {
    "vehicleId": "vehicle-001"
  },
  "features": {
    "signals": {
      "properties": {
        "speedKph": 60.0,
        "batteryPercent": 75.0,
        "temperatureCelsius": 108.0,
        "coolantPressureKpa": 140.0,
        "tirePressurePsi": {
          "frontLeft": 32.0
        },
        "sourceTimestamp": "2026-08-03T15:00:01.000Z"
      }
    },
    "health": {
      "properties": {
        "status": "CRITICAL",
        "activeFaults": [
          "COOLING_SYSTEM_FAILURE"
        ],
        "faultCount": 1,
        "processedTimestamp": "2026-08-03T15:00:01.400Z"
      }
    },
    "diagnostics": {
      "properties": {
        "lastActionId": "action-uuid",
        "lastTraceId": "trace-uuid",
        "actionStatus": "COMPLETED",
        "activeFaultDetails": []
      }
    }
  }
}
```

### Ditto Verification Requirements

The verifier must check:

- Required signal fields exist.
- Signal types are valid.
- Coolant pressure is present.
- Health status is recognized.
- `faultCount` matches `activeFaults`.
- Correlated-fault status matches the signal values.
- Required timestamps are valid ISO 8601 values.
- The digital twin is sufficiently fresh for the configured publication interval.
- Action, trace, and fault identifiers remain consistent where present.

---

## OpenSOVD-Compatible Diagnostic Contract

The diagnostic adapter must expose the correlated fault in a consistent diagnostic format.

```json
{
  "vehicleId": "vehicle-001",
  "resourceType": "diagnosticFault",
  "fault": {
    "code": "COOLING_SYSTEM_FAILURE",
    "description": "High temperature correlated with low coolant pressure",
    "severity": "CRITICAL",
    "status": "ACTIVE",
    "affectedSignals": [
      "temperatureCelsius",
      "coolantPressureKpa"
    ],
    "observedValues": {
      "temperatureCelsius": 108.0,
      "coolantPressureKpa": 140.0
    },
    "detectedAt": "2026-08-03T15:00:01.200Z"
  },
  "traceId": "trace-uuid",
  "actionId": "action-uuid"
}
```

If the available OpenSOVD gateway cannot perform writes, the project will use a documented OpenSOVD-compatible action adapter that forwards diagnostic actions to Spring Boot.

The report must distinguish this adapter from a complete production OpenSOVD implementation.

---

## Traceability and Profiling Contract

### Required Identifiers

| Field | Purpose |
|---|---|
| `eventId` | Identifies one vehicle-status event. |
| `traceId` | Connects processing stages across the end-to-end flow. |
| `actionId` | Identifies the diagnostic action that initiated a scenario. |

### Required Stage Timestamps

| Field | Measurement Point |
|---|---|
| `actionRequestedTimestamp` | Spring Boot receives the diagnostic action. |
| `simulatorGenerationTimestamp` | Simulator generates the signal snapshot. |
| `kuksaReadTimestamp` | Pipeline retrieves the current values from Kuksa. |
| `publicationTimestamp` | uProtocol publisher serializes or publishes the event. |
| `receptionTimestamp` | uProtocol receiver accepts and validates the event. |
| `ruleCompletedTimestamp` | Correlated health evaluation completes. |
| `dittoCompletedTimestamp` | Required Ditto updates complete successfully. |
| `diagnosticCompletedTimestamp` | Diagnostic mapping or response completes. |
| `frontendUpdatedTimestamp` | Frontend displays the result, if measured. |

### Derived Latencies

```text
Simulator-to-Kuksa latency = kuksaReadTimestamp - simulatorGenerationTimestamp

uProtocol latency = receptionTimestamp - publicationTimestamp

Rule-evaluation latency = ruleCompletedTimestamp - receptionTimestamp

Ditto-update latency = dittoCompletedTimestamp - ruleCompletedTimestamp

Diagnostic-mapping latency = diagnosticCompletedTimestamp - dittoCompletedTimestamp

Backend pipeline latency = diagnosticCompletedTimestamp - kuksaReadTimestamp

Action-to-diagnostic latency = diagnosticCompletedTimestamp - actionRequestedTimestamp
```

The team must document exactly which stages are included in each reported metric.

### Timing Requirements

- Use UTC ISO 8601 timestamps for values that cross process boundaries.
- Use a monotonic clock for elapsed-time measurements inside one process.
- Do not subtract monotonic-clock values produced by different processes.
- All experiment services should run on the same machine unless clock synchronization is documented.
- Failed events must be recorded with a failure reason rather than silently omitted.

---

## Experiment Record Contract

Each experiment record should contain at least:

```csv
experiment_id,event_id,trace_id,action_id,publication_interval_seconds,total_latency_ms,success,health_status,fault_code,failure_reason
```

Stage-level columns should be added when available:

```csv
simulator_to_kuksa_ms,uprotocol_ms,rule_evaluation_ms,ditto_update_ms,diagnostic_mapping_ms
```

### Required Experiment Metrics

- Event count
- Successful event count
- Failed event count
- Success rate
- Missing event count
- Duplicate event count
- Minimum latency
- Average latency
- Median latency
- p95 latency
- Maximum latency
- Standard deviation
- Observed throughput
- Average latency for each measured stage

---

## Error Contract

### Error Response

```json
{
  "timestamp": "2026-08-03T15:00:00Z",
  "status": 400,
  "error": "INVALID_DIAGNOSTIC_ACTION",
  "message": "Unsupported diagnostic action",
  "path": "/api/v1/diagnostics/actions",
  "traceId": "trace-uuid"
}
```

### Standard Error Codes

| HTTP Status | Error Code | Situation |
|---:|---|---|
| `400` | `INVALID_REQUEST` | Missing or malformed fields. |
| `400` | `INVALID_DIAGNOSTIC_ACTION` | Unsupported action value. |
| `400` | `INVALID_SCENARIO` | Unsupported scenario value. |
| `404` | `VEHICLE_NOT_FOUND` | Unsupported vehicle ID. |
| `404` | `ACTION_NOT_FOUND` | Unknown action ID. |
| `409` | `SCENARIO_STATE_CONFLICT` | Action conflicts with the current scenario state. |
| `502` | `COMPONENT_COMMUNICATION_FAILURE` | Downstream component returned an invalid response. |
| `503` | `COMPONENT_UNAVAILABLE` | Simulator, Kuksa, Ditto, or diagnostics service is unavailable. |
| `504` | `COMPONENT_TIMEOUT` | A downstream request exceeded the configured timeout. |

Errors must not expose stack traces, credentials, or internal secrets to the frontend.

---

## Component Ownership and Handoffs

| Contract Area | Primary Owner | Required Consumers |
|---|---|---|
| Spring Boot API and correlated rule | Ankit | Frontend, simulator adapter, tests |
| Coolant-pressure generation and Kuksa path | Emmanuel | Backend, uProtocol, Ditto, frontend |
| Protobuf schema and traceability metadata | Benjamin | Integration pipeline, backend, profiling |
| Ditto and OpenSOVD-compatible representation | Atharva | Backend, frontend, verifier |
| Dashboard requests and presentation | Mehtaj | Spring Boot API and diagnostic responses |

No owner should rename shared fields without notifying all consumers.

---

## Minimum End-to-End Acceptance Scenario

The Iteration 3 integration is accepted when the following test passes:

1. All required services start successfully.
2. `vehicle-001` initially reports `HEALTHY`.
3. The frontend or API client submits `INJECT_SCENARIO` for `COOLING_SYSTEM_FAILURE`.
4. Spring Boot returns `202 Accepted` with an action ID.
5. The simulator enters `ACTIVE` or `ACTIVATING` mode.
6. Temperature increases and coolant pressure decreases.
7. Kuksa exposes both updated signals.
8. uProtocol publisher and receiver preserve the same event and trace identifiers.
9. The correlated rule activates only after both thresholds are satisfied.
10. Ditto reports:
    - `health.status = CRITICAL`
    - `activeFaults` contains `COOLING_SYSTEM_FAILURE`
    - `faultCount = 1`, assuming no other fault is active
11. The diagnostic adapter returns the correlated fault with both observed values.
12. The profiler records successful stage and total latency values.
13. The clear action is submitted.
14. The simulator enters recovery mode.
15. The fault remains active until both recovery conditions are satisfied.
16. Ditto and diagnostics eventually report the fault as cleared.
17. The frontend returns to `HEALTHY` if no other fault is active.

---

## Required Automated Test Categories

- Contract and DTO validation tests
- Correlated-rule boundary tests
- Hysteresis and recovery tests
- Diagnostic-action controller tests
- Simulator control-adapter tests
- uProtocol serialization and metadata tests
- Duplicate, missing, and invalid-event tests
- Ditto completeness, consistency, and freshness tests
- OpenSOVD-compatible mapping tests
- Error and timeout tests
- Integration tests using mocks or test doubles
- Live component integration tests
- Complete end-to-end system tests
- Regression tests for Iteration 2 behaviour
- Performance and profiling validation tests

---

## Change-Control Rules

1. Changes to shared field names, types, units, thresholds, endpoints, states, or error codes require team review.
2. Contract changes must be made in this document before or with the implementation PR.
3. Breaking changes must increment the contract version.
4. Tests and example payloads must be updated with every approved contract change.
5. A component implementation that does not follow the approved contract must not be merged.

## Definition of Done

This contract is considered implemented when:

- The approved coolant-pressure path replaces `TO_BE_CONFIRMED`.
- All components use the agreed field names and units.
- Diagnostic inject, clear, and status operations work.
- The correlated rule and recovery behaviour pass boundary tests.
- Event, trace, and action identifiers are preserved.
- Ditto and the diagnostic adapter expose consistent state.
- Stage-level and total latency measurements are generated.
- Negative, integration, system, regression, and performance tests pass.
- The README, report, evidence, and demonstration match the implemented behaviour.
