"""Small interactive orchestrator for an already prepared real local V1 deployment."""
import argparse
from collections import deque
from datetime import datetime, timezone
import functools
import hashlib
import getpass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.v1_acceptance.assertions import fleet, preserved
from scripts.v1_acceptance.evidence import sanitize_text
from ditto.mqtt_ingress import validate_event

RUNTIME = Path.home()/'.local/share/qa-sdv-v1/runtime'


class IsolationError(Exception):
    pass


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timezone required')
    return result


def utc():
    return datetime.now(timezone.utc).isoformat()


def is_publisher(service, vehicle):
    # Providers carry SIMULATED_VEHICLE_ID too, but publish to KUKSA, not MQTT.
    # Unknown containers with an app identity are conservatively treated as publishers.
    return vehicle is not None and service not in ('provider-001', 'provider-002')


def publisher_guard(docker_names, kanto_running, expected):
    if any(name != expected for name in docker_names) or len(docker_names)+int(kanto_running) > 1:
        raise RuntimeError('Refusing duplicate/unknown vehicle-002 publisher; inspect Docker and dedicated Kanto namespace')


def post_restart(event, old_id, old_source, request, runtime):
    return event['eventId'] != old_id and timestamp(event['sourceTimestamp']) > max(
        timestamp(old_source), timestamp(request), timestamp(runtime))


def observed_status(running, source=None, *, now=None):
    if not running:
        return 'FAILED'
    if source:
        age = ((now or datetime.now(timezone.utc))-timestamp(source)).total_seconds()
        return 'PUBLISHING' if -1 <= age <= 5 else 'STALE'
    return 'RUNNING'


def bounded_wait(check, seconds, *, clock=time.monotonic, pause=time.sleep):
    deadline = clock()+seconds
    last = None
    while clock() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, ValueError, KeyError, AssertionError, RuntimeError) as error:
            last = type(error).__name__
        pause(.3)
    raise RuntimeError('readiness/propagation deadline exceeded; last failure type '+str(last))


def tcp(host, port):
    try:
        with socket.create_connection((host, port), timeout=.5):
            return True
    except OSError:
        return False


def serve(port, api):
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/', '/index.html'):
                text = (ROOT/'frontend/index.html').read_text().replace('</head>',
                    '<script>globalThis.SDV_CONFIG='+json.dumps({'API_BASE_URL':api})+';</script></head>')
                body = text.encode()
                self.send_response(200); self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            else:
                super().do_GET()
    ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Handler, directory=str(ROOT/'frontend'))).serve_forever()


class Demo:
    def __init__(self, config, check=False):
        import requests
        import paho.mqtt.client as mqtt
        self.requests, self.mqtt_module = requests, mqtt
        self.c = config
        self.check_only = check
        self.out = ROOT/'evidence/v1'/('demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        self.out.mkdir(parents=True, exist_ok=False)
        self.auth = (os.getenv('SDV_V1_DITTO_USERNAME') or getpass.getpass('Ditto username (hidden): '),
                     os.getenv('SDV_V1_DITTO_PASSWORD') or getpass.getpass('Ditto password: '))
        self.processes = []; self.log_threads = []; self.observer = None
        self.events = deque(maxlen=1000); self.lock = threading.Lock(); self.subscribed = threading.Event()
        self.active = False; self.changed_docker = False; self.created = False; self.keep = False
        self.name = 'autonomoushealthapp-vehicle-002-demo-'+self.out.name.removeprefix('demo-').lower()
        self.kanto_ready = False; self.isolation_failed = False
        self.cli = ['sudo', '-n', config['kantoCli'], '--host', config['kantoSocket'], '--timeout', '15']
        self.save('baseline.json', {'sha':self.git('rev-parse','HEAD'), 'dirty':self.git('status','--porcelain'),
            'startedAt':utc(), 'config':config, 'toolHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'scripts/v1_demo.py',ROOT/'scripts/run-v1-demo.sh')}, 'scope':'same-device narrated demo; not acceptance, remote LAN or automatic crash restart'})

    def git(self, *args):
        return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

    def save(self, name, value):
        (self.out/name).write_text(json.dumps(value,indent=2)+'\n')

    def append(self, name, value):
        with (self.out/name).open('a') as f:
            f.write(json.dumps(value)+'\n')

    def command(self, args, *, inspect=False, required=True, timeout=30):
        start=time.monotonic()
        try:
            p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired:
            self.append('commands.jsonl',{'argv':args,'exit':'TIMEOUT','seconds':time.monotonic()-start})
            raise RuntimeError('command timeout; see evidence')
        self.append('commands.jsonl',{'argv':args,'exit':p.returncode,'seconds':time.monotonic()-start,
            'stdout':'filtered Docker metadata only' if inspect else sanitize_text(p.stdout,*self.auth),
            'stderr':sanitize_text(p.stderr,*self.auth)})
        if required and p.returncode:
            raise RuntimeError('command failed; see commands.jsonl')
        return p

    def http(self, path, *, ditto=False, payload=None):
        base=self.c['ditto'] if ditto else self.c['backend']
        try:
            r=self.requests.request('POST' if payload is not None else 'GET',base+path,
                auth=self.auth if ditto else None,json=payload,timeout=2,allow_redirects=False)
            if r.headers.get('X-SDV-Mock'):
                raise RuntimeError('mock endpoint refused')
            if 300 <= r.status_code < 400:
                raise RuntimeError('HTTP redirect refused; inspect configured local endpoint')
            r.raise_for_status()
            return r.json()
        except self.requests.RequestException:
            raise RuntimeError('real HTTP read/action failed (credentials and URLs omitted)') from None

    def thing(self, vehicle):
        return self.http('/api/2/things/sdv:'+vehicle,ditto=True)

    def docker_inventory(self):
        ids=self.command(['docker','ps','-aq']).stdout.split()
        values=json.loads(self.command(['docker','inspect',*ids],inspect=True).stdout) if ids else []
        filtered=[]
        for value in values:
            env=dict(x.split('=',1) for x in value['Config'].get('Env',[]) if '=' in x)
            filtered.append({'name':value['Name'].lstrip('/'),'running':value['State']['Running'],
                'vehicle':env.get('SIMULATED_VEHICLE_ID'),
                'publisher':is_publisher((value['Config'].get('Labels') or {}).get('com.docker.compose.service'),env.get('SIMULATED_VEHICLE_ID')),'image':value['Image'],
                'configuredImage':value['Config']['Image'],'pid':value['State']['Pid'],'exitCode':value['State']['ExitCode'],'startedAt':value['State']['StartedAt']})
        self.save('docker-inventory.json',filtered)
        return filtered

    def guard(self):
        inv=self.docker_inventory()
        listing=self.command(self.cli+['list']).stdout
        # Dedicated namespace must have no other active containers, including unknown apps.
        active=[]
        for line in listing.splitlines():
            cells=[x.strip() for x in line.split('|')]
            if len(cells)>3 and cells[3].lower() not in ('status','stopped','exited','created') and not set(cells[3]) <= {'-'}:
                active.append(cells[1])
        if any(name != self.name for name in active):
            raise RuntimeError('Other active Kanto publisher/runtime found; inspect manually before demo')
        names=[v['name'] for v in inv if v['vehicle']=='vehicle-002' and v['publisher'] and v['running']]
        publisher_guard(names,self.name in active,self.c['dockerApp002'])
        return inv

    def start_capture(self):
        mqtt=self.mqtt_module
        self.observer=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=self.name+'-observer')
        def connected(client, userdata, flags, code, properties):
            if code == 0:
                client.subscribe('sdv/+/health',qos=1)
        self.observer.on_connect=connected
        self.observer.on_subscribe=lambda *args:self.subscribed.set()
        def message(client, userdata, msg):
            try:
                event=json.loads(msg.payload)
                validate_event(msg.topic,event)
                if msg.qos != 1 or msg.retain:
                    raise ValueError('expected live QoS1/non-retained')
                if event['vehicleId']=='vehicle-001' and (event['health']!='HEALTHY' or event['faults']):
                    self.isolation_failed=True
                row={'event':event,'topic':msg.topic,'qos':msg.qos,'retain':msg.retain,'receivedAt':utc()}
                with self.lock:
                    self.events.append(row)
                    self.append('mqtt.jsonl',row)
            except (ValueError, RuntimeError):
                self.append('mqtt-errors.jsonl',{'at':utc(),'error':'invalid event; no unvalidated payload retained'})
        self.observer.on_message=message
        self.observer.connect_timeout=2
        self.observer.connect(self.c['mqttHost'],self.c['mqttPort']);self.observer.loop_start()
        if not self.subscribed.wait(5):
            raise RuntimeError('MQTT subscription not acknowledged')

    def snapshot(self):
        things={v:self.thing(v) for v in ('vehicle-001','vehicle-002')}
        views={v:self.http('/api/v1/vehicles/'+v+'/state') for v in things}
        summary=self.http('/api/v1/fleet');fleet(summary)
        materialized=self.thing('fleet-v1')['features']['summary']['properties'];fleet(materialized)
        return {'at':utc(),'things':things,'views':views,'fleetApi':summary,'fleetThing':materialized}

    def match(self, health, boundary=None, previous=None):
        snap=self.snapshot()
        one=snap['views']['vehicle-001']
        self.append('isolation.jsonl',{'at':utc(),'vehicle001':one})
        if self.isolation_failed or one['healthStatus']!='HEALTHY' or one['activeFaults']:
            raise IsolationError('vehicle-001 isolation failed')
        if one['availability']!='AVAILABLE':return False
        with self.lock:
            events=list(self.events)
        for vehicle in ('vehicle-001','vehicle-002'):
            props=snap['things'][vehicle]['features']['v1']['properties']
            row=next((e for e in reversed(events) if e['event']['vehicleId']==vehicle and e['event']['eventId']==props['lastEventId']),None)
            if not row:
                return False
            event=row['event'];preserved(event,snap['things'][vehicle],snap['views'][vehicle])
            if observed_status(True,event['sourceTimestamp'])!='PUBLISHING':
                return False
            if vehicle=='vehicle-002':
                if event['health']!=health:
                    return False
                if health=='CRITICAL' and 'LIDAR_OBSTRUCTION' not in event['faults']:
                    return False
                if health=='HEALTHY' and event['faults']:
                    return False
                if boundary and not post_restart(event,previous['lastEventId'],previous['sourceTimestamp'],boundary['request'],boundary['runtime']):
                    return False
            for summary in (snap['fleetApi'],snap['fleetThing']):
                view=next(v for v in summary['vehicles'] if v['vehicleId']==vehicle)
                assert view['healthStatus']==snap['views'][vehicle]['healthStatus'] and view['availability']=='AVAILABLE'
                preserved(event,snap['things'][vehicle],view)
        return snap

    def table(self, label):
        rows=[];snap={}
        try: inventory=self.docker_inventory()
        except (RuntimeError, OSError, ValueError): inventory=[]
        for vehicle in ('vehicle-001','vehicle-002'):
            props=None
            try:
                thing=self.thing(vehicle);props=thing['features']['v1']['properties'];snap[vehicle]=thing
                state='READY' if observed_status(True,props['sourceTimestamp'])=='PUBLISHING' else 'STALE'
            except (RuntimeError,KeyError,ValueError):
                state='FAILED'
            identity=(props['sourceTimestamp']+' '+props['lastEventId'][:24]) if props else '-'
            rows.append(['Ditto',vehicle,state,self.c['ditto']+'/api/2/things/sdv:'+vehicle,identity])
            with self.lock:
                event=next((e['event'] for e in reversed(self.events) if e['event']['vehicleId']==vehicle),None)
            running=any(v['vehicle']==vehicle and v['publisher'] and v['running'] for v in inventory)
            runtime='Docker'
            if vehicle=='vehicle-002' and self.created:
                try:
                    value=json.loads(self.command(self.cli+['get','--name',self.name]).stdout)
                    running=value['state']['running'];runtime='Kanto '+self.name+' pid='+str(value['state']['pid'])
                except (RuntimeError,ValueError,KeyError): running=False
            status=observed_status(running,event['sourceTimestamp'] if event else None)
            # PUBLISHING requires actual observed MQTT, not container existence.
            rows.append(['App / MQTT',vehicle,status,runtime+'; sdv/'+vehicle+'/health',
                event['sourceTimestamp']+' '+event['eventId'][:24] if event else '-'])
            rows.append(['KUKSA',vehicle,'RUNNING' if tcp('127.0.0.1',self.c['kuksaPorts'][vehicle]) else 'FAILED',
                '127.0.0.1:'+str(self.c['kuksaPorts'][vehicle]),'TCP only; integration shown above'])
            try:
                v=self.http('/api/v1/vehicles/'+vehicle+'/state')
                state='READY' if v['availability']=='AVAILABLE' else 'STALE'
            except (RuntimeError,KeyError):state='FAILED'
            rows.append(['Backend',vehicle,state,self.c['backend']+'/api/v1/vehicles/'+vehicle+'/state','-'])
            try:
                response=self.requests.get(self.c['providers'][vehicle]+'/health',timeout=2)
                assert response.status_code==200
                state='READY'
            except (self.requests.RequestException,AssertionError):state='FAILED'
            rows.append(['Provider',vehicle,state,self.c['providers'][vehicle],'-'])
        try:
            summary=self.http('/api/v1/fleet');fleet(summary)
            materialized=self.thing('fleet-v1')['features']['summary']['properties'];fleet(materialized)
            fresh=all(observed_status(True,v['sourceTimestamp'])=='PUBLISHING' for v in materialized['vehicles'])
            same=[v['lastEventId'] for v in summary['vehicles']]==[v['lastEventId'] for v in materialized['vehicles']]
            state='READY' if fresh and same and summary['availableVehicles']==2 else 'RUNNING' if fresh else 'STALE'
        except (RuntimeError,AssertionError,KeyError):state='FAILED'
        rows.append(['MQTT','both','READY' if self.subscribed.is_set() else 'RUNNING' if tcp(self.c['mqttHost'],self.c['mqttPort']) else 'FAILED',str(self.c['mqttHost'])+':'+str(self.c['mqttPort']),'subscription acknowledged' if self.subscribed.is_set() else 'TCP only'])
        rows.append(['Fleet','both',state,self.c['backend']+'/api/v1/fleet','API + authenticated fleet Thing read'])
        try:
            response=self.requests.get(self.c['frontend'],timeout=2)
            assert response.status_code==200 and 'Fleet dashboard' in response.text
            state='READY'
        except (self.requests.RequestException,AssertionError):state='FAILED'
        rows.append(['Dashboard','both',state,self.c['frontend'],'HTTP/UI shell; inspect rendered state'])
        rows.append(['Kanto','vehicle-002','READY' if self.kanto_ready else 'FAILED',self.c['kantoSocket'],'namespace qa-sdv-v1-kanto; see runtime states'])
        print('\n'+label+'\nComponent | Vehicle | Observed | Endpoint/runtime | Source UTC / event')
        for row in rows:print(' | '.join(row))
        self.save('status-'+label.replace(' ','-')+'.json',{'at':utc(),'rows':rows,'things':snap})

    def spawn(self, args, env, label):
        process=subprocess.Popen(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        self.processes.append((process,label))
        def log():
            with (self.out/(label+'.txt')).open('a') as f:
                for line in process.stdout:
                    f.write(sanitize_text(line,*self.auth));f.flush()
        thread=threading.Thread(target=log,daemon=True);thread.start();self.log_threads.append(thread)
        self.append('owned-processes.jsonl',{'argv':args,'pid':process.pid,'label':label})

    def prepare(self):
        self.command(['docker','version'])
        for required in (Path(self.c['kantoCli']), Path(self.c['kantoSocket']), Path(self.c['imageInfo']).expanduser()):
            if not required.exists():
                raise RuntimeError('Missing '+str(required)+'; follow velocitas-app/kanto/LINUX-RUNTIME.md and configure demo.json; no install/build attempted')
        for vehicle,port in self.c['kuksaPorts'].items():
            if not tcp('127.0.0.1',port):
                raise RuntimeError('KUKSA '+vehicle+' is not listening; restore documented prerequisite Compose project first')
        for vehicle,base in self.c['providers'].items():
            try:
                response=self.requests.get(base+'/api/v1/vehicles/'+vehicle+'/scenarios/LIDAR_OBSTRUCTION',timeout=2,allow_redirects=False)
                response.raise_for_status();context=response.json()
                if context['active']:
                    raise RuntimeError("Existing scenario active on "+vehicle+"; launcher will not clear someone else's scenario")
            except (self.requests.RequestException,ValueError,KeyError):
                raise RuntimeError('Provider context unavailable for '+vehicle+'; restore documented edge prerequisites') from None
        try:
            self.thing('vehicle-001');self.thing('vehicle-002');self.thing('fleet-v1')
        except RuntimeError:
            raise RuntimeError('Authenticated individual/fleet Thing reads required. Inspect credentials/resources; missing fleet provisioning: python scripts/v1_fleet_provision.py with documented provisioning credentials and distinct subjects. No twins/policies modified.') from None
        # Interactive sudo uses the user's terminal; commands afterwards are noninteractive/fail closed.
        if subprocess.run(['sudo','-v']).returncode:
            raise RuntimeError('sudo authentication failed')
        self.kanto_ready=True
        inv=self.guard()
        for key in ('app001','dockerApp002'):
            if not any(v['name']==self.c[key] for v in inv):
                raise RuntimeError('Missing documented edge container '+self.c[key]+'; follow LINUX-RUNTIME.md, no automatic deployment')
        if not any(v['name']==self.c['app001'] and v['running'] for v in inv):
            raise RuntimeError('app001 must already run; inspect documented edge deployment')
        self.start_capture()
        if not any(v['name']==self.c['dockerApp002'] and v['running'] for v in inv):
            self.create_kanto()
        if not tcp('127.0.0.1',int(self.c['backend'].rsplit(':',1)[1])):
            jar=Path(self.c['backendJar']).expanduser()
            java=RUNTIME/'jdk21/bin/java'
            if not jar.is_file() or not java.is_file():
                raise RuntimeError('Missing packaged backend/Java21: use documented clean verify and set backendJar; no build attempted')
            env=dict(os.environ,SERVER_ADDRESS='127.0.0.1',SERVER_PORT=self.c['backend'].rsplit(':',1)[1],
                SDV_VEHICLE_IDS='vehicle-001,vehicle-002',SDV_V1_DITTO_MODE='live',SDV_V1_DITTO_BASE_URL=self.c['ditto'],
                SDV_V1_DITTO_USERNAME=self.auth[0],SDV_V1_DITTO_PASSWORD=self.auth[1],SDV_V1_FLEET_ENABLED='true',
                SDV_V1_FLEET_USERNAME=self.auth[0],SDV_V1_FLEET_PASSWORD=self.auth[1],SDV_SIMULATOR_MODE='http',
                SDV_PROVIDER_001_BASE_URL=self.c['providers']['vehicle-001'],SDV_PROVIDER_002_BASE_URL=self.c['providers']['vehicle-002'])
            self.save('backend-artifact.json',{'path':str(jar),'sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),'java':str(java)})
            self.command([str(java),'-version'])
            self.spawn([str(java),'-jar',str(jar)],env,'backend')
        # An occupied API port is reused only after real state/fleet readiness, never displaced.
        bounded_wait(lambda:self.http('/api/v1/vehicles')=={'vehicleIds':['vehicle-001','vehicle-002']},45)
        port=int(self.c['frontend'].rsplit(':',1)[1])
        if not tcp('127.0.0.1',port):
            env={k:v for k,v in os.environ.items() if not any(x in k for x in ('PASSWORD','USERNAME','SECRET','TOKEN'))}
            self.spawn([sys.executable,'-B',str(Path(__file__)),'--serve',str(port),self.c['backend']],env,'frontend')
        bounded_wait(lambda:self.match('HEALTHY'),45)
        def frontend_ready():
            try:
                response=self.requests.get(self.c['frontend'],timeout=2)
                return response.status_code==200 and self.c['backend'] in response.text
            except self.requests.RequestException:return False
        bounded_wait(frontend_ready,10)

    def create_kanto(self):
        self.guard()
        info=json.loads(Path(self.c['imageInfo']).expanduser().read_text())
        diff=self.git('diff',info['sourceSha'],'--','velocitas-app/app','velocitas-app/.velocitas.json','velocitas-app/.velocitas-lock.json')
        if diff:
            raise RuntimeError('Configured image source differs from current app; prepare a verified image explicitly')
        images=self.command(['sudo','-n','ctr','--address','/run/containerd/containerd.sock','--namespace','qa-sdv-v1-kanto','images','list']).stdout
        if not any(info['dockerRef'] in l and info['indexSha256'] in l for l in images.splitlines()):
            raise RuntimeError('Image not imported. Run: sudo ctr --address /run/containerd/containerd.sock --namespace qa-sdv-v1-kanto images import --platform linux/amd64 '+info['archive'])
        self.save('image.json',info)
        sys.path.insert(0,str(ROOT/'velocitas-app/kanto'))
        from render_pilot_config import render_descriptor
        config=json.loads((ROOT/'velocitas-app/kanto/pilot-config.local-linux.json').read_text())
        config.update(container_name=self.name,image=info['dockerRef'],mqtt_host=self.c['mqttHost'],mqtt_port=self.c['mqttPort'],kuksa_port=self.c['kuksaPorts']['vehicle-002'])
        descriptor=render_descriptor(config);self.save('descriptor.json',descriptor)
        self.created=True  # cleanup must inspect even if create response is lost
        self.command(self.cli+['create','--file',str(self.out/'descriptor.json')])
        self.command(self.cli+['start','--name',self.name])
        self.guard()

    def action(self, action):
        started=time.monotonic();request=utc()
        ack=self.http('/api/v1/diagnostics/actions',payload={'vehicleId':'vehicle-002','action':action,'scenario':'LIDAR_OBSTRUCTION'})
        self.append('actions.jsonl',{'request':request,'action':action,'ack':ack,'ackSeconds':time.monotonic()-started,'meaning':'dispatch acknowledgement, not observed completion'})
        if ack.get('status')!='ACCEPTED':raise RuntimeError('backend A3 action not accepted')
        return started

    def step(self, label, cue, operation=None):
        input('\n'+cue+'\nPress Enter to continue: ')
        start=time.monotonic()
        try:
            if operation:operation()
        except BaseException:
            self.append('steps.jsonl',{'step':label,'at':utc(),'seconds':time.monotonic()-start,'result':'FAIL/INTERRUPTED'})
            raise
        self.table(label)
        self.append('steps.jsonl',{'step':label,'at':utc(),'seconds':time.monotonic()-start,'result':'PASS'})

    def lifecycle(self):
        previous=self.thing('vehicle-002')['features']['v1']['properties']
        self.guard()
        if not self.created:
            self.changed_docker=True
            self.command(['docker','stop','--time','12',self.c['dockerApp002']])
            self.guard()  # stop confirmed before Kanto creation; never overlap
            self.create_kanto()
            bounded_wait(lambda:self.match('HEALTHY'),45)
        previous=self.thing('vehicle-002')['features']['v1']['properties']
        before=json.loads(self.command(self.cli+['get','--name',self.name]).stdout)
        self.save('managed-before-stop.json',before)
        self.command(self.cli+['stop','--name',self.name])
        stopped=json.loads(self.command(self.cli+['get','--name',self.name]).stdout)
        self.save('managed-stopped.json',stopped)
        if stopped['state']['running'] or stopped['state']['exit_code']!=0:
            raise RuntimeError('Kanto managed stop did not exit cleanly')
        if Path('/proc',str(before['state']['pid'])).exists():
            raise RuntimeError('Old managed process still exists')
        request=utc();self.command(self.cli+['start','--name',self.name])
        state=json.loads(self.command(self.cli+['get','--name',self.name]).stdout)
        assert state['state']['running']
        self.save('managed-restarted.json',state)
        boundary={'request':request,'runtime':state['state']['started_at']}
        snap=bounded_wait(lambda:self.match('HEALTHY',boundary,previous),45)
        self.save('post-restart-match.json',{'boundaries':boundary,'previous':previous,'observed':snap})
        self.guard()

    def run(self):
        self.table('startup')
        if self.check_only:
            # No sudo, scenario mutation, observer or service start in check mode.
            inv=self.docker_inventory()
            names=[v['name'] for v in inv if v['vehicle']=='vehicle-002' and v['publisher'] and v['running']]
            publisher_guard(names,False,self.c['dockerApp002'])
            self.snapshot()
            print('Read-only checks complete; Kanto/exclusive publisher and full readiness remain to be checked interactively.')
            return
        self.prepare();self.table('ready')
        print('Dashboard:',self.c['frontend'],'API:',self.c['backend']+'/api/v1/fleet')
        print('Twins:',self.c['ditto']+'/api/2/things/sdv:vehicle-001',self.c['ditto']+'/api/2/things/sdv:vehicle-002')
        if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            if __import__('shutil').which('xdg-open'):
                subprocess.Popen(['xdg-open',self.c['frontend']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.step('healthy','MVP → V1: two identified vehicles, isolated twins and one live fleet/dashboard.',lambda:bounded_wait(lambda:self.match('HEALTHY'),45))
        def inject():
            self.active=True;start=self.action('INJECT_SCENARIO')
            snap=bounded_wait(lambda:self.match('CRITICAL'),45);self.save('fault.json',snap)
            self.append('observations.jsonl',{'step':'fault','completionSeconds':time.monotonic()-start,'meaning':'polled observed completion, not transport-only latency'})
        self.step('fault','Inject vehicle-002 obstruction through backend A3. Show the fault and vehicle-001 isolation.',inject)
        def clear():
            start=self.action('CLEAR_SCENARIO');snap=bounded_wait(lambda:self.match('HEALTHY'),45)
            self.active=False;self.save('recovered.json',snap)
            self.append('observations.jsonl',{'step':'recovery','completionSeconds':time.monotonic()-start})
        self.step('recovery','Clear through backend A3. Wait for actual recovery rather than treating ACK as completion.',clear)
        self.step('managed-restart','Kanto managed stop/start: exclusive app002, clean exit, fresh source/event matched at MQTT and real Ditto.',self.lifecycle)
        print('\nShow existing specs, skill-use/traceability and exact-head CI evidence next. No records regenerated.')
        print('This demonstrates same-device managed restart, not crash auto-restart, remote LAN or full V1 acceptance.')
        self.keep=input('Keep demo services running in this terminal? [y/N]: ').strip().lower()=='y'
        if self.keep:
            print('Demo passed. Services remain running while this terminal stays open.')
            try: input('Press Enter (or Ctrl+C) to restore launcher changes and exit: ')
            finally: self.keep=False

    def cleanup(self):
        errors=[]
        if self.isolation_failed:errors.append('vehicle-001 isolation failed during observation')
        if self.active:
            try:self.action('CLEAR_SCENARIO');self.active=False
            except Exception:errors.append('Scenario clear failed; use backend A3 CLEAR_SCENARIO for vehicle-002')
        if self.observer:
            self.observer.disconnect()
            closer=threading.Thread(target=self.observer.loop_stop,daemon=True);closer.start();closer.join(timeout=3)
            if closer.is_alive():errors.append('MQTT observer close deadline exceeded')
        stopped=not self.created
        if self.created and not self.keep:
            try:
                self.command(self.cli+['stop','--name',self.name])
                value=json.loads(self.command(self.cli+['get','--name',self.name]).stdout)
                self.save('cleanup-kanto.json',value)
                self.command(self.cli+['logs','--name',self.name,'--tail','120'],required=False)
                stopped=not value['state']['running']
                if not stopped or value['state']['exit_code']!=0:errors.append('Kanto cleanup not clean; do not start Docker app002')
            except Exception:errors.append('Kanto cleanup unverified; DO NOT start Docker app002')
        if self.changed_docker and not self.keep and stopped:
            try:self.command(['docker','start',self.c['dockerApp002']])
            except Exception:errors.append('Docker app002 restoration failed; inspect evidence')
        if not self.keep:
            for process,label in reversed(self.processes):
                process.terminate()
                try:process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait();errors.append(label+' exceeded cleanup deadline')
                self.append('process-exits.jsonl',{'pid':process.pid,'label':label,'exit':process.returncode})
            for thread in self.log_threads:thread.join(timeout=1)
        self.save('cleanup.json',{'keep':self.keep,'errors':errors,'dockerChanged':self.changed_docker,'kantoName':self.name if self.created else None,
            'ownedProcesses':[{'pid':p.pid,'label':l} for p,l in self.processes],'sharedResources':'twins/policies/volumes/prerequisite services untouched'})
        if errors:print('CLEANUP REQUIRES ATTENTION:', '; '.join(errors))
        return not errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=str(RUNTIME/'demo.json'))
    parser.add_argument('--check',action='store_true',help='Read-only HTTP/state rehearsal; no sudo or service/scenario changes')
    parser.add_argument('--serve',nargs=2,metavar=('PORT','API'),help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.serve:
        serve(int(args.serve[0]),args.serve[1]);return 0
    demo=None;success=False
    try:
        path=Path(args.config)
        if not path.is_file():
            raise RuntimeError('Missing '+str(path)+'. Copy scripts/v1-demo.example.json there and configure prepared resources; no deployments/builds performed.')
        config=json.loads(path.read_text())
        allowed=set(json.loads((ROOT/'scripts/v1-demo.example.json').read_text()))
        if set(config)!=allowed:
            raise RuntimeError('Use only documented demo.json fields; credentials belong in terminal prompts/environment')
        # Deliberately same-host only; refuse embedded credentials and non-loopback service targets.
        from urllib.parse import urlsplit
        urls={key:config[key] for key in ('ditto','backend','frontend')}
        urls.update(config['providers'])
        for key,value in urls.items():
            url=urlsplit(value)
            if url.hostname not in ('127.0.0.1','localhost') or url.username or url.password or url.scheme!='http' or url.query or url.fragment or url.path not in ('','/'):
                raise RuntimeError('Only credential-free local HTTP URLs supported for '+key)
        if config['frontend'] not in ('http://localhost:3000','http://localhost:5173','http://localhost:8081','http://localhost:8080'):
            raise RuntimeError('Frontend origin must match existing backend CORS (localhost ports3000/5173/8081/8080)')
        if config['mqttHost'] not in ('127.0.0.1','localhost'):
            raise RuntimeError('Same-host MQTT only; LAN is outside this demo')
        demo=Demo(config,args.check)
        signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
        demo.run();success=True
    except (Exception,KeyboardInterrupt) as error:
        # No exception/HTTP/credential text is printed or saved by default.
        detail=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        print('BLOCKED/FAILED:',detail)
        if demo:
            demo.save('failure.json',{'at':utc(),'type':type(error).__name__,'detail':detail})
            try:demo.table('failed')
            except Exception:pass
    finally:
        if demo:
            signal.signal(signal.SIGINT,signal.SIG_IGN)
            signal.signal(signal.SIGTERM,signal.SIG_IGN)
            clean=demo.cleanup();success=success and clean
            demo.save('result.json',{'result':'PASS' if success else 'BLOCKED/FAIL','checkOnly':args.check,'at':utc(),'notAcceptance':True})
            print('Evidence:',demo.out)
            print('Result:', 'PASS' if success else 'BLOCKED/FAIL')
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
