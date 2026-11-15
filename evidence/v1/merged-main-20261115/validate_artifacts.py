"""Validate fresh evidence, documented sanitization hashes and added relative links."""
from pathlib import Path
import json,hashlib,re,base64,subprocess,ast,datetime
root=Path(__file__).resolve().parents[3];out=root/'evidence/v1/merged-main-20261115'
folders=[out,root/'evidence/v1/merged-main-live-20261115T191503Z',root/'evidence/v1/merged-main-kanto-live-20261115T191810Z']
changes={x['file']:x for x in json.loads((out/'text-normalization.json').read_text())['files']};verified=0;transformed=[]
for folder in folders:
 manifest=folder/'artifact-sha256.json'
 if manifest.exists():
  for name,digest in json.loads(manifest.read_text()).items():
   p=folder/name;actual=hashlib.sha256(p.read_bytes()).hexdigest()
   if actual!=digest:
    v=changes[str(p.relative_to(root))];assert v['before']==digest and v['after']==actual
    transformed.append(str(p.relative_to(root)))
   verified+=1
for p in out.glob('*.py'):ast.parse(p.read_text())
for name in subprocess.check_output(['git','ls-files','*.json'],cwd=root,text=True).splitlines():json.loads((root/name).read_text(encoding='utf-8-sig'))
source=(Path.home()/'.local/share/qa-sdv-v1/runtime/ditto-source/documentation/src/main/resources/pages/ditto/intro-hello-world.md').read_text()
auth=re.findall(r'(?:-u|--user)\s+[\'\"]?([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)',source)[0];pair=':'.join(auth)
files=[p for folder in folders for p in folder.rglob('*') if p.is_file()]
for p in files:
 b=p.read_bytes();assert pair.encode() not in b and base64.b64encode(pair.encode()) not in b,str(p)
 try:s=b.decode()
 except UnicodeDecodeError:continue
 assert not re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',s),str(p)
changed=subprocess.check_output(['git','diff','origin/main','--name-only'],cwd=root,text=True).splitlines()
assert all(p.startswith(('docs/','evidence/')) or p=='scripts/v1_acceptance/README.md' for p in changed)
missing=[];count=0
for name in ['docs/findings/v1-release-readiness.md','docs/findings/v1-implementation-verification.md','docs/findings/mvp-to-v1-comparison.md','evidence/README.md','scripts/v1_acceptance/README.md','evidence/v1/merged-main-20261115/README.md']:
 p=root/name
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#')[0].split(' "')[0].strip('<>');count+=1
  if not (p.parent/target).exists():missing.append({'file':name,'target':target})
assert len(missing)==10 and all(x['target'].endswith('.log') for x in missing),missing
(out/'validation.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'priorArtifactHashesVerifiedOrDocumentedNormalization':verified,'normalizedArtifacts':transformed,'freshFilesSecretScanned':len(files),'relativeLinksChecked':count,'newMissingLinks':[],'historicalMissingLinks':missing,'newPythonToolsAst':'PASS','applicationDiff':'empty','scope':'documentation/evidence only'},indent=2)+'\n')
for folder in folders:
 manifest={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and p.name not in ('artifact-sha256.json','final-artifact-sha256.json')}
 (folder/'final-artifact-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS',verified,'hashes verified/qualified;',len(files),'files scanned;',count,'links;10 historical raw logs missing')
