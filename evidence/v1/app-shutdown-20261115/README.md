# Graceful application shutdown — Ankit / Phase V1 lifecycle

Independent baseline main `6a965bb` (merged #43); branch
`ankit/fix/v1-graceful-app-shutdown`, persistent worktree `worktrees/app-shutdown`.
No initialization or HTTP compatibility code imported. The historical #43 pilot
remains valid and unchanged; this run tests the newly affected lifecycle boundary.

## Defect, correction and pinned lifecycle

SIGTERM previously called LOOP.stop under run_until_complete(main()), producing
RuntimeError and exit1. New asyncio.run entry point handles SIGTERM/SIGINT by an
Event. It cancels/awaits the owned run/monitor tasks, drains already dispatched
bounded reads/publication, closes direct KUKSA and SDK VDB/subscriptions, disconnects
both owned Paho clients and joins their network loops. Cleanup is idempotent; all
resource closes are attempted and failures remain nonzero exceptions.

Pinned native SDK0.15.7 start performs synchronous MQTT connect and native stop is
a no-op. This app has no SDK topic/data decorators. It keeps those same SDK Paho
connections but starts them through Paho2.1 connect_async/network-loop APIs, so
startup remains cancellable during broker outage. Public connect_timeout=2 seconds
bounds pending socket connects. KUKSA0.5.1 startup connection no longer executes an
unbounded GetServerInfo RPC; actual polling has a 2-second RPC deadline. Existing
publication, QoS1/PUBACK gating, reconnect and scenario logic remain intact.

Paho loop_stop returning INVAL means its thread is already None after disconnect,
verified from pinned implementation. It is accepted as completed cleanup, unlike
other return codes/errors. No exception is suppressed to force exit0.

## Actual verification and retained failed attempts

- [Initial red](red.txt): orderly lifecycle module absent. [Later Paho red](paho-already-stopped-red.txt)
  reproduces treating an already-finished network thread as a cleanup failure.
- [App suite](green.txt): 213 passed, 2 explicit skips (native SDK host dependency
  absent and external publisher integration unset). [Broad final Python regression](python-regression-final.txt)
  records the documented command; skips/deselections are not live passes.
- [First actual-image failure](first-image-failure.txt), [observer record](docker-live-first.json):
  observer subscribed before connection readiness and saw no events. Actual app
  published, then our overly strict Paho result handling caused nonzero cleanup.
  Both findings were investigated/corrected; failures retained rather than relabelled.
- [Final Docker cases](docker-live.json): two polling cycles with fresh-source exact
  Ditto matches, startup with broker absent, KUKSA absent, and broker paused until
  unacknowledged publication logged. All five application exits0, old PID0/runningfalse,
  completed shutdown logs, no observer failures. Stop durations0.199–1.145 seconds.
  Only a new test-owned broker was paused/resumed, never the existing broker.
- [Image identity](image.json) identifies committed source `6ad9a4bef847f55fe735b71632adb7690dee43f9`,
  linux/amd64 image/index and persistent archive hash. Runtime Python3.10, SDK0.15.7,
  KUKSA0.5.1, gRPC1.68.0/Paho2.1. Host tests use Python3.12.16.
- [Three actual Kanto cycles](../shutdown-kanto-live-20261115T152137Z/independent-review.json):
  operator used normal sudo in their terminal; no weakened socket/sudo security.
  Dedicated namespace, unique new pilot name, verified imported index. All three
  managed-stop exits0 and final cleanup exit0. All three new sources exceed previous
  source, start request and actual Kanto started_at, matching exact MQTT/real Ditto.
  Four completed-shutdown log entries, no RuntimeError; all restarted PIDs now absent.
  158 final twin samples keep vehicle-001 HEALTHY/fault-free, max gap0.350410 seconds.
  Result counts151 samples before cleanup; seven further cleanup/log reads are retained.

Only same-device managed restart is verified, not remote LAN or automatic crash
recovery. The Kanto descriptor/container remains stopped for inspection; Docker
app-002 remains stopped. Test Docker apps/broker remain stopped; original services,
one ingress, dedicated daemon and original database volumes/policies/twins preserved
apart from authorized normal telemetry updates. Separate Ditto18090 was used for
Docker smoke; Kanto uses existing Ditto18080/ingress with app-001 unaffected.

Applied repository TDD/debugging/verification instructions, exact files in baseline
Git; missing supporting skills are not claimed. Human review remains pending.
Combined candidate, final CI and all release decisions remain separate. No merge,
tag, release or report/video work performed.
