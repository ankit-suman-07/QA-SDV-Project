# Eclipse OpenSOVD - Diagnostic Interface (Atharva)

## Status
OpenSOVD's gateway is confirmed read-only - both for sensor data
(Iteration 2) and for app/operation-style resources (Iteration 3:
`/sovd/v1/apps/diagnostics` exposes only `data`, `belongs-to`, and
`is-located-on` links, no operations resource). Diagnostics are exposed
through two standalone adapters instead, both wired to the live Ditto
twin, neither writing into the real OpenSOVD gateway. This is NOT a
complete production OpenSOVD implementation.

## Explore the real gateway (mock mode, read-only)
```bash
docker run -p 7690:7690 ghcr.io/eclipse-opensovd/opensovd-gateway --mock
curl -s http://localhost:7690/sovd/v1
```
API is discoverable: root → `components`/`apps` → `{resource}/data` →
`{signal}`. See `docs/evidence/component-tests/opensovd-mock/` and
`docs/evidence/iteration-2/07-opensovd-confirmed-read-only.png` for the
full read-only confirmation (a correctly-shaped `PUT` returns
`{"error_code":"error-response","message":"read only"}`).

## Fault mapping (`fault_mapper.py`)
Maps Ditto's active faults into OpenSOVD's diagnostic resource shape.
Handles both single-signal faults (`BATTERY_LOW`, `TEMPERATURE_HIGH`,
tire pressure) and correlated faults (`COOLING_SYSTEM_FAILURE` - two
affected signals, both observed values, both activation/recovery
threshold sets).

```bash
python opensovd/scripts/map-active-faults.py --watch
```
Polls the live Ditto twin and prints each active fault in OpenSOVD shape.

## Diagnostic actions (`action_adapter.py`)
Validates and forwards `INJECT_SCENARIO`/`CLEAR_SCENARIO` diagnostic
requests to the Spring Boot API (`/api/v1/diagnostics/actions`), since
OpenSOVD itself has nothing to forward to. Returns structured errors
(`docs/10-iteration-3-contract.md` Error Contract) for invalid requests,
an unavailable backend, or a timeout - without ever making a network call
for a request that fails local validation.

```python
from opensovd.action_adapter import submit_diagnostic_action, get_diagnostic_action_status

response = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
status = get_diagnostic_action_status(response["actionId"])
```

## Tests
```bash
python -m pytest tests/test_fault_mapper.py tests/test_action_adapter.py -v
```

## Known limitations
- `action_adapter.py`'s `DEFAULT_BACKEND_URL` is a placeholder, not yet confirmed against Ankit's running Spring Boot service.
- Correlated fault mapping and verification depend on `diagnostics.activeFaultDetails` being populated by the integration bridge; until then, `detectedAt`/`traceId`/`actionId`/`eventId` report as `None` in mapped output.
- Only `COOLING_SYSTEM_FAILURE` is defined as a correlated fault; single-signal faults remain `BATTERY_LOW`, `TEMPERATURE_HIGH`, and the four tire-pressure codes.