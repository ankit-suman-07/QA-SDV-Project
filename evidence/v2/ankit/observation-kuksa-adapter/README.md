# V2 observation adapter offline handoff

Starting main `585c2e9bd1b453d7f6725b9d5b254bab13b30cb5`.
Tested code `c8fd78306a0e5cf1b38741d1635c9caaa50d2ecd`.
PR #55 merged as a proposal. Its review and comment records were empty, and
the merged [binding record](../../../../docs/v2-ankit-preparation-baseline.md)
still requires affected-owner agreement before production wiring.

## Emmanuel and Bayan handoff

Run `python -m scripts.v2_dev.replay --ack-development-only --sequence recovery --vehicle vehicle-003`.
For offline mapping pass the JSON-encoded record payload, `vehicle_id="vehicle-003"`,
the existing `tests/fixtures/v2/observations/session-manifest.json` as a decoded
manifest, and the parsed record evaluationTime as `now` to
`scripts.v2_dev.observation_mapping.prepare_observation`. Pass the last accepted
envelope for that vehicle as `previous` on subsequent calls. For session rollover
supply the trusted successor manifest while carrying forward the old watermark.
The first sample yields the unchanged envelope for `vehicle-003-s1-0` and
these values:

```json
{
  "Vehicle.Automation.Lidar.Front.IsHealthy": true,
  "Vehicle.Automation.Lidar.Front.NearestObstacleDistance": 3.0
}
```

An unavailable sample yields only the validity path with boolean false.
The pure mapper returns no values for an exact latest retry. It checks source
UTC against the manifest at datetime precision, checks processing time as UTC,
and rejects source time more than one second ahead. Aged replay retains its
original timestamp. A live sender will need durable registration and ordering
state, reviewed clock precision, and an explicit decision on when a delivery
advances the watermark.

Emmanuel needs to provide the actual motion input contract, including units
and how it matches observation identity/time. The shared envelope has no
velocity or speed. This mapping emits LiDAR values only and leaves V1
publication and its legacy psi conversion on their existing path. Bayan's
consumer receives the original C2 envelope as a proposed handoff once approved.

The proposed live order is successful KUKSA acknowledgement followed by the
companion publication. Broker failure suppresses the companion, and companion
failure after a broker write can leave a detectable gap. Ankit and Bayan need
to settle broker source timestamp and metadata support, ACLs, registration,
reconnect and partial-failure retry behavior before wiring. Emmanuel reviews
real source mapping and clock parameters. Broker and companion failure tests,
real broker publication and CARLA acceptance are blocked by the unapproved
binding. No owned services were started.

## Verification

Applied Ankit verification-before-completion v1.0.0 to tie C1/C2/C4 tests to
observed results, revision and boundaries. Used the repository test-first
workflow. No Ankit versioned TDD derivative was available.

- `python -m unittest tests.test_v2_observation_mapping -q` initially failed to
  import the absent mapper, then passed as the implementation and cases were
  added. Final combined command `python -m unittest tests.test_v2_observation_mapping tests.test_v2_http -q`
  passed 7 tests, exit 0. Initial sandbox run denied the loopback socket;
  permitted retry passed. The mapper tests exercise all three targets, wrong
  target, JSON/shape/time errors, dropout, retry/order and session rollover.
  HTTP is a separate existing substitute check.
- `python -m scripts.v2_dev.check` passed 8 tests and checked 22 synthetic
  fixture files and local guide links, exit 0.
- The replay command above was fed to the mapper using each record's injected
  clock and the prior envelope. Seven vehicle-003 samples mapped to 3.0 m
  then six 20.0 m readings with original identity/time, exit 0. Synthetic
  component check with no KUKSA or MQTT.
- `git diff --check origin/main HEAD` passed. Self-review confirmed the
  mapping has no network or production entry point.
- Python 3.12 CI-equivalent suite. Generated the five protobuf modules into a
  temporary directory with `python -m grpc_tools.protoc -I uprotocol/proto --python_out="$test_dir" uprotocol/proto/{common,health_status,vehicle_status,vehicle_fault,vehicle_diagnostic}.proto`
  and ran `PYTHONPATH="$test_dir" python -m pytest -q -ra -m "not integration"`
  with loopback permission. Exit 0, 567 passed, 456 subtests passed, 2 skipped
  (V1 MQTT host and native SDK unavailable), 9 deselected. The original
  sandboxed run had failures/errors while the permitted run passed.

## Publication continuation

The offline-only blocker above describes the original draft revision. Ankit
Suman explicitly authorized implementation of the companion, confirmed-write
ordering, durable retries, optional motion and the silence ownership rules
in the PR #56 continuation instruction. Bayan and Emmanuel have pending
affected-owner review. See the [updated decision record](../../../../docs/v2-ankit-preparation-baseline.md#authorized-observation-companion-binding).

Tested implementation `760afaa0759715b6720a7de8c711a4fa0ad219ee`. Applied
Ankit verification-before-completion v1.0.0 to map C1/C2/C4/C5 to the
negative cases, client response proof, isolated component check and limits
below. No versioned Ankit TDD derivative was available and no paired skill
evaluation is claimed.

### Configuration and source handoff

Install the existing pins with
`python -m pip install -r vehicle-simulator/requirements.txt -r ditto/requirements-mqtt.txt`.
The publisher uses KUKSA Client 0.5.1 and Paho MQTT 2.1.0. No pins changed.
Run one process for each registered vehicle on Linux. Give all local
instances the same private persistent state directory and use one dedicated
writer/credential set per vehicle. Disable the V1 synthetic writer for any
broker assigned to the V2 adapter. Across hosts, enforce one active owner per
vehicle through deployment and per-target KUKSA/MQTT grants. The local file
lock prevents duplicate processes sharing the configured state directory.
It cannot fence independently configured hosts or directories.

Copy the [manifest example](../../../../tests/fixtures/v2/observations/session-manifest.json)
and configure its trusted registry with all three vehicle IDs, distinct
broker host/port pairs, registered session and exact UTC/simulation origin.
For example, use loopback broker ports 55556, 55557 and 55558, with local
Mosquitto at 1883. Use `--kuksa-ca` and `--mqtt-ca` for non-loopback
endpoints. For authenticated deployments supply `SDV_KUKSA_TOKEN` and
`--mqtt-user` with `SDV_MQTT_PASSWORD` through local secret configuration.
The MQTT client requires MQTT 5 and uses a clean start with no persistent
offline queue.

```bash
python -m scripts.v2_dev.observation_publisher \
  --vehicle vehicle-001 --manifest ./trusted-session.json \
  --state-dir ./local-adapter-state --mqtt-host 127.0.0.1 --mqtt-port 1883 \
  < ./vehicle-001-observations.jsonl
```

Emmanuel feeds one original compact C2 observation per UTF-8 JSON line.
The replay tool's outer topic/evaluationTime record is for its offline
harness. Feed its payload alone when intentionally checking against isolated
brokers. The [motion fixture](../../../../tests/fixtures/v2/observations/vehicle-001-motion.json)
supplies `velocityMetersPerSecond: {"x":3,"y":-4,"z":0}`, which yields
`Vehicle.Speed` float 18.0 km/h, LiDAR 20.0 m, boolean validity true and the
original envelope on `sdv/vehicle-001/v2/observations`. Missing motion omits
the speed write. Dropout writes false validity and omits distance, so consumers
must ignore any cached distance. This publisher emits no supporting battery,
temperature or tire telemetry. V1 retains its existing synthetic signals and
psi conversion. Emmanuel's actor/extractor changes remain his handoff.

### Ordering, failure and restart

Each vehicle keeps a SQLite pending record, KUKSA-confirmation phase, completed
watermark and used event IDs. Keep the journal across restarts. Its event ID
ledger grows with accepted observations. Drain the pending observation before
changing endpoint mappings or session manifests. Restart first resumes the
pending observation, then accepts new input. Upstream observations not yet
journaled need replay if lost. A malformed or mismatched record has no
publication side effects. An overlong input line stops the process to avoid
treating its tail as another record.

KUKSA metadata checks validate the expected types and units. The pinned
client's explicit VAL v1 Set checks top-level and per-path errors. The public
convenience method can fall back from VAL v2 without carrying the deadline,
so the publisher selects VAL v1 directly. Each RPC and MQTT connection or
acknowledgement wait has a 2 s bound, with up to three attempts per phase
and 0.25/0.5 s retry waits. OS name resolution is external to the socket
timeout. Failure closes the corresponding client before reconnect. If
attempts exhaust, the process exits nonzero with the pending state intact.

Incomplete or uncertain KUKSA writes cannot advance completion or emit a
companion. A retry may rewrite signals already applied in a partial batch.
After KUKSA confirmation is journaled, retry resumes at MQTT. If the process
dies before journaling that confirmation, it reruns the same KUKSA write.
A lost PUBACK or crash before persisting completion can redeliver the original
companion. QoS 1 confirms broker acceptance rather than consumer processing.
The consumer must deduplicate. No atomicity spans KUKSA, MQTT and SQLite.

Bayan's consumer uses the companion for original identity and source UTC.
The 100 ms Velocitas silence evaluation, separate versioned status schema and
ingress ordering remain Bayan's handoff. The status must retain last real
identity/time. Cached, rejected and duplicate deliveries cannot reset silence
or advance recovery. Backend freshness remains independent of status.

### Verification of the continuation

- Focused Python tests exercised MQTT disconnect/negative acknowledgement,
  unchanged retry and completed duplicate, pending restart, wrong target,
  per-path KUKSA rejection and reconnect, metadata mismatch, dropout and speed.
  `python -m pytest -q tests/test_v2_observation_mapping.py tests/test_v2_observation_publisher.py vehicle-simulator/tests/test_kuksa_publication.py`
  returned 12 passed and 19 subtests passed. Nine existing V1 live tests were
  deselected by the non-integration default.
- `python -m scripts.v2_dev.check` passed 8 tests and 23 fixture/link checks.
- `git diff --check origin/main HEAD` passed.
- Python 3.12 CI-equivalent suite used the same five generated protobuf
  modules and command documented above, with loopback permission. Exit 0,
  573 passed, 461 subtests passed, 2 skipped (V1 MQTT host and native SDK),
  and 9 V1 integration tests deselected.
- `bash evidence/v2/ankit/observation-kuksa-adapter/component-check.sh`
  used temporary loopback KUKSA 0.7.0 and Mosquitto 2 with the existing VSS.
  Exit 0. Read back 20.0 m, true validity and 18.0 km/h. Actual MQTT subscriber
  received the byte-identical envelope at QoS 1, retain false, and a completed
  retry after publisher restart emitted nothing. The source was
  `2026-01-01T00:00:00.000Z`. KUKSA readback used broker time
  `2026-11-21T03:51:10.627Z` (individual writes differed below a millisecond).
  The SDK test verified the original timestamp in every outbound VAL Set
  entry, and MQTT retained the original timestamp. This used synthetic input
  with real components, without CARLA or Velocitas. Both temporary containers
  were stopped. Joined three-vehicle CARLA/Velocitas, production TLS/ACLs and
  owner review remain pending.
