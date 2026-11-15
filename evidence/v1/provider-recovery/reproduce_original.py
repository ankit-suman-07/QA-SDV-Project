"""Deterministic reproduction of original provider exit on SDK UNAVAILABLE.

Only the SDK boundary/control listener are substituted; execute actual baseline
main source. Live KUKSA/MQTT recovery is separately checked by live_check.py.
"""
import json
import pathlib
import subprocess
import sys
import types
from kuksa_client.grpc import VSSClientError

root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root/'vehicle-simulator/src'))
baseline = 'f33e7cbbb4968fec28d2d5acf4f10df246fa9fba'
source = subprocess.check_output(['git','show',baseline+':vehicle-simulator/src/main.py'],text=True,cwd=root)
module = types.ModuleType('baseline_provider')
exec(compile(source,'baseline:vehicle-simulator/src/main.py','exec'),module.__dict__)
closed=[]
class Client:
    def __enter__(self): return self
    def __exit__(self,*_): closed.append('client')
    def set_current_values(self,*_,**__):
        raise VSSClientError({'code':14,'reason':'unavailable'},[])
class Control:
    def shutdown(self): closed.append('control shutdown')
    def server_close(self): closed.append('control close')
module.get_client = Client
module.start_control_server = lambda **_: Control()
try:
    module.main()
except VSSClientError as error:
    assert error.error['code']==14
    assert closed==['client','control shutdown','control close']
    print(json.dumps({'baseline':baseline,'reproduced':True,'observation':'UNAVAILABLE escapes main; process would exit without managed restart',
                      'boundary':'MOCK SDK UNAVAILABLE; actual baseline provider main/controller/generator', 'cleanup':closed}))
else:
    raise AssertionError('baseline unexpectedly recovered')
