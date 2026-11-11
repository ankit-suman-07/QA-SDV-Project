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
decoded objects or imposing that wire budget on persisted state. Ditto PUT bodies
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
errors are persistence failures, never acknowledgments of rejected input.

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
