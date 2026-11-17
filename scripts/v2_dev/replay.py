"""Offline feeder/replay and optional MQTT CLI transport. JSONL stdout by default."""
import argparse
import json
import subprocess
from pathlib import Path
from . import contract as c

ROOT=Path(__file__).resolve().parents[2]/'tests/fixtures/v2'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ack-development-only',action='store_true',required=True)
    parser.add_argument('--sequence',choices=[p.stem for p in (ROOT/'sequences').glob('*.json')],default='recovery')
    parser.add_argument('--kind',choices=['observations','health'],default='observations')
    parser.add_argument('--vehicle',choices=c.VEHICLES,default='vehicle-002')
    parser.add_argument('--anchor',default=c.iso(c.EPOCH))
    parser.add_argument('--mqtt-publish',action='store_true')
    parser.add_argument('--capture',type=int,metavar='COUNT')
    parser.add_argument('--host',choices=['localhost','127.0.0.1'],default='127.0.0.1')
    parser.add_argument('--port',type=int,default=18884)
    args=parser.parse_args()
    if args.capture is not None:
        c.require(0<args.capture<=10000,'INVALID_CONFIG','bounded count')
        subprocess.run(['mosquitto_sub','-h',args.host,'-p',str(args.port),'-t','sdv/+/v2/+',
                        '-q','1','-C',str(args.capture),'-W','10','-v'],check=True,timeout=12)
        return
    fixture=c.rebase(json.loads((ROOT/'sequences'/f'{args.sequence}.json').read_text()),c.parse_timestamp(args.anchor))
    oracle=c.Sequence()
    for step in fixture['steps']:
        if 'observation' not in step:
            if not args.mqtt_publish: print(json.dumps(dict(control='clock',evaluationTime=step['now'])))
            continue
        e=step['observation']; original=e['vehicleId']; e['vehicleId']=args.vehicle
        e['eventId']=e['eventId'].replace(original,args.vehicle)
        # Includes negative deliveries intentionally: receiver must reject them.
        if args.kind=='health':
            if 'register' in step: oracle.session=tuple(step['register'])
            try: health,recovery=oracle.accept(e,c.parse_timestamp(step.get('nowOverride',step['now'])))
            except c.ContractError: continue
            faults=oracle.faults
            e=dict(e,health=health,faults=faults,recoveryState=recovery,
                   recoveryStartedAt=c.iso(oracle.start) if oracle.start else None,sourceSilent=False)
        topic=f'sdv/{args.vehicle}/v2/{args.kind}'
        payload=json.dumps(e,allow_nan=False,separators=(',',':'))
        if args.mqtt_publish:
            subprocess.run(['mosquitto_pub','-h',args.host,'-p',str(args.port),'-t',topic,
                            '-q','1','-m',payload],check=True,timeout=3)
        else: print(json.dumps(dict(topic=topic,payload=e,evaluationTime=step.get('nowOverride',step['now']))))

if __name__=='__main__': main()
