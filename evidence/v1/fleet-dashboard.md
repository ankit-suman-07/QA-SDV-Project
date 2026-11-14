# A5 — fleet aggregation, materialization and dashboard

Executed November 12, 2026. Started from clean main `2803429` (A3 PR #35), updated with `git pull --ff-only origin main` (already current), on `ankit/feature/v1-fleet-dashboard`. Main contained A2/A3 but no Java fleet API, fleet writer or V1 fleet dashboard. No teammate's unmerged branch was used.

## Scope, contract and implementation

Contract: `docs/v1-interface-contracts.md` **1.0.0**, C5–C7/C9–C10, still proposed for affected-owner review. Current task distribution assigns Ankit the only fleet aggregator/writer. No shared wire contract, fixture, classification or freshness threshold was changed. C7's query-time individual-twin derivation governs the API; a materialized fleet Thing is never used as a freshness cache.

| Acceptance | Component evidence | Remaining live evidence |
|---|---|---|
| V1-08 / A5 | Exact fleet fixture, counts/order/shared clock, authenticated materialization, real Java + browser fault/recovery | Compare actual individual twins, API, persisted fleet Thing and dashboard during the integrated run |
| V1-03 support | A3 inject/clear through Java and observed mock fault/recovery; vehicle-001 isolated | Provider→app→MQTT→Ditto→dashboard cycle |
| V1-04 regression | All A2 tests retained; stale/missing/future/boundary fleet checks | Live Ditto/disconnected-source acceptance |
| V1-05 / V1-07 support | Repeatable component/runtime commands and results below | A4 full-stack CI, release/tag/demo |
| V1-06 | Skill use and red/green evidence below | Human affected-owner review |

Checkpoints: `9c6478f` tests; `10ddf33` fleet API; `d106650` writer/provisioning; `96bdadc` dashboard; `96030f3` scheduler isolation. Integration checkpoint `058aca5` adds portable Java/browser smoke runners and explicitly provisions an empty summary feature before writes. The documentation checkpoint records these results. Fleet counting includes each canonical V1 identity exactly once, independent of the legacy three-vehicle registry.

## Actual skills

Read/applied [test-driven-development](../../skills/test-driven-development.md) for failing fleet endpoint, materializer, provisioning and dashboard behavior tests before implementation. Initial fleet run: 13 assertion failures, all expected 200 versus absent endpoint 404. Initial writer run: 8 unsuccessful tests (7 missing-bean errors plus the concurrent test's failed entry wait); no writer existed. Provisioning tests failed while the script was absent, then passed; a later red test required the summary feature explicitly. Frontend missing-module/stub runs failed before model behavior; a subsequent stub regression run confirmed all five behavioral tests fail, then pass with the implementation restored. Removing error correlation fields reproduces the API test failure; restoring them passes.

Read/applied [systematic-debugging](../../skills/systematic-debugging.md) for harness response ordering, Python dependency collection and scheduler interference. A new heartbeat test **failed** because synchronous fleet I/O blocked the shared scheduler; after offloading the guarded update to its owned executor, all 9 focused scheduler/materializer tests passed. Browser delayed-route failure was a harness release/unroute race, corrected before successful runs.

Read/applied [verification-before-completion](../../skills/verification-before-completion.md): fresh commands/results below were inspected before completion claims. Skill sources are the repository copies at baseline `2803429`, not a claimed upstream pin. `skills/writing-good-tests.md` is absent; debugging supporting files named by its skill are also absent. No AGENTS.md was found. Human review is pending; no upstream provenance or supporting-file usage is claimed.

## Executed tests and limitations

Java: isolated Amazon Corretto **21.0.13**; Maven wrapper **3.9.16**; Spring Boot **4.1.0**. Java 25 was the system default and was not used for backend verification. Node **22.16.0**; Chrome via isolated `playwright-core` **1.56.1**. System/isolated Python **3.14** (not the CI Python 3.12 environment).

Commands from repository root:

```bash
JAVA_HOME=/tmp/a5-tooling/amazon-corretto-21.0.13.0.11-linux-x64 \
MAVEN_USER_HOME=/tmp/a5-tooling/m2 \
bash backend/mvnw -f backend/pom.xml -Dmaven.repo.local=/tmp/a5-tooling/m2/repository \
  --batch-mode --no-transfer-progress clean verify

python3 -B -m unittest discover -s tests -p 'test_v1_*.py' -q
python3 -B -m unittest discover -s tests -p test_fleet_provisioning.py -v
PATH=/tmp/a5-tooling/node-v22.16.0-linux-x64/bin:$PATH \
  /tmp/a5-tooling/node-v22.16.0-linux-x64/bin/npm --prefix frontend test

git diff --check
```

| Check | Observed result |
|---|---|
| Before edits: backend clean verify | **183 passed**, zero failures/errors/skips; packaged jar built |
| Before edits/final: contract/mock unittest suite | **31 passed** with sockets enabled; Python resource warnings, no failed tests. Initial sandbox-only run skipped six transport tests; approved runs skipped none |
| Fleet+A2 checkpoint | **67 passed** including shared-clock/concurrent-read unit test and A2 controller regressions |
| Writer configuration/materialization checkpoint | **10 passed**, including live-auth rejection, separate service credentials, HTTP failures and bounded/concurrent writes |
| Final backend clean verify after scheduler fix | **208 passed**, zero failures/errors/skips; packaged jar built |
| Frontend final npm test | **7 passed**, zero failures/skips |
| Provisioning final unittest | **2 passed** |
| Packaged Java + mocks/capture final smoke | **12 checks passed** |
| Chrome + actual Java final smoke | **9 checks passed**, no page errors; 375px layout checked |
| Whitespace check | Exit 0 |
| Full Python regression | **Blocked at collection**, not passed: `vehicle-simulator/tests/test_kuksa_publication.py` imports missing `kuksa_client` |
| Available Python regression with blocked module explicitly ignored | **160 passed, 221 subtests passed** |

Initial `python3 -m pytest -q` could not start because pytest was absent. An isolated venv installed pytest 9.2.0, requests 2.34.2 and grpcio-tools 1.85.1; generated protobuf modules were kept in `/tmp`. Full pytest then exposed the missing KUKSA import. Installing `kuksa_client==0.5.1` failed because its pinned `grpcio-tools==1.68.0` requires a source build on Python 3.14 and `c++` is absent. No dependency versions or CI configuration were changed to bypass this. Exact available-suite command:

```bash
mkdir -p /tmp/a5-tooling/protobuf
/tmp/a5-tooling/venv/bin/python -m grpc_tools.protoc -I uprotocol/proto \
  --python_out=/tmp/a5-tooling/protobuf uprotocol/proto/common.proto \
  uprotocol/proto/health_status.proto uprotocol/proto/vehicle_status.proto \
  uprotocol/proto/vehicle_fault.proto uprotocol/proto/vehicle_diagnostic.proto
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/a5-tooling/protobuf \
  /tmp/a5-tooling/venv/bin/python -B -m pytest -q -ra -p no:cacheprovider \
  --ignore=vehicle-simulator/tests/test_kuksa_publication.py
```

Backend coverage includes canonical healthy projection, warning/fault/recovery, stale/missing/unavailable and future source times, exact −1s/5s/30s boundaries, both count invariants, deterministic identity order, one captured evaluation time, independent parallel reads, stalled body isolation, exact API-versus-writer equality at a fixed time, 200/201/204 write success, 401/403/500/503 failures, no immediate retry, timeout, non-overlap and scheduled recovery without blocking legacy work. A2/A3/legacy tests remain in clean verify.

## Exact runtime reproduction

[Setup guide](../../backend/docs/v1-fleet-dashboard.md) contains all properties, provisioning commands, service-account requirements and ordinary Java/frontend startup commands. The prepared preview does not persist fleet state; the runtime harness adds a separate **controlled HTTP capture** for fleet writes/provisioning and delegates individual reads to the unchanged prepared mock.

Final commands:

```bash
python3 -B -m scripts.v1_dev.fleet_smoke \
  --java /tmp/a5-tooling/amazon-corretto-21.0.13.0.11-linux-x64/bin/java \
  --artifacts-dir /tmp/a5-fleet-smoke-final --hold

PLAYWRIGHT_MODULE=/tmp/a5-tooling/browser/node_modules/playwright-core/index.mjs \
  /tmp/a5-tooling/node-v22.16.0-linux-x64/bin/node \
  frontend/tests/fleet-browser.mjs /tmp/a5-fleet-smoke-final/stack.json
```

Final allocated ports: Java **38837**, individual Ditto mock **46397**, provider-001 **52729**, provider-002 **45921**, fleet capture **58977**, frontend **3000**. Mock preview **32987** was not used as backend evidence. The committed harness records new allocated ports in `stack.json` on each run. It launches the packaged jar with `v1-mock`, the capture as `sdv.v1.ditto.base-url`, both provider mappings, `sdv.v1.fleet.enabled=true`, a 200ms interval/100ms initial delay/500ms write deadline, and isolated test-only service credentials. Provisioning calls the actual provisioning module with a distinct test-only administrator; no live resource is provisioned.

The backend smoke checks API invariants, selected fault/clear and action lookup, stale/missing/unavailable isolation, captured materialization, failure-preserved reads and recovery on the next schedule. Runtime generatedAt differs between sequential reads/writes; the smoke compares all other fields, while fixed-clock HTTP tests compare the entire projection exactly. The browser checks actual Java data and A3 actions, selection races using a delayed real response, and request-error rendering using explicitly intercepted browser errors.

Permanent samples: [API/writer result](fleet-dashboard/mock-api-writer-result.json), [browser result](fleet-dashboard/browser-result.json), [mock-backed fault screenshot](fleet-dashboard/mock-fault.png). Scratch logs are `/tmp/a5-tooling/{baseline,final-verify,scheduler-red,scheduler-green,pytest,pytest-available-final}.log` and `/tmp/a5-fleet-smoke-final/{spring,mocks}.log`. These logs are not release artifacts. The screenshot shows actual Java with synthetic HTTP dependencies, not live Ditto/MQTT acceptance.

## Handoff and pending integration

Bayan supplies the two independently validated V1 individual twins; no second aggregator/writer is needed. Ankit provisions the fleet policy/Thing and enables exactly one backend writer. Emmanuel supplies real providers enforcing identity and returning A3 acknowledgements. Both affected owners review these boundaries.

Pending A4: real authentication subject mapping and least-privilege fleet writes in Ditto; compare both real individual twins, fleet Thing, API and dashboard during healthy→fault→healthy with vehicle-001 isolated; verify write outage/recovery and source aging on the real deployment; rerun the complete Python regression under the supported dependency environment. No live MQTT, KUKSA, provider or Eclipse Ditto was used here. No fleet acceptance, full-stack CI, release, CARLA, Kanto or Phase V2 execution completion is claimed.
