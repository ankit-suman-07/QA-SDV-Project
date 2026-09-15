# Ditto and OpenSOVD Feasibility

## Objective
Determine how vehicle-001 can be represented and synchronized as a digital twin
in Eclipse Ditto, and confirm a minimum viable OpenSOVD setup for exposing
diagnostic information, ahead of Day 2 contract finalization.

## Proposed Role in This Project
- Eclipse Ditto: backend digital-twin store. Holds current vehicle signals
  (speed, battery, temperature, tire pressure) and calculated health/fault
  state for vehicle-001, split into independent `signals` and `health`
  features so frequent signal updates don't require rewriting health data.
- Eclipse OpenSOVD: diagnostic-facing interface. Exposes current sensor data
  and (eventually) fault/DTC-style information derived from backend health
  logic, through a discoverable REST API (entry point → components → data).

## Official Sources Reviewed
- https://eclipse.dev/ditto/intro-overview.html
- https://github.com/eclipse-ditto/ditto/blob/master/deployment/docker/README.md
- https://github.com/eclipse-opensovd
- Emmanuel Adegboye's `vehicle-simulator` README and source
  (`emmanuel/feature/kuksa-vehicle-simulator`) — Kuksa databroker version,
  VSS paths, and fault-injection behaviour.

## Recommended Approach
- Run Ditto locally via its official docker-compose recipe (NOT the dev.env
  file, which pins a SNAPSHOT tag only available to Ditto's own build
  pipeline; omitting it lets images default to the public `latest` tag).
- Model vehicle-001 as a single Thing (`sdv:vehicle-001`) with two features:
  `signals` (raw telemetry) and `health` (status/activeFaults/faultCount).
- Bridge Kuksa to Ditto with a small interim Python service (stands in for
  the Spring Boot backend's eventual Kuksa adapter) that reads current
  values via `kuksa_client`, applies the battery-low health rule, and PUTs
  results into Ditto.
- Run OpenSOVD's gateway container in `--mock` mode for now, since the real
  backend/adapter isn't built yet. Its REST API is discoverable: root →
  `/sovd/v1` → `components` → `{component}/data` → `{signal}`.

## Minimum Working Example or Evidence
See `docs/evidence/integration-tests/ditto-kuksa/evidence.md` for full request/response logs:
- Created policy + thing for vehicle-001 in Ditto; confirmed partial-state
  synchronization (single-property update leaves other fields untouched).
- Ran OpenSOVD gateway in mock mode; confirmed it exposes ECU voltage
  (12.6V) and temperature (85.0°C) readings via `/sovd/v1/components/ecu/data/...`.
- Integrated Emmanuel's real `vehicle-simulator` (Kuksa databroker 0.7.0) via
  the bridge script; confirmed full fault lifecycle against real data:
  battery-low fault triggered when `INJECT_FAULT=1` drained battery to 0
  (`health.status` → `WARNING`, `activeFaults` → `["BATTERY_LOW"]`), and
  cleared automatically once the simulator recovered (`health.status` →
  `HEALTHY`, `activeFaults` → `[]`). Cross-checked simulator log values
  against the Ditto twin to confirm live sync, not stale data.

## Required Inputs and Produced Outputs
- Ditto needs: policy JSON, thing JSON, and a feed of real signal updates -
  now supplied by Emmanuel's simulator via the interim bridge (previously
  "eventually," now working).
- Ditto produces: a queryable, always-current twin per vehicle.
- OpenSOVD needs: a mapping from our health engine's fault output to
  OpenSOVD-style diagnostic resources (not yet built - mock mode stands in
  for now; still not wired to the live Kuksa→Ditto pipeline).
- OpenSOVD produces: standard diagnostic queries (current data, faults) over
  REST, following the `/sovd/v1/...` discoverable link pattern.

## Dependencies
- Docker Desktop running locally.
- Final field names/thresholds from `docs/04-vehicle-health-contracts.md`
  (still "Proposed" as of this update) before the thing schema can be
  considered final — signal paths are now confirmed via Emmanuel's work,
  but thresholds beyond battery (temperature, tire pressure) are not yet
  team-approved.
- Backend health engine (Ankit) to know what values/fault structure to map
  into OpenSOVD.

## Technical Risks
- OpenSOVD is a young project (v0.1.1 as of testing); real (non-mock)
  integration with our own backend is unproven and may need a custom adapter.
- The Kuksa→Ditto bridge is a Python interim stand-in, not the team's actual
  Spring Boot backend — will need to be superseded once Ankit's service is
  ready, and behaviour should be re-verified after that swap.
- Emmanuel's simulator currently only publishes front-left tire pressure
  (per his own documented limitation) — the other three tire signals in our
  thing schema have no real data source yet.

## Fallback Approach
- If real OpenSOVD backend integration proves impractical within the
  schedule, keep using mock mode and instead implement and document a
  bounded adapter mapping our health engine's fault output into an
  OpenSOVD-shaped JSON response ourselves, matching the fallback already
  identified in our project proposal's risk table.

## Decisions Required on Day 2
- ~~Final field names and units for signals~~ - resolved for speed, battery,
  temperature, and front-left tire pressure via Emmanuel's verified VSS
  paths (confirmed tire pressure unit is psi, not kPa, by direct
  observation: simulator publishes ~32, consistent with our `tirePressurePsi`
  field name).
- Final activation/recovery thresholds for temperature and tire-pressure
  faults (battery threshold already implemented at 20%/25% per proposal
  baseline).
- Whether OpenSOVD is integrated live or via the documented fallback adapter.
- Whether the interim Python bridge is kept temporarily or replaced
  immediately once Ankit's Spring Boot backend is ready.
- Data source for the three remaining tire-pressure signals, since only
  front-left is currently simulated.

## Open Questions
- Does OpenSOVD support pushing fault/DTC-style data in mock mode, or only
  current-data sensor values? (Still unresolved - needs follow-up
  investigation before diagnostic-mapping work begins.)
- Should the interim bridge's health-rule logic move as-is into the Spring
  Boot backend, or be reimplemented there to match the team's chosen
  language/framework conventions?