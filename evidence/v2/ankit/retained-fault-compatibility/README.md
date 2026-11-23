# V2 retained-fault compatibility

Fetched `origin/main` at `6651d610296112381a3efe19890818454f2bad4f`. GitHub still reported #62 open, so this branch includes its existing commits through `f705e457df068d5210c314e0be74bbd4725f1461` as a prerequisite. The backend change was tested at `866972c2e999b300f26fad21e08093aa00ffbccc`. Bayan's #54 producer was tested at fetched head `e594c5c3f25fd4a52191072e2f8a8180ff70b4aa`.

## Producer and backend checks

- Exported #54's `v2_health_recovery.py` and `v1_event.py` with `git archive`. Ran `PYTHONPATH=/tmp/sdv-retained-types/velocitas-app/app/src python /tmp/sdv-retained-types/probe.py` (exit 0). The temporary probe started each case with an 8 m obstruction or unavailable sensor at 0 ms, then accepted 20 m at 500 ms and delivered 31 m at source/receipt 1,000 ms with UTC age +5,001 or −1,001 ms. It checked the accepted observation fields, NONE/null reset and retained fault. Fresh 20 m samples at 1,000, 1,500, 2,000, 2,500, 2,999 and 3,000 ms restarted recovery, retained the fault at 1,999 ms into the new window and cleared at 2,000 ms.
- Stored the reset, 1,999 ms and 2,000 ms producer snapshots for each case in [the backend fixture](../../../../tests/fixtures/v2/twins/retained-fault-resets.json), using C5's `eventId` to `lastEventId` mapping. The backend exercised all 12 snapshots via the existing loopback Ditto response and vehicle API, with the backend clock fixed at each accepted source time.
- From `backend/` with Corretto 21, `bash ./mvnw --batch-mode --no-transfer-progress -Dtest=V2FleetProjectionTest test` on #62 plus the new tests exited 1. The four resets returned UNAVAILABLE instead of AVAILABLE. After the fix, the same command exited 0 with 16 passes, including contradictory health/fault pairs, an invalid reset start and a sensor fault at an obstruction distance. The red-green result and the observation identity trace applied the repository TDD, debugging and verification workflows.
- `bash ./mvnw --batch-mode --no-transfer-progress clean verify` exited 0 with 233 passes and no skips. From the root, `python -m scripts.v2_dev.check` exited 0 with eight passes, 24 synthetic JSON fixtures and local contract links checked. `git diff --check` passed.

The [C4/C5 clarification](../../../../docs/v2-interface-contracts.md#v2-c4-signals-health-and-recovery) covers the existing supported fault pairs. No teammate review is recorded here. Live MQTT → ingress → real Ditto still needs to prove that the reset is applied with the same accepted observation and watermark. These checks used offline producer output and HTTP substitutes.

## Final review

Compared actual file contents against fetched `main` at `6651d610296112381a3efe19890818454f2bad4f`. #62 is open against main and its CRITICAL obstruction reset change is absent there. #64 retains #62's two existing prerequisite commits. #63 merged into the Task 2 branch at `e594c5c3f25fd4a52191072e2f8a8180ff70b4aa`. Both producer modules used by the offline probe are byte-identical at the latest #54 head `210f259f70dfcccd18adf7fa14fd1552babefe62`.

Reviewed #64 at `274d8d84db2edf651990219d0efbc3ce7c4d131b`. Above 10 m, the reader accepts only the three canonical singleton fault pairs or HEALTHY with an empty fault list and recovery NONE. Recovery timestamp and below-threshold validation still apply. The reader passes through the accepted identity and source timestamp. Watermark persistence remains an ingress responsibility. No code defects were found in this diff.

- From `backend/`, `bash ./mvnw --batch-mode --no-transfer-progress -Dtest=V2FleetProjectionTest,HttpVehicleTwinReaderTest test` exited 0 with 27 passes, using Corretto 21 and HTTP substitutes.
- In an isolated export of the latest #54 head, `python -m pytest -q velocitas-app/app/tests/test_v2_health_recovery.py` exited 0 with 26 passes.

After review, merge #62 first, update #64 against main if needed, then merge #64 before #54. If #62 lands via squash, compare the resulting patches and reconcile #64 with a normal branch update. Live MQTT, ingress and real Ditto still need to demonstrate that a same-identity reset is persisted without advancing the watermark.
