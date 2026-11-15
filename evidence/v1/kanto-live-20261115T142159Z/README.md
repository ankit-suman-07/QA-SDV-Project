# V1-09 — PASS, same-device managed stop/start

Live operator-assisted run on November 15, 2026, starting from PR #43 head
`633714cd48bfb883022e7c8799fab6f14ef3e5e6`, immutable app source
`92f3fc14a15ae7bd1aa6663bdedccb99a6c69446`. The operator ran the reviewed
[per-run observer](../kanto-recovery-20261115T141500Z/operator-pilot.py) from their
sudo-authenticated terminal because the agent terminal remained password-gated.
No credentials were shared in chat, logged or committed.

[Independent review](independent-review.json) confirms actual Kanto launch,
managed stop/start and exact fresh MQTT/real-Ditto propagation. This is the
V1-09 outcome in the requested same-device profile, not full V1 acceptance,
remote-LAN verification, crash auto-restart or clean shutdown acceptance.

## Runtime and event evidence

- [Imported namespace image](namespace-images.json) matches index
  `sha256:efad7228ebf00f092d43ec7242e2d60bdd56866d2f94f0afc3c8c5af9e6ac4a6`,
  linux/amd64. Successful create/start validates runtime resolution for this image
  on the installed Kanto 1.0.0 / containerd 2.4.2 setup; not general compatibility.
- [Descriptor](descriptor.json), [initial state](initial-state-parsed.json) and
  [restarted state](restarted-state-parsed.json) agree on environment, host network,
  nonprivileged mode, no devices and unless-stopped policy. Container ID is stable;
  PID changes 36351 → 37250. Initial runtime start:
  `2026-11-15T14:22:15.085508129Z`.
- [Initial exact match](initial-correlation.json) retains event
  `vehicle-002-f1519bc7b72b4e728ed6d8e4de2bfae1`, source
  `2026-11-15T14:22:20.700757Z`.
- [Managed stop](managed-stop.json) succeeded; [stopped state](stopped-state-parsed.json)
  reports running=false. [Start request](restart-request.json):
  `2026-11-15T14:22:23.959401+00:00`. [Managed start](managed-start.json) succeeded.
  Actual restarted `state.started_at`: `2026-11-15T14:22:24.216247116Z`.
- [Post-restart exact match](restart-correlation.json):
  `vehicle-002-88d5e09f279d4e06b08e7a726afca3db`, source
  `2026-11-15T14:22:25.713946Z`, strictly after all three boundaries, including
  **1.497699 seconds after runtime restart**. MQTT receipt:
  `2026-11-15T14:22:26.760616+0000`; observed real twin snapshot at
  `2026-11-15T14:22:26.866267+00:00` matches complete properties with eventId
  mapped to lastEventId. Identity, schema, health, faults and LiDAR all match.
- [Raw MQTT](mqtt.jsonl): five vehicle-001 and two vehicle-002 observations, all
  QoS 1, retain=false, HEALTHY/no faults, with increasing per-vehicle source times.
  Maximum source age at receipt 1.478962 seconds. Initial 12-second subscription
  interval contained no vehicle-002 event; Docker app-002 remained stopped and
  the dedicated Kanto namespace was initially empty. No replay publisher started.
- [Twin timeline](twin-timeline.jsonl): 109 samples of exactly the two vehicle
  identities, maximum sample gap 0.381037 seconds; vehicle-001 stays HEALTHY,
  fault-free and advances its own source throughout launch/stop/start/cleanup.
  The runner result counts 104 samples before cleanup; final timeline includes
  five additional cleanup observations. Sampled isolation cannot exclude changes
  between observations. Host clock [synchronized](clock.json),
  [chrony tracking](chrony.json) retained; UTC comparisons share host clock and
  reported synchronization is not a guaranteed bound on clock error.

## Reproduced shutdown gap

Both [managed stop state](stopped-state-parsed.json) and
[final state](cleanup-state-parsed.json) report application exit_code=1 despite
successful Kanto stop commands. [App logs](kanto-app.log), captured read-only via
[helper](collect-kanto-log.py), show `RuntimeError: Event loop stopped before
Future completed.` at `/workspace/app/src/main.py:276` on **both stops**. This
reproduces the earlier Docker shutdown issue in Kanto. The current source installs
signal handlers that call LOOP.stop while run_until_complete(main()) is active,
consistent with that failure. No shutdown fix or image replacement was included;
clean shutdown remains an explicit follow-up/review gap. App successfully restarted
and produced the required fresh correlated event, so this does not erase the
observed managed restart/propagation outcome.

## Checks, cleanup and readiness

Recovery [targeted tests](../kanto-recovery-20261115T141500Z/targeted-tests.log):
153 passed. CLI help/rendering, effective descriptor comparison, timestamp/event
checks, complete JSON and log parse, secret-pattern scan and diff checks were
reviewed. No complete fault/outage harness was run. Historical evidence retained.

[Cleanup stop](cleanup-stop.json) succeeded and [final Kanto state](cleanup-state-parsed.json)
is running=false, manually_stopped=true, pid=-1. Descriptor/container retained
for inspection; do not rerun the create-only observer against this existing name.
[Observer stop](observer-stop.json) removes only the uniquely named MQTT observer;
[exit](capture-exit.json) is retained. Edge prerequisites, one ingress and dedicated
Kanto daemon remain running. Docker app-002 remains stopped. No backend/fleet writer,
fault injection, twin/policy replacement, volume deletion or network deletion.
MongoDB volumes and unused docker_default network remain intact.

PR #43 is ready for evidence review, remains draft/open, and is not merged.
Remaining gaps: shutdown exit 1, human review, historical remote-LAN task wording,
automatic crash restart untested, and the other full V1 acceptance/release criteria.
Latest-head CI must be assessed separately; green core CI is not Kanto evidence.
