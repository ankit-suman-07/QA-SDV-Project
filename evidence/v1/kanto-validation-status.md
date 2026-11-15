# Phase V1 Kanto validation preparation

## Runtime prerequisite follow-up — 2026-11-15, after PR #42

Baseline: `92f3fc14a15ae7bd1aa6663bdedccb99a6c69446`, the confirmed merge
of [PR #42](https://github.com/ankit-suman-07/QA-SDV-Project/pull/42).
Main was fetched and fast-forward checked; the clean original checkout and all
other worktrees were preserved. New isolated worktree `/tmp/qa-kanto-live`, branch
`ankit/test/v1-kanto-live-validation`; no existing task branch/PR was found.
Everything in this follow-up uses this Linux device, as instructed. No remote
host, Kanto app launch/restart, outage, fault trial or full pilot was used.
Ankit retains V1-09; **V1-09 is NOT complete**.

The current prerequisite status supersedes the older table below, whose evidence
is retained unchanged. Sources/skills were reread: SOURCE-OF-TRUTH, scope, task
distribution, C10, original pilot guide, verification findings and PR #41's
`verification-20261115T024553Z` record. Repository systematic-debugging and
verification skills informed the investigation; no applicable AGENTS.md or
additional supporting skill files were found. No production behavior changed.

| Prerequisite | Status | Observed result |
|---|---|---|
| Linux/Docker | READY | Fedora 44 x86_64; Docker and containerd active; initial Docker inventory empty. Existing containerd configuration and unrelated workloads were not changed. |
| Kanto binaries / flags | READY | Official x86_64 Kanto 1.0.0 archive checksum matched; CLI/API 1.0.0, build `c23e90e`. CLI and daemon unpacked under `/tmp/qa-v1-runtime/kanto-1.0.0/container-management`. `create --file`, `get/start/stop --name`, `list`, `--host`, and daemon flags inspected. No daemon started. |
| Kanto daemon and runtime compatibility | BLOCKED | Root-owned `/run/containerd/containerd.sock` denies this user; `sudo -n true` requires a password. No Kanto socket/service exists. Need secure operator sudo authentication, isolated daemon setup and compatibility checks against containerd 2.4.2. Do not replace Docker/containerd or change socket permissions globally. |
| MQTT capture tooling | READY | Cached official linux/amd64 Mosquitto client 2.1.2/libmosquitto 2.1.0 executes through Docker with explicit client entrypoint; successful real `%j` captures include receipt, topic, QoS and retain. No native system package was installed. |
| GHCR pull | BLOCKED | Exact old/current-main tags both denied with existing GitHub credential (HTTP 403 `DENIED`); anonymous token request 401. Package API explicitly requires `read:packages`. Authentication/authorization failure is confirmed; image absence is **not** established. No token printed, saved or new login performed. |
| Local source image / export alternative | READY | Built current main with revision label, linux/amd64; exact image/export hashes below. No credentials required. |
| Kanto image availability | BLOCKED | Export exists, but import into isolated containerd namespace and Kanto cache/resolution remain unverified because root/runtime access is blocked. A Docker image does not establish Kanto availability. |
| Real KUKSA and networking | READY | Both local providers return fresh real readings through host ports 55556/55557: healthy LiDAR 35 m, tire pressure 221/220 kPa at the captured instants. Container apps use service DNS; Kanto descriptor uses host networking and loopback host ports. No outage/recovery trial repeated. |
| Real MQTT | READY | Host 127.0.0.1:18883, healthy source-derived QoS 1 non-retained observations captured. Baseline-only Docker app-002 was briefly run and then stopped in `finally`; it is not Kanto evidence. |
| Clock | READY | `NTPSynchronized=yes`, NTP enabled, chronyd stratum 3, leap Normal. Initial observed system offset 0.000415507 s fast; raw tracking output retained. All containers share this host kernel clock; recheck before pilot. This is not a guaranteed bound on clock error. |
| Real Ditto / individual access | READY | New test-owned official Ditto 3.8.4 stack at 127.0.0.1:18080, authenticated HTTP 200 using the repository-documented official local-sample credential; both intended Things read successfully. No shared resources were reset. |
| Individual ingress / write subject | READY | One ingress with client ID `qa-v1-kanto-prereq-ingress` runs on this host; `nginx:ditto` has checked READ/WRITE policies. A newer real vehicle-001 event was persisted after ingress startup. No second individual writer is running. |
| Backend/fleet configuration | READY | Java 21 backend read smoke verified exactly two registered identities and a fresh healthy vehicle-001 event/source matching real Ditto, with the legitimate local subject. Owned backend stopped afterward. Absent test-owned fleet Thing/policy provisioned; fleet writer deliberately disabled and **not live-verified**. Only Spring Boot may materialize fleet; production subject separation/approvals remain open. |
| Exclusive app-002 handoff | READY | Docker app-002 stopped; Kanto daemon/app absent; no fixture replay. New Compose overlay profiles out app-002 and leaves app-001 active. Recheck process/container ownership before every Kanto start. |

### Durable observations and local state

[Manifest and command exits](kanto-prerequisites-20261115T070500Z/manifest.json),
[KUKSA readings](kanto-prerequisites-20261115T070500Z/kuksa-readings.json),
[MQTT baseline](kanto-prerequisites-20261115T070500Z/mqtt-baseline.jsonl),
[Ditto access](kanto-prerequisites-20261115T070500Z/ditto-access.json),
[writer/policy configuration](kanto-prerequisites-20261115T070500Z/writer-configuration.json),
[001 exact prepared twin](kanto-prerequisites-20261115T070500Z/vehicle-001-prepared-twin.json),
[002 exact prepared twin](kanto-prerequisites-20261115T070500Z/vehicle-002-prepared-twin.json),
[001 newer ingress snapshot](kanto-prerequisites-20261115T070500Z/vehicle-001-live-ingress-twin.json).
These are fresh **prerequisite/baseline** observations, not post-Kanto-start data.
The initial access record correctly shows absent features before preparation.
The [actual backend read](kanto-prerequisites-20261115T070500Z/backend-real-read.json)
used Java 21 and the documented per-vehicle health endpoint. An initial observer
mistook the vehicle-list object for health rows; that failed probe and its cleanup
are retained separately, not attributed to a production defect or hidden.

Official Ditto source is existing checkout `/tmp/qa-v1-ditto-source`, revision
`5dbb05e6294e5ac0103506102baff9eab755d180` (3.8.4). Unique Compose projects:
`qa-v1-kanto-prereq-edge` and `qa-v1-kanto-prereq-ditto`. Rendered local configs
are `/tmp/qa-v1-runtime/edge.json` and `/tmp/qa-v1-runtime/ditto.json`.
The isolated nginx config retains PR #41's explicit Accept-Encoding normalization.
As in its recorded preparation, absent individual `v1` features were initialized
from actual MQTT observations with their exact event/source identity, only before
starting ingress. Conditional create writes never replaced an existing feature.
These are deployment workarounds, not fixes or approval of provisioning gaps.

The verified app image is
`docker.io/library/qa-v1-kanto-app:sha-92f3fc14a15ae7bd1aa6663bdedccb99a6c69446`:

- Docker image/index identity: `sha256:efad7228ebf00f092d43ec7242e2d60bdd56866d2f94f0afc3c8c5af9e6ac4a6`.
- OCI revision label: `92f3fc14a15ae7bd1aa6663bdedccb99a6c69446`; linux/amd64.
- Export `/tmp/qa-v1-runtime/kanto-app-92f3fc1.tar`, SHA-256
  `e38c7eb081dda149535b62d4a7767f9b36b8dc19aa5f0a595e58e54d3fa66403`.
- Official Kanto archive SHA-256:
  `3d28098008e27621624f28adb880d1e3ed93654c29fb5919bcfca21c439d593a`.

The initial Compose `--build` rebuilt app-001 without OCI labels and moved the
tag; this was detected and the verified exported tag restored. Running app-001's
different image/index identity is recorded in the manifest; its rootfs layers
match the verified build. It was not restarted for metadata alone. The new overlay
clears inherited app builds to prevent recurrence. Rebuild only providers through
Compose; build/export the app explicitly with revision labels.

The binary/image archives remain local prerequisites, not Git artifacts. If lost,
redownload the official checksum-verified archive and rebuild/export from the
recorded source; record any changed image identity rather than reusing old hashes.
The raw capture, snapshots, command outputs and build log are tracked durably.
Trailing whitespace in captured build/Maven logs was normalized for Git checks;
the manifest names the affected logs. Results, identities and values are preserved,
and artifact hashes cover the reviewed tracked files.

### Exact continuation commands and configuration

Use the new [Linux runtime runbook](../../velocitas-app/kanto/LINUX-RUNTIME.md)
for the administrator gate, namespace import, daemon readiness, launch/restart,
timed captures and cleanup. Its commands are **prepared, not executed**, except
the explicitly recorded prerequisite commands. The
[same-device config](../../velocitas-app/kanto/pilot-config.local-linux.json)
uses `remote_lan=false`, MQTT 127.0.0.1:18883 and KUKSA 127.0.0.1:55557.
The [Compose overlay](../../velocitas-app/kanto/compose.prerequisites.yml)
binds all edge ports to loopback and disables Docker app-002 by default.

Credentials remain out of tracked configuration. Python reader/ingress variables
are `SDV_DITTO_BASE_URL`, `SDV_DITTO_USERNAME`, `SDV_DITTO_PASSWORD`;
backend reads use **`SDV_V1_DITTO_BASE_URL`, `SDV_V1_DITTO_USERNAME`,
`SDV_V1_DITTO_PASSWORD`**, and fleet writes additionally use
`SDV_V1_FLEET_USERNAME`, `SDV_V1_FLEET_PASSWORD`, `SDV_V1_FLEET_ENABLED`.
These are different namespaces; the old Python-only environment instructions
below do not configure Java. No credentials are added to command lines or files.
The isolated sample subject is not approval of production authentication design.
Load the new [secret-free backend configuration](../../velocitas-app/kanto/backend.local-linux.env.example)
before any backend start: it explicitly restricts vehicle IDs to 001/002 (the
application's broader default includes 003), binds loopback port 18081 and maps
provider ports correctly. No application default or interface was silently changed.

Services intentionally left for continuation: both providers/KUKSA instances,
MQTT, app-001, real Ditto, and one ingress. Docker app-002 is stopped; backend,
fleet writer and Kanto are absent. Ingress PID is recorded in
`/tmp/qa-v1-runtime/ingress.pid`; live output is `/tmp/qa-v1-runtime/ingress.log`.
Inspect PID command/start identity before any stop; do not trust a stale PID.
Immutable evidence contains a snapshot of the live log, not a growing tracked file.
No faults or outages require restoration. To tear down preparation, stop this
owned ingress and only these two named projects without volume deletion, as the
runbook specifies. Do not perform unrestricted Compose up during Kanto use.

**Next session cannot yet run the actual pilot.** An operator must authenticate
sudo securely on this Linux device, install/start the isolated Kanto daemon,
verify containerd compatibility and import/resolve the recorded image. Do not send
a password/token in chat or loosen shared runtime permissions. Once those gates
pass, use the recorded observer-boundary and exact MQTT→Ditto correlation checks;
retain all failures and vehicle-001 intermediate states. Static results and green
CI do not complete V1-09. No contract, release requirement or approval is waived.

Fresh verification: the available complete Python suite passed **516 tests and
386 subtests**, with two explicit skips (live publisher integration unset;
native Velocitas SDK absent) and nine integration tests deselected. No live fault,
outage or Kanto tests were substituted. New static CI checks exercise default
app-002 exclusion, opt-in two-vehicle identities, loopback-only port mappings,
cleared inherited app builds and failure when the verified image variable is
unset. Actual local CLI help checks and config rendering passed; daemon list
still fails as expected. Markdown links, runbook Bash syntax, JSON, and
`git diff --check` passed. See
[static results](kanto-prerequisites-20261115T070500Z/static-results.json) and
[Python log](kanto-prerequisites-20261115T070500Z/python-regression.log).
Java 21 `clean verify` also passed **208 tests**; the bounded real backend read
smoke passed and its owned process was stopped. Java/frontend application code
was unchanged; frontend checks were not rerun for these configuration changes.

## Historical PR #42 preparation record (preserved)

Prepared 2026-11-15 UTC by Ankit. **PREPARATION COMPLETE; LIVE V1-09 BLOCKED.**
No Kanto installation, container lifecycle operation, live pilot, twin write or
release consolidation was performed. Static checks and Docker metadata inspection
are not Kanto runtime evidence. Exactly two vehicles remain required.

## Baseline and requirements

Baseline main: `755916e0efea1f5dab58b7f5b71c8db63e41c129`.
The following merges were independently read from GitHub and are ancestors of
that baseline:

| PR | Scope | Merge SHA |
|---|---|---|
| [38](https://github.com/ankit-suman-07/QA-SDV-Project/pull/38) | Provider recovery | `ed5016c7b96f32191eb1b1b3a6737895b63a1063` |
| [39](https://github.com/ankit-suman-07/QA-SDV-Project/pull/39) | Pressure publication units | `e3a4c506c1a5b1a4cb6bd46fb728cc163b1ff1d9` |
| [40](https://github.com/ankit-suman-07/QA-SDV-Project/pull/40) | Ownership/architecture documentation | `0e837f5f8eef71de57a9cdd69b626bcf999193aa` |
| [41](https://github.com/ankit-suman-07/QA-SDV-Project/pull/41) | Integrated acceptance tooling/evidence | `755916e0efea1f5dab58b7f5b71c8db63e41c129` |

No existing branch/PR for this task was found. Work uses an isolated worktree;
other checkouts and historical evidence are preserved. Applicable references:
[SOURCE-OF-TRUTH](../../docs/SOURCE-OF-TRUTH.md),
[scope](../../docs/08-project-scope-and-acceptance.md),
[task distribution](../../docs/10-detailed-task-distribution.md),
[C10 and C2–C5](../../docs/v1-interface-contracts.md),
[independent development](../../docs/v1-independent-development.md),
[original pilot guide](../../velocitas-app/kanto/V1-PILOT.md).
Repository TDD, systematic-debugging and verification skills were read; no
applicable AGENTS.md was found. Historical contributors remain credited.

V1-09 requires actual Linux Kanto to launch and restart app-002, a fresh
post-start observation on MQTT persisted in its **real** individual Ditto Thing,
and vehicle-001 remaining unaffected throughout. Ankit owns this remaining work.
Kanto RUNNING, MQTT acknowledgement, Docker restart and HTTP mocks cannot satisfy
the requirement. Kanto validation does not waive other V1/release requirements.
No proposed interface, numeric threshold or approval status is amended here.

## Inspected prerequisites

| Boundary | Preparation result / remaining prerequisite |
|---|---|
| Linux | Available locally: Fedora Linux 44 Workstation, x86_64, kernel `7.3.3-200.fc44.x86_64`. Not a Mac/Windows host. Clock synchronization has not been verified. |
| Kanto | `kanto-cm` absent; no Kanto/container-management systemd units found. Install a reviewed Fedora-compatible Kanto/runtime configuration in a later authorized session; the documented upstream DEB procedure cannot be assumed suitable for Fedora. No remote host identified or contacted. |
| Runtime | Docker available; containerd `v2.4.2` (`b7a25261e029d68978bbf290df0a62fc819b3c51`) and its socket present. Kanto compatibility, namespace, daemon access and image resolution are unverified. |
| Image | Main publish workflows succeeded, but anonymous inspection of `ghcr.io/ankit-suman-07/qa-sdv-project-autonomous-health-app:sha-755916e0efea1f5dab58b7f5b71c8db63e41c129` returned GHCR token HTTP 401. Supply legitimate pull access or a reviewed accessible registry; resolve and record an immutable digest, revision label and linux/amd64 manifest through the Kanto runtime. |
| Cached image | Docker has `qa-v1verify-app:20261114`, ID `sha256:68c87df33526be780ce2848fd0349279721d889c476b211d018c2ef3e5799452`, linux/amd64, without a revision label. This does not establish its source revision, registry availability or Kanto/containerd availability. Do not substitute it as proven baseline. |
| Edge/network | Docker container inventory empty at inspection. No two-vehicle services or endpoint reachability verified. Need both real providers/KUKSA instances, one MQTT broker and app-001. Select same-host or LAN topology explicitly and verify routing/firewall. |
| Ditto | Need the identified isolated real Ditto deployment, existing permitted policies/Things, legitimate credentials and one individual-twin ingress writer. No live Ditto endpoint or credentials validated in this preparation. Do not reset shared Things/policies. |
| Capture | Existing `scripts/v1_dev/mqtt.py` fixture tooling lacks receipt/QoS/retain capture needed here. Use Mosquitto JSON capture below; `mosquitto_sub` is not installed locally. No fixture replay during the pilot. |

The app image and descriptor were inspected statically: current app supports
V1 source-derived observations and retry-preserved identity; the descriptor uses
host networking, vehicle-002, native middleware, unprivileged execution and
`unless-stopped`. These inspections do not verify effective runtime settings.
Spring Boot remains the sole fleet materializer; do not introduce a second
individual writer or fleet writer for the pilot.

## Secret-free configuration

Use a local, reviewed copy of
[pilot-config.example.json](../../velocitas-app/kanto/pilot-config.example.json).
Set `vehicle_id=vehicle-002`, `container_name=autonomoushealthapp-vehicle-002`,
`image` to the verified registry digest, separate KUKSA/MQTT hostnames or IPs,
their actual host ports, polling interval 2.0 and the existing restart policy.
The example addresses/image are placeholders. Do not use legacy `deploy.sh`.

For the existing two-edge Compose defaults, host-reachable ports are MQTT
**18883**, KUKSA-001 **55556**, KUKSA-002 **55557**. On a remote Linux host use
the approved edge host's reachable address, never Compose-only service DNS.
With an explicitly selected same-host deployment, use `remote_lan=false` and
loopback; record the topology and confirm it meets the agreed pilot deployment
expectation before acceptance. `remote_lan=true` deliberately rejects loopback.

Rendered environment must include `SIMULATED_VEHICLE_ID=vehicle-002`,
`SDV_MIDDLEWARE_TYPE=native`, `DATABROKER_HOST`/`DATABROKER_PORT`,
`SDV_VEHICLEDATABROKER_ADDRESS=grpc://<host>:<port>` and
`SDV_MQTT_ADDRESS=mqtt://<host>:<port>` matching the real endpoints.
This renderer supports plaintext grpc/mqtt endpoints, not credentials or TLS;
use only the approved isolated network. A topology requiring authenticated/TLS
edge endpoints needs a reviewed configuration change, not embedded secrets.

Ditto reader/ingress uses `SDV_DITTO_BASE_URL`, `SDV_DITTO_USERNAME`,
`SDV_DITTO_PASSWORD`, optional `SDV_DITTO_TLS_CA`, and bounded timeout settings.
Load legitimate secrets from the approved local secret mechanism into process
environment; disable shell tracing and do not record environment dumps, auth
headers, passwords or registry tokens. Never add secrets to the descriptor or PR.

## Exact next commands — future pilot only, gated

Run from repository root on the selected Linux host. Stop on any failed
prerequisite. Set `PYTHON` to the reviewed Python 3.12 interpreter, `PILOT_CONFIG`
to the reviewed secret-free local JSON path, and `RUN_DIR` to a new
`evidence/v1/kanto-validation-<UTC timestamp>` directory. Capture each command's
exit status and reviewed/redacted logs. Do not run the following lifecycle
commands until Kanto, image, endpoints, real Ditto and publisher ownership pass
preflight. These commands were **not executed** in this session.

```bash
git rev-parse HEAD
git status --short
uname -srm
timedatectl status
kanto-cm --help
kanto-cm create --help
kanto-cm get --help
kanto-cm start --help
kanto-cm stop --help
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config "$PILOT_CONFIG" --check-cli
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config "$PILOT_CONFIG" --mode validate
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config "$PILOT_CONFIG" --mode render > "$RUN_DIR/descriptor.json"
docker compose -f vehicle-simulator/docker-compose.v1.yml ps -a
kanto-cm get
```

Record installed Kanto/package/daemon versions and effective settings. The
upstream CLI supports `create --file` and `get/start/stop --name`; verify those
flags on the installed version before using them. The preparation help check
alone does not validate these flags or daemon readiness. See the
[official CLI source](https://github.com/eclipse-kanto/container-management/tree/main/containerm/cli)
and [installation prerequisites](https://eclipse.dev/kanto/docs/getting-started/install/).

If edge services must be started, first confirm the selected Compose project is
test-owned, has no conflicting baseline ports, and record its previous state.
Start only these services, never an unrestricted `compose up` during Kanto use:

```bash
docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build mqtt kuksa-001 kuksa-002 provider-001 provider-002 app-001
```

Verify both providers/KUKSA and MQTT ready with fresh healthy source readings,
and real Ditto reads/writes authorized. Identify the existing ingress and
Spring Boot processes; use their documented deployment interfaces if missing,
not a second ad hoc writer. Do not automatically provision or replace Things.
Before stopping Docker app-002 record whether it was running, then:

```bash
docker compose -f vehicle-simulator/docker-compose.v1.yml stop app-002
docker compose -f vehicle-simulator/docker-compose.v1.yml ps -a app-002
```

Require app-002 stopped and no other vehicle-002 publisher, fixture replay or
Kanto instance active. Inventory process/container identity, not just MQTT
traffic: MQTT event identity alone does not prove which runtime produced it.
If the Kanto name already exists inspect it and stop for an owner/configuration
decision; **do not replace it**. Only if absent create it:

```bash
kanto-cm create --file "$RUN_DIR/descriptor.json"
kanto-cm get --name autonomoushealthapp-vehicle-002
```

In a dedicated observer terminal, capture before the first launch and keep it
running through restart. Install/verify the Mosquitto CLI first. For this isolated
plaintext broker, this read-only command records received timestamp, topic,
QoS, retain and escaped raw payload (format `%j`, not payload-only `%p`):

```bash
TZ=UTC mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -q 1 -V mqttv5 --retain-as-published -t sdv/vehicle-001/health -t sdv/vehicle-002/health -F '%j' -W 180 > "$RUN_DIR/mqtt.jsonl" 2> "$RUN_DIR/mqtt.stderr"
```

Verify subscription readiness before proceeding (receive vehicle-001 events).
Preserve exit status: exit 27 can mean the bounded observation window expired;
it is not evidence of successful acceptance. Any connection/error/empty capture
or missing required stage blocks acceptance. Do not clear retained messages.
The capture format/options are documented by
[Mosquitto](https://mosquitto.org/man/mosquitto_sub-1.html).

Then launch, wait for healthy app-002 MQTT and real twin persistence, and snapshot:

```bash
kanto-cm start --name autonomoushealthapp-vehicle-002
kanto-cm get --name autonomoushealthapp-vehicle-002
"$PYTHON" -m ditto.v1 read all > "$RUN_DIR/before-restart-twins.json"
kanto-cm stop --name autonomoushealthapp-vehicle-002
kanto-cm get --name autonomoushealthapp-vehicle-002
"$PYTHON" -c 'import datetime,json,time; print(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"monotonicNs":time.monotonic_ns()}))' > "$RUN_DIR/start-request.json"
kanto-cm start --name autonomoushealthapp-vehicle-002
kanto-cm get --name autonomoushealthapp-vehicle-002
```

In a second observer terminal, begin repeated real twin snapshots before the
stop/start sequence (export `PYTHON` for the child shell):

```bash
export PYTHON
timeout --signal=TERM 60s bash -c 'while true; do "$PYTHON" -c '\''import datetime,json,time; print(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"monotonicNs":time.monotonic_ns()}))'\''; "$PYTHON" -m ditto.v1 read all || exit 1; sleep 1; done' > "$RUN_DIR/twin-timeline.log" 2> "$RUN_DIR/twin-timeline.stderr"
```

Exit 124 denotes the expected bounded capture deadline, **not acceptance**;
exit 1/read errors must be retained and investigated. Timeline entries separate
the observer's pre-read timestamp from each whole-Thing result; do not interpret
it as a Ditto persistence timestamp. Record capture return UTC/monotonic time
too when calculating completion bounds. A blocking read is terminated at the
outer deadline; incomplete final output is not a valid snapshot.

Confirm STOPPED before the second start. Record start return time too. Poll
`"$PYTHON" -m ditto.v1 read all` with a bounded 60-second observer deadline,
saving each successful snapshot with UTC receipt and monotonic time; retain
errors and nonzero exits. This reads actual Ditto through existing credentials,
not the backend cache or HTTP mock. Save a matching snapshot as
`after-restart-twins.json`. Do not overwrite failed observations with a final
healthy state. A timed-out or uncorrelated stage is BLOCKED/FAILED.

## Required event correlation and isolation

For each decoded MQTT payload, validate C2–C4 and exact allowed topic/vehicle.
Keep pre-restart vehicle-002 event ID/source, all intermediate observations and
the start-request boundary. The accepted post-start event must have:

- `schemaVersion=1.0.0`, topic `sdv/vehicle-002/health`, matching `vehicleId`,
  QoS 1, retain false and expected healthy fields without injected faults.
- A different `eventId`, `sourceTimestamp` strictly newer than both the
  pre-restart source and start-request UTC, and observer receipt after start.
  A new ID over old source, retained replay or an earlier queued event fails.
- Source age at receipt within C5's 5-second freshness and 1-second future
  tolerance. Record measured UTC synchronization/skew across provider,
  observer and backend hosts; clock uncertainty crossing the restart boundary
  makes post-start provenance inconclusive. Do not replace source with receipt.

Match the exact captured event against Thing `sdv:vehicle-002`:
`attributes.vehicleId`, `features.v1.properties.vehicleId`, `lastEventId`
(MQTT `eventId`), `sourceTimestamp`, `health`, `faults`, `lidar` and any present
command context. A later unrelated twin update does not prove this event.
Poll/capture fast enough to retain a matching snapshot; if missed, collect
another fresh post-start event and its matching persisted snapshot.

Every observed vehicle-001 event must remain HEALTHY with no faults, correct
topic/identity and monotonic source progress. Capture its twin repeatedly before,
during stop/start and after; ensure independent healthy updates continue, rather
than requiring its whole changing snapshot to remain byte-identical. Check
exactly the two allowed vehicle identities throughout; fleet Thing is not a third
vehicle. A transient isolation failure must survive in the evidence and fail the
pilot, even if final snapshots recover.

Use the observer monotonic clock for lifecycle-to-observed completion intervals.
Mosquitto `%j` receipt timestamps are wall-clock: disclose that limitation and
clock sync assumptions; do not call lifecycle/scenario completion transport
latency. Do not claim MVP speedup. Explicit stop/start proves managed lifecycle
restart, not automatic crash-restart policy; record that distinction.

## Cleanup and restoration (also on interruption/failure)

Stop only the named pilot Kanto container and confirm stopped:

```bash
kanto-cm stop --name autonomoushealthapp-vehicle-002
kanto-cm get --name autonomoushealthapp-vehicle-002
```

Only after confirmed Kanto stop, and **only if Docker app-002 was previously
running**, restore it with:

```bash
docker compose -f vehicle-simulator/docker-compose.v1.yml start app-002
docker compose -f vehicle-simulator/docker-compose.v1.yml ps -a app-002
```

If Kanto stop cannot be confirmed, leave Docker app-002 stopped and report the
handoff blocker. On exit terminate only the observer process owned by this run;
retain logs and all failed stages. This pilot injects no scenarios or outages.
If any are introduced later, record and clear only test-owned scenarios and
restore test-induced outages using documented interfaces. Stop only services
newly started by this run after restoring the agreed initial state. Do not run
`down --volumes`, remove shared policies/Things, restart host daemons, or remove
unrelated containers. No cleanup command was needed in this preparation session.

## Preparation verification and next-session gate

Fresh static/configuration results are recorded below after execution. They
cover renderer/identity/restart settings, non-deploying modes and handoff guidance;
they do not establish a working Kanto/image/network/real-Ditto chain.
The new handoff regression first failed for the missing plan, then passed.

| Fresh check | Result |
|---|---|
| Python runtime | Python 3.12.16, pre-existing isolated environment |
| Pilot preparation suite | 149 passed |
| Entire app suite | 205 passed, 2 skipped |
| Broader Python regression | 516 passed, 386 subtests passed; 2 skipped and 9 integration tests deselected |
| Renderer validate/render/default dry-run | Exit 0; descriptor remains non-deploying and vehicle-002 only |
| Actual local `--check-cli` | Exit 1, expected: Kanto unavailable; not a runtime pass |
| Relative Markdown links / shell syntax | 14 links resolve; 9 Bash blocks parse without execution |
| JSON and whitespace | Kanto descriptor/example JSON valid; `git diff --check` passed |

Durable command/exits, source-file SHA-256 values and logs:
[preparation manifest](kanto-preparation-20261115T041414Z/commands.json),
[app test log](kanto-preparation-20261115T041414Z/01.log),
[broader regression summary](kanto-preparation-20261115T041414Z/python-regression.log).
The manifest records baseline plus dirty preparation state, rather than claiming
that uncommitted changes were tested at a published commit SHA. The restricted
sandbox app run stalled in a selector and was interrupted; the complete rerun
with local socket access passed. Live MQTT publisher integration was skipped
because `V1_MQTT_TEST_HOST` was unset, and the native SDK check was skipped because
`velocitas_sdk` was unavailable. No live service test was substituted with a mock
and represented as runtime evidence. Java/frontend code was not changed or
retested for this preparation-only change.

Next session **cannot immediately run the pilot**: obtain a reviewed compatible
Kanto installation/daemon on the identified Linux host (or identify an authorized
Linux/Kanto host), legitimate immutable image access, Mosquitto capture CLI,
verified clock synchronization, approved endpoint topology and ready real Ditto
with credentials/single ingress. Then execute the gated procedure and durably
track the manifest, source/image SHAs, command/exits, lifecycle/status logs,
MQTT JSONL, before/intermediate/after twin snapshots and correlation results.
V1-09 and release acceptance remain open until that evidence passes review.
