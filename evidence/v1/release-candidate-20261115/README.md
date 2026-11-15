# UNMERGED INTEGRATION CANDIDATE — November 15, 2026

## Final stop checkpoint — d8c1f40 INCLUDED

Current candidate includes shutdown source d8c1f40 and branch checkpoint5211375.
[Exact inclusion and pending checks](delta-d8c1f40.json). Targeted app214/2 skips
and five actual Docker cases pass. **Final combined and Kanto verification after
this correction are PENDING.** The complete combined PASS below tested6a6badc,
before d8c1f40; do not relabel it as current-candidate or final-main verification.
No further enhancement/full integration run started after the stop instruction.


**Engineering checks PASS within the recorded boundaries; not verified main or a release.**
Ankit assembled exact independent fix commits in a persistent worktree, without
merging a PR or changing main. [Inputs/assembly](included-commits.json) records
main `6a965bb`, F03 `cd89160`, F04 `0a010eb`, shutdown `9c899c8`.
Actual tested candidate: `6a6badc207e3cf43f6bba1d1c9584538d6450fed`.
Working tree at execution contained only new evidence artifacts, recorded in live
manifest; no dirty implementation code. The only integration conflict was appended
README prose; both independent corrections were retained. No implementation conflict.

## Checks actually run

- [Python](python.txt): **540 passed, 386 subtests; 2 skips, 9 integration deselections**.
  Skips: external configured MQTT publisher integration and unavailable native SDK
  in host Python3.12 environment. Actual pinned SDK image/runtime is checked separately.
- [Java21 clean verify](java.txt): **209 passed**, zero failures/errors/skips.
- [Node22 frontend](frontend.txt): **7 passed**. Host initially had no Node; restored
  official Node22.23.5 archive after checking official SHA256
  cdeb8670a0c81f51b4dc4ac61919f9b1ad917b304bf8221eb939570663d240f8.
- Both baseline/V1 Compose configurations validated. [Versions/clock/workloads](versions-readiness.json).
- [Selected real run](../release-candidate-live-20261115T152908Z/candidate-verdict.json):
  nine affected gates PASS. A new project/network/database, not shared reset.
  [Before publishers](../release-candidate-live-20261115T152908Z/clean-provisioned-before-edge.json)
  has V1 absent on both Things. Sole ingress initializes from real provider/app MQTT;
  no manual bootstrap. Original upstream nginx configuration, no header normalization.
- Five backend-routed fault and five clear trials reached MQTT, individual twins,
  API, fleet API/materialized Thing and actual Chrome dashboard. Vehicle-001 isolation
  checked throughout. Source aging/null, invalid/order/restart, individual/fleet denied
  write recovery, affected MQTT reconnect and final dashboard all PASS.
- [Images](../release-candidate-live-20261115T152908Z/image-identities.json),
  [actual image source hashes](../release-candidate-live-20261115T152908Z/actual-app-source-hashes.txt),
  [independent clean-boundary review](../release-candidate-live-20261115T152908Z/clean-boundary-review.json).
- Unaffected provider/KUKSA outage recovery and existing baseline workflows are reused
  from merged #38/#39 and exact fix-head CI, not rerun unnecessarily. Kanto is reused
  from merged #43 plus the shutdown fix's three newly affected actual managed cycles.
  REUSED gates are clearly separate from this live run's PASS gates.

[Raw results](../release-candidate-live-20261115T152908Z/results.json),
[command exits](../release-candidate-live-20261115T152908Z/commands.json),
[statistics](../release-candidate-live-20261115T152908Z/statistics.json),
[measurements/limitations](../release-candidate-live-20261115T152908Z/measurement-limitations.json),
[screenshots](../release-candidate-live-20261115T152908Z/dashboard-final.png).
All image/source identities, environment versions, configs, logs, snapshots and
browser/resource observations are retained. Command-to-observed completion includes
scenario and polling work, not pure transport latency. No matched MVP speedup,
production delivery-rate guarantee, cross-host clock bound or scalability claim.

## Cleanup and limitations

Candidate scenarios cleared; only candidate projects stopped/removed without volume
removal. [Process exits](../release-candidate-live-20261115T152908Z/process-exits.jsonl)
retain expected termination signals for observers/Java; these are not relabelled
application exits0. Shutdown app exits0 are independently recorded in its own live
records. [Final workload/volume inventory](final-workloads.json) confirms original
prerequisites and one ingress remain, Docker app-002 stopped, dedicated daemon active.
The separate Part B stack is stopped with database retained; some third-party Ditto
services reached stop timeout/exit137, retained in inventory, not a clean-shutdown
claim for those services. Old failed test app and new successful test containers
are stopped and retained for inspection. Existing MongoDB volumes and unused
docker_default network preserved. No shared policies/Things reset.

Remote LAN and automatic crash restart remain unverified. Same-device V1-09 is
passed at its stated boundary. Main still needs reviewed fix merges and final-SHA
checks. C1–C10/principal/freshness/budget/clock decisions, human review, complete
historical skill provenance and release/submission gates remain open. Report/video
creation/recording/submission excluded from this work and remain pending. No tags,
releases, approvals or PR merges performed.
