# Final d8c1f40 candidate verification — resumed November 15, 2026

**UNMERGED INTEGRATION CANDIDATE: selected engineering checks PASS.**
[Exact tested/input revisions and scope](final-verdict.json). Source includes final
bounded shutdown d8c1f40. Python541 +386 subtests (2 skips,9 deselections), Java209,
frontend7 and both Compose configurations passed. [Actual live results](../release-candidate-live-20261115T183301Z/results.json)
pass nine selected gates: clean provisioned startup, healthy state,5 backend-routed
fault/clear trials, aging/null, invalid/order/restart, individual/fleet denied-write
recovery, affected MQTT reconnect and dashboard. Both features absent before edge
startup; sole ingress initializes real observations; original nginx without header
normalization. Actual app source hashes match current committed code.

[Final same-device Kanto verification](../shutdown-bounded-kanto-live-20261115T182944Z/independent-review.json)
passes3 managed restarts with exact fresh source/event/Ditto matches and exit0;
154 final twin samples keep001 healthy. This closes the earlier d8c1f40-pending
checkpoint without changing its historical statements/results.

New logs, config, screenshots, raw measurements/statistics and resource samples are
under the linked live folder. Source/UTC/monotonic and polling limitations remain
explicit; no matched MVP speedup or reliability-rate claim. Unaffected provider and
legacy baseline boundaries reused from prior merged evidence and exact-head CI.
The runner's reused-Kanto reason still references its earlier snapshot; this final
verdict links the independently verified newer d8c1f40 run explicitly.

Only owned candidate projects/observers were cleaned without volume deletion.
Original edge/real Ditto/one ingress and dedicated daemon remain running; original
Docker app-002 and all Kanto pilots remain stopped. Separate Part B stack/test
containers stopped with database retained. Final checks recorded in final-state-checks.json.

No final-main/full V1 acceptance, remote-LAN or automatic crash-recovery claim.
Human approvals, final merged-head CI/smoke and release/submission decisions remain.
No merge/tag/release/report/video action. Earlier checkpoints are preserved.
