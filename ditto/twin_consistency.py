"""B3 read-only V1 snapshot/sequence checks. No MQTT writer or fleet aggregate.

Implements contract 1.0.0 C3-C6 independently of unmerged B1/B2 production code.
"""
import copy
from datetime import datetime, timezone
import math
import re

VEHICLES = ('vehicle-001', 'vehicle-002')


class ConsistencyError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ConsistencyError(code)


def _timestamp(value):
    _require(isinstance(value, str) and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)', value), 'INVALID_TIMESTAMP')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ConsistencyError('INVALID_TIMESTAMP') from error


def _time_key(value):
    return (_timestamp(value).replace(microsecond=0),
            value[19:].removesuffix('Z').removesuffix('+00:00').removeprefix('.').rstrip('0'))


def _object(value, code='INVALID_TYPE'):
    _require(isinstance(value, dict), code)
    return value


def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _reject_nonfinite(properties):
    """Check every nested property/extension without serialization or a size limit."""
    pending = [properties]
    visited = set()
    while pending:
        value = pending.pop()
        if isinstance(value, float):
            _require(math.isfinite(value), 'NON_FINITE_VALUE')
        elif isinstance(value, (dict, list)) and id(value) not in visited:
            visited.add(id(value))
            pending.extend(value.values() if isinstance(value, dict) else value)


def inspect_v1_twin(vehicle_id, thing, *, now=None, stale_after=5, unavailable_after=30):
    """Return validated properties and derived availability; never mutate a twin.

    Invalid identity/schema/time raises ConsistencyError. A valid old snapshot
    remains inspectable as STALE/UNAVAILABLE, never silently current or healthy.
    """
    _require(vehicle_id in VEHICLES, 'UNKNOWN_VEHICLE')
    now = now if now is not None else datetime.now(timezone.utc)
    _require(isinstance(now, datetime) and now.utcoffset() is not None, 'INVALID_CLOCK')
    _require(_finite(stale_after) and _finite(unavailable_after) and
             0 < stale_after < unavailable_after, 'INVALID_CONFIG')
    thing = _object(thing)
    _require(thing.get('thingId') == f'sdv:{vehicle_id}', 'TWIN_IDENTITY')
    _require(_object(thing.get('attributes')).get('vehicleId') == vehicle_id, 'TWIN_IDENTITY')
    features = _object(thing.get('features'))
    feature = _object(features.get('v1'))
    props = _object(feature.get('properties'))
    _reject_nonfinite(props)
    for key in ('vehicleId', 'schemaVersion', 'lastEventId', 'sourceTimestamp', 'health', 'faults', 'lidar'):
        _require(key in props, 'MISSING_FIELD')
    _require(props['vehicleId'] == vehicle_id, 'TWIN_IDENTITY')
    _require(props['schemaVersion'] == '1.0.0', 'UNSUPPORTED_VERSION')
    for key in ('lastEventId', 'actionId', 'traceId'):
        if key in props:
            _require(isinstance(props[key], str) and bool(props[key].strip()), 'INVALID_TYPE')
    source = _timestamp(props['sourceTimestamp'])
    lidar = _object(props['lidar'])
    _require('sensorAvailable' in lidar and 'distanceMeters' in lidar, 'MISSING_FIELD')
    sensor, distance = lidar['sensorAvailable'], lidar['distanceMeters']
    _require(type(sensor) is bool, 'INVALID_TYPE')
    _require((_finite(distance) and distance >= 0) or (distance is None and not sensor), 'INVALID_TYPE')
    _require(isinstance(props['faults'], list) and all(isinstance(code, str) for code in props['faults']), 'INVALID_TYPE')
    if not sensor:
        expected = ('CRITICAL', ['LIDAR_SENSOR_FAILURE'])
    elif distance <= 5:
        expected = ('CRITICAL', ['LIDAR_OBSTRUCTION'])
    elif distance <= 10:
        expected = ('WARNING', ['LIDAR_OBSTRUCTION'])
    else:
        expected = ('HEALTHY', [])
    _require(isinstance(props['health'], str) and props['health'] in ('HEALTHY', 'WARNING', 'CRITICAL'), 'INVALID_HEALTH')
    _require((props['health'], props['faults']) == expected, 'HEALTH_FAULT_MISMATCH')
    age = (now - source).total_seconds()
    _require(age >= -1, 'FUTURE_TIMESTAMP')
    availability = 'UNAVAILABLE' if age > unavailable_after else 'STALE' if age > stale_after else 'AVAILABLE'
    return {'properties': copy.deepcopy(props), 'availability': availability}


class TwinSequence:
    """Observation-only watermarks. Exact repeated polls are detected, not errors.

    Rejected/conflicting snapshots never replace a previously trusted snapshot.
    This does not enforce ordering on production writes or aggregate vehicles.
    """
    def __init__(self):
        self._previous = {}

    def observe(self, vehicle_id, thing, *, now=None):
        current = inspect_v1_twin(vehicle_id, thing, now=now)['properties']
        previous = self._previous.get(vehicle_id)
        if previous is not None:
            if current['lastEventId'] == previous['lastEventId']:
                _require(current == previous, 'CONFLICTING_EVENT')
                return 'DUPLICATE_EVENT'
            _require(_time_key(current['sourceTimestamp']) > _time_key(previous['sourceTimestamp']), 'OUT_OF_ORDER')
        self._previous[vehicle_id] = copy.deepcopy(current)
        return 'INITIAL' if previous is None else 'UPDATED'


def verify_isolation(before, after, *, target='vehicle-002', now=None):
    """Check a controlled target-only update, not simultaneous live publications.

    Both inputs map the two registered IDs to whole-Thing snapshots. All
    non-target whole Things must be exactly unchanged; no fleet values are built.
    """
    _require(target in VEHICLES, 'UNKNOWN_VEHICLE')
    _require(isinstance(before, dict) and isinstance(after, dict) and
             set(before) == set(VEHICLES) and set(after) == set(VEHICLES), 'TWIN_IDENTITIES')
    for vehicle in VEHICLES:
        inspect_v1_twin(vehicle, before[vehicle], now=now)
        inspect_v1_twin(vehicle, after[vehicle], now=now)
        if vehicle != target:
            _require(before[vehicle] == after[vehicle], 'ISOLATION_FAILURE')
