# B1: V1 MQTT ingress

Development baseline: `docs/v1-interface-contracts.md` 1.0.0, C2-C6,
and `docs/10-detailed-task-distribution.md`, B1. This component supports V1-02;
unit checks do not establish live two-vehicle acceptance.

`mqtt_ingress.py` strictly decodes and validates events, checks the two exact
topic/vehicle mappings, and serializes writes separately per vehicle. It preserves
source time and command context. Optional extension fields are preserved. It
checks classification against C4 without substituting its own classification for
the publisher's result. It never writes processing time or availability.
Only `decode_event` applies the 64 KiB MQTT budget to original UTF-8 bytes.
`validate_event` shares all semantic checks with the B2 writer without serializing
decoded objects or imposing that wire budget on persisted state. Text values and
object keys, including extensions and context IDs, must contain Unicode scalar
values: escaped lone high/low surrogates reject with MALFORMED_JSON. Valid escaped
surrogate pairs decode to non-BMP characters and remain supported. Validation
walks nested containers iteratively and rejects non-finite values and cycles.
`decode_event` also preflights the UTF-8 persistence encoder before enqueueing;
this does not reapply the wire-size budget to the encoded result. Ditto PUT bodies
are compact UTF-8 JSON; Unicode is not unnecessarily expanded to ASCII escapes.

`mqtt_subscriber.py` uses Paho MQTT 2.1.0, MQTT 3.1.1 and a persistent session.
It subscribes to `sdv/+/health` at QoS 1 on every successful connection, checks
SUBACK, and reconnects with a 1-30 second backoff. Use one stable, unique client ID
and a persistent broker. Do not run multiple ingress writers for these twins.
Retained messages and QoS 0 deliveries are rejected.

## Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| SDV_MQTT_HOST | localhost | Broker host |
| SDV_MQTT_PORT | 1883 | Broker port |
| SDV_MQTT_CLIENT_ID | sdv-v1-twin-ingress | Stable persistent-session identity |
| SDV_MQTT_USERNAME | unset | Optional broker username |
| SDV_MQTT_PASSWORD | unset | Local secret; requires username |
| SDV_MQTT_TLS_CA | unset | CA certificate file; enables verified TLS |
| SDV_MQTT_KEEPALIVE | 60 | Keepalive seconds |
| SDV_MQTT_QUEUE_SIZE | 100 | Maximum queued messages per vehicle |
| SDV_MQTT_RETRY_SECONDS | 1 | Delay between downstream recovery attempts |

Use `python -m pip install -r ditto/requirements-mqtt.txt` in an approved
Python 3.12 environment. Domain validation has no third-party dependencies.
The legacy bridge and HTTP helpers remain unchanged: their polling, property
writes and retry semantics are not reused for the MQTT persistence transaction.
No production module imports `scripts/v1_dev`.

## B2 integration boundary

B2's `DittoWriter` in `v1_writer.py` implements the `TwinWriter` protocol in
`mqtt_ingress.py`. See [V1-TWINS.md](V1-TWINS.md) for authenticated startup,
create-only provisioning, read commands and live verification:

* `load_watermark(vehicle_id)` reads and validates the live Thing, attributes and
  V1 feature identities/schema, returning `(lastEventId, sourceTimestamp)`.
  Return `None` only for a verified, provisioned individual twin with no V1 state.
  Missing, unreadable or corrupt twins must raise; a failed read is never empty state.
* `persist(vehicle_id, properties)` maps to the allowlisted individual Thing and
  atomically replaces `/features/v1/properties`. It returns only after confirmed
  success and raises on failure or uncertain outcome. B2 owns HTTP timeouts,
  bounded HTTP retries, authentication and provisioning. Never overwrite the
  whole Thing or legacy features. The supplied snapshot renames `eventId` to
  `lastEventId`, retaining `vehicleId`, `sourceTimestamp` and optional context.

Wire the real adapter explicitly; there is no default mock or no-op writer:

```python
from ditto.mqtt_ingress import Ingress
from ditto.mqtt_subscriber import MqttConfig, Subscriber
from ditto.v1_writer import DittoConfig, DittoWriter

writer = DittoWriter(DittoConfig.from_env())
subscriber = Subscriber(Ingress(writer), MqttConfig.from_env())
try:
    subscriber.run()
except KeyboardInterrupt:
    subscriber.stop()
```

The committed watermark advances only after `persist` returns. A read/write
failure leaves the current message unacknowledged, logs `persistence_pending`,
and retries that message before later messages for the same vehicle. The other
vehicle has its own worker. Transport ACK follows successful persistence;
invalid, duplicate and late events are logged and acknowledged as rejected so
they do not become poison-message loops. Duplicate latest IDs never overwrite
state, even if their payload changed. Equal source timestamps are rejected.
Ordering preserves ISO fractional precision beyond microseconds. A failed write
invalidates the cached watermark: the next attempt first reloads the live twin,
because a timed-out request may already have been applied. Downstream validation
errors from reads/stored-state validation remain persistence failures, never
acknowledgments of rejected input. The narrow `LocalJSONError(EventError)` exception
identifies deterministic serialization failure **before HTTP dispatch**. It is
rejected/ACKed without retry or watermark advancement. It must never be used for
an HTTP response, timeout, connection failure or any uncertain write outcome.

The queues are bounded; overflow or subscription/ACK failure visibly stops the
subscriber without acknowledging queued work. Restart it after fixing the cause.
Connection generations prevent completed work from acknowledging a reused message
ID on a newer connection. A successful write before a lost ACK is safe to replay
because the live twin watermark rejects its duplicate after restart.

`stop()` leaves unfinished work unacknowledged. B2 must use bounded network calls
so workers can finish promptly; shutdown waits up to two seconds per worker and
logs any still-running writer. `wait_idle()` drains while running and can block
during an outage; do not call it after stopping.

MQTT delivery still depends on publisher QoS 1, stable sessions, broker persistence
and broker queue limits. This component does not promise an offline spool or
unlimited broker retention. Source age/future-clock availability is evaluated by
Ankit's backend; ingress preserves the original source timestamp.

## Verification

From the repository root, with Python 3.12 and pytest available:

```powershell
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_mqtt_ingress.py tests/test_mqtt_subscriber.py
```

Tests use existing V1 fixtures, a fake writer and a fake MQTT transport. One
additional test instantiates the real Paho client and checks version-2 callback
reason codes when the optional dependency is installed. No test here proves
live Mosquitto delivery, real Ditto persistence, policy enforcement or a full
Emmanuel-to-Ankit pipeline. A subsequent live integration run remains needed.
Fleet counting/provisioning/materialization belongs to Ankit A5.


## PR30-F01/F02 correction evidence (November 12, 2026)

Read authoritative documentation and review findings from fetched `origin/main`
`8e9566ed3fe24f75889325aa867e4395019f350b`, without merging/rebasing. Contract
1.0.0 remains proposed for affected-owner review. A5 remains Ankit's responsibility.

The 600-level extension previously passed validation then failed recursive
`deepcopy`, entering persistence retry forever. Event-to-properties copying now
uses the existing strict JSON codec without a byte budget, before watermark reads;
the returned event and writer properties remain independent. B2 only needs a
shallow envelope copy to rename lastEventId while validating stored properties;
its validation never mutates nested data. No recursive deepcopy remains in either
production path. The shared compact UTF-8 encoder returns a controlled
LocalJSONError for local encoding failures instead of reporting a Ditto outage.
The subscriber's existing input-rejection handler is retained; generic downstream
errors still invalidate the cached watermark and retry without ACK.

No new shared numeric depth limit is introduced. The standard-library JSON
parser/encoder still have runtime-specific nesting limits; unsupported shapes
produce controlled MALFORMED_JSON / LocalJSONError, not a raw local RecursionError.
Tests cover arrays/dictionaries at 599, 600, 601 and 1400 levels. The original
assumption that 5000 levels always exceed codec capacity was incorrect across
runtimes; see the CI correction below. These are test cases, not advertised
protocol depth limits.
A deployment-wide depth guarantee (including Ditto and Ankit's HTTP/JSON clients)
requires affected-owner agreement and target-runtime verification. Unbounded input
or universal decoder compatibility is not promised.

The UTF-8 writer requires scalar text, so ingress rejects lone surrogates in both
keys and values. PR #31 is a read-only decoded-snapshot consumer whose existing
surrogate acceptance is explicitly pending affected-owner policy review. Ordinary
Unicode, non-BMP text, fixtures, identity, ordering and classification remain
compatible; do not claim that every snapshot accepted by #31 is UTF-8 serializable.
No #31 production code is imported or changed by this correction.

Initial Python 3.12.10 verification (mock/component only; updated CI correction below):

- Added regressions first reproduced the deep-copy/retry and surrogate failures.
- Focused command below: **64 passed, 66 subtests passed**.
- Full repository pytest attempted: collection stopped at four modules missing
  common_pb2 / kuksa_client. Three are transport modules; one is the KUKSA
  publication module. No installation was attempted.
- Available regressions: **212 passed, 284 subtests passed**, explicitly ignoring
  those four modules and selecting `-m "not integration"`.
- A read-only in-memory compatibility probe against PR #31's corrected verifier
  passed for four fixture events: both vehicles, healthy/fault/recovery, 600-level
  extensions, Unicode command context and duplicate polls. It added no dependency
  or source file from #31 to this branch.
- AST syntax, tracked JSON parsing, targeted secret scan and `git diff --check`
  passed. Fresh CI and live MQTT/Ditto acceptance remain pending.

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_mqtt_poison_inputs.py tests/test_mqtt_ingress.py tests/test_mqtt_subscriber.py tests/test_ditto_v1_writer.py tests/test_ditto_v1_cli.py
.\.venv-b1\Scripts\python.exe -X utf8 -B -m pytest -q -ra -p no:cacheprovider -m "not integration" --ignore=tests/test_uprotocol_transport.py --ignore=uprotocol/tests/test_extended_transport.py --ignore=uprotocol/tests/test_transport.py --ignore=vehicle-simulator/tests/test_kuksa_publication.py
```

New tests use in-memory HTTP and fake MQTT, finite synchronization waits, invalid
input floods with a one-slot queue, later events for both vehicles, restart/late
checks and genuine HTTP 503 retry/ACK gating. Existing exact-64-KiB and near-limit
Unicode persistence/restart tests remain unchanged. Existing loopback HTTP tests
use only a temporary mock server, not Eclipse Ditto. No live runtime services were
contacted, dependencies installed, or files staged/committed/pushed.

Applied the actual repository systematic-debugging, test-driven-development and
verification-before-completion skill sources under `skills/`. Referenced supporting
writing-good-tests/debugging files and a separate review skill are absent; their
use is not claimed. `.venv-b1/` remains local, untracked and unstaged.


## CI correction: runtime-dependent nesting expectations

Two subsequent CI assertion failures shared one test-data defect: a valid,
under-budget 5000-level extension was assumed to be invalid on every Python
runtime. The local Python 3.12.10 codec rejects it, while the reported CI codec
accepts it. CI selects floating Python `3.12`; it does not promise a fixed JSON
nesting capacity. Both exact assertion failures were independently reproduced on
the already-installed Python 3.15.2, whose codec also accepts the extension.
No Python 3.12.16 interpreter was available for a direct local run.

The flood's message 19 was that valid event. It entered the vehicle worker and
correctly had no immediate rejection ACK: successful persistence must precede
its ACK. Waiting longer for a rejection ACK would leave the incorrect no-writer
expectation intact. Production ingress, subscriber, Ditto writer and CI remain
unchanged by this correction; no depth restriction or broader ACK rule is added.

Test corrections and added evidence:

- The invalid-input flood uses genuinely malformed deep arrays/objects (trailing
  comma / invalid token), all below 64 KiB. Every invalid delivery must still be
  rejected/ACKed synchronously without any worker call, HTTP request, watermark
  advance or queue overflow. Later valid events for both vehicles must persist.
- The codec-limit test injects RecursionError independently at the actual JSON
  decoder and encoder for arrays and objects. It verifies MALFORMED_JSON before
  HTTP/watermark access, then verifies progress for both vehicles. No numerical
  rejection threshold is assumed, and no test is skipped.
- A real 5000-level extension test checks the native codec's capability: where
  supported it must persist, preserve its leaf, recover its watermark on restart
  and reject a duplicate. Where the native codec itself raises RecursionError,
  ingress must reject with a controlled error and no I/O. Both paths must allow
  subsequent events for both vehicles.
- A blocked-PUT test explicitly withholds ACK for a supported deep message 19,
  lets vehicle-001 progress, then releases persistence and verifies vehicle-002's
  next event. It uses bounded synchronization instead of immediate worker-ACK
  assumptions. Older persistence-failure/uncertain-write tests remain intact.
- The prior-state rejection test now requires MALFORMED_JSON for malformed deep
  input; a DUPLICATE_EVENT can no longer mask the incorrect depth assumption.

Fresh verification after correction, all static/mock/component only:

- Both formerly failing tests: 20 consecutive runs each on Python 3.12.10 and
  Python 3.15.2, **80 executions passed**.
- Python 3.12.10 focused suite: **66 passed, 72 subtests passed**.
- Python 3.12.10 available regressions: **214 passed, 290 subtests passed**.
- Additional Python 3.15.2 unittest probe: **all 12 poison-input tests passed**,
  including accepted 5000-level arrays/objects and persistence-gated ACKs. This
  reused installed pure-Python test dependencies; no installation was performed.
- Full Python 3.12 collection still stops at the four local common_pb2 /
  kuksa_client dependency blockers listed above. These are separate from the
  reported CI assertion failures, where collection completed.
- Syntax and `git diff --check` passed. No staging, commit, push, deployment or
  live-service access was performed. The local environment remains preserved.

Fresh supported-patch GitHub Actions, affected-owner shared-interface review and
real MQTT/Ditto acceptance remain pending. The 3.15 probe demonstrates the runtime
variation and exercises both codec capability paths; it does not replace 3.12 CI.
