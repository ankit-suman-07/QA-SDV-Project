# Same-device Linux runtime continuation

See [current evidence/status](../../evidence/v1/kanto-validation-status.md).
No command below authorizes acceptance without real Kanto observations. Run from
the reviewed repository root. Do not run the complete acceptance harness during
this preparation task: it includes faults, outages and a different deployment.
Execute gated commands one at a time and stop on unexpected nonzero exits.
Initialize the required variables in every observer terminal; do not rely on
variables exported in another terminal.


## Verified live checkpoint — 2026-11-15 14:22 UTC

[V1-09 same-device pilot passed](../../evidence/v1/kanto-live-20261115T142159Z/README.md)
with operator-assisted privileged lifecycle execution. The agent terminal's sudo
remained password-gated; the operator ran the reviewed observer in their own
terminal. Actual namespace image digest, effective descriptor, launch and managed
stop/start were verified. A fresh source newer than all three restart boundaries
matched exact MQTT/real-Ditto identity and complete properties; vehicle-001 stayed
healthy across sampled observations. This does not establish full V1 acceptance,
remote-LAN behavior or automatic crash restart.

Both stop states have application exit_code=1 and retained logs reproduce the
historical event-loop shutdown RuntimeError. Preserve that follow-up gap; do not
label cleanup a clean application exit. Kanto reports running=false, pid=-1,
manually_stopped=true. Docker app-002 remains stopped. The Kanto container is
retained for inspection, so the original create-only observer must not be rerun
against its existing name; inspect first and use the reviewed existing-container
lifecycle sequence if another trial is authorized. Do not replace it implicitly.

## Historical recovery checkpoint — 2026-11-15 14:14 UTC

[Recovery evidence](../../evidence/v1/kanto-recovery-20261115T141500Z/README.md)
supersedes old temporary paths. Binaries are installed in
`/opt/qa-sdv-v1-kanto/bin`; dedicated daemon is active. Persistent runtime is
`$HOME/.local/share/qa-sdv-v1/runtime`. Do not reinstall, reimport, recreate the
namespace or restart the daemon just to continue. The operator reports imported
image/index `efad7228ebf00f092d43ec7242e2d60bdd56866d2f94f0afc3c8c5af9e6ac4a6`;
privileged namespace/image inspection and actual Kanto resolution remain pending.

The daemon initially crashed with HOME/XDG_CONFIG_HOME unset. Its inspected unit
now has `HOME=/var/lib/qa-sdv-v1-kanto` and
`XDG_CONFIG_HOME=/var/lib/qa-sdv-v1-kanto/config`; retain both on future starts.
Automatic deployment and remote Things integration are disabled. The corrected
systemd-run example below records these settings; it is not an instruction to
restart the running service.

Restore the documented observer/test environment without using system Python
3.14 (grpcio-tools 1.68.0 falls back to a source build there):

```bash
export RUNTIME="$HOME/.local/share/qa-sdv-v1/runtime"
uv python install 3.12.16
# Only if this environment is absent:
uv venv --python 3.12.16 "$RUNTIME/venv-3.12"
uv pip install --python "$RUNTIME/venv-3.12/bin/python" -r requirements-test.txt
export PYTHON="$RUNTIME/venv-3.12/bin/python"
```

One recovered ingress uses this interpreter and repository checkout. Its process
identity and log live at `runtime/ingress-identity.json` and `runtime/ingress.log`
under the persistent runtime parent. Inspect the identity and processes before
starting another; do not print process environments. Both existing Things were
read, never provisioned or replaced. Credentials were read in memory from the
restored official source's documented local-sample authentication and not saved.
Restored Compose is `runtime/ditto-restored.json`; it reuses the existing Ditto
network. Preserve MongoDB volumes and the unused `docker_default` network.

This session's `sudo -n true` requires authentication. Direct unprivileged Kanto
list times out on the protected socket, which is not evidence the daemon is down.
Ask the operator to run the exact privileged list command below; do not loosen
socket permissions, request passwords, or assume their terminal's sudo timestamp
applies to an agent terminal. Launch/managed restart and post-restart event
correlation remain blocked until authorized privileged execution is available.
The old optional `/tmp/qa-v1-jdk` backend command is historical and unavailable;
no backend is needed for this bounded Kanto pilot.

## Current non-deploying checks

```bash
set -euo pipefail
export PYTHON=${HOME}/.local/share/qa-sdv-v1/runtime/venv-3.12/bin/python
export V1_KANTO_APP_IMAGE=docker.io/library/qa-v1-kanto-app:sha-92f3fc14a15ae7bd1aa6663bdedccb99a6c69446
export PATH=/opt/qa-sdv-v1-kanto/bin:$PATH
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config velocitas-app/kanto/pilot-config.local-linux.json --check-cli
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml config --quiet
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml ps -a
timedatectl show -p NTPSynchronized -p NTP
chronyc tracking
```

Compose must support `!override` and `!reset` (the local version is recorded).
Default config must exclude app-002 and remove both inherited app build blocks.
Only if prerequisites have stopped, bring them back without enabling app-002:

```bash
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml up -d --no-build mqtt kuksa-001 kuksa-002 provider-001 provider-002 app-001
docker compose -p qa-v1-kanto-prereq-ditto -f ${HOME}/.local/share/qa-sdv-v1/runtime/ditto-restored.json up -d
```

Do not use `--build` for the app reference. If rebuilding is necessary:

```bash
docker build --platform linux/amd64 --label org.opencontainers.image.source=https://github.com/ankit-suman-07/QA-SDV-Project --label org.opencontainers.image.revision=92f3fc14a15ae7bd1aa6663bdedccb99a6c69446 --file velocitas-app/app/Dockerfile --tag "$V1_KANTO_APP_IMAGE" velocitas-app
docker image inspect "$V1_KANTO_APP_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
docker save -o ${HOME}/.local/share/qa-sdv-v1/runtime/kanto-app-92f3fc1.tar "$V1_KANTO_APP_IMAGE"
sha256sum ${HOME}/.local/share/qa-sdv-v1/runtime/kanto-app-92f3fc1.tar
```

Only label a build with that SHA after confirming the application build inputs
match it; otherwise use the actual source revision and update config/evidence.
Record new hashes; do not assume rebuilds preserve image/index identity.

## Optional backend read continuation

Optional backend read continuation (not required to launch Kanto itself): load
the [secret-free two-vehicle environment](backend.local-linux.env.example) and
legitimate `SDV_V1_DITTO_USERNAME/PASSWORD` securely before starting the current
Java 21 jar. The prior bounded smoke process has been stopped. Keep fleet writing
disabled for preparation, and never start a second backend fleet materializer.
This file restricts the backend's broader default vehicle list to exactly two.

```bash
set -a
. velocitas-app/kanto/backend.local-linux.env.example
set +a
/tmp/qa-v1-jdk/bin/java -Xmx256m -jar backend/target/backend-0.0.1-SNAPSHOT.jar
```

Use its own terminal and Ctrl-C for cleanup. Do not log credentials or enable
Actuator environment dumps. The real read smoke is recorded in current evidence;
this is not dashboard or fleet-materialization acceptance.

## Administrator installation — historical procedure; inspect restored state first

Use the official [Kanto 1.0.0 release](https://github.com/eclipse-kanto/kanto/releases/tag/v1.0.0).
The verified archive already exists in `${HOME}/.local/share/qa-sdv-v1/runtime/downloads`; extracted
binaries run on this host. No package scripts were run. Do not install the full
suite blindly: it includes unrelated connectors/services. Secure sudo operator
authentication is required; never provide a password to this PR or chat.

Inspect existing paths, namespace and unit before additive installation. Stop if
any already belongs to another workload. The runtime namespace, daemon socket,
state and log paths below are dedicated to this pilot. Containerd configuration,
Docker services, shared namespaces and socket permissions must stay intact.

```bash
systemctl status qa-sdv-v1-kanto --no-pager
sudo ctr --address /run/containerd/containerd.sock namespaces list
sha256sum ${HOME}/.local/share/qa-sdv-v1/runtime/downloads/kanto_1.0.0_linux_x86_64.tar.gz
sudo install -d -m 0755 /opt/qa-sdv-v1-kanto/bin /var/lib/qa-sdv-v1-kanto /run/qa-sdv-v1-kanto /var/log/qa-sdv-v1-kanto
sudo install -m 0755 ${HOME}/.local/share/qa-sdv-v1/runtime/kanto-1.0.0/container-management/kanto-cm /opt/qa-sdv-v1-kanto/bin/kanto-cm
sudo install -m 0755 ${HOME}/.local/share/qa-sdv-v1/runtime/kanto-1.0.0/container-management/container-management /opt/qa-sdv-v1-kanto/bin/container-management
```

Verify the archive against the recorded official checksum before installation;
inspect any existing installed binaries rather than overwriting them. For a new
namespace only, import the recorded export. `ctr` namespace is not Docker's image
store, and its import is not yet proof that Kanto resolves the image:

```bash
sudo ctr --address /run/containerd/containerd.sock namespaces create qa-sdv-v1-kanto
sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto images import --platform linux/amd64 ${HOME}/.local/share/qa-sdv-v1/runtime/kanto-app-92f3fc1.tar
sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto images list
```

Kanto 1.0.0 with this host's containerd 2.4.2 is **not yet verified compatible**.
The following starts only a dedicated management daemon, not app-002. Flags were
confirmed against the downloaded binary's help. Disable its unrelated remote
Things integration and default bridge; app descriptor uses host networking.

```bash
sudo systemd-run --unit=qa-sdv-v1-kanto --collect --setenv=HOME=/var/lib/qa-sdv-v1-kanto --setenv=XDG_CONFIG_HOME=/var/lib/qa-sdv-v1-kanto/config /opt/qa-sdv-v1-kanto/bin/container-management --ccl-ap /run/containerd/containerd.sock --ccl-default-ns qa-sdv-v1-kanto --grpc-serv-ap /run/qa-sdv-v1-kanto/container-management.sock --cm-home-dir /var/lib/qa-sdv-v1-kanto --cm-exec-root-dir /run/qa-sdv-v1-kanto --ccl-home-dir /var/lib/qa-sdv-v1-kanto --ccl-exec-root-dir /run/qa-sdv-v1-kanto --deployment-home-dir /var/lib/qa-sdv-v1-kanto --deployment-enable=false --things-home-dir /var/lib/qa-sdv-v1-kanto --net-home-dir /var/lib/qa-sdv-v1-kanto --net-exec-root-dir /run/qa-sdv-v1-kanto --net-type host --net-tbr-disable --things-enable=false --log-file /var/log/qa-sdv-v1-kanto/container-management.log
export KANTO_CLI=/opt/qa-sdv-v1-kanto/bin/kanto-cm
export KANTO_HOST=/run/qa-sdv-v1-kanto/container-management.sock
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 list
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 sysinfo
sudo journalctl -u qa-sdv-v1-kanto --no-pager -n 60
```

Any daemon/API/runtime/import failure is BLOCKED. Resolve it without downgrading
or resetting shared runtimes. Readiness alone does not verify container lifecycle
compatibility. Inspect Kanto image resolution during the actual pilot; if it tries
an unavailable registry despite import, retain that failure and resolve the cache
or approved isolated registry configuration, never claim the import succeeded as
an application launch.

## Live pilot commands — require current readiness and privileged access

Require current READY statuses, synchronized clock, real Ditto access, one
ingress, no replay publisher and app-001 healthy. Set a new evidence directory
without overwriting prior runs. Load legitimate local Ditto credentials securely
into `SDV_DITTO_USERNAME/PASSWORD`, never command arguments or tracked files.
The already running ingress needs no replacement; inspect it first. If it has
stopped, inspect its old PID/start identity, load credentials and start **one**:

```bash
export SDV_DITTO_BASE_URL=http://127.0.0.1:18080
export SDV_MQTT_HOST=127.0.0.1
export SDV_MQTT_PORT=18883
export SDV_MQTT_CLIENT_ID=qa-v1-kanto-prereq-ingress
"$PYTHON" -m ditto.v1 read all
# Run in its own terminal ONLY if the recorded ingress is confirmed stopped:
"$PYTHON" -m ditto.v1 run
```

Record Docker app-002's pre-pilot state. It was already stopped by this preparation;
do not restore it to running merely because its container exists.

```bash
export RUN_DIR="evidence/v1/kanto-validation-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 0755 "$RUN_DIR"
git rev-parse HEAD > "$RUN_DIR/source-sha.txt"
git status --short > "$RUN_DIR/dirty-state.txt"
docker inspect qa-v1-kanto-prereq-edge-app-002-1 --format '{{.State.Status}}'
docker stop --time 30 qa-v1-kanto-prereq-edge-app-002-1
docker inspect qa-v1-kanto-prereq-edge-app-002-1 --format '{{.State.Status}}'
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 list
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config velocitas-app/kanto/pilot-config.local-linux.json --mode render > "$RUN_DIR/descriptor.json"
```

Require Docker app-002 exited, with no other publisher or Kanto duplicate. For
an absent Kanto name only, create then inspect (never replace an existing one):

```bash
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 30 create --file "$RUN_DIR/descriptor.json"
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 get --name autonomoushealthapp-vehicle-002
```

In an observer terminal, start the bounded capture **before** lifecycle changes:

```bash
docker run --rm --network host --read-only --cap-drop ALL --security-opt no-new-privileges -e TZ=UTC --entrypoint mosquitto_sub eclipse-mosquitto@sha256:75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98 -h 127.0.0.1 -p 18883 -q 1 -V mqttv5 --retain-as-published -t sdv/vehicle-001/health -t sdv/vehicle-002/health -F '%j' -W 180 > "$RUN_DIR/mqtt.jsonl" 2> "$RUN_DIR/mqtt.stderr"
```

Capture exits/errors must be retained; exit 27 indicates the observation deadline,
not a passed pilot. Start the twin timeline observer from the original pilot
guide/status before stop/start. Verify subscription receipt from vehicle-001,
then use these lifecycle commands, recording each exit/status and return time:

```bash
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 30 start --name autonomoushealthapp-vehicle-002
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 get --name autonomoushealthapp-vehicle-002 > "$RUN_DIR/kanto-initial-start.json"
"$PYTHON" -m ditto.v1 read all > "$RUN_DIR/before-restart-twins.json"
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 30 stop --name autonomoushealthapp-vehicle-002
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 get --name autonomoushealthapp-vehicle-002
"$PYTHON" -c 'import datetime,json,time; print(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"monotonicNs":time.monotonic_ns()}))' > "$RUN_DIR/start-request.json"
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 30 start --name autonomoushealthapp-vehicle-002
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 get --name autonomoushealthapp-vehicle-002 > "$RUN_DIR/kanto-restarted.json"
```

Wait for a real healthy event/twin match before saving the pre-restart snapshot.
Confirm stopped before recording the second start boundary. Poll actual Ditto
within a recorded bounded deadline, keeping intermediate vehicle-001 snapshots.
Apply all [event correlation/isolation requirements](../../evidence/v1/kanto-validation-status.md#required-event-correlation-and-isolation):
new event ID; source strictly newer than old source and start request; receipt
after start; non-retained correct topic/schema/identity; source freshness/clock
assumptions; **exact** event ID/source/properties in real Ditto; no intermediate
vehicle-001 fault. Do not accept the old prepared twin or a different later event
as proof. A managed stop/start is not crash auto-restart verification.

For the actual pilot, also require source time **strictly after the restarted
application's Kanto-reported `state.started_at`**, not just the start request.
The pinned v1.0.0 CLI `get` emits the container JSON including `state.running`,
`state.pid` and `state.started_at`. Preserve both initial and restarted JSON;
require running state, a parseable timezone-aware start timestamp, and a later
restart timestamp than the initial launch. Record PID and container ID as
provenance, but do not use PID alone as restart proof. Reject missing/invalid
runtime start time rather than substituting the request or observation time.
Use a fresh event different from the pre-restart event and newer than **all**
three boundaries: pre-restart source, start request, and runtime-reported restart.
Continue capturing through stop/start so in-flight old events cannot satisfy this
check. Keep both lifecycle command exits and return times. UTC comparisons use
this host's synchronized clock; monotonic observer time measures completion.

## Cleanup and restoration

On failure/interruption stop only the named Kanto pilot and confirm stopped
before considering any Docker app-002 start:

```bash
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 30 stop --name autonomoushealthapp-vehicle-002
sudo "$KANTO_CLI" --host "$KANTO_HOST" --timeout 5 get --name autonomoushealthapp-vehicle-002
```

Leave Docker app-002 stopped when restoring this preparation state. Only if it was
running at the start of a future pilot, after confirmed Kanto stop, use:

```bash
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml --profile docker-app-002 start app-002
```

If Kanto cannot be confirmed stopped, do not start Docker app-002. Stop only owned
observer processes; preserve failed captures and evidence. No test scenarios or
outages were introduced in preparation. To stop the entire newly owned preparation
environment, first verify the recorded ingress PID/command/start identity and
terminate that process only. Then:

```bash
"$PYTHON" - <<'PY'
import json, os, signal
from pathlib import Path
record = json.loads((Path.home() / '.local/share/qa-sdv-v1/runtime/ingress-identity.json').read_text())
proc = Path('/proc') / str(record['pid'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == record['bootId']
assert proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == record['startTicks']
assert proc.joinpath('cmdline').read_bytes().decode().strip('\0').split('\0') == record['argv']
os.kill(record['pid'], signal.SIGINT)
PY
```

Confirm that exact process exited before proceeding. If its record is missing or
identity differs, inspect ownership manually; do not signal an unknown PID.
For a newly started ingress in its own terminal, use Ctrl-C in that owned terminal.
Then stop only the two test-owned projects:

```bash
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml down
docker compose -p qa-v1-kanto-prereq-ditto -f ${HOME}/.local/share/qa-sdv-v1/runtime/ditto-restored.json down
```

These commands omit volume deletion. Preserve the test-owned stopped app-002
container if it is outside the default profile config; if necessary stop it by
its exact recorded name. Do not use `--remove-orphans` or remove unknown services.
Only after the pilot container is confirmed stopped and no Kanto workload depends
on it, an operator may stop the dedicated `qa-sdv-v1-kanto` transient service.
Do not stop shared Docker/containerd, delete shared namespaces/policies/Things,
clear retained messages, or reset volumes. Initial state was no Docker containers;
the next session deliberately starts from the documented running prerequisites.


## Interactive Phase V1 demo launcher

From a reviewed main-based checkout:

```bash
bash scripts/run-v1-demo.sh
```

First copy `scripts/v1-demo.example.json` to
`$HOME/.local/share/qa-sdv-v1/runtime/demo.json` (or pass `--config PATH`) and review
its endpoints/container names/artifact paths. The example matches the restored
same-device prerequisite deployment; it is not a new Compose deployment. Reuse an
already provisioned real Ditto, both Things/policies, fleet Thing/policy, sole
individual ingress, MQTT, both KUKSA/providers and app001. Keep the configured Docker
app002 container present (running or stopped). No image rebuilds, downloads, package
installation, provisioning, twin reset or volume deletion occur in this launcher.
If those prerequisites are missing, follow this guide's explicit preparation and
`scripts/v1_fleet_provision.py` instructions with authorized subjects; never invent
subjects or replace existing policies. Only one backend may write this fleet Thing.

Use the persistent Python3.12 environment with documented requirements-test.txt
(including paho-mqtt) and the existing prepared Java21/backend jar. Set `backendJar`
to an already built, verified artifact (the example reuses the merged-main validation
worktree). `imageInfo` points to the verified image/source/index metadata; its image
must already be imported in the dedicated Kanto namespace. The launcher checks image
identity and current application-source compatibility; it does not import/build
images automatically. Missing-image output supplies the exact local import command.
The dedicated daemon must use its documented HOME/XDG_CONFIG_HOME correction.

Load authorized Ditto credentials through `SDV_V1_DITTO_USERNAME` and
`SDV_V1_DITTO_PASSWORD` in your private terminal environment, or use the launcher's
hidden terminal prompts. Do not put credentials in JSON, command arguments, shell
history or recordings; never enable shell tracing. The documented official local
sample authentication may be used for this prepared local demo. Production subject/
TLS separation remains an approval decision. Normal interactive `sudo -v` is used
for Kanto, followed by bounded `sudo -n` operations; no socket/sudo permissions change.

The launcher reuses compatible services and may start only its packaged backend and
static dashboard on free configured loopback ports. An occupied incompatible endpoint
fails readiness and is never displaced. Frontend origins must match existing backend
CORS (default `http://localhost:3000`). It opens the dashboard when desktop support
exists, otherwise prints the URL. A read-only preliminary check is available with
`bash scripts/run-v1-demo.sh --check`; it intentionally does not start observers,
authenticate sudo, start services or claim complete integration/publisher readiness.

Press Enter for healthy vehicles, backend A3 inject, observed002 fault with001
isolation, A3 clear/recovery, and managed Kanto stop/start. When Docker002 is running,
it is stopped and verified absent before a uniquely named Kanto002 starts. If Docker002
was initially stopped, the unique Kanto pilot supplies002 from preparation onward.
Other/duplicate publishers or active prior scenarios cause refusal. The restart must
exit0 and produce a different live QoS1/non-retained event with source time after the
previous source, start request and runtime-reported start; MQTT, real twin, individual
API and fleet observations must agree. ACK timing is separate from polled completion.

A compact status table appears at startup, readiness and each step (also on failure):
RUNNING means process/TCP evidence only; READY means the indicated real read/subscription
check passed; PUBLISHING requires a fresh validated MQTT observation; STALE denotes
aged source data; FAILED means the required check failed/unavailable. In read-only
mode Kanto remains unverified, shown FAILED with that limitation. A dashboard HTTP
check proves its shell is served; inspect the displayed live state during narration.
KUKSA TCP alone remains RUNNING, not integrated READY. Detailed secret-redacted logs,
commands/exits, action IDs, snapshots, source/image/artifact identities and status rows
are saved under root `evidence/v1/demo-<UTC timestamp>/`. Show existing spec/skill-use/
CI evidence afterward; do not regenerate it. No full acceptance, remote LAN or crash
auto-restart claim is made.

Choose N at completion to stop owned observers/backend/dashboard/Kanto and restore
Docker002 **only if this run stopped it and Kanto is confirmed stopped**. Initially
stopped002 stays stopped. Choose Y to keep services running under this terminal's
supervision; Enter or Ctrl+C then performs restoration. Keep the terminal open in
that mode so redacted log readers remain alive. Existing shared services, policies,
twins, volumes and historical pilots are preserved. Created pilots remain stopped
for inspection; no container/volume deletion is attempted.

On failure/Ctrl+C, review `result.json`, `failure.json` and `cleanup.json` in that run's
evidence directory. It attempts to clear its injected scenario and stops only its
owned resources. If Kanto cleanup is unverified, **do not start Docker002**: inspect
with the documented CLI `get --name <kantoName from cleanup.json>` and perform a normal
managed stop first. Correct the recorded missing prerequisite/conflict, then rerun;
never reset shared state to manufacture a pass. Do not call an incomplete rehearsal
successful. Submission video recording is outside this launcher task.
