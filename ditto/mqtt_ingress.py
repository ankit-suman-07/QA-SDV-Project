"""Production V1 event validation and persistence-gated ingestion (C2-C6).

No network or development-tool dependencies. B2 supplies the TwinWriter.
"""
import copy
from datetime import datetime, timedelta
import json
import math
import re
from threading import Lock
from typing import Protocol

VEHICLES = ('vehicle-001', 'vehicle-002')
MAX_PAYLOAD_BYTES = 65536
_UTC_TIMESTAMP = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)\Z')


class EventError(ValueError):
    """A rejected event; code is safe for structured operational logs."""
    def __init__(self, code):
        self.code = code
        self.vehicle_id = None
        self.event_id = None
        super().__init__(code)


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


def _finite_numbers(value):
    # Extensions must also be valid finite JSON; e.g. 1e999 is not JSON Infinity
    # syntax, but Python decodes it as an infinite float.
    if isinstance(value, float):
        _require(math.isfinite(value), 'MALFORMED_JSON')
    elif isinstance(value, dict):
        for item in value.values():
            _finite_numbers(item)
    elif isinstance(value, list):
        for item in value:
            _finite_numbers(item)


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
        _finite_numbers(event)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, EventError):
            raise
        raise EventError('MALFORMED_JSON') from error
    return event


def decode_event(topic, payload):
    """Decode strict UTF-8 JSON and validate the complete C3/C4 envelope."""
    return validate_event(topic, decode_json(payload, max_bytes=MAX_PAYLOAD_BYTES))


def validate_event(topic, event):
    """Validate decoded event semantics without imposing a wire encoding/budget."""
    try:
        _finite_numbers(event)
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

    def process(self, topic, payload):
        event = decode_event(topic, payload)
        vehicle = event['vehicleId']
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
            properties = copy.deepcopy(event)
            properties['lastEventId'] = properties.pop('eventId')
            # A writer must not be able to mutate the event used for ordering.
            try:
                self.writer.persist(vehicle, properties)
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
