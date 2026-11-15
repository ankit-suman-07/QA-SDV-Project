"""Offline check of operator rehearsal; no service actions or credential access."""
from pathlib import Path
import json,datetime as dt
root=Path(__file__).resolve().parents[3]
p=root/'evidence/v1/demo-20261115T234255Z'
load=lambda name:json.loads((p/name).read_text())
stamp=lambda value:dt.datetime.fromisoformat(value.replace('Z','+00:00'))
assert load('result.json')['result']=='PASS'
cleanup=load('cleanup.json');assert cleanup['errors']==[] and not cleanup['keep']
assert not load('cleanup-kanto.json')['state']['running'] and load('cleanup-kanto.json')['state']['exit_code']==0
messages=[json.loads(l) for l in (p/'mqtt.jsonl').read_text().splitlines()]
events={row['event']['eventId']:row for row in messages}
for row in messages:
 assert row['qos']==1 and not row['retain']
 if row['event']['vehicleId']=='vehicle-001':assert row['event']['health']=='HEALTHY' and row['event']['faults']==[]
for name,health in [('fault.json','CRITICAL'),('recovered.json','HEALTHY')]:
 snap=load(name)
 for vehicle in ('vehicle-001','vehicle-002'):
  props=snap['things'][vehicle]['features']['v1']['properties'];event=events[props['lastEventId']]['event']
  expected=dict(event);expected['lastEventId']=expected.pop('eventId');assert props==expected
  assert props['health']==('HEALTHY' if vehicle=='vehicle-001' else health)
  for summary in (snap['fleetApi'],snap['fleetThing']):
   view=next(x for x in summary['vehicles'] if x['vehicleId']==vehicle)
   assert view['lastEventId']==props['lastEventId'] and view['sourceTimestamp']==props['sourceTimestamp']
restart=load('post-restart-match.json');props=restart['observed']['things']['vehicle-002']['features']['v1']['properties']
event=events[props['lastEventId']]['event'];expected=dict(event);expected['lastEventId']=expected.pop('eventId');assert props==expected
assert props['lastEventId']!=restart['previous']['lastEventId']
assert stamp(props['sourceTimestamp'])>max(stamp(restart['previous']['sourceTimestamp']),stamp(restart['boundaries']['request']),stamp(restart['boundaries']['runtime']))
assert load('managed-stopped.json')['state']['exit_code']==0
old=load('managed-before-stop.json')['state']['pid'];assert not Path('/proc',str(old)).exists()
assert all(not Path('/proc',str(x['pid'])).exists() for x in cleanup['ownedProcesses'])
commands=[json.loads(l) for l in (p/'commands.jsonl').read_text().splitlines()];assert all(x['exit']==0 for x in commands)
summary={'result':'PASS','scope':'operator working-copy demo sequence; not final SHA/full acceptance','mqttMessages':len(messages),'vehicle001HealthyMqttMessages':sum(x['event']['vehicleId']=='vehicle-001' for x in messages),'faultAndRecoveryFleetIdentity':'exact source/event match','restart':'exact MQTT/twin/API and three source boundaries PASS; stop/cleanup exit0','cleanup':'owned Kanto/backend/frontend stopped; initially stopped Docker002 unchanged','limitations':['Operator run predates final source-hash/backend-artifact metadata, fleet-lag retry/status and bounded observer-close hardening. Those final changes covered by focused controls; no second full campaign.','Restart fleet snapshots lagged individual identity while retaining healthy counts; latest helper retries exact identity before step completion.','Docker-to-Kanto transition/keep-running/failure cleanup controls tested with focused substitutes; live run began with Docker002 already stopped.']}
(p/'independent-review.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
