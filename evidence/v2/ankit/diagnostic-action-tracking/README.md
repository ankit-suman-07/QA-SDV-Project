# V2 diagnostic action tracking

Starting main `1b7978552d7961e59ec7835e27cd678608f3e33e` includes preparation
#52, the #55/#56 follow-ups and backend projection #57. The implementation
follows [C5–C7](../../../../docs/v2-interface-contracts.md).
[Native feasibility](../../../../docs/v2-native-diagnostic-feasibility.md)
still leaves transport, provider and permissions review open.

## Backend API and persistence

Enable with `sdv.v2.actions.enabled=true`, an absolute private durable file
at `sdv.v2.actions.journal`, and a local secret for `sdv.v2.actions.token`.
All V2 diagnostic routes require that secret as an Authorization bearer token.
Keep it in a trusted service or authorized gateway. Use TLS for cross-host
access. An authorization split finer than the single operator credential
requires the deployment's target-specific policy and review.

`POST /api/v2/diagnostics/actions` takes the shared example, without
fixture metadata:

```json
{"vehicleId":"vehicle-003","actionId":"action-003","traceId":"trace-003","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}
```

Use `CLEAR_SCENARIO` for clear. For `RESTART_APP`, omit scenario or send null.
IDs use letters, digits, periods, underscores or hyphens, start with a
letter or digit and are at most 128 characters. An accepted dispatch returns
202. `GET /api/v2/diagnostics/actions/action-003` returns the authoritative
record with identity, status, request/update/deadline timestamps, reason,
uncertainty and execution/late evidence. An identical retry returns the same
record (202 while ACCEPTED, 200 for later states). A conflicting retry gets
409. While the original acknowledgement is in flight a parallel read or
identical retry returns 503 so the reservation cannot be mistaken for
accepted dispatch. Malformed requests return 400 and unknown targets 404.
Executor rejection returns 409, outage 503 and an uncertain dispatch 504.
Use the original ID to inspect that record. Do not submit a new ID to
compensate for an uncertain delivery.

The journal reserves IDs before dispatch and replaces the file atomically
before promoting state in memory. Use a local filesystem with atomic rename
and run one owning backend with the journal mounted persistently. The lock
prevents concurrent writers to that path. A process interruption with only
a reservation on disk leaves a TIMED_OUT record with dispatch uncertainty
and does not redispatch. The journal bounds each vehicle to the latest 100
records and seven days. Capacity pressure evicts a terminal record before
accepting another. Idempotency is scoped to retained IDs. This is a local
process-restart design, without a replicated journal or a power-loss
durability guarantee.

Bayan can read `GET /api/v2/diagnostics/vehicles/vehicle-003/actions` for the
correlated retained records for that vehicle. This projection does not write
individual twins or health history. The backend polls outstanding records
every 500 ms by default and also polls on action reads. At the execution
deadline the backend marks the record TIMED_OUT with uncertainty. A later
action read can record the first correlated terminal result as late evidence
without changing status or its terminal timestamp.

## Executor handoff for review

- Map each `sdv.v2.actions.scenario-providers[vehicle-00N]` to the intended
  provider base. Spring uses the existing V1 POST `/api/v1/scenarios/actions`
  and exact identity/active acknowledgement validation with a 2 s transport
  deadline. Acceptance alone does not record SUCCEEDED. Clear success
  confirms scenario execution only. Velocitas observes the separate two-second
  health recovery.
- Map `sdv.v2.actions.lifecycle-executors[vehicle-00N]` to a distinct lifecycle
  executor base. This proposed project adapter calls POST `/actions` with
  the same request body and expects HTTP 202 and matching vehicleId, actionId,
  traceId and status ACCEPTED. A missing endpoint returns 503. Restart never
  routes to the scenario provider.
- Map `sdv.v2.actions.results[vehicle-00N]` to an executor result base. GET
  `/actions/{actionId}` uses a 2 s transport deadline. Return JSON with
  vehicleId/actionId/traceId and status EXECUTING, SUCCEEDED or FAILED.
  When the first observed result is SUCCEEDED, include executionStartedAt
  in UTC as evidence of entry into execution. The backend deadline is
  request time +10 s for inject/clear, +30 s for restart. Unavailable result
  reads preserve state until the deadline. The backend never retries a command
  automatically after dispatch.
- Restart SUCCEEDED additionally requires a `restart` object containing
  UTC stoppedAt, startRequestedAt, startedAt and observationSourceTimestamp,
  plus observationEventId and observationSessionId. The timestamps must
  order stop, start request, runtime start and the newer source observation.
  The backend checks the selected vehicle's current trusted AVAILABLE V2
  projection for the same event, session and timestamp. It also compares
  against the pre-dispatch source timestamp when available. A superseding
  twin observation can make an older proof unverifiable with the current
  whole-Thing boundary. Agree how the live executor supplies a matching
  observation during joined review. HTTP acknowledgement alone is insufficient.
- Deployment owners still need to review these project HTTP bindings,
  authorization and TLS configuration before live wiring. No native SDK
  operation or lifecycle service endpoint is assumed available here.

## Explicit fixture mode

Run the existing substitute on loopback:

```sh
python -m scripts.v2_dev.http_mocks --ack-development-only --port 18082 --provider-vehicle vehicle-003
```

Set `sdv.v2.actions.fixture-base=http://127.0.0.1:18082` and map the selected
scenario provider to the same port. Do not configure production result or
lifecycle bases in this mode. Use the substitute's `/_mock/action-result`
control to feed progression. The substitute has no real restart evidence.
Authorized GET `/api/v2/diagnostics/vehicles/{vehicleId}/health` and `/faults`
use the marked project substitute via a 2 s deadline. The marker and
vehicle identity are validated. Without fixture configuration these reads
return 503 until Bayan's native binding is supplied. Fixture mode has no
fallback from a failed live dependency.

## Verification

Applied Ankit verification-before-completion v1.0.0 to trace request validation,
routing, correlation, retention, restart and missed/late delivery to concrete
tests and record the fixture and live boundaries. No versioned Ankit TDD
derivative was available.

- JDK 21, from `backend/`,
  `bash ./mvnw -o --batch-mode --no-transfer-progress clean verify`
  on `7c0f7aa47259db77c3b15bbb2551f0082b789fa0` exited 0. Maven
  reported 221 tests with zero failures, errors or skips and packaged the
  backend. This includes V1 compatibility and authentication regressions.
- After tightening textual result correlation, JDK 21
  `bash ./mvnw -o --batch-mode --no-transfer-progress -Dtest=V2ActionTrackerTest,V2ActionHttpTest test`
  on `e3c9374968f2c2f9a5e78a413f6a9d7d8123b3dd` exited 0.
  Eight tests cover the fixture lifecycle, API and selected-target adapter,
  idempotency, timeout/late evidence, restart and persistence failure.
  An initial compile failed on an enum option absent from Jackson 3.
  Final code checks JSON token types directly and passed the focused suite.
- `python -m scripts.v2_dev.check` and
  `python -m unittest tests.test_v2_http -q` exited 0 with eight shared
  prep tests, 23 fixture files and one loopback HTTP test.
- `git diff --check origin/main HEAD` and local evidence links passed.
  The Java HTTP tests used a loopback executor substitute, shared request
  fixtures and controlled evidence. No CARLA, Kanto, real native diagnostic
  or production executor was started. No owned services remain running.
