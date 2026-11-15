"""Read-only operator log capture; no lifecycle changes."""
from pathlib import Path
import json
import subprocess
out = Path(__file__).resolve().parent
args = ['sudo', '-n', '/opt/qa-sdv-v1-kanto/bin/kanto-cm', '--host', '/run/qa-sdv-v1-kanto/container-management.sock', '--timeout', '5', 'logs', '--name', 'autonomoushealthapp-vehicle-002', '--tail', '120']
p = subprocess.run(args, capture_output=True, text=True, timeout=15)
(out / 'kanto-app.log').write_text(p.stdout)
(out / 'log-capture.json').write_text(json.dumps(dict(argv=args,exit=p.returncode,stderr=p.stderr),indent=2)+'\n')
print('Log saved; exit:',p.returncode)
