# A3 vehicle-specific scenario routing

Implements C2/C8 of `docs/v1-interface-contracts.md` version 1.0.0 (still proposed for affected-owner review). This is a component implementation supporting V1-03, not completion of live V1 acceptance.

## Run with prepared mocks

From the repository root, start the opt-in development services:

```sh
python3 -B -m scripts.v1_dev.http_mocks --ack-development-only --live-clock
```

In another terminal, with Java 21 selected:

```sh
cd backend
bash ./mvnw spring-boot:run -Dspring-boot.run.profiles=v1-mock
```

The actual Spring Boot backend listens on 8082. Its A2 Ditto adapter reads the mock at 19080; scenario actions use provider-001 at 19091 and provider-002 at 19092. The separate mock preview on 19082 is not the backend and must not count as implementation evidence.

```sh
curl -i http://localhost:8082/api/v1/diagnostics/actions \
  -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}'
curl http://localhost:19092/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION
curl http://localhost:19091/api/v1/vehicles/vehicle-001/scenarios/LIDAR_OBSTRUCTION
curl http://localhost:8082/api/v1/vehicles/vehicle-002/state
# Substitute the returned actionId:
curl http://localhost:8082/api/v1/diagnostics/actions/ACTION_ID
curl -i http://localhost:8082/api/v1/diagnostics/actions \
  -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"CLEAR_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}'
```

Use the same GET checks after clear. Mock state changes are synthetic; they do not prove MQTT delivery or real twin recovery.

## Configuration and real providers

| Setting | Environment override | Default |
|---|---|---|
| `sdv.simulator.mode` | `SDV_SIMULATOR_MODE` | `development` |
| `sdv.simulator.providers[vehicle-001]` | `SDV_PROVIDER_001_BASE_URL` | existing `sdv.simulator.base-url` (legacy `SIMULATOR_BASE_URL`, default localhost:8090) |
| `sdv.simulator.providers[vehicle-002]` | `SDV_PROVIDER_002_BASE_URL` | http://localhost:8092 |
| `sdv.simulator.connect-timeout` | `SDV_PROVIDER_CONNECT_TIMEOUT` | 2s |
| `sdv.simulator.read-timeout` | `SDV_PROVIDER_READ_TIMEOUT` | 2s |

The read timeout is a deadline for the whole exchange, including response body reading. HTTP redirects are disabled. Exactly one POST is made; timeouts cancel the local operation but cannot undo provider execution. HTTP mode requires both canonical vehicle mappings. Invalid modes, URLs and nonpositive timeouts fail configuration validation. Provider URLs cannot contain credentials, query strings or fragments.

For real providers, set their actual reachable URLs (example addresses below are placeholders):

```sh
export SDV_SIMULATOR_MODE=http
export SDV_PROVIDER_001_BASE_URL=http://provider-001:8091
export SDV_PROVIDER_002_BASE_URL=http://provider-002:8091
export SDV_PROVIDER_CONNECT_TIMEOUT=2s
export SDV_PROVIDER_READ_TIMEOUT=2s
cd backend
bash ./mvnw spring-boot:run
```

A2 Ditto configuration is independent; see [live twin API setup](v1-live-twin-api.md). Do not select the `v1-mock` profile for real integration. There is no fallback from failed HTTP dispatch to the development adapter. The default development adapter keeps its existing simulated cooling behavior and seven-field acknowledgement; it does not claim `DISPATCHED` without a provider acknowledgement.

## HTTP behavior and handoff

Public POST `/api/v1/diagnostics/actions` accepts `vehicleId`, `action` (`INJECT_SCENARIO` or `CLEAR_SCENARIO`) and `scenario` (`LIDAR_OBSTRUCTION` or existing `COOLING_SYSTEM_FAILURE`). Missing, nontext, unsupported or padded fields produce 400; unknown vehicles produce 404. Validation failures make no provider request. The HTTP adapter supports only vehicle-001/002. Existing development cooling support for the legacy registry is preserved.

Spring generates actionId and traceId and sends all five fields to the selected provider's `/api/v1/scenarios/actions`. A provider must return all five matching values and a boolean `active` equal to true for injection and false for clearing. This is the handoff to Emmanuel: enforce identity locally, return the complete acknowledgement, and expose the vehicle-specific scenario-context GET. Body serialization uses Content-Length for compatibility with the existing Python handler.

A validated acknowledgement yields 202 with `status=ACCEPTED`, `dispatchStatus=DISPATCHED`. No execution completion is inferred. GET `/api/v1/diagnostics/actions/{actionId}` returns the retained acknowledgement or failed submission; unknown actions return 404.

| Outcome | HTTP / code | Stored lifecycle / dispatch |
|---|---|---|
| Provider 4xx | 502 / PROVIDER_REJECTED | REJECTED / REJECTED |
| Refused/reset connection | 503 / PROVIDER_UNAVAILABLE | FAILED / FAILED |
| Deadline exceeded | 504 / PROVIDER_TIMEOUT | FAILED / UNKNOWN |
| Provider 5xx, malformed or mismatched acknowledgement | 502 / PROVIDER_BAD_RESPONSE | FAILED / FAILED |

Errors retain timestamp/code/message/path plus actionId/traceId/dispatchStatus once allocated. Provider bodies, URLs and raw network errors are not exposed. Failed submissions are retained in the existing process-local action store; restart loses that history. Timeout UNKNOWN explicitly leaves provider execution uncertain. Automatic retries and a full execution lifecycle are outside A3.

See [verification evidence](../../evidence/v1/scenario-routing.md) for executed checks and remaining live integration.
