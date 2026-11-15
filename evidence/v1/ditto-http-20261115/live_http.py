"""Actual configured Java client through original nginx into isolated real Ditto."""
from pathlib import Path
import subprocess,json,os,re,time,zipfile,hashlib
import requests
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent;r=Path.home()/'.local/share/qa-sdv-v1/runtime'
s=(r/'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text();auth=re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)',s)[0];base='http://127.0.0.1:18090'
for _ in range(60):
 try:
  response=requests.get(base+'/api/2/things',auth=auth,timeout=3)
  if response.status_code==200:break
 except requests.RequestException:pass
 time.sleep(1)
else:raise AssertionError('isolated Ditto not ready')
policy='sdv:http-check-policy'
value={'entries':{'owner':{'subjects':{'nginx:'+auth[0]:{'type':'isolated regression'}},'resources':{x:{'grant':['READ','WRITE'],'revoke':[]} for x in ('thing:/','policy:/')}}}}
res=requests.put(base+'/api/2/policies/'+policy,auth=auth,headers={'If-None-Match':'*'},json=value,timeout=5);assert res.status_code in (201,204)
prepared=[]
for v in ('vehicle-001','vehicle-002'):
 source=requests.get('http://127.0.0.1:18080/api/2/things/sdv:'+v,auth=auth,timeout=5);assert source.status_code==200
 thing=source.json();thing['policyId']=policy
 res=requests.put(base+'/api/2/things/sdv:'+v,auth=auth,headers={'If-None-Match':'*'},json=thing,timeout=5);assert res.status_code in (201,204)
 prepared.append(thing)
res=requests.put(base+'/api/2/things/sdv:fleet-v1',auth=auth,headers={'If-None-Match':'*'},json={'policyId':policy,'features':{'summary':{'properties':{}}}},timeout=5);assert res.status_code in (201,204)
libs=r/'ditto-http-java-libs';libs.mkdir(exist_ok=True);classes=r/'ditto-http-java-classes';classes.mkdir(exist_ok=True)
with zipfile.ZipFile(root/'backend/target/backend-0.0.1-SNAPSHOT.jar') as z:
 for n in z.namelist():
  if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
cp=str(root/'backend/target/classes')+':'+str(libs/'*')
subprocess.run([str(r/'jdk21/bin/javac'),'-cp',cp,'-d',str(classes),str(out/'DittoHeaderLiveProbe.java')],check=True)
env=os.environ.copy();env.update(SDV_DITTO_USERNAME=auth[0],SDV_DITTO_PASSWORD=auth[1])
p=subprocess.run([str(r/'jdk21/bin/java'),'-cp',str(classes)+':'+cp,'com.ankit.sdv.backend.config.DittoHeaderLiveProbe',base],env=env,capture_output=True,text=True,timeout=40)
(out/'actual-java.txt').write_text(p.stdout+p.stderr)
assert p.returncode==0,'Java probe failed; see retained sanitized output'
fleet=requests.get(base+'/api/2/things/sdv:fleet-v1',auth=auth,timeout=5);assert fleet.status_code==200
(out/'live.json').write_text(json.dumps(dict(result='PASS',javaExit=p.returncode,nginx='official original config; NO Accept-Encoding normalization',nginxSha256=hashlib.sha256((r/'ditto-source/deployment/docker/nginx.conf').read_bytes()).hexdigest(),dittoBase=base,preparedIndividualTwins=prepared,materializedFleet=fleet.json(),scope='actual client read/write HTTP compatibility; copied real observations prepare this isolated existing-state test, not first-event initialization',services='separate new qa-v1-release-engineering-ditto project; original workloads untouched'),indent=2)+'\n')
print('PASS real individual reads/fleet writes; baseline400 reproduced without proxy normalization')
