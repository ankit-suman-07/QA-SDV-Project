# V1 individual twin read API (A2)

Spring Boot reads whole Things from Ditto for the two C2 identities and serves:

- `GET /api/v1/vehicles` → `{"vehicleIds":["vehicle-001","vehicle-002"]}`
- `GET /api/v1/vehicles/{vehicleId}/state`
- `GET /api/v1/vehicles/{vehicleId}/health`

State and health return the same C7 projection: `vehicleId`, `thingId`,
`healthStatus`, `availability`, `activeFaults`, `lidar`, `sourceTimestamp`,
`lastEventId`. Unknown, padded and non-V1 IDs return 404 without dispatch.
`vehicle-003` remains a legacy registry entry by default, not a V1 vehicle.

The implementation follows [contract 1.0.0](../../docs/v1-interface-contracts.md),
C2–C7 and A2/V1-04. The contract is still **proposed for affected-owner review**;
this implementation does not claim owner approval or complete live acceptance.

## Configuration

The new read path uses **`sdv.v1.ditto.*`**. Existing `sdv.ditto.mode` selects the
legacy write adapter and is intentionally unchanged. No new dependency is needed.
The new endpoints never consult the generated legacy state provider, even when a
Ditto read fails. Existing `/api/vehicles/{id}/state` and `/health` retain their
old fields and behavior, including initial state population by the legacy scheduler.

| Property | Environment override | Default |
| --- | --- | --- |
| `sdv.v1.ditto.mode` | `SDV_V1_DITTO_MODE` | `live` (`mock` and `live` only) |
| `sdv.v1.ditto.base-url` | `SDV_V1_DITTO_BASE_URL` | `http://localhost:8080` |
| `sdv.v1.ditto.username` | `SDV_V1_DITTO_USERNAME` | unset |
| `sdv.v1.ditto.password` | `SDV_V1_DITTO_PASSWORD` | unset |
| `sdv.v1.ditto.connect-timeout` | `SDV_V1_DITTO_CONNECT_TIMEOUT` | `2s` |
| `sdv.v1.ditto.read-timeout` | `SDV_V1_DITTO_READ_TIMEOUT` | `2s` |
| `sdv.v1.ditto.stale-after` | `SDV_V1_STALE_AFTER` | `5s` |
| `sdv.v1.ditto.unavailable-after` | `SDV_V1_UNAVAILABLE_AFTER` | `30s` |
| `sdv.v1.ditto.things[vehicle-001]` | Spring property binding | `sdv:vehicle-001` |
| `sdv.v1.ditto.things[vehicle-002]` | Spring property binding | `sdv:vehicle-002` |

The map binds as typed configuration and must match the two contract identities;
unknown keys or cross-vehicle Thing mappings fail startup. This is deliberately
separate from the legacy registry's broader configuration. Mode, nonempty HTTP(S)
base URL, positive timeouts, `0 < stale < unavailable`, and paired Basic credentials
are validated at startup. URL credentials/query/fragment are rejected. Base URLs
may include a deployment prefix, before `/api/2/things/{thingId}`.

Both modes perform actual HTTP reads. `mock` labels the explicitly selected mock
configuration; it never supplies an in-process generated snapshot. No replay,
preview or Python development module is imported by production Java code.

For live Ditto, leave the mock profile inactive, set `SDV_V1_DITTO_MODE=live` and
configure `SDV_V1_DITTO_BASE_URL` to your agreed HTTP(S) deployment. Set both Basic
authentication variables using your local secret mechanism if authentication is
required. No credentials are committed or loaded from `.env` automatically.
Default JDK TLS certificate validation remains enabled. Mock authentication is
not evidence of real Ditto policy enforcement.

## Run real Spring Boot against the prepared mock

Use Java 21 and the Maven wrapper. From the repository root, terminal one:

```bash
python3 -B -m scripts.v1_dev.http_mocks --ack-development-only --live-clock
```

This starts the **prepared HTTP mocks**, including Ditto at `127.0.0.1:19080`.
The preview backend at 19082 is not this Spring Boot implementation and is not
used below. `--live-clock` rebases the entire initial sequence, then observations
age naturally. Without it, the default January fixtures correctly appear old to
a production UTC clock. Automated backend tests instead inject a fixed clock at
`2026-01-01T00:00:04Z` against the canonical January fixtures.

Terminal two:

```bash
cd backend
bash ./mvnw --batch-mode --no-transfer-progress clean verify
bash ./mvnw spring-boot:run -Dspring-boot.run.profiles=v1-mock
```

Alternatively, after packaging, from the repository root:

```bash
java -jar backend/target/backend-0.0.1-SNAPSHOT.jar --spring.profiles.active=v1-mock
```

The opt-in `v1-mock` profile explicitly sets mode `mock` and the prepared Ditto
URL. Override it with `SDV_V1_DITTO_BASE_URL` for your isolated mock port.
`SERVER_PORT` overrides Spring Boot's default 8082. Do not activate this profile
when configuring live Ditto.

Terminal three, refreshing both observations after Spring has started:

```bash
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-001 -H 'Content-Type: application/json' -d '{"state":"healthy"}'
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"healthy"}'
curl -fsS http://127.0.0.1:8082/api/v1/vehicles
curl -fsS http://127.0.0.1:8082/api/v1/vehicles/vehicle-002/state
curl -fsS http://127.0.0.1:8082/api/v1/vehicles/vehicle-002/health
curl -fsS http://127.0.0.1:19080/api/2/things/sdv:vehicle-002
```

Compare original `sourceTimestamp` and `lastEventId` between the last read and
Spring Boot's projections; polling does not refresh them. Fresh healthy data has
`healthStatus=HEALTHY`, `availability=AVAILABLE`, empty faults and LiDAR distance
35 m. Refreshing through the mock is a new synthetic observation, not a simulator
command. For fault/recovery/isolation and failure checks:

```bash
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"fault"}'
curl -fsS http://127.0.0.1:8082/api/v1/vehicles/vehicle-002/state
curl -fsS http://127.0.0.1:8082/api/v1/vehicles/vehicle-001/state
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"recovered"}'
curl -fsS http://127.0.0.1:8082/api/v1/vehicles/vehicle-002/state
```

Repeat with mock states `stale`, `missing`, and `unavailable`. Stale is a trusted
six-second-old observation. Missing (HTTP 404) or unavailable (HTTP 503) produce
HTTP 200 from the registered vehicle endpoint with `UNAVAILABLE` and explicit
null health/fault/LiDAR/source/event fields. Stop only your own mock process and
repeat a registered vehicle read to verify connection failure does not generate
healthy state. Stop the Spring process you started afterward.

## Validation, availability and failures

Reads require HTTP 200 and matching `thingId`, `attributes.vehicleId` and
`features.v1.properties.vehicleId`. Schema must be `1.0.0`; required fields,
nonblank event/context IDs, UTC timestamp, finite nonnegative numeric distance,
boolean sensor state and C4 health/fault consistency are checked without coercion.
Duplicate JSON keys, trailing JSON, malformed UTF-8/JSON and lone Unicode
surrogates are rejected. Extensions are traversed without recursive copying;
only the typed compact projection is returned. Whole-Thing responses are bounded
to 1 MiB before parsing; Jackson's standard structural/number limits also apply
(in this dependency version, maximum nesting 500). Unusable input yields an
untrusted unavailable projection, not an exception/retry loop. This is an HTTP
read safety bound, not a change to the MQTT wire contract or fixtures.

The existing injected `Clock` defaults to UTC. Evaluation occurs after the read,
using source time, with exact decimal fractional comparisons (including fractions
beyond Java Instant nanoseconds), and preserves original timestamp text:

| Source age at evaluation | Result |
| --- | --- |
| More than 1 s in future | UNAVAILABLE, all snapshot fields null |
| Up to 1 s future through exactly stale threshold | AVAILABLE |
| Greater than stale through exactly unavailable threshold | STALE |
| Greater than unavailable threshold | UNAVAILABLE, trusted last-known fields retained |
| Missing/failed/invalid read | UNAVAILABLE, all snapshot fields null |

A fresh sensor-failure observation is AVAILABLE/CRITICAL. Last-known valid stale
or expired health is not relabeled healthy/current. There is no cache fallback.

One bounded GET is attempted per read; no retries, writes or aggregate operations
are performed. Connect and response/body read timeouts are separate, configurable
limits, not a measured end-to-end latency guarantee. Redirects are disabled.
Unexpected 2xx, 3xx, 4xx and 5xx are unavailable. Authentication 401/403 produces
an error log with `code=AUTH_CONFIGURATION`; other safe codes include `HTTP_STATUS`,
`TRANSPORT_UNAVAILABLE`, `INVALID_SNAPSHOT`, `RESPONSE_TOO_LARGE` and
`FUTURE_SOURCE_TIMESTAMP`. Logs expose registered vehicle/status/code, never raw
response content, credential values, URLs or dependency exception text.

## Verification and handoff

See [A2 evidence](../../evidence/v1/live-twin-api.md). Unit/API tests include
MockRestServiceServer, real loopback HTTP, bounded timeout/refused connection,
fixed-clock boundaries, both identities, invalid snapshots, redacted errors and
legacy endpoint regressions. The independent smoke run used the actual packaged
Spring Boot process against the prepared Python Ditto mock, not its preview API.

Real Ditto authorization, actual publisher observations, disconnected-source
behavior against the live deployment, and affected-owner contract review remain
pending. Bayan supplies individual twins; Ankit A3/A5 implements scenario routing
and fleet aggregation separately. No fleet, scenario, dashboard, CI expansion,
CARLA, Kanto, uProtocol or OpenSOVD implementation is included here.
