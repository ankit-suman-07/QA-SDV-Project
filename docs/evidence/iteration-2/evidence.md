# Iteration 2 — Ditto Validation Evidence

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