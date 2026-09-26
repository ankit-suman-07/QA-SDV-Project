# Week 1 - Messaging and Digital Twin Audit

## 1. Current Transport Audit

### Already Supported
- `vehicle_id`
- `event_id`
- `trace_id`
- optional `action_id`
- `event_type`
- `schema_version`
- source timestamp
- publication timestamp
- Protobuf serialization/deserialization
- duplicate detection
- invalid parse tracking

### Missing / Needs Review
- `sequence_number` is required by the Week 1 event-envelope contract but is not currently defined in `EventMetadata`.
- No per-vehicle ordering mechanism is implemented.
- Metadata validation is currently limited.
- Real network transport is not implemented; messages are delivered in-process.
- Duplicate-processing behavior needs review.
- Multi-vehicle isolation tests are needed.

### Confirmed EventMetadata Fields
- `schema_version`
- `event_id`
- `trace_id`
- optional `action_id`
- `vehicle_id`
- `event_type`
- `source_timestamp`
- `publication_timestamp`

### Note
- `reception_timestamp` is intentionally recorded at receive time and is not part of the outbound wire message.

---

## 2. Ditto HTTP Helper Audit

- `ditto_http.py` is generic and does not hard-code vehicle IDs, Ditto thing IDs, namespaces, or feature names.
- PUT and GET URLs are passed in by callers.
- Retry behavior is already implemented for transient HTTP failures.
- Multi-vehicle routing logic is not implemented in this file and must be handled by higher-level bridge or Ditto code.

---

## 3. Fault Details Audit

- `fault_details.py` does not hard-code any vehicle ID or Ditto thing ID.
- The module is vehicle-agnostic.
- Fault code, description, affected signal names, severity, activation thresholds, and recovery thresholds are hard-coded.
- The module builds correlated fault details including `eventId`, `traceId`, and optional `actionId`.
- Multi-vehicle routing is not handled in this file.
- Threshold and fault definitions may need configuration in future iterations, but they are not a Week 1 multi-vehicle blocker.

---

## 4. Ditto Provisioning Audit

- Current provisioning is hard-coded for a single vehicle.
- Current Policy ID: `sdv:vehicle-001-policy`
- Current Thing ID: `sdv:vehicle-001`
- A deterministic `vehicleId -> Ditto thing ID / policy ID` mapping is required for multi-vehicle support.
- The current Kuksa-to-Ditto bridge is temporary.
- The existing workflow assumes one running vehicle twin.
- The current OpenSOVD diagnostic action implementation is a standalone adapter, not a full write-capable OpenSOVD gateway.
- The Spring Boot backend URL used by the action adapter is currently a placeholder.
- Current correlated-fault behaviour is centered on `COOLING_SYSTEM_FAILURE` with fixed thresholds.

---

## 5. Interim Kuksa-to-Ditto Bridge Audit

### Hard-Coded Single-Vehicle Assumptions
- `DITTO_URL` is hard-coded to `sdv:vehicle-001`.
- `vehicle_id="vehicle-001"` is hard-coded when publishing:
  - vehicle status
  - correlated fault detected
  - correlated fault cleared
- Kuksa connection is hard-coded to `127.0.0.1:55556`.

### Runtime State
The bridge currently maintains one set of runtime fault state:
- `battery_fault_active`
- `cooling_fault_active`
- `active_fault_details`

### Ditto Updates
All telemetry, health, and diagnostics updates are written to one vehicle twin.

### Week 2 Changes Required
The bridge must become vehicle-aware by resolving:
- vehicle-specific Kuksa source/configuration
- `vehicleId`
- Ditto thing ID
- per-vehicle fault state
- per-vehicle routing

---

## 6. OpenSOVD Fault Mapper Audit

- `fault_mapper.py` maps Ditto fault data into OpenSOVD-compatible diagnostic resources.
- The mapper is mostly vehicle-agnostic when processing a provided Ditto thing.
- Fault definitions, thresholds, signal names, and severity rules are hard-coded.
- `build_diagnostic_resource()` defaults `vehicle_id` to `"vehicle-001"`.
- The default vehicle ID must be removed or made explicit/configurable for multi-vehicle support.
- The mapper already preserves trace and action identifiers when available.
- The current OpenSOVD gateway is treated as read-only; this module only produces compatible resource shapes.

---

## 7. OpenSOVD Action Adapter Audit

- `DEFAULT_BACKEND_URL` is hard-coded to `http://localhost:8082`.
- Supported diagnostic actions are currently limited to:
  - `INJECT_SCENARIO`
  - `CLEAR_SCENARIO`
- Supported scenarios are currently limited to:
  - `COOLING_SYSTEM_FAILURE`
- `SUPPORTED_VEHICLE_IDS` is hard-coded to only `vehicle-001`.
- Requests for other vehicles currently return `VEHICLE_NOT_FOUND`.
- The adapter already forwards `vehicleId`, `action`, and `scenario` to the Spring Boot backend.
- Multi-vehicle support will require replacing the fixed supported vehicle set with configurable or dynamically resolved vehicle IDs.
- The adapter includes structured error handling for timeout, unavailable backend, backend errors, and invalid responses.
- This module is OpenSOVD-compatible, not a complete production OpenSOVD implementation.

---

## 8. Current Event Flow

Current single-vehicle flow:

`Kuksa -> Interim Bridge -> uProtocol/Protobuf -> Ditto vehicle-001 -> OpenSOVD Fault Mapper`

### Current Single-Vehicle Blockers

#### Messaging
- `sequence_number` missing
- no per-vehicle ordering
- limited metadata validation

#### Bridge
- `vehicle-001` hard-coded
- Ditto URL hard-coded
- one Kuksa endpoint
- one shared set of fault state

#### Ditto
- one hard-coded vehicle thing
- one hard-coded policy
- provisioning is single-vehicle

#### OpenSOVD Fault Mapper
- default `vehicle_id="vehicle-001"`

#### OpenSOVD Action Adapter
- `SUPPORTED_VEHICLE_IDS={"vehicle-001"}`
- backend URL hard-coded

---

## 9. Week 2 Vehicle-Aware Changes Identified

The following components must become vehicle-aware in Week 2:

- event envelope and ordering
- bridge routing
- Kuksa source configuration
- Ditto thing mapping
- per-vehicle fault state
- Ditto provisioning
- OpenSOVD diagnostic resource generation
- diagnostic action validation
- multi-vehicle isolation tests
