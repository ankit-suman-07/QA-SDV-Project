"""Selected affected live gates on a new real stack; no shared-state reset."""
import argparse,datetime as dt,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
R=Path.home()/'.local/share/qa-sdv-v1/runtime'
s=(R/'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text()
auth=re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)',s)[0]
os.environ.update(SDV_ACCEPTANCE_DITTO_USERNAME=auth[0],SDV_ACCEPTANCE_DITTO_PASSWORD=auth[1],SDV_ACCEPTANCE_DITTO_SUBJECT='nginx:'+auth[0])
from scripts.v1_acceptance.run import Run
out='evidence/v1/release-candidate-live-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
run=Run(argparse.Namespace(output=out,ditto_source=str(R/'ditto-source'),trials=5,chrome='/usr/bin/google-chrome'))
selected=[('healthy',run.healthy),('fault-recovery-trials',run.trials),('freshness-null',run.freshness),('invalid-ordering-restart',run.negatives),('individual-write-recovery',run.individual_failure),('fleet-write-recovery',run.fleet_failure),('mqtt-reconnect',run.reconnect),('dashboard',run.dashboard)]
try:
 run.gate('readiness',run.configure)
 if run.results['readiness']['status']=='PASS':
  for name,fn in selected:run.gate(name,fn)
 run.results['provider-kuksa-recovery']={'status':'REUSED','reason':'Unaffected provider implementation: merged #38/#39 real recovery evidence and exact fix-head CI; avoid another provider outage here.'}
 run.results['baseline-regression']={'status':'REUSED','reason':'Existing baseline workflow at exact PR heads; no legacy implementation change except app lifecycle, independently live-tested.'}
 run.results['kanto-v1-09']={'status':'REUSED','reason':'Merged #43 original pass plus affected lifecycle three-cycle actual Kanto verification in shutdown-kanto-live-20261115T152137Z.'}
finally:run.cleanup()
required=['readiness']+[n for n,fn in selected]
result='PASS' if all(run.results[n]['status']=='PASS' for n in required) else 'FAIL'
run.write('candidate-verdict.json',{'label':'UNMERGED INTEGRATION CANDIDATE','result':result,'selectedGates':required,'reusedEvidence':'explicitly identified in results.json','noReleaseClaim':True})
print('Evidence:',out);print('Candidate:',result)
raise SystemExit(0 if result=='PASS' else 1)
