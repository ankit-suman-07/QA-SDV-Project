"""Opt-in loopback V2 HTTP substitutes, NOT production/native protocols."""
import argparse
import copy
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import unquote
from . import contract as c

FIXTURES=Path(__file__).resolve().parents[2]/'tests/fixtures/v2'

class State:
    def __init__(self,anchor=c.EPOCH,provider_vehicle='vehicle-002'):
        c.require(provider_vehicle in c.VEHICLES,'UNKNOWN_VEHICLE','provider identity')
        self.provider_vehicle=provider_vehicle
        self.lock=RLock(); self.now=anchor; self.revisions={v:1 for v in c.VEHICLES}
        self.twins={v:c.rebase(json.loads((FIXTURES/f'twins/{v}.json').read_text()),anchor) for v in c.VEHICLES}
        self.actions={}; self.failure='none'; self.received={v:anchor for v in c.VEHICLES}
    def view(self,v):
        p=self.twins[v]['features'].get('v2',{}).get('properties')
        result=dict(vehicleId=v,thingId='sdv:'+v,healthStatus=None,activeFaults=None,
                    sourceTimestamp=None,lastEventId=None,availability='UNAVAILABLE',
                    lidar=None,recoveryState='NONE',sourceSilent=True)
        if p:
            result.update({k:p[k] for k in ('sourceTimestamp','lastEventId','lidar','recoveryState','sourceSilent','sessionId','sessionGeneration','sequence')})
            result.update(healthStatus=p['health'],activeFaults=p['faults'],
                          availability=c.availability(c.parse_timestamp(p['sourceTimestamp']),self.now))
            result['sourceSilent']=p['sourceSilent'] or (self.now-self.received[v]).total_seconds()>.5
            if result['sourceSilent']: result['recoveryState']='NONE'
        return result

def handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,status,payload,etag=None):
            data=b'' if status==204 else json.dumps(payload,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('X-SDV-Mock','true')
            self.send_header('Access-Control-Allow-Origin','http://localhost:3000')
            self.send_header('Access-Control-Allow-Headers','Content-Type,If-Match,If-None-Match')
            self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS')
            if etag: self.send_header('ETag',etag)
            self.end_headers()
            if status!=204: self.wfile.write(data)
        def run(self):
            try:
                with state.lock: self.route()
            except c.ContractError as error:
                self.reply({'UNKNOWN_VEHICLE':404,'CORRELATION_MISMATCH':409,'TERMINAL_ACTION':409,
                            'INVALID_TRANSITION':409}.get(error.code,400),{'error':error.code})
            except (ValueError,KeyError,TypeError): self.reply(400,{'error':'INVALID_REQUEST'})
        def body(self):
            size=int(self.headers.get('Content-Length','0'))
            c.require(0<size<=65536,'MALFORMED_JSON','bounded body required')
            value=c.decode_event(self.rfile.read(size))
            c.require(isinstance(value,dict),'INVALID_TYPE','object required')
            return value
        def route(self):
            path=unquote(self.path); method=self.command
            if method=='OPTIONS': return self.reply(200,{'mock':True})
            if method=='POST' and path=='/_mock/clock':
                state.now=c.parse_timestamp(self.body()['now']); return self.reply(200,{'now':c.iso(state.now)})
            if method=='POST' and path=='/_mock/failure':
                mode=self.body()['mode']; c.require(mode in ('none','reject','unavailable','timeout'),'INVALID_REQUEST','mode')
                state.failure=mode; return self.reply(200,{'mode':mode})
            if state.failure=='unavailable': return self.reply(503,{'error':'MOCK_SERVICE_UNAVAILABLE'})
            match=re.fullmatch(r'/api/2/things/sdv:(vehicle-\d{3})(/features/v2/properties)?',path)
            if match:
                v=match[1]; c.require(v in c.VEHICLES,'UNKNOWN_VEHICLE','target')
                etag=f'"{state.revisions[v]}"'; props=state.twins[v]['features'].get('v2',{}).get('properties')
                if method=='GET':
                    if match[2] and props is None: return self.reply(404,{'error':'FEATURE_MISSING'})
                    return self.reply(200,props if match[2] else state.twins[v],etag)
                if method=='PUT' and match[2]:
                    if props is None:
                        if self.headers.get('If-None-Match')!='*': return self.reply(428,{'error':'PRECONDITION_REQUIRED'})
                    elif self.headers.get('If-None-Match')=='*': return self.reply(412,{'error':'PRECONDITION_FAILED'})
                    elif self.headers.get('If-Match') is None: return self.reply(428,{'error':'PRECONDITION_REQUIRED'})
                    elif self.headers['If-Match']!=etag: return self.reply(412,{'error':'PRECONDITION_FAILED'})
                    value=self.body(); event=dict(value,eventId=value.get('lastEventId')); event.pop('lastEventId',None); c.validate_health(event)
                    c.require(event['vehicleId']==v,'TOPIC_MISMATCH','twin identity')
                    if props:
                        seq=c.Sequence(); seq.latest=dict(props,eventId=props['lastEventId'])
                        seq.latest.pop('lastEventId',None); seq.session=(props['sessionGeneration'],props['sessionId'])
                        # Session registration belongs to real ingress. This mock will not trust remote jumps.
                        try: seq.accept(event,state.now)
                        except c.ContractError as error: return self.reply(409,{'error':error.code})
                    state.twins[v]['features']['v2']={'properties':copy.deepcopy(value)}
                    state.revisions[v]+=1; state.received[v]=state.now
                    return self.reply(204 if props else 201,{},f'"{state.revisions[v]}"')
            if method=='GET' and path=='/api/v2/vehicles': return self.reply(200,{'vehicleIds':list(c.VEHICLES),'mock':True})
            match=re.fullmatch(r'/api/v2/vehicles/(vehicle-\d{3})/state',path)
            if method=='GET' and match:
                c.require(match[1] in c.VEHICLES,'UNKNOWN_VEHICLE','target'); return self.reply(200,state.view(match[1]))
            if method=='GET' and path=='/api/v2/fleet':
                views=[state.view(v) for v in c.VEHICLES]
                values=c.counts([v['availability'] for v in views],[v['healthStatus'] for v in views])
                keys=('totalVehicles','availableVehicles','staleVehicles','unavailableVehicles','healthyVehicles','warningVehicles','criticalVehicles')
                return self.reply(200,dict(zip(keys,values),generatedAt=c.iso(state.now),vehicles=views,mock=True))
            match=re.fullmatch(r'/mock/v2/diagnostics/(vehicle-\d{3})/(health|faults)',path)
            if method=='GET' and match:
                v=match[1]; c.require(v in c.VEHICLES,'UNKNOWN_VEHICLE','target'); view=state.view(v)
                if match[2]=='health': result=view
                else:
                    result=dict(vehicleId=v,faults=[dict(faultId=code.lower().replace('_','-'),code=code,
                        severity=view['healthStatus'],status='ACTIVE',sourceTimestamp=view['sourceTimestamp'],
                        eventId=view['lastEventId'],observedValue=view['lidar']['distanceMeters'],unit='m')
                        for code in view['activeFaults'] or []])
                return self.reply(200,dict(result,boundary='PROJECT_MOCK_NOT_NATIVE_PROTOCOL'))
            if method=='POST' and path in ('/api/v2/diagnostics/actions','/api/v1/scenarios/actions'):
                request=self.body(); request.pop('fixtureLabel',None)
                action=c.Action(request,state.now)
                if path=='/api/v1/scenarios/actions' and request['vehicleId']!=state.provider_vehicle:
                    return self.reply(404,{'error':'PROVIDER_IDENTITY_MISMATCH'})
                if path=='/api/v1/scenarios/actions' and request['action']=='RESTART_APP': return self.reply(422,{'error':'NOT_A_LIFECYCLE_EXECUTOR'})
                old=state.actions.get(request['actionId'])
                if old:
                    if old.request!=request: return self.reply(409,{'error':'ACTION_ID_CONFLICT'})
                    if path=='/api/v1/scenarios/actions':
                        return self.reply(200,dict(request,active=request['action']=='INJECT_SCENARIO'))
                    return self.reply(202,old.view(state.now))
                if state.failure!='none':
                    code={'reject':409,'timeout':504}[state.failure]
                    return self.reply(code,{'error':'MOCK_'+state.failure.upper(),'execution':'UNKNOWN' if code==504 else 'NOT_ACCEPTED'})
                state.actions[request['actionId']]=action
                if path=='/api/v1/scenarios/actions':
                    return self.reply(200,dict(request,active=request['action']=='INJECT_SCENARIO'))
                return self.reply(202,action.view(state.now))
            match=re.fullmatch(r'/api/v2/diagnostics/actions/([^/]+)',path)
            if method=='GET' and match:
                action=state.actions.get(match[1])
                return self.reply(200,action.view(state.now)) if action else self.reply(404,{'error':'UNKNOWN_ACTION'})
            if method=='POST' and path=='/_mock/action-result':
                result=self.body(); action=state.actions.get(result.get('actionId'))
                if not action: return self.reply(404,{'error':'UNKNOWN_ACTION'})
                action.update(result,state.now); return self.reply(200,action.view(state.now))
            self.reply(404,{'error':'UNSUPPORTED_MOCK_ROUTE'})
        do_GET=run; do_POST=run; do_PUT=run; do_DELETE=run; do_OPTIONS=run
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ack-development-only',action='store_true',required=True)
    parser.add_argument('--port',type=int,default=18082)
    parser.add_argument('--provider-vehicle',choices=c.VEHICLES,default='vehicle-002')
    parser.add_argument('--anchor',default=c.iso(c.EPOCH),help='UTC epoch replacement; frozen injected clock')
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(State(c.parse_timestamp(args.anchor),args.provider_vehicle)))
    print(f'SDV V2 MOCK ONLY http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
