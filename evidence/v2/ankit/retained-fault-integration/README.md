# V2 retained-fault integration handoff

## Historical observations

| Input | Revision and contents at the time of the offline check |
| --- | --- |
| Main | `ddc7a687001d2963040dffdc090b5255c608533b`. #62 merged here. The reader and C4/C5 contract match #62 head `f705e457df068d5210c314e0be74bbd4725f1461` byte for byte. |
| Task 2 (#54) | `210f259f70dfcccd18adf7fa14fd1552babefe62`. #63 merged as `e594c5c3f25fd4a52191072e2f8a8180ff70b4aa`. The actual state-machine code matches #63 head `a6dd75564ea453a09d07d59290af9d70f6a8260b`. |
| #64 | Open at `9711a591576c3615f6c43285a654aaad074de494`. The tested main revision lacked its WARNING obstruction and CRITICAL sensor-failure fix. |
| Offline combination | Detached at main. `git merge --no-commit --no-ff 210f259f70dfcccd18adf7fa14fd1552babefe62` exited 0. `git write-tree` returned `783409e54d6d35c7c5ba517a2d1810d959af950c` before adding temporary test inputs. No conflicts and no merge commit created. |

## Offline verification

- Used the existing #64 probe in the detached worktree, adding the 3 m CRITICAL obstruction alongside the 8 m WARNING and unavailable-sensor cases. `PYTHONPATH=velocitas-app/app/src python compat_probe.py` exited 0. Across all six fault/clock combinations, ordered 31 m samples at UTC ages +5,001 or −1,001 ms preserved the accepted 20 m observation and watermark and reset recovery to NONE/null. Fresh observations retained the fault at 1,999 ms and cleared at 2,000 ms into the new window.
- Exported the #64 projection test into the temporary worktree, added the two CRITICAL obstruction rows and supplied all 18 actual producer snapshots as test inputs using C5's `eventId` to `lastEventId` mapping. With Corretto 21, ran `bash ./mvnw --batch-mode --no-transfer-progress '-Dtest=V2FleetProjectionTest#projectsProducerSnapshotsAfterClockRejection' test` from `backend/`. Exit 1. Both CRITICAL obstruction sequences passed all stages. The four WARNING and CRITICAL sensor-failure sequences returned UNAVAILABLE at the reset stage. The checked-out production reader was identical to main.
- Reused #64's passing offline result for those four sequences. The backend and fixtures match tested commit `866972c2e999b300f26fad21e08093aa00ffbccc` and the two relevant producer modules match the producer revision used in that result. See [#64 verification](https://github.com/ankit-suman-07/QA-SDV-Project/blob/9711a591576c3615f6c43285a654aaad074de494/evidence/v2/ankit/retained-fault-compatibility/README.md).

`docker ps --format '{{.Names}} {{.Ports}}'` showed only the existing V1 prerequisite containers. No V2 isolated runtime was ready. No live request or write was attempted and no expected state was seeded in Ditto.

The temporary HTTP substitute exercised backend projection only. The temporary test code and snapshots were kept outside the evidence branch.

## Resolution · 2026-11-25

GitHub reports all three PRs merged into `main`. Their recorded merge commits appear on the first-parent history of fetched `origin/main` at `be17612fcf4917942ee7fb381722cb682edda454`.

| PR | Main commit | Merged (UTC) | Scope |
| --- | --- | --- | --- |
| [#62](https://github.com/ankit-suman-07/QA-SDV-Project/pull/62) | `ddc7a687001d2963040dffdc090b5255c608533b` | 2026-11-22 | Resolves the historical CRITICAL obstruction reset rejection. [Offline verification](https://github.com/ankit-suman-07/QA-SDV-Project/blob/ddc7a687001d2963040dffdc090b5255c608533b/evidence/v2/ankit/retained-fault-validation/README.md) |
| [#64](https://github.com/ankit-suman-07/QA-SDV-Project/pull/64) | `05ed5a3c300f5463228683a00d18044709487fe8` | 2026-11-22 | Resolves the four remaining WARNING obstruction and CRITICAL sensor-failure backend rejections documented above. |
| [#54](https://github.com/ankit-suman-07/QA-SDV-Project/pull/54) | `be17612fcf4917942ee7fb381722cb682edda454` | 2026-11-25 | Lands Bayan’s offline health and recovery state machine. |

The backend reader at fetched main matches the #64 merge result. The failed results above remain tied to the historical test inputs and revisions. Passing results apply to the separately documented offline fix revisions. The fetched main revision was inspected for merge status and file contents only.

Bayan continues the agreed C5 schema, fingerprint, status ordering, durable replay and MQTT-to-Ditto verification work in [#68](https://github.com/ankit-suman-07/QA-SDV-Project/pull/68). Live same-observation recovery/status reset propagation, preservation of the accepted observation identity, source time and watermark, and subsequent recovery remain pending under #68. For live verification, use isolated MQTT topics, Ditto Things and watermark storage with the backend pointed at that Ditto. Capture the accepted 20 m IN_PROGRESS snapshot and the same-identity NONE/null reset after each rejected sample. Verify that the reset persists with the observation fields and watermark unchanged, then capture fresh recovery through the two-second clear boundary. [C4/C5](../../../../docs/v2-interface-contracts.md#v2-c4-signals-health-and-recovery)
