# Iteration 2 — OpenSOVD Mapping Evidence

## 07-opensovd-confirmed-read-only.png

Commands: curl.exe -s -X PUT http://localhost:7690/sovd/v1/components/ecu/data/voltage -H "Content-Type: application/json" -d "@voltage-test.json"

Output: `{"error_code":"error-response","message":"read only"}`

Context: resolves the open question from the Iteration 1 research doc -
confirmed via direct testing (correct request shape, ruled out earlier
JSON-quoting false positives) that OpenSOVD's mock gateway data resources
are read-only. This is why fault mapping is implemented as a standalone
adapter (fault_mapper.py) rather than writing into the gateway directly.

## 08-all-four-components-integrated.png

All four components running simultaneously: Kuksa (real simulator, fault
mode) -> uProtocol (event IDs, publish/receive timestamps, Benjamin's
relocated transport) -> health rule -> Ditto (WARNING/BATTERY_LOW) ->
OpenSOVD fault mapper (opensovd/scripts/map-active-faults.py --watch,
independently polling the same Ditto twin).

Mapper correctly escalated severity to CRITICAL since battery was below
the contract's 10% critical threshold - a distinction the bridge's own
simpler rule doesn't make, only fault_mapper.py does.

Context: proves the full Kuksa-Ditto-OpenSOVD chain works end-to-end
without modifying Ankit's or Benjamin's in-progress files - the mapper
reads Ditto independently rather than being wired into the bridge
directly, avoiding merge conflicts with their ongoing work.