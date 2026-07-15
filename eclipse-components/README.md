# Eclipse Components - Ditto & OpenSOVD (Atharva)

Setup and run instructions for the Ditto digital twin and OpenSOVD diagnostic
components. For the vehicle signal source (Kuksa + simulator), see
`vehicle-simulator/README.md`.

## Prerequisites
- Docker Desktop running
- Python 3.11 (NOT 3.14 - `grpcio-tools`, a `kuksa_client` dependency, has no
  prebuilt wheel for 3.14 yet and will fail to install without a full
  Visual C++ build toolchain). Check installed versions with `py -0p`.

## 1. Start Eclipse Ditto

```bash
git clone --depth 1 https://github.com/eclipse-ditto/ditto.git /tmp/ditto-src
cd /tmp/ditto-src/deployment/docker
docker compose up -d
```
Do **not** copy `dev.env` to `.env` - it pins an unpublished `0-SNAPSHOT` tag
only available to Ditto's own build pipeline. Omit `.env` entirely; images
default to the public `latest` tag.

Verify: `curl -u ditto:ditto http://localhost:8080/api/2/things` → expect `[]`.

## 2. Create the vehicle-001 policy and thing

```bash
cd eclipse-components/ditto
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/policies/sdv:vehicle-001-policy -H "Content-Type: application/json" -d "@vehicle-policy.json"
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/things/sdv:vehicle-001 -H "Content-Type: application/json" -d "@vehicle-001-thing.json"
```

## 3. Start Eclipse OpenSOVD (standalone, mock mode)

```bash
docker run -p 7690:7690 ghcr.io/eclipse-opensovd/opensovd-gateway --mock
```
Not yet wired into the live pipeline below - demonstrated independently.
Explore via `curl -s http://localhost:7690/sovd/v1`.

## 4. Start the vehicle signal source (Kuksa + simulator)

See `vehicle-simulator/README.md` for full details. Summary:
```bash
cd vehicle-simulator
docker-compose up --build
```
Starts Kuksa Databroker (pinned `0.7.0`) and the real signal provider
together on port `55555`. To trigger a fault, set `INJECT_FAULT=1` under the
`provider` service in `docker-compose.yml` and rerun.

## 5. Run the Kuksa → Ditto bridge (interim, stands in for the Spring Boot backend)

```bash
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install kuksa-client requests
python eclipse-components\ditto\vehicle_pipeline.py
```
Reads current signals from Kuksa, applies the battery-low health rule
(WARNING below 20%, clears at 25%+), and writes both raw signals and
calculated health/fault state into the Ditto twin every ~2 seconds.

## 6. Verify

```bash
curl.exe -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001
```
`batteryPercent`/`temperatureCelsius`/`tirePressurePsi.frontLeft` should
match the values in the `vehicle-simulator` provider logs, confirming live
sync. See `eclipse-components/ditto/evidence.md` for captured evidence
including a full fault trigger/clear cycle.

## Known limitations
- The Kuksa→Ditto bridge is a temporary Python stand-in, not the team's
  Spring Boot backend.
- Only front-left tire pressure is simulated (see `vehicle-simulator`'s own
  known limitations).
- OpenSOVD runs standalone; not yet receiving data from this pipeline.

See 'vehicle-simulator/screenshots/' for a visual walkthrough of the
full fault lifecycle (normal → fault injected → detected → cleared).
