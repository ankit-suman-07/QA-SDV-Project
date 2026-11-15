# V1-09 recovery checkpoint — November 15, 2026

**V1-09 BLOCKED: privileged Kanto lifecycle execution requires operator sudo authentication.**
No application launch, managed restart, runtime `state.started_at` or post-restart
MQTT→Ditto correlation was executed. Daemon readiness alone does not pass V1-09.
PR #43 remains draft/open; no merge or duplicate PR. Source baseline:
`f7d5f4f56c9441f578408b529c7201302ed1c166`.

## Observed outcomes

- [Daemon unit](daemon-unit.txt): active/running with corrected HOME and
  XDG_CONFIG_HOME, isolated namespace/socket, automatic deployment and remote
  Things integration disabled. Installed CLI help succeeds [here](cli-check.json).
- [Privilege gate](sudo-gate.json): sudo requires a password.
  [Unprivileged CLI](kanto-unprivileged.json): exit 1, socket dial deadline.
  This is an access blocker, not a daemon failure. Operator-reported imported
  image/index identity has not been independently inspected through root containerd.
- Python 3.12.16 recovered at
  `$HOME/.local/share/qa-sdv-v1/runtime/venv-3.12`, using `uv python install`,
  `uv venv`, then `uv pip install ... -r requirements-test.txt` (28 packages).
  Initial system Python 3.14.10 venv `runtime/python-env` was unused after
  grpcio-tools 1.68.0 source-build setup failed because `c++` was unavailable.
  No dependency pins changed; failed environment retained. Successful environment
  is [frozen](python-environment.txt). No unavailable old /tmp environment reused.
- [Authenticated twin access](ditto-access.json): HTTP 200 for both existing
  Things; credentials extracted in memory from official restored source
  `documentation/src/main/resources/pages/ditto/intro-hello-world.md`, not logged
  or saved. No policies/Things provisioned or overwritten.
- [Clock](clock.json), [chrony](chrony.json): synchronized, stratum 2, leap Normal,
  reported offset 0.000171384 seconds slow; not a guaranteed clock-error bound.
  Provider and observer share this host kernel clock.
- [Both KUKSA reads](kuksa.json): healthy LiDAR 35 m with current source times.
- [Ingress inspection](existing-ingress.json): none present before recovery.
  Exactly one [owned ingress restored](restored-ingress.json), with durable log
  and process identity in persistent runtime. [Log snapshot](ingress.log) shows
  new vehicle-001 persisted events. Reinspect ownership before any future start.
- [MQTT capture](mqtt-capture.json): three live vehicle-001 QoS 1 non-retained,
  HEALTHY/no-fault events with increasing source times and source ages within
  five seconds. [Exact property correlation](correlation.json) matches the final
  captured event to [real Ditto](vehicle-001-after.json). This confirms recovered
  ingress operation, not Kanto evidence. Capture ends on message count, not a
  complete duplicate-publisher exclusion interval.
- Vehicle-001 [before](vehicle-001-before.json) and [after](vehicle-001-after.json)
  remain HEALTHY and its telemetry advances. No lifecycle trial means continuous
  restart isolation has not been established. Vehicle-002
  [before](vehicle-002-before.json)/[after](vehicle-002-after.json) remains historical
  at `2026-11-15T07:09:20.427904Z`; authenticated access is not fresh propagation.
- [Docker inventory](docker-state.json): app-002 exited, app-001 and prerequisites
  running. No app-002 publisher started. [Rendered descriptor](descriptor.json)
  uses the requested image, host networking, loopback KUKSA/MQTT, vehicle-002 and
  unless-stopped policy. Effective runtime configuration remains unverified.
- [Targeted tests](targeted-tests.log): 153 passed. [Prior-head CI](pr-before.json):
  eight successful checks at the exact baseline SHA, including real two-vehicle
  core. These checks do not execute the Kanto pilot or establish full V1 acceptance.

## Remaining acceptance and service state

Operator must enable normal authorized privileged execution; no passwords in chat,
no weakened sudo/socket security. Exact initial operator command:

```bash
sudo /opt/qa-sdv-v1-kanto/bin/kanto-cm --host /run/qa-sdv-v1-kanto/container-management.sock --timeout 5 list
```

Then inspect namespace/image, confirm exclusive publisher ownership, start bounded
MQTT/twin observers, create only if absent, launch and managed stop/start using the
[runbook](../../../velocitas-app/kanto/LINUX-RUNTIME.md). Require exact real MQTT/
Ditto event properties and source strictly newer than pre-restart source,
start request and Kanto `state.started_at`; retain all intermediate vehicle-001
states. Missing lifecycle/runtime timestamps cannot be replaced with this baseline.
Same-device loopback evidence will not establish the historical remote-LAN task
wording or crash automatic restart; record those limitations during review.

Prerequisites and one recovered ingress intentionally remain running. Dedicated
Kanto daemon left unchanged; this session created/started no Kanto app. Docker
app-002 remains stopped. Observers exited. No faults/outages/full harness,
backend/fleet writer, volume deletion, network deletion or unrelated workload
changes occurred. Existing MongoDB volumes and historical evidence preserved.

Applied repository `skills/systematic-debugging.md` and
`skills/verification-before-completion.md`: investigated access and Python failure,
used documented Python version/dependencies, verified actual reads/ingress and
retained the unresolved gate. Missing supporting technique skills are not claimed.
Human acceptance/review remains pending.

## Operator-assisted continuation

After the operator confirmed `No containers found`, the agent retried normal
`sudo -n` and still received `sudo: a password is required`. The prepared
[bounded operator runner](operator-pilot.py) lets the operator perform the same
reviewed lifecycle from their authenticated terminal while collecting durable
live evidence. Its syntax was checked; execution/results remain pending and
must be reviewed before replacing BLOCKED. It reads the documented sample
credentials in memory and calls only dedicated Kanto operations plus read-only
containerd image inspection. MQTT and both real twins are sampled throughout
lifecycle commands. It leaves its created Kanto app stopped and Docker app-002
stopped. No broad sudoers or socket change is proposed.

```bash
sudo -v
$HOME/.local/share/qa-sdv-v1/runtime/venv-3.12/bin/python evidence/v1/kanto-recovery-20261115T141500Z/operator-pilot.py
```
