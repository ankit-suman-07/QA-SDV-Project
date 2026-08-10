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

## Stopping Ditto
```bash
cd /tmp/ditto-src/deployment/docker
docker compose down
```

## Verifying vehicle state
```bash
python ditto/scripts/verify-vehicle-state.py
python ditto/scripts/verify-vehicle-state.py --publication-interval-seconds 0.2
```
Exits `0` if the twin is complete and fresh, `1` with a printed list of
problems otherwise (missing fields, invalid health status, or a twin older
than `max(3x publication interval, 5s)` per docs/04 Section 6). Evidence
from experiment runs is under `docs/evidence/iteration-2/`

## Iteration 3: correlated cooling-system fault

The Ditto thing now includes `coolantPressureKpa` (signals) and a new
`diagnostics` feature (`lastActionId`, `lastTraceId`, `actionStatus`,
`activeFaultDetails`) per docs/10-iteration-3-contract.md.

`COOLING_SYSTEM_FAILURE` activates when `temperatureCelsius >= 105` AND
`coolantPressureKpa <= 150` (both conditions required - a single abnormal
signal must not trigger it), and clears only when `temperatureCelsius <= 100`
AND `coolantPressureKpa >= 180`. The gap between these thresholds is
intentional hysteresis, not a bug - a fault legitimately stays active
while signals sit between activation and recovery.

The verifier (`verify-vehicle-state.py`) now also checks:
- `coolantPressureKpa` is present and a valid finite number (not boolean).
- All signal timestamps are valid ISO 8601.
- An active correlated fault hasn't fully recovered on both signals while
  still reported active (see hysteresis note above - only full recovery
  on both conditions is flagged, not the hysteresis zone itself).
- `diagnostics.activeFaultDetails` has a complete, matching record for
  any active correlated fault.

## OpenSOVD-compatible diagnostic action adapter

Since OpenSOVD's gateway is confirmed read-only for both data (Iteration 2)
and app/operation-style resources (re-confirmed in Iteration 3 -
`/sovd/v1/apps/diagnostics` exposes only `data`, `belongs-to`, and
`is-located-on` links, no operations resource), diagnostic actions are
implemented as a standalone adapter (`opensovd/action_adapter.py`) that
validates and forwards requests to the Spring Boot API instead. This is
NOT a complete production OpenSOVD implementation - see
docs/10-iteration-3-contract.md's OpenSOVD-Compatible Diagnostic Contract
section.

```python
from opensovd.action_adapter import submit_diagnostic_action, get_diagnostic_action_status

response = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
# {"actionId": "...", "status": "ACCEPTED", ...} or a structured error, e.g.
# {"status": 404, "error": "VEHICLE_NOT_FOUND", ...}

status = get_diagnostic_action_status(response["actionId"])
```

Update `DEFAULT_BACKEND_URL` in `action_adapter.py` once Spring Boot's
actual local port is confirmed with Ankit (currently a placeholder).

## Correlated fault mapping

`opensovd/fault_mapper.py` now dispatches correlated faults (currently
just `COOLING_SYSTEM_FAILURE`) through `map_correlated_fault_to_opensovd`,
returning both affected signals, both observed values, and both
activation/recovery threshold sets - the single-signal fault shape
(`map_fault_to_opensovd`) is unchanged and still used for
`BATTERY_LOW`/`TEMPERATURE_HIGH`/tire faults.

```bash
python opensovd/scripts/map-active-faults.py --watch
```

## Known limitations
- Bridge script is temporary, not the team's Spring Boot backend.
- Only front-left tire pressure has real data (per vehicle-simulator's own limitation).
- The action adapter's Spring Boot backend URL is a placeholder, not yet confirmed against the real running service.
- `diagnostics.activeFaultDetails` must be populated by the integration bridge for correlated-fault verification and mapping to show full data; until then, `detectedAt`/`traceId`/`actionId` fields report as `None`, and the verifier will flag a missing detail record for any active correlated fault.