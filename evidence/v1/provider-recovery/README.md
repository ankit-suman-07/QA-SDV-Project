# V1 provider recovery — Ankit

Date: 2026-11-14 UTC. Branch: `ankit/fix/v1-provider-recovery`.
Independent baseline: `f33e7cbbb4968fec28d2d5acf4f10df246fa9fba` (`main` and fetched `origin/main` matched; clean primary checkout). No existing task branch/PR was found before creation. Owner for this repair: **Ankit**, by the current task instruction; historical component authorship is retained.

## Requirement and root cause

Closes the provider recovery boundary in [F01](../../../docs/findings/v1-implementation-verification.md), supporting V1-01/V1-03/V1-05 and C2–C5. Read the source-of-truth, scope, task allocation, contracts and independent-development guide. Applied the repository TDD, systematic-debugging and verification skills; referenced `writing-good-tests.md` and `root-cause-tracing.md` are unavailable and their use is not claimed.

The previous main allowed `VSSClientError` to escape the publication loop. Compose has no provider restart policy. An UNAVAILABLE causes the process to exit; an RPC without a deadline can also remain blocked. A restart-only fix would reset the provider's in-memory selected scenario. Instead, retain the process/controller and retry only transient SDK status4 (deadline) or14 (unavailable).

## Chosen strategy

- Nonblocking client connection (`ensure_startup_connection=False`) avoids the pinned0.5.1 SDK's unbounded startup GetServerInfo RPC. Actual publication RPCs have a2s deadline; the SDK may issue metadata and multiple per-signal RPCs, so this is **per RPC**, not a2s whole-batch budget.
- On a transient error, close the context-managed client/channel, back off1/2/4/5s (cap5s), then create a new client. No busy loop or unbounded individual RPC. A successful batch resets backoff. Permanent permission/schema errors still fail rather than being hidden.
- Keep the controller and last successful generator state outside the reconnect loop. Failed attempts do not advance scenario progression; no stale datapoint queue is replayed. Next attempts construct fresh datapoints from the then-current scenario. No fabricated health or receipt-time replacement of observation time.
- SIGINT/SIGTERM set an interruptible stop event; normal waits/backoff are interruptible, channels close, the control server shuts down, and original signal handlers are restored. Provider Compose grace30s accommodates an in-flight bounded multi-RPC batch; the baseline gets the same grace.
- No new twin writers, identity changes, pressure conversion, fleet changes or V2 work.

## Test-first and fresh results

| Evidence | Result / boundary |
| --- | --- |
| [red.txt](red.txt) | Exit1:4 failing new retry/lifecycle cases,2 existing passing; the new loop API was absent. |
| [original-failure.txt](original-failure.txt), [reproducer](reproduce_original.py) | Exit0 reproducer confirms actual **baseline main** lets SDK UNAVAILABLE escape and closes resources. SDK/control boundary substituted: **MOCK**, not real KUKSA failure evidence. |
| [first-green-attempt.txt](first-green-attempt.txt) |2 failures from an incorrect new test ladder expectation20→10; existing trajectory actually20→8. Test expectation corrected; no ladder implementation change. |
| [green.txt](green.txt) | Exit0:6 focused tests, including capped retries, state/scenario continuity, shutdown and permanent-error passthrough. |
| [final commands](final-commands.json), [full Python output](final-check-0.txt) | Exit0:492 passed +385 subtests;1 broker-dependent module skipped,9 live tests deselected,2 existing SDK Paho callback deprecation warnings. Compose V1/baseline and diff whitespace checks exit0. Skips/deselections are not passes. |
| [fixed live result](fixed-result.json), [MQTT capture](fixed-mqtt.jsonl), [service logs](fixed-services.txt), [commands](fixed-commands.json) | Exit0: actual providers/KUKSA/apps/Mosquitto. Both brokers individually killed/restored; both providers automatically produced fresh post-restoration observations with restartCount0. Other vehicle continued HEALTHY. Initial absent broker recovered; SIGTERM exited0. No manual provider restart used for the two outage-recovery assertions. A separate explicit provider restart tested startup with broker absent. |

The initial sandbox-only full run could not bind local sockets: `WriterTests::test_real_requests_against_loopback_mock_http` failed and9 `test_control_server.py` fixtures errored;6 mock transport tests skipped. It was interrupted after stalled shutdown; [output](python-suite.txt) preserves466 passes,7 skips,9 deselections,9 errors and the failure. The network-enabled full suite above is authoritative, not the blocked attempt.

### Important baseline qualification

The fresh graceful-stop baseline and abrupt-stop baseline attempts **did not reproduce the historical provider exit**: their in-flight RPCs waited and publication resumed after broker return. Their expected-reproduction assertions therefore exited1. Preserve [initial result](initial-baseline-result.json), [second result](baseline-result.json) and associated commands/logs as contrary observations, not claimed failed product runs. The previous verification recorded actual exit1 and no restart, while the deterministic substituted SDK reproduction independently shows the unhandled-error path in this exact baseline. Recovery/error outcome depends on connection timing. The correction handles both unbounded waiting and escaped transient failures; no claim is made that every12s outage killed original main.

## Runtime and isolation

Pinned provider requirements, Python3.12.16 unit environment, actual Python3.10 provider image, KUKSA0.7.0, SDK0.15.7 app and Mosquitto2; [image identities](image-identities.txt). Unit SDK is separately supplied on PYTHONPATH; generated protobuf files live outside the repository. [Manifest](manifest.json) records revisions, versions and input hashes.

Owned projects `qa-recovery-baseline`/`qa-recovery-fixed` used loopback29883,57556/57557,29091/29092. [Harness](live_check.py) and [override](live-override.yaml) are reproducible and credential-free. It requires those ports free and the named local app/provider images; build provider from this branch and use approved E1 app image as recorded. It clears only owned services via Compose down; no volume deletion. No unrelated services or shared twins were changed. All test-owned services stopped. Raw logs use tracked `.txt` files, not globally ignored `.log` names. A synthetic fixture Authorization header in the failed sandbox traceback is explicitly redacted; no real credentials were used.

## Review and remaining boundaries

Actual fresh MQTT source/event identity establishes this edge recovery boundary; **not** real Ditto/API/fleet/dashboard/Kanto acceptance. Existing owner approvals and full integrated V1 gates remain. Historical main evidence stays unchanged.

The pressure PR is independent, but both touch provider main. Merge/rebase can require combining `publication_values(observation)` with this reconnect loop; do not restore an old inline unconverted publication or remove timeouts. Recheck full Python tests and live outage/pressure checks after integrating both. No merge or approval is performed by this task.

## Merge preview

A three-tree preview against the common baseline confirms **content conflicts in `vehicle-simulator/src/main.py`**. [Preview](merge-preview.txt) contains both branches’ source, not an accepted resolution. Recommended order: recovery first, then rebase pressure on updated main and use `publication_values(observation)` inside the recovered loop with `timeout=2.0`. Keep the helper definition and both sets of tests. This is an integration conflict, not a functional dependency; the pressure branch remains independently based on main.
