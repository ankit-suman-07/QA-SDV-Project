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

## Recommended Approach
- Run Ditto locally via its official docker-compose recipe (NOT the dev.env
  file, which pins a SNAPSHOT tag only available to Ditto's own build
  pipeline, omitting it lets images default to the public `latest` tag).
- Model vehicle-001 as a single Thing (`sdv:vehicle-001`) with two features:
  `signals` (raw telemetry) and `health` (status/activeFaults/faultCount).
- Run OpenSOVD's gateway container in `--mock` mode for now, since the real
  backend/adapter isn't built yet. Its REST API is discoverable: root →
  `/sovd/v1` → `components` → `{component}/data` → `{signal}`.

## Minimum Working Example or Evidence
See `eclipse-components/ditto/evidence.md` for full request/response logs:
- Created policy + thing for vehicle-001 in Ditto.
- Updated `batteryPercent` via a single-property PUT; confirmed via GET that
  only that field changed, proving partial-state synchronization works.
- Ran OpenSOVD gateway in mock mode; confirmed it exposes ECU voltage
  (12.6V) and temperature (85.0°C) readings via `/sovd/v1/components/ecu/data/...`.

## Required Inputs and Produced Outputs
- Ditto needs: policy JSON, thing JSON, and (eventually) a feed of real
  signal updates from the backend/simulator.
- Ditto produces: a queryable, always-current twin per vehicle.
- OpenSOVD needs: a mapping from our health engine's fault output to
  OpenSOVD-style diagnostic resources (not yet built, mock mode stands in
  for now).
- OpenSOVD produces: standard diagnostic queries (current data, faults) over
  REST, following the `/sovd/v1/...` discoverable link pattern.

## Dependencies
- Docker Desktop running locally.
- Final field names/thresholds from `docs/04-vehicle-health-contracts.md`
  (currently "Proposed") before the thing schema can be considered final.
- Backend health engine (Ankit) to know what values/fault structure to map
  into OpenSOVD.

## Technical Risks
- OpenSOVD is a young project (v0.1.1 as of testing); real (non-mock)
  integration with our own backend is unproven and may need a custom adapter.
- Ditto thing schema will need revision once the contract locks on Day 2.

## Fallback Approach
- If real OpenSOVD backend integration proves impractical within the
  schedule, keep using mock mode and instead implement and document a
  bounded adapter mapping our health engine's fault output into an
  OpenSOVD-shaped JSON response ourselves, matching the fallback already
  identified in our project proposal's risk table.

## Decisions Required on Day 2
- Final field names and units for signals (per docs/04 checklist).
- Final activation/recovery thresholds for each fault type.
- Whether OpenSOVD is integrated live or via the documented fallback adapter.

## Open Questions
- Does OpenSOVD support pushing fault/DTC-style data in mock mode, or only
  current-data sensor values? (Needs follow-up investigation before
  diagnostic-mapping work begins.)