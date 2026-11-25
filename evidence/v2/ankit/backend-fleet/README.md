# V2 backend state and fleet verification

Starting main `4d629c0f942f588d0c096f402eba82949ddb5f93` includes shared
prep #52 and the #55/#56 follow-ups. Java implementation and component tests
are at `ae9bc072af81499ba51697674abdd857393c1970`.
[Contract C5–C7](../../../../docs/v2-interface-contracts.md)

## Dashboard handoff

- `GET /api/v2/vehicles` returns
  `{"vehicleIds":["vehicle-001","vehicle-002","vehicle-003"]}`.
- `GET /api/v2/vehicles/vehicle-002/state` returns 200 for the registered
  vehicle. For the synthetic recovering sensor-failure case the projection is:

  ```json
  {
    "vehicleId": "vehicle-002",
    "thingId": "sdv:vehicle-002",
    "healthStatus": "CRITICAL",
    "availability": "AVAILABLE",
    "activeFaults": ["LIDAR_SENSOR_FAILURE"],
    "lidar": {"distanceMeters": 20, "sensorAvailable": true},
    "sourceTimestamp": "2026-01-01T00:00:00.000Z",
    "lastEventId": "vehicle-002-s1-0",
    "sessionId": "session-1",
    "sessionGeneration": 1,
    "sequence": 0,
    "frame": 100,
    "recoveryState": "IN_PROGRESS",
    "recoveryStartedAt": "2026-01-01T00:00:00.000Z",
    "sourceSilent": false
  }
  ```

  An unknown ID returns 404. Missing, malformed, unreadable or excessively
  future state returns `availability: "UNAVAILABLE"` with identity and
  explicit null observation fields. Trusted source age through 5 s is
  AVAILABLE, above 5 through 30 s is STALE, and above 30 s is UNAVAILABLE.
  An aged trusted projection retains its last-known data. Silence, sensor
  validity, recovery and availability are independent display fields.
- `GET /api/v2/fleet` returns `generatedAt`, the same top-level count names
  as V1, and three sorted `vehicles` with the full V2 state shape. One
  healthy, one warning and one critical AVAILABLE entry yields
  `totalVehicles=3`, `availableVehicles=3`, `staleVehicles=0`,
  `unavailableVehicles=0`, and `healthyVehicles=warningVehicles=criticalVehicles=1`.
  Only AVAILABLE entries count toward severity. Treat `generatedAt` as the
  point in time at which the whole fleet was evaluated.

Spring reads whole Things using the existing configured Ditto read endpoint,
credentials and HTTP timeouts (`SDV_V1_DITTO_BASE_URL` and the corresponding
V1 Ditto properties). Individual V2 reads require matching Thing, attribute
and feature identities and trusted V2 properties. V1 fields and endpoints
remain available. Run the backend against an explicit whole-Thing HTTP
substitute for offline use. The mock preview API is separate.

## Writer selection and rollback

With writing disabled, the fleet API derives a V2 view on demand. With the
sole writer enabled and `SDV_FLEET_VERSION=v2`, the same summary served by
the API is the payload attempted at
`/api/2/things/sdv:fleet-v2/features/summary/properties`. Before the first
scheduled refresh the API derives a view on demand. After that it serves the
most recent scheduled derivation, including on persistence failure. A failed
write can leave Ditto behind the API until the next successful attempt.
Individual state routes read independently. Existing fleet writer credentials,
intervals and timeout settings still apply.

Keep the writer disabled until the target and least-privilege policy are
provisioned. Enable one writer replica with `SDV_V1_FLEET_ENABLED=true`.
The default target is `v1`. Selecting `v2` changes the sole target and
does not write fleet-v1. Choose `v1` again to roll back targeting, or disable
writes. Existing Things remain. Joined rollout and policy review are pending.

## Verification boundaries

Used Ankit's verification-before-completion v1.0.0 to trace whole-Thing
validation, clock boundaries, count invariants and failed PUT handling to
observed results. No versioned Ankit TDD derivative was available.

- From `backend/`, JDK 21 and
  `bash ./mvnw -o -q -Dtest=V2FleetProjectionTest test` passed four
  component tests before the final recovery count assertion. The full
  verification below ran the final test set.
- `python -m scripts.v2_dev.check` exited 0 with 8 prep tests and 23 fixture
  files and guide links checked. The fleet component tests use literal
  shared expected counts and real Spring routes against a local HTTP
  substitute for Ditto's whole-Thing read and fleet summary write.
- `git diff --check origin/main HEAD` passed. Reviewed V1 route and DTO
  compatibility and the single writer selection.

Real Ditto policy, Bayan's live V2 individual twins, and joined V2 fleet
agreement are pending. No production or CARLA services were started.

Final JDK 21 check from `backend/` with loopback permission,
`bash ./mvnw -o --batch-mode --no-transfer-progress clean verify`, exited 0.
Maven reported 213 tests, zero failures, zero errors and zero skips and
packaged the backend. The suite includes existing V1 transport header,
authentication, configuration, controller and fleet materialization checks.
The contract link above resolved from this evidence directory.
