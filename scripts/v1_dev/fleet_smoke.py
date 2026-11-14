"""Opt-in Java A5 smoke: prepared mocks + isolated fleet-write capture (not live Ditto).

Run from repository root. --hold keeps the owned stack up for browser verification.
"""
import argparse
import base64
import functools
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def request(url, body=None, method=None, auth=None):
    headers = {'Content-Type': 'application/json'}
    if auth:
        headers['Authorization'] = 'Basic ' + base64.b64encode(auth.encode()).decode()
    req = Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    with urlopen(req, timeout=5) as response:
        data = response.read()
        return json.loads(data) if data else None


def eventually(check, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(.05)
    raise AssertionError('Timed out waiting for expected mock-backed result')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default=str(Path(os.environ.get('JAVA_HOME', '/usr')) / 'bin/java'))
    parser.add_argument('--jar', default='backend/target/backend-0.0.1-SNAPSHOT.jar')
    parser.add_argument('--artifacts-dir', default='/tmp/a5-fleet-smoke')
    parser.add_argument('--frontend-port', type=int, default=3000)
    parser.add_argument('--hold', action='store_true')
    args = parser.parse_args()
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    artifacts = Path(args.artifacts_dir); artifacts.mkdir(parents=True, exist_ok=True)
    ports = {key: free_port() for key in ('ditto', 'provider001', 'provider002', 'preview', 'capture', 'backend')}
    api = 'http://localhost:' + str(ports['backend'])
    mock = 'http://127.0.0.1:' + str(ports['ditto'])
    state = {'summary': None, 'writes': 0, 'failedWrites': 0, 'status': 204, 'resources': {}, 'writeAuth': None}
    lock = threading.Lock()

    class Capture(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            # The fleet capture does not simulate individual twins: delegate to the prepared mock.
            try:
                with urlopen(mock + self.path, timeout=3) as response:
                    data = response.read(); code = response.status
            except HTTPError as error:
                data = error.read(); code = error.code
            self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(data)
        def do_PUT(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            auth = self.headers.get('Authorization')
            expected = 'Basic ' + base64.b64encode(('fleet-service:test-only-password' if self.path.endswith('/properties') else 'admin:test-only-admin').encode()).decode()
            if auth != expected:
                self.send_response(401); self.end_headers(); return
            with lock:
                if self.path == '/api/2/things/sdv:fleet-v1/features/summary/properties':
                    assert '/api/2/things/sdv:fleet-v1' in state['resources']
                    state['writes'] += 1; state['writeAuth'] = auth
                    code = state['status']
                    if code == 204: state['summary'] = body
                    else: state['failedWrites'] += 1
                else:
                    assert self.headers.get('If-None-Match') == '*'
                    code = 412 if self.path in state['resources'] else 201
                    if code == 201: state['resources'][self.path] = body
            self.send_response(code); self.end_headers()

    class Static(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass

    processes = []; servers = []; files = []
    def launch(command, name, env=None):
        output = open(artifacts / (name + '.log'), 'w'); files.append(output)
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
        processes.append(process); return process
    try:
        launch([sys.executable, '-B', '-m', 'scripts.v1_dev.http_mocks', '--ack-development-only', '--live-clock',
                '--ditto-port', str(ports['ditto']), '--provider-001-port', str(ports['provider001']),
                '--provider-002-port', str(ports['provider002']), '--backend-port', str(ports['preview'])], 'mocks')
        eventually(lambda: request(mock + '/health'))
        capture = ThreadingHTTPServer(('127.0.0.1', ports['capture']), Capture); servers.append(capture)
        threading.Thread(target=capture.serve_forever, daemon=True).start()
        # Exercise the actual provisioning implementation against a controlled HTTP boundary.
        from scripts.v1_fleet_provision import provision
        provision('http://127.0.0.1:' + str(ports['capture']), 'admin', 'test-only-admin', 'nginx:admin', 'nginx:fleet-service')
        provisioned = state['resources']['/api/2/things/sdv:fleet-v1']
        assert provisioned['attributes'] == {'kind': 'fleet', 'vehicleIds': ['vehicle-001', 'vehicle-002']}
        assert provisioned['features'] == {'summary': {}}
        assert 'nginx:fleet-service' in state['resources']['/api/2/policies/sdv:fleet-v1-policy']['entries']['fleet-writer']['subjects']
        static = ThreadingHTTPServer(('127.0.0.1', args.frontend_port), functools.partial(Static, directory=str(ROOT / 'frontend')))
        servers.append(static); threading.Thread(target=static.serve_forever, daemon=True).start()
        env = os.environ.copy()
        env.update(SDV_V1_FLEET_USERNAME='fleet-service', SDV_V1_FLEET_PASSWORD='test-only-password')
        launch([args.java, '-jar', args.jar, '--spring.profiles.active=v1-mock', '--server.address=127.0.0.1',
                '--server.port=' + str(ports['backend']), '--sdv.v1.ditto.base-url=http://127.0.0.1:' + str(ports['capture']),
                '--sdv.simulator.providers[vehicle-001]=http://127.0.0.1:' + str(ports['provider001']),
                '--sdv.simulator.providers[vehicle-002]=http://127.0.0.1:' + str(ports['provider002']),
                '--sdv.v1.fleet.enabled=true', '--sdv.v1.fleet.interval=200ms', '--sdv.v1.fleet.initial-delay=100ms',
                '--sdv.v1.fleet.write-timeout=500ms'], 'spring', env)
        eventually(lambda: request(api + '/api/v1/vehicles'))
        def set_state(vehicle, value): request(mock + '/_mock/states/' + vehicle, {'state': value})
        def fleet():
            result = request(api + '/api/v1/fleet')
            assert result['totalVehicles'] == sum(result[k] for k in ('availableVehicles', 'staleVehicles', 'unavailableVehicles'))
            assert result['availableVehicles'] == sum(result[k] for k in ('healthyVehicles', 'warningVehicles', 'criticalVehicles'))
            assert [v['vehicleId'] for v in result['vehicles']] == ['vehicle-001', 'vehicle-002']
            return result
        for vehicle in ('vehicle-001', 'vehicle-002'): set_state(vehicle, 'healthy')
        healthy = fleet(); assert healthy['healthyVehicles'] == 2
        eventually(lambda: state['summary'] and state['summary']['healthyVehicles'] == 2)
        stored = json.loads(json.dumps(state['summary']))
        assert {k: v for k, v in stored.items() if k != 'generatedAt'} == {k: v for k, v in healthy.items() if k != 'generatedAt'}
        action_body = {'vehicleId': 'vehicle-002', 'action': 'INJECT_SCENARIO', 'scenario': 'LIDAR_OBSTRUCTION'}
        ack = request(api + '/api/v1/diagnostics/actions', action_body)
        assert ack['status'] == 'ACCEPTED' and ack['dispatchStatus'] == 'DISPATCHED'
        assert request(api + '/api/v1/diagnostics/actions/' + ack['actionId']) == ack
        fault = fleet(); assert fault['criticalVehicles'] == 1 and fault['healthyVehicles'] == 1
        eventually(lambda: state['summary']['criticalVehicles'] == 1)
        action_body['action'] = 'CLEAR_SCENARIO'; request(api + '/api/v1/diagnostics/actions', action_body)
        assert fleet()['healthyVehicles'] == 2
        set_state('vehicle-002', 'stale'); stale = fleet(); assert stale['staleVehicles'] == 1 and stale['healthyVehicles'] == 1
        set_state('vehicle-002', 'missing'); missing = fleet(); assert missing['unavailableVehicles'] == 1 and missing['healthyVehicles'] == 1
        set_state('vehicle-002', 'unavailable'); assert fleet()['healthyVehicles'] == 1
        set_state('vehicle-002', 'recovered')
        with lock: state['status'] = 503
        eventually(lambda: state['failedWrites'] > 0)
        assert fleet()['healthyVehicles'] == 2
        with lock: state['status'] = 204; previous = state['writes']
        eventually(lambda: state['writes'] > previous and state['summary']['healthyVehicles'] == 2)
        stack = {'api': api, 'mock': mock, 'frontend': 'http://localhost:' + str(args.frontend_port),
                 'ports': ports, 'dependencies': 'prepared HTTP mocks plus controlled fleet capture; no live MQTT/Ditto'}
        (artifacts / 'stack.json').write_text(json.dumps(stack, indent=2) + '\n')
        result = {'checks': ['healthy fixture projection', 'materialized projection apart from evaluation timestamp',
                             'targeted injection and lookup', 'fleet fault isolation', 'clear/recovery', 'stale exclusion',
                             'missing isolation', 'unavailable isolation', 'write failure preserves API', 'scheduled retry recovery',
                             'provisioning policy/Thing', 'service authentication'],
                  'healthy': healthy, 'fault': fault, 'stale': stale, 'missing': missing, 'materialized': stored}
        (artifacts / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'status': 'PASS', 'checks': len(result['checks']), **stack}), flush=True)
        if args.hold:
            while True: time.sleep(1)
    finally:
        for process in reversed(processes):
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for server in servers: server.shutdown(); server.server_close()
        for output in files: output.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
