# V2 retained-fault integration handoff

| Input | Verified revision and contents |
| --- | --- |
| Main | `ddc7a687001d2963040dffdc090b5255c608533b`. #62 merged here. The reader and C4/C5 contract match #62 head `f705e457df068d5210c314e0be74bbd4725f1461` byte for byte. |
| Task 2 (#54) | `210f259f70dfcccd18adf7fa14fd1552babefe62`. #63 merged as `e594c5c3f25fd4a52191072e2f8a8180ff70b4aa`. The actual state-machine code matches #63 head `a6dd75564ea453a09d07d59290af9d70f6a8260b`. |
| #64 | Open at `9711a591576c3615f6c43285a654aaad074de494`. Its WARNING and CRITICAL sensor-failure acceptance is absent from main. |
| Offline combination | Detached at main. `git merge --no-commit --no-ff 210f259f70dfcccd18adf7fa14fd1552babefe62` exited 0. `git write-tree` returned `783409e54d6d35c7c5ba517a2d1810d959af950c` before adding temporary test inputs. No conflicts and no merge commit created. |

## Offline verification

- Used the existing #64 probe in the detached worktree, adding the 3 m CRITICAL obstruction alongside the 8 m WARNING and unavailable-sensor cases. `PYTHONPATH=velocitas-app/app/src python compat_probe.py` exited 0. Across all six fault/clock combinations, ordered 31 m samples at UTC ages +5,001 or −1,001 ms preserved the accepted 20 m observation and watermark and reset recovery to NONE/null. Fresh observations retained the fault at 1,999 ms and cleared at 2,000 ms into the new window.
- Exported the #64 projection test into the temporary worktree, added the two CRITICAL obstruction rows and supplied all 18 actual producer snapshots as test inputs using C5's `eventId` to `lastEventId` mapping. With Corretto 21, ran `bash ./mvnw --batch-mode --no-transfer-progress '-Dtest=V2FleetProjectionTest#projectsProducerSnapshotsAfterClockRejection' test` from `backend/`. Exit 1. Both CRITICAL obstruction sequences passed all stages. The four WARNING and CRITICAL sensor-failure sequences returned UNAVAILABLE at the reset stage. The checked-out production reader was identical to main.
- Reused #64's passing offline result for those four sequences. The backend and fixtures match tested commit `866972c2e999b300f26fad21e08093aa00ffbccc` and the two relevant producer modules match the producer revision used in that result. See [#64 verification](https://github.com/ankit-suman-07/QA-SDV-Project/blob/9711a591576c3615f6c43285a654aaad074de494/evidence/v2/ankit/retained-fault-compatibility/README.md).

## Handoff

- **Ankit, backend.** Main's [clear-distance validation](../../../../backend/src/main/java/com/ankit/sdv/backend/adapter/ditto/HttpVehicleTwinReader.java#L190) still rejects the two remaining reset fault types. #64 contains the reviewed remedy.
- **Bayan, Task 2 and ingress.** Pull the latest Task 2 branch and merge current main when ready. The tested combination had no conflicts. For live verification, arrange a V2 publisher and ingress with isolated MQTT topics, Ditto Things and watermark storage, and a backend pointed at that Ditto. Capture an accepted 20 m IN_PROGRESS snapshot and the same-identity NONE/null reset after each rejected sample. Verify the reset persists while the observation identity, source time and watermark stay fixed, then capture fresh recovery through the clear boundary. [C4/C5](../../../../docs/v2-interface-contracts.md#v2-c4-signals-health-and-recovery) describes independent status ordering and observation duplicate protection.
- **Live status.** `docker ps --format '{{.Names}} {{.Ports}}'` showed only the existing V1 prerequisite containers. The Task 2 merge adds the offline state machine, tests and evidence, leaving the V2 same-identity reset ingress path unverified. No V2 isolated runtime was ready. No live request or write was attempted and no expected state was seeded in Ditto.

The temporary HTTP substitute exercised backend projection only. The temporary test code and snapshots were kept outside the evidence branch.
