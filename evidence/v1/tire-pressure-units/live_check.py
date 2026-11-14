"""Actual provider/KUKSA pressure readback; in-process legacy conversions only."""
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
from kuksa_client.grpc import VSSClient

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ditto.pressure_units import kpa_to_psi
from opensovd.fault_mapper import map_fault_to_opensovd
from uprotocol.transport import publish_vehicle_status, receive_vehicle_status

OUT = pathlib.Path(__file__).resolve().parent
PATH = 'Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure'
compose = ['docker', 'compose', '-p', 'qa-pressure-units', '-f', str(OUT/'live-compose.yaml')]
commands = []
observations = []


def run(*cmd):
    p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    commands.append({'command':list(cmd), 'exitCode':p.returncode, 'output':p.stdout})
    if p.returncode:
        raise RuntimeError('owned command failed')
    return p.stdout


def scenario(action):
    data = json.dumps({'vehicleId':'vehicle-001', 'action':action, 'scenario':'COOLING_SYSTEM_FAILURE',
                       'actionId':'pressure-verification', 'traceId':'pressure-verification'}).encode()
    request = urllib.request.Request('http://127.0.0.1:29093/api/v1/scenarios/actions',data=data,
                                      headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)


(OUT/'live-compose.yaml').write_text('''services:
  broker:
    image: ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0
    command: ["--insecure", "--vss", "/config/vss.json"]
    volumes:
      - ../../../vehicle-simulator/config/vss-with-autonomous-sensors.json:/config/vss.json:ro
    ports: ["127.0.0.1:57558:55555"]
  provider:
    image: qa-pressure-units:fixed
    depends_on: [broker]
    ports: ["127.0.0.1:29093:8090"]
    environment:
      DATABROKER_HOST: broker
      DATABROKER_PORT: "55555"
      SIMULATED_VEHICLE_ID: vehicle-001
      PUBLISH_INTERVAL_SECONDS: "0.2"
''')
try:
    run('docker','build','-t','qa-pressure-units:fixed','vehicle-simulator')
    run(*compose,'up','-d')
    end = time.monotonic()+30
    while True:
        try:
            with VSSClient('127.0.0.1',57558,ensure_startup_connection=False) as client:
                point = client.get_current_values([PATH],timeout=2)[PATH]
                if point.value is not None:
                    break
        except Exception:
            if time.monotonic()>end:
                raise
        time.sleep(.2)
    assert 207 <= point.value <= 234
    observations.append({'phase':'healthy','kpa':point.value,'psi':kpa_to_psi(point.value),'sourceTimestamp':str(point.timestamp)})
    # Real signals suite runs while source is healthy; integration designation explicit.
    run('/tmp/qa-review-venv/bin/python','-B','-m','pytest','-q','-p','no:cacheprovider','-m','integration',
        'vehicle-simulator/tests/test_kuksa_publication.py')
    acknowledgement = scenario('INJECT_SCENARIO')
    end = time.monotonic()+30
    while True:
        with VSSClient('127.0.0.1',57558,ensure_startup_connection=False) as client:
            point = client.get_current_values([PATH],timeout=2)[PATH]
        psi = kpa_to_psi(point.value)
        if psi <= 24:
            break
        assert time.monotonic()<end
        time.sleep(.2)
    # Exactly the legacy bridge's conversion + protobuf serialization boundary.
    payload = publish_vehicle_status('vehicle-001',60,80,90,200,psi)
    decoded = receive_vehicle_status(payload).signals.tire_pressure_psi.front_left
    assert abs(decoded-psi)<1e-5  # float32 protobuf, no second conversion
    thing = {'features':{'signals':{'properties':{'tirePressurePsi':{'frontLeft':decoded}}},
                         'health':{'properties':{'activeFaults':['TIRE_PRESSURE_LOW_FRONT_LEFT']}}}}
    mapped = map_fault_to_opensovd('TIRE_PRESSURE_LOW_FRONT_LEFT',thing)
    assert mapped['unit']=='psi' and mapped['severity']=='CRITICAL' and mapped['status']=='ACTIVE'
    observations.append({'phase':'fault','kpa':point.value,'psi':psi,'protobufPsi':decoded,
                         'sourceTimestamp':str(point.timestamp),'mapped':mapped,'mapperFaultCode':'explicit controlled fixture, not a live bridge-generated fault'})
    scenario('CLEAR_SCENARIO')
    time.sleep(.6)
    with VSSClient('127.0.0.1',57558,ensure_startup_connection=False) as client:
        point = client.get_current_values([PATH],timeout=2)[PATH]
    assert 207 <= point.value <= 234
    observations.append({'phase':'clear','kpa':point.value,'psi':kpa_to_psi(point.value)})
finally:
    try:
        scenario('CLEAR_SCENARIO')
    except Exception:
        pass
    try:
        (OUT/'live-services.txt').write_text(run(*compose,'logs','--no-color'))
        (OUT/'image-identities.txt').write_text(run('docker','image','inspect','qa-pressure-units:fixed',
                    'ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0','--format','{{.Id}} {{json .RepoDigests}}'))
    finally:
        run(*compose,'down')
        (OUT/'live-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        (OUT/'live-result.json').write_text(json.dumps({'observations':observations,
             'boundary':'Actual provider and KUKSA; conversion/protobuf/mapper in-process. No real legacy bridge loop, Ditto or OpenSOVD gateway.'},indent=2)+'\n')
print(json.dumps(observations,indent=2))
