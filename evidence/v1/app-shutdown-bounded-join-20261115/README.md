# d8c1f40 targeted shutdown verification — final stop checkpoint

Confirmed defect: asyncio.to_thread client join can remain blocked after wait_for
times out; asyncio.run then waits forever for its default executor.
[Red subprocess regression](stalled-join-red.txt) times out after9 seconds.
Source d8c1f4048522da3e79a81e6ee5919017b941b00d uses owned daemon close helpers
with explicit deadlines. Incomplete cleanup still raises and exits nonzero;
no forced-success exit or hidden client error. KUKSA close uses the same boundary.

[Final targeted app suite](green-bounded-join.txt):214 passed,2 explicit skips.
[Actual image](image.json), [five Docker cases](docker-live.json): all application
exits0; two fresh-source exact real-Ditto polling matches, absent-broker startup,
KUKSA absence and unacknowledged publication. Only owned test broker paused/resumed.
[Summary](targeted-verification.json). Previous failed attempts/old image evidence
are preserved in sibling directories, not overwritten.

No new Kanto trial was executed for d8c1f40. The prior three-cycle real Kanto PASS
was source6ad9a4b and remains historical. A reviewed new-name operator runner is
prepared here but not run. No full combined re-verification was started after the
user's stop instruction; earlier combined PASS6a6badc predates this correction.
Latest shutdown-head CI and final combined smoke remain pending.

All new Docker app/broker containers are stopped and retained. Separate test Ditto
is stopped after the probe, with database preserved. Original prerequisites,
app-001, ingress and dedicated Kanto daemon remain; Docker app-002 and prior pilots
stay stopped. No merge/tag/release/report/video activity.
