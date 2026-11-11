"""Development-only Ditto/provider/backend-preview mocks. No production imports.

Run explicitly: python -m scripts.v1_dev.http_mocks --ack-development-only
"""
import argparse
import copy
import json
import socket
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock, Thread
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import Request, urlopen

from . import contract as c

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/v1'


class MockState:
    def __init__(self, now=c.TEST_NOW, live_clock=False):
        self.lock = RLock()
        self.live_clock = live_clock
        self.now = now
        self.anchor = now - c.timedelta(seconds=4)
        self.twins = {v: c.event_to_twin(self.load_event(v + '-healthy')) for v in c.VEHICLES}
        self.states = {v: 'healthy' for v in c.VEHICLES}
        self.failure = {v: 'success' for v in c.VEHICLES}
        self.context = {}
        self.actions = {}
        self.dispatches = []
        self.counter = 0
        self.delay_seconds = 5.

    def clock(self):
        return datetime.now(timezone.utc) if self.live_clock else self.now

    def load(self, name):
        return json.loads((FIXTURES / (name + '.json')).read_text())

    def load_event(self, name):
        return c.rebase_event(self.load(name), self.anchor)

    def set_state(self, vehicle, state):
        c.require(vehicle in c.VEHICLES, 'UNKNOWN_VEHICLE', vehicle)
        c.require(state in ('healthy', 'fault', 'recovered', 'stale', 'missing', 'unavailable'),
                  'INVALID_STATE', state)
        with self.lock:
            if state not in ('missing', 'unavailable'):
                name = 'vehicle-002-' + state if state != 'healthy' else vehicle + '-healthy'
                event = self.load_event(name)
                event['vehicleId'] = vehicle
                self.counter += 1
                event['eventId'] = f'mock-{vehicle}-{self.counter:04d}'
                # State changes are observations now; stale explicitly means six seconds old.
                event['sourceTimestamp'] = c.iso(self.clock() - c.timedelta(seconds=6 if state == 'stale' else 0))
                self.twins[vehicle] = c.event_to_twin(event)
            self.states[vehicle] = state

    def view(self, vehicle):
        c.require(vehicle in c.VEHICLES, 'UNKNOWN_VEHICLE', vehicle)
        with self.lock:
            twin = None if self.states[vehicle] in ('missing', 'unavailable') else self.twins[vehicle]
            return c.vehicle_view(vehicle, twin, self.clock())

    def execute(self, vehicle, body):
        c.require(vehicle == body.get('vehicleId') and vehicle in c.VEHICLES,
                  'UNKNOWN_VEHICLE', 'provider owns only ' + str(vehicle))
        c.require(body.get('action') in ('INJECT_SCENARIO', 'CLEAR_SCENARIO'), 'INVALID_REQUEST', 'action')
        c.require(body.get('scenario') == 'LIDAR_OBSTRUCTION', 'INVALID_REQUEST', 'scenario')
        for key in ('actionId', 'traceId'):
            c.require(isinstance(body.get(key), str) and bool(body[key].strip()), 'INVALID_REQUEST', key)
        mode = self.failure[vehicle]
        if mode == 'reject':
            raise c.ContractError('PROVIDER_REJECTED', 'configured mock rejection')
        if mode == 'timeout':
            time.sleep(self.delay_seconds)
            raise c.ContractError('PROVIDER_TIMEOUT', 'configured mock delay; no execution')
        if mode == 'disconnect':
            raise c.ContractError('PROVIDER_UNAVAILABLE', 'configured disconnect')
        with self.lock:
            active = body['action'] == 'INJECT_SCENARIO'
            self.set_state(vehicle, 'fault' if active else 'recovered')
            result = dict(vehicleId=vehicle, scenario=body['scenario'], active=active,
                          actionId=body['actionId'], traceId=body['traceId'], action=body['action'])
            self.context[vehicle] = result
            self.dispatches.append(copy.deepcopy(result))
            return result


def dispatch(endpoints, body, timeout=2.):
    """Test client for routing/failure assertions, not the Java implementation."""
    vehicle = body.get('vehicleId')
    c.require(vehicle in endpoints, 'UNKNOWN_VEHICLE', 'no configured provider')
    req = Request(endpoints[vehicle].rstrip('/') + '/api/v1/scenarios/actions',
                  data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=timeout) as response:
            result = json.load(response)
        c.require(result.get('vehicleId') == vehicle and result.get('actionId') == body.get('actionId') and
                  result.get('traceId') == body.get('traceId'), 'PROVIDER_REJECTED', 'response identity differs')
        return result
    except HTTPError as error:
        error.close()
        raise c.ContractError('PROVIDER_REJECTED', f'HTTP {error.code}') from error
    except (TimeoutError, socket.timeout) as error:
        raise c.ContractError('PROVIDER_TIMEOUT', 'dispatch timed out; execution unknown') from error
    except (URLError, ConnectionError) as error:
        raise c.ContractError('PROVIDER_UNAVAILABLE', 'connection failed') from error


def make_handler(state, service, vehicle=None):
    c.require(service in ('ditto', 'provider', 'backend'), 'INVALID_CONFIG', service)
    c.require(service != 'provider' or vehicle in c.VEHICLES, 'INVALID_CONFIG', 'provider vehicle required')

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, payload):
            data = json.dumps(payload, allow_nan=False).encode()
            try:
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('X-SDV-Mock', 'true')
                self.send_header('X-Mock-Now', c.iso(state.clock()))
                self.send_header('Access-Control-Allow-Origin', 'http://localhost:3000')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,OPTIONS')
                self.end_headers(); self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Deliberate timeout/disconnect tests may close their socket.

        def body(self):
            length = int(self.headers.get('Content-Length', 0))
            c.require(0 < length <= 65536, 'INVALID_REQUEST', 'body length must be 1..65536')
            body = json.loads(self.rfile.read(length))
            c.require(isinstance(body, dict), 'INVALID_REQUEST', 'body must be an object')
            return body

        def handle_request(self):
            parts = unquote(self.path).strip('/').split('/')
            if self.path == '/health':
                return self.reply(200, {'status': 'UP', 'mock': True, 'service': service})
            if self.command == 'POST' and parts[:1] == ['_mock']:
                body = self.body()
                if parts == ['_mock', 'clock']:
                    c.require(not state.live_clock, 'INVALID_CONFIG', 'fixed clock mode required')
                    state.now = c.parse_timestamp(body.get('now'))
                elif len(parts) == 3 and parts[1] == 'states':
                    state.set_state(parts[2], body.get('state'))
                elif len(parts) == 3 and parts[1] == 'failures':
                    c.require(parts[2] in c.VEHICLES, 'UNKNOWN_VEHICLE', parts[2])
                    c.require(body.get('mode') in ('success', 'reject', 'timeout', 'disconnect'),
                              'INVALID_REQUEST', 'failure mode')
                    state.failure[parts[2]] = body['mode']
                else:
                    return self.reply(404, self.error('NOT_FOUND', 'mock control not found'))
                return self.reply(200, {'mock': True, 'now': c.iso(state.clock())})
            if service == 'ditto' and parts[:3] == ['api', '2', 'things'] and len(parts) in (4, 7):
                target = parts[3].removeprefix('sdv:')
                c.require(parts[3] == 'sdv:' + target and target in c.VEHICLES, 'UNKNOWN_VEHICLE', parts[3])
                if self.command == 'PUT' and parts[4:] == ['features', 'v1', 'properties']:
                    props = self.body()
                    twin = {'thingId': parts[3], 'attributes': {'vehicleId': target},
                            'features': {'v1': {'properties': props}}}
                    c.vehicle_view(target, twin, state.clock())
                    state.twins[target] = copy.deepcopy(twin); state.states[target] = 'custom'
                    return self.reply(200, props)
                if self.command == 'GET':
                    if state.states[target] == 'missing':
                        return self.reply(404, self.error('TWIN_MISSING', 'mock twin missing'))
                    if state.states[target] == 'unavailable':
                        return self.reply(503, self.error('DITTO_UNAVAILABLE', 'mock Ditto unavailable'))
                    if len(parts) == 4:
                        return self.reply(200, state.twins[target])
                    if parts[4:] == ['features', 'v1', 'properties']:
                        return self.reply(200, state.twins[target]['features']['v1']['properties'])
            if service == 'provider':
                if self.command == 'POST' and self.path == '/api/v1/scenarios/actions':
                    body = self.body()
                    if state.failure[vehicle] == 'disconnect':
                        self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
                    return self.reply(200, state.execute(vehicle, body))
                if self.command == 'GET' and len(parts) == 6 and parts[:3] == ['api', 'v1', 'vehicles'] and parts[4:] == ['scenarios', 'LIDAR_OBSTRUCTION']:
                    c.require(parts[3] == vehicle, 'UNKNOWN_VEHICLE', parts[3])
                    return self.reply(200, state.context.get(vehicle, dict(vehicleId=vehicle,
                        scenario='LIDAR_OBSTRUCTION', active=False, actionId=None, traceId=None, action=None)))
            if service == 'backend':
                if self.command == 'GET' and self.path == '/api/v1/vehicles':
                    return self.reply(200, {'vehicleIds': list(c.VEHICLES)})
                if parts[:3] == ['api', 'v1', 'vehicles']:
                    parts = ['api', 'vehicles'] + parts[3:]
                if self.command == 'GET' and self.path == '/api/v1/fleet':
                    return self.reply(200, c.fleet_summary([state.view(v) for v in c.VEHICLES], state.clock()))
                if self.command == 'GET' and len(parts) == 4 and parts[:2] == ['api', 'vehicles'] and parts[3] in ('state', 'health'):
                    return self.reply(200, state.view(parts[2]))
                if self.command == 'POST' and self.path == '/api/v1/diagnostics/actions':
                    body = self.body()
                    state.counter += 1
                    action_id = f'mock-action-{state.counter:04d}'
                    body.update(actionId=action_id, traceId=action_id)
                    state.execute(body.get('vehicleId'), body)
                    result = {k: body[k] for k in ('vehicleId', 'action', 'scenario', 'actionId', 'traceId')}
                    result.update(status='ACCEPTED', dispatchStatus='DISPATCHED', requestedAt=c.iso(state.clock()))
                    state.actions[action_id] = result
                    return self.reply(202, result)
                if self.command == 'GET' and len(parts) == 5 and parts[:4] == ['api', 'v1', 'diagnostics', 'actions']:
                    result = state.actions.get(parts[4])
                    return self.reply(200, result) if result else self.reply(404, self.error('ACTION_NOT_FOUND', parts[4]))
            return self.reply(404, self.error('NOT_FOUND', 'route not found'))

        def error(self, code, message):
            return dict(timestamp=c.iso(state.clock()), code=code, message=message, path=self.path)

        def guarded(self):
            try:
                self.handle_request()
            except c.ContractError as error:
                status = {'UNKNOWN_VEHICLE': 404, 'PROVIDER_REJECTED': 409,
                          'PROVIDER_TIMEOUT': 504, 'PROVIDER_UNAVAILABLE': 503}.get(error.code, 400)
                self.reply(status, self.error(error.code, str(error)))
            except (ValueError, TypeError, KeyError) as error:
                self.reply(400, self.error('INVALID_REQUEST', str(error)))

        do_GET = guarded
        do_POST = guarded
        do_PUT = guarded

        def do_OPTIONS(self):
            self.reply(200, {'mock': True})

        def log_message(self, *_args):
            pass

    return Handler


def make_server(state, service, vehicle=None, host='127.0.0.1', port=19080):
    return ThreadingHTTPServer((host, port), make_handler(state, service, vehicle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ack-development-only', action='store_true', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--ditto-port', type=int, default=19080)
    parser.add_argument('--provider-001-port', type=int, default=19091)
    parser.add_argument('--provider-002-port', type=int, default=19092)
    parser.add_argument('--backend-port', type=int, default=19082)
    parser.add_argument('--now', default='2026-01-01T00:00:04Z')
    parser.add_argument('--live-clock', action='store_true')
    args = parser.parse_args()
    state = MockState(datetime.now(timezone.utc) if args.live_clock else c.parse_timestamp(args.now), args.live_clock)
    servers = []
    try:
        for service, vehicle, port in [('ditto', None, args.ditto_port),
                ('provider', 'vehicle-001', args.provider_001_port),
                ('provider', 'vehicle-002', args.provider_002_port), ('backend', None, args.backend_port)]:
            server = make_server(state, service, vehicle, args.host, port)
            servers.append(server)
            Thread(target=server.serve_forever, daemon=True).start()
            print(f'DEVELOPMENT MOCK {service} {vehicle or ""}: http://{args.host}:{server.server_address[1]}', flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.shutdown(); server.server_close()


if __name__ == '__main__':
    main()
