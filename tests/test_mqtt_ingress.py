"""B1 production ingress tests; no broker or Ditto deployment required."""
import copy
import importlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock

FIXTURES = Path(__file__).parent / 'fixtures' / 'v1'


def fixture(name='vehicle-002-healthy'):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


class FakeWriter:
    def __init__(self):
        self.states = {}
        self.writes = []
        self.fail_read = set()
        self.fail_write = set()

    def load_watermark(self, vehicle_id):
        if vehicle_id in self.fail_read:
            raise OSError('read unavailable')
        return copy.deepcopy(self.states.get(vehicle_id))

    def persist(self, vehicle_id, properties):
        if vehicle_id in self.fail_write:
            raise OSError('write unavailable')
        self.writes.append((vehicle_id, copy.deepcopy(properties)))
        self.states[vehicle_id] = properties['lastEventId'], properties['sourceTimestamp']


class IngressTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/mqtt_ingress.py').exists(),
                        'production B1 ingress is missing')
        self.m = importlib.import_module('ditto.mqtt_ingress')
        self.writer = FakeWriter()
        self.ingress = self.m.Ingress(self.writer)

    def send(self, event, topic=None):
        topic = topic or 'sdv/' + event['vehicleId'] + '/health'
        return self.ingress.process(topic, json.dumps(event).encode())

    def rejected(self, payload, code, topic='sdv/vehicle-002/health'):
        before = copy.deepcopy(self.writer.writes)
        with self.assertRaises(self.m.EventError) as caught:
            self.ingress.process(topic, payload)
        self.assertEqual(code, caught.exception.code)
        self.assertEqual(before, self.writer.writes)

    def test_fixture_cycle_preserves_context_and_isolation(self):
        for name in ['vehicle-001-healthy', 'vehicle-002-healthy',
                     'vehicle-002-fault', 'vehicle-002-recovered']:
            event = fixture(name)
            event.update(actionId='action', traceId='trace')
            self.send(event)
            vehicle, properties = self.writer.writes[-1]
            self.assertEqual(event['vehicleId'], vehicle)
            expected = dict(event)
            expected['lastEventId'] = expected.pop('eventId')
            self.assertEqual(expected, properties)
        self.assertEqual(1, sum(v == 'vehicle-001' for v, _ in self.writer.writes))

    def test_strict_wire_decoding(self):
        for payload in [b'{', b'\xff', b'{"x":1,"x":2}', b'{"x":NaN}',
                        b'{"x":Infinity}', b'{"x":1e999}', b' ' * 65537,
                        b'{"x":{"a":1,"a":2}}']:
            with self.subTest(payload=payload[:40]):
                self.rejected(payload, 'MALFORMED_JSON')
        self.rejected(b'[]', 'INVALID_TYPE')

    def test_schema_rejections(self):
        cases = [('vehicleId', 'vehicle-999', 'UNKNOWN_VEHICLE'),
                 ('vehicleId', ' vehicle-002', 'UNKNOWN_VEHICLE'),
                 ('schemaVersion', '2.0.0', 'UNSUPPORTED_VERSION'),
                 ('eventId', ' ', 'INVALID_TYPE'), ('health', [], 'INVALID_HEALTH'),
                 ('health', 'SENSOR_FAILURE', 'INVALID_HEALTH'),
                 ('faults', ['LIDAR_OBSTRUCTION'], 'HEALTH_FAULT_MISMATCH'),
                 ('faults', ['LIDAR_OBSTRUCTION'] * 2, 'HEALTH_FAULT_MISMATCH'),
                 ('faults', None, 'INVALID_TYPE'), ('actionId', '', 'INVALID_TYPE'),
                 ('traceId', None, 'INVALID_TYPE'), ('lidar', [], 'INVALID_TYPE')]
        for key, value, code in cases:
            with self.subTest(key=key, value=value):
                event = fixture()
                event[key] = value
                self.rejected(json.dumps(event), code)
        for key in fixture():
            event = fixture()
            del event[key]
            self.rejected(json.dumps(event), 'MISSING_FIELD')
        self.rejected(json.dumps(fixture()), 'TOPIC_MISMATCH', 'sdv/vehicle-001/health')

    def test_timestamp_rejections(self):
        for timestamp in ['2026-01-01', '2026-01-01T00:00:00',
                          '2026-01-01T00:00:00+01:00', 'invalidZ',
                          '2026-02-30T00:00:00Z', None, 10]:
            event = fixture()
            event['sourceTimestamp'] = timestamp
            self.rejected(json.dumps(event), 'INVALID_TIMESTAMP')

    def test_lidar_types_and_boundaries(self):
        for distance in [True, '3', -1, None]:
            event = fixture()
            event['lidar']['distanceMeters'] = distance
            self.rejected(json.dumps(event), 'INVALID_TYPE')
        for sensor in [0, 'true', None]:
            event = fixture()
            event['lidar']['sensorAvailable'] = sensor
            self.rejected(json.dumps(event), 'INVALID_TYPE')
        for distance, sensor, health, faults in [
            (0, True, 'CRITICAL', ['LIDAR_OBSTRUCTION']),
            (5, True, 'CRITICAL', ['LIDAR_OBSTRUCTION']),
            (10, True, 'WARNING', ['LIDAR_OBSTRUCTION']),
            (10.01, True, 'HEALTHY', []),
            (None, False, 'CRITICAL', ['LIDAR_SENSOR_FAILURE'])]:
            event = fixture()
            event.update(health=health, faults=faults)
            event['lidar'] = dict(distanceMeters=distance, sensorAvailable=sensor)
            self.m.decode_event('sdv/vehicle-002/health', json.dumps(event))

    def test_failed_write_does_not_commit_and_retry_succeeds(self):
        event = fixture()
        self.writer.fail_write.add('vehicle-002')
        with self.assertRaises(OSError):
            self.send(event)
        self.writer.fail_write.clear()
        self.send(event)
        self.assertEqual(1, len(self.writer.writes))
        self.rejected(json.dumps(event), 'DUPLICATE_EVENT')

    def test_restart_duplicate_equal_and_older_events(self):
        self.send(fixture('vehicle-002-fault'))
        self.ingress = self.m.Ingress(self.writer)
        self.rejected(json.dumps(fixture('vehicle-002-fault')), 'DUPLICATE_EVENT')
        self.rejected(json.dumps(fixture()), 'OUT_OF_ORDER')
        event = fixture('vehicle-002-fault')
        event['eventId'] = 'different'
        self.rejected(json.dumps(event), 'OUT_OF_ORDER')
        self.send(fixture('vehicle-002-recovered'))

    def test_reused_latest_id_with_changed_content_never_overwrites(self):
        event = fixture()
        self.send(event)
        changed = fixture('vehicle-002-fault')
        changed['eventId'] = event['eventId']
        self.rejected(json.dumps(changed), 'DUPLICATE_EVENT')

    def test_invalid_event_does_not_poison_watermark(self):
        event = fixture('vehicle-002-recovered')
        event['health'] = 'CRITICAL'
        self.rejected(json.dumps(event), 'HEALTH_FAULT_MISMATCH')
        self.send(fixture())
        self.assertEqual(1, len(self.writer.writes))

    def test_existing_negative_fixtures_leave_state_unchanged(self):
        self.rejected(json.dumps(fixture('event-malformed')), 'MISSING_FIELD')
        self.rejected(json.dumps(fixture('vehicle-unknown')), 'UNKNOWN_VEHICLE')
        self.send(fixture())
        self.rejected(json.dumps(fixture('event-out-of-order')), 'OUT_OF_ORDER')

    def test_semantic_rejection_exposes_identifiers_without_payload(self):
        event = fixture('event-malformed')
        with self.assertRaises(self.m.EventError) as caught:
            self.send(event)
        self.assertEqual(event['vehicleId'], caught.exception.vehicle_id)
        self.assertEqual(event['eventId'], caught.exception.event_id)

    def test_unreadable_watermark_blocks_only_its_vehicle(self):
        self.writer.fail_read.add('vehicle-002')
        with self.assertRaises(OSError):
            self.send(fixture())
        self.send(fixture('vehicle-001-healthy'))
        self.writer.fail_read.clear()
        self.send(fixture())
        self.assertEqual(2, len(self.writer.writes))

    def test_invalid_stored_watermark_blocks_write(self):
        self.writer.states['vehicle-002'] = ('id', 'naive')
        with self.assertRaises(self.m.WatermarkError):
            self.send(fixture())
        self.assertEqual([], self.writer.writes)

    def test_downstream_validation_failure_is_not_an_input_rejection(self):
        self.writer.load_watermark = Mock(side_effect=self.m.EventError('INVALID_TIMESTAMP'))
        with self.assertRaises(self.m.WatermarkError):
            self.send(fixture())

    def test_submicrosecond_source_times_remain_strictly_ordered(self):
        event = fixture()
        event['sourceTimestamp'] = '2026-01-01T00:00:00.000000001Z'
        self.send(event)
        event['eventId'] = 'newer'
        event['sourceTimestamp'] = '2026-01-01T00:00:00.000000002Z'
        self.send(event)
        self.assertEqual(2, len(self.writer.writes))

    def test_uncertain_write_reloads_live_watermark_before_next_event(self):
        original = self.writer.persist
        def applied_then_timed_out(vehicle, properties):
            original(vehicle, properties)
            raise OSError('response lost after server applied write')
        self.writer.persist = applied_then_timed_out
        with self.assertRaises(OSError):
            self.send(fixture('vehicle-002-fault'))
        self.writer.persist = original
        self.rejected(json.dumps(fixture()), 'OUT_OF_ORDER')

    def test_concurrent_duplicate_is_persisted_once(self):
        outcomes = []
        def send():
            try:
                self.send(fixture())
                outcomes.append('written')
            except self.m.EventError as error:
                outcomes.append(error.code)
        threads = [threading.Thread(target=send) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(1, outcomes.count('written'))
        self.assertEqual(7, outcomes.count('DUPLICATE_EVENT'))


if __name__ == '__main__':
    unittest.main()
