# Iteration 2 - Ditto Validation Evidence

## 01-verifier-detects-missing-fields.png

Command: python ditto\scripts\verify-vehicle-state.py

Output: FAILED: sdv:vehicle-001 validation errors:

    Missing signal field: sourceTimestamp
    Missing health field: processedTimestamp


Context: run against the live vehicle-001 twin, unchanged since before
processedTimestamp was added to the schema. Correctly detects two real
gaps, sourceTimestamp was never populated by the bridge, and
processedTimestamp doesn't exist yet on the live twin (schema file
updated, but nothing has re-PUT the Thing since). Confirms the verifier's
missing-field detection works end-to-end against real Ditto responses,
not just mocked data.

## 02-verifier-tests-passing.png

Command: python -m pytest tests/test_verify_vehicle_state.py -v

Output: 10 passed in 0.11s

Context: mocked unit tests covering the verifier's core behavior. Valid
state passes, missing signal/tire/health fields fail with the correct
field named in the error, invalid or inconsistent health status fails,
stale timestamps are detected, Ditto being unreachable is handled
gracefully, and the contract's staleness formula (max(3x interval, 5s))
is verified directly, including the 5-second floor at fast publication
rates.

## 03-regression-warning-battery-low.png

Commands:

curl.exe -u ditto:ditto -X PUT .../health/properties/status -d "@status.json"
curl.exe -u ditto:ditto -X PUT .../health/properties/activeFaults -d "@active-faults.json"
curl.exe -u ditto:ditto http://localhost:8080/api/2/things/sdv:vehicle-001
python ditto\scripts\verify-vehicle-state.py

Output: twin shows batteryPercent:15, status:"WARNING",
activeFaults:["BATTERY_LOW"], faultCount:1. Verifier reports only the
pre-existing sourceTimestamp/processedTimestamp gaps — no complaint about
the WARNING/activeFaults relationship, confirming validate_health()
correctly accepts this as a valid fault state.

Context: manually driven via Ditto's REST API rather than the bridge,
since the bridge on main currently has an unresolved import bug
and a Kuksa port mismatch.
Both flagged to the team; this test validates Ditto's own behavior
independently of that blocker.

## 04-regression-healthy-recovery.png

Commands: set batteryPercent to 27, health.status to "HEALTHY",
activeFaults to [], faultCount to 0; verified via GET and the verifier.

Output: twin shows batteryPercent:27, status:"HEALTHY", activeFaults:[],
faultCount:0 - fully consistent. Verifier again reports only the
pre-existing timestamp gaps, no health-consistency complaints.

Context: completes the regression pair with 03 - confirms Ditto correctly
represents both the WARNING/BATTERY_LOW state and its recovery to
HEALTHY, independent of the currently-blocked bridge.

## 05-tests-with-faultcount-check.png

All 11 mocked tests passing, including the new
test_fault_count_mismatch_fails, added after discovering a real bug (see
06) while running the fully-integrated bridge.

## 06-verifier-catches-faultcount-bug.png

Verifier run against the live twin after running the real, merged bridge
(Benjamin's transport relocation + Emmanuel's simulator, both merged to
main). Correctly detects a genuine bug: the bridge writes activeFaults
but never updates faultCount, leaving it stale. Contract (docs/04
Section 3) requires faultCount == activeFaults.length. Flagged to Ankit
as a bridge bug, separate from the two pre-existing timestamp gaps.