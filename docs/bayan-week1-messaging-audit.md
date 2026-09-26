# Week 1 - Messaging and Digital Twin Audit

## Current Transport Audit

### Already Supported
- vehicle_id
- event_id
- trace_id
- action_id
- event_type
- schema_version
- source timestamp
- publication timestamp
- Protobuf serialization/deserialization
- duplicate detection
- invalid parse tracking

### Missing / Needs Review
- sequence_number
- per-vehicle ordering
- stronger metadata validation
- real network transport
- duplicate-processing behavior
- multi-vehicle isolation tests

### Confirmed EventMetadata Fields
- schema_version
- event_id
- trace_id
- optional action_id
- vehicle_id
- event_type
- source_timestamp
- publication_timestamp

Note:
- reception_timestamp is intentionally recorded at receive time and is not part of the outbound wire message.
