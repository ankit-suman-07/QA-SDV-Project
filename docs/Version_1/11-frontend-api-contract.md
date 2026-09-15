# SDV Frontend API and Data Contract

This document defines the backend APIs that may be consumed by the SDV frontend dashboard, the expected request and response data, and the mock data to use while unfinished endpoints are being implemented.

## 1. Integration boundary

The frontend must communicate only with the Spring Boot backend.

```text
Frontend -> Spring Boot REST API -> SDV components
```

The browser must not connect directly to Eclipse Kuksa, Eclipse Ditto, Eclipse uProtocol, Eclipse OpenSOVD, the simulator, or Docker containers.

## 2. API configuration

| Setting | Value |
|---|---|
| Local base URL | `http://localhost:8080` |
| Content type | `application/json` |
| Authentication | None in the current local-development scope |
| Supported vehicle | `vehicle-001` |
| Timestamp format | ISO-8601 UTC, such as `2026-08-03T17:00:00Z` |
| Recommended GET timeout | 5 seconds |
| Recommended dashboard polling interval | 2 seconds |
| Recommended action-status polling interval | 1 second |

Recommended environment variable:

```env
VITE_API_BASE_URL=http://localhost:8080
```

## 3. Endpoint summary

| Status | Method | Endpoint | Frontend use |
|---|---|---|---|
| Ready | `GET` | `/api/vehicles/{vehicleId}/state` | Read the current temperature, coolant pressure, vehicle ID, and source timestamp |
| Ready | `GET` | `/api/vehicles/{vehicleId}/health` | Read the calculated vehicle health status |
| Ready | `POST` | `/api/v1/diagnostics/actions` | Inject or clear a diagnostic scenario |
| In progress | `GET` | `/api/v1/diagnostics/actions/{actionId}` | Retrieve the latest state of a submitted diagnostic action |
| Planned | WebSocket | Path not finalized | Receive live vehicle updates without polling |
| Planned | `GET` | Path not finalized | Retrieve performance and experiment results |

`Ready` means the frontend may connect to the endpoint now. `In progress` means the frontend should implement its API method and use the mock response until the backend endpoint is finished. `Planned` means no URL should be hard-coded yet.

---

## 4. Get current vehicle state

### Request

```http
GET /api/vehicles/vehicle-001/state
```

No request body is required.

### Successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "vehicleId": "vehicle-001",
  "sourceTimestamp": "2026-08-03T16:00:00Z",
  "temperatureCelsius": 89.0,
  "coolantPressureKpa": 200.0
}
```

### Response fields

| Field | Type | Required | Frontend use |
|---|---|---:|---|
| `vehicleId` | String | Yes | Verify and display the selected vehicle |
| `sourceTimestamp` | ISO-8601 string | Yes | Display last-updated time and calculate freshness |
| `temperatureCelsius` | Number | Yes | Display the current temperature in °C |
| `coolantPressureKpa` | Number | Yes | Display the current coolant pressure in kPa |

### TypeScript model

```ts
export interface VehicleStateResponse {
  vehicleId: string;
  sourceTimestamp: string;
  temperatureCelsius: number;
  coolantPressureKpa: number;
}
```

### Frontend behavior

- Poll this endpoint every two seconds until a live-update contract is available.
- Use `sourceTimestamp`, not the browser request time, to calculate freshness.
- If the timestamp is more than five seconds old, show a `Stale` warning.
- On a temporary request failure, preserve the last successful values and show `Disconnected`.
- Do not expect speed, battery level, or tire pressure in this response yet.

### Unsupported vehicle example

```http
GET /api/vehicles/vehicle-999/state
```

Expected result: `404 Not Found` using the standard error format described later in this document.

---

## 5. Get current vehicle health

### Request

```http
GET /api/vehicles/vehicle-001/health
```

No request body is required.

### Successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "vehicleId": "vehicle-001",
  "healthStatus": "CRITICAL"
}
```

### Response fields

| Field | Type | Required | Allowed values |
|---|---|---:|---|
| `vehicleId` | String | Yes | `vehicle-001` |
| `healthStatus` | String enum | Yes | `HEALTHY`, `WARNING`, `CRITICAL` |

### TypeScript model

```ts
export type HealthStatus =
  | "HEALTHY"
  | "WARNING"
  | "CRITICAL";

export interface VehicleHealthResponse {
  vehicleId: string;
  healthStatus: HealthStatus;
}
```

### Status presentation

| Value | Meaning | Recommended UI |
|---|---|---|
| `HEALTHY` | No current rule indicates a warning or critical condition | Green status badge |
| `WARNING` | A warning condition is present | Amber status badge |
| `CRITICAL` | A critical condition is present, including a correlated cooling-system failure | Red status badge and alert treatment |

### Current limitation

The response does not currently include an `activeFaults` collection. The frontend must not assume a particular fault code solely because `healthStatus` is `CRITICAL`.

Until an active-fault contract is added, use mock fault data only in mock/demo mode and label it accordingly.

---

## 6. Submit a diagnostic action

### Endpoint

```http
POST /api/v1/diagnostics/actions
Content-Type: application/json
```

This endpoint is used both to inject and clear a diagnostic scenario.

### Inject the cooling-system-failure scenario

```json
{
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE"
}
```

### Clear the cooling-system-failure scenario

```json
{
  "vehicleId": "vehicle-001",
  "action": "CLEAR_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE"
}
```

### Request fields

| Field | Type | Required | Allowed values |
|---|---|---:|---|
| `vehicleId` | String | Yes | `vehicle-001` |
| `action` | String enum | Yes | `INJECT_SCENARIO`, `CLEAR_SCENARIO` |
| `scenario` | String enum | Yes | `COOLING_SYSTEM_FAILURE` |

### TypeScript request model

```ts
export type DiagnosticAction =
  | "INJECT_SCENARIO"
  | "CLEAR_SCENARIO";

export type DiagnosticScenario =
  | "COOLING_SYSTEM_FAILURE";

export interface DiagnosticActionRequest {
  vehicleId: string;
  action: DiagnosticAction;
  scenario: DiagnosticScenario;
}
```

### Accepted response

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "actionId": "action-001",
  "traceId": "action-001",
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE",
  "status": "ACCEPTED",
  "requestedAt": "2026-08-03T17:00:00Z"
}
```

### Response fields

| Field | Type | Required | Frontend use |
|---|---|---:|---|
| `actionId` | String | Yes | Display it and use it to retrieve action status |
| `traceId` | String | Yes | Display in action details and use for traceability |
| `vehicleId` | String | Yes | Identify the affected vehicle |
| `action` | String enum | Yes | Show whether the scenario was injected or cleared |
| `scenario` | String enum | Yes | Show the requested scenario |
| `status` | String enum | Yes | Show the current action state |
| `requestedAt` | ISO-8601 string | Yes | Display when the action was accepted |

### TypeScript response model

```ts
export type DiagnosticActionStatus =
  | "ACCEPTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "FAILED"
  | "REJECTED";

export interface DiagnosticActionResponse {
  actionId: string;
  traceId: string;
  vehicleId: string;
  action: DiagnosticAction;
  scenario: DiagnosticScenario;
  status: DiagnosticActionStatus;
  requestedAt: string;
}
```

### Required frontend behavior

- Show a confirmation dialog before sending either action.
- Disable both action buttons while the request is being submitted.
- Prevent duplicate requests caused by repeated clicks or Enter key presses.
- Display the exact `actionId`, `traceId`, `status`, and `requestedAt` returned by the backend.
- Do not claim that the vehicle state changed merely because the request was accepted.
- Do not automatically retry this POST request. A timeout does not prove that the backend failed to accept it.
- After receiving `202 Accepted`, begin action-status polling when the GET action endpoint becomes available.

### Validation error example

Request:

```json
{
  "vehicleId": "",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE"
}
```

Response:

```http
HTTP/1.1 400 Bad Request
```

```json
{
  "timestamp": "2026-08-03T21:50:13Z",
  "code": "VALIDATION_ERROR",
  "message": "vehicleId: must not be blank",
  "path": "/api/v1/diagnostics/actions"
}
```

### Unsupported vehicle example

```json
{
  "vehicleId": "vehicle-999",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE"
}
```

Expected response:

```http
HTTP/1.1 404 Not Found
```

```json
{
  "timestamp": "2026-08-03T21:50:13Z",
  "code": "VEHICLE_NOT_FOUND",
  "message": "Unsupported vehicle ID: vehicle-999",
  "path": "/api/v1/diagnostics/actions"
}
```

---

## 7. Get diagnostic action status

> **Backend status:** In progress. The frontend may create the API method now but must use mock data until the endpoint is completed and confirmed.

### Expected request

```http
GET /api/v1/diagnostics/actions/action-001
```

### Expected successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "actionId": "action-001",
  "traceId": "action-001",
  "vehicleId": "vehicle-001",
  "action": "INJECT_SCENARIO",
  "scenario": "COOLING_SYSTEM_FAILURE",
  "status": "COMPLETED",
  "requestedAt": "2026-08-03T17:00:00Z"
}
```

The response uses the same `DiagnosticActionResponse` model returned by the POST endpoint.

### Expected action-state behavior

| Status | Frontend behavior |
|---|---|
| `ACCEPTED` | Show accepted and continue polling |
| `IN_PROGRESS` | Show progress and continue polling |
| `COMPLETED` | Stop polling and refresh vehicle state and health |
| `FAILED` | Stop polling and show an error message |
| `REJECTED` | Stop polling and explain that the request was rejected |

### Recommended polling behavior

- Poll once per second while the status is `ACCEPTED` or `IN_PROGRESS`.
- Stop polling when the status is terminal: `COMPLETED`, `FAILED`, or `REJECTED`.
- Stop polling when the page unmounts.
- Apply a configurable maximum polling duration.
- If the maximum duration expires, show `Action status unknown`; do not automatically resubmit the POST request.

### Expected unknown-action response

This response must remain mocked until the backend exception contract is finalized.

```http
HTTP/1.1 404 Not Found
```

```json
{
  "timestamp": "2026-08-03T21:55:00Z",
  "code": "ACTION_NOT_FOUND",
  "message": "Diagnostic action not found: action-999",
  "path": "/api/v1/diagnostics/actions/action-999"
}
```

---

## 8. Standard API error response

All handled backend errors should be normalized into this shape:

```ts
export interface ApiErrorResponse {
  timestamp: string;
  code: string;
  message: string;
  path: string;
}
```

Example:

```json
{
  "timestamp": "2026-08-03T21:50:13Z",
  "code": "VALIDATION_ERROR",
  "message": "scenario: must not be null",
  "path": "/api/v1/diagnostics/actions"
}
```

### Error handling table

| HTTP status | Typical code | Frontend behavior |
|---:|---|---|
| `400` | `VALIDATION_ERROR` | Show the message beside the form and focus the invalid field |
| `404` | `VEHICLE_NOT_FOUND` | Show that the selected vehicle is unsupported |
| `404` | `ACTION_NOT_FOUND` | Stop action polling and show that the action could not be found |
| `408` or client timeout | Varies | Show timeout; retry safe GET requests only |
| `500-599` | Varies | Show server unavailable and preserve last successful dashboard data |
| Network failure | No JSON body | Show disconnected and provide a manual Retry button |

If the response body does not match `ApiErrorResponse`, use a generic message such as `The service is currently unavailable.`

---

## 9. Mock-only frontend data

The following fields appear in the dashboard design but are not currently returned by the Spring Boot vehicle-state endpoint:

- `speedKph`
- `batteryPercent`
- `tirePressurePsi`
- `activeFaults`

Keep them inside mock fixtures rather than adding them to the real API response model.

### Normal dashboard fixture

```json
{
  "state": {
    "vehicleId": "vehicle-001",
    "sourceTimestamp": "2026-08-03T16:00:00Z",
    "temperatureCelsius": 89.0,
    "coolantPressureKpa": 200.0
  },
  "health": {
    "vehicleId": "vehicle-001",
    "healthStatus": "HEALTHY"
  },
  "mockTelemetry": {
    "speedKph": 64.0,
    "batteryPercent": 81.0,
    "tirePressurePsi": 32.0,
    "activeFaults": []
  }
}
```

### Correlated cooling-failure fixture

```json
{
  "state": {
    "vehicleId": "vehicle-001",
    "sourceTimestamp": "2026-08-03T16:05:00Z",
    "temperatureCelsius": 105.0,
    "coolantPressureKpa": 150.0
  },
  "health": {
    "vehicleId": "vehicle-001",
    "healthStatus": "CRITICAL"
  },
  "mockTelemetry": {
    "speedKph": 60.0,
    "batteryPercent": 80.0,
    "tirePressurePsi": 32.0,
    "activeFaults": ["COOLING_SYSTEM_FAILURE"]
  }
}
```

### Recovery fixture

```json
{
  "state": {
    "vehicleId": "vehicle-001",
    "sourceTimestamp": "2026-08-03T16:06:00Z",
    "temperatureCelsius": 100.0,
    "coolantPressureKpa": 180.0
  },
  "health": {
    "vehicleId": "vehicle-001",
    "healthStatus": "HEALTHY"
  },
  "mockTelemetry": {
    "speedKph": 61.0,
    "batteryPercent": 79.0,
    "tirePressurePsi": 32.0,
    "activeFaults": []
  }
}
```

Do not send `mockTelemetry` to the backend and do not describe these values as live backend data while mock mode is enabled.

---

## 10. Mock performance data

No performance-results API is currently finalized. The Performance & Testing page should initially load a local fixture or repository-generated experiment data.

```json
{
  "generatedAt": "2026-08-03T20:00:00Z",
  "testSummary": {
    "backend": {
      "passed": 25,
      "total": 25
    },
    "python": {
      "passed": 34,
      "total": 34
    }
  },
  "experiments": [
    {
      "intervalSeconds": 5.0,
      "messageCount": 30,
      "averageLatencyMs": 316.997,
      "p95LatencyMs": 466.788,
      "throughputMessagesPerSecond": 0.194,
      "successRatePercent": 100.0
    },
    {
      "intervalSeconds": 1.0,
      "messageCount": 30,
      "averageLatencyMs": 227.832,
      "p95LatencyMs": 730.731,
      "throughputMessagesPerSecond": 0.823,
      "successRatePercent": 100.0
    },
    {
      "intervalSeconds": 0.2,
      "messageCount": 30,
      "averageLatencyMs": 150.202,
      "p95LatencyMs": 235.013,
      "throughputMessagesPerSecond": 2.848,
      "successRatePercent": 100.0
    }
  ]
}
```

Keep performance-data access behind a `performanceApi` interface so a future real endpoint can replace the fixture without changing the page components.

---

## 11. API client responsibilities

The frontend API layer should expose functions similar to:

```ts
export interface VehicleApi {
  getState(vehicleId: string): Promise<VehicleStateResponse>;
  getHealth(vehicleId: string): Promise<VehicleHealthResponse>;
}

export interface DiagnosticApi {
  submitAction(
    request: DiagnosticActionRequest
  ): Promise<DiagnosticActionResponse>;

  getAction(
    actionId: string
  ): Promise<DiagnosticActionResponse>;
}
```

Page components must not contain raw `fetch` calls. The API layer must own:

- Base URL construction
- Request methods and JSON headers
- Timeout and request cancellation
- JSON parsing
- Error normalization
- Mock-versus-real implementation switching

## 12. Final frontend contract checklist

- [ ] API base URL comes from an environment variable.
- [ ] Only `vehicle-001` is sent in the current scope.
- [ ] State and health GET requests use the documented response types.
- [ ] Diagnostic actions use the exact enum strings documented above.
- [ ] Diagnostic POST requests are never retried automatically.
- [ ] Action IDs and trace IDs are treated as opaque strings.
- [ ] Action lookup remains mocked until the backend endpoint is confirmed.
- [ ] Speed, battery, tire pressure, and active faults are not added to the real state/health models prematurely.
- [ ] Planned WebSocket and performance URLs are not hard-coded.
- [ ] All errors are converted to one frontend error model.
- [ ] Last successful dashboard values remain visible during temporary failures.
- [ ] Mocks and real APIs expose identical frontend method signatures.
