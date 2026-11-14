# A3 — vehicle-specific scenario routing

Reviewed/executed November 12, 2026. Shared main baseline: `9ef82a9404b2c8a260c74ed1e845203d4d9d06c8` (merged A2). Implementation checkpoints: `e17482f` (red tests), `ff90f66` (routing), `81d8efd` (correlated failures), `9470420` (fixed-length HTTP bodies). This documentation checkpoint records those revisions; no teammate's unmerged branch was used.

## Requirements and boundaries

Spec: `docs/v1-interface-contracts.md` **1.0.0, proposed for affected-owner review**, C2/C8/C9/C10; current scope and task distribution assign A3 to Ankit. Implemented the owner-requested development baseline without changing the shared fixtures or claiming contract approval. Emmanuel and Bayan still review affected boundaries before merge.

| Acceptance | Evidence here | Remaining |
|---|---|---|
| V1-03 | Actual Spring dispatch selects vehicle-002, inject/clear works with prepared providers, vehicle-001 stays isolated; A2 reads corresponding synthetic mock state | Real provider→KUKSA/app→MQTT→Ditto→API/UI healthy/fault/healthy run |
| V1-04 regression | Existing A2 suite passes; packaged backend reads prepared mock fault/recovery | Live Ditto acceptance remains pending |
| V1-05 | Backend, contract and Python regression results below, dependencies identified | Full live two-vehicle CI is separate work |
| V1-06 | Actual skill use recorded below, red/green cycles and requirement-based tests | Human affected-owner review |
| V1-07 | Reproduction/configuration in backend setup document | Tagged release/demo remains separate |

Scope excludes fleet aggregation/writes, dashboard/CI expansion, scenario execution completion and V2. `ACCEPTED`/`DISPATCHED` prove acknowledged dispatch only. Failed actions remain lookup-able in process memory; timeouts are FAILED/UNKNOWN and never retried automatically.

## Skills actually used

Read and applied repository `skills/test-driven-development.md`: established failing routing/failure tests before implementation, then red/green for whole-body timeouts and fixed-length Python-compatible requests. Read/applied `skills/systematic-debugging.md` to investigate test harness, body timeout and HTTP framing failures. Read/applied `skills/verification-before-completion.md` before final verification/commit. Its evidence-before-claims rule was applied to the results below. The TDD skill's referenced `skills/writing-good-tests.md` is absent; use of that supporting file is not claimed. No AGENTS.md was found.

## Environment and exact test commands

Java: Amazon Corretto 21.0.13, Maven wrapper Maven 3.9.16, Spring Boot 4.1.0. Maven uses the already prepared isolated cache. Python contract command used system Python 3.14; full Python regression used the existing isolated Python 3.12.16/pytest 9.1.1 environment and generated protobuf path. Socket-based commands required sandbox approval to bind local test servers.

```sh
JAVA_HOME=/tmp/v1-twin-api-tooling/amazon-corretto-21.0.13.0.11-linux-x64 \
MAVEN_USER_HOME=/tmp/v1-twin-api-tooling/m2 \
bash backend/mvnw -f backend/pom.xml \
  -Dmaven.repo.local=/tmp/v1-twin-api-tooling/m2/repository \
  --batch-mode --no-transfer-progress clean verify

PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_v1_*.py' -q

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/v1-twin-api-tooling/protobuf \
/tmp/bayan-review-ndC62A/venv/bin/python -B -m pytest -q -ra -p no:cacheprovider

git diff --check
```

| Execution | Observed result |
|---|---|
| Before edits: backend clean verify | Exit 0; 124 tests, zero failures/errors/skips |
| Before edits and final: V1 contract unittest discovery | Exit 0; 31 tests passed on each run; Python resource warnings, no failing tests |
| Initial routing red run | Exit 1; 41 tests, 9 failures, 28 errors. Included absent behavior and test harness assumptions; not all errors were product defects |
| Intermediate focused verification | Test fixture path and Mockito default-method assumptions corrected; one remaining stalled-body test exposed 503 instead of expected 504 |
| After whole-exchange deadline fix | Exit 0; 57 focused tests passed |
| First full suite after implementation | Exit 1; 182 tests, one A2 configuration failure caused by duplicate test Clock beans; isolated the new test Clock with TestBean, no A2 production changes |
| Full suite after test Clock isolation | Exit 0; 182 tests, zero failures/errors/skips |
| Python regression | Exit 0; 158 passed, 9 deselected, 218 subtests passed; no failed tests |
| Packaged Spring/mocks first smoke | Failed: prepared Python handler rejected a streamed request without Content-Length; no success claimed |
| Framing regression before fix | Exit 1; one test failed, expected Content-Length 184, observed absent header |
| Final backend clean verify after framing fix | Exit 0; **183 tests, zero failures/errors/skips**, packaged jar built |
| Final packaged Spring/mocks smoke | Exit 0; **13 checks passed**, described below |
| Final whitespace check | Exit 0; no whitespace errors |

Focused red command for framing used the same Maven/JDK settings with `'-Dtest=ScenarioRoutingTest#requestBodyHasFixedByteLengthForPythonProviderCompatibility' test` in place of `clean verify`.

Routing coverage includes both configured providers, inject/clear, cooling compatibility, malformed/missing/numeric/padded fields, unsupported action/scenario/vehicle, no dispatch on validation failure, generated unique IDs, exact six-field acknowledgement matching (including boolean active), malformed/duplicate/trailing/oversized responses, provider 4xx/5xx, reset/refused sockets, header/body timeout, stored success/failure lookups, whole-exchange deadlines and fixed-length request framing. Existing A2 and legacy diagnostic tests remain in clean verify. No public request can select an arbitrary provider URL.

## Actual Spring Boot to prepared mocks smoke

The packaged jar from final clean verify was launched, not the preview service. An isolated Python orchestration harness (`python3 -B /tmp/v1-scenario-routing/smoke.py`, exit 0) launched the following exact processes from repository root and cleaned up only its own processes:

```sh
python3 -B -m scripts.v1_dev.http_mocks --ack-development-only --live-clock \
  --ditto-port 32180 --provider-001-port 32191 --provider-002-port 32192 --backend-port 32182

/tmp/v1-twin-api-tooling/amazon-corretto-21.0.13.0.11-linux-x64/bin/java \
  -jar backend/target/backend-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=v1-mock --server.address=127.0.0.1 --server.port=30183 \
  --sdv.v1.ditto.base-url=http://127.0.0.1:32180 \
  '--sdv.simulator.providers[vehicle-001]=http://127.0.0.1:32191' \
  '--sdv.simulator.providers[vehicle-002]=http://127.0.0.1:32192'
```

The harness exercised port **30183 only as the backend**, never preview port 32182. Its 13 assertions were:

1. Vehicle-002 injection reaches only provider-002; provider-001 context unchanged.
2. A2 health reads CRITICAL from the synthetic mock Thing.
3. Clear returns provider-002 to inactive and A2 mock health to HEALTHY.
4. Vehicle-001 injection reaches its own provider.
5. Vehicle-001 clear reaches its own provider.
6. Padded/unknown targets produce 400/404 without changing provider contexts.
7. Provider rejection produces correlated 502/PROVIDER_REJECTED and stored REJECTED/REJECTED.
8. Vehicle-001 continues after vehicle-002 rejection.
9. Provider timeout returns within four seconds as 504/PROVIDER_TIMEOUT with stored FAILED/UNKNOWN.
10. Vehicle-001 continues after vehicle-002 timeout.
11. Provider disconnect produces 503/PROVIDER_UNAVAILABLE with stored FAILED/FAILED.
12. Vehicle-001 continues after vehicle-002 disconnect.
13. Stopping the owned mock process produces real connection-refused 503 with retained failure and no development fallback.

Every submitted success/failure was checked with public GET lookup and matching actionId/traceId. Runtime results/logs are local scratch files `/tmp/v1-scenario-routing/{result.json,spring.log,mocks.log,final-verify.log}`; not permanent release artifacts. Portable launch and curl verification instructions are in [backend setup](../../backend/docs/v1-scenario-routing.md). For failure replay against the ports above:

```sh
curl http://127.0.0.1:32192/_mock/failures/vehicle-002 \
  -H 'Content-Type: application/json' -d '{"mode":"reject"}'
# Replace reject with timeout or disconnect for the other one-shot failure modes.
curl -i http://127.0.0.1:30183/api/v1/diagnostics/actions \
  -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}'
# GET /api/v1/diagnostics/actions/{returned actionId} to verify retained outcome.
```

## Handoff and remaining real integration

Emmanuel: configure independently reachable provider endpoints; require matching vehicle identity; return vehicleId/action/scenario/actionId/traceId plus expected active boolean. Verify both cooling and LiDAR against actual provider deployments. Acknowledgement is not execution completion; timeout cannot establish whether the provider applied the request.

Bayan/Emmanuel/Ankit: record a real targeted fault and clear through provider→app→MQTT→individual Ditto twin→A2, preserving source time/event identity and vehicle isolation. No live simulator, KUKSA, MQTT or Ditto was used in these checks. Mock-induced Thing recovery cannot satisfy that integration requirement. No retries, fleet work or Phase V2 lifecycle was added.
