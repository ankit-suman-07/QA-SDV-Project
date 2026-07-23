# Eclipse Ditto - Digital Twin (Atharva)

## Setup
```bash
git clone --depth 1 https://github.com/eclipse-ditto/ditto.git /tmp/ditto-src
cd /tmp/ditto-src/deployment/docker
docker compose up -d
```
Do not copy `dev.env` to `.env` - it pins an unpublished `0-SNAPSHOT` tag.
Omit `.env` entirely; images default to the public `latest` tag.

## Create the vehicle-001 policy and thing
```bash
cd ditto/config
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/policies/sdv:vehicle-001-policy -H "Content-Type: application/json" -d "@vehicle-policy.json"
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/things/sdv:vehicle-001 -H "Content-Type: application/json" -d "@vehicle-001-thing.json"
```

## Run the interim Kuksa→Ditto bridge
Stands in for the Spring Boot backend's Kuksa adapter until it's built.
```bash
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install kuksa-client requests
python ditto/scripts/interim-kuksa-to-ditto-bridge.py
```
Requires `vehicle-simulator` (see its own README) already running.

## Verify
```bash
curl.exe -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001
```
See `docs/evidence/integration-tests/ditto-kuksa/` for full fault-lifecycle
evidence (trigger + clear, with screenshots).

## Known limitations
- Bridge script is temporary, not the team's Spring Boot backend.
- Only front-left tire pressure has real data (per vehicle-simulator's own limitation).