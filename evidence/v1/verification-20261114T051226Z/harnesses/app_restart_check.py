import datetime,json,subprocess,threading,time
from pathlib import Path
import paho.mqtt.client as mqtt
OUT=Path('evidence/v1/verification-20261114T051226Z/app-restart');OUT.mkdir(exist_ok=False)
records=[];ready=threading.Event();client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
def connected(c,u,f,r,p):c.subscribe('sdv/+/health',qos=1)
def msg(c,u,m):
    row={'receivedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':time.monotonic(),'topic':m.topic,'event':json.loads(m.payload)};records.append(row);ready.set()
client.on_connect=connected;client.on_message=msg
try:
    client.connect('127.0.0.1',28883);client.loop_start();assert ready.wait(12)
    command=time.monotonic();subprocess.run(['docker','restart','qa-v1verify20261114-app-002-1'],check=True,stdout=subprocess.DEVNULL)
    started_text=subprocess.check_output(['docker','inspect','qa-v1verify20261114-app-002-1','--format','{{.State.StartedAt}}'],text=True).strip()
    started=datetime.datetime.fromisoformat(started_text.replace('Z','+00:00'))
    deadline=time.monotonic()+22;match=None
    while time.monotonic()<deadline:
        match=next((r for r in records if r['monotonic']>=command and r['event']['vehicleId']=='vehicle-002' and datetime.datetime.fromisoformat(r['event']['sourceTimestamp'].replace('Z','+00:00'))>started),None)
        if match:break
        time.sleep(.1)
    result={'check':'post-start new source observation; excludes in-flight pre-restart messages','result':'PASS' if match else 'FAILED','containerStartedAt':started_text,'commandToFreshMqttSeconds':None if not match else match['monotonic']-command,'firstFreshEvent':None if not match else match['event'],'boundary':'Docker restart command -> MQTT receipt whose sourceTimestamp is after new container StartedAt; includes stop/start/provider interval/app poll; not a strict SLA or twin acceptance'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    assert match
finally:
    client.disconnect();client.loop_stop();(OUT/'mqtt.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
