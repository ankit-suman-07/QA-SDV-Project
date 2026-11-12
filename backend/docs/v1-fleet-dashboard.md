# A5 fleet API, writer and dashboard

C5–C7 of `docs/v1-interface-contracts.md` 1.0.0 define the projection. `GET /api/v1/fleet` derives it from both individual V1 twins, using one captured UTC evaluation time, sorted identities, concurrent reads and a whole-response read deadline. Health counts include only AVAILABLE observations. STALE and old UNAVAILABLE snapshots retain explicitly labelled last-known health; missing/untrusted snapshots have null data. The API never reads a cached fleet Thing or waits for a fleet write.

## Backend configuration

A2 endpoint/auth/timeouts remain under `sdv.v1.ditto.*`. See [A2 setup](v1-live-twin-api.md). A3 provider mapping remains independent; see [A3 setup](v1-scenario-routing.md).

| Property | Environment | Default |
|---|---|---|
| `sdv.v1.fleet.enabled` | `SDV_V1_FLEET_ENABLED` | false |
| `sdv.v1.fleet.interval` | `SDV_V1_FLEET_INTERVAL` | 2s |
| `sdv.v1.fleet.initial-delay` | `SDV_V1_FLEET_INITIAL_DELAY` | 2s |
| `sdv.v1.fleet.write-timeout` | `SDV_V1_FLEET_WRITE_TIMEOUT` | 2s |
| `sdv.v1.fleet.username` | `SDV_V1_FLEET_USERNAME` | empty |
| `sdv.v1.fleet.password` | `SDV_V1_FLEET_PASSWORD` | empty |

Enable **exactly one backend writer per fleet Thing**, including across replicas. There is no distributed leader election. The process prevents overlapping updates; intervals are measured after the schedule trigger, with busy triggers skipped. Each attempt recomputes observations, then sends one atomic PUT of the exact fleet projection to `/api/2/things/sdv:fleet-v1/features/summary/properties`. The read deadline and write deadline are separate budgets. No immediate HTTP retry occurs; the next configured schedule attempts fresh materialization.

Live enabled writes require a valid service Basic-auth pair; anonymous operation is permitted only in explicit mock mode. The writer uses the configured A2 Ditto base URL and connect timeout, with its **own** service credentials and write deadline. Read credentials remain independent. Redirects are disabled. Success is logged as `fleet_write_succeeded`; failures log a safe code, including `AUTH_CONFIGURATION` for 401/403, and `retry=NEXT_INTERVAL`. The writer retains an in-process failure counter/last-success timestamp for tests and inspection. Failed writes do not discard individual reads or fail the fleet API.

## Explicit real Ditto provisioning

Provision against your intended isolated Ditto deployment before enabling writes. First create a backend service account in the deployment's authentication layer; its resolved subject must match `SDV_FLEET_SERVICE_SUBJECT`. The existing deployment uses `nginx:<username>` subjects. The provisioning administrator is a separate account. Credentials are server-side environment values only.

From repository root, with actual deployed account names and subject IDs:

```bash
export SDV_V1_DITTO_BASE_URL=http://localhost:8080
export SDV_FLEET_PROVISION_USERNAME=ditto
export SDV_FLEET_OWNER_SUBJECT=nginx:ditto
export SDV_FLEET_SERVICE_SUBJECT=nginx:fleet-service
read -r -s -p 'Provisioning password: ' SDV_FLEET_PROVISION_PASSWORD
export SDV_FLEET_PROVISION_PASSWORD
python3 -B scripts/v1_fleet_provision.py
unset SDV_FLEET_PROVISION_PASSWORD
```

The script creates `sdv:fleet-v1-policy` first. Its owner can manage the Thing/policy; the fleet service can READ/WRITE only `thing:/features/summary/properties`. It then creates `sdv:fleet-v1` with `policyId=sdv:fleet-v1-policy`, `attributes.kind=fleet`, `attributes.vehicleIds=[vehicle-001,vehicle-002]` and an empty `summary` feature. No fabricated summary counts are provisioned. All requests carry `If-None-Match: *`; existing resources return a conflict and are preserved. A partial run can leave the policy created: inspect/finish provisioning with the administrator rather than overwriting deployed policy or data. The script refuses redirects and prints no credentials or raw response bodies.

With Java 21 selected and read credentials configured as documented by A2:

```bash
export SDV_V1_FLEET_ENABLED=true
export SDV_V1_FLEET_USERNAME=fleet-service
read -r -s -p 'Fleet service password: ' SDV_V1_FLEET_PASSWORD
export SDV_V1_FLEET_PASSWORD
(cd backend && bash ./mvnw spring-boot:run)
curl -fsS http://localhost:8082/api/v1/fleet
# In another terminal, use administrator credentials to inspect the materialized feature:
curl --user "$SDV_FLEET_PROVISION_USERNAME" -fsS \
  "$SDV_V1_DITTO_BASE_URL/api/2/things/sdv:fleet-v1/features/summary/properties"
```

These real-Ditto commands are a handoff, **not executed live evidence**. Policy principal resolution, actual authorization and resource creation must be verified on the integrated deployment. Compare the stored projection with API output at the same evaluation time; ordinary sequential live calls naturally have different generatedAt values. Fixed-clock HTTP tests verify exact equality.

## Prepared mocks and dashboard

The prepared mock does not persist fleet summaries. For ordinary API/UI development, leave the fleet writer disabled:

```bash
python3 -B -m scripts.v1_dev.http_mocks --ack-development-only --live-clock
(cd backend && bash ./mvnw spring-boot:run -Dspring-boot.run.profiles=v1-mock)
python3 -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

Open `http://localhost:3000/`. `frontend/js/config.js` defaults to Java on 8082; set `API_BASE_URL` there or set `globalThis.SDV_CONFIG.API_BASE_URL` before loading modules. `FLEET_PREVIEW=true` visibly labels an isolated preview API (default preview port 19082 is also detected). No browser configuration contains Ditto endpoints or credentials. Preview screenshots do not verify Java or persistence. Mocks age naturally: refresh with their `/_mock/states/{vehicleId}` controls as needed.

The dashboard uses the shared API client and existing CSS. It shows fleet counters and a selected vehicle, protects selection from old responses, labels retained data on failures and sends LiDAR inject/clear via A3. ACCEPTED/DISPATCHED is dispatch acknowledgement only; subsequent observations establish health/recovery. Scenario POSTs are never automatically retried. The old dashboard remains at `vehicle.html`, with diagnostics/performance pages retained.

## Reproducible Java and browser smoke

After Java 21 `clean verify`, the following launches owned mocks, actual packaged Java, an isolated authenticated provisioning/fleet-write capture, and the frontend. Ports other than the frontend are allocated locally; no existing live resources are touched:

```bash
python3 -B -m scripts.v1_dev.fleet_smoke --java "$JAVA_HOME/bin/java" \
  --artifacts-dir /tmp/a5-fleet-smoke --hold
```

The command prints PASS after backend checks and writes exact URLs to `stack.json`. In another terminal, with `playwright-core` and Chrome installed:

```bash
PLAYWRIGHT_MODULE=/path/to/playwright-core/index.mjs \
CHROME_PATH=/usr/bin/google-chrome \
node frontend/tests/fleet-browser.mjs /tmp/a5-fleet-smoke/stack.json
```

Ctrl-C stops the harness and only its owned processes. Omit `--hold` for backend-only verification and automatic cleanup. This capture is a controlled HTTP substitute for fleet persistence, not Eclipse Ditto. See [recorded evidence](../../evidence/v1/fleet-dashboard.md).
