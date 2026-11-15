"""Owned real two-vehicle stack. Exit 0=all implemented live gates pass; 1=FAIL; 2=BLOCKED.

Requires legitimate credentials for the pinned official local Ditto sample. Never
points at a shared deployment. No mock fallback exists in this runner.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from scripts.v1_acceptance.assertions import IDS, fleet, preserved
from scripts.v1_acceptance.evidence import sanitize_text

ROOT = Path(__file__).resolve().parents[2]
DITTO_REV = '5dbb05e6294e5ac0103506102baff9eab755d180'  # official 3.8.4
GATES = ('readiness', 'healthy', 'fault-recovery-trials', 'freshness-null',
         'invalid-ordering-restart', 'individual-write-recovery', 'fleet-write-recovery',
         'mqtt-reconnect', 'provider-kuksa-recovery', 'dashboard', 'baseline-regression', 'kanto-v1-09')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Run:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.output).resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.project = 'qa-v1-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '-' + str(os.getpid())
        self.results = {g: {'status': 'BLOCKED', 'reason': 'not reached'} for g in GATES}
        self.samples = []
        self.events = {}
        self.lock = threading.Lock()
        self.processes = []
        self.handles = []
        self.owned = []
        self.stop = threading.Event()
        self.commands = []
        self.write('harness-source.json', {str(p.relative_to(ROOT)):p.read_text() for p in (ROOT/'scripts/v1_acceptance').glob('*.py')})
        self.opener = build_opener(NoRedirect())
        self.browser = self.page = self.playwright = self.mqtt = self.web = None
        self.ports = {}
        for name in ('ditto', 'mqtt', 'kuksa001', 'kuksa002', 'provider001', 'provider002', 'api'):
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0)); self.ports[name] = s.getsockname()[1]
        self.auth = (os.environ.get('SDV_ACCEPTANCE_DITTO_USERNAME', ''), os.environ.get('SDV_ACCEPTANCE_DITTO_PASSWORD', ''))
        self.subject = os.environ.get('SDV_ACCEPTANCE_DITTO_SUBJECT', '')
        self.ditto = f'http://127.0.0.1:{self.ports["ditto"]}'
        self.api = f'http://127.0.0.1:{self.ports["api"]}'
        self.write('manifest.json', {'startedUtc': datetime.now(timezone.utc).isoformat(),
            'sha': self.git('rev-parse', 'HEAD'), 'dirty': self.git('status', '--porcelain'),
            'project': self.project, 'ports': self.ports, 'dittoRevision': DITTO_REV,
            'clock': 'one host time.monotonic observer; source UTC shares host kernel clock via containers; no cross-host clock accuracy bound',
            'trials': args.trials, 'dependencies': 'real providers/KUKSA/Velocitas/Mosquitto/ingress/Ditto/Java/dashboard; no mocks',
            'pendingWordingAlignment': 'separate docs PR; current main C1-C10 proposed status retained',
            'notAcceptance': ['Kanto is a separate required live gate', 'release/report/video/approvals are not automated here']})

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value, indent=2) + '\n')

    def append(self, name, value):
        with (self.out / name).open('a') as f:
            f.write(json.dumps(value) + '\n')

    def command(self, argv, *, env=None, check=True, timeout=600):
        # Credentials travel only in process environment, never argv or saved environment.
        index = len(self.commands)
        log = self.out / f'command-{index:03d}.txt'
        start = time.monotonic()
        with log.open('w') as f:
            try:
                p = subprocess.run(argv, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
                code = p.returncode
            except subprocess.TimeoutExpired:
                code = 124
        log.write_text(sanitize_text(log.read_text(), *self.auth))
        row = {'argv': list(map(str, argv)), 'exit': code, 'seconds': time.monotonic()-start, 'output': log.name}
        self.commands.append(row); self.write('commands.json', self.commands)
        if check and code:
            raise RuntimeError(f'command {index} exit {code}')
        return log.read_text()

    def spawn(self, argv, name, env=None):
        f = (self.out / (name + '.txt')).open('w'); self.handles.append(f)
        p = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
        self.processes.append(p)
        self.append('processes.jsonl', {'argv': list(map(str, argv)), 'pid': p.pid, 'log': name+'.txt'})
        return p

    def http(self, base, path, body=None, method=None, auth=False):
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Authorization'] = 'Basic ' + base64.b64encode(':'.join(self.auth).encode()).decode()
        req = Request(base+path, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
        with self.opener.open(req, timeout=4) as response:
            data = response.read()
            return json.loads(data) if data else None

    def thing(self, vehicle):
        return self.http(self.ditto, '/api/2/things/sdv:'+vehicle, auth=True)

    def props(self, vehicle):
        return self.thing(vehicle)['features']['v1']['properties']

    def view(self, vehicle):
        return self.http(self.api, '/api/v1/vehicles/'+vehicle+'/state')

    def summary(self):
        value = self.http(self.api, '/api/v1/fleet'); fleet(value); return value

    def wait(self, check, seconds=50):
        end = time.monotonic()+seconds
        last = None
        while time.monotonic() < end:
            try:
                result = check()
                if result:
                    return result
            except (AssertionError, HTTPError, URLError, OSError, KeyError, ValueError) as error:
                last = type(error).__name__
            self.stop.wait(.15)
        raise AssertionError('boundary timeout; last error type='+str(last))

    def gate(self, name, fn):
        started = time.monotonic()
        try:
            fn()
            self.results[name] = {'status': 'PASS', 'seconds': time.monotonic()-started}
        except Exception as error:
            # Exception messages may carry URLs/credentials; retain only safe type.
            self.results[name] = {'status': 'BLOCKED' if name == 'readiness' else 'FAIL', 'errorType': type(error).__name__, 'seconds': time.monotonic()-started, 'reason': 'see commands/process logs; no substitute used'}
        self.write('results.json', self.results)
        print(name, self.results[name]['status'], flush=True)

    def compose(self, which, *args, **kw):
        return self.command(['docker', 'compose', '-p', self.project+'-'+which, '-f', str(self.out / (which+'.json')), *args], **kw)

    def configure(self):
        import yaml
        if not all(self.auth) or not self.subject:
            raise ValueError('legitimate local sample credentials and authenticated subject required')
        source = Path(self.args.ditto_source).resolve()
        if not source.exists():
            self.command(['git', 'clone', '--depth', '1', '--branch', '3.8.4', 'https://github.com/eclipse-ditto/ditto.git', str(source)])
        assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == DITTO_REV
        deployment = source/'deployment/docker'
        config = yaml.safe_load((deployment/'docker-compose.yml').read_text())
        config.pop('version', None)
        for name, service in config['services'].items():
            service.pop('ports', None)
            service['restart'] = 'no'
            if 'volumes' in service:
                service['volumes'] = [str((deployment/v.split(':')[0]).resolve())+':'+':'.join(v.split(':')[1:]) for v in service['volumes']]
            if 'image' in service:
                service['image'] = service['image'].replace('${DITTO_VERSION:-latest}', '3.8.4')
        config['services']['nginx']['ports'] = [f'127.0.0.1:{self.ports["ditto"]}:80']
        config.pop('volumes', None)  # upstream unused host /var/log bind declaration
        # Official nginx passes Spring's duplicate Accept-Encoding fields through;
        # Ditto rejects them. Normalize this transport header in this isolated
        # deployment; preserve the unmodified-stack failure as a release finding.
        nginx=(deployment/'nginx.conf').read_text().replace('location /api {',
            'location /api {\n      proxy_set_header Accept-Encoding "";')
        (self.out/'nginx-acceptance.conf').write_text(nginx)
        config['services']['nginx']['volumes'] = [
            str(self.out/'nginx-acceptance.conf')+':/etc/nginx/nginx.conf:ro' if v.endswith(':/etc/nginx/nginx.conf:ro') else v
            for v in config['services']['nginx']['volumes']]
        self.write('ditto.json', config)
        env = dict(os.environ, V1_MQTT_PORT=str(self.ports['mqtt']), V1_KUKSA_001_PORT=str(self.ports['kuksa001']),
                   V1_KUKSA_002_PORT=str(self.ports['kuksa002']), V1_PROVIDER_001_PORT=str(self.ports['provider001']),
                   V1_PROVIDER_002_PORT=str(self.ports['provider002']), PUBLISH_INTERVAL_SECONDS='1.0')
        # Existing production edge definition, with only unique project/ports/build tags.
        raw = self.command(['docker','compose','-f','vehicle-simulator/docker-compose.v1.yml','config','--format','json'], env=env)
        edge = json.loads(raw); edge.pop('name',None)
        for name, service in edge['services'].items():
            service['restart'] = 'no' if name.startswith('provider') else service.get('restart', 'no')
            for port in service.get('ports', []):
                port['host_ip'] = '127.0.0.1'
            if name.startswith('app'):
                service['image'] = self.project+'-app'
            if name.startswith('provider'):
                service['image'] = self.project+'-provider'
        self.write('edge.json',edge)
        self.command(['docker','version'])
        self.command(['java','-version'])
        self.write('python-packages.json', {d.metadata['Name']: d.version for d in __import__('importlib.metadata',fromlist=['distributions']).distributions()})
        self.owned.append('ditto'); self.compose('ditto', 'up','-d', timeout=900)
        self.wait(lambda: self.http(self.ditto, '/api/2/things', auth=True) is not None, 240)
        from ditto.v1_writer import DittoConfig, DittoWriter
        self.writer = DittoWriter(DittoConfig(self.ditto, *self.auth))
        self.writer.provision(self.subject)
        # Create-only fleet provisioning; same legitimate local subject, no invented second credential.
        policy = {'entries': {'owner': {'subjects': {self.subject: {'type': 'isolated acceptance owner'}},
            'resources': {'thing:/': {'grant':['READ','WRITE'],'revoke':[]}, 'policy:/': {'grant':['READ','WRITE'],'revoke':[]}}}}}
        # Require fresh, test-owned namespace: never replace an existing fleet Thing/policy.
        for resource, payload in [('policies/sdv:fleet-v1-policy',policy), ('things/sdv:fleet-v1',{
                'policyId':'sdv:fleet-v1-policy','attributes':{'kind':'fleet','vehicleIds':list(IDS)},'features':{'summary':{}}})]:
            headers = {'Content-Type':'application/json','If-None-Match':'*',
                       'Authorization':'Basic '+base64.b64encode(':'.join(self.auth).encode()).decode()}
            with self.opener.open(Request(self.ditto+'/api/2/'+resource, data=json.dumps(payload).encode(), headers=headers, method='PUT'), timeout=5):
                pass
        self.ingress_env = dict(os.environ, SDV_DITTO_BASE_URL=self.ditto, SDV_DITTO_USERNAME=self.auth[0],
            SDV_DITTO_PASSWORD=self.auth[1], SDV_MQTT_HOST='127.0.0.1', SDV_MQTT_PORT=str(self.ports['mqtt']),
            SDV_MQTT_CLIENT_ID=self.project+'-ingress')
        self.owned.append('edge'); self.compose('edge','up','-d','--build', timeout=900)
        self.start_capture()
        # Ingress itself initializes absent features conditionally from actual
        # observations. No observer/provisioner seeds telemetry or watermarks.
        self.ingress = self.spawn([sys.executable,'-B','-m','ditto.v1','run'], 'ingress', self.ingress_env)
        env = dict(os.environ, SERVER_PORT=str(self.ports['api']), SDV_V1_DITTO_BASE_URL=self.ditto,
            SDV_V1_DITTO_USERNAME=self.auth[0], SDV_V1_DITTO_PASSWORD=self.auth[1], SDV_V1_DITTO_MODE='live',
            SDV_V1_FLEET_ENABLED='true', SDV_V1_FLEET_USERNAME=self.auth[0], SDV_V1_FLEET_PASSWORD=self.auth[1],
            SDV_PROVIDER_001_BASE_URL=f'http://127.0.0.1:{self.ports["provider001"]}',
            SDV_PROVIDER_002_BASE_URL=f'http://127.0.0.1:{self.ports["provider002"]}', SDV_SIMULATOR_MODE='http',
            SDV_VEHICLE_IDS=','.join(IDS))
        self.backend = self.spawn(['java','-jar',str(ROOT/'backend/target/backend-0.0.1-SNAPSHOT.jar')], 'backend', env)
        self.wait(lambda: self.http(self.api,'/api/v1/vehicles') == {'vehicleIds':list(IDS)},90)
        self.resource_thread = threading.Thread(target=self.resources,daemon=True); self.resource_thread.start()
        self.command(['docker','image','ls','--digests','--no-trunc'])
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        opts = {'headless':True, 'args':['--no-sandbox']}
        if self.args.chrome:
            opts['executable_path'] = self.args.chrome
        self.browser = self.playwright.chromium.launch(**opts)
        self.page = self.browser.new_page(viewport={'width':1440,'height':1050})
        self.page.on('pageerror', lambda err: self.append('browser-errors.jsonl', {'type':'pageerror','message':str(err)}))
        self.page.on('response', lambda response: self.append('browser-http.jsonl', {'url':response.url,'status':response.status}))
        self.page.add_init_script('globalThis.SDV_CONFIG = '+json.dumps({'API_BASE_URL':self.api})+';')
        # Existing CORS permits port 3000; fail if occupied rather than displacing another service.
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT/'frontend'))
        self.web = ThreadingHTTPServer(('127.0.0.1',3000),handler)
        threading.Thread(target=self.web.serve_forever, daemon=True).start()
        self.page.goto('http://localhost:3000')
        self.page.select_option('#vehicle-select','vehicle-002')

    def start_capture(self):
        import paho.mqtt.client as mqtt
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.project+'-observer')
        def connected(c, userdata, flags, code, properties):
            c.subscribe('sdv/+/health',qos=1)
        def message(c, userdata, msg):
            at = time.monotonic()
            try:
                event = json.loads(msg.payload)
                # Production validator below owns schema semantics; this capture retains rejected injections too.
                from ditto.mqtt_ingress import validate_event as validate
                validate(msg.topic,event)
                with self.lock:
                    self.events[event['eventId']] = (event,at)
                valid = True
            except Exception:
                event = msg.payload.decode(errors='replace'); valid=False
            self.append('mqtt.jsonl', {'monotonic':at,'topic':msg.topic,'qos':msg.qos,'retain':msg.retain,'valid':valid,'event':event})
        client.on_connect=connected;client.on_message=message
        self.wait(lambda: self._connect(client),30)
        client.loop_start();self.mqtt=client

    def _connect(self, client):
        client.connect('127.0.0.1',self.ports['mqtt'],keepalive=5);return True

    def resources(self):
        while not self.stop.is_set():
            for which in self.owned:
                p = subprocess.run(['docker','stats','--no-stream','--format','{{json .}}'], capture_output=True,text=True,timeout=15)
                for line in p.stdout.splitlines():
                    if self.project in line:
                        self.append('resources.jsonl',{'monotonic':time.monotonic(),'docker':json.loads(line)})
                break
            self.stop.wait(3)

    def snapshot(self, label):
        things={v:self.thing(v) for v in IDS}
        views={v:self.view(v) for v in IDS}
        summary=self.summary()
        materialized=self.thing('fleet-v1')
        self.write(label+'.json', {'monotonic':time.monotonic(),'things':things,'views':views,'apiFleet':summary,'fleetThing':materialized})
        return things,views,summary,materialized

    def isolation(self):
        one=self.view('vehicle-001')
        assert one['healthStatus']=='HEALTHY' and one['activeFaults']==[], 'vehicle-001 changed'
        thing=self.thing('vehicle-001')
        with self.lock:
            event=self.events.get(one['lastEventId'])
        assert event is not None, 'vehicle-001 event absent from actual MQTT capture'
        preserved(event[0],thing,one)
        self.append('isolation.jsonl', {'monotonic':time.monotonic(),'view':one})

    def boundary(self, health, label, started=None):
        started=time.monotonic() if started is None else started
        row={'operation':label,'startedMonotonic':started,'boundaries':{},'status':'FAIL'}
        self.samples.append(row)
        def observed():
            self.isolation()
            with self.lock:
                hits=[(e,t) for e,t in self.events.values() if e['vehicleId']=='vehicle-002' and e['health']==health and t>=started]
            if hits:
                row['boundaries'].setdefault('mqtt', min(t for e,t in hits)-started)
            thing=self.thing('vehicle-002');p=thing['features']['v1']['properties']
            if p['health']==health:
                with self.lock:
                    event=self.events.get(p['lastEventId'])
                if event and event[1]>=started:
                    row['boundaries'].setdefault('twin',time.monotonic()-started)
                    self.append('propagation.jsonl', {'eventId':p['lastEventId'],'sourceTimestamp':p['sourceTimestamp'],
                        'observerUtc':datetime.now(timezone.utc).isoformat(), 'limitation':'source UTC to polling observation; shared kernel clock, no measured synchronization error'})
                    view=self.view('vehicle-002')
                    if view['lastEventId']==p['lastEventId']:
                        preserved(event[0],thing,view)
                        row['boundaries'].setdefault('api',time.monotonic()-started)
            summary=self.summary()
            if summary['vehicles'][1]['healthStatus']==health and summary['vehicles'][1]['availability']=='AVAILABLE':
                row['boundaries'].setdefault('fleetApi',time.monotonic()-started)
            mat=self.thing('fleet-v1')['features']['summary'].get('properties',{})
            if mat:
                fleet(mat)
                if mat['vehicles'][1]['healthStatus']==health and mat['vehicles'][1]['availability']=='AVAILABLE':
                    row['boundaries'].setdefault('fleetThing',time.monotonic()-started)
            text=self.page.locator('#vehicle-health').inner_text()
            if text==health:
                row['boundaries'].setdefault('dashboard',time.monotonic()-started)
            return len(row['boundaries'])==6
        try:
            self.wait(observed,70)
            row['status']='PASS'
            self.snapshot(label)
            self.page.screenshot(path=str(self.out/(label+'.png')),full_page=True)
        finally:
            self.write('measurements.json',self.samples)

    def action(self, action):
        started=time.monotonic()
        value=self.http(self.api,'/api/v1/diagnostics/actions',{'vehicleId':'vehicle-002','action':action,'scenario':'LIDAR_OBSTRUCTION'})
        self.append('actions.jsonl',{'monotonic':started,'ackSeconds':time.monotonic()-started,'response':value})
        assert value['status']=='ACCEPTED'
        return started

    def healthy(self):
        self.wait(lambda: all(self.view(v)['healthStatus']=='HEALTHY' for v in IDS))
        self.boundary('HEALTHY','healthy')
        with self.lock:
            assert {e['vehicleId'] for e,t in self.events.values()}==set(IDS)

    def trials(self):
        for trial in range(self.args.trials):
            # Each operation is retained independently even when it times out.
            for action,health in [('INJECT_SCENARIO','CRITICAL'),('CLEAR_SCENARIO','HEALTHY')]:
                label=f'trial-{trial+1}-{action.lower()}'
                count=len(self.samples)
                try:
                    started=self.action(action)
                    self.boundary(health,label,started)
                except Exception as error:
                    if len(self.samples)==count:
                        self.samples.append({'operation':label,'status':'FAIL','boundaries':{},'errorType':type(error).__name__})
                        self.write('measurements.json',self.samples)
        assert all(s['status']=='PASS' for s in self.samples if s['operation'].startswith('trial-'))

    def freshness(self):
        self.compose('edge','stop','app-002')
        try:
            source=self.props('vehicle-002')['sourceTimestamp']
            self.wait(lambda: self.view('vehicle-002')['availability']=='STALE',15)
            assert self.view('vehicle-002')['sourceTimestamp']==source
            self.snapshot('stale')
            self.wait(lambda: self.view('vehicle-002')['availability']=='UNAVAILABLE',40)
            self.snapshot('aged-unavailable')
            summary=self.summary(); assert summary['unavailableVehicles']==1; self.isolation()
            # Missing feature -> untrusted snapshot with explicit nulls; stop ingress before test-owned mutation.
            self.kill_ingress()
            previous=self.props('vehicle-002')
            self.http(self.ditto,'/api/2/things/sdv:vehicle-002/features/v1',method='DELETE',auth=True)
            try:
                view=self.view('vehicle-002')
                assert view['availability']=='UNAVAILABLE'
                for field in ('healthStatus','activeFaults','lidar','sourceTimestamp','lastEventId'):
                    assert view[field] is None,field
                self.snapshot('missing-null')
            finally:
                self.http(self.ditto,'/api/2/things/sdv:vehicle-002/features/v1',{'properties':previous},'PUT',True)
                self.start_ingress()
        finally:
            self.compose('edge','start','app-002')
        self.wait(lambda: self.view('vehicle-002')['availability']=='AVAILABLE')

    def kill_ingress(self):
        self.ingress.terminate()
        try:self.ingress.wait(timeout=8)
        except subprocess.TimeoutExpired:self.ingress.kill();self.ingress.wait()

    def start_ingress(self):
        self.ingress=self.spawn([sys.executable,'-B','-m','ditto.v1','run'], 'ingress-'+str(len(self.processes)),self.ingress_env)
        self.stop.wait(2)

    def publish(self,event,topic=None):
        payload=event if isinstance(event,str) else json.dumps(event)
        result=self.mqtt.publish(topic or 'sdv/'+event['vehicleId']+'/health',payload,qos=1,retain=False)
        result.wait_for_publish(timeout=5)
        assert result.is_published()

    def new_event(self,vehicle='vehicle-002'):
        props=self.props(vehicle);event=copy.deepcopy(props);event['eventId']=event.pop('lastEventId')+'-acceptance-'+str(time.monotonic_ns())
        event['sourceTimestamp']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        return event

    def negatives(self):
        self.compose('edge','stop','app-001','app-002')
        try:
            self.stop.wait(3)
            before={v:self.props(v) for v in IDS}
            event=copy.deepcopy(before['vehicle-002']);event['eventId']=event.pop('lastEventId')
            unknown=dict(event,vehicleId='vehicle-999',eventId='unknown')
            equal=dict(event,eventId='equal-'+str(time.monotonic_ns()))
            late=dict(event,eventId='late-'+str(time.monotonic_ns()),sourceTimestamp='2000-01-01T00:00:00Z')
            cases=[('malformed','{','sdv/vehicle-002/health'),('unknown',unknown,'sdv/vehicle-999/health'),
                ('mismatched',event,'sdv/vehicle-001/health'),('duplicate',event,None),('equal',equal,None),('late',late,None)]
            for name,value,topic in cases:
                self.publish(value,topic);self.stop.wait(1)
                assert {v:self.props(v) for v in IDS}==before,name
                self.write('negative-'+name+'.json',{'before':before,'after':{v:self.props(v) for v in IDS}})
            self.kill_ingress();self.start_ingress();self.publish(event);self.stop.wait(2)
            assert {v:self.props(v) for v in IDS}==before
            valid=self.new_event();self.publish(valid)
            self.wait(lambda:self.props('vehicle-002')['lastEventId']==valid['eventId'])
            self.snapshot('restart-watermark-successor')
        finally:self.compose('edge','start','app-001','app-002')

    def revoke(self,vehicle,path,fn):
        resource='/api/2/policies/sdv:'+vehicle+'-policy'
        original=self.http(self.ditto,resource,auth=True)
        changed=copy.deepcopy(original)
        # Revoke only the selected write path on this newly provisioned isolated policy.
        entry=next(e for e in changed['entries'].values() if self.subject in e['subjects'])
        entry['resources'][path]={'grant':['READ'],'revoke':['WRITE']}
        self.http(self.ditto,resource,changed,'PUT',True)
        try:
            self.stop.wait(3);fn()
        finally:
            self.http(self.ditto,resource,original,'PUT',True)
            self.stop.wait(3)

    def individual_failure(self):
        self.compose('edge','stop','app-001','app-002')
        try:
            self.stop.wait(3)
            before=self.props('vehicle-002');event=self.new_event()
            def denied():
                self.publish(event);self.stop.wait(5)
                assert self.props('vehicle-002')==before
                other=self.new_event('vehicle-001');self.publish(other)
                self.wait(lambda:self.props('vehicle-001')['lastEventId']==other['eventId'])
                self.snapshot('individual-write-denied')
            self.revoke('vehicle-002','thing:/features/v1/properties',denied)
            self.wait(lambda:self.props('vehicle-002')['lastEventId']==event['eventId'])
            self.snapshot('individual-write-recovered')
        finally:self.compose('edge','start','app-001','app-002')

    def fleet_failure(self):
        before={}
        def denied():
            before.update(self.thing('fleet-v1')['features']['summary']['properties'])
            ids={v:self.view(v)['lastEventId'] for v in IDS}
            self.stop.wait(6)
            assert self.thing('fleet-v1')['features']['summary']['properties']==before
            assert all(self.view(v)['lastEventId'] != ids[v] for v in IDS)
            self.summary();self.isolation();self.snapshot('fleet-write-denied')
        self.revoke('fleet-v1','thing:/features/summary/properties',denied)
        self.wait(lambda:self.thing('fleet-v1')['features']['summary']['properties']['generatedAt']!=before['generatedAt'])
        self.snapshot('fleet-write-recovered')

    def reconnect(self):
        before=self.props('vehicle-002')['lastEventId']
        self.compose('edge','stop','mqtt')
        try:self.stop.wait(6)
        finally:self.compose('edge','start','mqtt')
        self.wait(lambda:self.props('vehicle-002')['lastEventId']!=before,70)
        self.snapshot('mqtt-reconnected')

    def provider_recovery(self):
        before=self.props('vehicle-002')['sourceTimestamp']
        self.compose('edge','stop','kuksa-002')
        try:self.stop.wait(12)
        finally:
            self.compose('edge','start','kuksa-002')
        returned=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        # No manual provider restart may discharge this check.
        self.wait(lambda:self.props('vehicle-002')['sourceTimestamp']>returned,60)
        self.isolation();self.snapshot('provider-recovered')

    def dashboard(self):
        self.page.click('#refresh')
        self.wait(lambda:self.page.locator('#vehicle-health').inner_text()=='HEALTHY',30)
        self.page.screenshot(path=str(self.out/'dashboard-final.png'),full_page=True)
        assert not (self.out/'browser-errors.jsonl').exists()

    def cleanup(self):
        self.stop.set()
        if hasattr(self, 'resource_thread'):
            self.resource_thread.join(timeout=20)
        # Restore any test-induced outages before clearing, even after interruption.
        if 'edge' in self.owned:
            self.compose('edge','start','kuksa-001','kuksa-002','mqtt',check=False,timeout=45)
            for v,key in [('vehicle-001','provider001'),('vehicle-002','provider002')]:
                try:
                    self.http(f'http://127.0.0.1:{self.ports[key]}','/api/v1/scenarios/actions',{
                        'vehicleId':v,'action':'CLEAR_SCENARIO','scenario':'LIDAR_OBSTRUCTION','actionId':'acceptance-cleanup','traceId':'acceptance-cleanup'})
                    self.append('cleanup.jsonl',{'vehicle':v,'clear':'PASS'})
                except Exception:
                    self.append('cleanup.jsonl',{'vehicle':v,'clear':'BLOCKED; provider unavailable; owned stack will stop'})
        if self.browser:self.browser.close()
        if self.playwright:self.playwright.stop()
        if self.web:self.web.shutdown();self.web.server_close()
        if self.mqtt:self.mqtt.disconnect();self.mqtt.loop_stop()
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            self.append('process-exits.jsonl',{'pid':process.pid,'exit':process.returncode})
        for handle in self.handles:handle.close()
        for which in reversed(self.owned):
            self.compose(which,'ps','--all',check=False)
            self.compose(which,'logs','--no-color','--tail','500',check=False)
            self.compose(which,'down','--timeout','15',check=False,timeout=90) # no volume deletion
        self.write('results.json',self.results)
        stats={}
        for name in ('inject_scenario', 'clear_scenario'):
            selected=[s for s in self.samples if s['operation'].endswith(name) and s['operation'].startswith('trial-')]
            stats[name]={'trials':len(selected),'failures':sum(s['status']!='PASS' for s in selected),'boundaries':{}}
            for boundary in ('mqtt','twin','api','fleetApi','fleetThing','dashboard'):
                values=[s['boundaries'][boundary] for s in selected if boundary in s['boundaries']]
                stats[name]['boundaries'][boundary]={'n':len(values),'medianSeconds':statistics.median(values) if values else None,
                    'rangeSeconds':[min(values),max(values)] if values else None}
        self.write('statistics.json',stats)
        self.write('measurement-limitations.json', {
            'method':'command-to-observed completion including scenario progression, HTTP/poll/browser work; not pure transport latency',
            'mqttContext':'events may omit actionId/traceId; temporal association on isolated stack is not causal command correlation',
            'sourceClocks':'shared host kernel UTC assumed; no clock error bound; source-to-twin samples are upper polling observations',
            'updateSuccess':'trial boundary observations only, not every MQTT event delivery or persistence success rate',
            'resources':'docker stats samples during workload; no isolated process attribution or benchmark claim',
            'fleetComparison':'separate evaluations; counts checked on materialized and API summaries, generatedAt may differ',
            'mvpComparison':'not directly comparable; no speedup claimed'})
        for path in self.out.rglob('*'):
            if path.is_file() and path.suffix in ('.txt', '.conf'):
                path.write_text(sanitize_text(path.read_text(), *self.auth))
        self.write('artifact-sha256.json',{str(p.relative_to(self.out)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.out.rglob('*') if p.is_file() and p.name!='artifact-sha256.json'})

    def run(self):
        try:
            self.gate('readiness',self.configure)
            if self.results['readiness']['status']=='PASS':
                for name,fn in [('healthy',self.healthy),('fault-recovery-trials',self.trials),('freshness-null',self.freshness),
                    ('invalid-ordering-restart',self.negatives),('individual-write-recovery',self.individual_failure),
                    ('fleet-write-recovery',self.fleet_failure),('mqtt-reconnect',self.reconnect),
                    ('dashboard',self.dashboard),('provider-kuksa-recovery',self.provider_recovery)]:
                    self.gate(name,fn)
            self.results['baseline-regression']={'status':'BLOCKED','reason':'run existing baseline workflow separately; this runner never replaces it'}
            self.results['kanto-v1-09']={'status':'BLOCKED','reason':'requires actual Linux Kanto launch/restart -> fresh source/event -> real twin; Docker is insufficient'}
        finally:self.cleanup()
        required=[v for k,v in self.results.items() if k not in ('baseline-regression','kanto-v1-09')]
        if self.results['readiness']['status']!='PASS':return 2
        return 1 if any(v['status']!='PASS' for v in required) else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidence/v1/verification-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--ditto-source',default='/tmp/qa-v1-ditto-source')
    parser.add_argument('--trials',type=int,default=5)
    parser.add_argument('--chrome',default=os.environ.get('CHROME_PATH',''))
    args=parser.parse_args()
    if args.trials<5:parser.error('at least five trials required; retain failures')
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    return Run(args).run()


if __name__=='__main__':raise SystemExit(main())
