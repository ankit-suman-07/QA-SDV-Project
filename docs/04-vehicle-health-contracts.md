# Vehicle Health Contract

## Status

| Field | Value |
|---|---|
| **Project** | Software-Defined Vehicle Health Monitoring and Diagnostic System |
| **Vehicle** | `vehicle-001` |
| **Status** | Proposed — finalize during the Day 2 team meeting |
| **Owner** | Ankit Suman |
| **Reviewers** | Emmanuel: Kuksa/VSS; Benjamin: uProtocol; Atharva: Ditto/OpenSOVD; Mehtaj: dashboard |
| **Last updated** | July 14, 2026 |

This document is the shared implementation contract for signal names, units, health rules, faults, and cross-component mappings. Affected team members must approve changes before implementation.

## 1. Common Conventions

| Concern | Rule |
|---|---|
| Vehicle ID | String; `vehicle-001` for the MVP |
| JSON fields | `camelCase` |
| Protobuf fields | `snake_case`, explicitly mapped to the logical JSON fields |
| Timestamps | UTC ISO 8601, for example `2026-07-14T14:30:00.123Z` |
| Java timestamps | `Instant` |
| Health values | `HEALTHY`, `WARNING`, `CRITICAL` |
| Fault status | `ACTIVE`, `CLEARED` |
| Severity | `WARNING`, `CRITICAL` |
| IDs | Unique non-empty strings; UUID recommended |
| Missing values | Use absent or `null`; never substitute `0` |

## 2. Vehicle Signal Contract

Paths other than `Vehicle.Speed` must be verified by Emmanuel against the selected Kuksa image and VSS version. Do not implement an unverified custom path without team approval.

| Logical Field | VSS/Kuksa Path | Type | Unit | Valid Simulation Range | Normal Example | Fault Example | Status |
|---|---|---|---|---|---|---|---|
| `speedKph` | `Vehicle.Speed` | number | km/h | 0–250 | 60 | Not a health fault | Verify selected version |
| `batteryPercent` | Pending verification | number | % | 0–100 | 75 | 8 | Pending |
| `temperatureCelsius` | Pending verification | number | °C | -40–150 | 85 | 110 | Pending |
| `tirePressurePsi.frontLeft` | Pending verification | number | psi | 0–60 | 32 | 22 | Pending |
| `tirePressurePsi.frontRight` | Pending verification | number | psi | 0–60 | 32 | 22 | Pending |
| `tirePressurePsi.rearLeft` | Pending verification | number | psi | 0–60 | 31 | 22 | Pending |
| `tirePressurePsi.rearRight` | Pending verification | number | psi | 0–60 | 32 | 22 | Pending |

The ranges above are software-validation boundaries for the simulation, not automotive performance claims.

### Validation Rules

- Reject a sample with a missing or incorrect `vehicleId`.
- Reject or quarantine values outside the approved simulation range.
- Reject malformed timestamps and ignore out-of-order samples for current state.
- Preserve `sourceTimestamp` through every component.
- Convert units only at an adapter boundary and test the conversion.
- Never clamp an invalid value or convert a missing value to zero.
- Log the field, rejected value, vehicle ID, timestamp, and reason.

## 3. Shared Vehicle State

| Field | Type | Required | Description |
|---|---|---|---|
| `vehicleId` | string | Yes | `vehicle-001` |
| `sourceTimestamp` | timestamp | Yes | Time the simulator generated the sample |
| `speedKph` | number | Yes* | Current speed |
| `batteryPercent` | number | Yes* | Battery state of charge |
| `temperatureCelsius` | number | Yes* | Selected vehicle or powertrain temperature |
| `tirePressurePsi` | object | Yes* | Four named tire-pressure values |
| `healthStatus` | enum | Yes | Aggregated health |
| `activeFaults` | array | Yes | Active faults; empty when healthy |
| `faultCount` | integer | Yes | Must equal `activeFaults.length` |
| `processedTimestamp` | timestamp | Yes | Time backend evaluation completed |

`Yes*` means required for a complete sample. A partial or disconnected response may use `null`, but it must expose the data-quality condition.

```json
{
  "vehicleId": "vehicle-001",
  "sourceTimestamp": "2026-07-14T14:30:00.000Z",
  "speedKph": 60.0,
  "batteryPercent": 75.0,
  "temperatureCelsius": 85.0,
  "tirePressurePsi": {
    "frontLeft": 32.0,
    "frontRight": 32.0,
    "rearLeft": 31.0,
    "rearRight": 32.0
  },
  "healthStatus": "HEALTHY",
  "activeFaults": [],
  "faultCount": 0,
  "processedTimestamp": "2026-07-14T14:30:00.120Z"
}
```

## 4. Health and Fault Rules

Overall health equals the highest active severity:

```text
CRITICAL > WARNING > HEALTHY
```

- No active fault → `HEALTHY`
- At least one warning and no critical fault → `WARNING`
- At least one critical fault → `CRITICAL`
- Speed is monitored but does not create a health fault in the MVP.
- Missing, invalid, stale, or disconnected data must not be presented as confidently healthy.

### Proposed Thresholds

These are testable starting values and require Day 2 approval.

| Fault | Code | Field | Warning | Critical | Clear Warning | Clear Critical | Activation/Clear Persistence |
|---|---|---|---|---|---|---|---|
| Low battery | `BATTERY_LOW` | `batteryPercent` | ≤ 20% | ≤ 10% | > 22% | > 12% | 2 consecutive valid samples |
| High temperature | `TEMPERATURE_HIGH` | `temperatureCelsius` | ≥ 90°C | ≥ 105°C | < 87°C | < 102°C | 2 consecutive valid samples |
| Low tire pressure | `TIRE_PRESSURE_LOW_{POSITION}` | Individual tire | ≤ 28 psi | ≤ 24 psi | > 29 psi | > 25 psi | 2 consecutive valid samples |

Rules:

- Activation thresholds are inclusive.
- Clear thresholds are strict and include recovery margins to prevent rapid switching.
- A critical fault downgrades to warning when the critical-clear condition passes but the warning condition remains.
- A fault clears only after its warning-clear condition satisfies the persistence requirement.
- Persistence must be converted from samples to a duration after the simulator interval is approved.
- Each tire has a separate code, such as `TIRE_PRESSURE_LOW_FRONT_LEFT`.

## 5. Fault Record

| Field | Type | Description |
|---|---|---|
| `faultId` | string | Unique ID for one activation-to-clear lifecycle |
| `code` | string | Stable machine-readable fault code |
| `description` | string | Human-readable description |
| `severity` | enum | `WARNING` or `CRITICAL` |
| `status` | enum | `ACTIVE` or `CLEARED` |
| `affectedSignal` | string | Canonical logical field name |
| `observedValue` | number | Value associated with the decision |
| `unit` | string | Canonical unit |
| `threshold` | number | Applied threshold |
| `sourceTimestamp` | timestamp | Source-sample time |
| `detectedTimestamp` | timestamp | Activation time |
| `lastUpdatedTimestamp` | timestamp | Most recent material change |
| `clearedTimestamp` | timestamp/null | Clear time, or `null` while active |
| `correlationId` | string | Trace ID shared by downstream outputs |

Lifecycle rules:

- Create a new `faultId` when an inactive fault activates.
- Retain that ID while the fault persists, escalates, or downgrades.
- Do not emit a new detection for every abnormal sample.
- When cleared, remove the record from `activeFaults` and retain it as cleared history where supported.
- A later reactivation receives a new `faultId`.

## 6. Missing and Stale Data

Proposed stale timeout:

```text
max(3 × expected update interval, 5 seconds)
```

| Condition | Behaviour |
|---|---|
| Missing field | Mark the sample incomplete; do not substitute zero |
| Invalid value | Record a data error; do not interpret it as a vehicle fault |
| Stale timestamp | Retain the last known value with a stale label; do not claim `HEALTHY` |
| Kuksa unavailable | Expose a disconnected state through backend and dashboard |
| Out-of-order sample | Do not replace newer current state; record the occurrence |

The team must decide whether data-quality problems use a separate status or a `DATA_UNAVAILABLE` fault. They are not part of the three committed vehicle faults unless explicitly approved.

## 7. Events and Component Mapping

### Minimum Event Set

| Event | Trigger |
|---|---|
| `VehicleStatusUpdated` | Backend accepts a valid normalized state |
| `HealthStatusChanged` | Aggregated health changes |
| `FaultDetected` | A new fault satisfies activation persistence |
| `FaultCleared` | An active fault satisfies recovery persistence |

Every event includes `eventId`, `correlationId`, `eventType`, `vehicleId`, `sourceTimestamp`, and `eventTimestamp`. Fault events also contain the fault record. Repeated unchanged samples must not create duplicate lifecycle events.

### Cross-Component Mapping

| Logical Field | Spring Boot | uProtocol | Ditto | Dashboard |
|---|---|---|---|---|
| Vehicle ID | `vehicleId` | `vehicle_id` | Thing ID / `vehicleId` | `vehicleId` |
| Source time | `sourceTimestamp` | `source_timestamp` | `sourceTimestamp` | `sourceTimestamp` |
| Speed | `speedKph` | `speed_kph` | `signals.speedKph` | `speedKph` |
| Battery | `batteryPercent` | `battery_percent` | `signals.batteryPercent` | `batteryPercent` |
| Temperature | `temperatureCelsius` | `temperature_celsius` | `signals.temperatureCelsius` | `temperatureCelsius` |
| Tire pressures | `tirePressurePsi.*` | `tire_pressure_psi.*` | `signals.tirePressurePsi.*` | `tirePressurePsi.*` |
| Health | `healthStatus` | `health_status` | `health.status` | `healthStatus` |
| Active faults | `activeFaults` | Fault event payload | `health.activeFaults` | `activeFaults` |
| Fault count | `faultCount` | Optional | `health.faultCount` | `faultCount` |
| Processed time | `processedTimestamp` | Optional | `health.processedTimestamp` | `processedTimestamp` |

Atharva will finalize OpenSOVD mappings. Each diagnostic fault must expose, where supported: vehicle ID, code, description, severity, status, affected signal, observed value, unit, threshold, timestamps, and correlation ID.

## 8. Minimum Contract Tests

- Accept a complete valid state and reject invalid IDs, ranges, or timestamps.
- Preserve values, units, and source timestamps through mappings.
- Test each fault immediately outside, exactly at, and beyond warning/critical boundaries.
- Test activation persistence, escalation, downgrade, recovery, clearing, and reactivation.
- Test simultaneous faults and maximum-severity aggregation.
- Emit exactly one `FaultDetected` and one `FaultCleared` per lifecycle.
- Verify Kuksa → backend → Ditto/diagnostics/dashboard field consistency.

Detailed test cases and results belong in `testing-and-results.md`.

## 9. Day 2 Approval Checklist

- [ ] Kuksa image and VSS version
- [ ] Exact paths for all seven signal values
- [ ] Temperature source and meaning
- [ ] Types, units, and validation ranges
- [ ] Warning, critical, and clear thresholds
- [ ] Simulator interval and persistence duration
- [ ] Missing, invalid, stale, and disconnected behaviour
- [ ] Fault codes and common payload fields
- [ ] Timestamp precision and ID formats
- [ ] uProtocol event fields and integration level
- [ ] Ditto structure and OpenSOVD mappings
- [ ] Dashboard/API field compatibility
- [ ] Contract tests and acceptance criteria

After approval, replace proposed values with final values, remove resolved checklist items, and record the approving pull request.