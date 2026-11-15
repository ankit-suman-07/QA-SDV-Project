# Same-device Linux runtime continuation (preparation only)

See [current evidence/status](../../evidence/v1/kanto-validation-status.md).
No command below authorizes acceptance without real Kanto observations. Run from
the reviewed repository root. Do not run the complete acceptance harness during
this preparation task: it includes faults, outages and a different deployment.
Execute gated commands one at a time and stop on unexpected nonzero exits.
Initialize the required variables in every observer terminal; do not rely on
variables exported in another terminal.

## Current non-deploying checks

```bash
set -euo pipefail
export PYTHON=/tmp/qa-v1-env/bin/python
export V1_KANTO_APP_IMAGE=docker.io/library/qa-v1-kanto-app:sha-92f3fc14a15ae7bd1aa6663bdedccb99a6c69446
export PATH=/tmp/qa-v1-runtime/kanto-1.0.0/container-management:$PATH
"$PYTHON" velocitas-app/kanto/prepare_v1_pilot.py --config velocitas-app/kanto/pilot-config.local-linux.json --check-cli
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml config --quiet
docker compose -p qa-v1-kanto-prereq-edge -f /tmp/qa-v1-runtime/edge.json ps -a
timedatectl show -p NTPSynchronized -p NTP
chronyc tracking
```

Compose must support `!override` and `!reset` (the local version is recorded).
Default config must exclude app-002 and remove both inherited app build blocks.
Only if prerequisites have stopped, bring them back without enabling app-002:

```bash
docker compose -p qa-v1-kanto-prereq-edge -f vehicle-simulator/docker-compose.v1.yml -f velocitas-app/kanto/compose.prerequisites.yml up -d --no-build mqtt kuksa-001 kuksa-002 provider-001 provider-002 app-001
docker compose -p qa-v1-kanto-prereq-ditto -f /tmp/qa-v1-runtime/ditto.json up -d
```

Do not use `--build` for the app reference. If rebuilding is necessary:

```bash
docker build --platform linux/amd64 --label org.opencontainers.image.source=https://github.com/ankit-suman-07/QA-SDV-Project --label org.opencontainers.image.revision=92f3fc14a15ae7bd1aa6663bdedccb99a6c69446 --file velocitas-app/app/Dockerfile --tag "$V1_KANTO_APP_IMAGE" velocitas-app
docker image inspect "$V1_KANTO_APP_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
docker save -o /tmp/qa-v1-runtime/kanto-app-92f3fc1.tar "$V1_KANTO_APP_IMAGE"
sha256sum /tmp/qa-v1-runtime/kanto-app-92f3fc1.tar
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

## Administrator gate — BLOCKED, not executed

Use the official [Kanto 1.0.0 release](https://github.com/eclipse-kanto/kanto/releases/tag/v1.0.0).
The verified archive already exists in `/tmp/qa-v1-runtime/downloads`; extracted
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
sha256sum /tmp/qa-v1-runtime/downloads/kanto_1.0.0_linux_x86_64.tar.gz
sudo install -d -m 0755 /opt/qa-sdv-v1-kanto/bin /var/lib/qa-sdv-v1-kanto /run/qa-sdv-v1-kanto /var/log/qa-sdv-v1-kanto
sudo install -m 0755 /tmp/qa-v1-runtime/kanto-1.0.0/container-management/kanto-cm /opt/qa-sdv-v1-kanto/bin/kanto-cm
sudo install -m 0755 /tmp/qa-v1-runtime/kanto-1.0.0/container-management/container-management /opt/qa-sdv-v1-kanto/bin/container-management
```

Verify the archive against the recorded official checksum before installation;
inspect any existing installed binaries rather than overwriting them. For a new
namespace only, import the recorded export. `ctr` namespace is not Docker's image
store, and its import is not yet proof that Kanto resolves the image:

```bash
sudo ctr --address /run/containerd/containerd.sock namespaces create qa-sdv-v1-kanto
sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto images import --platform linux/amd64 /tmp/qa-v1-runtime/kanto-app-92f3fc1.tar
sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto images list
```

Kanto 1.0.0 with this host's containerd 2.4.2 is **not yet verified compatible**.
The following starts only a dedicated management daemon, not app-002. Flags were
confirmed against the downloaded binary's help. Disable its unrelated remote
Things integration and default bridge; app descriptor uses host networking.

```bash
sudo systemd-run --unit=qa-sdv-v1-kanto --collect /opt/qa-sdv-v1-kanto/bin/container-management --ccl-ap /run/containerd/containerd.sock --ccl-default-ns qa-sdv-v1-kanto --grpc-serv-ap /run/qa-sdv-v1-kanto/container-management.sock --cm-home-dir /var/lib/qa-sdv-v1-kanto --cm-exec-root-dir /run/qa-sdv-v1-kanto --ccl-home-dir /var/lib/qa-sdv-v1-kanto --ccl-exec-root-dir /run/qa-sdv-v1-kanto --deployment-home-dir /var/lib/qa-sdv-v1-kanto --things-home-dir /var/lib/qa-sdv-v1-kanto --net-home-dir /var/lib/qa-sdv-v1-kanto --net-exec-root-dir /run/qa-sdv-v1-kanto --net-type host --net-tbr-disable --things-enable=false --log-file /var/log/qa-sdv-v1-kanto/container-management.log
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

## Next-session pilot commands — do not run in preparation

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
record = json.loads(Path('/tmp/qa-v1-runtime/ingress-identity.json').read_text())
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
docker compose -p qa-v1-kanto-prereq-edge -f /tmp/qa-v1-runtime/edge.json down
docker compose -p qa-v1-kanto-prereq-ditto -f /tmp/qa-v1-runtime/ditto.json down
```

These commands omit volume deletion. Preserve the test-owned stopped app-002
container if it is outside the default profile config; if necessary stop it by
its exact recorded name. Do not use `--remove-orphans` or remove unknown services.
Only after the pilot container is confirmed stopped and no Kanto workload depends
on it, an operator may stop the dedicated `qa-sdv-v1-kanto` transient service.
Do not stop shared Docker/containerd, delete shared namespaces/policies/Things,
clear retained messages, or reset volumes. Initial state was no Docker containers;
the next session deliberately starts from the documented running prerequisites.
