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