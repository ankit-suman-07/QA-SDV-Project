"""Single-run operator observer; never provisions twins or restores Docker app-002.
Run from repository root with the recovered Python environment after sudo -v.
All privilege operations use sudo -n and the dedicated Kanto namespace/name.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import sys

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
RUNTIME = Path.home() / '.local/share/qa-sdv-v1/runtime'
OUT = ROOT / 'evidence/v1' / ('merged-main-kanto-live-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
CLI = ['sudo', '-n', '/opt/qa-sdv-v1-kanto/bin/kanto-cm', '--host', '/run/qa-sdv-v1-kanto/container-management.sock', '--timeout', '30']
NAME = 'autonomoushealthapp-vehicle-002-shutdown-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')
IMAGE_INFO = json.loads(Path(__file__).with_name('image.json').read_text())
IMAGE = IMAGE_INFO['dockerRef']
IMAGE_SHA = IMAGE_INFO['indexSha256']
created = False
capture = None
lock = threading.Lock()
messages = []
twins = []
sequence = 0
monitoring = False
CAPTURE_NAME = "qa-v1-kanto-observer-" + OUT.name.removeprefix("kanto-live-").lower()

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def stamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert result.tzinfo is not None, 'timestamp has no timezone'
    return result

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

def command(label, argv, timeout=40, required=True):
    before = dict(utc=utc(), monotonicNs=time.monotonic_ns())
    if monitoring:
        observe_twin()
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=min(0.3, max(0.01, deadline - time.monotonic())))
            break
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                proc.kill()
                stdout, stderr = proc.communicate()
                save(label + '-timeout.json', dict(argv=argv, stdout=stdout, stderr=stderr))
                raise AssertionError(label + ' timed out')
            if monitoring:
                observe_twin()
    p = subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)
    if monitoring:
        observe_twin()
    save(label + '.json', dict(argv=argv, request=before, returned=dict(utc=utc(), monotonicNs=time.monotonic_ns()), exit=p.returncode, stdout=p.stdout, stderr=p.stderr))
    if required:
        assert p.returncode == 0, label + ' failed; inspect recorded exit/output'
    return p

def get(label):
    p = command(label, CLI + ['get', '--name', NAME])
    value = json.loads(p.stdout)
    save(label + '-parsed.json', value)
    return value

def running_start(value):
    state = value['state']
    assert state['running'] is True, 'Kanto does not report running'
    return stamp(state['started_at'])

def verify001(thing):
    assert thing['attributes']['vehicleId'] == 'vehicle-001'
    p = thing['features']['v1']['properties']
    assert p['vehicleId'] == 'vehicle-001' and p['health'] == 'HEALTHY' and p['faults'] == [], 'vehicle-001 isolation failure'
    return p['sourceTimestamp']

def observe_twin():
    global sequence
    row = dict(utc=utc(), monotonicNs=time.monotonic_ns(), things={})
    for vehicle in ('vehicle-001', 'vehicle-002'):
        response = requests.get('http://127.0.0.1:18080/api/2/things/sdv:' + vehicle, auth=auth, timeout=3)
        assert response.status_code == 200, 'authenticated twin read failed'
        row['things'][vehicle] = response.json()
    with (OUT / 'twin-timeline.jsonl').open('a') as f:
        f.write(json.dumps(row) + '\n')
    source = verify001(row['things']['vehicle-001'])
    if twins:
        assert stamp(source) >= stamp(verify001(twins[-1]['things']['vehicle-001'])), 'vehicle-001 source regressed'
    twins.append(row)
    return row

def match(label, boundary, previous=None):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        row = observe_twin()
        properties = row['things']['vehicle-002']['features']['v1']['properties']
        with lock:
            observed = list(messages)
        for msg in reversed(observed):
            if msg['wire']['topic'] != 'sdv/vehicle-002/health':
                continue
            event = msg['event']
            if stamp(event['sourceTimestamp']) <= boundary:
                continue
            if previous and (event['eventId'] == previous['eventId'] or stamp(event['sourceTimestamp']) <= stamp(previous['sourceTimestamp'])):
                continue
            expected = dict(event)
            expected['lastEventId'] = expected.pop('eventId')
            if expected != properties:
                continue
            assert row['things']['vehicle-002']['attributes']['vehicleId'] == 'vehicle-002'
            assert event['vehicleId'] == 'vehicle-002' and event['health'] == 'HEALTHY' and event['faults'] == []
            assert stamp(msg['observedAt']) > boundary
            save(label, dict(message=msg, twin=row, comparison='exact complete properties', boundary=boundary.isoformat()))
            return event
        time.sleep(0.2)
    raise AssertionError('No exact fresh MQTT/Ditto match within 45 seconds')

def read_capture():
    with (OUT / 'mqtt.jsonl').open('a') as f:
        for line in capture.stdout:
            f.write(line)
            f.flush()
            wire = json.loads(line)
            event = json.loads(wire['payload'])
            row = dict(wire=wire, event=event, observedAt=utc(), monotonicNs=time.monotonic_ns())
            with lock:
                messages.append(row)

try:
    import requests
    from ditto.mqtt_ingress import validate_event
    source = (RUNTIME / 'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text()
    auth = re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)', source)[0]
    command('sudo-gate', ['sudo', '-n', 'true'])
    clock = command('clock', ['timedatectl', 'show', '-p', 'NTPSynchronized', '-p', 'NTP'])
    assert 'NTPSynchronized=yes' in clock.stdout
    command('chrony', ['chronyc', 'tracking'])
    command('source-sha', ['git', 'rev-parse', 'HEAD'])
    listing = command('kanto-list-before', CLI + ['list'])
    assert not re.search(r'\brunning\b', listing.stdout, re.I), 'A dedicated namespace app is already running'
    previous_pilot = command('previous-pilot-state', CLI + ['get', '--name', 'autonomoushealthapp-vehicle-002'])
    assert json.loads(previous_pilot.stdout)['state']['running'] is False
    assert NAME not in listing.stdout, 'New pilot name already exists; inspect manually'
    command('import-image', ['sudo','-n','ctr','--address','/run/containerd/containerd.sock','--namespace','qa-sdv-v1-kanto','images','import','--platform','linux/amd64',IMAGE_INFO['archive']], timeout=90)
    images = command('namespace-images', ['sudo', '-n', 'ctr', '--address', '/run/containerd/containerd.sock', '--namespace', 'qa-sdv-v1-kanto', 'images', 'list'])
    assert any(IMAGE in line and IMAGE_SHA in line for line in images.stdout.splitlines()), 'Imported image identity mismatch'
    inventory = command('docker-before', ['docker', 'ps', '-a', '--format', '{{.Names}} {{.Status}}'])
    stopped = command('docker-app002', ['docker', 'inspect', 'qa-v1-kanto-prereq-edge-app-002-1', '--format', '{{.State.Status}}'])
    assert stopped.stdout.strip() == 'exited'
    identity = json.loads((RUNTIME / 'ingress-identity.json').read_text())
    proc = Path('/proc') / str(identity['pid'])
    assert proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == identity['startTicks']
    assert proc.joinpath('cmdline').read_bytes().decode().strip('\0').split('\0') == identity['argv']
    observe_twin()
    command('render', [str(RUNTIME / 'venv-3.12/bin/python'), 'velocitas-app/kanto/prepare_v1_pilot.py', '--config', 'velocitas-app/kanto/pilot-config.local-linux.json', '--mode', 'render'])
    descriptor = json.loads(json.loads((OUT / 'render.json').read_text())['stdout'])
    descriptor['container_name'] = NAME
    descriptor['image']['name'] = IMAGE
    save('descriptor.json', descriptor)
    monitoring = True
    capture_args = ['docker', 'run', '--rm', '--name', CAPTURE_NAME, '--network', 'host', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '-e', 'TZ=UTC', '--entrypoint', 'mosquitto_sub', 'eclipse-mosquitto@sha256:75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98', '-h', '127.0.0.1', '-p', '18883', '-q', '1', '-V', 'mqttv5', '--retain-as-published', '-t', 'sdv/vehicle-001/health', '-t', 'sdv/vehicle-002/health', '-F', '%j', '-W', '180']
    capture = subprocess.Popen(capture_args, stdout=subprocess.PIPE, stderr=(OUT / 'mqtt.stderr').open('w'), text=True)
    thread = threading.Thread(target=read_capture, daemon=True)
    thread.start()
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        observe_twin()
        with lock:
            observed = list(messages)
        assert not any(m['event']['vehicleId'] == 'vehicle-002' for m in observed), 'Unexpected vehicle-002 publisher before launch'
        time.sleep(0.3)
    assert observed, 'No MQTT subscription receipt'
    command('create', CLI + ['create', '--file', str(OUT / 'descriptor.json')])
    created = True
    save('pre-start-status.json', get('created-status'))
    initial_boundary = stamp(utc())
    command('initial-start', CLI + ['start', '--name', NAME])
    initial = get('initial-state')
    initial_started = running_start(initial)
    assert initial_started > initial_boundary
    old = match('initial-correlation.json', initial_started)
    cycles = []
    for cycle in range(1, 4):
        prefix = 'cycle-' + str(cycle)
        command(prefix + '-stop', CLI + ['stop', '--name', NAME])
        stopped_state = get(prefix + '-stopped-state')
        assert stopped_state['state']['running'] is False
        assert stopped_state['state']['exit_code'] == 0
        for _ in range(3):
            observe_twin()
            time.sleep(0.3)
        request = dict(utc=utc(), monotonicNs=time.monotonic_ns())
        save(prefix + '-restart-request.json', request)
        command(prefix + '-start', CLI + ['start', '--name', NAME])
        restarted = get(prefix + '-restarted-state')
        restarted_at = running_start(restarted)
        assert restarted_at > initial_started
        boundary = max(restarted_at, stamp(request['utc']), stamp(old['sourceTimestamp']))
        new = match(prefix + '-restart-correlation.json', boundary, old)
        cycles.append(dict(cycle=cycle,eventId=new['eventId'],sourceTimestamp=new['sourceTimestamp'],runtimeStartedAt=restarted['state']['started_at'],request=request,previousSourceTimestamp=old['sourceTimestamp']))
        initial_started = restarted_at
        old = new
        for _ in range(3):
            observe_twin()
            time.sleep(0.3)
    with lock:
        observed = list(messages)
    previous001 = None
    for msg in observed:
        wire, event = msg['wire'], msg['event']
        validate_event(wire['topic'], event)
        assert wire['qos'] == 1 and wire['retain'] is False
        age = (stamp(wire['tst']) - stamp(event['sourceTimestamp'])).total_seconds()
        assert -1 <= age <= 5, 'MQTT source freshness failure'
        if event['vehicleId'] == 'vehicle-001':
            assert event['health'] == 'HEALTHY' and event['faults'] == []
            if previous001:
                assert stamp(event['sourceTimestamp']) > previous001
            previous001 = stamp(event['sourceTimestamp'])
    assert previous001 is not None
    assert stamp(verify001(twins[-1]['things']['vehicle-001'])) > stamp(verify001(twins[0]['things']['vehicle-001']))
    save('result.json', dict(result='PASS',scope='same-device managed stop/start pilot only; no full V1 acceptance, remote LAN or crash auto-restart claim',eventId=new['eventId'],sourceTimestamp=new['sourceTimestamp'],runtimeStartedAt=restarted_at.isoformat(),request=request,previousSourceTimestamp=cycles[-1]['previousSourceTimestamp'],mqttMessages=len(observed),twinSnapshots=len(twins),cycles=cycles))
except BaseException as error:
    # Exception text may contain authentication from HTTP libraries; never emit it.
    save('result.json', dict(result='FAIL' if created else 'BLOCKED',errorType=type(error).__name__,detail=str(error) if isinstance(error, AssertionError) else 'Inspect stage records; exception content intentionally omitted'))
finally:
    if created:
        try:
            command('cleanup-stop', CLI + ['stop', '--name', NAME])
            final = get('cleanup-state')
            assert final['state']['running'] is False
            assert final['state']['exit_code'] == 0
            command('application-logs', CLI + ['logs','--name',NAME,'--tail','250'])
            save('cleanup.json',dict(kantoStopped=True,dockerApp002='left stopped',prerequisitesAndIngress='left running'))
        except BaseException as error:
            save('cleanup.json',dict(kantoStopped=False,errorType=type(error).__name__,dockerApp002='DO NOT START'))
            save('result.json',dict(result='FAIL',reason='cleanup not verified; inspect retained stage outputs'))
    if capture:
        monitoring = False
        command('observer-stop', ['docker', 'stop', '--time', '3', CAPTURE_NAME], required=False)
        try:
            capture.terminate()
            capture.wait(timeout=5)
        except subprocess.TimeoutExpired:
            capture.kill()
            capture.wait(timeout=5)
        save('capture-exit.json',dict(exit=capture.returncode,observerTerminatedByRunner=True))
    print('Evidence:',OUT)
    print((OUT / 'result.json').read_text() if (OUT / 'result.json').exists() else 'Result missing')
