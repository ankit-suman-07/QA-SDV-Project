"""Mock HTTP B2 component tests; these are not live Eclipse Ditto evidence."""
import copy
import importlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import requests
from ditto.mqtt_ingress import Ingress, EventError, WatermarkError
from ditto.mqtt_subscriber import Subscriber, MqttConfig
from test_mqtt_ingress import fixture


def response(status, body=None, raw=None):
    result = Mock(status_code=status)
    result.content = raw if raw is not None else json.dumps(body).encode()
    return result


class FakeDitto:
    """Opt-in test-only store, including create-only provisioning semantics."""
    def __init__(self):
        self.things = {}
        self.policies = {}
        self.calls = []
        self.fail = {}

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, copy.deepcopy(kwargs)))
        if 'data' in kwargs:
            kwargs['json'] = json.loads(kwargs['data'])
        kind, identity, *tail = url.split('/api/2/')[1].split('/')
        store = self.things if kind == 'things' else self.policies
        if identity in self.fail:
            return response(self.fail[identity])
        if method == 'GET':
            return response(200, store[identity]) if identity in store else response(404)
        if tail:
            if identity not in store:
                return response(404)
            store[identity].setdefault('features', {})['v1'] = {'properties': copy.deepcopy(kwargs['json'])}
            return response(204)
        if identity in store:
            return response(412)
        if kwargs['headers'].get('If-None-Match') != '*':
            raise AssertionError('provisioning must always be create-only')
        store[identity] = copy.deepcopy(kwargs['json'])
        store[identity]['thingId' if kind == 'things' else 'policyId'] = identity
        return response(201)


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/v1_writer.py').exists(),
                        'B2 production writer is missing')
        self.m = importlib.import_module('ditto.v1_writer')
        self.config = self.m.DittoConfig(base_url='http://ditto:8080', username='ditto', password='secret')
        self.http = FakeDitto()
        self.writer = self.m.DittoWriter(self.config, request=self.http, sleeper=lambda _: None)

    def provision(self):
        self.writer.provision('nginx:ditto')

    def send(self, ingress, name):
        event = fixture(name)
        return ingress.process('sdv/' + event['vehicleId'] + '/health', json.dumps(event))

    def test_provision_twice_preserves_legacy_and_v1_state(self):
        self.provision()
        one = self.http.things['sdv:vehicle-001']
        one['features'] = {'signals': {'properties': {'speedKph': 12}}}
        self.send(Ingress(self.writer), 'vehicle-001-healthy')
        before = copy.deepcopy(self.http.things)
        calls = len(self.http.calls)
        self.provision()
        self.assertEqual(before, self.http.things)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.http.calls[calls:]))
        self.assertEqual(2, len(self.http.policies))
        self.assertTrue(all('v1' not in thing.get('features', {})
                            for key, thing in self.http.things.items() if key.endswith('002')))

    def test_cycle_atomic_payload_context_and_isolation(self):
        self.provision()
        ingress = Ingress(self.writer)
        self.send(ingress, 'vehicle-001-healthy')
        one = copy.deepcopy(self.http.things['sdv:vehicle-001'])
        for name in ['vehicle-002-healthy', 'vehicle-002-fault', 'vehicle-002-recovered']:
            event = fixture(name)
            event.update(actionId='action', traceId='trace')
            ingress.process('sdv/vehicle-002/health', json.dumps(event))
            properties = self.http.things['sdv:vehicle-002']['features']['v1']['properties']
            expected = dict(event)
            expected['lastEventId'] = expected.pop('eventId')
            self.assertEqual(expected, properties)
            self.assertEqual(one, self.http.things['sdv:vehicle-001'])
        puts = [(url, kw) for method, url, kw in self.http.calls if method == 'PUT' and '/features/' in url]
        self.assertEqual(4, len(puts))
        self.assertTrue(all(url.endswith('/features/v1/properties') for url, _ in puts))
        for _, kw in puts:
            self.assertEqual(('ditto', 'secret'), kw['auth'])
            self.assertFalse(kw['allow_redirects'])
            self.assertTrue(kw['verify'])
            self.assertEqual('application/json', kw['headers']['Accept'])

    def assert_large_event_roundtrip(self, event):
        self.provision()
        wire = json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.assertLessEqual(len(wire), 65536)
        ingress = Ingress(self.writer)
        ingress.process('sdv/vehicle-002/health', wire)
        properties = self.http.things['sdv:vehicle-002']['features']['v1']['properties']
        expected = dict(event)
        expected['lastEventId'] = expected.pop('eventId')
        self.assertEqual(expected, properties)
        put = [kw for method, url, kw in self.http.calls if method == 'PUT' and '/features/' in url][-1]
        self.assertEqual(expected, json.loads(put['data']))
        self.assertEqual(json.dumps(expected, ensure_ascii=False, separators=(',', ':')).encode(), put['data'])
        # Fake GET deliberately ASCII-escapes Unicode: persisted responses do not
        # inherit the MQTT payload budget, whatever encoding the server chooses.
        restarted = Ingress(self.m.DittoWriter(self.config, request=self.http))
        with self.assertRaises(EventError) as caught:
            restarted.process('sdv/vehicle-002/health', wire)
        self.assertEqual('DUPLICATE_EVENT', caught.exception.code)
        event['eventId'] += '-next'
        event['sourceTimestamp'] = '2026-01-01T00:00:01Z'
        event['extension'] = event['extension'][:-5]  # keep the longer ID within the wire budget
        restarted.process('sdv/vehicle-002/health',
                          json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode())
        self.assertEqual((event['eventId'], event['sourceTimestamp']),
                         self.writer.load_watermark('vehicle-002'))

    def test_unicode_event_persists_without_reserialization_block_and_restarts(self):
        event = fixture()
        event.update(eventId='event-\u00e9', actionId='action-\u00e9', traceId='trace-\u00e9')
        event['extension'] = '\u00e9' * 30000
        self.assertGreater(len(json.dumps(event).encode()), 65536)
        self.assert_large_event_roundtrip(event)

    def test_exact_wire_limit_persists_and_larger_state_recovers(self):
        event = fixture()
        event['extension'] = ''
        overhead = len(json.dumps(event, separators=(',', ':')).encode())
        event['extension'] = 'a' * (65536 - overhead)
        self.assertEqual(65536, len(json.dumps(event, separators=(',', ':')).encode()))
        self.assert_large_event_roundtrip(event)

    def test_oversized_wire_is_rejected_before_any_ditto_io(self):
        for extension in ['a' * 65536, '\u00e9' * 33000]:
            event = fixture()
            event['extension'] = extension
            wire = json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode()
            self.assertGreater(len(wire), 65536)
            with self.assertRaises(EventError) as caught:
                Ingress(self.writer).process('sdv/vehicle-002/health', wire)
            self.assertEqual('MALFORMED_JSON', caught.exception.code)
        self.assertEqual([], self.http.calls)

    def test_persisted_state_semantics_do_not_inherit_wire_budget(self):
        self.provision()
        event = fixture()
        event['extension'] = 'a' * 80000
        properties = dict(event)
        properties['lastEventId'] = properties.pop('eventId')
        self.writer.persist('vehicle-002', properties)
        self.assertEqual((event['eventId'], event['sourceTimestamp']),
                         self.writer.load_watermark('vehicle-002'))

    def test_unicode_message_is_acknowledged_after_real_writer_persists(self):
        self.provision()
        client = Mock()
        client.subscribe.return_value = (0, 1)
        acknowledged = threading.Event()
        def ack(mid, qos):
            acknowledged.set()
            return 0
        client.ack.side_effect = ack
        subscriber = Subscriber(Ingress(self.writer), MqttConfig(), client=client)
        self.addCleanup(subscriber.stop)
        subscriber.on_connect(client, None, {}, 0, None)
        event = fixture()
        event['extension'] = '\u00e9' * 30000
        subscriber.on_message(client, None, SimpleNamespace(topic='sdv/vehicle-002/health',
            payload=json.dumps(event, ensure_ascii=False).encode(), qos=1, mid=1, retain=False))
        self.assertTrue(acknowledged.wait(2), 'valid Unicode message blocked before ACK')
        subscriber.wait_idle()
        self.assertEqual(event['eventId'], self.writer.load_watermark('vehicle-002')[0])
        client.ack.assert_called_once_with(1, 1)

    def test_missing_state_is_allowed_only_when_feature_is_absent(self):
        self.provision()
        self.assertIsNone(self.writer.load_watermark('vehicle-001'))
        thing = self.http.things['sdv:vehicle-001']
        for invalid in [None, {}, {'properties': None}, {'properties': {}}, []]:
            thing['features'] = {'v1': invalid}
            with self.subTest(invalid=invalid), self.assertRaises(WatermarkError):
                self.writer.load_watermark('vehicle-001')
        thing['features'] = None
        with self.assertRaises(WatermarkError):
            self.writer.load_watermark('vehicle-001')

    def test_identity_and_persisted_schema_are_validated(self):
        twin = json.loads((Path(__file__).parent / 'fixtures/v1/ditto-vehicle-001.json').read_text())
        for path, value in [('thingId', 'sdv:vehicle-002'), ('attributes', {'vehicleId': 'vehicle-002'}),
                            ('features', {'v1': {'properties': {'vehicleId': 'vehicle-002'}}})]:
            invalid = copy.deepcopy(twin)
            invalid[path] = value
            self.http.things['sdv:vehicle-001'] = invalid
            with self.subTest(path=path), self.assertRaises(WatermarkError):
                self.writer.load_watermark('vehicle-001')
        self.http.things['sdv:vehicle-001'] = twin
        self.assertEqual(('vehicle-001-event-000', '2026-01-01T00:00:00Z'),
                         self.writer.load_watermark('vehicle-001'))
        twin['features']['v1']['properties']['health'] = 'CRITICAL'
        with self.assertRaises(WatermarkError):
            self.writer.load_watermark('vehicle-001')

    def test_restart_duplicate_late_failed_write_and_other_vehicle(self):
        self.provision()
        ingress = Ingress(self.writer)
        self.send(ingress, 'vehicle-002-healthy')
        self.http.fail['sdv:vehicle-002'] = 503
        with self.assertRaises(self.m.DittoError):
            self.send(ingress, 'vehicle-002-fault')
        self.send(ingress, 'vehicle-001-healthy')
        del self.http.fail['sdv:vehicle-002']
        self.send(ingress, 'vehicle-002-fault')
        restarted = Ingress(self.m.DittoWriter(self.config, request=self.http))
        for name, code in [('vehicle-002-fault', 'DUPLICATE_EVENT'), ('vehicle-002-healthy', 'OUT_OF_ORDER')]:
            with self.assertRaises(EventError) as caught:
                self.send(restarted, name)
            self.assertEqual(code, caught.exception.code)
        self.send(restarted, 'vehicle-002-recovered')

    def test_bad_reads_never_become_empty_state(self):
        for status in [404, 401, 403, 500, 503, 302]:
            request = Mock(return_value=response(status))
            writer = self.m.DittoWriter(self.config, request=request, sleeper=lambda _: None)
            with self.subTest(status=status), self.assertRaises(self.m.DittoError):
                writer.load_watermark('vehicle-001')
            self.assertEqual(3 if status in (500, 503) else 1, request.call_count)
        for raw in [b'{', b'{"thingId":"x","thingId":"y"}', b'{"x":NaN}']:
            writer = self.m.DittoWriter(self.config, request=Mock(return_value=response(200, raw=raw)))
            with self.assertRaises(WatermarkError):
                writer.load_watermark('vehicle-001')

    def test_transient_retry_and_success_codes(self):
        event = fixture()
        properties = dict(event)
        properties['lastEventId'] = properties.pop('eventId')
        for status in (200, 201, 204):
            request = Mock(side_effect=[requests.Timeout(), response(503), response(status)])
            sleeper = Mock()
            writer = self.m.DittoWriter(self.config, request=request, sleeper=sleeper)
            writer.persist('vehicle-002', properties)
            self.assertEqual(3, request.call_count)
            self.assertEqual([0.2, 0.4], [call.args[0] for call in sleeper.call_args_list])

    def test_persist_rejects_bad_identity_and_properties_before_http(self):
        for vehicle, properties in [('vehicle-999', {}), ('vehicle-002', {}),
                                    ('vehicle-001', {'vehicleId': 'vehicle-002'})]:
            with self.assertRaises(WatermarkError):
                self.writer.persist(vehicle, properties)
        self.assertEqual([], self.http.calls)

    def test_provisioning_does_not_overwrite_mismatched_policy_or_thing(self):
        self.provision()
        self.http.policies['sdv:vehicle-001-policy']['entries'] = {}
        with self.assertRaises(WatermarkError):
            self.provision()
        self.assertEqual({}, self.http.policies['sdv:vehicle-001-policy']['entries'])

    def test_later_policy_entry_revocation_is_not_hidden_by_root_grant(self):
        self.provision()
        policy = self.http.policies['sdv:vehicle-001-policy']
        policy['entries']['blocked'] = {'subjects': {'nginx:ditto': {}},
            'resources': {'thing:/features/v1': {'grant': [], 'revoke': ['WRITE']}}}
        with self.assertRaises(self.m.DittoError):
            self.provision()

    def test_wrong_policy_binding_and_invalid_json_null_are_not_fresh_twins(self):
        self.provision()
        self.http.things['sdv:vehicle-001']['policyId'] = 'someone-elses-policy'
        before = copy.deepcopy(self.http.things)
        with self.assertRaises(WatermarkError):
            self.provision()
        self.assertEqual(before, self.http.things)
        writer = self.m.DittoWriter(self.config, request=Mock(return_value=response(200, raw=b'null')))
        with self.assertRaises(WatermarkError):
            writer.load_watermark('vehicle-001')

    def test_real_writer_consumer_acknowledges_only_after_http_success(self):
        self.provision()
        client = Mock()
        client.subscribe.return_value = (0, 1)
        client.ack.return_value = 0
        subscriber = Subscriber(Ingress(self.writer), MqttConfig(retry_seconds=0.01), client=client)
        self.addCleanup(subscriber.stop)
        subscriber.on_connect(client, None, {}, 0, None)
        failed, other_done = threading.Event(), threading.Event()
        original = self.writer._request
        def request(method, url, **kwargs):
            if method == 'PUT' and '/features/' in url and 'vehicle-002/' in url and not other_done.is_set():
                failed.set()
                return response(503)
            return original(method, url, **kwargs)
        self.writer._request = request
        event = fixture()
        subscriber.on_message(client, None, SimpleNamespace(topic='sdv/vehicle-002/health',
            payload=json.dumps(event).encode(), qos=1, mid=1, retain=False))
        self.assertTrue(failed.wait(1))
        client.ack.assert_not_called()
        def ack(mid, qos):
            if mid == 2:
                other_done.set()
            return 0
        client.ack.side_effect = ack
        event = fixture('vehicle-001-healthy')
        subscriber.on_message(client, None, SimpleNamespace(topic='sdv/vehicle-001/health',
            payload=json.dumps(event).encode(), qos=1, mid=2, retain=False))
        self.assertTrue(other_done.wait(1))
        subscriber.wait_idle()
        self.assertEqual(2, client.ack.call_count)
        self.assertEqual('vehicle-002-event-000', self.writer.load_watermark('vehicle-002')[0])

    def test_real_requests_against_loopback_mock_http(self):
        """Real HTTP serialization/auth; server still a mock, not Eclipse Ditto."""
        backend = self.http
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def handle_request(self):
                if self.headers.get('Authorization') != 'Basic ZGl0dG86c2VjcmV0':
                    self.send_response(401)
                    self.end_headers()
                    return
                kwargs = {'headers': dict(self.headers)}
                if self.command == 'PUT':
                    kwargs['json'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result = backend(self.command, 'http://local' + self.path, **kwargs)
                self.send_response(result.status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(result.content)
            do_GET = handle_request
            do_PUT = handle_request
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = self.m.DittoConfig(base_url=f'http://127.0.0.1:{server.server_port}',
                                       username='ditto', password='secret')
            writer = self.m.DittoWriter(config)
            writer.provision('nginx:ditto')
            self.send(Ingress(writer), 'vehicle-002-fault')
            self.assertEqual('vehicle-002-event-001', writer.load_watermark('vehicle-002')[0])
            self.assertIsNone(writer.load_watermark('vehicle-001'))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_configuration_validation_and_secret_redaction(self):
        self.assertNotIn('secret', repr(self.config))
        for url in ['ftp://ditto', 'http://user:secret@ditto', 'http://ditto?x=y']:
            with self.assertRaises(ValueError):
                self.m.DittoConfig(base_url=url, username='u', password='p')
        for overrides in [{'attempts': 0}, {'timeout_seconds': float('nan')}, {'password': ''}]:
            values = dict(base_url='http://ditto', username='u', password='p')
            values.update(overrides)
            with self.assertRaises(ValueError):
                self.m.DittoConfig(**values)


if __name__ == '__main__':
    unittest.main()
