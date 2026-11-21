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
