# Independent V1 development

## Remaining Phase V1 ownership — November 14, 2026

Ankit owns all remaining Phase V1 remediation, integration, verification, fleet CI,
Kanto validation (B5 / V1-09), report/video and release work. Bayan and Emmanuel's
component contributions and original task IDs remain historical attribution, not
assignments of remaining work. Phase V2 ownership is unchanged. The sole fleet
aggregator and fleet-twin materializer are in Spring Boot under Ankit (A5).
V1-09 remains required and separately tracked; a blocked Linux/LAN pilot does not
constitute acceptance. Release still requires all applicable criteria and reviews.
This ownership update does not approve proposed interfaces, freshness defaults,
measurement budgets, authentication subjects or other unresolved decisions.


Use [contract 1.0.0](v1-interface-contracts.md) and the [task distribution](10-detailed-task-distribution.md). The contracts are proposed for affected-owner review; this package does not implement the V1 platform. The November 16, 2026 V1 deadline and December 5, 2026 V2 deadline remain unchanged.

## Start from one shared baseline

After the preparation PR is approved and merged, every developer updates main and starts from the same recorded SHA. Do not depend on another developer's unmerged branch. Use [fixtures](../tests/fixtures/v1/README.md) for the other components and develop your own real implementation behind explicit configuration.

This preparation branch is `docs/v1-independent-development`. No push or merge was performed by this task. Future branch/PR commands below are instructions for developers, not actions already taken.

## Dependencies and command verification labels

Run commands from the repository root unless stated otherwise. Python standard library is sufficient for contract tests, offline replay and HTTP mocks. Existing CI uses Python 3.12 and Java 21; match those for application builds. Do not install the Velocitas SDK into the shared unit-test environment: its existing Dockerfile owns that environment.

- **Verified here:** standard-library contract/offline commands, in-memory HTTP request-handler tests, CLI help and Compose configuration parsing. Actual verification results are in [the validation record](findings/2026-11-11-v1-preparation-validation.md).
- **Unverified here:** starting/listening HTTP servers (socket creation denied), running Mosquitto clients/broker (clients absent, Docker access denied), Maven/Java 21 backend, Velocitas images/KUKSA integration and Linux Kanto. Their commands are provided for normal developer machines and must be recorded as unverified until executed there.
- Existing full pytest could not run because pytest and several application dependencies are absent. Passing these mocks is not live MQTT/HTTP/Eclipse acceptance.

### Dependency-free commands — verified

```bash
python3 -B -m unittest discover -s tests -p 'test_v1_*.py' -v
python3 -B -m scripts.v1_dev.mqtt render --scenario cycle --anchor 2026-01-01T00:00:00Z
python3 -B -m scripts.v1_dev.mqtt render --scenario cycle --anchor 2026-01-01T00:00:00Z | python3 -B -m scripts.v1_dev.mqtt check --expect-cycle
python3 -B -m scripts.v1_dev.http_mocks --help
python3 -B -m scripts.v1_dev.mqtt --help
```

The unittest runner skips loopback transport tests only when socket creation is forbidden. In-memory tests still exercise the actual handlers, routes and state changes; transport remains unverified. A normal machine should run those transport tests without skips. No dependency download is needed for this suite.

### Optional local MQTT broker — runtime unverified here

Install Mosquitto 2 CLI clients (`mosquitto_pub`, `mosquitto_sub`) through your OS package manager and ensure Docker/Compose is usable if using the isolated broker below. No Python MQTT dependency is needed. Validate first:

```bash
docker compose -p sdv-v1-dev -f scripts/v1_dev/compose.yaml config --quiet
# Local test broker only; default host port 18883 avoids the existing MVP's 1883.
docker compose -p sdv-v1-dev -f scripts/v1_dev/compose.yaml up -d
```

Set `V1_MQTT_PORT` before Compose if 18883 is occupied, then pass that same port to both tools and your component. The development broker allows anonymous access and binds the host port to loopback. Do not deploy it as a production configuration. On a shared machine use a mutually agreed endpoint/auth configuration instead. Optional teardown removes only this development project:

```bash
docker compose -p sdv-v1-dev -f scripts/v1_dev/compose.yaml down
```

## Ankit — backend, routing, fleet and dashboard

Tasks A1–A5 can start without Ditto, Emmanuel's providers or Bayan's consumer. Required for implementation: Java 21/Maven wrapper dependencies for Spring Boot, Python for substitutes, and a browser/static server for UI. No MQTT broker is required for Ankit's component work.

### Start substitute dependencies — runtime unverified here

```bash
python3 -B -m scripts.v1_dev.http_mocks --ack-development-only
```

This starts four development-only services sharing isolated in-memory state:

| Service | Default URL |
|---|---|
| Ditto read/feature-write mock | http://127.0.0.1:19080 |
| Provider 001 | http://127.0.0.1:19091 |
| Provider 002 | http://127.0.0.1:19092 |
| Backend/UI preview | http://127.0.0.1:19082 |

Override ports with `--ditto-port`, `--provider-001-port`, `--provider-002-port`, `--backend-port`; override bind address with `--host`. All responses have `X-SDV-Mock: true`; `/health` identifies the service as mock. Data is memory-only and resets on restart. Ctrl-C stops these mock services; no real simulator/twin is changed.

Default clock is fixed at `2026-01-01T00:00:04Z`. In backend tests inject that same `Clock.fixed(...)`. For browser/current-clock smoke checks start with `--live-clock` instead; initial samples are rebased to startup−4 seconds and then naturally age. Refresh a selected state through the controls below. The mock does not pretend a silent source keeps publishing.

### Read, control and fail dependencies — runtime unverified here

```bash
curl -fsS http://127.0.0.1:19080/api/2/things/sdv:vehicle-001
curl -fsS http://127.0.0.1:19080/api/2/things/sdv:vehicle-002
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"fault"}'
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"stale"}'
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"missing"}'
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"unavailable"}'
curl -fsS -X POST http://127.0.0.1:19080/_mock/states/vehicle-002 -H 'Content-Type: application/json' -d '{"state":"recovered"}'
# Fixed-clock mode only; one clock serves all four mocks.
curl -fsS -X POST http://127.0.0.1:19080/_mock/clock -H 'Content-Type: application/json' -d '{"now":"2026-01-01T00:00:10Z"}'
# Fail only provider-002. Modes: success, reject, timeout, disconnect.
curl -fsS -X POST http://127.0.0.1:19092/_mock/failures/vehicle-002 -H 'Content-Type: application/json' -d '{"mode":"reject"}'
```

`missing` returns Ditto 404; `unavailable` returns 503. `timeout` waits five seconds without applying the scenario, so configure the Java client timeout below that (proposed two seconds). `disconnect` drops the socket. For a refused connection, map vehicle-002 to a deliberately unused local port in your **test** configuration; do not repoint a live deployment. Reset failures with mode `success`. Tests cover endpoint selection, wrong identity, reject, timeout and connection failure; none proves that a real provider never executed a timed-out request.

### Run your implementation and UI

The endpoint [example](../scripts/v1_dev/endpoints.example.json) is a template, not an existing Spring configuration loader. In A2/A3 bind equivalent values in your explicit development profile: Ditto 19080, provider-001 19091, provider-002 19092, two allowlisted vehicle IDs, injected clock, timeout/freshness settings. Implement the live Ditto adapter, new LiDAR scenario support and v1 APIs on your branch. Do not describe these as already present.

Existing backend build/test command, **unverified here**:

```bash
(cd backend && bash ./mvnw --batch-mode --no-transfer-progress clean verify)
```

Existing application launch command, **unverified here**:

```bash
(cd backend && bash ./mvnw spring-boot:run)
```

The latter currently starts development-generated telemetry. It becomes a mock-Ditto-backed implementation only after your A2 profile/configuration exists. Do not assume setting a nonexistent environment variable activates an adapter. Document your exact new profile launch in your PR.

For UI scaffolding before your backend is ready, explicitly set the API base URL on **your feature branch's development config** to `http://localhost:19082` and use the proposed v1 URLs. The preview also serves legacy state/health projections, but no historical cooling telemetry is invented. It supports the action POST/GET and fleet response. Start a static server (**unverified here**):

```bash
python3 -m http.server 3000 --directory frontend
```

Preview action example (**unverified runtime**):

```bash
curl -fsS http://127.0.0.1:19082/api/v1/fleet
curl -fsS -X POST http://127.0.0.1:19082/api/v1/diagnostics/actions -H 'Content-Type: application/json' --data-binary @tests/fixtures/v1/scenario-inject-request.json
curl -fsS -X POST http://127.0.0.1:19082/api/v1/diagnostics/actions -H 'Content-Type: application/json' --data-binary @tests/fixtures/v1/scenario-clear-request.json
```

These preview actions immediately change mock observations and return deterministic accepted IDs; they do not execute Java, MQTT or a vehicle. The Java routing tests should call the two provider mocks (public scenario fixture plus generated actionId/traceId), not this preview. Keep preview URLs and mock credentials/configuration out of live defaults. The preview does not emulate fleet-twin persistence; test that writer with your own mocked Ditto HTTP responses.

Independent tests: new backend adapter/service/controller tests with MockRestServiceServer and fixed clock, fleet count invariants, outages/wrong identities, dispatch failure tests, and the standard-library contract suite. UI tests can use the preview without waiting for either teammate. Capture payloads/screenshots as **mock** evidence.

## Bayan — ingress, two individual twins and Kanto

Tasks B1/B2/B3 need Python, Mosquitto CLI clients and a broker; real Ditto can be your own isolated deployment. No simulator, Velocitas, Spring Boot or frontend is needed. A mock writer or the HTTP feature PUT/GET service can validate transformations before your Ditto is installed. The mock is deliberately not a complete Ditto deployment.

### Replay inputs — MQTT runtime unverified here

Start your consumer against the configured broker, allowlist both IDs and direct its writer to your own twins/mock writer. Then publish:

```bash
python3 -B -m scripts.v1_dev.mqtt publish --scenario cycle --host 127.0.0.1 --port 18883 --run-id bayan-cycle-1
python3 -B -m scripts.v1_dev.mqtt publish --scenario malformed --host 127.0.0.1 --port 18883
python3 -B -m scripts.v1_dev.mqtt publish --scenario unknown --host 127.0.0.1 --port 18883
python3 -B -m scripts.v1_dev.mqtt publish --scenario out-of-order --host 127.0.0.1 --port 18883 --run-id bayan-order-1
```

For deterministic test clocks use `--anchor 2026-01-01T00:00:00Z`. In normal replay the anchor is current time−4 seconds; source offsets survive. Each replay against existing watermarks should use a fresh run ID and later anchor. `out-of-order` sends a newer fault followed by an older healthy sample so the second must not overwrite the first. Negative scenarios intentionally bypass publisher validation to test **your consumer**. It must log/reject and continue; compare before/after twin state for both IDs. Unknown input publishes `sdv/vehicle-999/health`, so subscribe with `sdv/+/health` then validate allowlists.

`render` produces broker-free topic/JSON lines for unit tests. `check` rejects malformed/unknown/late input locally; a rejected local check does not establish your consumer rejects it. QoS 1 duplicates and a restart from the twin watermark need explicit consumer tests. Review auth/policy/revision/retry behavior against your own real Ditto separately.

Independent verification: unit tests for validation/transformation and writer failures; replay positives/negatives into your own consumer; twin reads and source/event IDs; B3 legacy verifier regressions with fixed clock. Do not implement a second aggregator. Supply Ankit the individual-twin fixtures and exact read contract; Ankit owns counting and fleet-twin writes.

### Kanto pilot without waiting for a teammate

B5 descriptor/configuration work, static tests and capture-oracle rehearsal can proceed independently. For actual runtime, use your own Linux/Kanto device and your own KUKSA/MQTT endpoints or deterministic signal feeder. No teammate's unmerged branch is required to prepare or component-test this configuration. A replayed event alone is not Kanto evidence.

The current descriptor/deploy script still targets vehicle-001/loopback; parameterizing it for app-002, the correct host ports/LAN endpoints and the new v1 event publisher is B5/E1 implementation work. Existing command, **unverified here and suitable only after reviewing/configuring your own target**:

```bash
sh velocitas-app/kanto/deploy.sh
```

It builds/pushes an image and replaces its named Kanto container, so run only on your intended development target. Record runtime versions, launch/restart logs and fresh source/event IDs. Final V1-09 requires that a fresh app-002 event after restart reaches the correct live twin. If Linux/LAN blocks this, record it separately as pending; do not substitute descriptor tests for runtime acceptance.

## Emmanuel — two edge pipelines and deterministic LiDAR cycle

Tasks E1/E2 need Docker/Compose with KUKSA and the Velocitas app dependencies from existing Dockerfiles, plus Mosquitto CLI clients for capture. No Ditto, backend or frontend is needed. Build your two-edge configuration on your branch; the existing production Compose still deploys only one edge and old topic format.

Run your own implementation of the two-edge Compose deployment with configured MQTT endpoint matching capture. Existing single-edge Compose syntax can be checked now; the two-edge service names/mappings in C2 are targets, not services already delivered here. Do not copy a fake startup command referencing nonexistent services.

Start capture **before** starting observations/actions (**broker/runtime unverified here**):

```bash
python3 -B -m scripts.v1_dev.mqtt capture --host 127.0.0.1 --port 18883 --timeout 180 --expect-cycle
```

It subscribes to both exact vehicle topics, validates every received event and checks vehicle-001 remains healthy and vehicle-002 goes healthy→CRITICAL/LIDAR_OBSTRUCTION→healthy. A warning phase during approach/recovery is allowed. The tool observes until the timeout; errors/late/duplicate events return a nonzero exit, making defects visible. Use an isolated clean broker/test run to avoid unrelated retained messages. A successful cycle only verifies events captured during that observation window.

Before your real publisher exists, verify the observer offline with the verified render→check command above, or against Bayan's fixture publisher locally. Your E1 implementation must publish the new contract; the legacy `sdv/autonomy/status` topic does not satisfy this capture.

To exercise your own provider directly, use the current simulator route and supply action/trace IDs (**runtime unverified here; host ports are examples configured by your E1 work**):

```bash
curl -fsS -X POST http://127.0.0.1:8092/api/v1/scenarios/actions -H 'Content-Type: application/json' -d '{"vehicleId":"vehicle-002","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION","actionId":"edge-inject-1","traceId":"edge-trace-1"}'
curl -fsS http://127.0.0.1:8092/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION
curl -fsS -X POST http://127.0.0.1:8092/api/v1/scenarios/actions -H 'Content-Type: application/json' -d '{"vehicleId":"vehicle-002","action":"CLEAR_SCENARIO","scenario":"LIDAR_OBSTRUCTION","actionId":"edge-clear-1","traceId":"edge-trace-2"}'
```

This is individual component verification; the final acceptance scenario uses Spring Boot as control entry point. Use a fixed seed or deterministic trajectory, preserve observation time, and record injection ground truth separately from events. Test 10 m and 5 m boundaries, sensor failure, wrong vehicle rejection, source silence and unit conversion. Keep original single-vehicle tests/demo available. Capture both vehicle streams and clock/endpoint configuration. The reference classifier does not replace your Velocitas implementation.

## Evidence and PR strategy

For every PR record: task/acceptance IDs; contract version/revision; actual skill file/version/use; human review/corrections; test commands/exits; fixed clock or source-time/clock handling; exact Git SHA; dependencies labelled mock/live; observed limitations. Use [evidence index](../evidence/README.md) and add owner evidence under `evidence/v1/` in your implementation PR. Pin skill provenance before claiming rubric completion; the existing usage template alone is not evidence. Preparation verification is not completed V1-06 evidence for all members.

| Proposed branch / focused PR | Owner and file boundary | Review |
|---|---|---|
| ankit/feature/v1-live-twin-api | A2; backend Ditto adapter, registry/config, vehicle DTO/service/controllers/tests | Bayan consumes/provides twin contract; Emmanuel reviews units |
| ankit/feature/v1-scenario-routing | A3; backend simulator adapter/diagnostic service and tests | Emmanuel reviews provider boundary |
| ankit/feature/v1-fleet-dashboard | A5; Spring Boot aggregate/fleet writer/API, frontend and UI tests | Bayan reviews twin reads; Emmanuel reviews health semantics |
| ankit/test/v1-fleet-acceptance | A4; acceptance scripts/CI/submission evidence | Both component owners |
| bayan/feature/v1-mqtt-twins | B1/B2; new ingress/writer, individual provisioning and tests | Emmanuel reviews events; Ankit reviews reads |
| bayan/fix/v1-twin-verifier | B3; verifier/legacy context caller/mapper tests | Ankit and Emmanuel for affected boundaries |
| bayan/config/v1-kanto-pilot | B5; kanto descriptor/deploy config/static tests | Emmanuel reviews app configuration |
| emmanuel/feature/v1-two-vehicle-edge | E1; simulator Compose/VSS/provider plus Velocitas publisher/tests | Bayan reviews topics/schema; Ankit reviews provider mapping |
| emmanuel/feature/v1-lidar-scenarios | E2; deterministic generator/scenario/context/identity tests | Ankit reviews commands; Bayan reviews event examples |

One owner per implementation area; Ankit owns backend/frontend/CI, Bayan owns ingress/twins/verifier/Kanto, Emmanuel owns simulator/Compose/VSS/Velocitas. Coordinate E1 app-image changes with B5 descriptor work through the contract, not shared unmerged files. Tire-unit/context fixes cross boundaries: review both sides and preserve baseline compatibility. Each branch starts from the common merged baseline; same-owner dependent PRs can follow once their prerequisite merges.

Follow [contribution guidelines](00-github-contribution-guidelines.md). Shared contracts require review from every affected developer; ordinary PRs require at least one reviewer. No PR is merged or pushed by this preparation task. Suggested future workflow:

```bash
# Future developer actions after the contract PR merges, not executed here.
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git switch -c <owner>/<type>/<focused-task>
```

## Replace substitutes during team integration

1. Record the shared approved contract SHA. Owners finish independent mock tests and component reviews first.
2. Run Emmanuel's real two-edge stacks and Bayan's real ingress/twins; keep the same topic/schema/identity mappings. Remove replay publishers from that broker during the acceptance run.
3. Point Ankit's explicit live profile at shared Ditto and the two real providers. Remove mock preview URLs, generated telemetry adapters and mock credentials; fail visibly rather than substitute healthy data.
4. Drive the scenario through Spring Boot. Compare captured MQTT, individual twins, API, fleet twin and dashboard with one timeline. Assert vehicle-001 stays unaffected through fault and recovery, not just at the final snapshot.
5. Run the existing single-vehicle baseline plus new two-vehicle CI. Label each dependency and retain failure logs. Record exact SHA, versions, commands and outcomes.
6. Capture the separate Kanto post-restart event→twin check, actual skill-use/review evidence, release tag, report, video and contributions. Unavailable Linux or other blockers stay pending.

Mock-only implementation readiness is never described as satisfying live V1 acceptance. CARLA, full diagnostic execution outcomes, networked uProtocol/OpenSOVD and customized-skill comparisons remain V2.
