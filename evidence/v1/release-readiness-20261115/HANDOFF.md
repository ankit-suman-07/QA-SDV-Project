# PR47 post-merge preparation checkpoint — November 15, 2026

This current section supersedes merge/retarget instructions in the historical handoff.
PR44 merged5b485cb4f9aff8aae26ac615c8c208bd2c7bde9a;
PR45 merged0a4c5513d23db922e540e2323f0f2160cd33b227;
PR46 merged4afbbd8c11425a9e0e1701fea66b7ed13731abfe.
PR47 now targets main, normal merge used, no force-push. Backup reference:
backup/pr47-before-main-20261115 at9ea2652100ca2d5e02e101ba977df46a654d4c05.
PR48/candidate remains open/unmerged; do not merge or delete it here.

Fresh exact-main4afbbd8 verification:541 Python+386 subtests,209 Java,7 frontend,
both Compose configs, four selected real gates and three actual Kanto cycles PASS.
174 final healthy001 twin samples, clean stops exit0, exact fresh MQTT/Ditto.
New evidence: evidence/v1/merged-main-20261115/README.md plus linked live directories.
Original live wrapper FAIL/exit1 retained and qualified as selected-gate count error;
raw selected gates and independent review PASS. No product defect found or fixed.
Main CI/baseline/real acceptance all green. Latest PR47 head/CI/reviews must be
inspected after push; persistent root HANDOFF.md records final non-self-referential SHA.

All application implementation diff against main empty. Final PR diff preserves
unique candidate evidence and adds only docs/verification tools/artifacts/evidence.
Original workloads remain; own smoke projects down without volume deletion; new
Kanto pilot retained stopped, Docker002 remains stopped, original001/ingress active.
No merge/tag/release/submission or permissions weakening performed.

Next: human PR47 review + exact-head CI; merge only by authorized human, inspect final
merged-main CI and unchanged implementation. If main changes, assess/rerun affected
checks. C1–C10/auth/TLS/freshness/timing/LAN decisions, skill provenance review and
report/video/delivery gates remain. No full V1 acceptance/tag justified yet.

## Historical checkpoint retained

# Persistent Phase V1 handoff — resumed final engineering checkpoint

This section supersedes the historical stop handoff retained below. No PR merge,
approval, tag, release or report/video activity was performed.

## Latest exact references

- main — `6a965bbaf5966d096e18c57058cfdbee6185ee2e`
- ankit/fix/v1-ditto-feature-initialization — `cd89160ccdd1b65901d365e46431b1af73ea1efc`
- ankit/fix/v1-ditto-http-compatibility — `0a010eb30e81a63595638b88f81096dc561c5b28`
- ankit/fix/v1-graceful-app-shutdown — `39a58534abad25e11af3139435787874a2b19ed6`
- ankit/test/v1-release-candidate-20261115 — `57fd7d7b31bd6f3699767d7c40f3ab411833ddd4`
- Source fix: d8c1f4048522da3e79a81e6ee5919017b941b00d.
- Fix PRs: #44 initialization, #45 HTTP compatibility, #46 shutdown; all draft.
- Documentation: #47, branch ankit/docs/v1-release-readiness; base is the temporary
  candidate. Resolve current exact doc head from its PR; final reference copy is
  also saved at $HOME/.local/share/qa-sdv-v1/HANDOFF.md after push.

## Completed after resume

- Full final candidate tested at49f8b8d:541 Python +386 subtests,209 Java,7 frontend,
  both Compose checks;2 explicit skips/9 deselections. Nine selected real gates and
  five fault/clear trials pass with clean first-event initialization and original
  nginx. New evidence: evidence/v1/release-candidate-live-20261115T183301Z/.
- Actual d8c1f40 Kanto:3 managed cycles PASS, every stop exit0, exact fresh source/
  event/twin matches,154 final healthy001 twin samples; old PIDs absent. Evidence:
  evidence/v1/shutdown-bounded-kanto-live-20261115T182944Z/.
- Prior candidate6a6badc/source6ad9a4b results keep their original scope; no relabel.
- Later candidate updates attach evidence only: production/config/harness/frontend
  diff from tested49f8b8d is empty. No further enhancements started.

## Next work — humans and final main

1. Inspect latest exact PR heads/CI; no duplicate PRs. Latest fix-head snapshot is
   resumed-final-checkpoint.json (all eight checks PASS for #44/#45/#46); new
   documentation-head CI is inspected after its final push.
2. Obtain actual team/affected-owner approvals and decide C1–C10, subjects/TLS,
   freshness/timing/clock and B5 LAN wording. Current skill/reference qualifications
   and ten absent historical raw logs are documented, not invented or approved.
3. Suggested merge order44 →45 →46, then47. Fixes are independent/main-based.
   Do NOT merge the candidate branch. Update later branches with reviewed main,
   preserving both README follow-ups. No reset/rebase/force-push.
4. After fix merges, merge origin/main into readiness worktree/branch, verify no
   implementation diff against main, retarget existing PR47 to main. Then run the
   documented final merged-SHA CI and clean-init/header/lifecycle smoke. Broader
   repeats only for changed code, failures or unresolved concerns.
5. No release tag is justified until human/final-main and V1-06/07 gates close.
   Report/video creation/recording/submission remained excluded and pending.

## Current service state

Original edge/app-001/MQTT/KUKSA/providers/real Ditto/one ingress and dedicated
Kanto daemon remain running. Docker app-002 and all pilot/test app containers are
stopped. Final candidate projects/observers removed/stopped without volume deletion;
Part B stack stopped with its database retained. Original policies/twins, MongoDB
volumes, unrelated workloads and unused docker_default network preserved. Check
final service inventory before any start/stop. Persistent worktrees/runtime remain.

## Historical stop handoff — superseded where indicated

# Persistent Phase V1 handoff — final stop checkpoint

No merges, tags, releases, approvals or report/video work performed.

## Exact references

- main — `6a965bbaf5966d096e18c57058cfdbee6185ee2e`
- ankit/fix/v1-ditto-feature-initialization — `cd89160ccdd1b65901d365e46431b1af73ea1efc` https://github.com/ankit-suman-07/QA-SDV-Project/pull/44
- ankit/fix/v1-ditto-http-compatibility — `0a010eb30e81a63595638b88f81096dc561c5b28` https://github.com/ankit-suman-07/QA-SDV-Project/pull/45
- ankit/fix/v1-graceful-app-shutdown — `52113759df178057c24749cbd4baef5303c67589` https://github.com/ankit-suman-07/QA-SDV-Project/pull/46
- ankit/test/v1-release-candidate-20261115 — `49f8b8d59eeef7245ba643f9f88f86709c44e99a`

- Shutdown source: `d8c1f4048522da3e79a81e6ee5919017b941b00d`; branch checkpoint5211375 includes targeted evidence.
- Readiness: `ankit/docs/v1-release-readiness`, stacked on candidate; draft PR reference added after creation. Resolve current exact head with git rev-parse or gh pr view.

## Verified and pending

- F03:532 Python tests/386 subtests,2 skips/9 deselections; real isolated first-event initialization, conditional properties update and restart PASS. PR44 prior exact head all8 CI PASS.
- F04:209 Java tests; actual baseline400/fixed individual reads+fleet writes through original nginx PASS. PR45 exact head all8 CI PASS.
- Previous combined candidate6a6badc:540 Python/386 subtests,209 Java,7 frontend;2 skips/9 deselections; nine affected real gates/five fault+clear trials PASS. This source PRECEDES d8c1f40.
- Prior Kanto source6ad9a4b: three managed cycles and158 final healthy001 samples PASS. This source PRECEDES d8c1f40.
- d8c1f40:214 app tests,2 skips PASS. Confirmed stalled-join red timed out9s; corrected regression returns NONZERO incomplete-cleanup error within budget. Five actual-image Docker cases all application exits0, fresh real-Ditto polling matches, absent broker/KUKSA and unacknowledged publication checked.
- Current candidate AND readiness branch include d8c1f40. Final combined verification and Kanto on this final delta PENDING. Latest shutdown/docs exact-head CI pending inspection/completion. Do not relabel previous PASS as final main.

## Resume order — no enhancement first

1. Inspect clean/dirty state in all persistent worktrees; inspect latest PR heads/status and do not duplicate PRs.
2. Verify exact latest shutdown-head CI. On current candidate run relevant combined regression/smoke; full combined re-verification is pending. Preserve previous full-run evidence and reuse unaffected gates explicitly.
3. If privileged Kanto delta check is needed, use own terminal: sudo -v, then persistent Python evidence/v1/app-shutdown-bounded-join-20261115/kanto_lifecycle.py from app-shutdown worktree. Runner creates a NEW name, imports the pinned d8c image and requires existing namespace apps stopped. It is prepared, NOT executed; no passwords in chat.
4. Obtain real human approvals. Suggested merge order #44 → #45 → #46; fixes independently target main. After approved merges, update later branches with origin/main normally; preserve both README append follow-ups. No reset/rebase/force-push.
5. Never merge the temporary candidate branch. Merge current origin/main into readiness branch after fix merges, confirm implementation diff empty, retarget its existing documentation PR to main. Detailed commands: docs/findings/v1-release-readiness.md.
6. Run final merged-main Java21/Python/frontend/Compose checks, exact-head CI and clean-init/header/lifecycle smoke with fresh isolated resources/new images. Record exact SHA and source hashes. No tag/release before owner decisions and V1-06/07 gates.

## Persistent locations and evidence

- Root: $HOME/.local/share/qa-sdv-v1/. Original checkout remains main6a965bb, clean.
- worktrees/ditto-initialization, ditto-http, app-shutdown, release-candidate, release-readiness.
- runtime/venv-3.12, jdk21, node22, ditto-source, ditto-restored.json (original), ditto-engineering.json (separate stopped Part B stack), image archives. Never depend on old /tmp.
- Newest shutdown: evidence/v1/app-shutdown-bounded-join-20261115/README.md and targeted-verification.json.
- Prior full candidate: evidence/v1/release-candidate-20261115/README.md; raw evidence/v1/release-candidate-live-20261115T152908Z/.
- CI/references: final-checkpoint.json. Final services: final-service-state.json. Skill reference/license/diff and ten historical missing raw-log targets recorded here.

## Service/cleanup state

- Original MQTT, both KUKSA/providers, app-001, real Ditto/MongoDB and one ingress remain running; dedicated Kanto daemon active.
- Original Docker app-002 stays stopped. Both prior Kanto pilot containers recorded stopped; no new d8c Kanto trial.
- New Docker lifecycle test apps/brokers and separate Part B Ditto stack stopped; retained for inspection. Some third-party Ditto stop exits137/143 preserved; only application target exit0 is claimed.
- Candidate test projects cleaned up without volume deletion. Original volumes, policies/twins, historical evidence, unrelated workloads and unused docker_default network preserved.

## Human decisions/remaining release limits

- C1–C10 owner review; exact principal/resource/TLS decisions;5s/30s/1s freshness defaults; update/dispatch budgets and clock assumptions.
- B5 remote-LAN wording decision; same-device V1-09 passed, remote LAN and automatic crash recovery NOT verified.
- Skill provenance: current v6.4.2 reference found, two exact copies and two-line debugging redaction difference; no invented historical E1/E2 installed/invocation pins. Ten old raw logs absent; command metadata is not raw output.
- Report/video creation/recording/submission excluded and pending. Final main/release acceptance/tag decision still human; full V1 NOT accepted.
