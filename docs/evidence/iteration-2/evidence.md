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