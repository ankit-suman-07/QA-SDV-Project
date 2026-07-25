# uProtocol Component

Event schemas and in-process transport for vehicle status/health/fault events.

## Contents

```
uprotocol/
|-- README.md
|-- pom.xml
|-- __init__.py
|-- transport.py
|-- proto/
|   |-- common.proto
|   |-- vehicle_status.proto
|   |-- health_status.proto
|   `-- vehicle_fault.proto
|-- generated/                (not committed - created by the protoc step below)
|-- tests/
|   `-- test_transport.py
|-- demo/
`-- src/main/java/com/sdv/uprotocol/
    `-- EventPublisher.java
```

## transport.py location

Located at `uprotocol/transport.py`. Any importing script should add the
repo root to `sys.path` based on its own file location:

```python
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from uprotocol.transport import publish_vehicle_status, receive_vehicle_status, get_delivery_stats
```

No manual `PYTHONPATH` setting required - the path insertion happens in code.

## What transport.py does

- `publish_vehicle_status(...)` - builds and serializes a `VehicleStatusUpdated` event, records it as published.
- `receive_vehicle_status(bytes)` - deserializes an event, records a reception timestamp, detects duplicates/invalid messages.
- `get_delivery_stats()` - returns `published_count`, `received_count`, `duplicate_count`, `missing_count`, `missing_event_ids`, `invalid_count`.

Every event carries a unique event ID, vehicle ID, source timestamp, and
publication timestamp. Reception timestamp is tracked separately by the
transport module, not embedded in the message itself.

## Key facts

- In-process transport only - no MQTT/Zenoh broker. Messages are
  serialized/deserialized as they would be over a real wire, delivered
  via direct in-process call.
- `.proto` files are message templates; `generated/` holds the compiled
  Python classes.
- Delivery tracking is in-memory and process-wide; stats reset only via
  `tracker.reset()` or process restart.

## Tests

| Test | Checks |
|---|---|
| `test_serialization_and_deserialization_round_trip` | No data lost converting a message to bytes and back |
| `test_matching_event_ids` | Published event ID matches received event ID |
| `test_unique_event_ids_across_multiple_publishes` | No duplicate IDs across 20 publishes |
| `test_timestamp_preservation` | Timestamp unchanged after the wire round-trip |
| `test_corrupted_message_is_rejected_not_crashed` | Broken bytes raise a clean error, not a crash |
| `test_message_missing_required_fields_is_rejected` | A message with no vehicle/event ID is rejected |
| `test_duplicate_detection` | Same message delivered twice counts as 1 delivery + 1 duplicate |
| `test_missing_event_detection` | A published-but-undelivered message is correctly flagged missing |
| `test_delivery_stats_exposed_and_accumulate` | `get_delivery_stats()` returns accurate counts |

## How to Run

```
pip install protobuf grpcio-tools pytest
python -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated uprotocol/proto/common.proto uprotocol/proto/vehicle_status.proto uprotocol/proto/health_status.proto uprotocol/proto/vehicle_fault.proto
python3 -m pytest uprotocol/tests/test_transport.py -v
```
Expect `9 passed`.

Query stats:
```python
from uprotocol.transport import get_delivery_stats
print(get_delivery_stats())
```

## Status

- [x] Schemas designed and verified
- [x] transport.py located at uprotocol/, bridge import updated
- [x] Delivery tracking: published, received, duplicate, missing, invalid
- [x] Transport tests passing (9/9)
- [x] EventPublisher.java compiles, JUnit tests passing (7/7)
- [ ] Real network transport (MQTT/Zenoh)
- [ ] Full live backend connection

## Open items

- Tire pressure unit: schema assumes PSI; simulator may publish kPa.
- Only VehicleStatusUpdated is wired through transport.py currently.
