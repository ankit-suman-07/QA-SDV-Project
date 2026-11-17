# Coding-agent instructions

Applies to the whole QA-SDV-Project repository. Place this file at the repository root.

## Read before working

Read [docs/SOURCE_OF_TRUTH.md](docs/SOURCE_OF_TRUTH.md) first. It is the authoritative project index and explains document precedence, Phase V2 boundaries, ownership and evidence requirements. Follow its relevant linked specifications; this file adds workflow guidance and does not replace them.

If that exact file is missing, locate the existing source-of-truth index and report the filename discrepancy. Do not create competing specifications or silently infer missing requirements. For conflicting product requirements, identify the conflict for Ankit Suman and continue unaffected work.

## Current boundaries

- Phase V2 is the final phase. Extend the working V1 baseline and preserve its compatibility and historical evidence.
- Emmanuel owns CARLA actors, front LiDAR, extraction, source scenarios and replay inputs.
- Ankit owns adapter-to-KUKSA publication, backend/actions, the sole fleet aggregator/writer, dashboard and integration/release coordination.
- Bayan owns health/recovery, individual twins/history, native diagnostics and coordinated Kanto validation.
- Use current task acceptance and interface contracts for details. Do not change another owner's shared interface incidentally.

## Implementation workflow

1. Inspect the current branch, worktree status, relevant instructions and task acceptance criteria. Preserve existing changes. Never reset, clean or overwrite work to obtain a clean checkout.
2. For a new task, use a focused branch from updated `main` after required preparation is merged. For a continuation or PR fix, use the existing task branch. Record the starting SHA; do not duplicate branches or PRs.
3. Read relevant code and shared fixtures before editing. Use the V2 independent-development guide for actual mock/replay commands. Keep changes within the requested task.
4. Apply the relevant repository skill version and record actual use. Phase V2 requires justified customizations and evaluation; preserve original versions/licenses and do not invent provenance or claim unavailable supporting files were read.
5. Add meaningful behavior/regression checks, including relevant negative cases. Update shared contracts, fixtures and consumers together when an authorized interface change requires it.
6. Run focused verification first, then the broader checks required by affected behavior and CI. For documentation-only work, check links/formatting without starting CARLA or the full stack.
7. Follow contribution guidelines for commit checkpoints, PR naming and review. Commit, push or create PRs when authorized by the task. Merge, tag, release or submit only with explicit authorization.

## Runtime and evidence rules

- Keep deployment local. Preserve unrelated services, volumes, twins and policies. Do not run destructive cleanup or broaden privileged access to bypass a blocker.
- Keep vehicle identities isolated and prevent duplicate publishers. Velocitas owns health decisions; Spring Boot owns fleet aggregation/materialization.
- Separate mocks, synthetic inputs and replay from actual CARLA/native-protocol/live integration. Never replace a failed live dependency with fabricated healthy data.
- Preserve source/event IDs, units and timestamp semantics. An action acknowledgement does not prove recovery completed.
- Save durable, secret-free evidence under root `evidence/`, following its index. Record the tested SHA, commands, observed results and limitations. Keep findings under `docs/findings/` where appropriate.
- Do not claim approval, skill use, coverage or performance improvements without evidence. Mark blocked/skipped checks explicitly; preserve historical failures and append dated resolutions.

## Efficient completion and handoff

Read only the sources needed for the task. Reuse valid verification at the same relevant revision; rerun when changes, failures or required checks justify it. Avoid unrelated refactors, dependency upgrades and repeated full-stack runs.

Finish with changes made, branch/commit/PR references, verification results and remaining blockers. If interrupted, save a persistent handoff with exact next steps and runtime ownership. Keep human approvals and final delivery gates explicit.
