"""Small executable V2 development oracle. Expected vectors live separately in JSON.

Reuses V1 strict wire/time/availability/classification utilities without mutating V1.
Not a health implementation for production use.
"""
import copy
import math
from scripts.v1_dev.contract import (ContractError, require, decode_event, parse_timestamp,
                                    iso, availability, classify, EPOCH, timedelta)

VEHICLES = ('vehicle-001', 'vehicle-002', 'vehicle-003')
TERMINAL = ('SUCCEEDED', 'FAILED', 'TIMED_OUT')

def number(value):
    return type(value) in (int, float) and math.isfinite(value)

def validate(event, topic=None):
    require(isinstance(event, dict), 'INVALID_TYPE', 'object required')
    required = ('schemaVersion','vehicleId','eventId','sessionId','sessionGeneration',
                'sequence','frame','simulationSeconds','sourceTimestamp',
                'processingTimestamp','provenance','lidar')
    require(all(k in event for k in required), 'MISSING_FIELD', 'observation envelope')
    require(event['schemaVersion'] == '2.0.0', 'UNSUPPORTED_VERSION', '2.0.0 required')
    require(event['vehicleId'] in VEHICLES, 'UNKNOWN_VEHICLE', 'unregistered identity')
    if topic is not None:
        require(topic == f"sdv/{event['vehicleId']}/v2/observations", 'TOPIC_MISMATCH','identity')
    for key in ('eventId','sessionId'):
        require(isinstance(event[key],str) and bool(event[key].strip()),'INVALID_TYPE',key)
    for key in ('sequence','frame','sessionGeneration'):
        require(type(event[key]) is int and event[key] >= (1 if key == 'sessionGeneration' else 0),
                'INVALID_TYPE', key)
    require(number(event['simulationSeconds']) and event['simulationSeconds'] >= 0,'INVALID_TYPE','simulationSeconds')
    parse_timestamp(event['sourceTimestamp']); parse_timestamp(event['processingTimestamp'])
    require(event['provenance'] in ('CARLA','SYNTHETIC'),'INVALID_TYPE','provenance')
    lidar=event['lidar']
    require(isinstance(lidar,dict) and type(lidar.get('sensorAvailable')) is bool,'INVALID_TYPE','lidar')
    d=lidar.get('distanceMeters')
    require((lidar['sensorAvailable'] and number(d) and d>=0) or
            (not lidar['sensorAvailable'] and d is None),'INVALID_TYPE','distance/availability')
    return event

def validate_health(event):
    validate(event)
    require(event.get('health') in ('HEALTHY','WARNING','CRITICAL'),'INVALID_HEALTH','health')
    require(event.get('recoveryState') in ('NONE','IN_PROGRESS'),'INVALID_TYPE','recoveryState')
    require(type(event.get('sourceSilent')) is bool,'INVALID_TYPE','sourceSilent')
    require(event.get('faults') in ([],['LIDAR_OBSTRUCTION'],['LIDAR_SENSOR_FAILURE']),
            'HEALTH_FAULT_MISMATCH','faults')
    if event['recoveryState']=='NONE':
        require((event['health'],event['faults'])==classify(event['lidar']['distanceMeters'],event['lidar']['sensorAvailable']),
                'HEALTH_FAULT_MISMATCH','classification')
    else:
        require(event['health']!='HEALTHY' and event['faults'] and event.get('recoveryStartedAt') is not None,
                'HEALTH_FAULT_MISMATCH','recovery retains fault')
        parse_timestamp(event['recoveryStartedAt'])
    return event

def extract(points):
    if not points or not isinstance(points,list): return [None,False]
    if any(not isinstance(p,list) or len(p)!=4 or not all(number(n) for n in p) for p in points):
        return [None,False]
    xs=[p[0] for p in points if 0<p[0]<=50 and abs(p[1])<=1.5 and -1<=p[2]<=1]
    return [min(xs) if xs else 50,True]

def rebase(value, anchor):
    """Shift all valid UTC strings once; leave invalid timestamp vectors untouched."""
    if isinstance(value,dict): return {k:rebase(v,anchor) for k,v in value.items()}
    if isinstance(value,list): return [rebase(v,anchor) for v in value]
    if isinstance(value,str) and 'T' in value and value.endswith(('Z','+00:00')):
        try: return iso(anchor+(parse_timestamp(value)-EPOCH))
        except ContractError: pass
    return value

class Sequence:
    def __init__(self):
        self.latest=None; self.session=(1,'session-1'); self.health='HEALTHY'
        self.start=None; self.last_receipt=None; self.faults=[]
    def accept(self,e,now):
        validate(e); source=parse_timestamp(e['sourceTimestamp'])
        generation=e['sessionGeneration']; session=(generation,e['sessionId'])
        if self.latest:
            old=self.latest
            if generation < old['sessionGeneration']: raise ContractError('OUT_OF_ORDER','retired session')
            if e['eventId']==old['eventId']:
                require(e==old,'EVENT_ID_CONFLICT','changed payload')
                raise ContractError('DUPLICATE_EVENT','cached observation')
            require(source>parse_timestamp(old['sourceTimestamp']),'OUT_OF_ORDER','equal/late UTC')
            if generation==old['sessionGeneration']:
                require(e['sequence']>old['sequence'] and e['frame']>old['frame'],'OUT_OF_ORDER','sequence/frame')
        require(session==self.session,'UNREGISTERED_SESSION','explicit session registration required')
        restart=self.latest and generation!=self.latest['sessionGeneration']
        gap=self.latest and (source-parse_timestamp(self.latest['sourceTimestamp'])).total_seconds()>.5
        receipt_gap=self.last_receipt and (now-self.last_receipt).total_seconds()>.5
        if restart or gap or receipt_gap: self.start=None
        current,faults=classify(e['lidar']['distanceMeters'],e['lidar']['sensorAvailable'])
        fresh=availability(source,now)=='AVAILABLE'
        if current!='HEALTHY': self.health=current; self.faults=faults; self.start=None
        elif not fresh: self.start=None
        elif self.health!='HEALTHY':
            if self.start is None: self.start=source
            if (source-self.start).total_seconds()>=2: self.health='HEALTHY'; self.faults=[]; self.start=None
        self.latest=copy.deepcopy(e); self.last_receipt=now
        return [self.health,'IN_PROGRESS' if self.start is not None else 'NONE']

    def silence(self,now):
        silent=self.last_receipt is None or (now-self.last_receipt).total_seconds()>.5
        if silent: self.start=None
        return [self.health,'IN_PROGRESS' if self.start is not None else 'NONE',silent]

def evaluate_case(case):
    kind=case['kind']; value=case['input']
    try:
        if kind=='decode': decode_event(value); return 'VALID'
        if kind=='validate':
            validate(value.get('event',value),value.get('topic')); return 'VALID'
        if kind=='classify': validate(value); return list(classify(value['lidar']['distanceMeters'],value['lidar']['sensorAvailable']))
        if kind=='extract': return extract(value)
        if kind=='availability':
            return availability(parse_timestamp(value['sourceTimestamp']) if value['sourceTimestamp'] else None,parse_timestamp(value['now']))
        if kind=='clock': return iso(parse_timestamp(value['utcOrigin'])+timedelta(seconds=value['simulationSeconds']-value['simulationOrigin']))
        raise ValueError('unknown vector kind '+kind)
    except ContractError as error: return error.code

def check_sequence(fixture):
    sequence=Sequence(); failures=[]
    for i,step in enumerate(fixture['steps']):
        if 'register' in step: sequence.session=tuple(step['register'])
        try:
            now=parse_timestamp(step.get('nowOverride',step['now']))
            actual=sequence.accept(step['observation'],now) if 'observation' in step else sequence.silence(now)
        except ContractError as error: actual=error.code
        if actual!=step['expected']: failures.append((i,step['expected'],actual))
    return failures

def counts(availabilities,health):
    require(len(availabilities)==len(health)==3,'FLEET_IDENTITY','three registered vehicles')
    return [3,*[availabilities.count(a) for a in ('AVAILABLE','STALE','UNAVAILABLE')],
            *[sum(a=='AVAILABLE' and h==state for a,h in zip(availabilities,health))
              for state in ('HEALTHY','WARNING','CRITICAL')]]

class Action:
    def __init__(self,request,now):
        require(isinstance(request,dict),'INVALID_REQUEST','object')
        require(request.get('vehicleId') in VEHICLES,'UNKNOWN_VEHICLE','target')
        require(request.get('action') in ('INJECT_SCENARIO','CLEAR_SCENARIO','RESTART_APP'), 'INVALID_REQUEST','action')
        if request['action']!='RESTART_APP': require(request.get('scenario')=='LIDAR_OBSTRUCTION','INVALID_REQUEST','scenario')
        for key in ('actionId','traceId'): require(isinstance(request.get(key),str) and bool(request[key].strip()),'INVALID_REQUEST',key)
        self.request=copy.deepcopy(request); self.status='ACCEPTED'
        self.deadline=now+timedelta(seconds=30 if request['action']=='RESTART_APP' else 10)
    def expire(self,now):
        if self.status not in TERMINAL and now>=self.deadline: self.status='TIMED_OUT'
    def update(self,result,now):
        require(all(result.get(k)==self.request[k] for k in ('vehicleId','actionId','traceId')),
                'CORRELATION_MISMATCH','vehicle/action/trace')
        self.expire(now)
        require(self.status not in TERMINAL,'TERMINAL_ACTION','immutable outcome')
        status=result.get('status')
        allowed={'ACCEPTED':('EXECUTING','FAILED'),'EXECUTING':('SUCCEEDED','FAILED')}
        require(status in allowed[self.status],'INVALID_TRANSITION','execution order')
        self.status=status
    def view(self,now):
        self.expire(now)
        return dict(self.request,status=self.status,deadline=iso(self.deadline),mock=True)
