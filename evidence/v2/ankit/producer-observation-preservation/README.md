# V2 producer observation preservation

[Task 2 PR #54](https://github.com/ankit-suman-07/QA-SDV-Project/pull/54) was open at fetched head `734c358c87f00c52d108d021dea56237418ab9f5`, the same producer revision tested in [PR #62](../retained-fault-validation/README.md). Producer fix tested at `6ae3bdef5066cb755a962a8d9873c0f5be78e02b`. Backend tested at PR #62 head `f705e457df068d5210c314e0be74bbd4725f1461`.

## Reproduction and verification

- Reran the prior offline probe with `PYTHONPATH="$probe_dir/velocitas-app/app/src" python "$probe_dir/probe.py"` after exporting the fetched producer source. Exit 1. With an accepted 3 m obstruction at 0 ms and a 20 m sample at 500 ms, both ordered 31 m inputs at 1,000 ms (UTC ages +5,001 and −1,001 ms) returned new observation fields despite resetting recovery.
- `python -m pytest -q velocitas-app/app/tests/test_v2_health_recovery.py -k clock_rejection` before the fix exited 1 with four preservation failures. The same selection after the fix exited 0 with four passes before the no-prior-observation test was added.
- `python -m pytest -q velocitas-app/app/tests/test_v2_health_recovery.py` on the fix exited 0 with 24 passes (Python 3.12). It verifies all accepted observation fields, the unchanged watermark and accepted-ID ledger, and fresh recovery starting at 1,000 ms, retaining the obstruction at 2,999 ms and clearing at 3,000 ms. Existing replay, isolation, gap and silence tests passed. The broader app command `python -m pytest -q velocitas-app/app/tests -m "not integration" --tb=short` stalled with no progress near the end and was interrupted (exit 130).
- In a detached #62 worktree, exported the fixed producer module and ran `PYTHONPATH=velocitas-app/app/src python compat_probe.py`. The temporary probe wrote six whole-Thing responses from actual producer output, using C5's event ID rename. It used separate clocks and emitted the reset, fresh recovery at 1,999 ms into the new window, and clear at 2,000 ms for each rejection. From `backend/`, `bash ./mvnw --batch-mode --no-transfer-progress '-Dtest=V2FleetProjectionTest#projectsActualProducerOutputAfterBothClockRejections' test` exited 0 (one temporary test covering all six responses, Corretto 21.0.13). The test drove the existing HTTP substitute and vehicle API and checked the accepted identity, timestamp, distance, health, faults and recovery fields.

The C4/C5 identity trace placed the defect before the producer updated its observation and replay state. The red-green regressions and revision-to-check record applied the repository TDD, systematic-debugging and verification workflows.

## Pending boundary

The offline check fed snapshots directly to the backend HTTP substitute. Live MQTT and ingress still need to demonstrate that a reset snapshot with the same accepted identity reaches real Ditto without advancing the C5 watermark or appending a new observation. No teammate approval is recorded. Recommended order after review is #62 into main, the producer fix into #54, then #54 into main.
