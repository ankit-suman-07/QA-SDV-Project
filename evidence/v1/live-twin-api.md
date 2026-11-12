# A2 — Individual Ditto twin API implementation evidence

Date: November 12, 2026. Owner: Ankit. Branch: `ankit/feature/v1-live-twin-api`.
Acceptance: **V1-04**; supports V1-02, V1-03, V1-05 and the later A5/V1-08 handoff.
This is component/backend-to-mock evidence, not completed live V1 acceptance.

## Specification and boundaries

Baseline: `388004933779bfb08e11d9707af7054b7a0e7b7b` on clean local/remote main,
including the shared preparation baseline `8b3143a`. Sources: `docs/SOURCE-OF-TRUTH.md`,
`docs/v1-interface-contracts.md` **1.0.0 (proposed for affected-owner review)**,
`docs/10-detailed-task-distribution.md` A2, current scope, architecture,
independent-development guide and GitHub contribution guidelines. No AGENTS.md
was found in the repository search. No affected shared contract or fixture changed.

The user authorized implementation against these prepared interfaces. Proposed
30-second unavailable default, measured propagation budgets and owner approval
remain review items; configurable thresholds keep the proposed baseline explicit.
No additional unresolved decision blocked this bounded implementation. Ankit owns
fleet aggregation separately. No code or commits from Bayan's unmerged PRs were used.

Implementation checkpoints:

- `0f38c63` — `test: cover vehicle twin reads and freshness rules`
- `3d1d8ad` — `feat: read vehicle state through configured ditto adapter`
- `a08a988` — `feat: expose v1 vehicle state and health endpoints`
- Follow-up documentation checkpoint contains this evidence and the setup guide.

[Setup/configuration and exact developer launch commands](../../backend/docs/v1-live-twin-api.md).
The new `sdv.v1.ditto.*` read configuration is separate from the existing legacy
`sdv.ditto.mode` writer. Existing legacy endpoints/provider/registry remain unchanged.
Only v1's two canonical identities are listed/accepted. No generated fallback is
reachable from the v1 controller/service/HTTP reader.

## Baseline and red-green execution

Tooling was installed under `/tmp/v1-twin-api-tooling`, without changing system
Java: Amazon Corretto **21.0.13**, Maven wrapper **3.9.16**, Spring Boot **4.1.0**,
Jackson **3.1.4** and Spring Web **7.0.8** (project-managed dependencies).
The system Java 25 was not used for verified backend results. Contract unittest
used Python **3.14.10**; the full Python regression used Python **3.12.16**,
pytest **9.1.1** and the pinned project dependency environment from the earlier
review. Generated Python Protobuf files were written under `/tmp`, not committed.

Backend commands ran from `backend/` unless `-f backend/pom.xml` is shown. Prefix:

```bash
export JAVA_HOME=/tmp/v1-twin-api-tooling/amazon-corretto-21.0.13.0.11-linux-x64
export MAVEN_USER_HOME=/tmp/v1-twin-api-tooling/m2
# Every Maven invocation below also used:
# -Dmaven.repo.local=/tmp/v1-twin-api-tooling/m2/repository
```

| Stage | Command, in addition to temporary Maven cache argument | Observed result |
| --- | --- | --- |
| Pre-change backend | `bash ./mvnw --batch-mode --no-transfer-progress clean verify` | **44 tests passed**, 0 failures/errors/skips; BUILD SUCCESS |
| Pre-change contracts | `python3 -B -m unittest discover -s tests -p 'test_v1_*.py' -q` from root, with `PYTHONDONTWRITEBYTECODE=1` | **31 tests passed**, no skips after allowing loopback sockets |
| Initial API red | `bash ./mvnw --batch-mode --no-transfer-progress -Dtest=V1VehicleControllerTest test` | 32 tests; **28 failures**, 0 errors, 4 existing unknown-route checks passed; missing routes returned 404 instead of 200 |
| Expanded validation/configuration red | `bash backend/mvnw -f backend/pom.xml --batch-mode --no-transfer-progress -Dtest=V1VehicleControllerTest,V1DittoConfigurationTest test` | 64 tests; **60 failures**, 0 errors; routes absent and invalid configuration still allowed startup |
| Invalid-calendar regression | Same focused Maven command with `-Dtest=V1VehicleControllerTest` | Invalid February date escaped as `DateTimeParseException`/ServletException; 53 tests, 1 error; corrected to unavailable/null projection |
| Configuration/API green | Focused two-class command above | **68 tests passed**, 0 failures/errors/skips after date and explicitly empty URL fixes |
| Required final backend check | `bash backend/mvnw -f backend/pom.xml --batch-mode --no-transfer-progress clean verify` | **124 tests passed**, 0 failures/errors/skips; BUILD SUCCESS; packaged jar |
| Full Python regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/v1-twin-api-tooling/protobuf /tmp/bayan-review-ndC62A/venv/bin/python -B -m pytest -q -ra -p no:cacheprovider` from root | **158 passed**, 9 integration tests deselected, 218 subtests passed; exit 0 |
| Diff validation | `git diff --check 3880049...HEAD` and working-tree `git diff --check` | Passed before documentation checkpoint |

The initial default Maven attempt stopped before tests because `/home/ankitsuman/.m2`
was read-only. Moving the Maven cache to `/tmp` and using Java 21 resolved setup.
The initial sandboxed contract run skipped six socket tests; the unsandboxed rerun
executed all 31 successfully. A sandboxed API run also failed socket creation;
those context errors are environment failures, not passing tests. Reruns with the
required loopback access produced the results above. No pre-existing code/test
failure was found in the supported-toolchain baseline.

One development regression initially expected a 600-level extension to be accepted.
A direct Jackson parser check established its default maximum depth is 500. The
safety test was corrected to require successful shallower extension reads, controlled
unavailable results beyond the parser bound, and valid surrogate-pair acceptance;
no fixture or production parser safety limit was relaxed to make it pass. The
completed 124-test run includes this behavior. Earlier full iteration: 124 tests,
1 failure in that expectation; final full run: 124 passed.

The full Python suite required generation of the five existing schemas into `/tmp`:

```bash
mkdir -p /tmp/v1-twin-api-tooling/protobuf
PYTHONDONTWRITEBYTECODE=1 /tmp/bayan-review-ndC62A/venv/bin/python -m grpc_tools.protoc \
  -I uprotocol/proto --python_out=/tmp/v1-twin-api-tooling/protobuf \
  uprotocol/proto/common.proto uprotocol/proto/health_status.proto \
  uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto \
  uprotocol/proto/vehicle_diagnostic.proto
```

## Requirement-to-test mapping

| Requirement | Executed coverage |
| --- | --- |
| C2/C6 individual Thing mapping, V1-02/V1-04 | Both actual fixture identities, three identity locations, cross-vehicle mismatch rejection, unknown/padded IDs do not issue HTTP requests, separate V1/legacy registry scope |
| C3/C4 schema and typed projection | Required field/type checks, version mismatch, faults/health consistency, numeric/boolean/null LiDAR, sensor failure AVAILABLE/CRITICAL, canonical fault/recovery fixtures |
| C5 source-time freshness, V1-04 | Fixed UTC clock `2026-01-01T00:00:04Z`; exactly 5/30 seconds and one nanosecond above; exactly one second future and one nanosecond beyond; custom thresholds; subnanosecond future excess; original offset/fraction text retained |
| Untrusted versus last-known fields | Missing/invalid/read failures return explicit null data fields; trusted old observations retain source/event/health with stale/unavailable availability |
| C6 HTTP response handling | Whole-Thing GET with Accept JSON, URL prefix, Basic header, unexpected 2xx/redirect/4xx/5xx, mock-server statuses and body failures, auth error observability without raw dependency/credential details |
| Bounded failure/isolation | MockRestServiceServer timeout, real loopback delayed response bounded at configured 100 ms (asserted <3 seconds), real refused connection, failure of 002 leaves 001 readable; no retries or generated fallback |
| Untrusted extensions | Duplicate keys, trailing JSON, nonfinite distance, lone surrogate rejection, allowed shallow/deep safety cases and valid Unicode pairs; 1-MiB response-size cap |
| Legacy compatibility | Existing controller/service/provider/registry tests all pass; running Spring Boot legacy state fields checked after its existing initial scheduler population |

Tests use real Java production components for projection/validation/freshness.
External HTTP substitutes are explicitly mocked: MockRestServiceServer, a JDK
loopback server, and the prepared Python HTTP mocks. The existing baseline tests
still exercise their original mocked dependencies; they are not promoted to live
KUKSA/Ditto acceptance by this task.

## Real Spring Boot → prepared Ditto mock smoke

Executed the packaged Spring Boot jar, not the Python preview API. Temporary,
owned subprocesses were started with these commands from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m scripts.v1_dev.http_mocks \
  --ack-development-only --live-clock \
  --ditto-port 29180 --provider-001-port 29191 --provider-002-port 29192 --backend-port 29182

/tmp/v1-twin-api-tooling/amazon-corretto-21.0.13.0.11-linux-x64/bin/java \
  -jar backend/target/backend-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=v1-mock --server.address=127.0.0.1 --server.port=28182 \
  --sdv.v1.ditto.base-url=http://127.0.0.1:29180
```

A temporary urllib script (`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/v1-twin-api-tooling/smoke.py`)
made requests only to Spring at **28182** and the Ditto mock/control at **29180**.
No request went to preview port 29182. It asserted Spring responses did not carry
`X-SDV-Mock`, while data originated from the prepared HTTP mock. It refreshed mock
observations after Spring readiness, compared source/event IDs with direct Thing
reads and exercised mock controls. **12 checks passed, exit 0**:

1. Exactly the two registered V1 IDs.
2. Vehicle-001 state/health projection, availability and preserved IDs/time.
3. Vehicle-002 equivalent projection.
4. Vehicle-002 CRITICAL fault while vehicle-001 remains unchanged.
5. Vehicle-002 recovery.
6. Six-second-old source remains visible as STALE.
7. Missing twin produces explicit null data fields.
8. Mock HTTP 503 produces explicit null data fields.
9. Unknown vehicle returns 404.
10. Legacy state retains temperature/coolant fields after scheduler population.
11. Stopping only the owned mock process produces connection-refused UNAVAILABLE,
    with no generated health fallback.
12. The registry endpoint still works during the Ditto outage.

All owned processes were terminated in a `finally` block, including on unsuccessful
attempts. The first smoke attempt asserted legacy fields before its unchanged
initial scheduler tick; a readiness wait corrected that harness assumption, with
no production change. A second attempt's port preflight encountered recently used
sockets. The successful run used fresh isolated ports shown above. No shared
services were provisioned or stopped. Logs/result artifacts remain under `/tmp`;
the setup guide provides the equivalent repeatable manual request sequence.

## Actual skill use and review

Available repository skills were read and applied at baseline `3880049`:

| Skill | Actual use | SHA-256 of local source |
| --- | --- | --- |
| `skills/test-driven-development.md` | API/config tests failed before implementation; invalid-date regression reproduced before correction | `64b03fce4aee5a97a93160cea8111f3ba13a17b7c001db4bd5836d67fd10705d` |
| `skills/verification-before-completion.md` | Baseline, required clean verify, full Python regression, smoke assertions and final scope/diff checks before completion/push | `2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3` |
| `skills/systematic-debugging.md` | Traced invalid-date exception, empty-URL binding, Jackson depth constraint and smoke readiness/port setup | `51c6435d98c83c42c96ba7c35725a0b2c376cd487fb1a4e6bd0ddbe7e33ef202` |

The TDD skill's referenced `writing-good-tests.md` is absent after searching the
repository and available local skills; use of that supporting file is not claimed.
Local skill source/version is recorded; an upstream original commit/license match
was not independently established and is not claimed. AI self-review checked scope,
null/freshness semantics, identity isolation, safe logging and legacy separation.
Human/affected-owner PR review and full V1-06 evidence remain pending.

## Pending live verification and scope

- Real Ditto deployment authentication/policies, TLS trust and actual Thing reads.
- Comparison of preserved source/event IDs with Bayan's real individual twins and
  Emmanuel's real V1 publisher; no unmerged teammate branch dependency.
- Live disconnected-source/freshness evidence and measured HTTP propagation budget.
- Affected-owner review of the still-proposed shared interface/defaults.
- Team full V1 acceptance, submission and human review.

Scenario routing, fleet aggregation/materialization, dashboard, expanded full-stack
CI, CARLA, Kanto, uProtocol and OpenSOVD implementations remain separate tasks.
The existing legacy pipeline still uses development adapters by default; this PR
does not describe those adapters as live or change their response contracts.
