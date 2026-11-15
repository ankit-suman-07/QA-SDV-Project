# Phase V1 engineering and release readiness — November 15, 2026

## Stop checkpoint requested after d8c1f40

Final combined verification is **PENDING** after the bounded-cleanup correction
`d8c1f4048522da3e79a81e6ee5919017b941b00d`. It prevents a stalled client join from
hanging Python's default-executor shutdown, while retaining a nonzero incomplete-
cleanup result. Targeted app verification passes 214 tests with two explicit skips;
the stalled-join subprocess regression now terminates within its budget.

The complete combined run recorded below tested `6a6badc`, **before d8c1f40**.
Its results remain valid historical evidence at that SHA and must not be relabelled
as final combined verification of d8c1f40. The final handoff records the updated
candidate's actual inclusion and remaining smoke/CI checks. No further enhancement
or full integration run was started after the user's stop-checkpoint instruction.


**UNMERGED INTEGRATION CANDIDATE: engineering verification PASS; full V1 acceptance
and release approval remain pending.** Report/video writing, recording and submission
were excluded from this work and remain pending unless separately evidenced. No PR
merge, owner approval, release tag or publication was performed.

## Baseline, branches and exact revisions

Original checkout was clean on merged PR #43 branch at
`4bead79bf2e2837ba58bb9e9a3e73f83d3cc5135`. Fetched origin, switched main and ran
`git pull --ff-only`: main fast-forwarded to `6a965bbaf5966d096e18c57058cfdbee6185ee2e`.
No local changes were discarded, no reset/force-push, no old temporary environment
used. No applicable AGENTS.md was found. All new work belongs to Ankit under current
SOURCE-OF-TRUTH. Historical teammate authorship is preserved.

| Independent fix | Exact reviewed input | Draft PR | Verification |
|---|---|---|---|
| F03 safe feature initialization | `cd89160ccdd1b65901d365e46431b1af73ea1efc` | [#44](https://github.com/ankit-suman-07/QA-SDV-Project/pull/44) | [Red/green, real resources, restart](../../evidence/v1/ditto-initialization-20261115/README.md) |
| F04 HTTP compatibility | `0a010eb30e81a63595638b88f81096dc561c5b28` | [#45](https://github.com/ankit-suman-07/QA-SDV-Project/pull/45) | [Actual Spring/JDK/nginx/real Ditto](../../evidence/v1/ditto-http-20261115/README.md) |
| Graceful application shutdown | `9c899c823cc71c0431319c91d6bd79e06ad71564` | [#46](https://github.com/ankit-suman-07/QA-SDV-Project/pull/46) | [Five Docker cases/three Kanto cycles](../../evidence/v1/app-shutdown-20261115/README.md) |

All three branches start independently from the same main baseline. At
[exact-head inspection](../../evidence/v1/release-readiness-20261115/exact-head-pr-status.json),
all eight checks passed on each fix head. No human approvals are inferred from CI.

Temporary candidate branch: `ankit/test/v1-release-candidate-20261115`, persistent
worktree `$HOME/.local/share/qa-sdv-v1/worktrees/release-candidate`.
Actual tested candidate: `6a6badc207e3cf43f6bba1d1c9584538d6450fed`.
Evidence checkpoint/base of this documentation branch:
`021730d85a39cc59e15a967b55414437bee15f12`.
[Included commits and assembly](../../evidence/v1/release-candidate-20261115/included-commits.json).
Only an appended README conflict needed resolution; both independent follow-ups
were retained. No implementation conflict or unrelated implementation changes.
This candidate branch is evidence scaffolding, not a PR to merge into main.

Documentation branch `ankit/docs/v1-release-readiness` explicitly stacks on that
candidate and targets it, so its initial PR diff contains only documentation and
readiness evidence. This is not silently imported implementation in an independent PR.

## Findings and affected boundaries

**F03 corrected on candidate:** authenticated successful Thing read establishes
identity/absence. First validated real observation creates only the absent feature
with If-None-Match. Existing updates retain the narrower properties-only permission
boundary and use properties GET ETag/If-Match. Legacy/features/context/watermarks
are preserved. Failed read/auth/transport, missing Thing, conflict or uncertain
commit never grants overwrite permission or advances persistence ACK semantics.
Fresh real namespaces and a fresh candidate database verify initialization/restart.

**F04 corrected on candidate:** Spring7.0.8's JDK request implementation adds gzip
and deflate as separate values. Java21 emits separate fields, nginx forwards them,
and Ditto rejects the duplicate name. Explicit one-field `gzip, deflate` defaults
at both Ditto clients preserve decompression, authentication/TLS, bounds/timeouts.
Actual baseline400 and fixed individual reads/fleet writes pass through original
nginx; no normalization workaround remains in candidate deployment.

**Shutdown corrected on candidate:** signal-driven orderly cancellation, bounded
I/O draining and explicit owned SDK/KUKSA/MQTT closes replace abrupt LOOP.stop.
Initial failing actual-image attempt and Paho already-stopped semantics are retained.
Final five actual Docker cases and three actual Kanto managed stop/start cycles
all exit0; old PIDs absent, no overlapping publisher. Four complete-shutdown log
entries replace the historical RuntimeError. No general reliability rate inferred.

## Technical readiness by acceptance criterion

| Criterion | Latest technical evidence | Remaining acceptance work |
|---|---|---|
| V1-01 | Two actual providers/KUKSA/apps with distinct IDs/topics PASS on candidate; merged #38/#39 provider recovery evidence reused | Review/merge candidate fixes and confirm final main |
| V1-02 | Clean initialization from real observations; invalid/unknown/mismatched/equal/late/duplicate invariance, watermark restart and denied-write recovery PASS | Production principal/policy approval; final main check |
| V1-03 | Five backend-routed faults and five clears reach all six observed boundaries; 001 isolated | Human review; final main smoke |
| V1-04 | Real twin/API source aging/null, bounded client reads and compatibility PASS | Approve current freshness/clock assumptions |
| V1-05 | Candidate Python540 +386 subtests, Java209, frontend7 and Compose checks PASS; all fix-head CI eight checks PASS | Two Python skips/nine deselections explicit; final merged-head CI required |
| V1-06 | Actual task/source/test traceability and upstream investigation recorded | Human review; historical installed/invocation provenance not inferred |
| V1-07 | Reproduction, candidate evidence and engineering contribution record prepared | Reviewed final SHA/tag decision, report/video and submission remain pending/excluded |
| V1-08 | Real individual twins, sole Spring fleet writer, materialized summary/API/dashboard agree through five trials; denial recovery PASS | Production writer permissions/approval; final main smoke |
| V1-09 | [Merged #43 same-device managed restart PASS](../../evidence/v1/kanto-live-20261115T142159Z/README.md); [affected shutdown three-cycle recheck PASS](../../evidence/v1/shutdown-kanto-live-20261115T152137Z/independent-review.json) | Exact B5 LAN wording decision below; no remote LAN/crash-auto-restart claim |

[Candidate summary](../../evidence/v1/release-candidate-20261115/README.md),
[live results](../../evidence/v1/release-candidate-live-20261115T152908Z/results.json),
[clean pre-publisher state](../../evidence/v1/release-candidate-live-20261115T152908Z/clean-provisioned-before-edge.json),
[raw measurements/statistics](../../evidence/v1/release-candidate-live-20261115T152908Z/statistics.json),
[dashboard screenshot](../../evidence/v1/release-candidate-live-20261115T152908Z/dashboard-final.png).
Prepared-deployment historical success remains preserved; the new candidate starts
with V1 absent and uses original nginx, so these clean boundaries are now separately
verified. No historical failed result or exit was changed.

Measurements are command-to-observed completion, including scenario progression,
polling and browser work. Sources/observer share one kernel clock with recorded NTP;
no guaranteed error bound or cross-host measurement exists. Optional command context
can be absent, so isolated chronology is not event-level causal command correlation.
No matched MVP speedup, production delivery probability or scalability claim.

## Concrete decisions awaiting humans

No decision in this table is approved by this document. Record named reviewers,
chosen option, rationale and authoritative revision; retain proposed C1–C10 status
until affected-owner review is actually evidenced.

| Decision | Proposed review package | Required disposition |
|---|---|---|
| B5 LAN wording vs V1-09 | User-directed same-device managed restart and explicit V1-09 outcome passed. B5 row still requests main-host LAN connectivity | Explicitly accept same-device evidence for V1-09 and classify remote LAN as outstanding supplementary work, or retain LAN as a gate and schedule an additional real test. Do not infer either approval |
| Authentication/permissions | Dedicated provisioning authority; ingress read identity/watermark + conditional feature creation/property writes; backend read-only individuals; sole Spring writer write-only fleet scope | Approve concrete subject IDs/resource grants, CA/TLS and deployment secret handling. The local sample shares one legitimate subject and proves no production role separation |
| Freshness/defaults | Existing stale5s, unavailable30s, future tolerance1s verified without changing defaults; truthful missing/null preserved | Approve or revise with owner-reviewed tests; configured defaults are not accepted requirements by themselves |
| Timing budgets | Retained five-trial distributions and bounded request timeouts, separate dispatch acknowledgements | Choose product budgets and measurement boundary explicitly; current timeouts/medians are not SLA approval |
| Clock assumptions | Same-host kernel/NTP evidence; no guaranteed skew bound or LAN synchronization proof | Accept stated same-host qualification or require measured cross-host error bounds before broader timing claims |
| C1–C10 and skill review | Exact schema/identity/unit/context behavior and PR traceability; provenance lookup below | Obtain actual affected-owner and team-member review; no approval on anyone's behalf |
| Release/submission | Engineering candidate passing, unmerged; all PRs draft | Decide final main SHA after reviewed merges/checks. Report/video creation/recording/submission remain outside this work and pending |

## Merge/update procedure — humans only

Suggested review order: #44, #45, #46, then documentation. Fixes are independent;
this is an integration sequence, not a claim that #45/#46 depend on unmerged #44.
All remain based on main. Follow repository review and merge strategy (squash is
recommended); do not merge the temporary candidate branch.

After each approved fix merges, update the next independent branch by merging the
new origin/main, resolve any README append conflict by retaining both sections,
rerun affected checks and push normally. Do not rebase/force-push to manufacture a
clean history. Retain expected-head guards when merging remotely.

After all fixes merge, merge current origin/main into the documentation branch,
confirm its implementation tree equals reviewed main, then retarget its existing PR
from candidate to main. Example **future commands, not executed here**:

```bash
git fetch origin
git switch ankit/docs/v1-release-readiness
git merge origin/main
# Resolve real conflicts, preserve both follow-ups, run checks, commit if needed.
git diff origin/main -- ditto/v1_writer.py velocitas-app/app/src backend/src/main
# This implementation diff must be empty before retargeting.
git push origin ankit/docs/v1-release-readiness
gh pr edit DOCUMENTATION_PR_NUMBER --base main
```

The documentation can retain exact unmerged-candidate evidence as historical evidence;
new final-main evidence must have its own actual revision, not relabelled old results.

## Exact final-main checks still required

After humans merge approved PRs, use a clean persistent checkout/worktree; preserve
any local changes and run fetch/switch main/pull --ff-only as usual. Record the new
full SHA, clean/dirty state and included fixes. Never call the candidate verified main.
Use persistent Java21/Python3.12/Node22 under `$HOME/.local/share/qa-sdv-v1/runtime`.

```bash
# From clean final-main repository root; secure local Ditto environment already loaded.
export RUNTIME="$HOME/.local/share/qa-sdv-v1/runtime"
export PATH="$RUNTIME/jdk21/bin:$RUNTIME/node22/bin:$PATH"
export JAVA_HOME="$RUNTIME/jdk21"
(cd backend && bash ./mvnw --batch-mode --no-transfer-progress clean verify)
"$RUNTIME/venv-3.12/bin/python" -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated uprotocol/proto/common.proto uprotocol/proto/health_status.proto uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto uprotocol/proto/vehicle_diagnostic.proto
"$RUNTIME/venv-3.12/bin/python" -B -m pytest -q -ra -p no:cacheprovider -m 'not integration'
(cd frontend && npm test)
docker compose -f vehicle-simulator/docker-compose.yml config --quiet
docker compose -f vehicle-simulator/docker-compose.v1.yml config --quiet
git diff --check
```

Ensure generated directory exists and install documented dependencies first if needed.
Run a fresh isolated clean-init/header check and affected lifecycle restart smoke on
final main; retain original #43 and candidate results as prior evidence. Inspect
exact final-main CI, including original baseline and real two-vehicle workflow.
Rerun broader fault/outage trials only if merge/source changes, failures or concerns
justify them; do not reset original shared twins/volumes. New lifecycle pilot names
and newly built/pinned final-main images are required: do not rerun create-only
old observers against retained container names or label old images with a new SHA.

A Phase V1 acceptance/release tag is **not justified solely by these merges/checks**:
human decisions, review, V1-06 provenance qualification and V1-07 deliverables remain.
No tag or release has been created or authorized for automatic execution.

## Contributions, provenance and service handoff

Bayan's #30/#31/#32 individual-ingress/twin/Kanto preparation and Emmanuel's #33/#37
edge/scenario contributions remain historical authorship. Ankit's #34/#35/#36
backend/API/fleet work, #38/#39 remediation, #41/#42/#43 verification, and new
#44/#45/#46 remediation/candidate/readiness are recorded as Ankit's work. No teammate
is assigned remaining V1 work by retaining historical attribution.

[Skill provenance investigation](../../evidence/v1/release-readiness-20261115/skill-provenance-investigation.json)
resolves reported Superpowers v6.4.2 to commit
`8ca22dba9a94f28898bbce59f2537ff4d87c747d`. Current repository TDD and verification
copies match exactly; debugging differs only in two secret-redaction example lines,
with [exact diff](../../evidence/v1/release-readiness-20261115/systematic-debugging-provenance.diff)
and [MIT license](../../evidence/v1/release-readiness-20261115/superpowers-v6.4.2-LICENSE.txt).
This lookup establishes current reference/content comparison, not historical E1/E2
installed bytes or invocation proofs. Actual inherited repository debugging copy
was used, not falsely labelled byte-identical original. Missing supporting skill
files remain unclaimed; owner/rubric disposition remains pending.

[Final workload inventory](../../evidence/v1/release-candidate-20261115/final-workloads.json):
original edge/app-001/real Ditto/one ingress and dedicated Kanto daemon remain running;
Docker app-002, both retained Kanto pilots and owned shutdown smoke containers are
stopped. Candidate projects/observers removed/stopped without volume deletion.
Separate Part B stack stopped with database retained; some third-party JVM stops
reached timeout/exit137, preserved rather than described as clean exits. No MongoDB
volume, original policy/twin, unrelated workload or unused docker_default network
was removed. Old failed test containers and immutable evidence retained.


## Historical artifact qualification

[Link audit](../../evidence/v1/release-readiness-20261115/relative-links.json)
finds ten pre-existing absent `.log` targets in the historical implementation
findings. Matching JSON command metadata exists, but references output filenames
rather than containing the missing raw output. [Git history check](../../evidence/v1/release-readiness-20261115/historical-artifact-gaps.json)
found no tracked versions of those paths. The earlier MVP console-log provenance
gap also remains. Historical references/results were preserved; no replacement
historical logs or pins were invented. New fix/candidate raw outputs, snapshots,
images/source identities, screenshots and hashes are tracked and independently
available. Human rubric/provenance disposition or original external artifacts
remain necessary where those older records are required.
