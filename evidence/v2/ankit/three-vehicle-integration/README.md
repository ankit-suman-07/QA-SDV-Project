# V2 three-vehicle integration readiness

Starting main `5c0686853beb26b0e3fd558e655147fc11d2cb17`.
[Staged local setup, captures and continuation commands](../../../../scripts/v2_acceptance/README.md)

## Prerequisites and disposition

GitHub showed #52–#53 and #55–#59 merged. Bayan's health/recovery PR #54 was
open and draft at `734c358c87f00c52d108d021dea56237418ab9f5`. The fetched
main contained no reviewed CARLA extractor or production V2 health/ingress
owner stack. No owner branch was imported. No CARLA module was importable
with local Python, neither CarlaUE4 nor nvidia-smi was on PATH, and the
local Docker inventory did not supply a CARLA image. Those checks establish
this runner's missing prerequisites. Remote availability and clock skew
remain unmeasured. No CARLA, Docker stack, Kanto or native service was
started.

| Gate | Status | Evidence or exact blocker |
|---|---|---|
| One CARLA actor through browser, then three | BLOCKED | Needs Emmanuel's reviewed extractor, manifest and real CARLA host, Bayan's production Velocitas and ingress entry points, and a joined configuration including the authorized dashboard gateway. |
| Fault/clear/recovery, dropout/silence, aging and peer isolation | BLOCKED for real traffic | Same owner dependencies. Separate status ordering still needs Bayan's reviewed handoff. Existing prep vectors cover simulated recovery, timing and rejection. |
| Ordering and session rejection, ingress restart, denied and failed writes | BLOCKED for real V2 persistence | Requires reviewed ingress and scoped Ditto policies; loopback substitute checks cannot attest real authorization or persisted watermark. |
| Executor success/failure/timeout | BLOCKED for real executors | No reviewed live result and lifecycle endpoint mapping. #58 verifies the backend tracking with loopback substitutes. |
| Native selected-vehicle health and fault read | BLOCKED for joined V2-06 | [Bayan's later native probes](../../task-1/README.md) add real Rust/MQTT 5 and CDA/DoIP/UDS evidence with fixtures to the earlier source-inspection note. The production selected-vehicle URI/payload, CDA project fault/provider mapping, and permissions remain unapproved. No transport pin is changed here. |
| CARLA-backed Kanto | BLOCKED | Existing same-device V1 restart evidence is historical and synthetic. There is a cached V1 edge image and local Kanto installation. Neither supplies the reviewed V2 CARLA-fed app, real observation correlation or publisher isolation. |
| Joined browser and raw live correlated artifacts | SKIPPED | Blocked by the first gate. [Prior Chrome component evidence](../dashboard/README.md) used synthetic routes on `bacaba1816b9bdb9f024f43859f11295709b2918`. The frontend is unchanged here, so that check was reused at its original scope. No live artifacts exist for this run. |

The inherited KUKSA/MQTT probe used actual isolated components with
synthetic input, including broker write timestamps and retry behavior.
[Publisher component handoff](../observation-kuksa-adapter/README.md#publication-continuation)

## Local inventory and cleanup

Read-only `docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'` and
`docker image inspect --format '{{.Id}} {{json .RepoDigests}}'` completed
with Docker permission. The cached references returned these digests:

| Image | Local digest |
|---|---|
| ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0 | sha256:9ace2824719ba7c05929f0af4827d9b25fa5ca7b2e0d58d0acff95885c649d6d |
| eclipse-mosquitto:2 | sha256:75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98 |
| eclipse/ditto-gateway:3.8.4 | sha256:8d560c823952981d0d5b62f853f7be7207f6a7b9ed4a7414672d203b505b8af3 |

Existing project containers `qa-v1-kanto-prereq-ditto-nginx-1`,
`qa-v1-kanto-prereq-ditto-swagger-ui-1` and `qa-v1-kanto-prereq-edge-app-001-1`
were present at both inventory checks. No owned services or volumes were
created. Loopback test servers closed at suite exit.

## Executed checks

Applied Ankit verification-before-completion v1.0.0 to distinguish blocked
runtime prerequisites and original evidence scope from tested trace and
CI changes. No versioned Ankit TDD derivative was available.

- At `772780914d69f4200110d4c3ec83764048362d25`, JDK/backend product code
  was unchanged. The Python 3.12 non-integration CI-equivalent suite
  `python -m pytest -q -ra -m "not integration"` ran with loopback permission
  and the five CI protobuf modules generated into a temporary PYTHONPATH.
  Exit 0, 578 passed, 461 subtests passed, 2 skipped (V1 MQTT host and native
  SDK), and 9 deselected. Java was not rerun locally.
- At the same checkpoint Node 22.23.5 `cd frontend && npm test` exited 0
  with 12 passed. `python -m scripts.v2_dev.check` exited 0 with 8 tests
  and 23 synthetic fixture files and guide links checked. The CI YAML parsed
  with PyYAML. The workflow adds a Node job and prep check, retaining the
  existing Java, Python, Compose and Docker checks.
- `python -m unittest tests.test_v2_trace -q` on
  `18c295ca6492168f39e80461b5f23df498613363` exited 0 with five tests.
  Shared synthetic observation, health and twin fixtures exercise one and
  three identity joins, unavailable capture, wrong topic and mismatches.
  An initial browser mismatch assertion failed because the test mutated
  its API sample by reference. Separate browser fixture values fixed the
  test. The focused verification covered the later inactive actor mapping
  change. These are synthetic checker tests.
- The CLI returned exit 2 and BLOCKED with the shared fixture manifest and
  an absent trace path. `git diff --check origin/main HEAD` passed.
