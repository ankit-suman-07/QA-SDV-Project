# V2 independent development

Shared package version **2.0.0-prep.1**. Start all component branches from the
**same merged preparation commit**, not a teammate's unfinished branch. After this
draft is reviewed/merged, Ankit records the merged SHA in the team handoff. Everyone
runs `git fetch origin`, checks out that exact SHA and creates their own branch.
If squash merged, use the resulting main commit, not an earlier preparation SHA.
Baseline before preparation: `140e6ffe4b939cb643654d862e46cd5a83be4d74`.

Read [contracts](v2-interface-contracts.md), [native feasibility](v2-native-diagnostic-feasibility.md),
[task cards](13-FINAL-phase-v2-tasks-and-acceptance.md) and
[preparation evidence](../evidence/v2/preparation.md). New defaults are project-lead
decisions for review; independent mock-tested code is not live acceptance.

## Minimal setup and commands

From repository root, Python **3.10+ standard library only**; no pip install,
CARLA, Java, Kanto, Ditto or teammate service for offline checks:

```bash
python -m scripts.v2_dev.check
python -m unittest tests.test_v2_http -q
python -m scripts.v2_dev.replay --ack-development-only --sequence recovery --vehicle vehicle-003
python -m scripts.v2_dev.http_mocks --ack-development-only --port 18082
```

HTTP mock remains in foreground; Ctrl+C stops only that process. It binds
127.0.0.1, frozen epoch by default, advertises X-SDV-Mock, and supports only documented
routes. Another terminal can read `http://127.0.0.1:18082/api/v2/fleet` or
`/api/v2/vehicles/vehicle-003/state`. Frontend preview: explicitly point the owner's
configurable API base to this mock URL; preview is synthetic, not a dashboard live
profile. Example provider base and Ditto base can both point to the mock for the
supported routes. Live URLs must be configured separately; no fallback logic.

Clock rebase and control:

```bash
python -m scripts.v2_dev.http_mocks --ack-development-only --port 18083 --anchor 2026-11-17T12:00:00Z
python -m scripts.v2_dev.replay --ack-development-only --anchor 2026-11-17T12:00:00Z --kind health
curl -X POST http://127.0.0.1:18083/_mock/clock -H 'Content-Type: application/json' -d '{"now":"2026-11-17T12:00:06Z"}'
```

Rebase whole sequences once. JSONL feeder emits topic/payload/evaluationTime;
consume stdin/file in component test adapters, injecting the evaluation clock.
Replay is deterministic and immediate, not real-time pacing. Clock-only silence
steps emit a control record without payload; a test harness advances time without
feeding an observation (MQTT publication skips these controls). It never writes
KUKSA directly: Ankit's adapter under test does that. `--kind health` converts
accepted source vectors into mock health envelopes for twin/backend development.
Observation mode deliberately preserves negative deliveries. Source silence must
be tested by advancing the injected clock without delivering new observations.

## HTTP subset and negative cases

- GET `/api/2/things/sdv:vehicle-00N` or `/features/v2/properties`; ETag provided.
- PUT feature properties: valid complete V2 envelope, `eventId` renamed lastEventId;
  existing feature requires If-Match; absent feature requires If-None-Match `*`.
  201 create/204 replace; 428 missing condition, 412 failed condition, 409 ordering,
  400 invalid shape/identity. Only V2 feature changes; legacy data preserved.
- GET `/api/v2/vehicles`, `/api/v2/vehicles/{id}/state`, `/api/v2/fleet` are preview.
- POST `/api/v2/diagnostics/actions` or provider `/api/v1/scenarios/actions` accepts
  the [request](../tests/fixtures/v2/diagnostics/request.json). IDs are required.
  Backend returns 202 ACCEPTED; provider preserves V1 HTTP 200 with request
  identity and `active` scenario flag. That mock flag is not a recovery observation.
  Provider identity defaults to vehicle-002; choose `--provider-vehicle vehicle-003`
  for that provider (different target 404). Run separate ports for per-vehicle
  providers. Provider rejects RESTART_APP (422); acceptance never changes sensor input.
- GET `/api/v2/diagnostics/actions/{id}` tracks status. Explicit test control
  POST `/_mock/action-result` with vehicleId/actionId/traceId/status drives
  EXECUTING then SUCCEEDED/FAILED. Advance `/_mock/clock` past deadline for timeout.
- POST `/_mock/failure` with `{"mode":"reject"}`, `unavailable`, `timeout`, `none`
  selects 409/503/504/normal. Timeout response models uncertainty immediately,
  not a measured network delay. Unknown routes/targets 404; malformed bodies 400.
- GET `/mock/v2/diagnostics/{id}/health` or `/faults` is a project mock, never
  native uProtocol or OpenSOVD. Mock authentication/policies/TLS are not implemented.

Mock state is ephemeral: restart resets fixtures/actions. Real owners must persist
watermarks/history and implement auth, bounded network calls and retries. The mock
rejects unregistered session changes; session-registration negotiation belongs to
ingress, not a public production control endpoint. No generic success handler.

## Owner workflows and coverage matrix

Each row maps every task in the final V2 task cards, including work requiring live
handoff. `check` means the shared `python -m scripts.v2_dev.check`; `HTTP` means
`python -m unittest tests.test_v2_http -q`. These validate the substitutes; owners
must add component checks using the same literal expected results.

| Owner/task → real component/files | Contract | Input → expectation / substitute / offline check | Final live handoff/dependency |
|---|---|---|---|
| Ankit: technical baseline/contracts; docs/, shared fixture review | C1–C7 | all fixture references; check + HTTP | affected-owner review, native decisions |
| Ankit: adapter/KUKSA; new adapter module + vehicle-simulator signal boundary | C1–C4 | observations/cases.json, three vehicle files; JSONL feeder → units/identity/time validated; check | Emmanuel real observations; per-vehicle broker metadata + companion binding |
| Ankit: backend/fleet/dashboard; backend/, frontend/, fleet Thing provisioning | C5–C6 | twins/ + fleet-cases.json → exact 3-vehicle counts; HTTP preview | Bayan real twins; same-time API/materialized fleet/UI agreement |
| Ankit: action tracking; backend diagnostics/history | C6 | diagnostics/cases.json → accepted/executing/terminal/mismatch; provider mock; check + HTTP | Bayan native services + Emmanuel scenario executor + Kanto restart executor |
| Ankit: integration/CI/measurements/release; integration scripts, evidence/v2 | C1–C7 | deterministic sequence timing/isolation baseline, check + HTTP | real three-vehicle stack; repeated measurement, CPU/memory, report/video/reviews |
| Bayan: health/recovery; velocitas-app/app/src | C2/C4 | sequences/ + observations/cases.json → boundary/window/reset outcomes; feeder; check | Ankit KUKSA+companion identity and Emmanuel source cadence |
| Bayan: individual twins/history; ditto/ ingress/provisioning | C5 | health-events/, twins/, cached/session sequences → reject corruptions, preserve watermark; HTTP conditional writes | real Ditto ACLs/persistence/restart/history retention |
| Bayan: uProtocol; uprotocol/ | C6 + feasibility | diagnostics request/results, project health mock; check | pinned transport, protobuf service/addressing, real correlated sender/receiver spike |
| Bayan: OpenSOVD; opensovd/ | C6 + feasibility | diagnostics/faults.json → honest project mapping; project fault mock; check | supported provider/version + actual vehicle fault read |
| Bayan: Kanto coordinated with Ankit; kanto/ descriptors | C2/C6 | session/restart vectors + restart action timeout; check | Linux Kanto, real fresh post-start observation and isolation; duplicate publishers excluded |
| Emmanuel: CARLA runtime/three actors; new CARLA source module/config | C1/C3 | three identity files and extraction vectors → stable mappings; check | compatible pinned CARLA/client, map/settings/manifest; owned actor cleanup |
| Emmanuel: extraction/replay handoff; CARLA extraction module | C2/C3 | synthetic front frames → minimum x / empty invalid rules; check, feeder output | actual scan sample and matching adapter input; no downstream health decisions |
| Emmanuel: scenarios/ground truth; scenario controls and evidence/v2 | C2/C4/C6 | recovery/dropout sequences → labelled intended source timeline; check | targeted inject/restore and independent ground truth, unaffected other actors |
| Each: skill customization/evaluation; skills/ + owner evidence | C7 + final task cards | preserve original, record comparable task + acceptance + diff | original/customized runs, human review/course references; no evaluation claimed here |
| Each: owned verification/review/handoff; owner tests/evidence | C7 | fixture input → literal expected output; check + HTTP | component tests, actual runtime traces, PR review/contribution record |

Avoid overlapping production edits: Emmanuel owns the CARLA source/extractor/scenarios;
Ankit owns adapter publication and backend/frontend; Bayan owns health and Ditto
individual ingress. Agree exact new module paths before touching shared entry points.
Shared fixtures/contracts require all affected reviewers. No second fleet writer.
V2 ownership here supersedes conflicting E4/old scope wording; V1 history preserved.

## Optional transport checks

No MQTT transport is needed for offline checks. Existing V1 Mosquitto compose and
CLI approach is reused; do not change its broker or publish V2 into a production
broker. Only if Docker plus **already available** image/CLI clients exist, create an
isolated broker using the V1 configuration, distinct project name and host port:

```bash
docker run --rm --name sdv-v2-prep-mqtt -p 127.0.0.1:18884:1883 -v "$PWD/scripts/v1_dev/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" eclipse-mosquitto:2
python -m scripts.v2_dev.replay --ack-development-only --capture 7
python -m scripts.v2_dev.replay --ack-development-only --mqtt-publish --sequence recovery
```

Run capture and publication in separate terminals after broker is ready. Do not
pull/install/build solely for this check. Stop only `docker stop sdv-v2-prep-mqtt`
(or Ctrl+C in its terminal); no global compose down/prune/kill commands. CLI capture
is bounded to 10 seconds. Native MQTT retain/QoS and broker ACL behavior require a
real broker check, not HTTP. Optional real KUKSA check requires already running
isolated brokers and owner's adapter; not implemented or executed in this PR.

Linux/macOS: use python3 if python is absent. Windows: `py -3` may replace python;
use WSL for POSIX/docker volume examples and existing shell scripts. Pure Python
commands need no shell-specific features. CARLA GPU/OS support, Kanto Linux daemon,
Mosquitto binaries, Docker Desktop mounts and real protocol SDK toolchains are
separate host dependencies; this preparation does not install or claim them tested.
Use an unused configured port; do not stop unrelated services to free a port.

Preserve repository original skills/source/license before customization. Record
original and customized run version/hash, comparable starting code/task/acceptance,
course rationale, model/tool settings, interventions, output, review and defects
caught as development happens. Do not reconstruct historical runs. This PR does
not perform the V2 skill evaluation.

Shared changes update contract, literal expected fixtures, substitute checks and
evidence together; review before dependent merges. Mock-tested implementation
remains pending live acceptance, including all native diagnostic/Kanto/three-vehicle
integration, measurement and release requirements.
