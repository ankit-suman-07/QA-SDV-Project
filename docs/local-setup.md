# Local setup and run guide

This guide describes the merged Phase V1 implementation assessed at `e406e36`.
Start at [SOURCE-OF-TRUTH](SOURCE-OF-TRUTH.md); the [scope](08-project-scope-and-acceptance.md),
[task distribution](10-detailed-task-distribution.md), [architecture](09-architecture-diagrams.md)
and [contracts](v1-interface-contracts.md) distinguish requirements from recorded results.
V1 has exactly **two synthetic vehicles**. CARLA and broader distributed diagnostics belong to V2.

**Command convention:** fenced `bash` and `powershell` blocks contain commands for the
named shell. Fenced `text` blocks show expected output, not commands. Never type a
credential prompt as a command. Unless a block says otherwise, work at the repository root.

## 1. Choose a run mode

| Mode | What it demonstrates | Platform and evidence boundary |
|---|---|---|
| Source/unit development | Java/Python/frontend behavior, contract fixtures and substitutes. | Windows PowerShell, Linux Bash and macOS Bash instructions below. Native Windows commands are statically reviewed, not runtime-certified. Mocks prove no live integration. |
| Core two-vehicle Docker workflow | Two provider/KUKSA/app pipelines → MQTT ingress → real individual Ditto twins → Spring/fleet/dashboard; backend fault/clear. | Linux is the full-stack recorded host. Use WSL2/Linux containers on Windows. macOS has historical arm64 edge evidence, not a fresh full-stack check of this guide. Check all image architectures. |
| Interactive V1 demo | Narrated fault/clear and Kanto managed restart, component tables and dated evidence. | **Prepared Linux host only** in the current launcher. It is not a cross-platform installer. |
| Kanto lifecycle pilot | Exclusive app-002 managed stop/start and fresh MQTT/Ditto correlation. | Recorded Linux x86_64, Kanto 1.0.0, dedicated containerd namespace/socket. No native Windows/macOS or Docker Desktop VM/WSL Kanto claim. |
| Legacy MVP | Separate single-vehicle MQTT demo, or older iteration-3 bridge/backend workflow. | Historical workflows; see section 13. They are not the two-vehicle V1 path. |

Core containers can run under Docker Desktop without making Kanto available on the host.
For a Windows/macOS demonstration of Kanto, use a separately prepared supported Linux
machine/VM as the runtime, and its browser/desktop as appropriate. A VM's host integration
and remote-LAN endpoints are separate, unverified setup work; do not label WSL/Desktop
containers as the verified Kanto device.

## 2. Requirements and installation references

| Requirement | Repository basis / guidance |
|---|---|
| Git | Clone and record revisions. [Official downloads](https://git-scm.com/downloads/). |
| JDK **21** | `backend/pom.xml` and CI; Maven wrapper is included (`mvnw`, `mvnw.cmd`). Set `JAVA_HOME` to a JDK, not a JRE. [Temurin 21](https://adoptium.net/temurin/releases/?version=21) or another compatible JDK21. |
| Host Python **3.12** | CI and recorded verification use 3.12 (recorded 3.12.16). Do not use the host's arbitrary newest Python for the pinned gRPC toolchain. [Python releases](https://www.python.org/downloads/) or [uv](https://docs.astral.sh/uv/getting-started/installation/) with managed 3.12. |
| Node **22**, npm | Recorded frontend checks use 22.23.5; package.json uses Node's test runner and an experimental isolation flag. No `engines` minimum or browser bundler is declared. Use tested Node22, not an assumed older version. [Select Node22](https://nodejs.org/en/download). Static frontend serving itself does not require Node. |
| Docker + Compose plugin | Linux containers, BuildKit/buildx for the app Dockerfile, Compose `config --format json`, profiles, `!reset` and `!override`. Use current Compose **2.24.4 or later**, including newer plugin versions; `!override` needs that minimum. Legacy `docker-compose` v1 is not the documented route. [Merge-tag reference](https://docs.docker.com/reference/compose-file/merge/). |
| Shell/browser | Bash for the shared orchestration; PowerShell for native Windows development. A current browser with JavaScript modules/fetch. Optional Mosquitto CLI for live capture; no CLI client is needed for unit tests. |
| Linux Kanto only | Ordinary interactive sudo, containerd, Kanto/container-management 1.0.0, cgroups/networking and the dedicated daemon configuration. These are additional to Docker. See section 11. |

No benchmarked project-wide CPU/RAM/disk minimum is specified. As a **planning estimate,
not a tested minimum**, budget a 16 GB host, about 8 GB available to Docker, 4 CPUs and
25 GB free disk for JVM services, MongoDB, images and builds; workload/platform may need
more. Docker Desktop's vendor minimum (for example 4 GB RAM on Mac) is not a promise
that the complete V1 stack fits. See the platform vendor's current requirements.

### Windows: PowerShell versus WSL2

For source inspection/unit work, install Git, JDK21, Node22 and Python3.12/uv for Windows.
The explicit PowerShell commands in section 3 do not require venv activation or changing
execution policy. `scripts/start-demo.ps1` is a **legacy** launcher, not a V1 equivalent.

For core Docker orchestration, use the [Microsoft WSL installation procedure](https://learn.microsoft.com/en-us/windows/wsl/install)
and [Docker Desktop Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/).
Run in **administrator PowerShell** if WSL is not installed:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
wsl --list --verbose
```

Restart if requested; complete Ubuntu's first-login setup. If the verbose list shows
version1, convert it in PowerShell with `wsl --set-version Ubuntu-24.04 2`. Open the
Linux shell with `wsl -d Ubuntu-24.04`. Install/start Docker Desktop in Linux-container mode and enable
its WSL2 engine and **Settings → Resources → WSL Integration → your Ubuntu distribution**.
Follow [Docker's integration guide](https://docs.docker.com/desktop/features/wsl/);
do not install a competing Docker Engine inside that same Docker-Desktop-managed distro.
Open Ubuntu/WSL, then use the **Bash** instructions below. Check `docker version` there.
Keep the Linux clone/environment under the WSL home directory, not a Windows venv
or a shared `/mnt/c` checkout. Windows-native and WSL interpreters/paths are different.
Windows ARM and the full WSL2 V1 workflow were not exercised for this documentation.

### Linux

Use the [official Docker Engine instructions for your distro](https://docs.docker.com/engine/install/)
and install the Compose/buildx plugins. Do not mix Ubuntu package commands into Fedora.
Examples for basic tools/JDK **only** (run only on the matching distribution):

```bash
# Ubuntu 24.04 / compatible apt repositories:
sudo apt update
sudo apt install git curl ca-certificates openjdk-21-jdk python3.12 python3.12-venv
```

```bash
# Fedora, with Java21 packages available:
sudo dnf install git curl java-21-openjdk-devel
```

On Fedora and other hosts whose default Python is newer, use managed Python3.12
(section 3). Install Node22 from its official distribution or a reviewed version manager;
distro `nodejs` may select a different major. Select Java21 in your distro's alternatives
manager if another JDK is the default. In **Linux Bash**, derive that selected JDK's home:

```bash
export JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

Stop if this does not report Java21; deriving a path alone does not select a JDK version.

Run `docker version` using your authorized Docker context. Docker's [post-install guide](https://docs.docker.com/engine/install/linux-postinstall/)
explains ordinary sudo, rootless mode and the root-equivalent Docker group. Choose access
with your administrator; never make the Docker/Kanto socket world-writable or disable security.
The interactive launcher needs Docker access as your user and separately requests normal
sudo for Kanto. Rootless Docker alone does not establish Kanto/containerd compatibility.

### macOS: Intel and Apple Silicon

Install the [Docker Desktop build for your architecture](https://docs.docker.com/desktop/setup/install/mac-install/),
Git, a matching JDK21, Node22 and Python3.12/uv. Start Docker Desktop before Compose.
Set Java21 in Bash using the installed JDK:

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 21)"
export PATH="$JAVA_HOME/bin:$PATH"
```

The edge Dockerfile uses `$TARGETPLATFORM`, not a forced amd64 platform. E1 records
macOS arm64 edge publication; that does not certify every current upstream image,
Ditto/MongoDB, or the whole current stack on Apple Silicon. Before building, inspect
registry manifests for **your** CPU, including KUKSA0.7.0, the Velocitas Python v0.4
base, Python3.10-slim, Mosquitto2, Mongo7.0 and the Ditto3.8.4 services. Example:

```bash
docker buildx imagetools inspect ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0
docker buildx imagetools inspect ghcr.io/eclipse-velocitas/devcontainer-base-images/python:v0.4
```

These commands inspect remote manifests; they do not prove a runtime launch. If a required
platform is absent, stop and use a supported Linux host rather than silently forcing
amd64 emulation. Native macOS Kanto is not supported by this guide. Intel Mac full-stack
execution and Apple Silicon emulation were not tested here. Observe Mongo's CPU requirements.

## 3. Clone, persistent environment and development checks

First-time setup below downloads project dependencies/build tooling; the **demo launcher
itself never does so**. Preserve any existing clone/environment rather than replacing it.

### Bash: Linux, WSL2 or macOS

```bash
mkdir -p "$HOME/src"
cd "$HOME/src"
git -c core.autocrlf=input clone https://github.com/ankit-suman-07/QA-SDV-Project.git
cd QA-SDV-Project
export REPO="$(pwd -P)"
git rev-parse HEAD
git status --short
```

Choose persistent storage for your platform (run **one** block):

```bash
# Linux / WSL2:
export V1_RUNTIME="$HOME/.local/share/qa-sdv-v1/runtime"
```

```bash
# macOS core development:
export V1_RUNTIME="$HOME/Library/Application Support/qa-sdv-v1/runtime"
```

Install uv through its linked vendor instructions if needed; then, from the root:

```bash
mkdir -p "$V1_RUNTIME"
uv python install 3.12
test -x "$V1_RUNTIME/venv-3.12/bin/python" || uv venv --python 3.12 "$V1_RUNTIME/venv-3.12"
export PYTHON="$V1_RUNTIME/venv-3.12/bin/python"
uv pip install --python "$PYTHON" -r requirements-test.txt
mkdir -p uprotocol/generated
"$PYTHON" -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated uprotocol/proto/common.proto uprotocol/proto/health_status.proto uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto uprotocol/proto/vehicle_diagnostic.proto
```

Create a venv only if absent; for an existing venv, inspect its version and reuse it.
If using an installed Python3.12 instead of uv, `python3.12 -m venv` and that venv's
`python -m pip install -r requirements-test.txt` are equivalent preparation routes.
Container app dependencies are separate: the app image pins SDK0.15.7, KUKSA0.5.1 and
gRPC1.68.0; the host requirements include a different gRPC version. Do not replace
container requirements with the host test environment. Base provider/app images use Python3.10.

### Windows-native PowerShell: development only

Run in a normal **PowerShell** terminal with Git/uv/JDK21/Node22 installed:

```powershell
New-Item -ItemType Directory -Force "$HOME\src" | Out-Null
Set-Location "$HOME\src"
git clone https://github.com/ankit-suman-07/QA-SDV-Project.git
Set-Location QA-SDV-Project
$Repo = (Get-Location).Path
$V1Runtime = Join-Path $env:LOCALAPPDATA 'qa-sdv-v1\runtime'
New-Item -ItemType Directory -Force $V1Runtime | Out-Null
uv python install 3.12
$Python = Join-Path $V1Runtime 'venv-3.12\Scripts\python.exe'
if (-not (Test-Path $Python)) { uv venv --python 3.12 (Join-Path $V1Runtime 'venv-3.12') }
uv pip install --python $Python -r requirements-test.txt
New-Item -ItemType Directory -Force uprotocol/generated | Out-Null
& $Python -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated uprotocol/proto/common.proto uprotocol/proto/health_status.proto uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto uprotocol/proto/vehicle_diagnostic.proto
Push-Location backend
.\mvnw.cmd --batch-mode --no-transfer-progress clean verify
Pop-Location
& $Python -B -m pytest -q -ra -m 'not integration'
Push-Location frontend
npm.cmd test
Pop-Location
```

Do not paste later Bash exports/heredocs/functions into PowerShell. Use WSL2 for the
core workflow. Native test cases may involve sockets/subprocesses/platform tools;
inspect skips/failures rather than claiming parity with Ubuntu CI. Bash scripts and
Linux process cleanup are not certified by native Windows unit execution.

### Test selection and mocks

Bash component/regression commands, after dependency/Protobuf preparation:

```bash
java -version
"$PYTHON" --version
node --version
docker compose version
(cd backend && bash ./mvnw --batch-mode --no-transfer-progress clean verify)
"$PYTHON" -B -m pytest -q -ra -m 'not integration'
(cd frontend && npm test)
```

No `npm install` is needed by the current dependency-free frontend package. Java tests
use controlled dependencies/loopback servers, not a running real Ditto. Python's default
pytest marker excludes external integration tests; some SDK/MQTT cases require optional
runtime configuration. Tests and recorded skips must be distinguished from live proof.
For fast standard-library fixture development, see [independent development](v1-independent-development.md):

```bash
"$PYTHON" -B -m scripts.v1_dev.mqtt render --scenario cycle --anchor 2026-01-01T00:00:00Z | "$PYTHON" -B -m scripts.v1_dev.mqtt check --expect-cycle
"$PYTHON" -m scripts.v1_dev.http_mocks --help
```

The HTTP tools exercise **substitutes**. Optional `scripts/v1_dev/fleet_smoke.py`
also needs the packaged Java artifact and free ports; pass `--artifacts-dir` pointing
under your persistent runtime instead of relying on its temporary default. The mocks advertise `X-SDV-Mock: true`; never
substitute them silently for the following real run. Full fault/outage acceptance is
separate and deliberately mutating: [acceptance guide](../scripts/v1_acceptance/README.md).
Do not run it merely to install or check documentation.

## 4. Core deployment plan, addresses and collision checks

Sections 4–10 are **Bash** recipes for Linux, WSL2 and conditionally macOS. They are
statically reviewed onboarding commands, not a new claim of fresh runtime execution.
The historical full-stack Linux evidence is linked in section 15.

| Host endpoint in this guide | Container/service endpoint | Purpose |
|---|---|---|
| 127.0.0.1:18080 | nginx:80 → Ditto gateway | Authenticated Ditto API/UI |
| 127.0.0.1:18883 | mqtt:1883 | Local anonymous Mosquitto |
| 127.0.0.1:55556 / 55557 | kuksa-001/002:55555 | Dedicated signal brokers |
| 127.0.0.1:8091 / 8092 | provider-001/002:8090 | Provider health/scenario control |
| 127.0.0.1:8082 | Host Java process | Spring V1 individual/fleet/A3 APIs |
| localhost:3000 | Host static server | Dashboard (allowed backend CORS origin) |

Inside containers, `localhost` is that container; use Compose DNS names as the existing
edge YAML does. Host ingress/backend use published loopback ports. No service should use
Docker Desktop's internal VM address as a guessed Kanto/LAN endpoint. Windows browser
loopback forwarding from WSL2 depends on local WSL/network configuration; verify it.

Before creating anything, inspect `docker ps -a`, `docker compose ls`, running host
processes and ports. Linux: `ss -ltn`; macOS: `lsof -nP -iTCP -sTCP:LISTEN`; Windows
PowerShell: `Get-NetTCPConnection -State Listen` (inspect WSL ports inside WSL too).
Stop on unrelated occupants. Use an existing compatible deployment's actual project,
configuration and volume identities, or choose new free ports consistently; never
stop arbitrary workloads to free a port. The example project names are `qa-sdv-v1`
(edge) and `qa-sdv-v1-ditto` (new private Ditto). Reusing a name can target existing containers.

In each terminal, start at the root and re-establish `REPO`, `V1_RUNTIME` and `PYTHON`
from section 3. Credential exports and shell functions are local to that terminal. After choosing the
platform's `V1_RUNTIME`, initialize reusable **non-secret** session paths without cloning again:

```bash
export REPO="$(pwd -P)"
export PYTHON="$V1_RUNTIME/venv-3.12/bin/python"
export DITTO_SOURCE="$V1_RUNTIME/ditto-source"
export DITTO_DEPLOYMENT="$DITTO_SOURCE/deployment/docker"
```

Do not copy a venv or another developer's absolute runtime/evidence configuration.

## 5. First-time real Ditto setup (new deployment only)

There is no bundled all-platform Ditto installer/Compose stack. The verified harness
uses official Ditto **3.8.4**, revision `5dbb05e6294e5ac0103506102baff9eab755d180`.
The recipe below uses that upstream deployment plus a private loopback/volume override.
It does not modify upstream nginx or apply the historical header workaround; current
Spring clients handle the actual header compatibility issue. [Vendor deployment guide](https://eclipse.dev/ditto/installation-running.html).

**For existing Ditto/MongoDB:** do not apply these new-volume recipes. Recover its exact
Compose files/project and volume mappings and use them. Attaching a new empty volume to
an existing deployment would hide its data; a stopped container is not permission to replace it.

For a **new private runtime only**, after confirming the destination does not exist:

```bash
export DITTO_SOURCE="$V1_RUNTIME/ditto-source"
git clone --branch 3.8.4 --depth 1 https://github.com/eclipse-ditto/ditto.git "$DITTO_SOURCE"
git -C "$DITTO_SOURCE" rev-parse HEAD
export DITTO_DEPLOYMENT="$DITTO_SOURCE/deployment/docker"
```

Expected revision output (stop on a mismatch):

```text
5dbb05e6294e5ac0103506102baff9eab755d180
```

Use the upstream sample authentication unchanged for the documented local-sample
path. Do not edit or commit password material in either Git clone. Create
`$V1_RUNTIME/ditto-local.yaml` **only if absent**, outside Git. This portable Compose
override is statically checked; it is not a freshly executed deployment recipe:

```bash
test ! -e "$V1_RUNTIME/ditto-local.yaml" && cat > "$V1_RUNTIME/ditto-local.yaml" <<'YAML'
services:
  mongodb:
    ports: !reset []
    volumes:
      - qa_v1_mongodb:/data/db
  gateway:
    ports: !reset []
  nginx:
    ports: !override
      - "127.0.0.1:18080:80"
volumes:
  qa_v1_mongodb:
YAML
```

Define this function in the control terminal (and again in new control terminals):

```bash
ditto_stack() {
  DITTO_VERSION=3.8.4 docker compose -p qa-sdv-v1-ditto \
    -f "$DITTO_DEPLOYMENT/docker-compose.yml" -f "$V1_RUNTIME/ditto-local.yaml" "$@"
}
ditto_stack config --quiet
ditto_stack up -d
ditto_stack ps -a
```

The first Compose file determines upstream relative bind paths. The override adds a new named database volume; `down` without `-v` retains it. Image tags other than Ditto
may still resolve new patch digests; record actual digests for evidence. The upstream
sample is development configuration, not a production security baseline. Review any
host mounts and Fedora SELinux labels with the vendor instructions; do not disable SELinux.

## 6. Private authentication and additive provisioning

Read the pinned official sample's `documentation/src/main/resources/pages/ditto/intro-hello-world.md`
and `deployment/docker/nginx.conf` locally. They document the sample account and the
`nginx:<authenticated username>` subject mapping. Do not paste sample passwords into
commands, this guide, screenshots or Git. Other proxies may supply different subjects.

In the Bash provisioning/ingress terminal, prompt privately:

```bash
read -r -s -p 'Ditto username (hidden): ' SDV_DITTO_USERNAME
printf '\n'
read -r -s -p 'Ditto password (hidden): ' SDV_DITTO_PASSWORD
printf '\n'
export SDV_DITTO_USERNAME SDV_DITTO_PASSWORD
export SDV_DITTO_BASE_URL=http://127.0.0.1:18080
export SDV_MQTT_HOST=127.0.0.1
export SDV_MQTT_PORT=18883
export SDV_MQTT_CLIENT_ID=qa-sdv-v1-twin-ingress
curl --fail --silent --show-error --max-time 5 --user "$SDV_DITTO_USERNAME" \
  -o /dev/null -w 'HTTP %{http_code}\n' "$SDV_DITTO_BASE_URL/api/2/things"
```

Curl prompts separately for the password; it is intentionally not supplied in argv.
Expected output after successful authentication (prompts themselves are **output**):

```text
Ditto username (hidden):
Ditto password (hidden):
HTTP 200
```

If HTTP is not 200, resolve service/authentication first. Do not infer missing resources
from 401/403/timeouts. Configure legitimate local accounts and grants before provisioning.

### Individual twins (one authorized provisioning process)

With ingress stopped, run once on new resources or to validate existing compatible ones:

```bash
"$PYTHON" -B -m ditto.v1 provision --subject "nginx:$SDV_DITTO_USERNAME"
"$PYTHON" -B -m ditto.v1 read all
```

This creates only absent individual policies/Things with conditional requests; it
validates existing identities/grants rather than replacing them. A mismatch requires
review, not a reset. Provisioning requires explicit subject root READ/WRITE grants on
`thing:/` and `policy:/`; see [individual twin details](../ditto/V1-TWINS.md).
The Things initially have no V1 health snapshot. The **first validated real observation**
initializes it; never seed fabricated HEALTHY state. Ingress later preserves legacy
features, context and watermarks with conditional persistence.

### Fleet Thing: distinct writer subject and real authentication

Spring's materializer needs an existing `sdv:fleet-v1` and policy. The explicit fleet
provisioner requires **different owner and service subjects**; inventing a subject string
does not create an authenticated account. The historical live harness used the one
legitimate sample subject in its isolated fixture; that is not the role-separated
provisioning command below. Production subjects/grants/TLS need owner approval.

**Prerequisite/gap:** a distinct fleet-writer account must already be configured and
authenticate through the deployment's proxy. This repository does not provide a
verified fresh-machine procedure for that role-separated account configuration.
Have the deployment owner supply the actual writer username and authenticated subject;
do not invent one, weaken policies or modify the sample auth file to bypass this gap.
The earlier isolated one-subject fixture is evidence of that fixture only, not a
production identity-separation procedure.

```bash
read -r -p 'Existing authorized fleet-writer username: ' FLEET_USER
test "$FLEET_USER" != "$SDV_DITTO_USERNAME"
```

Stop here if that prerequisite is unavailable. The provisioning and backend commands
below apply only after real accounts/subjects and permissions are established.

Load the chosen writer password privately and provision **only if the fleet resources
are confirmed absent in this new deployment**:

```bash
read -r -s -p 'Fleet writer password (hidden): ' FLEET_PASSWORD
printf '\n'
export SDV_V1_DITTO_BASE_URL="$SDV_DITTO_BASE_URL"
export SDV_FLEET_PROVISION_USERNAME="$SDV_DITTO_USERNAME"
export SDV_FLEET_PROVISION_PASSWORD="$SDV_DITTO_PASSWORD"
export SDV_FLEET_OWNER_SUBJECT="nginx:$SDV_DITTO_USERNAME"
export SDV_FLEET_SERVICE_SUBJECT="nginx:$FLEET_USER"
"$PYTHON" scripts/v1_fleet_provision.py
```

Check authenticated GET `/api/2/things/sdv:fleet-v1` and policy access before deciding
it is absent. This script is create-only and can partially create resources before a
later failure. Existing 409/412, authorization errors or partial state require inspection;
never delete/recreate to make it succeed. The script grants the fleet service READ/WRITE
only at `thing:/features/summary/properties`; keep individual writes with the sole ingress.
Separate production-role policy review is not completed by this local-sample recipe.

## 7. First-time edge build, then normal startup

Do not run the single-vehicle Compose file concurrently. On a new local-only setup,
create `$V1_RUNTIME/edge-local.yaml` **only if absent** to bind the base YAML's otherwise
all-interface ports to loopback:

```bash
test ! -e "$V1_RUNTIME/edge-local.yaml" && cat > "$V1_RUNTIME/edge-local.yaml" <<'YAML'
services:
  mqtt:
    ports: !override ["127.0.0.1:18883:1883"]
  kuksa-001:
    ports: !override ["127.0.0.1:55556:55555"]
  kuksa-002:
    ports: !override ["127.0.0.1:55557:55555"]
  provider-001:
    ports: !override ["127.0.0.1:8091:8090"]
  provider-002:
    ports: !override ["127.0.0.1:8092:8090"]
YAML
edge() {
  docker compose -p qa-sdv-v1 -f "$REPO/vehicle-simulator/docker-compose.v1.yml" \
    -f "$V1_RUNTIME/edge-local.yaml" "$@"
}
edge config --quiet
edge build
```

Builds download images/Python dependencies and Velocitas packages. Review registry
access, architecture and disk capacity first; a successful Compose parse is not a
successful build. This is an explicit first-time command, not hidden demo behavior.

Normal startup of **already built** prerequisites (no image rebuild):

```bash
edge up -d --no-build mqtt kuksa-001 kuksa-002 provider-001 provider-002
curl --fail --max-time 5 http://127.0.0.1:8091/health
curl --fail --max-time 5 http://127.0.0.1:8092/health
```

Expected provider output: `{"status":"UP"}` (JSON whitespace may differ).
Wait for both provider health endpoints, not merely `Up` container status. KUKSA uses
insecure local gRPC and MQTT allows anonymous local connections; these bindings are
for local development, not a public deployment. The committed Mosquitto configuration
sets `persistence false`: do **not** claim durable broker queues/sessions across restarts.
Ditto watermarks survive in MongoDB, but messages during broker downtime may not.

### Sole ingress (foreground terminal A)

After section 6 exports and MQTT are ready, at the repository root:

```bash
"$PYTHON" -B -m ditto.v1 run
```

Keep this terminal running; inspect startup/subscription and safe persistence messages.
Do not start a second ingress with the same or a different client ID writing these twins.
Before starting Docker002, inspect other Compose projects/app publishers. If Kanto
is installed on this Linux runtime, run the following **Linux-only check** and ensure
no app002 pilot is running before the Docker startup command:

```bash
sudo /opt/qa-sdv-v1-kanto/bin/kanto-cm --host /run/qa-sdv-v1-kanto/container-management.sock --timeout 15 list
```

If a managed pilot is active, coordinate ownership and use its documented managed
stop/get sequence to verify stopped before restoring Docker002. Do not stop unrelated
namespace workloads. Core Windows/macOS hosts without Kanto do not run this command.
In control terminal B, after defining `edge` again if necessary:

```bash
edge up -d --no-build app-001 app-002
"$PYTHON" -B -m ditto.v1 read all
```

The read terminal needs the same private Ditto exports. Expect two correctly identified
Things with `features.v1.properties`: `lastEventId`, original `sourceTimestamp`, health,
faults and LiDAR data. Wait for fresh source times to advance. If a fresh event arrives
but no V1 feature appears, inspect failed reads/permissions; do not manually seed one.

## 8. Backend, fleet materializer and frontend

Build the executable once after Java21 is configured (Bash, repository root):

```bash
(cd backend && bash ./mvnw --batch-mode --no-transfer-progress clean verify)
```

The artifact is `backend/target/backend-0.0.1-SNAPSHOT.jar`. In **one** backend terminal,
load the private owner/read and writer credentials again; do not assume another
terminal's variables are available. For the local sample, the ingress/provisioning
owner pair may also serve reads; production read-only identity separation needs review.
Set the actual variables consumed by application.properties:

```bash
export SERVER_ADDRESS=127.0.0.1
export SERVER_PORT=8082
export SDV_VEHICLE_IDS=vehicle-001,vehicle-002
export SDV_V1_DITTO_MODE=live
export SDV_V1_DITTO_BASE_URL=http://127.0.0.1:18080
export SDV_V1_DITTO_USERNAME="$SDV_DITTO_USERNAME"
export SDV_V1_DITTO_PASSWORD="$SDV_DITTO_PASSWORD"
export SDV_SIMULATOR_MODE=http
export SDV_PROVIDER_001_BASE_URL=http://127.0.0.1:8091
export SDV_PROVIDER_002_BASE_URL=http://127.0.0.1:8092
export SDV_V1_FLEET_ENABLED=true
export SDV_V1_FLEET_USERNAME="$FLEET_USER"
export SDV_V1_FLEET_PASSWORD="$FLEET_PASSWORD"
java -jar backend/target/backend-0.0.1-SNAPSHOT.jar
```

Enable fleet materialization on **exactly one backend instance**. A second frontend
or a second API reader is not a reason to start another fleet writer. Legacy adapters
still default to `development`; `SDV_V1_DITTO_MODE=live` and `SDV_SIMULATOR_MODE=http`
select the relevant real V1 paths without claiming other historical adapters are live.
The default vehicle registry includes a third ID; the explicit two-ID export is required.

In **frontend terminal C**, at the root with `PYTHON` defined:

```bash
"$PYTHON" -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

Open **http://localhost:3000**. The committed frontend defaults to API
`http://localhost:8082`; do not open index.html as a `file://` URL. Backend CORS permits
localhost ports3000/5173/8081/8080, not arbitrary hostnames/ports. A custom backend port
needs a controlled `globalThis.SDV_CONFIG.API_BASE_URL` injected before modules, as the
Linux demo helper does; there is no general environment-variable loader for static JS.
Do not edit production frontend code merely to follow this default path.

### Real readiness checks (control terminal)

```bash
curl --fail --max-time 5 http://127.0.0.1:8082/actuator/health
curl --fail --max-time 5 http://127.0.0.1:8082/api/v1/vehicles
curl --fail --max-time 5 http://127.0.0.1:8082/api/v1/vehicles/vehicle-001/state
curl --fail --max-time 5 http://127.0.0.1:8082/api/v1/vehicles/vehicle-002/state
curl --fail --max-time 5 http://127.0.0.1:8082/api/v1/fleet
"$PYTHON" -B -m ditto.v1 read all
curl --fail --max-time 5 --user "$SDV_DITTO_USERNAME" "$SDV_DITTO_BASE_URL/api/2/things/sdv:fleet-v1"
```

Expect the registry to contain only the two IDs; both views should become AVAILABLE
and HEALTHY with empty faults when real source observations are healthy. Fleet API
and materialized fleet should reflect both individuals; compare source/event identity
at the same observation boundary, allowing time for the scheduled write. A 200 registry
or actuator response alone is insufficient. Defaults are stale after5s, unavailable
after30s; source time is preserved rather than replaced by ingestion time. These are
configured defaults, not approved product SLAs. A stale snapshot is not fresh integration.

## 9. Simple backend fault/clear walkthrough

Use the **backend A3 endpoint**, not direct provider mutation, for this demonstration.
First confirm both vehicles healthy and no pre-existing user scenario on vehicle-002.
From the control terminal (Bash):

```bash
curl --fail --max-time 5 -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"INJECT_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}' \
  http://127.0.0.1:8082/api/v1/diagnostics/actions
```

Expected acknowledgement includes generated `actionId`, `traceId`, vehicle-002 and
`status: ACCEPTED`. This is **dispatch acknowledgement**, not completed health change.
Wait for actual vehicle-002 fault propagation (the deterministic scenario progresses
over ticks), and inspect individual twins/API, fleet summary and dashboard. Vehicle-001
must stay healthy/fault-free; keep original event/source times and do not fabricate
missing optional command context. Clear through the same backend:

```bash
curl --fail --max-time 5 -H 'Content-Type: application/json' \
  -d '{"vehicleId":"vehicle-002","action":"CLEAR_SCENARIO","scenario":"LIDAR_OBSTRUCTION"}' \
  http://127.0.0.1:8082/api/v1/diagnostics/actions
```

Wait for fresh HEALTHY recovery and fleet/dashboard agreement, not just the ACK.
If interrupted after injection, clear **your** scenario before stopping services.
Do not clear another user's active scenario or run fault tests on a shared deployment
without coordinating ownership. The interactive Linux launcher automates these waits
and saves commands, action IDs, snapshots and observed timings.

## 10. Restarting and stopping without deleting data

**Already prepared core restart:** inspect ports/processes first; use the same
`V1_RUNTIME`, Compose files/project names and volumes. Start Ditto with `ditto_stack up -d`,
wait for authenticated reads, start edge prerequisites without rebuilding, start the
sole ingress and apps, then the sole backend writer and frontend. Skip provisioning
for compatible existing resources; do not replay create-only fleet provisioning blindly.
Do not run the destructive/full acceptance harness as a startup command.

**Normal core stop:** clear your scenario, Ctrl+C the foreground frontend/backend/ingress
terminals, and stop only these reviewed projects:

```bash
edge stop
ditto_stack stop
```

Use the same functions/files that started them. To remove **only your new project
containers/networks**, `edge down` and `ditto_stack down` preserve named database volumes;
`stop` is preferable when simply pausing. Never add `-v`/`--volumes`, prune volumes,
reset twins/policies or delete unrelated networks. In particular do not copy the
base edge YAML's historical `down --volumes` comment into a data-preserving procedure.
A stopped service may retain historical nonzero exits: inspect, do not relabel them.

## 11. Linux-only interactive demo and Kanto boundary

The current launcher requires the Linux paths/process model, normal sudo and a dedicated
Kanto/containerd runtime. It does not provide a full fresh-machine installer. Read the
[detailed Linux runbook](../velocitas-app/kanto/LINUX-RUNTIME.md) and [pilot guide](../velocitas-app/kanto/V1-PILOT.md).
Their early checkpoints reference older images, historical failures and prepared-host
recovery; current clean shutdown evidence is [merged-main verification](../evidence/v1/merged-main-20261115/README.md).
Do not treat an old exit1 shutdown or previously missing environment as an unresolved
current application defect, nor a historical personal archive as a portable download.

Required before the launcher: Linux x86_64 and Kanto1.0.0/containerd prepared with
`/opt/qa-sdv-v1-kanto/bin/kanto-cm`, socket `/run/qa-sdv-v1-kanto/container-management.sock`,
namespace `qa-sdv-v1-kanto`, automatic deployment/remote Things integration disabled,
and daemon HOME/XDG_CONFIG_HOME explicitly set as documented. Inspect existing units,
namespace, paths and containers before additive installation. Use ordinary terminal
sudo; never alter socket permissions, containers in other namespaces or Docker's daemon.
No new Windows/WSL/macOS Kanto setup is certified here.

### Portable Linux configuration (no developer worktree dependency)

Keep the Linux runtime at `$HOME/.local/share/qa-sdv-v1/runtime`; the helper hardcodes
that runtime for Java/namespace operations. Ensure its `jdk21/bin/java` resolves to
your actual installed Java21. If `jdk21` is absent, a local symlink is sufficient:

```bash
# Linux only, after verifying JAVA_HOME points to Java21; never overwrite existing paths:
test -d "$JAVA_HOME"
test ! -e "$V1_RUNTIME/jdk21" && ln -s "$JAVA_HOME" "$V1_RUNTIME/jdk21"
```

Build the backend in **this** clone as in section 8. For a new Linux amd64 pilot image,
explicit build/export and identity preparation can use the recorded OCI workflow;
this is first-time operator preparation, not automatic launcher behavior:

```bash
export APP_SOURCE_SHA="$(git rev-parse HEAD)"
export V1_DEMO_APP_IMAGE="docker.io/library/qa-v1-demo-app:sha-$APP_SOURCE_SHA"
export V1_DEMO_ARCHIVE="$V1_RUNTIME/kanto-demo-$APP_SOURCE_SHA.tar"
docker buildx build --platform linux/amd64 --tag "$V1_DEMO_APP_IMAGE" \
  --output "type=oci,dest=$V1_DEMO_ARCHIVE" -f velocitas-app/app/Dockerfile velocitas-app
"$PYTHON" - <<'PY'
import hashlib, json, os, tarfile
from pathlib import Path
archive = Path(os.environ['V1_DEMO_ARCHIVE'])
with tarfile.open(archive) as stream:
    index = json.load(stream.extractfile('index.json'))
info = {'sourceSha': os.environ['APP_SOURCE_SHA'], 'dockerRef': os.environ['V1_DEMO_APP_IMAGE'],
        'indexSha256': index['manifests'][0]['digest'].split(':', 1)[1],
        'archive': str(archive), 'archiveSha256': hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()}
with (Path(os.environ['V1_RUNTIME'])/'kanto-image.json').open('x') as target:
    target.write(json.dumps(info, indent=2)+'\n')
PY
sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto \
  images import --platform linux/amd64 "$V1_DEMO_ARCHIVE"
sudo /opt/qa-sdv-v1-kanto/bin/kanto-cm --host /run/qa-sdv-v1-kanto/container-management.sock --timeout 15 list
```

Do not build from dirty app sources or copy a prebuilt image from a different CPU.
Record versions/digests and verify import identity; registration alone proves no lifecycle.
If using an already verified compatible image, reuse its **actual local** image metadata
instead; never relabel someone else's source/archive identity as yours.

Create a runtime config **only if absent**, adapting the example's personal defaults:

```bash
"$PYTHON" - <<'PY'
import json, os
from pathlib import Path
repo = Path.cwd()
config = json.loads((repo/'scripts/v1-demo.example.json').read_text())
runtime = Path(os.environ['V1_RUNTIME'])
config.update(backend='http://127.0.0.1:8082',
              backendJar=str(repo/'backend/target/backend-0.0.1-SNAPSHOT.jar'),
              imageInfo=str(runtime/'kanto-image.json'),
              app001='qa-sdv-v1-app-001-1', dockerApp002='qa-sdv-v1-app-002-1')
with (runtime/'demo.json').open('x') as target:
    json.dump(config, target, indent=2)
PY
```

If you used a different project/ports, set its real container names and endpoints.
The Docker app002 container must exist even when stopped. The generated config above
reuses the **existing backend8082**; keep that one authorized fleet writer running.
Stop the manually started static server (Ctrl+C in frontend terminal) before the launcher
owns port3000: its frontend-compatibility check expects its injected API configuration,
not any arbitrary static server. Do not start another backend writer on18081 alongside8082.

Then run from the root on the prepared Linux host:

```bash
bash scripts/run-v1-demo.sh
```

It privately prompts for `SDV_V1_DITTO_USERNAME`/`SDV_V1_DITTO_PASSWORD` if not exported
and performs ordinary terminal `sudo -v`; later commands use bounded `sudo -n`. Prompts
such as `Ditto username (hidden):` are **output**, not shell commands. It reuses compatible
prerequisites, narrates Enter-to-continue steps and saves `evidence/v1/demo-<UTC timestamp>/`.
`--check` is read-only and starts nothing; absent backend/dashboard can therefore fail it.
The current launcher uses local anonymous MQTT and one supplied Ditto pair for an
owned backend; it has no separate fleet-secret configuration for that spawn. Prefer
reusing the role-configured backend above; this is a remaining portability/security-role gap,
not a reason to broaden policies. Never expose secrets via shell tracing or process-env dumps.

At the Kanto step, it must stop and verify Docker002 before Kanto002 starts; it refuses
unknown/duplicate Docker publishers or other active dedicated-namespace containers.
Never run `edge up ... app-002` while Kanto002 is active. Managed restart requires clean
stop, no old process, a different event/source newer than previous source, request and
runtime started_at, plus exact real MQTT/Ditto matching and001 isolation. It proves
same-device managed restart, not crash auto-restart, remote LAN or full V1 acceptance.

Choose N for owned-resource cleanup; only Docker002 that this run stopped is restored
after Kanto is verified stopped. Initially stopped Docker002 stays stopped. Reused backend8082
and other pre-existing services remain yours to stop. Choose Y to keep demo services
supervised in the terminal until Enter/Ctrl+C. See `cleanup.json`/`failure.json` for recovery;
if Kanto cleanup is unverified, **do not start Docker002**. Inspect the recorded unique
pilot name with normal sudo and stop it cleanly first. No volume/policy/twin deletion.

## 12. Troubleshooting and explicit setup gaps

| Symptom | Check / action |
|---|---|
| `docker` unavailable/permission denied | Start Desktop or inspect Linux daemon/context. In WSL enable distro integration; do not install a competing daemon or loosen sockets. |
| Compose unknown `!override` / `!reset` | Check plugin version/capabilities; use2.24.4+ and validate merged config. Legacy v1 syntax is insufficient. |
| Port in use | Inspect the owner/project, including upstream gateway8081/Mongo27017 if using unmodified Compose. Use reviewed consistent loopback mappings; never kill unrelated services. |
| 401 / 403 / 404 from Ditto | Separate authentication, authorization, missing-resource and transport failures. Verify actual proxy subject and policy. Never treat a failed read as permission to overwrite. |
| Fleet provision409/412 | Existing or partially created resources: inspect policy/Thing and validate identity/grants; the script intentionally refuses replacement. Do not delete them to rerun. |
| MQTT visible but no twin update | Check QoS1/non-retained, correct topic/vehicle, sole ingress SUBACK, pending writes and feature-create permissions. Existing properties-only grants alone cannot create an absent feature. |
| Backend shows three vehicles/development data | Explicitly export two IDs, live V1 Ditto and HTTP simulator modes. Legacy development adapters are separate; mocks are not evidence. |
| Fleet API healthy but fleet Thing old | Inspect the one materializer's enabled flag, credentials and narrow summary-properties grant; wait for a new source/event. A successful API read proves no fleet write. |
| Frontend blank/CORS/error | Use localhost:3000 over HTTP, backend8082 or explicit injected config; check browser network/console. Shell-served HTML alone is not a rendered live dashboard. |
| STALE / UNAVAILABLE | Inspect preserved source time, provider/KUKSA/MQTT/ingress health and clock synchronization. Do not replace source time with now or hide missing/null values. |
| Protobuf/gRPC build errors | Verify Python3.12, use the recorded requirements, generate all five modules and keep host versus app-image versions separate. Do not arbitrarily upgrade pins. |
| No matching image platform / illegal instruction | Verify each registry manifest and CPU requirements. Apple Silicon edge history is not full-stack certification; no silent emulation guarantee. |
| Kanto socket failure | Use normal sudo, inspect daemon/namespace/socket and explicit HOME/XDG_CONFIG_HOME. Existing containers must be inspected; create-only pilot names cannot be blindly reused. |
| Failed/aborted rehearsal | Read dated result/cleanup records; clear only your scenario, verify Kanto stopped before restoring Docker002. Keep original failures and service exits. |

Separate implementation work is needed for a general cross-platform demo launcher,
configurable Linux runtime/JDK/containerd paths and credentials separated for its owned
backend writer. The committed sample JSON contains prepared-host artifact/container
assumptions; section 11 adapts them without changing application code. A general
cross-platform backend-URL injection mechanism, portable Kanto installer/daemon recipe
and a fully verified role-separated fresh deployment are not delivered by this docs PR.
The portable setup recipe and distinct-subject configuration are statically reviewed only;
no claim of a newly successful Windows/macOS or distinct-subject integration run is made.

## 13. Legacy MVP (separate deployment)

The recorded single-vehicle MQTT baseline remains supported by
[scripts/run-autonomous-mvp-demo.sh](../scripts/run-autonomous-mvp-demo.sh). It explicitly
builds/recreates its own Compose services; review before use on a shared Docker host:

```bash
# Bash, only after stopping conflicting V1 services and reviewing script side effects:
SIMULATED_VEHICLE_ID=vehicle-001 bash scripts/run-autonomous-mvp-demo.sh
```

This demonstrates simulator→KUKSA→Velocitas→MQTT healthy/fault/recovery, not V1 fleet
integration. The older bridge/Spring/frontend iteration-3 workflow has distinct
[contracts/evidence](Version_1/evidence/iteration-3/evidence.md) and a
[demo guide](Version_1/12-iteration-3-demo-guide.md). `scripts/start-demo.sh` and
`scripts/start-demo.ps1` belong to that older workflow; they expect a repo `.venv` and
other legacy configuration, not this persistent V1 environment. The Windows PowerShell
variant is not proof of a native Windows V1 launcher. Historical in-process uProtocol
and OpenSOVD-compatible mapping are not deployed V2 distributed integrations.

## 14. Security and evidence handling

Keep real credentials in private prompts/environment or an approved secret store,
never tracked `.env`, browser source, URLs, CLI password arguments, screenshots or logs.
Do not dump container environments to debug. On exit unset private terminal variables
or close the terminal. The local sample has plaintext loopback HTTP/gRPC and anonymous
MQTT; do not expose it as production. Certificate trust, authenticated role separation,
permissions and clock/timing decisions need explicit review, not disabled validation.

For a demonstration record, retain source SHA/dirty state, actual configs without
credentials, image identities, commands/exits, actions/observations and cleanup state.
Review/redact raw service logs **before** tracking/sharing; some upstream logs may contain
authentication. Current demo output is designed to redact known credentials; that does
not make arbitrary external logs safe. Preserve failed results and historical evidence.

## 15. Validation and evidence boundaries for this guide

This documentation change ran no project services, installed no system packages and
provisioned no resources. On the Linux review host, Markdown parsing and40 relative
links passed; the Bash examples and2 inline Python programs parsed; core-edge, pinned
upstream-Ditto and Kanto-prerequisite Compose configurations passed non-deploying
assertions. The offline MQTT fixture render/check passed. README Mermaid parsed and
rendered in installed Chrome with Mermaid11.4.1. None of these checks starts the stack.

Native PowerShell instructions were statically reviewed only (`pwsh` unavailable).
Windows/WSL2/macOS commands, distinct-subject authentication/provisioning and a fresh
Linux deployment of these new recipes were **not executed**. The prior Linux runtime
and macOS edge records below are historical evidence, not cross-platform certification.

Existing evidence (not fresh execution of these new onboarding recipes):

- [Merged-main Linux verification](../evidence/v1/merged-main-20261115/README.md): tested4afbbd8, real clean initialization/Spring HTTP/fleet and three Kanto managed cycles.
- [E1 macOS arm64 edge evidence](../evidence/v1/E1-two-vehicle-edge.md): two isolated edge pipelines, with explicit revision and later QoS correction boundaries.
- [Demo launcher controls/rehearsal](../evidence/v1/demo-launcher-development-20261115/README.md):11 focused controls and operator working-copy live sequence; later hardening not fully re-rehearsed.
- [Current release-readiness findings](findings/v1-release-readiness.md), [MVP–V1 comparison](findings/mvp-to-v1-comparison.md), [skill-use/provenance](../evidence/v1/skill-sources.md).

Read dated follow-ups and actual merged history before treating historical “pending”
text as current. Contract/human decisions and deliverables are separate from engineering
passes; no full V1 acceptance, remote-LAN or automatic crash-recovery claim follows from
this guide. The PR description records which documentation checks actually ran.
