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

**Contract clarification:** A rejected stale or future-dated observation
preserves the last accepted LiDAR values and the established health and fault
pair. Set `recoveryState=NONE` and `recoveryStartedAt=null`. With a retained
distance above 10 m, the supported fault pairs are WARNING with
`LIDAR_OBSTRUCTION`, or CRITICAL with either `LIDAR_OBSTRUCTION` or
`LIDAR_SENSOR_FAILURE` as the sole active fault. A subsequent fresh valid
observation above 10 m starts a new recovery window. Clearing still requires
at least two seconds of continuous fresh healthy source observations.

Freshness uses original UTC: age ≤5 s AVAILABLE, >5 through 30 STALE, >30 UNAVAILABLE;
>1 s future UNAVAILABLE/clock error. Sensor validity, last-known health, source
silence, recovery and transport availability are distinct fields. Stale values
remain visible but cannot clear faults or count currently healthy. Velocitas owns
`evaluate_silence()` every 100 ms using source intervals and local monotonic
receipt time. A gap strictly greater than 0.5 s triggers silence. Cached,
rejected and duplicate samples cannot reset silence or advance recovery.
The backend independently derives source availability. Silence propagation
requires a separate versioned status update with independent ordering that
retains the last real observation identity and time. See the [C5 status
handoff](#c5-status-handoff) for the contract and proposed deployment details.

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

For the rejected-input reset in C4, the snapshot preserves the accepted observation
and its ordering watermark, including
`sessionGeneration`, `sessionId`, `sequence`, `frame`, `sourceTimestamp`
and `lastEventId`. The rejected observation supplies neither a new observation
nor a new ordering watermark. Backend readers accept the retained-fault
snapshot under the existing validation and source availability rules.

**New project-lead retention default for review:** Bayan owns per-vehicle fault
transitions and diagnostic projection history (100 latest records and ≤7 days,
evict on read/write by UTC, retain current active faults separately). Ankit owns
authoritative action lifecycle/history with same bound; delivers correlated
records to Bayan, never a second fleet engine. Histories retain original event,
action/trace IDs, detection/clear times, outcome and provenance; transitions only,
not every 10 Hz sample. Evidence logs are separate artifacts, no raw clouds.

### C5 health envelope 2.0.0

The health topic is `sdv/{vehicleId}/v2/health`. For schema version
`2.0.0`, require exactly these application fields, plus the optional
fields listed below when present:

- Required: `schemaVersion`, `vehicleId`, `eventId`, `sessionId`,
  `sessionGeneration`, `sequence`, `frame`, `simulationSeconds`,
  `sourceTimestamp`, `processingTimestamp`, `provenance`, `lidar`,
  `health`, `faults`, `recoveryState`, `recoveryStartedAt`, `sourceSilent`.
- Optional: `actionId` and `traceId` as a pair, and
  `velocityMetersPerSecond`.

The C2 and C4 type, identity, and recovery rules apply. Reject unknown
top-level and nested keys. The required `lidar` object contains exactly
`sensorAvailable` and `distanceMeters`. Keep `distanceMeters` present
with null when unavailable and a finite nonnegative number when available.
The required `recoveryStartedAt` is null for `NONE` and a valid UTC
timestamp string for `IN_PROGRESS`. Other required values are non-null.

Omit both correlation identifiers or supply both as nonblank strings.
A lone identifier, explicit null, or another type is invalid. Omit
velocity or supply an object containing exactly `x`, `y`, and `z` with
valid finite numeric components and a representable derived speed per C2.
Null and incomplete velocity objects are invalid. A future C2/C3
dropout-reason wire field requires separate producer compatibility
review. This version allows no generic extensions.

### C5 status handoff

Publish status on **sdv/{vehicleId}/v2/status**, QoS 1, retain false.
The observation and health topics and their replay rules remain unchanged.
Require strict JSON, at most 64 KiB. For schema version `2.0.0`, all
fields below are required, including the explicit null for
`recoveryStartedAt`. There are no optional fields. Reject unknown
top-level keys and unknown keys inside `observationRef`:

| Field | Rule |
|---|---|
| schemaVersion | String "2.0.0". The topic selects the status schema. |
| vehicleId | Configured ID, matching the topic exactly. |
| sessionId, sessionGeneration | Nonblank unpadded ID and positive integer generation, both currently authorized for the vehicle. |
| statusEventId | Nonblank unpadded string, unique per vehicle and authorized session generation, independent of observation IDs. |
| statusRevision | Integer from 1 through 9007199254740991, strictly increasing per vehicle and authorized session generation. Gaps are allowed. |
| evaluationTimestamp | Valid C2 UTC timestamp for evidence only. |
| observationRef | Exactly eventId, sequence, frame and sourceTimestamp, using C2 types and exact accepted wire values. Outer vehicle and session fields complete the tuple. |
| recoveryState, recoveryStartedAt | Exactly "NONE" and null in this reset-only version. |
| sourceSilent | Boolean. May preserve the current value or set it true. Only an accepted observation clears it. |
| health, faults | The established C4 health and canonical fault list of the referenced observation, unchanged. |

Reject unknown fields, duplicate keys, nonfinite numbers, booleans as
integers, and mismatched identities. A valid sensor-failure reset at a
retained distance of 20 m:

~~~json
{"schemaVersion":"2.0.0","vehicleId":"vehicle-003","sessionId":"session-1","sessionGeneration":1,"statusEventId":"reset-1","statusRevision":1,"evaluationTimestamp":"2026-01-01T00:00:01.120Z","observationRef":{"eventId":"vehicle-003-11","sequence":11,"frame":111,"sourceTimestamp":"2026-01-01T00:00:01.100Z"},"recoveryState":"NONE","recoveryStartedAt":null,"sourceSilent":false,"health":"CRITICAL","faults":["LIDAR_SENSOR_FAILURE"]}
~~~

A silence update can preserve the same observation and fault pair and
set sourceSilent to true with a new status ID and revision. WARNING
obstruction, CRITICAL obstruction and CRITICAL sensor failure are valid
retained pairs above 10 m. A healthy source can go silent while its
last-known health remains HEALTHY and its faults remain empty.

Invalid example, rejected because sensor failure requires CRITICAL:

~~~json
{"schemaVersion":"2.0.0","vehicleId":"vehicle-003","sessionId":"session-1","sessionGeneration":1,"statusEventId":"invalid-2","statusRevision":2,"evaluationTimestamp":"2026-01-01T00:00:01.600Z","observationRef":{"eventId":"vehicle-003-11","sequence":11,"frame":111,"sourceTimestamp":"2026-01-01T00:00:01.100Z"},"recoveryState":"NONE","recoveryStartedAt":null,"sourceSilent":true,"health":"WARNING","faults":["LIDAR_SENSOR_FAILURE"]}
~~~

Only accepted observations initiate or advance recovery and clear or
de-escalate retained faults. Status never replaces accepted LiDAR, source
time or identity, advances sequence, frame or the observation watermark,
appends observation history, or refreshes source freshness. Availability
remains source-derived. A newer accepted observation supersedes the old
status projection while preserving status ordering for the active session.

#### Ordering and producer recovery

Serialize observation and status writes per vehicle. Reject unknown or
retired sessions and generation jumps. Status cannot register a session.
Within the active session, recognize a durable exact retry by revision,
ID and validated payload fingerprint before testing the current reference.
It is a no-op even if the observation has since advanced. Reject conflicting
revision reuse, reused IDs at another revision, and unseen revisions at
or below the high-water mark. A new status must reference exactly the
current accepted observation. Reject older or unknown references without
writing. Evaluation timestamps never determine order.

Persist the allocated revision and exact issued envelope before publish.
On restart, retry it unchanged or allocate a higher revision for a new
evaluation. If durable state is lost, stop publication until reconciled or
an authorized successor is established. Never reset an active counter.

#### Observation persistence receipts

**Proposed topic and schema for review:** Ingress publishes on
**sdv/{vehicleId}/v2/health/receipt**, QoS 1, retain false. Use strict JSON,
the same size limit, and exactly the fields below with the status envelope
types and reference rules:

~~~json
{"schemaVersion":"2.0.0","vehicleId":"vehicle-003","sessionId":"session-1","sessionGeneration":1,"observationRef":{"eventId":"vehicle-003-11","sequence":11,"frame":111,"sourceTimestamp":"2026-01-01T00:00:01.100Z"}}
~~~

Only authenticated ingress may publish receipts. The authorized producer
may subscribe only to its vehicle's receipt topic and cannot publish
receipts. Match the topic, vehicle, authorized session and complete
pending observation reference before issuing dependent status. MQTT
PUBACK alone proves transport handling, not application persistence.

Issue the receipt only after the health write is confirmed or the exact
retry of the current accepted observation is durably reconciled. Retrying
that observation unchanged regenerates the same receipt. Use bounded
backoff while the reference remains pending. Do not fabricate a replacement
observation after receipt loss. Duplicate receipts are idempotent.
On restart, recover the pending payload and retry it unchanged.

Allow one pending unissued status per vehicle awaiting a receipt and one
issued envelope for retry. Coalesce unissued evaluations for one reference.
Supersession invalidates the pending reference. Reevaluate on the newer
reference after its receipt, using a new ID and revision if needed. A
receipt proves the observation once committed, and ingress still requires
that it be current at the conditional status write. Thus cross-topic
delivery or receipt races cannot mutate a newer accepted observation.

#### C5 payload fingerprints

Ankit approved RFC 8785 JSON Canonicalization Scheme (JCS) and SHA-256.
This applies to the original C5 health envelope on
`sdv/{vehicleId}/v2/health` (the accepted observation) and the reset
envelope on `sdv/{vehicleId}/v2/status`. It does not change the C2
observation transport or assign a digest to persistence receipts.

Build a separate JSON object with exactly three members:
`messageType`, `schemaVersion` and `payload`. Copy the wire
`schemaVersion` to the outer object. Copy the following fields from the
validated wire envelope into `payload`, preserving field presence:

| `messageType` | Payload fields |
|---|---|
| `v2-health-observation` | `vehicleId`, `eventId`, `sessionId`, `sessionGeneration`, `sequence`, `frame`, `simulationSeconds`, `sourceTimestamp`, `processingTimestamp`, `provenance`, `lidar` (including `distanceMeters` and `sensorAvailable`), `health`, `faults`, `recoveryState`, `recoveryStartedAt`, `sourceSilent`, and optional `actionId` and `traceId` as a pair and `velocityMetersPerSecond` with `x`, `y`, `z` when present. |
| `v2-status` | `vehicleId`, `sessionId`, `sessionGeneration`, `statusEventId`, `statusRevision`, `evaluationTimestamp`, `observationRef` (exactly `eventId`, `sequence`, `frame`, `sourceTimestamp`), `recoveryState`, `recoveryStartedAt`, `sourceSilent`, `health`, `faults`. |

Reject unknown wire fields, including `packetId`, `brokerTimestamp`,
`fingerprint`, `fixtureLabel`, ingress-generated receipt fields,
projection metadata such as `_ingress` and `lastEventId`, and arbitrary
extensions. Transport metadata supplied outside the application envelope
never enters the fingerprint. The application `processingTimestamp`
is included.

The payload contains exactly the allowed application fields present on the
original wire message, with `schemaVersion` carried only in the wrapper.
Absent optional fields stay absent and required nulls remain present and
are hashed as JSON null. Explicit null is invalid for each optional field.
Do not mutate the original envelope or normalize timestamp strings.

1. Decode strict UTF-8 JSON, detecting duplicate property names at every
   level after JSON escape decoding. Retain number token kinds until
   validation. Validate the applicable application schema, including
   topic identity and the types and shape of any observation reference.
2. Reject malformed Unicode, including unpaired surrogates in strings and
   keys. Reject NaN and infinity, binary64 overflow, nonzero values that
   underflow to zero, and numbers outside field-specific bounds.
   Integer tokens must lie within ±(2^53 − 1) before conversion. In
   particular, `sessionGeneration`, `sequence`, `frame`,
   `statusRevision` and reference ordering fields require integer
   tokens and their schema-specific minimums. A decimal point or exponent
   is invalid on these fields even when the value is mathematically integral.
   For fields that accept fractional numbers, use finite IEEE 754 binary64
   semantics. Thus `1`, `1.0` and `1e0` have the same canonical
   representation there, and negative zero canonicalizes to `0`.
3. Construct the scoped object and apply [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html).
   Use recursive UTF-16 code-unit property sorting, ECMAScript-compatible
   number serialization and the RFC's string escaping. Preserve array
   order, original timestamp strings and precision, and decoded Unicode
   code-point sequences. Do not normalize Unicode, truncate timestamps
   or mutate the original envelope.
4. Encode the canonical result as UTF-8 without a BOM and hash those exact
   bytes with SHA-256. Store the 64 lowercase hexadecimal digits. Use
   SHA-256 of exact UTF-8 IDs for membership, with independent observation
   and status namespaces. Reject invalid envelopes without a fingerprint
   output or persistable record. For a status exact-retry candidate, use
   its scoped digest to check the durable record before comparing to the
   current reference. A new status requires an exact current reference.

Retain the digest of the original accepted health payload even after a
status overlay changes projected recovery or source silence. Reconcile an
exact health retry against that digest and the accepted observation tuple,
without recalculating the digest from projected properties or undoing the
overlay. See the [shared fingerprint vectors](../tests/fixtures/v2/status/README.md)
and [strict envelope cases](../tests/fixtures/v2/status/envelope-vectors.md).


#### Durable metadata and conditional writes

**Proposed layout for review:** Reserve an ingress-owned _ingress object
in v2 feature properties. Store authorized session ID and generation,
latest original health payload fingerprint, accepted observation-ID
membership scoped to the active session, status revision high-water mark,
and committed status records keyed by revision with status ID and payload
fingerprints. Keep the accepted observation tuple in public v2 properties,
with eventId persisted as lastEventId. Preserve the original health
fingerprint across status overlays so an exact health retry can reconcile.
Reject _ingress in incoming payloads. Keep private metadata out of
backend projections.

Use one ETag-protected write for each state change and its corresponding
metadata. Health creation keeps If-None-Match: *. Updates use If-Match
on the current properties ETag. Status requires an existing accepted
observation. After HTTP 412, reload and revalidate against the current
reference, revision, IDs and watermark before a bounded retry. After a
lost response, reload and reconcile exact committed records. Never
overwrite a newer snapshot or treat an unresolved outcome as persistence.
Restart reloads durable state and authorization before processing.
Keep all writes and metadata isolated per vehicle.

ACK QoS 1 after confirmed persistence or exact durable reconciliation.
Terminal rejection follows the existing rejection ACK policy, with a
recorded reason and no success receipt. Keep transient errors or uncertain
outcomes unacknowledged. Receipt publication is recoverable by exact
observation retry even if ingress stops after committing and before
publishing the receipt.

**Candidate limits (PROPOSED / PENDING ANKIT REVIEW):** Per active vehicle
session, cap counts at 4,096 observation IDs and 512 status records. Also
cap compact UTF-8 observation membership at 288 KiB, status records at
96 KiB, and the complete _ingress object at 400 KiB. Cap the compact
prospective full Thing at 768 KiB including legacy data. Verify actual
serialized response size on pinned Ditto against the existing 1 MiB
read limit before implementation.

Check counts and encoded bytes on the prospective state under the same
ETag before writing. Reject new observations at capacity, preserving exact
retry reconciliation and eligible status writes within their separate
budget and the total ceiling. Reject new statuses at their own limit.
Surface capacity rejection explicitly. Never evict active IDs. Require
authorized session rollover to resume accepting observations. At nominal
10 Hz, 4,096 IDs cover about 6 minutes 50 seconds. If the operating
window or measured full-Thing budget cannot support this layout, the
in-feature design is blocked. A separate store requires an agreed
atomic or fenced recovery design.

**Capacity measurement (PROPOSED / PENDING ANKIT REVIEW):** A compact
UTF-8 simulation used the vehicle-003 Thing fixture, a policy ID, a small
legacy health feature and current v2 properties. It added an authorized
session ID and generation, original observation fingerprint, high-water
revision, and the following unindented JSON maps:

- Observation membership maps each 64-character lowercase ID digest to
  `true`. The map takes `72 × count + 1` bytes including braces. At
  4,096 entries it uses 294,913 bytes, one byte above 288 KiB. With
  these candidate limits the byte cap permits 4,095 entries.
- Status records map the decimal revision string to an object containing
  `idHash` and `fingerprint` (both 64-character lowercase digests).
  Revisions 1–512 take 84,373 bytes. At that revision width profile,
  the first status byte-budget rejection without a count cap would occur
  at revision 597, so the 512-record cap binds first. Gaps and longer
  revision keys consume more bytes.
- At 4,095 observations and 512 statuses, the metadata is 379,436 bytes,
  leaving 30,164 bytes below 400 KiB. The sample whole Thing is 380,089
  bytes, leaving 406,343 bytes below 768 KiB and 668,487 bytes below
  1 MiB. These are fixture measurements, not a bound on legacy features,
  session IDs, server-added fields, or the real Ditto response.

| Accepted observations per second | 4,096 observation count slots | 4,095 usable slots under byte cap |
|---:|---:|---:|
| 10 (V2 nominal proposal) | 409.6 s | 409.5 s |
| 5 (V1 live evidence used a 0.2 s tick) | 819.2 s | 819 s |
| 2 (V1 live evidence used a 0.5 s tick) | 2,048 s | 2,047.5 s |
| 1 (V1 acceptance override) | 4,096 s | 4,095 s |
| 0.2 (V1 Compose default) | 20,480 s | 20,475 s |

Times are slots divided by rate, per vehicle, starting with an empty
ledger and assuming every publication is accepted. No deployed C5 health
or status publication rate was established. Status is transition-driven.
For illustration, at one distinct status per second, 512 records last
512 s and the 96 KiB budget in the dense-revision model would reject
the 597th record. At one distinct status per minute those points are
512 and 597 minutes. Exact retries do not consume new records. With the
sample Thing and proposed count bounds, neither the total metadata ceiling
nor the Thing ceiling binds. Evaluate both against the real persisted
Thing and response, especially with larger legacy entities.

**Freezing the limits is blocked** pending an agreed session lifetime,
actual Ditto response sizing, and an authorized rollover operating plan.
Nominal 10 Hz allows only about 6 minutes 50 seconds per session in
this layout. Options for review are a shorter explicitly authorized
session window or revised representation/budgets validated against real
Thing sizes. A separate store would require an agreed recovery and
fencing design.


#### Historical observation IDs and legacy migration

The latest watermark alone cannot detect an older accepted ID reused
with new sequence, frame and source time after ingress restart. Reject
historical reuse using durable membership, even when ordering would
otherwise pass. Exact retry of the latest accepted observation is a
separate fingerprint check. Commit membership and watermark together.

Treat missing or incomplete historical membership as legacy. Do not
reconstruct earlier IDs from the watermark. Block new writes under that
legacy session and require an explicitly authorized higher generation.
Atomically fence the old session, register the successor and initialize
empty ledgers and status high-water mark zero under If-Match. Preserve
the last accepted observation, source time, LiDAR and retained faults
until valid successor data arrives. Require the first successor source
time to be strictly newer. Reject old-session traffic, including retries.
Accept successor status only after its first observation commits.
Restart reloads the fence and pending-first-observation state. An uncertain
migration write requires reconciliation against the persisted authorization
and initialization state. Never reinitialize an already active generation.

#### Acceptance coverage

Share synthetic fixtures under tests/fixtures/v2/status. Offline tests
must cover the three retained pairs, contradictory pairs, reset and
silence, unchanged accepted identity and watermark, and recovery at
1.999 s and 2.000 s. Test receipt ACL and identity matching, receipt loss
and exact retry, revision and ID conflicts, late status, unknown
references, observation/status races, producer and ingress restarts,
historical ID reuse after restart, capacity, migration, HTTP 412 and
lost responses, ACK gating, and three-vehicle isolation.

Real Mosquitto-to-Ditto verification must capture broker-observed PUBACK
timing, receipt ACL and regeneration, actual conditional writes and HTTP
412, restart and all three Thing snapshots. Read through the backend to
verify the reset is visible with unchanged accepted source time and
watermark, and availability still uses the source clock. Earlier real
ordinary-ingestion results do not verify this handoff.


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
