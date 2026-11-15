"""Bounded actual-image lifecycle checks on a new broker and isolated Ditto stack."""
import datetime as dt,json,os,re,subprocess,time,sys
from pathlib import Path
import requests
import paho.mqtt.client as mqtt
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root));os.chdir(root)
from ditto.v1_writer import DittoWriter,DittoConfig
from ditto.mqtt_ingress import Ingress
out=Path(__file__).resolve().parent;r=Path.home()/'.local/share/qa-sdv-v1/runtime'
auth=re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)',(r/'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text())[0]
base='http://127.0.0.1:18090';ingress=Ingress(DittoWriter(DittoConfig(base,*auth)))
records=[];events=[];failures=[];broker='qa-v1-shutdown-mqtt-'+str(int(time.time()));active=None;paused=False

def run(args,required=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=35)
 if required:assert p.returncode==0,'command failed: '+args[0]
 return p

def on_message(client,userdata,msg):
 try:
  event=json.loads(msg.payload);ingress.process(msg.topic,msg.payload)
  twin=requests.get(base+'/api/2/things/sdv:vehicle-002',auth=auth,timeout=3).json()
  props=dict(event);props['lastEventId']=props.pop('eventId')
  if twin['features']['v1']['properties']==props:events.append(dict(observedAt=dt.datetime.now(dt.timezone.utc).isoformat(),event=event,twin=twin,qos=msg.qos,retain=msg.retain))
 except Exception as e:failures.append(type(e).__name__)

def wait(test,timeout=25):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if test():return
  time.sleep(.1)
 raise AssertionError('bounded observation deadline')

client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='qa-v1-shutdown-observer');client.on_message=on_message
client.on_connect=lambda c,u,f,rc,props:c.subscribe('sdv/vehicle-002/health',qos=1)
try:
 run(['docker','run','-d','--name',broker,'-p','127.0.0.1:18893:1883','-v',str(root/'vehicle-simulator/config/mosquitto.conf')+':/mosquitto/config/mosquitto.conf:ro','eclipse-mosquitto@sha256:75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98','mosquitto','-c','/mosquitto/config/mosquitto.conf'])
 client.connect('127.0.0.1',18893);client.subscribe('sdv/vehicle-002/health',qos=1);client.loop_start()
 for index,mode in enumerate(['polling-1','polling-2','startup-broker-absent','kuksa-absent','publication-broker-paused']):
  active='qa-v1-shutdown-app-'+str(int(time.time()))+'-'+str(index)
  args=['docker','run','-d','--name',active,'--network','host']
  env=dict(SDV_MIDDLEWARE_TYPE='native',SDV_MQTT_ADDRESS='mqtt://127.0.0.1:'+('18894' if mode=='startup-broker-absent' else '18893'),SDV_VEHICLEDATABROKER_ADDRESS='grpc://127.0.0.1:55557',DATABROKER_HOST='127.0.0.1',DATABROKER_PORT='55559' if mode=='kuksa-absent' else '55557',SIMULATED_VEHICLE_ID='vehicle-002',AUTONOMOUS_HEALTH_POLL_INTERVAL_SECONDS='0.5')
  for k,v in env.items():args+=['-e',k+'='+v]
  args+=[json.loads((out/'image.json').read_text())['dockerRef']];before=len(events);run(args)
  state=json.loads(run(['docker','inspect',active]).stdout)[0]
  if mode.startswith('polling') or mode.startswith('publication'):
   wait(lambda:len(events)>before and dt.datetime.fromisoformat(events[-1]['event']['sourceTimestamp'].replace('Z','+00:00'))>dt.datetime.fromisoformat(state['State']['StartedAt'].replace('Z','+00:00')))
   assert dt.datetime.fromisoformat(events[-1]['event']['sourceTimestamp'].replace('Z','+00:00'))>dt.datetime.fromisoformat(state['State']['StartedAt'].replace('Z','+00:00'))
  else:time.sleep(.6)
  if mode.startswith('publication'):
   run(['docker','pause',broker]);paused=True
   wait(lambda:'publish not acknowledged' in run(['docker','logs',active]).stderr,timeout=15)
  request=dt.datetime.now(dt.timezone.utc).isoformat();start=time.monotonic();stop=run(['docker','stop','--timeout','12',active]);elapsed=time.monotonic()-start
  stopped=json.loads(run(['docker','inspect',active]).stdout)[0]
  log=run(['docker','logs',active]);(out/(mode+'.txt')).write_text(log.stdout+log.stderr)
  record=dict(mode=mode,stopExit=stop.returncode,applicationExit=stopped['State']['ExitCode'],running=stopped['State']['Running'],pid=stopped['State']['Pid'],startedAt=state['State']['StartedAt'],stopRequest=request,stopDurationSeconds=elapsed,oom=stopped['State']['OOMKilled'],matchedEvents=events[before:])
  records.append(record)
  assert record['applicationExit']==0 and not record['running'] and record['pid']==0
  assert 'Application shutdown completed' in log.stderr and 'Event loop stopped before' not in log.stderr
  if paused:run(['docker','unpause',broker]);paused=False
  active=None
finally:
 if paused:run(['docker','unpause',broker],False)
 if active:run(['docker','stop','--timeout','12',active],False)
 client.disconnect();client.loop_stop()
 run(['docker','stop',broker],False)
 (out/'docker-live.json').write_text(json.dumps(dict(result='PASS' if len(records)==5 and all(x['applicationExit']==0 for x in records) else 'FAIL',records=records,observerFailures=failures,resources='Only new broker/app containers stopped; retained for inspection. Shared edge/ingress/twins unaffected. Isolated Ditto18090 updated by this sole test observer.'),indent=2)+'\n')
 print('Saved',out/'docker-live.json')
