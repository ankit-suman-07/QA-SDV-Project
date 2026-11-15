"""Fresh combined PR39 checks, adapted from both existing live_check.py records.

Actual two-vehicle edge recovery; separate deterministic pressure source fixture.
No Ditto/credentials/shared policies; full legacy HTTP loop/gateway not exercised.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

import paho.mqtt.client as mqtt
from kuksa_client.grpc import VSSClient

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'vehicle-simulator/src').is_dir())
sys.path.insert(0, str(ROOT))
from ditto.pressure_units import kpa_to_psi
from opensovd.fault_mapper import map_fault_to_opensovd
from uprotocol.transport import publish_vehicle_status, receive_vehicle_status

OUT = Path(__file__).resolve().parent
PATH = 'Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure'
IDS = ('vehicle-001', 'vehicle-002')
project = 'qa-pr39-' + str(os.getpid())
image = project + '-provider'
commands, results, events = [], [], []
lock = threading.Lock()
client = None
active_projects = []


def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')


def run(argv, *, env=None, check=True, timeout=300):
    started = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    log = f'runtime-command-{len(commands):02d}.txt'
    (OUT/log).write_text('\n'.join(x.rstrip() for x in p.stdout.splitlines()).rstrip()+'\n')
    commands.append({'argv':list(map(str,argv)), 'exit':p.returncode,
                     'seconds':time.monotonic()-started, 'output':log})
    save('runtime-commands.json',commands)
    if check and p.returncode:
        raise AssertionError(f'command {len(commands)-1} exit {p.returncode}')
    return p.stdout


def compose(kind, *args, **kwargs):
    return run(['docker','compose','-p',project+'-'+kind,'-f',str(OUT/(kind+'.json')),*args],**kwargs)


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


ports={k:port() for k in ('mqtt','kuksa001','kuksa002','provider001','provider002','knownKuksa','knownProvider','transportMqtt')}


def wait(check, seconds=50):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        try:
            value=check()
            if value:return value
        except (OSError,ValueError,KeyError):
            pass
        time.sleep(.2)
    raise AssertionError('bounded condition timed out')


def scenario(which, action, name='LIDAR_OBSTRUCTION', known=False):
    request=Request('http://127.0.0.1:'+str(ports['knownProvider' if known else 'provider'+which])+'/api/v1/scenarios/actions',
        data=json.dumps({'vehicleId':'vehicle-'+which,'action':action,'scenario':name,
                         'actionId':project+'-'+action,'traceId':project}).encode(),
        headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=3) as response:return json.load(response)


def pressure(host_port):
    with VSSClient('127.0.0.1',host_port,ensure_startup_connection=False) as kuksa:
        point=kuksa.get_current_values([PATH],timeout=2)[PATH]
    return {'kpa':point.value,'sourceTimestamp':str(point.timestamp)}


def latest(vehicle):
    with lock:
        return next((e for e in reversed(events) if e['event']['vehicleId']==vehicle),None)


def fresh(vehicle, after, health=None):
    event=latest(vehicle)
    return event and dt.datetime.fromisoformat(event['event']['sourceTimestamp'].replace('Z','+00:00'))>after and (health is None or event['event']['health']==health)


def status(kind, service):
    container=compose(kind,'ps','--all','-q',service).strip()
    raw=json.loads(run(['docker','inspect',container,'--format','{{json .State}}']))
    restarts=int(run(['docker','inspect',container,'--format','{{.RestartCount}}']).strip())
    return {'running':raw['Running'],'exitCode':raw['ExitCode'],'startedAt':raw['StartedAt'],'restartCount':restarts}


def on_message(c, userdata, message):
    event=json.loads(message.payload)
    assert event['vehicleId'] in IDS and message.topic=='sdv/'+event['vehicleId']+'/health'
    with lock:events.append({'receiptUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'topic':message.topic,'qos':message.qos,'retain':message.retain,'event':event})


save('runtime-manifest.json',{'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'project':project,'ports':ports,
    'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'dirty':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
    'boundary':'Actual provider/KUKSA/apps/MQTT; separate deterministic-pressure fixture and in-process protobuf/mapper; no Ditto or gateway',
    'deterministicFixture':'known provider overrides random.uniform with range midpoint; healthy generator pressure stays 32 psi; actual production main/publish_loop and real RPCs unchanged',
    'clock':'source/observer UTC on same host kernel; no latency benchmark or clock-error bound'})
try:
    run(['docker','ps','-a','--format','{{.Names}} {{.Image}} {{.Status}}'])
    run(['docker','build','-t',image,'vehicle-simulator'])
    env=dict(os.environ,V1_MQTT_PORT=str(ports['mqtt']),V1_KUKSA_001_PORT=str(ports['kuksa001']),
        V1_KUKSA_002_PORT=str(ports['kuksa002']),V1_PROVIDER_001_PORT=str(ports['provider001']),
        V1_PROVIDER_002_PORT=str(ports['provider002']),PUBLISH_INTERVAL_SECONDS='0.5')
    edge=json.loads(run(['docker','compose','-f','vehicle-simulator/docker-compose.v1.yml','config','--format','json'],env=env))
    edge.pop('name',None)
    for service in edge['services'].values():
        service.pop('build',None)
        for item in service.get('ports',[]):item['host_ip']='127.0.0.1'
    for n in ('001','002'):
        edge['services']['provider-'+n]['image']=image
        edge['services']['app-'+n]['image']='qa-v1verify-app:20261114'
    save('edge.json',edge)
    active_projects.append('edge');compose('edge','up','-d','--no-build')
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=project+'-observer')
    client.on_message=on_message
    def connect():
        client.connect('127.0.0.1',ports['mqtt']);return True
    wait(connect);client.subscribe('sdv/+/health',qos=1);client.loop_start()
    wait(lambda:all(latest(v) and latest(v)['event']['health']=='HEALTHY' for v in IDS))
    results.append({'healthyBoth':True,'pressureBoth':{v:pressure(ports['kuksa'+v[-3:]]) for v in IDS}})
    scenario('002','INJECT_SCENARIO')
    wait(lambda:latest('vehicle-002')['event']['health']=='CRITICAL')
    for n in ('002','001'):
        target='vehicle-'+n;other='vehicle-'+('001' if n=='002' else '002')
        before=status('edge','provider-'+n)
        down=dt.datetime.now(dt.timezone.utc)
        compose('edge','kill','-s','SIGKILL','kuksa-'+n)
        try:
            time.sleep(12)
            assert fresh(other,down,'HEALTHY')
        finally:
            compose('edge','start','kuksa-'+n)
        returned=dt.datetime.now(dt.timezone.utc)
        expected='CRITICAL' if n=='002' else 'HEALTHY'
        wait(lambda:fresh(target,returned,expected),60)
        after=status('edge','provider-'+n)
        assert after['running'] and after['startedAt']==before['startedAt'] and after['restartCount']==before['restartCount']==0
        point=pressure(ports['kuksa'+n]);assert type(point['kpa']) is int and 207<=point['kpa']<=234
        results.append({'vehicle':target,'outageSecondsAtLeast':12,'returnedUtc':returned.isoformat(),
                        'freshEvent':latest(target),'otherAdvancedHealthy':True,'providerBefore':before,'providerAfter':after,'pressureAfter':point})
        if n=='002':
            scenario(n,'CLEAR_SCENARIO');wait(lambda:latest(target)['event']['health']=='HEALTHY')
    # Separate startup-with-absent-broker and controlled shutdown regressions.
    compose('edge','stop','kuksa-002');compose('edge','restart','provider-002')
    try:
        time.sleep(5);assert status('edge','provider-002')['running']
    finally:compose('edge','start','kuksa-002')
    returned=dt.datetime.now(dt.timezone.utc);wait(lambda:fresh('vehicle-002',returned,'HEALTHY'),60)
    compose('edge','stop','-t','30','provider-002')
    assert status('edge','provider-002')['exitCode']==0
    results.append({'initialBrokerAbsentRecovered':True,'controlledSigtermExit':0})
    client.loop_stop();client.disconnect();client=None
    # Clear before stopping owned edge, then run deterministic pressure separately.
    scenario('001','CLEAR_SCENARIO')
    compose('edge','logs','--no-color','--tail','250')
    compose('edge','down','--timeout','30');active_projects.remove('edge')
    broker={'image':'ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0',
        'command':['--insecure','--vss','/config/vss.json'],
        'volumes':[str(ROOT/'vehicle-simulator/config/vss-with-autonomous-sensors.json')+':/config/vss.json:ro'],
        'ports':[f'127.0.0.1:{ports["knownKuksa"]}:55555']}
    known={'services':{'broker':broker,'provider':{'image':image,'stop_grace_period':'30s','depends_on':['broker'],
        'command':['python','-u','-c',"import random,runpy,sys; random.uniform=lambda lo,hi:(lo+hi)/2; sys.path.insert(0,'/app/src'); runpy.run_path('/app/src/main.py',run_name='__main__')"],
        'ports':[f'127.0.0.1:{ports["knownProvider"]}:8090'],
        'environment':{'DATABROKER_HOST':'broker','DATABROKER_PORT':'55555','SIMULATED_VEHICLE_ID':'vehicle-001','PUBLISH_INTERVAL_SECONDS':'0.2'}},
        'mqtt':{'image':'eclipse-mosquitto:2','command':['mosquitto','-c','/mosquitto/config/mosquitto.conf'],
                'volumes':[str(ROOT/'vehicle-simulator/config/mosquitto.conf')+':/mosquitto/config/mosquitto.conf:ro'],
                'ports':[f'127.0.0.1:{ports["transportMqtt"]}:1883']}}}
    save('known.json',known);active_projects.append('known');compose('known','up','-d')
    def known_ready():
        try:return pressure(ports['knownKuksa'])['kpa']==221
        except Exception:return False
    wait(known_ready,45)
    point=pressure(ports['knownKuksa']);assert point['kpa']==round(32*6.894757293168)==221
    results.append({'knownGeneratorPsi':32,'actualKuksa':point,'fixture':'midpoint random changes; actual production publication/recovery code'})
    test_env=dict(os.environ,DATABROKER_HOST='127.0.0.1',DATABROKER_PORT=str(ports['knownKuksa']))
    run([sys.executable,'-m','pytest','-q','-ra','-m','integration','vehicle-simulator/tests/test_kuksa_publication.py'],env=test_env,timeout=90)
    transport_env=dict(os.environ,V1_MQTT_TEST_HOST='127.0.0.1',V1_MQTT_TEST_PORT=str(ports['transportMqtt']))
    run([sys.executable,'-m','pytest','-q','-ra','-m','integration','velocitas-app/app/tests/test_v1_publisher_integration.py'],env=transport_env,timeout=90)
    scenario('001','INJECT_SCENARIO','COOLING_SYSTEM_FAILURE',True)
    def low():
        p=pressure(ports['knownKuksa']);return p if p['kpa'] is not None and kpa_to_psi(p['kpa'])<=24 else None
    p=wait(low,30);psi=kpa_to_psi(p['kpa'])
    payload=publish_vehicle_status('vehicle-001',60,80,90,200,psi)
    decoded=receive_vehicle_status(payload).signals.tire_pressure_psi.front_left
    assert abs(decoded-psi)<1e-5
    fixture={'features':{'signals':{'properties':{'tirePressurePsi':{'frontLeft':decoded}}},
                         'health':{'properties':{'activeFaults':['TIRE_PRESSURE_LOW_FRONT_LEFT']}}}}
    mapped=map_fault_to_opensovd('TIRE_PRESSURE_LOW_FRONT_LEFT',fixture)
    assert mapped['unit']=='psi' and mapped['severity']=='CRITICAL' and mapped['threshold']==24
    results.append({'actualLowKuksa':p,'legacyPsi':psi,'protobufPsi':decoded,'mapped':mapped,
                    'diagnosticContext':'explicit fixture; conversion/protobuf/mapper in-process, not a live legacy HTTP loop/gateway'})
    scenario('001','CLEAR_SCENARIO','COOLING_SYSTEM_FAILURE',True)
    wait(lambda: pressure(ports['knownKuksa'])['kpa']==207);results.append({'clearRestoredKnown207kpa':True,'generatorPsiAfterClear':30})
    run(['docker','image','inspect',image,'qa-v1verify-app:20261114','ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0','eclipse-mosquitto:2','--format','{{.Id}} {{json .RepoDigests}}'])
    save('runtime-results.json',{'status':'PASS','checks':results})
finally:
    if client:client.loop_stop();client.disconnect()
    for kind in reversed(active_projects):
        if kind=='edge':
            compose(kind,'start','kuksa-001','kuksa-002','mqtt',check=False)
            for n in ('001','002'):
                for name in ('LIDAR_OBSTRUCTION','COOLING_SYSTEM_FAILURE'):
                    try:scenario(n,'CLEAR_SCENARIO',name)
                    except Exception:pass
        else:
            try:scenario('001','CLEAR_SCENARIO','COOLING_SYSTEM_FAILURE',True)
            except Exception:pass
        compose(kind,'logs','--no-color','--tail','300',check=False)
        compose(kind,'down','--timeout','30',check=False)
    save('runtime-checks-retained.json',results)
    (OUT/'runtime-mqtt.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    run(['docker','ps','-a','--format','{{.Names}} {{.Status}}'])
print(json.dumps(results,indent=2))
