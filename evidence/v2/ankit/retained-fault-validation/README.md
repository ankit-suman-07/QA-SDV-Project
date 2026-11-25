# V2 retained-fault validation

Ankit Suman approved the [C4/C5 clarification](../../../../docs/v2-interface-contracts.md#v2-c4-signals-health-and-recovery) on November 21, 2026. Bayan's review remains pending.

## Backend snapshot verification

Base `6651d610296112381a3efe19890818454f2bad4f`. Verified backend commit `e5d75c5e9c89fb325a092c77be9c16413eb32953`. Commands ran from `backend/` with Corretto 21.0.13, a fixed clock and loopback HTTP substitutes.

| Command | Result |
| --- | --- |
| `bash ./mvnw --batch-mode --no-transfer-progress -Dtest=V2FleetProjectionTest test` before the fix, with the commit's tests applied to the base | Exit 1. One of 10 tests failed: expected AVAILABLE, got UNAVAILABLE on the retained-fault snapshot. |
| Same focused command after the fix | Exit 0. 10 passed. |
| `bash ./mvnw --batch-mode --no-transfer-progress clean verify` | Exit 0. 227 passed, zero skipped. |

The test starts at a substituted Ditto whole-Thing read and checks the vehicle API returns 20 m, the original event ID and UTC source timestamp, CRITICAL with LIDAR_OBSTRUCTION, and NONE with a null recovery start. Negative cases cover a fault paired with HEALTHY, a reset with a non-null start, sensor failure with 20 m and no recovery window, an unknown fault, and CRITICAL obstruction at the warning distance. Existing freshness boundary tests also ran. The first focused attempts could not reach the assertions until the local JDK 21 was selected and the sandbox allowed loopback bind.

## Producer and joined verification

Exported Bayan's branch at `734c358c87f00c52d108d021dea56237418ab9f5` with `git archive` into a temporary directory, using its app source, test module and V2 fixtures. With Python 3.12, `python -m pytest -q velocitas-app/app/tests/test_v2_health_recovery.py -k 'two_seconds_of_fresh or completion_requires_fresh'` from that export exited 0 (7 passed, 16 deselected).

A temporary offline probe (`PYTHONPATH="$producer_dir/velocitas-app/app/src" python "$producer_dir/probe.py"`) called the same state machine with separate fake UTC and monotonic clocks for each case. It delivered 3 m at source/receipt 0 ms, 20 m at 500 ms, then 31 m at 1000 ms with UTC age +5001 ms or −1001 ms. Both cases reset to CRITICAL/NONE with a null start but returned 31 m, the new event ID and the new source time. The preservation check exited 1. In both cases, fresh 20 m samples at 1500, 2000, 2500, 3000, 3499 and 3500 ms verified restart at 1500 ms, an active fault at 1999 ms into the new window, and clearing at 2000 ms.

Joined check pending with Bayan's producer and ingress: confirm both rejected inputs leave 20 m and the same accepted identity, timestamp and watermark in the twin while resetting recovery. Then verify the backend projects the retained fault through the new full two-second window. The offline export exercised no MQTT, real Ditto or CARLA.

The repository TDD workflow established the failing assertion before the change. The customized systematic-debugging identity trace isolated the boundary at the twin reader, and Ankit's verification-before-completion v1.0.0 mapped the contract to specific assertions and revisions (ENGR5510G Topic 2, verification and traceability). The producer probe exposed a remaining identity mismatch independently of the backend result.
