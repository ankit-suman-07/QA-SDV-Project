"""Offline recheck of retained raw merged-main evidence; no service operations."""
from pathlib import Path
import json,datetime as dt
root=Path(__file__).resolve().parents[3]
p=root/'evidence/v1/merged-main-kanto-live-20261115T191810Z'
load=lambda n:json.loads((p/n).read_text())
stamp=lambda s:dt.datetime.fromisoformat(s.replace('Z','+00:00'))
r=load('result.json');assert r['result']=='PASS'
assert load('source-sha.json')['stdout'].strip()=='4afbbd8c11425a9e0e1701fea66b7ed13731abfe'
cycles=[];pids=[]
for i in range(1,4):
 prefix=f'cycle-{i}';state=load(prefix+'-stopped-state-parsed.json')['state']
 assert state['exit_code']==0 and not state['running']
 pids.append(load(('initial-state' if i==1 else f'cycle-{i-1}-restarted-state')+'-parsed.json')['state']['pid'])
 c=load(prefix+'-restart-correlation.json');event=c['message']['event'];wire=c['message']['wire']
 expected=dict(event);expected['lastEventId']=expected.pop('eventId')
 assert c['twin']['things']['vehicle-002']['features']['v1']['properties']==expected
 cycle=r['cycles'][i-1];source=stamp(event['sourceTimestamp'])
 assert source>max(stamp(cycle['runtimeStartedAt']),stamp(cycle['request']['utc']),stamp(cycle['previousSourceTimestamp']))
 assert wire['qos']==1 and not wire['retain']
 cycles.append({'cycle':i,'eventId':event['eventId'],'sourceMarginSeconds':(source-stamp(cycle['runtimeStartedAt'])).total_seconds(),'stopExit':state['exit_code']})
final=load('cleanup-state-parsed.json')['state'];assert final['exit_code']==0 and not final['running'] and final['pid']==-1
rows=[json.loads(l) for l in (p/'twin-timeline.jsonl').read_text().splitlines()];sources=[]
for row in rows:
 v=row['things']['vehicle-001'];props=v['features']['v1']['properties']
 assert v['attributes']['vehicleId']=='vehicle-001' and props['vehicleId']=='vehicle-001' and props['health']=='HEALTHY' and props['faults']==[]
 sources.append(stamp(props['sourceTimestamp']))
assert all(a<=b for a,b in zip(sources,sources[1:])) and sources[-1]>sources[0]
log=load('application-logs.json');logtext=log['stdout']+log['stderr']
assert 'Event loop stopped before' not in logtext and logtext.count('Application shutdown completed')==4
pids.append(load('cycle-3-restarted-state-parsed.json')['state']['pid'])
absent=[pid for pid in pids if not Path('/proc',str(pid)).exists()];assert absent==pids
summary={'result':'PASS','mainSha':'4afbbd8c11425a9e0e1701fea66b7ed13731abfe','cycles':cycles,'finalState':final,'finalTwinSamples':len(rows),'maxSampleGapSeconds':max((stamp(b['utc'])-stamp(a['utc'])).total_seconds() for a,b in zip(rows,rows[1:])),'oldPidsAbsentAtReview':pids,'shutdownCompletedEntries':4,'scope':'same-device managed lifecycle only'}
(p/'independent-review.json').write_text(json.dumps(summary,indent=2)+'\n')
live=root/'evidence/v1/merged-main-live-20261115T191503Z';results=json.loads((live/'results.json').read_text())
selected=('readiness','healthy-individual-fleet-dashboard','one-routed-fault-clear-isolation','persisted-watermark-restart')
assert all(results[n]['status']=='PASS' for n in selected)
verdict={'result':'PASS','selectedGates':{n:results[n] for n in selected},'originalWrapperSummary':'FAIL due to counting preallocated unselected gates; raw summary and exit retained','correction':'evaluate named selected gates only; no service rerun or application changes','notFreshlyTested':'Other preallocated BLOCKED/not-reached gates were intentionally excluded; broader candidate campaign retained as historical evidence'}
(live/'selected-gates-review.json').write_text(json.dumps(verdict,indent=2)+'\n')
print(json.dumps(summary,indent=2));print('Selected live gates PASS; original summary instrumentation error qualified')
