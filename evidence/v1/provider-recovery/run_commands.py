import subprocess,json,sys,pathlib,datetime,os
root=pathlib.Path(sys.argv[1]);out=root/sys.argv[2];out.mkdir(parents=True,exist_ok=True)
commands=[['/tmp/qa-review-venv/bin/python','-B','-m','pytest','-q','-ra','-p','no:cacheprovider','-m','not integration'],['docker','compose','-f','vehicle-simulator/docker-compose.v1.yml','config','--quiet'],['docker','compose','-f','vehicle-simulator/docker-compose.yml','config','--quiet'],['git','diff','--check']]
records=[]
for n,cmd in enumerate(commands):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(cmd,cwd=root,env={**os.environ,'PYTHONPATH':'/tmp/qa-sdk-0157:/tmp/qa-v1-tooling/protobuf'},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 name=f'final-check-{n}.txt';(out/name).write_text(p.stdout);records.append({'command':cmd,'cwd':str(root),'startedAt':start,'exitCode':p.returncode,'output':name,'envOverrides':{'PYTHONPATH':'/tmp/qa-sdk-0157:/tmp/qa-v1-tooling/protobuf'}})
 print(cmd,'exit',p.returncode,flush=True)
(out/'final-commands.json').write_text(json.dumps(records,indent=2)+'\n')
if any(r['exitCode'] for r in records):sys.exit(1)
