"""Focused merged-main clean initialization / packaged Spring smoke; isolated stack only."""
import argparse,datetime as dt,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
R=Path.home()/'.local/share/qa-sdv-v1/runtime'
s=(R/'ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text()
auth=re.findall(r"(?:-u|--user)\s+['\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)",s)[0]
os.environ.update(SDV_ACCEPTANCE_DITTO_USERNAME=auth[0],SDV_ACCEPTANCE_DITTO_PASSWORD=auth[1],SDV_ACCEPTANCE_DITTO_SUBJECT='nginx:'+auth[0])
from scripts.v1_acceptance.run import Run
out='evidence/v1/merged-main-live-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
class MainRun(Run):
 def compose(self,which,*args,**kw):
  if which=='edge' and args and args[0]=='up':
   before={v:self.writer.read_thing(v) for v in ('vehicle-001','vehicle-002')}
   self.write('clean-before-publishers.json',before)
   assert all('v1' not in t.get('features',{}) for t in before.values())
  return super().compose(which,*args,**kw)
run=MainRun(argparse.Namespace(output=out,ditto_source=str(R/'ditto-source'),trials=1,chrome='/usr/bin/google-chrome'))
try:
 run.gate('readiness',run.configure)
 if run.results['readiness']['status']=='PASS':
  run.gate('healthy-individual-fleet-dashboard',run.healthy)
  run.gate('one-routed-fault-clear-isolation',run.trials)
  run.gate('persisted-watermark-restart',run.negatives)
finally:run.cleanup()
result='PASS' if all(run.results[n]['status']=='PASS' for n in ('readiness','healthy-individual-fleet-dashboard','one-routed-fault-clear-isolation','persisted-watermark-restart')) else 'FAIL'
run.write('merged-main-verdict.json',{'mainSha':'4afbbd8c11425a9e0e1701fea66b7ed13731abfe','result':result,'scope':'focused clean-init, packaged Spring individual/fleet, one fault-clear, restart ordering; historical broader campaign inherited explicitly'})
print('Evidence:',out);print(result);raise SystemExit(result!='PASS')
