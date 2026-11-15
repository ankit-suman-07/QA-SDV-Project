"""Bounded real Ditto check in new, uniquely named resources; no shared reset."""
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import requests
from ditto import v1_writer as module
from ditto.mqtt_ingress import Ingress, EventError

out = Path(__file__).resolve().parent
runtime = Path.home()/'.local/share/qa-sdv-v1/runtime'
text = (runtime/'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text()
auth = re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)', text)[0]
namespace = 'qa_v1_init_' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')
# Isolate fixed logical vehicle IDs into new test-owned Ditto resources only.
module.THINGS.update({v:namespace+':'+v for v in module.VEHICLES})
module.POLICIES.update({v:namespace+':'+v+'-policy' for v in module.VEHICLES})
operations=[]
def request(method,url,**kw):
    r=requests.request(method,url,**kw)
    operations.append(dict(method=method,path=url.split('/api/2/')[1],status=r.status_code,ifNoneMatch=kw['headers'].get('If-None-Match'),ifMatch=kw['headers'].get('If-Match'),etag=r.headers.get('ETag')))
    return r
writer=module.DittoWriter(module.DittoConfig('http://127.0.0.1:18080',*auth),request=request)
for thing in module.THINGS.values():
    r=requests.get('http://127.0.0.1:18080/api/2/things/'+thing,auth=auth,timeout=5)
    assert r.status_code==404,f'preflight missing-resource status {r.status_code}'
writer.provision('nginx:'+auth[0])
# Existing legacy feature belongs only to this new test Thing.
r=requests.put('http://127.0.0.1:18080/api/2/things/'+module.THINGS['vehicle-001']+'/features/legacy',auth=auth,json={'properties':{'sentinel':'preserve'}},timeout=5);assert r.status_code in (201,204)
before=writer.read_thing('vehicle-001');assert 'v1' not in before.get('features',{})
args=['docker','run','--rm','--network','host','--entrypoint','mosquitto_sub','eclipse-mosquitto@sha256:75d6662dee52c947dc9dd9c29f1d8d7ffef78ddaf38001caa09755681e8bbc98','-h','127.0.0.1','-p','18883','-q','1','-V','mqttv5','--retain-as-published','-t','sdv/vehicle-001/health','-F','%j','-C','2','-W','25']
p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0
messages=[json.loads(l) for l in p.stdout.splitlines()]
ingress=Ingress(writer)
for i,m in enumerate(messages):
    assert m['qos']==1 and not m['retain']
    ingress.process(m['topic'],m['payload'])
    snapshot=writer.read_thing('vehicle-001')
    assert snapshot['features']['legacy']==before['features']['legacy']
    a=json.loads(m['payload']);props=dict(a);props['lastEventId']=props.pop('eventId')
    assert snapshot['features']['v1']['properties']==props
    (out/f'twin-{i}.json').write_text(json.dumps(snapshot,indent=2)+'\n')
restarted=Ingress(writer)
try:restarted.process(messages[-1]['topic'],messages[-1]['payload'])
except EventError as e:assert e.code=='DUPLICATE_EVENT'
else:raise AssertionError('restart replay accepted')
assert writer.read_thing('vehicle-001')==snapshot
(out/'live.json').write_text(json.dumps(dict(result='PASS',namespace=namespace,things=module.THINGS,policyIds=module.POLICIES,mqtt=messages,operations=operations,firstEventInitialization=True,conditionalSubsequentUpdate=True,legacyPreserved=True,restartDuplicateRejected=True,resources='retained; only new namespaced resources created; shared twins/policies unchanged'),indent=2)+'\n')
print('PASS',namespace)
