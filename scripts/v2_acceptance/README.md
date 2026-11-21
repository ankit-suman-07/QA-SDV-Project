# V2 local acceptance handoff

This runbook and trace checker assume reviewed owner entry points. The
checker reads captured data and never starts, stops, or authenticates to a
service. Capture first on an isolated host or test namespace. Follow the
[contracts](../../docs/v2-interface-contracts.md) and
[independent development guide](../../docs/v2-independent-development.md).

## Pin and isolate the run

1. Record the exact Git SHAs for the extractor, publisher, Velocitas,
   ingress, backend and dashboard. Record CARLA server/client versions,
   architecture, map, seed, actor/sensor IDs, episode, sensor settings,
   synchronized UTC origin and simulation origin in the owner's run manifest.
   Record image digests and inspect the locally running image IDs. Pin
   KUKSA 0.7.0, Ditto 3.8.4 and a specific Mosquitto 2 digest, using the
   [inventory evidence](../../evidence/v2/ankit/three-vehicle-integration/README.md)
   as candidate pins for this host. Record all resolved images, including
   Ditto dependencies. Do not assume a cached V1 app is a reviewed V2 app.
2. Use a unique Compose project, e.g. `sdv-v2-acceptance-<run>`, and a
   private, durable directory for manifests, journals and mounted config.
   Record the project, Compose file paths, actual container identities,
   and owned processes before testing. Reserve these example loopback
   ports only after checking for conflicts:

   | Target | KUKSA (internal 55555) | Scenario provider | Individual Thing |
   |---|---:|---:|---|
   | vehicle-001 | 55556 | 8091 | sdv:vehicle-001 |
   | vehicle-002 | 55557 | 8092 | sdv:vehicle-002 |
   | vehicle-003 | 55558 | 8093 | sdv:vehicle-003 |

   Example shared loopback endpoints are MQTT 18884, Ditto 18080 and
   Spring 18082. Set the publisher manifest broker/port fields per row
   and pass `--vehicle`, `--manifest`, `--state-dir`, and `--mqtt-host/--mqtt-port`
   using the [adapter handoff](../../evidence/v2/ankit/observation-kuksa-adapter/README.md#publication-continuation).
   Configure `SDV_V1_DITTO_BASE_URL` for the selected test Ditto ingress.
   Enable exactly one backend fleet writer with `SDV_FLEET_VERSION=v2`
   after provisioning the scoped direct writer. Use the
   [backend](../../evidence/v2/ankit/backend-fleet/README.md),
   [action](../../evidence/v2/ankit/diagnostic-action-tracking/README.md), and
   [dashboard](../../evidence/v2/ankit/dashboard/README.md) handoffs for
   service settings, route auth and the same-origin gateway.
3. Keep tokens, policies and certificates in permission-restricted local
   files or the local secret mechanism. Record secret references and grants
   without values, raw authorization headers, browser cookies or full
   environment dumps. If CARLA is remote, record the chosen LAN addresses,
   owner endpoints, authenticated TLS boundary and measured UTC sync/skew
   and uncertainty on both hosts. Reject clock rollback and confirm registered
   episode generation before starting. Do not expose the loopback mock ports
   on LAN. Check one publisher per active vehicle, and ensure Docker and
   Kanto do not both publish for the pilot vehicle.
4. After the run stop only recorded owned PIDs or the unique Compose project
   with its exact files, for example
   `docker compose --project-name "$sdv_v2_project" -f "$sdv_v2_compose" stop`.
   Confirm its resources with `docker compose --project-name "$sdv_v2_project" -f "$sdv_v2_compose" ps -a`.
   Retain journals and volumes. Record before/after status and untouched peers.
   The required owner stack is presently incomplete. There is no full-stack
   Compose file to launch from this branch.

## Capture and verify

Prove one real actor first, then all three in a separate run or capture window.
After owner setup, obtain whole Thing and API responses using the deployment's
authorized client and a request deadline. Save source extraction and KUKSA
write/read observations, read-only MQTT captures, individual twin properties,
Spring state responses, and a browser capture. Retain raw sanitized artifacts
and link them to normalized JSONL. Do not treat a connection check as acceptance.

Each JSONL line is `{"boundary":"source","payload":{...}}` with the selected
payload; the boundaries are:

| Boundary | Payload |
|---|---|
| source | Original compact CARLA envelope |
| kuksa | Adapter-correlated vehicleId/eventId/sourceTimestamp, observed VSS values in `signals`, and `allWritesConfirmed:true` from the writer evidence |
| companion | MQTT envelope with `topic` as an additional top-level JSONL field |
| health | MQTT Velocitas envelope with `topic` as an additional top-level JSONL field |
| twin | `features.v2.properties` plus the actual whole-Thing `thingId` |
| api | Selected Spring V2 state response |
| browser | Displayed vehicleId, thingId, lastEventId, sourceTimestamp, availability, base healthStatus and recoveryState |

Capture the KUKSA signal map against the acknowledged write, preserving the
actual broker timestamp separately. KUKSA 0.7.0 may use its write clock
on readback. Source identity and UTC originate in the companion. Use a
controlled capture window when attributing a broker readback to a selected
write. Capture each API/browser projection once for each chosen event and
evaluation window. Reuse identical duplicated messages or use separate files
for repeated age transitions on the same event. The verifier joins on
vehicle and event, compares preserved observation context, and never uses
capture time or fleet generatedAt as observation identity. A browser
projection must match the corresponding meaning of the API state, including
availability. Retain original DOM/screenshots separately.

The owner manifest uses the [session mapping shape](../../tests/fixtures/v2/observations/session-manifest.json),
with the real UTC anchor and all three broker mappings. In the first phase,
actorId/sensorId may be null for the inactive vehicles. Use actual assigned
IDs for every vehicle in the three-actor phase:

```bash
python -m scripts.v2_acceptance.verify_trace --manifest "$sdv_run_manifest" --trace "$sdv_one_trace" --vehicle vehicle-001
python -m scripts.v2_acceptance.verify_trace --manifest "$sdv_run_manifest" --trace "$sdv_three_trace" --all-vehicles
```

Exit 0 means the supplied captures join, exit 1 means corrupt/mismatched
input, and exit 2 means missing capture or incomplete join. The checker
does not attest who produced the artifacts or exercise the transport itself.
Use `--synthetic` only for test fixtures. Live input rejects fixture/mock
markers and requires CARLA source provenance. Record runtime commands,
exits, capture paths, scope, SHA, and cleanup in the evidence directory.

## Manual acceptance after the owner handoffs

| Gate | Record |
|---|---|
| Targeted inject/clear and two-second recovery | Executor and CARLA ground truth for the selected actor, fault and clear event IDs, first healthy source time, and first clearing time. Observe prior severity through IN_PROGRESS and at least two continuous seconds with no gap over 0.5 s. Peers retain their identities, watermarks and unaffected health. |
| Dropout, source silence and freshness | Invalid sensor publishes false/null with original identity. Suppression produces no new observation. Evaluate silence via Velocitas's status boundary once reviewed, and observe the independent API source age crossing 5 s and 30 s. Browser labels retained values. |
| Ordering, persisted watermark and denied writes | On an isolated target, capture pre/post twin feature and watermark for malformed, cross-target, duplicate, late and retired-session input. Reopen ingress with the same state, prove rejection of replay and acceptance of a registered successor. Test a deliberately insufficient test principal or controlled dependency failure. Observe denied/failed write without committed watermark/history advancement and recovery with authorized input. |
| Fleet and browser | Sample fleet API and materialized summary from the same generatedAt. Keep all three sorted and compare literal counts and browser display. Use event/source identity for separately sampled individual reads rather than requiring time equality. |
| Real action, diagnostic and Kanto | Capture correlated successful, failed and timed-out executor results plus late evidence. Run native selected-vehicle uProtocol and supported OpenSOVD against authoritative project data, using Bayan's approved mappings and credentials. Coordinate same-device Kanto lifecycle with real CARLA and no overlapping publisher. Capture lifecycle times, fresh post-start observation, matching event through the twin, and unaffected peers. A managed restart gives no crash auto-restart evidence. |
