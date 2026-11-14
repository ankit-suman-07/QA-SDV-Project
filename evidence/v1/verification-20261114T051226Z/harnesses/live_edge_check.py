import datetime,json,logging,os,signal,subprocess,sys,threading,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from copy import deepcopy
from ditto.mqtt_ingress import Ingress
from ditto.mqtt_subscriber import Subscriber,MqttConfig
import paho.mqtt.client as mqtt
ROOT=Path.cwd();OUT=ROOT/'evidence/v1/verification-20261114T051226Z/live-edge';OUT.mkdir(exist_ok=False)
logging.basicConfig(filename=str(OUT/'ingress-mock-writer.log'),level=logging.INFO)
started=time.monotonic();captures=[];checks=[];measurements=[];api=[];lock=threading.RLock();active=False
class RecordingWriter:
    def __init__(self):self.states={};self.writes=[];self.fail=False;self.failures=0
    def load_watermark(self,v):
        with lock:
            p=self.states.get(v);return (p['lastEventId'],p['sourceTimestamp']) if p else None
    def persist(self,v,p):
        with lock:
            if v=='vehicle-002' and self.fail:self.failures+=1;raise OSError('test-owned simulated persistence outage')
            self.states[v]=deepcopy(p);self.writes.append({'vehicleId':v,'properties':deepcopy(p),'receiptMonotonicSeconds':time.monotonic()-started})
writer=RecordingWriter();subscriber=None;thread=None;client=None;java=None
compose=['docker','compose','-p','qa-v1verify20261114','-f','vehicle-simulator/docker-compose.v1.yml','-f','evidence/v1/verification-20261114T051226Z/edge-override.yaml']
java_cmd=['/tmp/qa-v1-tooling/amazon-corretto-21.0.13.0.11-linux-x64/bin/java','-jar','backend/target/backend-0.0.1-SNAPSHOT.jar','--server.address=127.0.0.1','--server.port=28082','--sdv.simulator.mode=http','--sdv.simulator.providers[vehicle-001]=http://127.0.0.1:28091','--sdv.simulator.providers[vehicle-002]=http://127.0.0.1:28092','--sdv.v1.ditto.mode=live','--sdv.v1.ditto.base-url=http://127.0.0.1:8080','--sdv.v1.fleet.enabled=false','--sdv.vehicles.ids=vehicle-001,vehicle-002']
(OUT/'configuration.json').write_text(json.dumps({'javaCommand':java_cmd,'compose':compose,'backendBoundary':'LIVE A3 to actual providers; Ditto absent at default port8080; A2/fleet must show unavailable; materializer disabled because real credentials unavailable','ingressBoundary':'Actual Subscriber+Ingress with IN-MEMORY RecordingWriter. NOT Eclipse Ditto; simulated writer failures/restart watermarks are MOCK-VERIFIED','providerIntervalSeconds':5,'appPollSeconds':2},indent=2)+'\n')
def request(path,body=None,base='http://127.0.0.1:28082'):
    req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=6) as r:status=r.status;value=json.load(r)
    except HTTPError as e:status=e.code;value=json.load(e)
    api.append({'path':path,'base':base,'request':body,'status':status,'response':value,'monotonicSeconds':time.monotonic()-started})
    return status,value
def wait(pred,label,timeout=45):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if pred():checks.append(label);return
        time.sleep(.05)
    raise AssertionError('TIMEOUT '+label)
def begin_subscriber():
    global subscriber,thread
    subscriber=Subscriber(Ingress(writer),MqttConfig(host='127.0.0.1',port=28883,client_id='qa-v1verify-individual-ingress',retry_seconds=.2))
    original=subscriber.client.on_message
    def capture(c,u,m):
        record={'topic':m.topic,'qos':m.qos,'retain':m.retain,'payload':m.payload.decode('utf-8',errors='replace'),'receivedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receiptMonotonicSeconds':time.monotonic()-started}
        try:record['event']=json.loads(m.payload)
        except (ValueError,UnicodeError):pass
        with lock:captures.append(record)
        original(c,u,m)
    subscriber.client.on_message=capture
    thread=threading.Thread(target=subscriber.run,daemon=True);thread.start();wait(lambda:subscriber._connected,'ingress connected',10);time.sleep(.4)
def health(v):return writer.states.get(v,{}).get('health')
def act(operation):return request('/api/v1/diagnostics/actions',{'vehicleId':'vehicle-002','action':operation,'scenario':'LIDAR_OBSTRUCTION'})
def observed_after(t,health_value):
    with lock:return next((r for r in captures if r.get('receiptMonotonicSeconds',0)>=t and r.get('event',{}).get('vehicleId')=='vehicle-002' and r['event']['health']==health_value),None)
def compose_action(*args):subprocess.run(compose+list(args),check=True,stdout=subprocess.DEVNULL)
try:
    stream=(OUT/'spring-live-routing.log').open('w');java=subprocess.Popen(java_cmd,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    def ready():
        try:return request('/api/v1/vehicles')[0]==200
        except OSError:return False
    wait(ready,'actual Java backend ready',35)
    assert request('/api/v1/vehicles')[1]=={'vehicleIds':['vehicle-001','vehicle-002']}
    for v in ('vehicle-001','vehicle-002'):
        response=request('/api/v1/vehicles/'+v+'/state')[1];assert response['availability']=='UNAVAILABLE' and response['healthStatus'] is None and response['sourceTimestamp'] is None
    assert request('/api/v1/vehicles/vehicle-003/state')[0]==404
    assert request('/api/v1/fleet')[1]['unavailableVehicles']==2
    begin_subscriber();wait(lambda:health('vehicle-001')==health('vehicle-002')=='HEALTHY','two actual edges publish healthy through real MQTT into mock writer',25)
    for operation,target in [('INJECT_SCENARIO','CRITICAL'),('CLEAR_SCENARIO','HEALTHY')]:
        t=time.monotonic()-started
        if operation=='INJECT_SCENARIO':active=True
        status,ack=act(operation);assert status==202 and ack['status']=='ACCEPTED' and ack['dispatchStatus']=='DISPATCHED'
        ack_time=time.monotonic()-started
        assert request('/api/v1/diagnostics/actions/'+ack['actionId'])[1]==ack
        context=request('/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION',base='http://127.0.0.1:28092')[1]
        assert context['actionId']==ack['actionId'] and context['traceId']==ack['traceId']
        if operation=='CLEAR_SCENARIO':active=False
        wait(lambda:observed_after(t,target) is not None,'observed '+target+' after '+operation,40)
        record=observed_after(t,target)
        measurements.append({'operation':operation,'status':'PASS','boundary':'command submission to observed MQTT status; includes scenario progression; not pure transport latency','commandMonotonicSeconds':t,'acknowledgementMonotonicSeconds':ack_time,'completionMonotonicSeconds':record['receiptMonotonicSeconds'],'completionSeconds':record['receiptMonotonicSeconds']-t,'acknowledgementSeconds':ack_time-t,'actionId':ack['actionId'],'traceId':ack['traceId'],'observedEventId':record['event']['eventId'],'sourceTimestamp':record['event']['sourceTimestamp'],'causalContextInMqtt':False})
        wait(lambda:writer.states['vehicle-002']['lastEventId']==record['event']['eventId'],'matching mock-writer event for '+operation,8)
    assert all(r['event']['health']=='HEALTHY' for r in captures if r.get('event',{}).get('vehicleId')=='vehicle-001')
    wait(lambda:writer.states['vehicle-002']['lidar']['distanceMeters']==35,'recovery observed at35m',20)
    request('/api/v1/scenarios/actions',{'vehicleId':'vehicle-001','action':'INJECT_SCENARIO','scenario':'LIDAR_OBSTRUCTION','actionId':'owned-wrong','traceId':'owned-wrong'},base='http://127.0.0.1:28092')
    assert api[-1]['status']==409
    compose_action('stop','provider-002');time.sleep(2.5);before=deepcopy(writer.states['vehicle-002']);one=writer.states['vehicle-001']['lastEventId'];time.sleep(6)
    assert writer.states['vehicle-002']==before and writer.states['vehicle-001']['lastEventId']!=one;checks.append('source silence preserves original002 source/event while001 continues; real A2 aging blocked by absent Ditto')
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2);client.connect('127.0.0.1',28883);client.loop_start()
    event={'schemaVersion':before['schemaVersion'],'eventId':before['lastEventId'],'vehicleId':'vehicle-002','sourceTimestamp':before['sourceTimestamp'],'health':before['health'],'faults':before['faults'],'lidar':before['lidar']}
    invalid=[('sdv/vehicle-002/health',b'{'),('sdv/vehicle-999/health',json.dumps(dict(event,vehicleId='vehicle-999')).encode()),('sdv/vehicle-001/health',json.dumps(event).encode()),('sdv/vehicle-002/health',json.dumps(event).encode()),('sdv/vehicle-002/health',json.dumps(dict(event,eventId='equal-owned')).encode()),('sdv/vehicle-002/health',json.dumps(dict(event,eventId='late-owned',sourceTimestamp='2026-01-01T00:00:00Z')).encode())]
    for topic,payload in invalid:client.publish(topic,payload,qos=1,retain=False).wait_for_publish(3)
    time.sleep(.8);assert writer.states['vehicle-002']==before;checks.append('six isolated malformed/unknown/mismatched/duplicate/equal/late messages leave mock twin unchanged')
    subscriber.stop();thread.join(5);begin_subscriber()
    client.publish('sdv/vehicle-002/health',json.dumps(event),qos=1).wait_for_publish(3);time.sleep(.5);assert writer.states['vehicle-002']==before;checks.append('subscriber restart reloads mock-writer watermark and rejects duplicate')
    writer.fail=True;compose_action('start','provider-002');wait(lambda:writer.failures>0,'simulated002 write outage encountered',15);assert writer.states['vehicle-002']==before
    writer.fail=False;wait(lambda:writer.states['vehicle-002']['lastEventId']!=before['lastEventId'],'mock-writer recovery progresses',12)
    # Ensure all actual app events observed before synthetic negatives use QoS1/non-retain.
    assert all(r['qos']==1 and not r['retain'] for r in captures)
    checks.append('real publisher deliveries QoS1 retain=false; IDs/source preserved into mock writer')
    print('PASS live A3 -> actual providers/KUKSA/apps/MQTT; real ingress + MOCK twin writer. Full Ditto/API/fleet acceptance BLOCKED.')
except BaseException as error:
    measurements.append({'status':'FAILED','errorType':type(error).__name__,'message':str(error),'atMonotonicSeconds':time.monotonic()-started});raise
finally:
    writer.fail=False
    if active:
        try:act('CLEAR_SCENARIO')
        except OSError:
            try:request('/api/v1/scenarios/actions',{'vehicleId':'vehicle-002','action':'CLEAR_SCENARIO','scenario':'LIDAR_OBSTRUCTION','actionId':'owned-cleanup','traceId':'owned-cleanup'},base='http://127.0.0.1:28092')
            except OSError:pass
    if client:client.disconnect();client.loop_stop()
    if subscriber:subscriber.stop()
    if thread:thread.join(5)
    if java:
        java.terminate()
        try:java.wait(timeout=12)
        except subprocess.TimeoutExpired:java.kill();java.wait()
        stream.close()
    (OUT/'mqtt.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in captures))
    (OUT/'api-responses.json').write_text(json.dumps(api,indent=2)+'\n')
    (OUT/'mock-individual-states.json').write_text(json.dumps(writer.states,indent=2)+'\n')
    (OUT/'mock-writes.json').write_text(json.dumps(writer.writes,indent=2)+'\n')
    (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
    (OUT/'checks.json').write_text(json.dumps({'checks':checks,'recordedMessages':len(captures),'simulatedWriteFailures':writer.failures,'realDitto':'BLOCKED','realTwinApiFleetDashboardAcceptance':'BLOCKED'},indent=2)+'\n')
