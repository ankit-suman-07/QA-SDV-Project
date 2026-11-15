# B2: two isolated individual Ditto twins

Baseline: `docs/v1-interface-contracts.md` v1.0.0, C2/C3/C5/C6, and
`docs/10-detailed-task-distribution.md` B1/B2. Supports V1-02 and the individual
twin boundary for V1-03/04/08. Ankit A5 owns all fleet provisioning/counting/writes.

`v1_writer.py` implements authenticated whole-Thing reads and one atomic
`PUT /api/2/things/{thingId}/features/v1` per accepted observation. Initial writes
use `If-None-Match: *`; later writes target only `/features/v1/properties`, preserving feature metadata
and the existing properties-only authorization boundary. They use the ETag from
an authenticated properties GET in `If-Match`. A conflict invalidates the ingress
watermark cache and requires a fresh read before retry. Feature-level READ/WRITE
permissions are required; production principal approval remains open.
`v1.py` wires it to the B1 subscriber; no fake writer or generated healthy fallback
exists. Legacy bridge/configuration/features are preserved. Shared strict JSON
decoding and event validation come from the production `mqtt_ingress.py` module,
never from development mocks. The legacy `ditto_http.py` helpers remain unchanged
because they do not provide the authenticated GET/status retry semantics needed.

| vehicleId | Thing ID | Policy ID |
|---|---|---|
| vehicle-001 | sdv:vehicle-001 | sdv:vehicle-001-policy |
| vehicle-002 | sdv:vehicle-002 | sdv:vehicle-002-policy |

## HTTP configuration

All values come from the process environment; `.env` is not loaded automatically.

| Variable | Default | Meaning |
|---|---|---|
| SDV_DITTO_BASE_URL | http://localhost:8080 | HTTP(S) origin or deployment prefix, before `/api/2` |
| SDV_DITTO_USERNAME | required | HTTP Basic username |
| SDV_DITTO_PASSWORD | required | Local secret; no committed default |
| SDV_DITTO_TIMEOUT_SECONDS | 2 | Per-request connect/read timeout |
| SDV_DITTO_ATTEMPTS | 3 | Maximum attempts per HTTP operation, range 1-10 |
| SDV_DITTO_RETRY_DELAY_SECONDS | 0.2 | Exponential retry base, each delay capped at 30 s |
| SDV_DITTO_TLS_CA | unset | Custom CA file; default verifies system CAs |

URL-embedded credentials, redirects and disabled certificate verification are not
supported. GET requires 200. Feature PUT accepts 200/201/204. Authentication 401/403,
missing resources and non-transient HTTP failures are reported without automatic
HTTP retry. Timeouts, connection failures and 408/429/500/502/503/504 have bounded
retries. TLS errors fail immediately. Logs use safe failure codes, not response
bodies, URL credentials or raw dependency exceptions. Each vehicle uses independent
requests; no mutable HTTP Session is shared across worker threads.

After a bounded HTTP failure, B1 leaves the message unacknowledged and periodically
attempts recovery. Auth/configuration failures therefore block that vehicle until
corrected; restart the process after changing its environment. They never become
successful deliveries. A 2-second timeout is per network operation, not a measured
end-to-end propagation guarantee.

## State validation and safe initialization

Read responses are strict JSON objects (maximum 1 MiB) with duplicate keys and
non-finite values and lone surrogate text/keys rejected. Whole-Thing and attribute
identities must match the requested vehicle. Existing `features.v1.properties` must match the third identity,
schema, full health/fault/LiDAR rules, source timestamp and lastEventId. A malformed,
null, empty or partial V1 feature blocks ingestion. A missing/unreadable Thing also
blocks ingestion. Only an existing correctly identified Thing with the **V1 feature
entirely absent** is allowed to receive its first observation. No initial health
or timestamp is fabricated. Freshness remains derived from the preserved source
timestamp by Ankit's backend; stale observations are not rewritten as current.

The 64 KiB limit applies only to the original MQTT UTF-8 payload bytes. Persisted
state uses the same semantic checks without an MQTT wire-size limit; the separate
1 MiB whole-response limit still applies. Ditto writes use compact UTF-8 JSON with
Unicode preserved rather than expanded to ASCII escapes. Unicode or whitespace
differences in a stored response cannot by themselves trigger the MQTT size limit.

Ingress serializes writes per vehicle. On restart it loads each watermark from
validated live state. Duplicate IDs and non-increasing source times cause no PUT.
The watermark advances only after confirmed PUT success. After a failed or
uncertain dispatched PUT it is reloaded before another attempt, covering a server
commit followed by a lost response. A deterministic local serialization failure
before dispatch is an input rejection; it makes no HTTP call and never advances
the watermark. See [correction evidence](MQTT-INGRESS.md#pr30-f01f02-correction-evidence-november-12-2026)
for deep extensions, Unicode validation, runtime codec limits and mock results.
A read failure never resets it to empty. Run only one ingress writer for these twins; multiple-writer coordination/revision locking is outside this contract.

## Reproducible provisioning and live commands

Prerequisites: running Eclipse Ditto with HTTP Basic authentication and a reachable
Mosquitto broker. Use the approved Python 3.12 environment with
`ditto/requirements-mqtt.txt` installed. Commands below are **not yet live-verified**.
They deliberately do not launch, stop or reset existing platform services.

From the repository root in PowerShell:

```powershell
$env:SDV_DITTO_BASE_URL = 'http://localhost:8080'
$env:SDV_DITTO_USERNAME = Read-Host 'Ditto username'
$dittoSecret = Read-Host 'Ditto password' -AsSecureString
$env:SDV_DITTO_PASSWORD = [System.Net.NetworkCredential]::new('', $dittoSecret).Password
$env:SDV_MQTT_HOST = '127.0.0.1'
$env:SDV_MQTT_PORT = '18883'  # match your broker; normal MQTT default is 1883
$env:SDV_MQTT_CLIENT_ID = 'bayan-v1-individual-twins'

.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 provision --subject "nginx:$($env:SDV_DITTO_USERNAME)"
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 read all
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 run
```

Use the policy subject actually supplied by your Ditto authentication proxy;
`nginx:<username>` is the stock nginx setup, not a universal identity assumption.
Set MQTT username/password and CA variables from [MQTT-INGRESS.md](MQTT-INGRESS.md)
when required. Configure the same Ditto environment in any separate read terminal.

Provision with ingress and other provisioning stopped. The command creates missing
policies first, then missing Things, using `If-None-Match: *`. Existing entities
are only read/validated; no policy, Thing, legacy feature or V1 watermark is replaced.
A creation race returning 412 is followed by a validated read.
If a create response is lost, a subsequent retry may receive 412 and trigger that
read. If the final HTTP attempt times out, provisioning exits with failure without
an immediate recovery read. Inspect and rerun provisioning: it reads and validates
any already-created resource, using create-only requests for anything still absent.
The create-only header follows [Ditto's conditional HTTP semantics](https://eclipse.dev/ditto/httpapi-concepts.html).
Existing policy bindings must match the table. Policies must explicitly grant the
configured subject READ/WRITE at `thing:/` and `policy:/`; malformed permissions or
revocations for that subject are conservatively rejected. More elaborate inherited
policies need deliberate review. New policies use the supplied subject and those
root grants. Provisioning is additive, not a cross-resource transaction: a later
failure may leave earlier creations in place, safe to inspect and rerun. An existing
resource mismatch requires manual review; provisioning never silently repairs it.

For replay into the **real broker and real Ditto**, in a second terminal (requires
existing Mosquitto CLI clients; no installation is performed by this implementation):

```powershell
$runId = 'b2-' + [guid]::NewGuid().ToString('N')
$anchor = [DateTime]::UtcNow.AddSeconds(-1).ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
.\.venv-b1\Scripts\python.exe -X utf8 -B -m scripts.v1_dev.mqtt publish --scenario healthy --host 127.0.0.1 --port 18883 --anchor $anchor --run-id $runId
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 read all
```

Before continuing, repeat the read until both twins show HEALTHY and lastEventId
`vehicle-001-event-000-$runId` / `vehicle-002-event-000-$runId` (substitute the
actual run ID). Allow up to ten seconds; stop and investigate on timeout. Save
this intermediate whole-Thing snapshot. Then publish the fault:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m scripts.v1_dev.mqtt publish --scenario fault --host 127.0.0.1 --port 18883 --anchor $anchor --run-id $runId
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 read all
```

Repeat the read until vehicle-002 is CRITICAL with `LIDAR_OBSTRUCTION` and
lastEventId `vehicle-002-event-001-$runId`. Vehicle-001 must retain its previous
state and event ID. Save this fault snapshot; stop on a ten-second timeout. Clear
with the recovery observation:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m scripts.v1_dev.mqtt publish --scenario recovery --host 127.0.0.1 --port 18883 --anchor $anchor --run-id $runId
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 read all
```

Repeat reads until vehicle-002 is HEALTHY with no faults and lastEventId
`vehicle-002-event-002-$runId`, with vehicle-001 unchanged. Save this recovery
snapshot; stop on a ten-second timeout. The same anchor preserves relative source
times across the whole sequence; these manual snapshots do not measure propagation
latency or establish that the observations are still fresh when reviewed later.
After the recovery snapshot, compare reads before and after the invalid inputs:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m scripts.v1_dev.mqtt publish --scenario malformed --host 127.0.0.1 --port 18883
.\.venv-b1\Scripts\python.exe -X utf8 -B -m scripts.v1_dev.mqtt publish --scenario unknown --host 127.0.0.1 --port 18883
.\.venv-b1\Scripts\python.exe -X utf8 -B -m ditto.v1 read all
```

The replay command is an explicitly development-only input generator; production
code does not import it. Default replay timestamps rebase the entire sequence to
current time minus four seconds. Use a new run ID and a later sequence time when
rerunning against persistent twins. Capture whole-Thing reads after each transition,
not just the final healthy state. Confirm vehicle-002 healthy -> fault -> healthy,
vehicle-001 isolation, original event/source/context IDs and unchanged legacy fields.
Compare both twins before/after invalid publications. Save exact event topic/JSON
for duplicate/equal/late replay checks; stop/restart only this subscriber with the
same client ID and repeat those publications to prove live watermark recovery.
An unavailable/wrong-auth test must leave both snapshots intact while withholding
ACK of the affected observation; restore configuration and confirm recovery.

This is replay-driven component integration, not Emmanuel's live edge workflow.
For full V1 acceptance remove replay publishers, use Emmanuel's actual V1 streams
and coordinate Ankit's API checks. No fleet acceptance is claimed here.

## Tests and current limitations

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_mqtt_ingress.py tests/test_mqtt_subscriber.py tests/test_ditto_v1_writer.py tests/test_ditto_v1_cli.py
```

All B1/B2 tests are mock/component checks. The loopback HTTP test uses real requests
and authentication headers against a **mock** server. Paho construction/reason codes
are exercised without a broker. Live Eclipse Ditto policies, real Mosquitto reconnect,
persisted broker sessions and the complete edge-to-twin scenario remain unverified.

After the payload-size fix, verified locally on November 11, 2026 with Python
3.12.10: 54 focused B1/B2 tests and 40 subtests passed; the available regression
run passed 202 tests and 258
subtests with the four modules below explicitly ignored. UTF-8 mode was enabled;
existing temporary-file tests required execution outside the filesystem sandbox.
Diff whitespace checks and CLI help also passed. No live service result is claimed.

The full non-integration suite was attempted on Python 3.12.10 ARM64. Three modules
cannot collect without generated Protobuf classes:
`tests/test_uprotocol_transport.py`, `uprotocol/tests/test_extended_transport.py`,
`uprotocol/tests/test_transport.py`. The fourth,
`vehicle-simulator/tests/test_kuksa_publication.py`, imports missing `kuksa_client`
before its integration marker can deselect it; its actual tests need live KUKSA.
An approved dependency installation was attempted, but gRPC packages required a
source build on this host and failed for missing Microsoft C++ Build Tools. No
build tools were installed and no dependency versions were changed to bypass it.
Run the repository CI dependency/protobuf-generation steps on a compatible Python
3.12 host, then rerun the full suite. Run the KUKSA module separately with its real
service before claiming that integration criterion.

Review fixes in B1: preserve submicrosecond timestamp ordering; treat downstream
validation failures as unacknowledged persistence failures; reload watermarks after
uncertain writes; ignore late connect callbacks after shutdown. Legacy HTTP/bridge,
B3 verifier, Kanto, backend, dashboard, fleet logic and V2 code are unchanged.
