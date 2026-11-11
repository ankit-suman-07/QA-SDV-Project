"""Local mock HTTP and MQTT-tool checks; no live Eclipse dependencies."""
import copy
import importlib
import json
import socket
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.v1_dev import contract as c

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def running_server(state, service, vehicle=None):
    from scripts.v1_dev.http_mocks import make_server
    try:
        server = make_server(state, service, vehicle, port=0)
    except PermissionError as error:
        raise unittest.SkipTest('local sockets unavailable: ' + str(error)) from error
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_address[1])
    finally:
        server.shutdown(); server.server_close(); thread.join()


def request(base, path, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(base + path, data=data, method=method,
                  headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=1) as response:
            return response.status, json.load(response), response.headers
    except HTTPError as error:
        return error.code, json.load(error), error.headers


class MockTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'scripts/v1_dev/http_mocks.py').exists(), 'HTTP mocks not implemented')
        self.h = importlib.import_module('scripts.v1_dev.http_mocks')
        self.state = self.h.MockState()
        self.state.delay_seconds = .15

    def test_ditto_reads_and_atomic_feature_identity(self):
        with running_server(self.state, 'ditto') as base:
            for vehicle in c.VEHICLES:
                status, body, headers = request(base, '/api/2/things/sdv:' + vehicle)
                self.assertEqual(200, status); self.assertEqual(vehicle, body['attributes']['vehicleId'])
                self.assertEqual('true', headers['X-SDV-Mock'])
            props = c.event_to_twin(self.state.load_event('vehicle-002-fault'))['features']['v1']['properties']
            self.assertEqual(200, request(base, '/api/2/things/sdv:vehicle-002/features/v1/properties', props, 'PUT')[0])
            self.assertEqual('HEALTHY', self.state.view('vehicle-001')['healthStatus'])
            self.assertEqual('CRITICAL', self.state.view('vehicle-002')['healthStatus'])
            self.assertEqual(400, request(base, '/api/2/things/sdv:vehicle-001/features/v1/properties', props, 'PUT')[0])

    def test_mock_state_controls_and_freshness(self):
        with running_server(self.state, 'ditto') as base:
            self.assertEqual(200, request(base, '/_mock/states/vehicle-002', {'state': 'stale'})[0])
            self.assertEqual('STALE', self.state.view('vehicle-002')['availability'])
            for state_name, expected in [('missing', 404), ('unavailable', 503)]:
                request(base, '/_mock/states/vehicle-002', {'state': state_name})
                self.assertEqual(expected, request(base, '/api/2/things/sdv:vehicle-002')[0])
                self.assertIsNone(self.state.view('vehicle-002')['healthStatus'])
            request(base, '/_mock/states/vehicle-002', {'state': 'healthy'})
            request(base, '/_mock/clock', {'now': '2026-01-01T00:00:10Z'})
            self.assertEqual('STALE', self.state.view('vehicle-002')['availability'])
            self.assertEqual('HEALTHY', self.state.view('vehicle-001')['healthStatus'])

    def test_provider_routing_identity_context_and_clear(self):
        with running_server(self.state, 'provider', 'vehicle-001') as one:
            with running_server(self.state, 'provider', 'vehicle-002') as two:
                endpoints = {'vehicle-001': one, 'vehicle-002': two}
                body = dict(self.state.load('scenario-inject-request'), actionId='a', traceId='t')
                result = self.h.dispatch(endpoints, body)
                self.assertTrue(result['active']); self.assertEqual('vehicle-002', result['vehicleId'])
                path = '/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION'
                self.assertEqual('a', request(two, path)[1]['actionId'])
                self.assertEqual('HEALTHY', self.state.view('vehicle-001')['healthStatus'])
                self.assertEqual('CRITICAL', self.state.view('vehicle-002')['healthStatus'])
                self.assertEqual(404, request(one, '/api/v1/scenarios/COOLING_SYSTEM_FAILURE')[0])
                self.assertEqual(404, request(one, '/api/v1/scenarios/actions', body)[0])
                body['action'] = 'CLEAR_SCENARIO'; self.h.dispatch(endpoints, body)
                self.assertEqual('HEALTHY', self.state.view('vehicle-002')['healthStatus'])
                self.assertEqual(2, len(self.state.dispatches))
                self.assertTrue(all(x['vehicleId'] == 'vehicle-002' for x in self.state.dispatches))

    def test_provider_rejection_timeout_and_connection_failure(self):
        with running_server(self.state, 'provider', 'vehicle-002') as base:
            body = dict(self.state.load('scenario-inject-request'), actionId='a', traceId='t')
            for mode, code in [('reject', 'PROVIDER_REJECTED'), ('timeout', 'PROVIDER_TIMEOUT'),
                               ('disconnect', 'PROVIDER_UNAVAILABLE')]:
                self.state.failure['vehicle-002'] = mode
                with self.subTest(mode=mode), self.assertRaisesRegex(c.ContractError, code):
                    self.h.dispatch({'vehicle-002': base}, body, timeout=.03)
            self.assertEqual([], self.state.dispatches)
        with socket.socket() as held:
            held.bind(('127.0.0.1', 0))
            # Bound but not listening: a deterministic refused connection.
            with self.assertRaisesRegex(c.ContractError, 'PROVIDER_UNAVAILABLE'):
                self.h.dispatch({'vehicle-002': 'http://127.0.0.1:' + str(held.getsockname()[1])}, body)

    def test_preview_apis_are_explicit_mocks_and_count_fault_and_recovery(self):
        with running_server(self.state, 'backend') as base:
            self.assertEqual(2, request(base, '/api/v1/fleet')[1]['healthyVehicles'])
            body = self.state.load('scenario-inject-request')
            status, accepted, _ = request(base, '/api/v1/diagnostics/actions', body)
            self.assertEqual(202, status); self.assertEqual('ACCEPTED', accepted['status'])
            self.assertEqual('DISPATCHED', accepted['dispatchStatus'])
            self.assertEqual('ACCEPTED', request(base, '/api/v1/diagnostics/actions/' + accepted['actionId'])[1]['status'])
            self.assertEqual(1, request(base, '/api/v1/fleet')[1]['criticalVehicles'])
            request(base, '/api/v1/diagnostics/actions', self.state.load('scenario-clear-request'))
            self.assertEqual(2, request(base, '/api/v1/fleet')[1]['healthyVehicles'])
            self.assertEqual(404, request(base, '/api/vehicles/vehicle-999/state')[0])
            self.assertEqual(404, request(base, '/api/v1/diagnostics/actions/missing')[0])

    def test_invalid_mock_controls_do_not_mutate_state(self):
        with running_server(self.state, 'ditto') as base:
            before = copy.deepcopy(self.state.twins)
            self.assertEqual(400, request(base, '/_mock/states/vehicle-002', {'state': 'invented'})[0])
            self.assertEqual(400, request(base, '/_mock/clock', {'now': 'invalid'})[0])
            self.assertEqual(before, self.state.twins)


class MqttToolTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'scripts/v1_dev/mqtt.py').exists(), 'MQTT tools not implemented')
        self.m = importlib.import_module('scripts.v1_dev.mqtt')

    def test_replay_selects_topics_and_preserves_order(self):
        packets = self.m.replay_packets('cycle', c.EPOCH)
        capture = c.Capture()
        for mqtt_topic, event in packets:
            capture.accept(mqtt_topic, event)
        self.assertTrue(capture.cycle_complete())
        for name in ['malformed', 'unknown', 'out-of-order']:
            self.assertTrue(self.m.replay_packets(name, c.EPOCH))

    def test_capture_lines_checks_cycle_and_fails_invalid_input(self):
        packets = self.m.replay_packets('cycle', c.EPOCH)
        lines = [t + ' ' + json.dumps(e) for t, e in packets]
        self.assertTrue(self.m.check_lines(lines, expect_cycle=True)['cycleComplete'])
        with self.assertRaisesRegex(c.ContractError, 'INCOMPLETE_CYCLE'):
            self.m.check_lines(lines[:2], expect_cycle=True)
        with self.assertRaises(c.ContractError):
            self.m.check_lines(['sdv/vehicle-001/health not-json'])
        with self.assertRaises(c.ContractError):
            self.m.check_lines(lines[:2] + ['sdv/vehicle-001/health ' + json.dumps(packets[2][1])])

    def test_publisher_executes_cli_without_shell_and_checks_exit_status(self):
        with patch('scripts.v1_dev.mqtt.subprocess.run') as run, patch('builtins.print'):
            self.m.publish_packets(self.m.replay_packets('cycle', c.EPOCH), '127.0.0.1', 1883, interval=0)
            self.assertEqual(4, run.call_count)
            kwargs = run.call_args.kwargs
            self.assertTrue(kwargs['check']); self.assertNotIn('shell', kwargs)
            self.assertIn('-q', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
