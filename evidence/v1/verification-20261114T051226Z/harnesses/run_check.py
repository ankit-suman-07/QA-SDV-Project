import argparse,datetime,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--cwd',default=os.getcwd());p.add_argument('--env',action='append',default=[]);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
root=Path('/home/ankitsuman/Desktop/SDV/QA-SDV-Project/evidence/v1/verification-20261114T051226Z');env=os.environ.copy();recorded={}
for pair in a.env:
    key,value=pair.split('=',1)
    assert not any(x in key.upper() for x in ('PASSWORD','TOKEN','SECRET'))
    env[key]=value;recorded[key]=value
command=a.command[1:] if a.command[:1]==['--'] else a.command
start=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (root/(a.name+'.log')).open('w') as out:
    result=subprocess.run(command,cwd=a.cwd,env=env,stdout=out,stderr=subprocess.STDOUT)
record={'name':a.name,'startedAt':stamp,'command':command,'cwd':a.cwd,'environmentOverrides':recorded,'exitCode':result.returncode,'durationSeconds':round(time.monotonic()-start,3),'output':a.name+'.log'}
(root/(a.name+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));print('\n'.join((root/(a.name+'.log')).read_text(errors='replace').splitlines()[-12:]))
raise SystemExit(result.returncode)
