"""Owned real KUKSA/provider/app/MQTT outage checks; no Ditto or credentials."""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import threading
import time
import urllib.request
import paho.mqtt.client as mqtt

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
label = 'baseline' if args.baseline else 'fixed'
project = 'qa-recovery-' + label
compose = ['docker', 'compose', '-p', project, '-f', str(ROOT/'vehicle-simulator/docker-compose.v1.yml'), '-f', str(OUT/'live-override.yaml')]
commands = []
messages = []
lock = threading.Lock()
results = []


def run(*command):
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    commands.append({'command': list(command), 'exitCode': result.returncode, 'output': result.stdout})
    if result.returncode:
        raise RuntimeError(f'command failed: {command[:3]}')
    return result.stdout


def wait_for(predicate, timeout=45):
    end = time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate():
            return
        time.sleep(.2)
    raise TimeoutError('condition not observed')


def last(vehicle):
    with lock:
        return next((m for m in reversed(messages) if m['payload']['vehicleId']==vehicle), None)


def fresh_since(vehicle, instant):
    event = last(vehicle)
    return event and dt.datetime.fromisoformat(event['payload']['sourceTimestamp'].replace('Z','+00:00')) > instant


def on_message(client, userdata, message):
    with lock:
        messages.append({'receivedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'topic': message.topic,
                         'qos': message.qos, 'retain': message.retain, 'payload': json.loads(message.payload)})


provider_image = 'qa-v1verify-provider:20261114' if args.baseline else 'qa-provider-recovery:fixed'
(OUT/'live-override.yaml').write_text(f'''services:
  mqtt:
    ports: !override ["127.0.0.1:29883:1883"]
  kuksa-001:
    ports: !override ["127.0.0.1:57556:55555"]
  kuksa-002:
    ports: !override ["127.0.0.1:57557:55555"]
  provider-001:
    image: {provider_image}
    ports: !override ["127.0.0.1:29091:8090"]
  provider-002:
    image: {provider_image}
    ports: !override ["127.0.0.1:29092:8090"]
  app-001:
    image: qa-v1verify-app:20261114
  app-002:
    image: qa-v1verify-app:20261114
''')
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='qa-recovery-check')
client.on_message = on_message
try:
    run(*compose, 'up', '-d', '--no-build')
    client.connect('127.0.0.1', 29883)
    client.subscribe('sdv/+/health', qos=1)
    client.loop_start()
    wait_for(lambda: last('vehicle-001') and last('vehicle-002'))
    for number in ('002', '001') if not args.baseline else ('002',):
        vehicle = 'vehicle-'+number
        other = 'vehicle-'+('001' if number=='002' else '002')
        before = last(vehicle)
        run(*compose, 'kill', '-s', 'SIGKILL', 'kuksa-'+number)
        time.sleep(12)
        other_during_outage = last(other)
        assert other_during_outage['payload']['health']=='HEALTHY'
        assert other_during_outage['receivedAt'] > before['receivedAt']
        restored = dt.datetime.now(dt.timezone.utc)
        run(*compose, 'start', 'kuksa-'+number)
        recovered = True
        try:
            wait_for(lambda: fresh_since(vehicle, restored), timeout=35)
        except TimeoutError:
            recovered = False
        status = json.loads(run('docker', 'inspect', f'{project}-provider-{number}-1'))[0]
        results.append({'vehicle': vehicle, 'automaticFreshRecovery': recovered,
                        'providerRunning': status['State']['Running'], 'providerExitCode': status['State']['ExitCode'],
                        'providerRestartCount': status['RestartCount'], 'otherVehicleAdvancedHealthy': True,
                        'restoredAt': restored.isoformat(), 'freshEvent': last(vehicle) if recovered else None})
        if args.baseline:
            assert not recovered and not status['State']['Running']
        else:
            assert recovered and status['State']['Running'] and status['RestartCount']==0
    if not args.baseline:
        # Initial dependency absence: a new provider process starts while broker is down.
        run(*compose, 'stop', 'kuksa-002')
        run(*compose, 'restart', 'provider-002')
        time.sleep(8)
        status = json.loads(run('docker', 'inspect', project+'-provider-002-1'))[0]
        assert status['State']['Running']
        restored = dt.datetime.now(dt.timezone.utc)
        run(*compose, 'start', 'kuksa-002')
        wait_for(lambda: fresh_since('vehicle-002', restored))
        results.append({'initialDependencyUnavailableThenFreshPublication': True})
        # Process signal must exit normally and release the control listener.
        run(*compose, 'stop', '-t', '30', 'provider-002')
        status = json.loads(run('docker', 'inspect', project+'-provider-002-1'))[0]
        assert status['State']['ExitCode']==0
        results.append({'controlledSigtermExitCode': 0})
finally:
    client.loop_stop()
    client.disconnect()
    try:
        (OUT/(label+'-services.txt')).write_text(run(*compose, 'logs', '--no-color'))
    finally:
        run(*compose, 'down')
        (OUT/(label+'-commands.json')).write_text(json.dumps(commands, indent=2)+'\n')
        (OUT/(label+'-mqtt.jsonl')).write_text(''.join(json.dumps(m)+'\n' for m in messages))
        (OUT/(label+'-result.json')).write_text(json.dumps({'baselineReproduction': args.baseline, 'results': results,
            'boundary': 'Real providers/KUKSA/apps/MQTT; no Ditto/API/fleet acceptance'}, indent=2)+'\n')
print(json.dumps(results, indent=2))
