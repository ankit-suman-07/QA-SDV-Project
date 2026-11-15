# Phase V1 implementation verification

**Overall verdict: DEFECTS FOUND.** Component verification passed and real edge routing was exercised, but automatic provider recovery failed and the existing tire-pressure unit boundary remains inconsistent. Full live Ditto acceptance and the required Kanto pilot are blocked. **V1 is not ready to tag; a verified integrated baseline for V2 has not been established.** These conclusions concern technical acceptance; video, report, contribution statements and owner approvals are separate gates.

## Assessed revision and scope

Assessment date: **2026-11-14 (UTC)**. Branch `main`, HEAD **`ac701cd9a56ffd1031d6cd8744e413075ab4b955`**. The fetched `origin/main` has the same SHA. The checkout was clean before evidence creation. This assessment verifies that checkout, not an unmerged branch. No implementation code, specifications or historical evidence were changed; no commit, push, PR or merge was made.

Authority read: [SOURCE-OF-TRUTH](../SOURCE-OF-TRUTH.md), [scope/acceptance](../08-project-scope-and-acceptance.md), [architecture](../09-architecture-diagrams.md), [work distribution](../10-detailed-task-distribution.md), [C1–C10 contracts](../v1-interface-contracts.md), [independent development](../v1-independent-development.md), E1/E2 [design](../superpowers/specs/2026-11-11-v1-two-vehicle-edge-design.md)/[scenario design](../superpowers/specs/2026-11-11-v1-lidar-scenarios-design.md), their plans, and the [MVP comparison](mvp-to-v1-comparison.md). No applicable `AGENTS.md` was found. Repository [verification](../../skills/verification-before-completion.md) and [debugging](../../skills/systematic-debugging.md) guidance was applied: fresh outputs precede conclusions, and failures were traced without implementation repairs.

Merged history includes Bayan #30/#31/#32, Ankit #34 (A2)/#35 (A3)/#36 (A5), and Emmanuel #33 (E1)/#37 (E2). E1 merged at `5115168`, E2 at `3561c00`; the QoS correction includes `a3e20c1`. See the captured [history and baseline](../../evidence/v1/verification-20261114T051226Z/baseline-inventory.json). C1 and the detailed task distribution assign **Bayan individual-twin ingress/writes; Ankit fleet aggregation and the sole fleet-twin writer**. Older scope-table ownership language must be read with that newer allocation.

Scope retains **V1-09/Kanto as required, separately tracked**, not deferred: scope acceptance row V1-09 and C10 require a Linux launch/restart and a fresh event reaching vehicle-002's twin. Docker restart evidence does not satisfy it. CARLA, customized skills and unrelated Phase V2 work are excluded. The scope's proposed status and the contracts' pending affected-owner review are unresolved approval gates; this verification does not approve them on the owners' behalf.

Status vocabulary: **IMPLEMENTED** is code/configuration inspection; **UNIT-VERIFIED** uses isolated tests; **MOCK-VERIFIED** uses controlled substitutes; **LIVE-VERIFIED** names actual components exercised; **FAILED** is an observed defect; **BLOCKED** identifies an unavailable prerequisite; **NOT VERIFIED** means no sufficient result was obtained. A row can have several statuses. Historical records are not fresh passes.

## Acceptance verification matrix

| Requirement and expected behavior | Implementation / merged work | Tests and historical evidence | Fresh result | Remaining gap |
| --- | --- | --- | --- | --- |
| **V1-01**: two distinct synthetic providers, KUKSA brokers/apps and identified observations | E1 #33; `vehicle-simulator/docker-compose.v1.yml`, provider `src/main.py`, `velocitas-app/app/src/main.py` | Provider/app Python tests; historical E1 capture | **IMPLEMENTED; UNIT-VERIFIED; LIVE-VERIFIED** for both actual edge chains, distinct MQTT topics/IDs and separate loopback control/broker ports | Automatic recovery after KUKSA loss **FAILED**, F01. This is not full downstream acceptance. |
| **V1-02**: MQTT updates two real individual twins; invalid/unknown events cannot overwrite them | B1/B2 #30/#31; `ditto/mqtt_ingress.py`, `mqtt_subscriber.py`, `v1_writer.py`, `ditto_http.py` | Ingress, validation, HTTP/provisioning and persistence tests; historical `live-twin-api.md` | **IMPLEMENTED; UNIT-VERIFIED; MOCK-VERIFIED** for atomic feature writes, restart watermark reload, rejection and write failure; **LIVE-VERIFIED** actual QoS1/non-retained MQTT transport into ingress | Real authenticated Ditto policies/provisioning, atomic persistence, reconnect/redelivery and persisted watermark assertions **BLOCKED**. Memory-writer state is not a Ditto snapshot. |
| **V1-03**: targeted vehicle-002 fault/clear; healthy→fault→healthy in twins/API; 001 unaffected | E2 #37, A3 #35; provider control, `HttpSimulatorControlAdapter`, `DefaultDiagnosticActionService`, `scripts/run-v1-lidar-cycle.sh` | Scenario/backend tests; historical `scenario-routing.md`, `E2-lidar-cycle.md` | **IMPLEMENTED; UNIT-VERIFIED; LIVE-VERIFIED** actual Java A3→provider→KUKSA→app→MQTT; 001 stayed healthy; **MOCK-VERIFIED** same events into memory writer | Real twin/A2/fleet/dashboard transitions **BLOCKED**. Provider action/trace context matches acknowledgements; optional MQTT context absent, so chronology alone does not establish event-to-command identity correlation. |
| **V1-04**: live A2 reads, explicit missing/stale state and preserved source time | A2 #34; `V1VehicleService`, `V1VehicleController`, V1 Ditto adapter/configuration | 208 backend tests include live-mode HTTP substitutes, identity/freshness and failure cases; historical A2 record | **IMPLEMENTED; UNIT-VERIFIED; MOCK-VERIFIED** freshness/null handling; actual Java with inaccessible Ditto returned truthful unavailable/null and unknown ID404; real source silence preserved 002 event/source identity while 001 advanced | Actual twin-backed 5s/30s availability transitions, authentication recovery and read/write consistency **BLOCKED**. Backend connection refusal is not proof of all live HTTP failure modes. |
| **V1-05**: baseline and relevant unit/integration checks; repeatable two-vehicle fault/clear CI with dependency labels | Existing CI, Python tests, backend/frontend tests, E1/E2 configuration | Exact-head CI and Pipeline integration succeeded; baseline flow/KUKSA integration are narrower than full V1 | **UNIT-VERIFIED** Python 488 +385 subtests, Java 208, JS 7; **LIVE-VERIFIED** KUKSA 9 and MQTT 2; both Compose configs validate; **FAILED** recovery F01 | No fresh complete legacy Ditto demo; no complete real two-vehicle twin/API/fleet fault-clear acceptance in CI. Green CI does not satisfy those boundaries. |
| **V1-06**: recorded vendor-skill use, human review and requirement-to-test traceability | `skills/`, E1/E2 plans, `evidence/v1/skill-sources.md`, earlier reviews | Source/version and concrete design/test/review examples recorded; QoS issue was corrected rather than relaxed | **IMPLEMENTED** documentation/traceability; source hashes captured. Fresh verification/debugging guidance applied | Formal affected-owner approval provenance **NOT VERIFIED**; do not infer approval from merges or skill-use claims. |
| **V1-07**: tagged, rerunnable demonstration plus report/video/contributions | Startup docs, evidence index, E1/E2 scripts, comparison | Historical MVP/E1/E2 and A2/A3/A5 component records | **IMPLEMENTED** procedures; this fresh run is reproducible within its stated boundaries | V1 release tag, final integrated demonstration/video/report and contribution readiness **NOT VERIFIED**. Existing iteration tag is not V1 acceptance. |
| **V1-08**: fleet summary, materialized fleet Thing and dashboard reflect both live twins during fault/recovery | A5 #36; `FleetService`, `FleetMaterializer`, fleet provisioning, `frontend/js/fleet-*` | A5 backend/frontend tests and historical mock screenshot/HTTP write capture | **IMPLEMENTED; UNIT-VERIFIED; MOCK-VERIFIED** actual Java API/writer 12 checks plus actual Chrome 9 checks, screenshot, no page errors | Actual Eclipse Ditto fleet Thing, sole authorized writer under deployment, real fault/recovery browser and fleet-write failure/recovery **BLOCKED**. HTTP mock capture is not a real materialized Thing. |
| **V1-09**: Linux/Kanto launches/restarts002 app and fresh event reaches its twin | B5 #32; `velocitas-app/kanto/`, C10 | Python validation covers pilot tooling; historical records identify runtime evidence outstanding | **IMPLEMENTED; UNIT-VERIFIED** tooling; actual Docker app restart produced a post-start source observation | **BLOCKED**: no Kanto CLI/device or real twin access; no Kanto launch/restart evidence. Required, not deferred. |

## Fresh automated verification

All commands, environment overrides, exit codes, UTC timestamps and output filenames are retained in the [run manifest](../../evidence/v1/verification-20261114T051226Z/manifest.json). Evidence root: [run index](../../evidence/v1/verification-20261114T051226Z/README.md). Counts below exclude skipped/deselected tests.

| Check / command | Exit / result | Boundary and evidence |
| --- | --- | --- |
| `python -B -m pytest -q -ra -p no:cacheprovider -m 'not integration'` with SDK/protobuf paths | **0**; 488 passed, 385 subtests; one broker-dependent module skipped,9 integration tests deselected; two SDK callback deprecation warnings | [Python final](../../evidence/v1/verification-20261114T051226Z/python-unit-final.log). Protobuf generated into `/tmp`; SDK 0.15.7 supplied separately, not substituted with an unpinned SDK. |
| Java21 `bash ./mvnw --batch-mode --no-transfer-progress -Dmaven.repo.local=/tmp/qa-m2 clean verify` in `backend` | **0**; 208 tests,0 failures/errors/skips | [Backend output](../../evidence/v1/verification-20261114T051226Z/backend.log), [parsed suite counts](../../evidence/v1/verification-20261114T051226Z/backend-counts.json). HTTP test doubles remain mocks. |
| Node 22 `npm --prefix frontend test` | **0**; 7 passed,0 skipped | [Frontend output](../../evidence/v1/verification-20261114T051226Z/frontend-unit.log). |
| Both baseline and V1 `docker compose ... config --quiet`; `sh -n scripts/run-v1-lidar-cycle.sh`; tracked JSON parsing | **0** each; 33 JSON files parsed | `configuration-baseline`, `configuration-v1`, `cycle-script-syntax`, `json-configuration` metadata/output in manifest. Configuration parsing does not start the baseline. |
| `pytest -m integration vehicle-simulator/tests/test_kuksa_publication.py` with actual broker 56556 | **0**; 9 passed | [KUKSA output](../../evidence/v1/verification-20261114T051226Z/kuksa-live-signals.log). Actual broker/signals, not full twin integration. |
| MQTT transport tests with separate actual Mosquitto 28884 | **0**; 2 passed | [MQTT output](../../evidence/v1/verification-20261114T051226Z/mqtt-live-transport.log). QoS1 positive and QoS0 negative checks, isolated from live edge traffic. |
| Actual packaged Java + HTTP twin/provider/write substitutes; existing browser runner in actual headless Chrome | **0**; 12 smoke assertions +9 browser assertions;0 page errors | [Mock results](../../evidence/v1/verification-20261114T051226Z/mock-smoke-port3000/result.json), [browser](../../evidence/v1/verification-20261114T051226Z/mock-smoke-port3000/browser-result.json), [captured screenshot](../../evidence/v1/verification-20261114T051226Z/mock-smoke-port3000/fleet-mock-fault.png). **MOCK-VERIFIED**, including simulated fleet write/recovery. |
| Exact assessed SHA Actions | All recorded completed runs succeeded | [CI43559014750](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43559014750), [Pipeline43559014772](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43559014772), two image-publication runs in [snapshot](../../evidence/v1/verification-20261114T051226Z/ci-exact-sha.json). These do not run complete real V1 acceptance. |

Initial unsuccessful attempts are preserved, not counted as passes: Python collection initially failed with three missing generated-protobuf imports (exit 2); generating them outside the repository enabled the recorded final run. The first browser attempt used port 23000 outside configured CORS origins; a second reused stale harness connection metadata. Both exit 1 attempts are superseded by the clean port 3000 run. [Attempt notes](../../evidence/v1/verification-20261114T051226Z/mock-smoke/ATTEMPT-NOTES.json) explain mixed scratch artifacts. An initial live harness import-path error failed before live checks; the correctly configured final run is separately recorded. These setup failures are not implementation defect findings.

The host default Java 25 was not used for backend verification: the documented Corretto 21.0.13.0.11 JDK was downloaded into `/tmp`; Node 22.16.0 and an isolated Playwright driver were similarly used. Python tests used 3.12.16; built app runtime used Python 3.10.12 and pinned SDK 0.15.7. Docker app packages included grpcio 1.68.0, protobuf 5.29.5 and paho 2.1.0. Full versions and exact commands are in the manifest/package outputs; no credentials are included.

## Fresh live results and environment

Initial Docker inventory was empty and no Compose projects were active. Existing unrelated listeners were left alone. The owned project `qa-v1verify20261114` used loopback MQTT 28883, KUKSA 56556/56557, provider 28091/28092; actual Java A3 used 28082. The independent transport-test broker used 28884. [Override](../../evidence/v1/verification-20261114T051226Z/edge-override.yaml) and [rendered configuration](../../evidence/v1/verification-20261114T051226Z/edge-rendered-configuration.log) record secret-free configuration. Provider publication 5s and app polling 2s are configuration, not measured latency.

Actual images were built from this checkout. Captured image IDs:

| Image | SHA256 image identity |
| --- | --- |
| Test-owned app | `68c87df33526be780ce2848fd0349279721d889c476b211d018c2ef3e5799452` |
| Test-owned provider | `33a1ec03b816de2533d0f498602c1797ca3477643dd8ef22ab4547f33b8c1958` |
| KUKSA 0.7.0 | `9ace2824719ba7c05929f0af4827d9b25fa5ca7b2e0d58d0acff95885c649d6d` |
| Mosquitto 2 | `75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98` |

See [identity capture](../../evidence/v1/verification-20261114T051226Z/edge-image-identities.log). No actual Ditto deployment or credentials were available. No shared twins or policies were reset/provisioned. The final Java/browser smoke used explicit HTTP mocks; the real edge experiment used the actual ingress with an **in-memory recording writer**. None of its mock individual states are presented as Eclipse Ditto snapshots.

### Healthy, fault/clear and isolation boundaries

The [live checks](../../evidence/v1/verification-20261114T051226Z/live-edge/checks.json), [MQTT capture](../../evidence/v1/verification-20261114T051226Z/live-edge/mqtt.jsonl), [API responses](../../evidence/v1/verification-20261114T051226Z/live-edge/api-responses.json), and [Java configuration](../../evidence/v1/verification-20261114T051226Z/live-edge/configuration.json) show:

- Both actual providers/KUKSA/apps published healthy C3 events under their own identities/topics. Only 001 and 002 are in the V1 map. The separately maintained legacy registry's 003 is not a third V1 edge; live test configuration constrained the legacy list as well.
- Actual Spring Boot accepted the selected 002 obstruction and clear requests; action lookup agreed with dispatch acknowledgement. Provider action/trace context agreed with each request. Observations progressed to CRITICAL at 3m and recovered through 20m to 35m. 001 stayed healthy throughout. An acknowledgement was recorded separately from health completion.
- `v1_publisher.py:39–45` uses SDK 0.15.7's native Paho `_pub_client`, publishes QoS1/retain=false and waits for publish acknowledgement. The actual runtime transport confirmed this; the older SDK convenience publisher's QoS0 path is not the V1 delivery path. No contract relaxation was needed. PUBACK proves broker delivery, **not successful downstream twin persistence**.
- Source timestamps and event IDs were preserved into the memory writer. Source silence on 002 did not fabricate a new healthy observation while 001 continued. Six isolated malformed/unknown/mismatched/duplicate/equal/late messages left memory state unchanged. Subscriber restart reloaded its mock-backed watermark and rejected a duplicate. A simulated write failure did not advance mock state, and later processing recovered. This is **MOCK-VERIFIED persistence**, not a real Ditto durability/replay result.
- Actual Java returned unavailable/null against absent Ditto, and 404 for unknown V1 identity; it did not invent healthy state. Actual real-twin availability aging, HTTP authentication recovery, fleet Thing and browser behavior remain blocked.

### Recovery and freshness

A 12s MQTT outage recovered without manual app restart. A 12s KUKSA-002 outage exposed F01: provider 002 exited and remained stopped after the broker returned; manually restarting that owned provider restored publication.

The corrected [app-restart check](../../evidence/v1/verification-20261114T051226Z/app-restart/result.json) required an event whose source timestamp was later than the new container start. It passed: container start `05:24:26.173094181Z`, source observation `05:24:27.820583Z`, command-to-observed fresh MQTT 3.138s. This includes Docker restart and polling; it is neither a Kanto result nor a strict startup SLA. The original recovery harness could count an in-flight message; its 0.068s row is **excluded** from conclusions by the retained [qualification](../../evidence/v1/verification-20261114T051226Z/edge-recovery/qualification.json). Startup unavailability until a real first observation is expected. Neither this run nor a configured 5s provider interval demonstrates a violation of the C5 freshness threshold. Real downstream freshness boundaries remain unverified.

### Measurements

One trial per operation used a single host monotonic clock, immediately before the actual A3 POST through receipt of the qualifying MQTT observation. [Raw measurements](../../evidence/v1/verification-20261114T051226Z/live-edge/measurements.json):

| Operation | Dispatch acknowledgement | Observed MQTT completion | Real twin / API / fleet / dashboard completion |
| --- | --- | --- | --- |
| Inject 002 obstruction |0.126s|16.017s|**BLOCKED / NOT MEASURED**|
| Clear 002 obstruction |0.016s|9.992s|**BLOCKED / NOT MEASURED**|

These are **command-to-observed-MQTT fault/recovery completion times, including scenario progression**, not pure transport latency or an MVP speedup. MQTT events lack optional action/trace context: observed progression is temporally associated with this isolated test; the events themselves do not prove command correlation. No repeated-trial performance claim is made. All timeouts/failures in setup and recovery checks are retained alongside successful results.

## Confirmed defects

### P2 — V1-F01: provider does not recover when its KUKSA broker returns

**Location:** [provider write](../../vehicle-simulator/src/main.py#L182), [cleanup-only finally](../../vehicle-simulator/src/main.py#L213), [provider Compose anchor](../../vehicle-simulator/docker-compose.v1.yml#L30). The app anchor has a restart policy; the provider does not.

**Reproduction using the isolated deployment:** stop `kuksa-002` for 12s while provider 002 is publishing; start `kuksa-002`; wait 20s. Inspect provider status and MQTT 002. The actual provider throws an unhandled `kuksa_client.grpc.VSSClientError` with UNAVAILABLE/connection refused, exits 1, and remains exited after the broker returns. `docker inspect` reports restart policy `no`. Manually starting only provider 002 restores publication.

**Expected:** the source resumes publishing after its dependency recovers, or an explicitly managed recovery mechanism brings it back. **Observed/impact:** a temporary KUKSA outage permanently silences that vehicle until operator intervention. Source-derived downstream health should become stale/unavailable; no real Ditto aging claim is made here. Evidence: [failed recovery](../../evidence/v1/verification-20261114T051226Z/edge-recovery/results.json), [restart policy](../../evidence/v1/verification-20261114T051226Z/provider-restart-policy.log), [actual service traceback and restoration](../../evidence/v1/verification-20261114T051226Z/edge-final-service-logs.log). Recovery harness exit 1 is a genuine failed check.

**Correction required:** implement bounded connection recovery or a suitable managed provider restart/readiness strategy, and retain an actual KUKSA-outage recovery regression. No correction was made in this verification.

### P2 — V1-F02: existing tire-pressure kPa→psi boundary relabels the raw value

**Location:** [VSS declaration](../../vehicle-simulator/config/vss-with-autonomous-sensors.json#L5919) declares `Tire.Pressure` as kPa; [legacy bridge](../../ditto/scripts/interim-kuksa-to-ditto-bridge.py#L191) passes `float(tire_fl)` as `tire_pressure_psi`; [mapper](../../opensovd/fault_mapper.py#L111) emits psi-labelled data/thresholds. The [synthetic generator](../../vehicle-simulator/src/signal_generator.py#L14) uses values around 32.

**Reproduction:** inspect that declaration and bridge expression, then read the actual test broker's left-front tire pressure. The [fresh probe](../../evidence/v1/verification-20261114T051226Z/tire-unit-boundary.log) observed 31 on the kPa-declared path and confirmed the bridge performs no conversion before the psi argument. The legacy bridge itself was not launched against real Ditto.

**Expected:** the source declaration, physical meaning, conversion and destination units agree. **Observed/impact:** legacy health/diagnostic consumers cannot reliably interpret the pressure; correcting only one side could produce misleading thresholds. This confirms an existing contract boundary defect, not a new LiDAR regression, and does not establish what physical unit the generator author intended. **Correction required:** owners choose and document the canonical unit, then explicitly convert at the legacy boundary and verify thresholds. No requirement or implementation was changed here.

## Historical evidence versus fresh observations

The [evidence index](../../evidence/README.md), [baseline](../../evidence/v1/baseline.md), [A2](../../evidence/v1/live-twin-api.md), [A3](../../evidence/v1/scenario-routing.md), [A5](../../evidence/v1/fleet-dashboard.md), [E1](../../evidence/v1/E1-two-vehicle-edge.md), [E2](../../evidence/v1/E2-lidar-cycle.md), raw captures and [skill sources](../../evidence/v1/skill-sources.md) were reviewed with [previous findings](pr-33-review.md) and the [comparison](mvp-to-v1-comparison.md). Historical event counts/QoS captures are component evidence, not a fresh end-to-end acceptance result. This assessment independently confirmed current QoS behavior and real routing; it did not reuse historical screenshots as fresh browser evidence.

Earlier #33 QoS concerns are addressed by the merged publisher correction and fresh actual transport. E1/A5 evidence records coexist on current main; there are no checkout conflict markers requiring resolution. Current unit tests cover Unicode/nested legacy fault compatibility, validation, write ownership, atomic feature updates and failure handling. They establish those tested boundaries, not every real deployment behavior. Current Java tests cover A2, A3 failure outcomes and A5 aggregation/materialization; actual Chrome verification here is against controlled mock twin data.

Historical MVP revision discrepancies (`098fd2…` versus `f06aa9…`), the timing CSV's unestablished tested revision, and the missing `mvp-demo.log` remain as documented in the comparison. No historical revision, result or metric was rewritten. Those uncertainties must not become claims about this fresh run.

## Unresolved scope, contracts and approvals

- Obtain recorded affected-owner approval for the current C1–C10 boundary, especially units, health/freshness and deployment authentication subjects. C5 explicitly calls the 30-second unavailable cutoff a proposed default needing review; update/dispatch budgets and clock handling also remain open. Fresh checks assess the configured 5s/30s behavior, not evidence of an approved new requirement. Proposed document status is not silently converted to approved by this assessment.
- Confirm Bayan's individual ingress service and Ankit's sole fleet writer are the only authorized runtime writers. Code supports that split; real policy permissions and deployed process counts were not inspectable here.
- Retain V1-09 as a required separately tracked gate, or obtain an explicit authoritative scope amendment. Docker-only recovery does not close the Linux/Kanto requirement.
- Keep technical acceptance separate from submission readiness: no final V1 tag/video/contribution acceptance was established.

## Remaining checks and prioritized next actions

1. Address F01 and agree/correct F02. Rerun the relevant unit tests and actual provider→KUKSA outage/recovery test without a manual provider restart. Recheck legacy pressure semantics after the owner decision.
2. Supply an **approved isolated real Ditto endpoint**, legitimate read/write credentials, approved authenticated subject IDs and TLS settings securely. No credentials were invented or written to evidence. Follow [individual provisioning/startup](../../ditto/V1-TWINS.md), [ingress](../../ditto/MQTT-INGRESS.md), [A5 setup](../v1-independent-development.md) and [frontend startup](../../frontend/README.md). With ingress stopped for provisioning, use `python -B -m ditto.v1 provision --subject "$SDV_DITTO_SUBJECT"`, then `python -B -m ditto.v1 read all` and `python -B -m ditto.v1 run` with the documented secure environment. For fleet provisioning, use `python3 -B scripts/v1_fleet_provision.py` with its documented `SDV_V1_*` credentials and distinct owner/service subjects. Do not provision/reset shared twins or enable multiple fleet writers. [Blocked prerequisite list](../../evidence/v1/verification-20261114T051226Z/blocked-live-checks.json) records the unavailable boundaries.
3. Run both real edges, ingress, Ditto, Java21 backend in live mode and dashboard. Capture healthy 001/002 MQTT events, individual Thing features, A2 state/health, fleet API and materialized fleet Thing. Compare source/event identities while accounting for sample/poll timing. Submit 002 inject/clear through the actual backend; capture acknowledgements separately and follow each observed transition at MQTT→twin→API→fleet→dashboard. Verify 001 remains healthy. Clear all test-owned scenarios in a finally/exit path.
4. On isolated resources, exercise source silence and recovery at the configured 5s/30s thresholds, missing readings, real read/authentication failure, individual write failure, equal/late/duplicate/unknown/mismatched messages, ingress restart and MQTT reconnect. Assert invalid input cannot poison valid successors; persist watermarks only on successful writes and prove restart reload against real Ditto. A broker PUBACK alone is insufficient. Separately fail/recover only fleet writes while individual reads continue. Unit/memory-writer substitutes above do not discharge these live assertions.
5. Repeat the browser flow against those real services: healthy counts 2,002 fault count while 001 remains healthy, recovery, selected 002 routing, stale/unavailable rendering, unavailable LiDAR nulls, and fleet-write degradation/recovery. Save actual screenshots and page/network errors. Browser automation was available and used for mocks; **no real-twin dashboard browser pass is claimed**.
6. Run V1-09 on Bayan's Linux/Kanto device with approved images/networking. Capture Kanto versions, launch/restart status, fresh post-start source/event identity at MQTT and matching real 002 twin; restore any intentionally stopped source separately. Complete a repeatable real two-vehicle CI/recorded integration run, owner approvals, final report/video/contribution evidence and release tag decision before calling V1 accepted or beginning V2 from a *verified* baseline.

Use a new UTC evidence directory for subsequent runs. Record revision/dirty state, image identities, commands and honest component boundaries; use one monotonic clock for comparative command completion measurements. Include timeouts/failures. Measure twin/API/dashboard boundaries separately rather than deriving them from event count or polling intervals.

## Cleanup and evidence integrity

Test-owned scenarios were cleared; final provider context had no active scenario. The owned edge Compose project was brought down **without deleting volumes**, and the isolated transport broker was stopped. Harness-owned Java, HTTP mocks and browser processes were terminated. Final Docker inventory has no running test-owned services; no unrelated service was stopped. Build images, stopped transport-test container and ignored build/dependency caches may remain as non-running artifacts. Existing listeners were preserved.

The [manifest](../../evidence/v1/verification-20261114T051226Z/manifest.json), [machine-readable summary](../../evidence/v1/verification-20261114T051226Z/result-summary.json), [artifact hashes](../../evidence/v1/verification-20261114T051226Z/artifact-sha256.json), final service logs and copied harnesses preserve this run. Repository `*.log` ignore rules apply to raw outputs; files are saved locally and linked here, without changing ignore policy or staging them. Source/config hashes identify the assessed inputs. Only this report and fresh evidence artifacts were created. Markdown relative links and whitespace were checked after writing.

## Follow-up — 2026-11-15 UTC: integrated acceptance on an isolated prepared deployment

This dated follow-up preserves the November 14 assessment above. Ankit owns all
remaining Phase V1 remediation, integration, Kanto validation and release work.
The independent documentation alignment is [draft PR #40](https://github.com/ankit-suman-07/QA-SDV-Project/pull/40);
this harness/evidence work is [draft PR #41](https://github.com/ankit-suman-07/QA-SDV-Project/pull/41),
branched directly from main `f33e7cb`, without the documentation branch's commits.
The C1–C10 proposed status and pending decisions remain unchanged.

**V1 remains unaccepted and not ready to tag.** The prepared local deployment
passed the implemented core gates below. Unmodified deployment setup still has
confirmed defects; provider-recovery #38 and tire-unit #39 are open/unmerged,
Kanto/V1-09 is required and unverified, and release/submission/approval gates remain.
A successful run on a prepared deployment does not approve a new shared interface
or close the unmodified startup defects.

### Runs, dependencies and reproducibility

- [Initial attempt](../../evidence/v1/verification-20261115T023010Z/README.md): real Ditto and edges started; browser origin `127.0.0.1:3000` was outside existing CORS. Readiness failed; cleanup ran. No downstream acceptance claimed.
- [Unmodified stack](../../evidence/v1/verification-20261115T023435Z/README.md): legitimate local authentication worked, but no individual `v1` feature existed and the Spring client received HTTP 400. Healthy failed, two attempted operations timed out, and the observer was interrupted through cleanup (exit 130). Later gates were not reached.
- [Prepared deployment](../../evidence/v1/verification-20261115T024001Z/README.md): harness/application revision `2118300d313a973da6b6857507115f74418c8b35`; source was committed, dirty state contained only new evidence directories. All ten implemented core gates recorded PASS. The tool reported launcher exit 143 despite finalized results/cleanup; this anomaly is retained, not represented as an exit-zero run. A separately launched repeat records the observer's actual return code.

The [independently launched repeat](../../evidence/v1/verification-20261115T024553Z/README.md)
completed with **observer exit 0** recorded in `launcher.json`, all ten core gates
PASS and five more fault/recovery trials. Its own n/median/range and raw samples are
retained separately; no trials are pooled or discarded. It resolves the launcher
ambiguity for this repeat, without rewriting the earlier tool-reported exit 143.
The 12s outage recovered again under the 1s workload, not a closure of historical
F01/default-workload behavior. Both runs cleared scenarios and stopped owned projects.

All live components were real: two providers → two KUKSA brokers → two Velocitas
apps → one Mosquitto → the production ingress/Ditto writer → Eclipse Ditto 3.8.4
→ packaged Java 21 Spring Boot → derived fleet API and separately materialized
`sdv:fleet-v1` → an actual Chrome dashboard. No HTTP mock, memory twin writer,
request interception or third production vehicle participated. Invalid/replay inputs
were isolated component probes with apps stopped; they are distinct from the five
real-provider trials. Offline harness controls and existing mocked unit tests remain
labelled as such.

The [runner and rerun instructions](../../scripts/v1_acceptance/README.md) reuse the
existing two-edge Compose and pin official Ditto deployment source
`5dbb05e6294e5ac0103506102baff9eab755d180`. It assigns unique projects, loopback ports,
one ingress and one fleet writer. Credentials use the official local sample's
existing nginx authentication, passed through environment and excluded from evidence.
No shared twin/policy reset or unrelated service/volume removal occurred. The local
sample deliberately uses one subject for all roles; production subject separation
and permission approval remain open. Mutable third-party image tags are identified
by the captured image list; stronger digest pinning remains a deployment limitation.

### New confirmed setup defects and explicit preparation

**V1-F03 — properties-only persistence cannot initialize a missing feature.** The
existing create-only provisioning CLI creates a Thing with attributes but no `v1`
feature. The real ingress calls PUT `/features/v1/properties`; Ditto returns 404
and the observation stays pending. The unmodified-stack nginx/ingress logs show
successful whole-Thing GET followed by failing properties PUT. Unit mocks did not
establish this real creation behavior. Release needs an approved initialization
path that handles absence without fabricating health or losing watermarks, plus a
real clean-namespace regression.

**V1-F04 — packaged Spring client sends duplicate Accept-Encoding fields.** Real
Ditto returns HTTP 400 `gateway:duplicate.header.field` for both backend reads and
fleet writes. [Packaged Spring reproduction](../../evidence/v1/verification-20261115T023435Z/spring-http-response.txt)
and its Java source are retained. Direct Java HTTP/1.1 and HTTP/2 probes, including
Accept JSON, both returned 200; changing HTTP version alone did not explain it.
Release needs an approved client/proxy compatibility decision and regression.

The prepared deployment explicitly normalizes `Accept-Encoding` in its isolated
nginx configuration. Before ingress starts, it creates each initial `v1` feature
from that vehicle's **first real captured MQTT observation**, preserving IDs and
source time in `bootstrap-real-observations.json`. Those seed writes are provisioning,
not evidence of ingress persistence. Subsequent real observations and all fault/clear
transitions traverse the real ingress. Neither preparation changes application code,
adds a simultaneous writer, invents observations or resolves F03/F04 on the unmodified
stack. They are disclosed configuration prerequisites, not mock substitution.

### Verified boundaries on the prepared deployment

| Boundary | Recorded outcome / limits |
| --- | --- |
| Healthy and identity/source preservation | Exactly 001/002; actual topic/schema/QoS1/retain=false capture, Thing identities, source/event/LiDAR fields and API projections checked. |
| A3 fault/clear and isolation | Five actual backend injects and five clears; each reached all six observed boundaries. Vehicle-001 stayed healthy without corresponding faults; its own telemetry could advance. Dispatch acknowledgements recorded separately. |
| A2 freshness and nulls | Stopping only app-002 preserved source time while it aged STALE then UNAVAILABLE. Missing isolated feature returned explicit null health/faults/LiDAR/source/event fields. Both registered vehicles stayed in the fleet denominator. |
| A5 counts and materialization | Availability/health partition invariants checked independently for API and stored summary. API derives from individual twins; scheduled materialization has a separate evaluation time. Neither reads an old fleet Thing to answer vehicle/fleet queries. |
| Negative/replay/restart | Malformed, unknown, mismatched, duplicate, equal and late publications each left snapshots unchanged. Restarted ingress rejected replay from the persisted watermark and accepted a valid successor. |
| Individual write failure | Real test-owned policy denied only 002 feature writes: no snapshot/watermark advancement; 001 successor persisted. Restoring policy allowed the pending observation to persist. |
| Fleet write failure | Real fleet-policy denial held the stored summary unchanged while individual event IDs progressed and derived reads remained usable. Restoration resumed materialization. |
| Reconnect and outage | Actual MQTT stop/start recovered. A 12s KUKSA-002 stop/start recovered in this 1s-provider workload without a manual provider start; a fresh source timestamp after broker return reached Ditto. This single observation does not close historical F01 or merge #38. |
| Dashboard | Actual browser showed live healthy/fault/recovery views; screenshots saved for all ten operations. No page errors. A missing favicon 404 is visible in HTTP capture. |
| Baseline | Existing single-vehicle script passed separately. Runner's baseline row deliberately says separately required; see external-checks.json for the actual baseline pass and cleanup. |
| Kanto / V1-09 | BLOCKED: no installed Kanto CLI/runtime validation on the intended Linux host. Docker stop/start is not Kanto evidence. |

### Measurements and regression checks

[Raw trials](../../evidence/v1/verification-20261115T024001Z/measurements.json),
[statistics](../../evidence/v1/verification-20261115T024001Z/statistics.json),
[resources](../../evidence/v1/verification-20261115T024001Z/resource-summary.json)
and [limitations](../../evidence/v1/verification-20261115T024001Z/measurement-limitations.json)
are durable run artifacts. Each table cell is median seconds [minimum–maximum], n=5
for fault and n=5 for recovery; no recorded trial boundary failed in this prepared run.

| Command → observed boundary | Fault | Recovery |
| --- | --- | --- |
| MQTT | 3.688 [2.479–4.292] | 2.409 [2.147–4.067] |
| Individual twin | 4.138 [2.567–4.507] | 2.552 [2.345–4.280] |
| Vehicle API | 4.162 [2.582–4.523] | 2.568 [2.388–4.301] |
| Derived fleet API | 4.185 [2.597–4.542] | 2.583 [2.406–4.320] |
| Materialized fleet Thing | 5.584 [3.738–5.931] | 3.777 [3.488–5.930] |
| Dashboard | 5.588 [3.976–5.857] | 3.869 [3.721–5.932] |

Ten dispatch acknowledgements had median 0.007675s [0.005182–0.100842]. Completion
uses one host monotonic clock starting before A3 POST. These include deterministic
scenario progression, polling, reads and browser work; **not pure transport latency**.
Optional MQTT action/trace fields are absent, so isolated temporal association is
not causal command-ID matching. The 1s provider configuration and workload differ
from the MVP; no speedup is claimed. Source→twin polling observations assume shared
host-kernel UTC, without a measured clock error bound; 66 repeated observations
(including repeated event IDs) had median 1.251s [0.144–2.828], not 66 independent
propagation trials. The resource capture contains 536 Docker CPU/memory rows during
this workload; per-service counts/distributions and exact memory units are retained.
Observed trial success (5/5 each) is not every-message delivery/persistence success.

[External checks](../../evidence/v1/verification-20261115T024001Z/external-checks.json)
retain commands, exits and outputs: Java21 208 tests; Python3.12 492 tests plus 385
subtests (two explicit skips, nine integration tests deselected); Node22 seven tests;
actual KUKSA nine tests; isolated actual MQTT two tests; native SDK publisher eleven
tests in a disposable image with test-only pytest (two SDK Paho deprecation warnings).
The skipped host SDK/MQTT boundaries were exercised separately. Failed protobuf
collection, sandbox socket/stall attempt, contaminated MQTT negative control and
missing-pytest image attempt remain recorded. No failed attempt is counted as a pass.

### CI, Kanto and release prerequisites

The new bounded real-services workflow has readiness, a 30-minute observer bound,
cleanup, separate offline controls and 30-day named artifacts. The existing baseline
workflow remains unchanged. Repository-local sample authentication is configured via
Actions secrets `V1_LOCAL_DITTO_USERNAME` / `V1_LOCAL_DITTO_PASSWORD` and variable
`V1_LOCAL_DITTO_SUBJECT`; no production credentials are committed. CI outcomes and
artifact availability must be checked at the final PR SHA; implementation of a job
is not a successful CI execution. Preserve durable evidence before artifact expiry.

Ankit must finish V1-09 on a genuine Linux Kanto/container runtime: record OS/runtime
versions and architecture; use a reachable pinned V1-compatible image (current
publication targets linux/amd64); replace descriptor placeholders with actual
vehicle-002 KUKSA/MQTT LAN endpoints and verify firewall/auth/TLS support; use the
installed CLI's reviewed descriptor/lifecycle procedure; stop the Docker app-002 so
only Kanto publishes for 002. Capture pre/post-start source/event IDs with source
time strictly after the recorded start boundary, QoS/identity/freshness and matching
real Ditto updates while 001 stays unaffected. Restore suppressed source input
separately. Follow the [pilot preparation](../../velocitas-app/kanto/V1-PILOT.md),
whose historical placeholders and preparation-only claims do not constitute a run.

Before release: merge reviewed remediation through normal human review (no merges
or approvals were performed here), rerun F01 under its failing/default workload and
F02 at the legacy physical-unit boundary, resolve F03/F04, obtain affected-owner
contract/authentication/freshness/budget decisions, pass live CI/baseline and Kanto,
complete skill provenance/human review, report/video/contributions and a reviewed
release SHA/tag decision. Phase V2 CARLA and customized-skill comparison remain open.

Final evidence handling: upstream service logs included encoded Basic authentication.
Before any evidence push, the fresh text outputs were authentication-redacted and
trailing whitespace normalized; event/source IDs, timestamps and exit/results were
preserved. A failing redaction control preceded the sanitizer implementation; all
six offline controls and the full final Python suite passed (493 tests plus 385
subtests, two explicit skips and nine deselections). See `python-sanitizer-final.txt`
and red/green controls in the prepared run. The two actual live runs assessed
committed `2118300`; final `fc28548` adds only this tested evidence handling, with
no application or live acceptance assertion change.

CI run [43669268812](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43669268812)
at `2118300` had passing offline controls; its first live attempt correctly blocked
on then-absent credential settings. After configuration, attempt 2 reached real
verification but was force-cancelled before upload because it predated the sanitizer.
No credential-bearing artifact from that attempt was published. The only artifact
then listed was first-attempt `14143631616` (readiness BLOCKED, no configured secrets).
The replacement final-SHA workflow is required; no successful live CI result is
claimed by these local runs. Existing standard CI and baseline pipeline at `2118300`
passed. Final PR checks/artifact IDs remain the source for newer CI status.
