# V2 independent-development contracts

Version **2.0.0-prep.1**, project-lead development baseline for affected-owner review.
Not team approval or evidence of implemented V2 behavior. Baseline main:
`140e6ffe4b939cb643654d862e46cd5a83be4d74`.
Extends [V1](v1-interface-contracts.md); follows the
[plan](11-FINAL-phase-v2-plan.md), [decisions](12-FINAL-phase-v2-technical-decisions.md)
and [task acceptance](13-FINAL-phase-v2-tasks-and-acceptance.md).

## V2-C1 Identity and ownership

| vehicleId | actor / sensor | provider | broker / app | twin |
|---|---|---|---|---|
| vehicle-001 | run manifest / front-001 | provider-001 | kuksa-001 / app-001 | sdv:vehicle-001 |
| vehicle-002 | run manifest / front-002 | provider-002 | kuksa-002 / app-002 | sdv:vehicle-002 |
| vehicle-003 | run manifest / front-003 | provider-003 | kuksa-003 / app-003 | sdv:vehicle-003 |

Emmanuel records actual actor/sensor integer IDs, episode, map, CARLA/client
versions, seed, sensor transform and settings in each run manifest. Actor IDs are
runtime values, never vehicle identities. Actor replacement starts a new session.
Ankit owns adapter→KUKSA, backend/actions, sole fleet aggregator/writer, dashboard,
integration/evaluation. Bayan owns Velocitas health/recovery, individual twins and
history, native diagnostics and coordinated Kanto validation. Emmanuel owns
actors/LiDAR, extraction, scenarios and independent ground truth.

Use per-vehicle configurable provider URLs and broker endpoints, existing
`SIMULATED_VEHICLE_ID`, `DATABROKER_HOST/PORT`, MQTT configuration where applicable.
Broker internal port stays 55555; host examples 55556/55557/55558, providers
8091/8092/8093. Ditto/MQTT/backend URLs are configurable. No duplicate publishers.
Mock endpoint defaults are in the [guide](v2-independent-development.md).

## V2-C2 Observation and clock

Compact JSON `schemaVersion="2.0.0"`, `fixtureLabel="SYNTHETIC"` in fixtures only:
`vehicleId`, nonblank `eventId`, nonblank `sessionId`, positive integer
`sessionGeneration`, integer `sequence` and `frame` ≥0, finite `simulationSeconds`
≥0, UTC `sourceTimestamp`, UTC `processingTimestamp`, `provenance` (CARLA or
SYNTHETIC), and `lidar={distanceMeters:number|null,sensorAvailable:boolean}`.
Distance is finite/nonnegative; unavailable requires null; available requires a
number. Identity must match the configured actor mapping and exact topic/target.
Reject malformed JSON, duplicate keys, nonfinite numbers, booleans as numbers,
unknown/padded IDs, unsupported versions and mismatches before side effects.
Event ID identifies one observation; retry preserves payload and ID. Processing
UTC records extraction/receipt and never refreshes source time. Optional actionId
and traceId are preserved together when known. Optional
`velocityMetersPerSecond={x,y,z}` contains three actual CARLA velocity
components in m/s. Each must be finite and numeric, excluding booleans.
The derived speed must be finite and representable as a VSS float. Omit the
field when motion is unknown. Existing LiDAR-only envelopes remain valid.
[Motion example](../tests/fixtures/v2/observations/vehicle-001-motion.json).

Each session manifest contains simulation origin and UTC origin. Convert:
`sourceUTC = utcOrigin + (simulationSeconds - simulationOrigin)`.
Never interpret simulation seconds as Unix time. Use one synchronized host UTC
anchor, record uncertainty, and preserve mapping through replay. Paused simulation
does not fabricate observations: source silence and freshness continue on UTC.
A restart/episode reset creates a new session and increasing persisted generation;
register it explicitly with ingress before publishing. Do not infer a restart
from a lower sequence or accept arbitrary remote generation jumps. UTC must not
roll backwards across sessions; correct clock/manifest before resuming.

**New project-lead defaults for review:** nominal 10 Hz (0.1 s); maximum continuous
healthy observation gap **0.5 s inclusive**, measured on source UTC and local
monotonic receipt clock. This permits modest jitter while rejecting cached data.
A gap >0.5 s resets recovery and marks `sourceSilent=true`; do not manufacture a
new source event every poll. Explicit invalid/dropout emits unavailable input
with original detection time and reason. Silence alone retains last-known health,
separate availability, and inhibits recovery; no healthy fallback. Fixed-clock
fixtures use epoch 2026-01-01 UTC. Rebase all UTC timestamps including origins,
processing/evaluation/action deadlines by a single offset; preserve relative
stale/future cases. Simulation seconds, sequences and IDs do not rebase.

## V2-C3 Front LiDAR extraction

Use standard `sensor.lidar.ray_cast`, not semantic LiDAR. CARLA local coordinates
are x forward, y right, z up; standard detections carry x/y/z/intensity floats.
See [official CARLA sensor reference](https://carla.readthedocs.io/en/0.9.16/ref_sensors/).
Record/pin the actual simulator/client pair before live use; 0.9.16 documentation
is the preparation reference, not a claim the project already runs that version.

**New project-lead extraction default for review:** sensor mounted at vehicle
front centre, yaw/pitch/roll zero, z=1.5 m above local road; range 50 m. Select
points in sensor coordinates with `0 < x <= 50`, `abs(y) <= 1.5`,
`-1.0 <= z <= 1.0`. Distance is minimum **x**, longitudinal metres from the sensor,
not Euclidean range or bumper distance. Configure rotation frequency/sensor_tick
for complete 10 Hz scans; exclude ego geometry through front mounting and positive
x. Ground truth uses this same region but independent scenario logs.

Any malformed tuple/nonfinite coordinate or intensity invalidates the entire
frame. Zero raw points, malformed byte length (not a multiple of 16), missing
frame or invalid timestamp → unavailable/null, reason INVALID_FRAME. A nonempty
valid scan with zero selected points → available distance 50, reason NO_FRONT_HIT
(censored at configured range, not measured free space). Complete sensor silence
has no frame and follows C2; never convert silence to 50 m.

Synthetic tuples `[x,y,z,intensity]`:
`[[5,0,0,1],[3,2,0,1],[-1,0,0,1]]` → 5 m;
`[[10,1.5,-1,0.5],[4,0,-1.1,1]]` → 10 m;
`[[2,2,0,1]]` → 50 m NO_FRONT_HIT;
`[]` → unavailable; `[[1,0,0,"bad"]]` → invalid/unavailable.
No raw cloud goes into Ditto.

## V2-C4 Signals, health and recovery

Preserve V1 paths/types: `Vehicle.Speed` float km/h, `Vehicle.Automation.Lidar.Front.NearestObstacleDistance`
float metres and `Vehicle.Automation.Lidar.Front.IsHealthy` boolean sensor validity
(the legacy name does not mean distance health). Existing warning/braking booleans
remain compatible legacy outputs. Adapter must not independently decide V2 health.
Unavailable writes validity false; never a fabricated large distance. Preserve
source timestamp and observation identity through an explicit companion envelope;
KUKSA value polling alone cannot prove new samples. Ankit authorized the C5
MQTT observation topic for implementation after all required KUKSA writes are
confirmed. Preserve the original envelope across retries and use the
companion's source timestamp for freshness. KUKSA 0.7.0 can stamp broker
write time on readback. See the [binding decision](v2-ankit-preparation-baseline.md#authorized-observation-companion-binding).

Speed = 3.6 × norm(CARLA velocity m/s), provenance CARLA for actual source
input. Omitted motion leaves speed unpublished. Existing battery
`Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` (%), temperature
`Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature` (°C), tire
`Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` (uint16 kPa) may stay SYNTHETIC.
Preserve existing VSS types; validate against broker metadata. Convert legacy psi
explicitly using 6.894757293168 kPa/psi and existing whole-kPa rounding; label each
supporting value's provenance, never present synthetic values as CARLA sensors.

Reuse V1 thresholds/codes: ≤5 CRITICAL obstruction, >5 through 10 WARNING
obstruction, >10 HEALTHY/no faults; unavailable CRITICAL sensor failure (priority).
After WARNING/CRITICAL, fresh valid >10 observations start recovery. Retain prior
health/faults and set `recoveryState=IN_PROGRESS` until ≥2 s continuous healthy
source observations. Then HEALTHY/[] and `recoveryState=NONE`. A fault/invalid/gap,
stale/future input or session restart resets window. Duplicate/cached/late events
never advance it. Initial fresh healthy observation needs no recovery window.
Freshness uses original UTC: age ≤5 s AVAILABLE, >5 through 30 STALE, >30 UNAVAILABLE;
>1 s future UNAVAILABLE/clock error. Sensor validity, last-known health, source
silence, recovery and transport availability are distinct fields. Stale values
remain visible but cannot clear faults or count currently healthy. Velocitas owns
`evaluate_silence()` every 100 ms using source intervals and local monotonic
receipt time. A gap strictly greater than 0.5 s triggers silence. Cached,
rejected and duplicate samples cannot reset silence or advance recovery.
The backend independently derives source availability. Silence propagation
requires a separate versioned status update with independent ordering that
retains the last real observation identity and time. Bayan's status schema
and ingress handoff remain pending.

## V2-C5 Events, twins, ordering and history

Explicit V2 MQTT topics `sdv/{vehicleId}/v2/observations` and
`sdv/{vehicleId}/v2/health`, QoS 1, retain false. Health carries C2 identity/time,
lidar, `health`, canonical `faults`, `recoveryState`, nullable `recoveryStartedAt`,
and `sourceSilent`. Separate V2 topic prevents V1 consumers applying instantaneous
recovery rules. Strict 64 KiB wire limit and validation reuse V1 rejection rules.

Provision only missing features; never PUT an empty whole Thing over legacy data.
Bayan writes atomic `/api/2/things/{thingId}/features/v2/properties` with health
payload and `eventId` renamed `lastEventId`; keep legacy features. GET whole Thing
validates thing/attribute/feature identity. Missing feature creation uses
`If-None-Match: *`; subsequent writes use current ETag with `If-Match`. 201/204 are
success, 412 reload/revalidate, 401/403 configuration error, 404 missing provisioning,
5xx bounded retry. Mock deliberately implements this subset, not Ditto policies.

Serialize per vehicle. Persist `(generation,sessionId,sequence,frame,sourceUTC,eventId)`
with successful snapshot. Reject equal/lower sequence/frame/time and conflicting
ID reuse; exact latest retry is ignored. On explicitly registered successor
session accept only higher generation with newer UTC; reject retired-session
traffic. Restart reloads persisted watermark; unreadable state blocks only that
vehicle. Failed/conditional writes never advance watermark or append committed
history. Idempotent retries must reconcile actual committed state after lost reply.

**New project-lead retention default for review:** Bayan owns per-vehicle fault
transitions and diagnostic projection history (100 latest records and ≤7 days,
evict on read/write by UTC, retain current active faults separately). Ankit owns
authoritative action lifecycle/history with same bound; delivers correlated
records to Bayan, never a second fleet engine. Histories retain original event,
action/trace IDs, detection/clear times, outcome and provenance; transitions only,
not every 10 Hz sample. Evidence logs are separate artifacts, no raw clouds.

## V2-C6 API, fleet and diagnostics

Keep V1 endpoints/fields and fixtures unchanged, including legacy action dispatch
status. Explicit `/api/v2/vehicles`, `/api/v2/vehicles/{id}/state`,
`/api/v2/fleet`, `/api/v2/diagnostics/actions` and `/api/v2/diagnostics/actions/{id}`
carry V2 projections. State retains V1 names `healthStatus`, `availability`,
`activeFaults`, lidar, sourceTimestamp, lastEventId, vehicleId, thingId; adds C5
recovery/sourceSilent/session fields. Unknown vehicle 404; known unavailable 200
with null fields if no trusted snapshot. No silent mock fallback in production.

Ankit alone counts/materializes `sdv:fleet-v2`, summary feature, same derived API
snapshot at one generatedAt. Exactly three sorted registered entries, even missing.
Only AVAILABLE entries count in health totals (recovering retains fault severity).
Availability totals sum to 3; health totals sum to available. Failed materialization
does not discard individual reads. Keep sdv:fleet-v1 and V1 readers during migration;
no automatic dual-write until affected owners review migration.

Actions preserve V1 `INJECT_SCENARIO`/`CLEAR_SCENARIO`, scenario LIDAR_OBSTRUCTION;
add `RESTART_APP` routed only to a lifecycle executor, never CARLA scenario provider.
Require vehicleId, actionId, traceId. Reused identical ID returns same accepted
record; conflicting payload 409. Validation 400, unknown target 404, provider
rejection 409, unavailable 503, dispatch timeout 504 (execution unknown).
202 ACCEPTED is not success. Correlated executor result → EXECUTING → SUCCEEDED /
FAILED / TIMED_OUT. Terminal states immutable; mismatch vehicle/action/trace is
rejected without mutation. **New project-lead defaults for review:** native health
request 2 s deadline, provider acceptance 2 s, inject/clear execution 10 s,
managed restart 30 s. Timeout stores uncertainty; late result retained as evidence,
never rewrites terminal outcome. Clear success means executor cleared injection;
observed 2 s recovery is separately required. Restart success needs actual lifecycle
and fresh post-start source observation, not acknowledgement alone.

[Native feasibility](v2-native-diagnostic-feasibility.md) isolates unresolved SDK/
OpenSOVD support. `/mock/v2/diagnostics/{vehicleId}/health` and `/faults` are
project-level HTTP boundaries only, never native uProtocol/OpenSOVD exchanges.
Fault mapping: LIDAR_OBSTRUCTION → project fault id lidar-obstruction, observed
metres and 5/10 thresholds; LIDAR_SENSOR_FAILURE → lidar-sensor-failure, unavailable
sensor, null distance; preserve severity, first/last seen, session/event and
correlation. No invented standardized DTC numbers. Healthy returns empty faults.

## V2-C7 Permissions and migration

Emmanuel controls CARLA actors/scenario permissions; Ankit broker publication,
backend action authorization and fleet-writer identity; Bayan per-vehicle MQTT
publish/subscribe ACLs, individual Ditto policies and native diagnostic permissions;
Ankit/Bayan coordinate Kanto identity/TLS. Browser never holds broker/privileged
Ditto credentials. Configure secrets locally, least-privilege per target, TLS for
cross-host authenticated traffic; no credentials here. Mocks are unauthenticated,
explicit opt-in, loopback only and advertise X-SDV-Mock; they do not test auth.

Affected owners review new defaults and live companion/native binding before
production merges. Update contract + independent expected fixtures + checks in
one reviewed PR. V1 schemas/endpoints, thresholds, availability and units stay
compatible; session/recovery/action semantics require explicit V2. This package
implements development substitutes only, not the owners' production components.
