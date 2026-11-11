"""Exercise actual HTTP handlers with byte streams; no socket permissions needed."""
import io
import json
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.v1_dev import contract as c
from scripts.v1_dev.http_mocks import MockState, dispatch, make_handler


def call(state, service, path, body=None, vehicle=None, method=None, raw=None):
    handler = make_handler(state, service, vehicle).__new__(make_handler(state, service, vehicle))
    handler.path = path
    handler.command = method or ('POST' if body is not None or raw is not None else 'GET')
    handler.request_version = 'HTTP/1.1'
    handler.requestline = handler.command + ' ' + path + ' HTTP/1.1'
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b'')
    handler.headers = Message(); handler.headers['Content-Length'] = str(len(data))
    handler.rfile = io.BytesIO(data); handler.wfile = io.BytesIO()
    getattr(handler, 'do_' + handler.command)()
    header, payload = handler.wfile.getvalue().split(b'\r\n\r\n', 1)
    return int(header.split()[1]), json.loads(payload), header.decode()


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.state = MockState()

    def test_ditto_routes_isolation_and_missing_unavailable(self):
        for vehicle in c.VEHICLES:
            code, twin, headers = call(self.state, 'ditto', '/api/2/things/sdv:' + vehicle)
            self.assertEqual(200, code); self.assertEqual(vehicle, twin['attributes']['vehicleId'])
            self.assertIn('X-SDV-Mock: true', headers)
        props = c.event_to_twin(self.state.load_event('vehicle-002-fault'))['features']['v1']['properties']
        path = '/api/2/things/sdv:vehicle-002/features/v1/properties'
        self.assertEqual(200, call(self.state, 'ditto', path, props, method='PUT')[0])
        self.assertEqual(props, call(self.state, 'ditto', path)[1])
        self.assertEqual('HEALTHY', self.state.view('vehicle-001')['healthStatus'])
        self.assertEqual(400, call(self.state, 'ditto', path.replace('002', '001'), props, method='PUT')[0])
        for state, code in [('missing', 404), ('unavailable', 503)]:
            self.state.set_state('vehicle-002', state)
            self.assertEqual(code, call(self.state, 'ditto', '/api/2/things/sdv:vehicle-002')[0])
            self.assertIsNone(self.state.view('vehicle-002')['healthStatus'])

    def test_provider_contract_inject_clear_and_identity(self):
        body = dict(self.state.load('scenario-inject-request'), actionId='a', traceId='t')
        path = '/api/v1/scenarios/actions'
        self.assertEqual(404, call(self.state, 'provider', path, body, vehicle='vehicle-001')[0])
        code, accepted, _ = call(self.state, 'provider', path, body, vehicle='vehicle-002')
        self.assertEqual(200, code); self.assertEqual('t', accepted['traceId'])
        context = '/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION'
        self.assertEqual(accepted, call(self.state, 'provider', context, vehicle='vehicle-002')[1])
        self.assertEqual('HEALTHY', self.state.view('vehicle-001')['healthStatus'])
        self.assertEqual('CRITICAL', self.state.view('vehicle-002')['healthStatus'])
        body['action'] = 'CLEAR_SCENARIO'
        self.assertEqual(200, call(self.state, 'provider', path, body, vehicle='vehicle-002')[0])
        self.assertEqual('HEALTHY', self.state.view('vehicle-002')['healthStatus'])
        self.assertEqual(404, call(self.state, 'provider', '/api/v1/scenarios/COOLING_SYSTEM_FAILURE', vehicle='vehicle-002')[0])

    def test_controls_clock_failures_and_invalid_requests(self):
        self.assertEqual(200, call(self.state, 'ditto', '/_mock/states/vehicle-002', {'state': 'stale'})[0])
        self.assertEqual('STALE', self.state.view('vehicle-002')['availability'])
        self.assertEqual(400, call(self.state, 'ditto', '/_mock/clock', {'now': 'invalid'})[0])
        self.assertEqual(400, call(self.state, 'ditto', '/_mock/states/vehicle-002', {'state': 'bad'})[0])
        self.assertEqual(400, call(self.state, 'ditto', '/_mock/clock', raw=b'not json')[0])
        self.assertEqual(200, call(self.state, 'ditto', '/_mock/clock', {'now': '2026-01-01T00:01:00Z'})[0])
        self.assertEqual('UNAVAILABLE', self.state.view('vehicle-001')['availability'])
        body = dict(self.state.load('scenario-inject-request'), actionId='a', traceId='t')
        call(self.state, 'provider', '/_mock/failures/vehicle-002', {'mode': 'reject'}, vehicle='vehicle-002')
        self.assertEqual(409, call(self.state, 'provider', '/api/v1/scenarios/actions', body, vehicle='vehicle-002')[0])
        self.assertEqual([], self.state.dispatches)
        self.assertEqual(400, call(self.state, 'ditto', '/_mock/clock', [], method='POST')[0])

    def test_backend_preview_actions_counts_and_mock_header(self):
        self.assertEqual(2, call(self.state, 'backend', '/api/v1/fleet')[1]['healthyVehicles'])
        code, action, headers = call(self.state, 'backend', '/api/v1/diagnostics/actions', self.state.load('scenario-inject-request'))
        self.assertEqual(202, code); self.assertEqual('ACCEPTED', action['status'])
        self.assertEqual('DISPATCHED', action['dispatchStatus']); self.assertIn('X-SDV-Mock: true', headers)
        self.assertEqual(1, call(self.state, 'backend', '/api/v1/fleet')[1]['criticalVehicles'])
        path = '/api/v1/diagnostics/actions/' + action['actionId']
        self.assertEqual(action, call(self.state, 'backend', path)[1])
        self.assertEqual(404, call(self.state, 'backend', '/api/vehicles/vehicle-999/state')[0])
        self.assertEqual(404, call(self.state, 'backend', '/api/v1/diagnostics/actions/missing')[0])
        call(self.state, 'backend', '/api/v1/diagnostics/actions', self.state.load('scenario-clear-request'))
        self.assertEqual(2, call(self.state, 'backend', '/api/v1/fleet')[1]['healthyVehicles'])

    def test_dispatch_maps_endpoint_and_transport_errors(self):
        body = dict(self.state.load('scenario-inject-request'), actionId='a', traceId='t')
        response = io.BytesIO(json.dumps(dict(body, active=True)).encode())
        with patch('scripts.v1_dev.http_mocks.urlopen', return_value=response) as opened:
            self.assertTrue(dispatch({'vehicle-002': 'http://provider-002:8090'}, body)['active'])
            self.assertEqual('http://provider-002:8090/api/v1/scenarios/actions', opened.call_args.args[0].full_url)
        for error, code in [(TimeoutError(), 'PROVIDER_TIMEOUT'), (URLError('refused'), 'PROVIDER_UNAVAILABLE'),
                            (HTTPError('http://provider', 409, 'reject', {}, io.BytesIO()), 'PROVIDER_REJECTED')]:
            with patch('scripts.v1_dev.http_mocks.urlopen', side_effect=error):
                with self.assertRaisesRegex(c.ContractError, code):
                    dispatch({'vehicle-002': 'http://provider-002'}, body)
        with self.assertRaisesRegex(c.ContractError, 'UNKNOWN_VEHICLE'):
            dispatch({'vehicle-001': 'http://provider-001'}, body)

class VersionedPreviewTests(unittest.TestCase):
    def test_versioned_vehicle_routes_and_list(self):
        state = MockState()
        self.assertEqual({'vehicleIds': list(c.VEHICLES)}, call(state, 'backend', '/api/v1/vehicles')[1])
        for suffix in ['state', 'health']:
            status, body, _ = call(state, 'backend', '/api/v1/vehicles/vehicle-002/' + suffix)
            self.assertEqual(200, status)
            self.assertEqual('vehicle-002', body['vehicleId'])


if __name__ == '__main__':
    unittest.main()
