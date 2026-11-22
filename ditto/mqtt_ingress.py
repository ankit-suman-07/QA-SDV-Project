"""Production V1 event validation and persistence-gated ingestion (C2-C6).

No network or development-tool dependencies. B2 supplies the TwinWriter.
"""
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math
import re
from threading import Lock
from typing import Protocol

VEHICLES = ('vehicle-001', 'vehicle-002')
V2_VEHICLES = (*VEHICLES, 'vehicle-003')
MAX_PAYLOAD_BYTES = 65536
# C2/C5 do not specify replay retention. Keep fixed-size ID digests for up to
# 65,536 observations (about 109 minutes at 10 Hz) per vehicle's active session.
# Do not evict IDs or silently switch sessions. Historical IDs are process-local.
MAX_V2_SESSION_EVENT_IDS = 65_536
MAX_VSS_FLOAT = float.fromhex('0x1.fffffep127')
_UTC_TIMESTAMP = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)\Z')


class EventError(ValueError):
    """A rejected event; code is safe for structured operational logs."""
    def __init__(self, code):
        self.code = code
        self.vehicle_id = None
        self.event_id = None
        super().__init__(code)


class LocalJSONError(EventError):
    """Deterministic pre-dispatch serialization failure, never an HTTP outcome."""


class WatermarkError(RuntimeError):
    """Stored state is unusable; do not treat it as an empty twin."""


def _require(condition, code):
    if not condition:
        raise EventError(code)


def parse_timestamp(value):
    _require(isinstance(value, str) and _UTC_TIMESTAMP.fullmatch(value), 'INVALID_TIMESTAMP')
    try:
        timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise EventError('INVALID_TIMESTAMP') from error
    _require(timestamp.utcoffset() == timedelta(0), 'INVALID_TIMESTAMP')
    return timestamp


def timestamp_key(value):
    """Compare full ISO fractional precision without datetime's microsecond loss."""
    timestamp = parse_timestamp(value)
    fraction = value[19:].removesuffix('Z').removesuffix('+00:00')
    return timestamp.replace(microsecond=0), fraction.removeprefix('.').rstrip('0')


def _validate_json(value):
    """Iteratively validate JSON scalars/keys, finite numbers and acyclic shape."""
    pending = [(value, False)]
    active = set()
    while pending:
        item, leaving = pending.pop()
        if leaving:
            active.remove(id(item))
        elif isinstance(item, (dict, list)):
            _require(id(item) not in active, 'MALFORMED_JSON')
            active.add(id(item))
            pending.append((item, True))
            if isinstance(item, dict):
                for key in item:
                    _require(isinstance(key, str), 'MALFORMED_JSON')
                    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in key), 'MALFORMED_JSON')
                pending.extend((child, False) for child in item.values())
            else:
                pending.extend((child, False) for child in item)
        elif isinstance(item, str):
            _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in item), 'MALFORMED_JSON')
        elif isinstance(item, float):
            _require(math.isfinite(item), 'MALFORMED_JSON')
        else:
            _require(item is None or isinstance(item, (bool, int)), 'MALFORMED_JSON')


def encode_json(value):
    """Compact UTF-8, with controlled local failures and no MQTT wire budget.

    Only use LocalJSONError before dispatch: an uncertain HTTP result is not
    evidence that an event is invalid and must never be ACKed as a rejection.
    """
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise LocalJSONError('MALFORMED_JSON') from error


def decode_json(payload, max_bytes=None):
    """Strict UTF-8 JSON shared by wire events and persisted Ditto reads."""
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'MALFORMED_JSON')
            result[key] = value
        return result

    def nonfinite(_value):
        raise EventError('MALFORMED_JSON')

    _require(isinstance(payload, (bytes, str)), 'MALFORMED_JSON')
    try:
        wire = payload.encode('utf-8') if isinstance(payload, str) else payload
        _require(max_bytes is None or len(wire) <= max_bytes, 'MALFORMED_JSON')
        event = json.loads(wire.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=nonfinite)
        _validate_json(event)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, EventError):
            raise
        raise EventError('MALFORMED_JSON') from error
    return event


def decode_event(topic, payload):
    """Decode strict UTF-8 JSON and validate the complete C3/C4 envelope."""
    event = validate_event(topic, decode_json(payload, max_bytes=MAX_PAYLOAD_BYTES))
    # Check the actual persistence codec, not an invented shared depth limit.
    # This is not a second size check on internally serialized bytes.
    encode_json(event)
    return event


def validate_event(topic, event):
    """Validate decoded event semantics without imposing a wire encoding/budget."""
    try:
        _validate_json(event)
        return _validate_event(topic, event)
    except RecursionError as error:
        raise EventError('MALFORMED_JSON') from error
    except EventError as error:
        if isinstance(event, dict):
            for key, attribute in (('vehicleId', 'vehicle_id'), ('eventId', 'event_id')):
                if isinstance(event.get(key), str):
                    setattr(error, attribute, event[key])
        raise


def _validate_event(topic, event):
    _require(isinstance(event, dict), 'INVALID_TYPE')
    for key in ('schemaVersion', 'eventId', 'vehicleId', 'sourceTimestamp',
                'health', 'faults', 'lidar'):
        _require(key in event, 'MISSING_FIELD')
    vehicle = event['vehicleId']
    _require(isinstance(vehicle, str) and vehicle in VEHICLES, 'UNKNOWN_VEHICLE')
    _require(topic == f'sdv/{vehicle}/health', 'TOPIC_MISMATCH')
    _require(event['schemaVersion'] == '1.0.0', 'UNSUPPORTED_VERSION')
    for key in ('eventId', 'actionId', 'traceId'):
        if key in event:
            _require(isinstance(event[key], str) and bool(event[key].strip()), 'INVALID_TYPE')
    parse_timestamp(event['sourceTimestamp'])
    lidar = event['lidar']
    _require(isinstance(lidar, dict), 'INVALID_TYPE')
    for key in ('distanceMeters', 'sensorAvailable'):
        _require(key in lidar, 'MISSING_FIELD')
    available = lidar['sensorAvailable']
    distance = lidar['distanceMeters']
    _require(type(available) is bool, 'INVALID_TYPE')
    # Avoid converting arbitrarily large JSON integers to float.
    numeric = type(distance) is int or (type(distance) is float and math.isfinite(distance))
    _require((numeric and distance >= 0) or (distance is None and not available), 'INVALID_TYPE')
    _require(isinstance(event['faults'], list) and
             all(isinstance(fault, str) for fault in event['faults']), 'INVALID_TYPE')
    _require(event['health'] in ('HEALTHY', 'WARNING', 'CRITICAL'), 'INVALID_HEALTH')
    if not available:
        expected = 'CRITICAL', ['LIDAR_SENSOR_FAILURE']
    elif distance <= 5:
        expected = 'CRITICAL', ['LIDAR_OBSTRUCTION']
    elif distance <= 10:
        expected = 'WARNING', ['LIDAR_OBSTRUCTION']
    else:
        expected = 'HEALTHY', []
    _require((event['health'], event['faults']) == expected, 'HEALTH_FAULT_MISMATCH')
    return event


def is_v2_health_topic(topic):
    return isinstance(topic, str) and topic.endswith('/v2/health')


def decode_v2_health(topic, payload):
    event = decode_json(payload, max_bytes=MAX_PAYLOAD_BYTES)
    try:
        validate_v2_health(topic, event)
        encode_json(event)
    except EventError as error:
        if isinstance(event, dict):
            for key, attribute in (('vehicleId', 'vehicle_id'), ('eventId', 'event_id')):
                if isinstance(event.get(key), str):
                    setattr(error, attribute, event[key])
        raise
    return event


def validate_v2_health(topic, event):
    """Validate the C2/C5 wire envelope before the persistence boundary."""
    _require(isinstance(event, dict), 'INVALID_TYPE')
    _require('lastEventId' not in event, 'INVALID_TYPE')
    required = (
        'schemaVersion', 'vehicleId', 'eventId', 'sessionId', 'sessionGeneration',
        'sequence', 'frame', 'simulationSeconds', 'sourceTimestamp', 'processingTimestamp',
        'provenance', 'lidar', 'health', 'faults', 'recoveryState', 'recoveryStartedAt',
        'sourceSilent',
    )
    _require(all(key in event for key in required), 'MISSING_FIELD')
    vehicle = event['vehicleId']
    _require(isinstance(vehicle, str) and vehicle in V2_VEHICLES, 'UNKNOWN_VEHICLE')
    _require(topic == f'sdv/{vehicle}/v2/health', 'TOPIC_MISMATCH')
    _require(event['schemaVersion'] == '2.0.0', 'UNSUPPORTED_VERSION')
    _require(('actionId' in event) == ('traceId' in event), 'MISSING_FIELD')
    for key in ('eventId', 'sessionId', 'actionId', 'traceId'):
        if key in event:
            _require(isinstance(event[key], str) and bool(event[key].strip()), 'INVALID_TYPE')
    for key, minimum in (('sessionGeneration', 1), ('sequence', 0), ('frame', 0)):
        _require(type(event[key]) is int and event[key] >= minimum, 'INVALID_TYPE')
    elapsed = event['simulationSeconds']
    _require(type(elapsed) in (int, float) and elapsed >= 0, 'INVALID_TYPE')
    try:
        finite_elapsed = math.isfinite(elapsed)
    except OverflowError as error:
        raise EventError('INVALID_TYPE') from error
    _require(finite_elapsed, 'INVALID_TYPE')
    parse_timestamp(event['sourceTimestamp'])
    parse_timestamp(event['processingTimestamp'])
    _require(event['provenance'] in ('CARLA', 'SYNTHETIC'), 'INVALID_TYPE')
    _require(type(event['sourceSilent']) is bool, 'INVALID_TYPE')

    if 'velocityMetersPerSecond' in event:
        velocity = event['velocityMetersPerSecond']
        _require(isinstance(velocity, dict) and velocity.keys() == {'x', 'y', 'z'},
                 'INVALID_TYPE')
        # Check the magnitude before hypot converts components to float.
        _require(all(type(value) in (int, float) and abs(value) <= MAX_VSS_FLOAT
                     for value in velocity.values()), 'INVALID_TYPE')
        speed = 3.6 * math.hypot(velocity['x'], velocity['y'], velocity['z'])
        _require(speed <= MAX_VSS_FLOAT, 'INVALID_TYPE')

    lidar = event['lidar']
    _require(isinstance(lidar, dict), 'INVALID_TYPE')
    _require('distanceMeters' in lidar and 'sensorAvailable' in lidar, 'MISSING_FIELD')
    available, distance = lidar['sensorAvailable'], lidar['distanceMeters']
    _require(type(available) is bool, 'INVALID_TYPE')
    if available:
        _require(type(distance) in (int, float) and distance >= 0, 'INVALID_TYPE')
        try:
            finite_distance = math.isfinite(distance)
        except OverflowError as error:
            raise EventError('INVALID_TYPE') from error
        _require(finite_distance, 'INVALID_TYPE')
    else:
        _require(distance is None, 'INVALID_TYPE')
    health, faults = event['health'], event['faults']
    _require(health in ('HEALTHY', 'WARNING', 'CRITICAL'), 'INVALID_HEALTH')
    state, started = event['recoveryState'], event['recoveryStartedAt']
    _require(state in ('NONE', 'IN_PROGRESS'), 'INVALID_TYPE')
    if state == 'IN_PROGRESS':
        _require(not event['sourceSilent'], 'INVALID_TYPE')
        _require(timestamp_key(started) <= timestamp_key(event['sourceTimestamp']),
                 'INVALID_TIMESTAMP')
        _require(available and distance > 10, 'HEALTH_FAULT_MISMATCH')
        _require((health in ('WARNING', 'CRITICAL') and faults == ['LIDAR_OBSTRUCTION'])
                 or (health == 'CRITICAL' and faults == ['LIDAR_SENSOR_FAILURE']),
                 'HEALTH_FAULT_MISMATCH')
    else:
        _require(started is None, 'INVALID_TYPE')
        if not available:
            expected = 'CRITICAL', ['LIDAR_SENSOR_FAILURE']
        elif distance <= 5:
            expected = 'CRITICAL', ['LIDAR_OBSTRUCTION']
        elif distance <= 10:
            expected = 'WARNING', ['LIDAR_OBSTRUCTION']
        else:
            expected = 'HEALTHY', []
        # A recovery reset can retain the prior fault on a healthy sample.
        retained_fault = expected[0] == 'HEALTHY' and (
            (health in ('WARNING', 'CRITICAL') and faults == ['LIDAR_OBSTRUCTION'])
            or (health == 'CRITICAL' and faults == ['LIDAR_SENSOR_FAILURE'])
        )
        _require((health, faults) == expected or retained_fault, 'HEALTH_FAULT_MISMATCH')
    return event


def v2_write_needed(properties, previous):
    """Compare a candidate with the last persisted V2 snapshot."""
    if previous is None:
        _require(properties['sessionGeneration'] == 1, 'UNREGISTERED_SESSION')
        return True
    if properties['lastEventId'] == previous['lastEventId']:
        _require(properties == previous, 'EVENT_ID_CONFLICT')
        return False
    generation = properties['sessionGeneration']
    _require(generation >= previous['sessionGeneration'], 'OUT_OF_ORDER')
    _require(generation == previous['sessionGeneration']
             and properties['sessionId'] == previous['sessionId'], 'UNREGISTERED_SESSION')
    _require(properties['sequence'] > previous['sequence']
             and properties['frame'] > previous['frame']
             and timestamp_key(properties['sourceTimestamp']) > timestamp_key(previous['sourceTimestamp']),
             'OUT_OF_ORDER')
    return True


class TwinWriter(Protocol):
    """B2 adapter boundary. Implementations must be safe across two vehicles.

    load_watermark validates the live Thing/attribute/feature identity and schema,
    returning (lastEventId, sourceTimestamp). None means a verified provisioned
    individual twin with no v1 state yet. Missing/unreadable/corrupt twins raise;
    never return None on a failed read. persist replaces only the complete v1
    properties atomically, returns only after confirmed success, and raises on
    all failures (including exhausted bounded retries and uncertain timeouts).
    """
    def load_watermark(self, vehicle_id: str) -> tuple[str, str] | None: ...

    def persist(self, vehicle_id: str, properties: dict) -> None: ...


class Ingress:
    """One instance per writer; serialize per vehicle, commit only after persist."""
    def __init__(self, writer: TwinWriter):
        self.writer = writer
        self._locks = {vehicle: Lock() for vehicle in VEHICLES}
        self._committed = {}
        self._v2_locks = {vehicle: Lock() for vehicle in V2_VEHICLES}
        self._v2_replay = {}

    @property
    def supports_v2(self):
        """Whether this writer exposes the version-specific persistence boundary."""
        return (callable(getattr(self.writer, 'load_v2_watermark', None))
                and callable(getattr(self.writer, 'persist_v2', None)))

    def _process_v2(self, topic, payload):
        event = decode_v2_health(topic, payload)
        properties = decode_json(encode_json(event))
        properties['lastEventId'] = properties.pop('eventId')
        vehicle = event['vehicleId']
        # A dedicated V2 store may implement the generic writer boundary.
        load = getattr(self.writer, 'load_v2_watermark', self.writer.load_watermark)
        persist = getattr(self.writer, 'persist_v2', self.writer.persist)
        with self._v2_locks[vehicle]:
            previous = load(vehicle)
            if previous is not None and not isinstance(previous, dict):
                raise WatermarkError('invalid V2 persisted snapshot')
            needs_write = v2_write_needed(properties, previous)
            session = (event['sessionGeneration'], event['sessionId'])
            active_session, accepted_ids = self._v2_replay.get(vehicle, (session, set()))
            _require(session == active_session, 'UNREGISTERED_SESSION')

            event_key = sha256(event['eventId'].encode('utf-8')).digest()
            if previous is not None and len(accepted_ids) < MAX_V2_SESSION_EVENT_IDS:
                # The snapshot is authoritative, including on the first read
                # after restart or after a write whose response was lost.
                accepted_ids.add(sha256(previous['lastEventId'].encode('utf-8')).digest())
                self._v2_replay[vehicle] = session, accepted_ids
            if needs_write:
                _require(event_key not in accepted_ids, 'EVENT_ID_CONFLICT')
                if len(accepted_ids) >= MAX_V2_SESSION_EVENT_IDS:
                    # A persistence failure keeps QoS 1 delivery pending.
                    raise WatermarkError('V2 source session event-ID capacity reached')
                persist(vehicle, properties)
                accepted_ids.add(event_key)
                self._v2_replay[vehicle] = session, accepted_ids
        return event

    def process(self, topic, payload):
        if is_v2_health_topic(topic):
            return self._process_v2(topic, payload)
        event = decode_event(topic, payload)
        vehicle = event['vehicleId']
        # JSON round-trip avoids deepcopy's lower recursion limit and gives the
        # writer an independent snapshot. Codec failures occur before any read.
        properties = decode_json(encode_json(event))
        properties['lastEventId'] = properties.pop('eventId')
        with self._locks[vehicle]:
            if vehicle not in self._committed:
                try:
                    previous = self.writer.load_watermark(vehicle)
                except EventError as error:
                    raise WatermarkError('downstream state validation failed') from error
                if previous is not None:
                    try:
                        if (not isinstance(previous, tuple) or len(previous) != 2 or
                                not isinstance(previous[0], str) or not previous[0].strip()):
                            raise WatermarkError('invalid stored event ID')
                        parse_timestamp(previous[1])
                    except EventError as error:
                        raise WatermarkError('invalid stored source timestamp') from error
                self._committed[vehicle] = previous
            previous = self._committed[vehicle]
            if previous is not None:
                _require(event['eventId'] != previous[0], 'DUPLICATE_EVENT')
                _require(timestamp_key(event['sourceTimestamp']) > timestamp_key(previous[1]),
                         'OUT_OF_ORDER')
            # A writer must not be able to mutate the event used for ordering.
            try:
                self.writer.persist(vehicle, properties)
            except LocalJSONError:
                # Only the encoder can certify no request was dispatched.
                # Retain the trusted watermark and reject without retrying.
                raise
            except Exception as error:
                # A timeout can mean the server committed but its reply was lost.
                # Reload live state before any retry or later event, never trust
                # the older in-memory watermark after an uncertain outcome.
                self._committed.pop(vehicle, None)
                if isinstance(error, EventError):
                    raise WatermarkError('downstream persistence validation failed') from error
                raise
            self._committed[vehicle] = event['eventId'], event['sourceTimestamp']
        return event
