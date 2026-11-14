import datetime,json,subprocess,threading,time
from pathlib import Path
import paho.mqtt.client as mqtt
OUT=Path('evidence/v1/verification-20261114T051226Z/edge-recovery');OUT.mkdir(exist_ok=False)
records=[];results=[];lock=threading.RLock();start=time.monotonic()
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
def connected(c,u,f,r,p):c.subscribe('sdv/+/health',qos=1)
def message(c,u,m):
    with lock:records.append({'receivedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonicSeconds':time.monotonic()-start,'topic':m.topic,'qos':m.qos,'retain':m.retain,'event':json.loads(m.payload)})
client.on_connect=connected;client.on_message=message
compose=['docker','compose','-p','qa-v1verify20261114','-f','vehicle-simulator/docker-compose.v1.yml','-f','evidence/v1/verification-20261114T051226Z/edge-override.yaml']
def control(*args):subprocess.run(compose+list(args),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def count(v):return sum(r['event']['vehicleId']==v for r in records)
def wait(pred,timeout):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if pred():return True
        time.sleep(.1)
    return False
def state(name):return json.loads(subprocess.check_output(['docker','inspect',name,'--format','{{json .State}}'],text=True))
try:
    client.connect('127.0.0.1',28883);client.loop_start();assert wait(lambda:count('vehicle-001') and count('vehicle-002'),12)
    before={v:count(v) for v in ('vehicle-001','vehicle-002')}
    control('stop','mqtt');time.sleep(12);control('start','mqtt')
    ok=wait(lambda:all(count(v)>before[v] for v in before),25)
    results.append({'check':'actual app MQTT outage/reconnect','result':'PASS' if ok else 'FAILED','outageSeconds':12});assert ok
    old=count('vehicle-002');restart=time.monotonic()-start;control('restart','app-002');ok=wait(lambda:count('vehicle-002')>old,22)
    received=next((r['monotonicSeconds'] for r in records if r['monotonicSeconds']>restart and r['event']['vehicleId']=='vehicle-002'),None)
    results.append({'check':'actual app002 restart then fresh publication','result':'PASS' if ok else 'FAILED','commandToFirstObservedEventSeconds':None if received is None else received-restart,'includesDockerStopGraceAndStartup':True,'availabilityAgainstRealDitto':'BLOCKED'});assert ok
    old=count('vehicle-002');control('stop','kuksa-002');time.sleep(12)
    provider_during=state('qa-v1verify20261114-provider-002-1');control('start','kuksa-002')
    ok=wait(lambda:count('vehicle-002')>old,20)
    provider_after=state('qa-v1verify20261114-provider-002-1')
    item={'check':'automatic edge002 recovery after KUKSA outage','result':'PASS' if ok else 'FAILED','outageSeconds':12,'providerDuringOutage':{k:provider_during.get(k) for k in ('Status','Running','ExitCode','Error')},'providerAfterBrokerRestart':{k:provider_after.get(k) for k in ('Status','Running','ExitCode','Error')}}
    if not ok:
        control('start','provider-002');item['manualTestOwnedProviderRestartRestoredPublication']=wait(lambda:count('vehicle-002')>old,20)
    results.append(item)
    print(json.dumps(results,indent=2))
finally:
    # Restore only test-owned broker/provider resources before later teardown.
    control('start','mqtt','kuksa-002','provider-002')
    client.disconnect();client.loop_stop()
    (OUT/'mqtt.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
if any(r['result']=='FAILED' for r in results):raise SystemExit(1)
