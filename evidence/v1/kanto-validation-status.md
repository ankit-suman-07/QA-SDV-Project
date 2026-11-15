# Phase V1 Kanto validation preparation

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
