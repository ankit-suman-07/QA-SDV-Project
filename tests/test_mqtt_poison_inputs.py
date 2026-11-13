"""PR30-F01/F02 regressions: fake MQTT and in-memory HTTP, never live services."""
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from ditto.mqtt_ingress import Ingress, EventError, decode_event, validate_event
from ditto.mqtt_subscriber import Subscriber, MqttConfig
from ditto.v1_writer import DittoConfig, DittoWriter, WatermarkError
from test_mqtt_ingress import fixture


TOPIC = 'sdv/vehicle-002/health'


def wire_extension(raw):
    return (json.dumps(fixture())[:-1] + ', "extension":' + raw + '}').encode()


class MemoryHTTP:
    """Store decoded Things using JSON only, avoiding recursive test deepcopy."""
    def __init__(self):
        self.things = {f'sdv:{v}': {'thingId': f'sdv:{v}',
                      'attributes': {'vehicleId': v}, 'features': {}}
                      for v in ('vehicle-001', 'vehicle-002')}
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        identity = url.split('/api/2/things/')[1].split('/')[0]
        if method == 'PUT':
            self.things[identity]['features']['v1'] = {'properties': json.loads(kwargs['data'])}
        return SimpleNamespace(status_code=200 if method == 'GET' else 204,
                               content=json.dumps(self.things[identity]).encode())


class PoisonInputTests(unittest.TestCase):
    def setUp(self):
        self.http = MemoryHTTP()
        self.writer = DittoWriter(DittoConfig('http://mock.invalid', 'test', 'test'),
                                 request=self.http, sleeper=lambda _: None)
        self.ingress = Ingress(self.writer)

    def send(self, event, ingress=None):
        return (ingress or self.ingress).process('sdv/' + event['vehicleId'] + '/health',
                                                json.dumps(event).encode())

    def test_deep_arrays_and_dictionaries_persist_and_recover_watermark(self):
        for depth in (599, 600, 601, 1400):
            for array in (True, False):
                with self.subTest(depth=depth, array=array):
                    self.setUp()
                    raw = '[' * depth + '0' + ']' * depth if array else (
                        '{"child":' * depth + '0' + '}' * depth)
                    wire = wire_extension(raw)
                    self.assertLess(len(wire), 65536)
                    event = self.ingress.process(TOPIC, wire)
                    props = self.http.things['sdv:vehicle-002']['features']['v1']['properties']
                    copied, original = props['extension'], event['extension']
                    for _ in range(depth):
                        self.assertIsNot(copied, original)
                        copied = copied[0] if array else copied['child']
                        original = original[0] if array else original['child']
                    self.assertEqual(0, copied)
                    restarted = Ingress(self.writer)
                    with self.assertRaises(EventError) as caught:
                        restarted.process(TOPIC, wire)
                    self.assertEqual('DUPLICATE_EVENT', caught.exception.code)
                    self.send(fixture('vehicle-002-fault'), restarted)
                    with self.assertRaises(EventError) as caught:
                        self.send(fixture(), restarted)
                    self.assertEqual('OUT_OF_ORDER', caught.exception.code)
                    self.send(fixture('vehicle-002-recovered'), restarted)
                    self.assertEqual({}, self.http.things['sdv:vehicle-001']['features'])

    def test_unsupported_codec_depth_rejected_before_io_then_both_vehicles_progress(self):
        depth = 5000
        for raw in ('[' * depth + '0' + ']' * depth,
                    '{"child":' * depth + '0' + '}' * depth):
            with self.assertRaises(EventError) as caught:
                self.ingress.process(TOPIC, wire_extension(raw))
            self.assertEqual('MALFORMED_JSON', caught.exception.code)
        self.assertEqual([], self.http.calls)
        self.assertEqual({}, self.ingress._committed)
        self.send(fixture())
        self.send(fixture('vehicle-001-healthy'))
        self.assertEqual(2, sum(method == 'PUT' for method, _, _ in self.http.calls))

    def bad_events(self):
        for surrogate in ('\ud800', '\udfff'):
            for key in ('eventId', 'actionId', 'traceId', 'extension'):
                event = fixture()
                event[key] = surrogate
                yield event
            for extension in ({surrogate: 'value'}, {'nested': [0, {surrogate: 'value'}]},
                              {'nested': [0, surrogate]}):
                event = fixture()
                event['extension'] = extension
                yield event
            event = fixture()
            event[surrogate] = 'extension key'
            yield event
            event = fixture()
            nested = {surrogate: surrogate}
            for _ in range(600):
                nested = [nested]
            event['extension'] = nested
            yield event

    def test_lone_surrogates_values_keys_and_identifiers_reject_before_any_io(self):
        for index, event in enumerate(self.bad_events()):
            with self.subTest(case=index):
                for check in (lambda: self.send(event),
                              lambda: validate_event(TOPIC, event)):
                    with self.assertRaises(EventError) as caught:
                        check()
                    self.assertEqual('MALFORMED_JSON', caught.exception.code)
        self.assertEqual([], self.http.calls)
        self.assertEqual({}, self.ingress._committed)
        self.send(fixture())
        self.send(fixture('vehicle-001-healthy'))

    def test_valid_unicode_nonbmp_and_escaped_surrogate_pairs_roundtrip(self):
        event = fixture()
        event.update(eventId='event-\U0001f697', actionId='action-\u00e9', traceId='trace-\U0001f680')
        event['extension'] = {'\U0001f697': ['\u00e9', '\U0001f680']}
        wire = json.dumps(event).encode()  # Non-BMP characters are valid pair escapes.
        self.assertIn(b'\\ud83d\\ude97', wire)
        self.ingress.process(TOPIC, wire)
        props = self.http.things['sdv:vehicle-002']['features']['v1']['properties']
        self.assertEqual(event['extension'], props['extension'])
        self.assertEqual(event['eventId'], props['lastEventId'])
        self.assertEqual(event['actionId'], props['actionId'])
        put = next(kw['data'] for method, _, kw in self.http.calls if method == 'PUT')
        self.assertIn('\U0001f697'.encode(), put)
        self.assertEqual((event['eventId'], event['sourceTimestamp']),
                         self.writer.load_watermark('vehicle-002'))

    def subscriber(self, queue_size=1):
        client = Mock()
        client.subscribe.return_value = (0, 1)
        condition = threading.Condition()
        acknowledgments = []
        def ack(mid, qos):
            with condition:
                acknowledgments.append(mid)
                condition.notify_all()
            return 0
        client.ack.side_effect = ack
        subscriber = Subscriber(self.ingress, MqttConfig(queue_size=queue_size, retry_seconds=0.01),
                                client=client)
        self.addCleanup(subscriber.stop)
        subscriber.on_connect(client, None, {}, 0, None)
        return subscriber, client, condition, acknowledgments

    def deliver(self, subscriber, client, wire, mid, topic=TOPIC):
        subscriber.on_message(client, None, SimpleNamespace(topic=topic, payload=wire,
                              qos=1, retain=False, mid=mid))

    def test_rejected_poison_flood_never_enters_writer_queue_or_retry(self):
        subscriber, client, condition, acks = self.subscriber()
        process = Mock(wraps=self.ingress.process)
        self.ingress.process = process
        bad = [json.dumps(event).encode() for event in self.bad_events()]
        bad.append(wire_extension('[' * (5000) + '0' +
                                  ']' * (5000)))
        for mid, wire in enumerate(bad, 1):
            self.deliver(subscriber, client, wire, mid)
            self.assertIn(mid, acks, 'Invalid input must be rejected/ACKed before queueing')
        process.assert_not_called()
        self.assertEqual([], self.http.calls)
        self.assertEqual({}, self.ingress._committed)
        self.assertIsNone(subscriber._fatal)
        for mid, name in ((100, 'vehicle-002-healthy'), (101, 'vehicle-001-healthy')):
            event = fixture(name)
            self.deliver(subscriber, client, json.dumps(event).encode(), mid,
                         'sdv/' + event['vehicleId'] + '/health')
        with condition:
            self.assertTrue(condition.wait_for(lambda: 100 in acks and 101 in acks, timeout=2))
        self.assertEqual(2, process.call_count)
        self.assertEqual(2, sum(method == 'PUT' for method, _, _ in self.http.calls))
        self.assertIsNone(subscriber._fatal)

    def test_600_level_input_and_later_events_are_persisted_and_acked_once(self):
        subscriber, client, condition, acks = self.subscriber(queue_size=2)
        process = Mock(wraps=self.ingress.process)
        self.ingress.process = process
        self.deliver(subscriber, client, wire_extension('[' * 600 + '0' + ']' * 600), 1)
        with condition:
            self.assertTrue(condition.wait_for(lambda: 1 in acks, timeout=2))
        for mid, name in ((2, 'vehicle-002-fault'), (3, 'vehicle-001-healthy')):
            event = fixture(name)
            self.deliver(subscriber, client, json.dumps(event).encode(), mid,
                         'sdv/' + event['vehicleId'] + '/health')
        with condition:
            self.assertTrue(condition.wait_for(lambda: len(acks) == 3, timeout=2))
        self.assertEqual(3, process.call_count)
        self.assertEqual([1, 2, 3], sorted(acks))
        self.assertIsNone(subscriber._fatal)

    def test_transient_http_failure_withholds_ack_and_watermark_until_success(self):
        subscriber, client, condition, acks = self.subscriber(queue_size=2)
        failed, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        original = self.writer._request
        def request(method, url, **kw):
            if method == 'PUT' and 'vehicle-002/' in url and not release.is_set():
                failed.set()
                return SimpleNamespace(status_code=503)
            return original(method, url, **kw)
        self.writer._request = request
        self.deliver(subscriber, client, json.dumps(fixture()).encode(), 1)
        self.assertTrue(failed.wait(1))
        self.assertNotIn(1, acks)
        self.assertIsNone(self.ingress._committed.get('vehicle-002'))
        self.assertEqual({}, self.http.things['sdv:vehicle-002']['features'])
        other = fixture('vehicle-001-healthy')
        self.deliver(subscriber, client, json.dumps(other).encode(), 2, 'sdv/vehicle-001/health')
        with condition:
            self.assertTrue(condition.wait_for(lambda: 2 in acks, timeout=2))
        self.assertNotIn(1, acks)
        release.set()
        with condition:
            self.assertTrue(condition.wait_for(lambda: 1 in acks, timeout=2))
        self.assertEqual(fixture()['eventId'], self.writer.load_watermark('vehicle-002')[0])

    def test_deterministic_local_serialization_is_input_error_without_http_retry(self):
        # The serializer fails before dispatch, unlike a timeout/failed read.
        for invalid in ({'extension': '\ud800'}, {'extension': object()}):
            with self.assertRaises(EventError):
                self.writer._http('PUT', 'things/sdv:vehicle-002/features/v1/properties', value=invalid)
        self.assertEqual([], self.http.calls)

    def test_local_serialization_error_is_not_reclassified_as_watermark_failure(self):
        original = self.writer.persist
        def unencodable(vehicle, properties):
            self.writer._http('PUT', 'things/sdv:vehicle-002/features/v1/properties',
                              value={'extension': object()})
        self.writer.persist = unencodable
        with self.assertRaises(EventError):
            self.send(fixture())
        self.assertFalse(any(method == 'PUT' for method, _, _ in self.http.calls))
        self.assertIsNone(self.ingress._committed.get('vehicle-002'))
        self.writer.persist = original
        self.send(fixture())
        self.send(fixture('vehicle-001-healthy'))

    def test_rejected_input_preserves_committed_snapshot_and_later_fault_recovery(self):
        self.send(fixture())
        before = json.dumps(self.http.things, sort_keys=True)
        watermark = dict(self.ingress._committed)
        calls = len(self.http.calls)
        for event in self.bad_events():
            with self.assertRaises(EventError):
                self.send(event)
        with self.assertRaises(EventError):
            self.ingress.process(TOPIC, wire_extension('[' * 5000 + '0' + ']' * 5000))
        self.assertEqual(before, json.dumps(self.http.things, sort_keys=True))
        self.assertEqual(watermark, self.ingress._committed)
        self.assertEqual(calls, len(self.http.calls))
        self.send(fixture('vehicle-002-fault'))
        self.send(fixture('vehicle-002-recovered'))
        self.send(fixture('vehicle-001-healthy'))
        self.assertEqual('vehicle-002-event-002', self.writer.load_watermark('vehicle-002')[0])
