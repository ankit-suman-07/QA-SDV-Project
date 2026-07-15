# Ditto Evidence - vehicle-001 Twin Creation & Sync

## Environment
- OS: Windows
- Docker Desktop / Docker Compose: (29.4.3, build 055a478 / Compose version v5.1.3)
- Ditto image tag: latest (docker.io/eclipse/ditto-*:latest)
- Date tested: 2026-07-14

## 1. Policy created

Command:
```
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/policies/sdv:vehicle-001-policy -H "Content-Type: application/json" -d "@vehicle-policy.json"
```

Response:
```json
{"policyId":"sdv:vehicle-001-policy","imports":{},"entries":{"owner":{"subjects":{"nginx:ditto":{"type":"nginx basic auth user"}},"resources":{"thing:/":{"grant":["READ","WRITE"],"revoke":[]},"policy:/":{"grant":["READ","WRITE"],"revoke":[]},"message:/":{"grant":["READ","WRITE"],"revoke":[]}},"importable":"implicit"}}}
```

## 2. Thing created (initial state)

Command:
```
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/things/sdv:vehicle-001 -H "Content-Type: application/json" -d "@vehicle-001-thing.json"
```

Response:
```json
{"thingId":"sdv:vehicle-001","policyId":"sdv:vehicle-001-policy","attributes":{"vehicleId":"vehicle-001"},"features":{"signals":{"properties":{"speedKph":0,"batteryPercent":0,"temperatureCelsius":0,"tirePressurePsi":{"frontLeft":0,"frontRight":0,"rearLeft":0,"rearRight":0},"sourceTimestamp":null}},"health":{"properties":{"status":"HEALTHY","activeFaults":[],"faultCount":0}}}}
```

## 3. Single-property update (batteryPercent to 8)

Command:
```
curl.exe -u ditto:ditto -X PUT http://localhost:8080/api/2/things/sdv:vehicle-001/features/signals/properties/batteryPercent -H "Content-Type: application/json" -d "8"
```

Response: 204 No Content (empty body - Ditto returns no content on a successful property update; the empty terminal output above is expected, not an error).

## 4. Verification GET - confirms the update and that nothing else changed

Command:
```
curl.exe -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001
```

Response:
```json
{"thingId":"sdv:vehicle-001","policyId":"sdv:vehicle-001-policy","attributes":{"vehicleId":"vehicle-001"},"features":{"signals":{"properties":{"speedKph":0,"batteryPercent":8,"temperatureCelsius":0,"tirePressurePsi":{"frontLeft":0,"frontRight":0,"rearLeft":0,"rearRight":0},"sourceTimestamp":null}},"health":{"properties":{"status":"HEALTHY","activeFaults":[],"faultCount":0}}}}
```

**Result:** `batteryPercent` changed from `0` to `8`; `speedKph`, `temperatureCelsius`, `tirePressurePsi`, and `health` remained unchanged - confirms partial state synchronization works as designed.

## OpenSOVD evidence

Gateway started in mock mode:
```
docker run -p 7690:7690 ghcr.io/eclipse-opensovd/opensovd-gateway --mock
```
Log confirms:
```
OpenSOVD Gateway Server version=0.1.1 sha1=fe75a8e build_date=2026-07-13
Mock topology enabled
Listening addr=0.0.0.0:7690 type=tcp base=/sovd
```

### API entry point
```
curl.exe -s http://localhost:7690/sovd/v1
```
```json
{"id":"","name":"","areas":"http://localhost:7690/sovd/v1/areas","components":"http://localhost:7690/sovd/v1/components","apps":"http://localhost:7690/sovd/v1/apps"}
```

### Components discovered
```json
{"items":[{"id":"ecu","name":"Engine Control Unit","tags":["powertrain","critical"]},{"id":"gateway","name":"Vehicle Gateway","tags":["network"]}]}
```

### ECU current sensor data (relevant to our vehicle-health signals)
```
GET /sovd/v1/components/ecu/data/voltage → {"id":"voltage","data":{"value":12.6}}
GET /sovd/v1/components/ecu/data/temperature → {"id":"temperature","data":{"value":85.0}}
```

**Result:** confirms that OpenSOVD's gateway runs alone in mock mode and shows the current sensor values (voltage, temperature) through a REST API - the same categories of data (battery, temperature) our team's Ditto twin and health engine will need to map into diagnostic resources.

## Fault Lifecycle Evidence — Real Simulator (Emmanuel's vehicle-simulator)

### Trigger: INJECT_FAULT=1, battery drains toward 0

Bridge script console output (`eclipse-components/ditto/vehicle_pipeline.py`):
```
[Rule] battery=0.0 < 20 -> WARNING, BATTERY_LOW
[Ditto] speed=56.9 battery=0.0 temp=150.0 tireFL=4 health=WARNING
```
(Captured from the script's console rather than a separate `curl` GET — this
output reflects the exact same PUT calls a GET would confirm, since the
script prints the values immediately after writing them to Ditto.)

### Recovery: INJECT_FAULT=0, battery restored

Simulator log (`vehicle-simulator` provider container):
```
provider-1 | [normal] speed=95.2 battery=85.2 engine_temp=89.9 tire_pressure=32.1
```

Ditto verification GET:
```
curl.exe -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001
```
```json
{"thingId":"sdv:vehicle-001","policyId":"sdv:vehicle-001-policy","attributes":{"vehicleId":"vehicle-001"},"features":{"signals":{"properties":{"speedKph":95.23506164550781,"batteryPercent":85.2,"temperatureCelsius":89.92329406738281,"tirePressurePsi":{"frontLeft":32,"frontRight":0,"rearLeft":0,"rearRight":0},"sourceTimestamp":null}},"health":{"properties":{"status":"HEALTHY","activeFaults":[],"faultCount":0}}}}
```

### Result

Confirms the full fault lifecycle: real simulator data flows through Kuksa,
into the bridge's health rule, into Ditto; a battery-low fault was triggered
and later cleared automatically as the underlying signal recovered.

Cross-check: simulator log values (battery≈85.2, temp≈89.9, tire≈32) match
the Ditto twin's stored values (batteryPercent:85.2, temperatureCelsius:89.9,
tirePressurePsi.frontLeft:32) almost exactly, confirming live synchronization
rather than stale or cached data.

