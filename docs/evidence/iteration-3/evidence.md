# Iteration 3 - Live End-to-End Correlated Fault Evidence

## 01-bridge-detects-correlated-fault.png

Real pipeline run: Emmanuel's simulator (fault mode triggered via
POST /api/v1/scenarios/actions), Kuksa, the merged bridge
(ditto/scripts/interim-kuksa-to-ditto-bridge.py), writing to Ditto.

[Rule] correlated cooling fault detected -> CRITICAL, COOLING_SYSTEM_FAILURE
[Ditto] speed=123.3 battery=66.5 temp=121.5 coolantPressure=100.0 tireFL=27.0 health=CRITICAL faults=['COOLING_SYSTEM_FAILURE']

Confirms the correlated rule fires only once both real signals (temperature,
coolant pressure) genuinely breach their thresholds together, and Ditto
correctly reflects CRITICAL with the fault active.

## 02-opensovd-mapper-live-output.png

python opensovd/scripts/map-active-faults.py

Output shows source: "activeFaultDetails" (not the "activeFaults" fallback),
confirming Ankit's bridge is writing complete fault detail records. All
fields real: observedValues from live Ditto signals, detectedAt from actual
detection time, traceId/actionId correctly threaded through from the
original scenario trigger (test-trace-001/test-action-001) all the way
through simulator -> bridge -> Ditto -> mapper.

## 03-verifier-passes-live-state.png

python ditto/scripts/verify-vehicle-state.py

OK: sdv:vehicle-001 is valid and fresh (<= 30.0s old)

Confirms the full Minimum End-to-End Acceptance Scenario from
docs/10-iteration-3-contract.md: real signals, correct correlated fault
detection, complete Ditto state, complete diagnostic mapping, all
independently verified as valid and fresh — no mocks anywhere in this run.