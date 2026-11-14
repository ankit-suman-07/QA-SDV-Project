import ast,json,sys
from pathlib import Path
from kuksa_client.grpc import VSSClient
vss=json.loads(Path('vehicle-simulator/config/vss-with-autonomous-sensors.json').read_text());node=vss['Vehicle']
for key in ['Chassis','Axle','Row1','Wheel','Left','Tire','Pressure']:node=node['children'][key]
assert node['unit']=='kPa'
with VSSClient('127.0.0.1',56556) as c:dp=c.get_current_values(['Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure'])['Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure']
tree=ast.parse(Path('ditto/scripts/interim-kuksa-to-ditto-bridge.py').read_text())
call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='publish_vehicle_status')
kw=next(k for k in call.keywords if k.arg=='tire_pressure_psi');expression=ast.unparse(kw.value)
assert expression=='float(tire_fl)'
result={'status':'CONFIRMED EXISTING UNIT-BOUNDARY DEFECT','VSSpath':'Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure','VSSunit':node['unit'],'liveKuksaNumericValue':dp.value,'sourceTimestamp':dp.timestamp.isoformat(),'legacyBridgeArgument':'tire_pressure_psi='+expression,'conversionPresentAtBoundary':False,'mapperUnit':'psi','interpretation':'The kPa-declared signal is relabelled psi without conversion. This does not establish the intended physical unit of the synthetic generator; owner decision/conversion is required. Live legacy bridge was NOT launched.'}
Path('evidence/v1/verification-20261114T051226Z/tire-unit-boundary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
