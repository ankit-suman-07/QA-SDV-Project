import json,os,signal,subprocess,sys,time
from pathlib import Path
root=Path('/home/ankitsuman/Desktop/SDV/QA-SDV-Project');out=root/'evidence/v1/verification-20261114T051226Z/mock-smoke-port3000';out.mkdir(exist_ok=False)
command=['/tmp/qa-review-venv/bin/python','-B','-m','scripts.v1_dev.fleet_smoke','--java','/tmp/qa-v1-tooling/amazon-corretto-21.0.13.0.11-linux-x64/bin/java','--artifacts-dir',str(out),'--frontend-port','3000','--hold']
(out/'commands.json').write_text(json.dumps({'smoke':command,'boundary':'Actual packaged Spring Boot and Chrome; HTTP mocks and controlled fleet-write capture, NOT real Ditto/providers/MQTT'},indent=2)+'\n')
log=(out/'harness.log').open('w');p=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
try:
    deadline=time.monotonic()+60
    while not (out/'stack.json').exists():
        if p.poll() is not None:raise RuntimeError('smoke failed; inspect harness.log')
        if time.monotonic()>deadline:raise TimeoutError('smoke readiness')
        time.sleep(.2)
    env=dict(os.environ,PLAYWRIGHT_MODULE='/tmp/qa-v1-tooling/browser/node_modules/playwright-core/index.mjs',CHROME_PATH='/usr/bin/google-chrome')
    browser=['/tmp/qa-v1-tooling/node-v22.16.0-linux-x64/bin/node','frontend/tests/fleet-browser.mjs',str(out/'stack.json')]
    with (out/'browser.log').open('w') as stream:r=subprocess.run(browser,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
    assert r.returncode==0,'browser failure; inspect browser.log'
    print('PASS actual Java + mock API/writer smoke and Chrome smoke; inspect saved result.json/browser-result.json/screenshots')
finally:
    if p.poll() is None:p.send_signal(signal.SIGINT)
    try:p.wait(timeout=25)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
    log.close()
