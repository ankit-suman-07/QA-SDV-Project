"""Executable proposed V1 contract, for development tools/tests only.

Production owners must implement their own adapters against the reviewed contract.
This module is never imported by the running application or a live fallback.
"""
import copy
import math
import json
from datetime import datetime, timedelta, timezone

VEHICLES = ('vehicle-001', 'vehicle-002')
VERSION = '1.0.0'
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
TEST_NOW = EPOCH + timedelta(seconds=4)


class ContractError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f'{code}: {message}')


def require(condition, code, message):
    if not condition:
        raise ContractError(code, message)


def decode_event(payload):
    """Strict wire JSON decoding before semantic validation."""
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'MALFORMED_JSON', 'duplicate key: ' + key)
            result[key] = value
        return result

    def nonfinite(value):
        raise ContractError('MALFORMED_JSON', 'non-finite JSON number: ' + value)

    require(isinstance(payload, (str, bytes)), 'MALFORMED_JSON', 'expected UTF-8 JSON')
    wire = payload.encode('utf-8') if isinstance(payload, str) else payload
    require(len(wire) <= 65536, 'MALFORMED_JSON', 'payload exceeds 64 KiB')
    try:
        return json.loads(wire, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError('MALFORMED_JSON', str(error)) from error


def parse_timestamp(value):
    require(isinstance(value, str) and 'T' in value and
            (value.endswith('Z') or value.endswith('+00:00')),
            'INVALID_TIMESTAMP', 'expected UTC ISO 8601 with Z or +00:00')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ContractError('INVALID_TIMESTAMP', str(error)) from error
    require(result.utcoffset() == timedelta(0), 'INVALID_TIMESTAMP', 'UTC required')
    return result


def iso(value):
    return value.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def topic(vehicle_id):
    return f'sdv/{vehicle_id}/health'


def classify(distance, sensor_available):
    if not sensor_available:
        return 'CRITICAL', ['LIDAR_SENSOR_FAILURE']
    if distance <= 5:
        return 'CRITICAL', ['LIDAR_OBSTRUCTION']
    if distance <= 10:
        return 'WARNING', ['LIDAR_OBSTRUCTION']
    return 'HEALTHY', []


def validate_event(mqtt_topic, event):
    require(isinstance(event, dict), 'INVALID_TYPE', 'event must be an object')
    for key in ['schemaVersion', 'eventId', 'vehicleId', 'sourceTimestamp', 'health', 'faults', 'lidar']:
        require(key in event, 'MISSING_FIELD', key)
    require(isinstance(event['vehicleId'], str) and event['vehicleId'] in VEHICLES,
            'UNKNOWN_VEHICLE', 'vehicle is not registered')
    require(mqtt_topic == topic(event['vehicleId']), 'TOPIC_MISMATCH', 'topic and payload differ')
    require(event['schemaVersion'] == VERSION, 'UNSUPPORTED_VERSION', VERSION)
    require(isinstance(event['eventId'], str) and bool(event['eventId'].strip()),
            'INVALID_TYPE', 'eventId must be nonempty')
    parse_timestamp(event['sourceTimestamp'])
    require(isinstance(event['lidar'], dict), 'INVALID_TYPE', 'lidar must be an object')
    lidar = event['lidar']
    for key in ['distanceMeters', 'sensorAvailable']:
        require(key in lidar, 'MISSING_FIELD', 'lidar.' + key)
    require(type(lidar['sensorAvailable']) is bool, 'INVALID_TYPE', 'sensorAvailable must be boolean')
    distance = lidar['distanceMeters']
    number = type(distance) in (int, float) and math.isfinite(distance) and distance >= 0
    require(number or (distance is None and not lidar['sensorAvailable']),
            'INVALID_TYPE', 'distance must be finite nonnegative metres; null only for failed sensor')
    require(isinstance(event['faults'], list) and all(isinstance(f, str) for f in event['faults']),
            'INVALID_TYPE', 'faults must be an array of strings')
    require(event['health'] in ('HEALTHY', 'WARNING', 'CRITICAL'), 'INVALID_HEALTH', 'unknown health')
    expected_health, expected_faults = classify(distance, lidar['sensorAvailable'])
    require(event['health'] == expected_health and event['faults'] == expected_faults,
            'HEALTH_FAULT_MISMATCH', 'health/faults disagree with LiDAR observations')
    for key in ['actionId', 'traceId']:
        if key in event:
            require(isinstance(event[key], str) and bool(event[key].strip()), 'INVALID_TYPE', key)
    return event


class EventStream:
    """Per-vehicle high-water marks; rejected events never advance state."""
    def __init__(self):
        self.latest = {}

    def accept(self, mqtt_topic, event):
        validate_event(mqtt_topic, event)
        previous = self.latest.get(event['vehicleId'])
        if previous:
            require(event['eventId'] != previous['eventId'], 'DUPLICATE_EVENT', 'latest ID already applied')
            require(parse_timestamp(event['sourceTimestamp']) > parse_timestamp(previous['sourceTimestamp']),
                    'OUT_OF_ORDER', 'source time must advance strictly')
        self.latest[event['vehicleId']] = copy.deepcopy(event)
        return event


class Capture(EventStream):
    """Acceptance-sequence oracle; vehicle-001 must remain healthy."""
    def __init__(self):
        super().__init__()
        self.phase = 0
        self.vehicle_one_seen = False

    def accept(self, mqtt_topic, event):
        validate_event(mqtt_topic, event)
        if event['vehicleId'] == 'vehicle-001':
            require(event['health'] == 'HEALTHY', 'ISOLATION_FAILURE', 'vehicle-001 changed health')
        super().accept(mqtt_topic, event)
        if event['vehicleId'] == 'vehicle-001':
            self.vehicle_one_seen = True
        elif self.phase == 0 and event['health'] == 'HEALTHY':
            self.phase = 1
        elif self.phase == 1 and event['health'] == 'CRITICAL' and event['faults'] == ['LIDAR_OBSTRUCTION']:
            self.phase = 2
        elif self.phase == 2 and event['health'] == 'HEALTHY':
            self.phase = 3
        return event

    def cycle_complete(self):
        return self.vehicle_one_seen and self.phase == 3


def availability(source_time, now, reachable=True, stale_after=5., unavailable_after=30.):
    require(0 < stale_after < unavailable_after, 'INVALID_CONFIG', '0 < stale < unavailable required')
    if not reachable or source_time is None:
        return 'UNAVAILABLE'
    age = (now - source_time).total_seconds()
    if age < -1 or age > unavailable_after:
        return 'UNAVAILABLE'
    return 'STALE' if age > stale_after else 'AVAILABLE'


def event_to_twin(event):
    validate_event(topic(event['vehicleId']), event)
    properties = copy.deepcopy(event)
    properties['lastEventId'] = properties.pop('eventId')
    return {'thingId': 'sdv:' + event['vehicleId'], 'attributes': {'vehicleId': event['vehicleId']},
            'features': {'v1': {'properties': properties}}}


def vehicle_view(vehicle_id, twin, now, reachable=True, stale_after=5., unavailable_after=30.):
    require(vehicle_id in VEHICLES, 'UNKNOWN_VEHICLE', vehicle_id)
    result = dict(vehicleId=vehicle_id, thingId='sdv:' + vehicle_id, healthStatus=None,
                  availability='UNAVAILABLE', activeFaults=None, lidar=None,
                  sourceTimestamp=None, lastEventId=None)
    if twin is None:
        return result
    require(isinstance(twin, dict) and twin.get('thingId') == 'sdv:' + vehicle_id and
            twin.get('attributes', {}).get('vehicleId') == vehicle_id,
            'TWIN_IDENTITY', 'requested and returned twin differ')
    props = copy.deepcopy(twin.get('features', {}).get('v1', {}).get('properties', {}))
    require(props.get('vehicleId') == vehicle_id, 'TWIN_IDENTITY', 'feature vehicle differs')
    props['eventId'] = props.pop('lastEventId', None)
    validate_event(topic(vehicle_id), props)
    result.update(healthStatus=props['health'], activeFaults=props['faults'], lidar=props['lidar'],
                  sourceTimestamp=props['sourceTimestamp'], lastEventId=props['eventId'],
                  availability=availability(parse_timestamp(props['sourceTimestamp']), now, reachable,
                                            stale_after, unavailable_after))
    return result


def fleet_summary(views, now):
    require(len(views) == len(VEHICLES) and {v['vehicleId'] for v in views} == set(VEHICLES),
            'FLEET_IDENTITY', 'exactly one view per registered vehicle required')
    counts = dict(totalVehicles=len(VEHICLES), availableVehicles=0, staleVehicles=0,
                  unavailableVehicles=0, healthyVehicles=0, warningVehicles=0, criticalVehicles=0)
    for view in views:
        availability_field = {'AVAILABLE': 'availableVehicles', 'STALE': 'staleVehicles',
                              'UNAVAILABLE': 'unavailableVehicles'}[view['availability']]
        counts[availability_field] += 1
        if view['availability'] == 'AVAILABLE':
            counts[{'HEALTHY': 'healthyVehicles', 'WARNING': 'warningVehicles',
                    'CRITICAL': 'criticalVehicles'}[view['healthStatus']]] += 1
    return dict(generatedAt=iso(now).replace('.000Z', 'Z'), **counts,
                vehicles=sorted(copy.deepcopy(views), key=lambda v: v['vehicleId']))


def rebase_event(event, anchor):
    result = copy.deepcopy(event)
    if 'sourceTimestamp' in result:
        result['sourceTimestamp'] = iso(anchor + (parse_timestamp(result['sourceTimestamp']) - EPOCH))
    return result
