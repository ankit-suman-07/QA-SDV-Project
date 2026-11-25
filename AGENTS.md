# Coding-agent instructions

Applies throughout QA-SDV-Project. Keep this file at the repository root.

## Sources and document selection

Read [docs/SOURCE-OF-TRUTH.md](docs/SOURCE-OF-TRUTH.md) first. Use the repository's existing hyphenated filename; do not create a competing underscore-named index. If references disagree, report and correct them within the authorized scope.

For Phase V2, select the documents relevant to the task:

| Document under `docs/` | Use |
|---|---|
| `11-FINAL-phase-v2-plan.md` | Final-phase goals and delivery sequence. |
| `12-FINAL-phase-v2-technical-decisions.md` | Technical decisions and integration boundaries. |
| `13-FINAL-phase-v2-tasks-and-acceptance.md` | Ownership, tasks and completion criteria. |
| `v2-interface-contracts.md` | Payloads, units, identity, ordering, timing and interface behavior. |
| `v2-independent-development.md` | Shared fixtures, replay, substitutes and independent setup. |
| `v2-native-diagnostic-feasibility.md` | Supported native operations, bindings and unresolved decisions. |

Use `08-project-scope-and-acceptance.md`, `09-architecture-diagrams.md`, `00-github-contribution-guidelines.md`, `local-setup.md` and relevant findings when needed. Read V1 contracts/implementation for compatibility work. Older plans and `Version_1/` are historical context; do not read them routinely or let them silently override current V2 decisions.

The source index defines authority by subject. `FINAL` or a newer timestamp alone does not establish precedence. Proposed decisions are not approvals or implemented behavior. Report concrete conflicts to Ankit Suman and continue unaffected work. Do not invent missing contracts or native SDK APIs.

## Ownership and architecture

- Phase V2 is the final phase: extend the verified V1 baseline to three vehicles total, preserving compatibility and historical evidence.
- Emmanuel owns CARLA actors/front LiDAR, extraction, source scenarios and replay inputs.
- Ankit owns adapter-to-KUKSA publication, backend/actions, the sole fleet aggregator/materializer, dashboard and integration/release coordination.
- Bayan owns Velocitas health/recovery, individual twins/history, native diagnostics and coordinated Kanto validation.
- Velocitas decides health; Spring Boot derives fleet state from individual twins. Prevent duplicate publishers and fleet writers. Follow current contracts for details.

## Implementation and Git workflow

1. Inspect branch, worktree status and relevant task acceptance. Preserve existing work; never reset, clean or overwrite changes merely to obtain a clean checkout.
2. For new work, use a focused branch from updated `main` after required preparation/dependencies merge. For continuation or PR fixes, reuse the task branch/PR. Record baseline SHA; do not duplicate branches or import unrelated teammate work.
3. Use existing code, contracts and shared fixtures. Change shared interfaces only through the required contract/fixture/consumer updates and affected-owner review.
4. Apply relevant versioned repository skills. V2 requires justified customization and evaluation; preserve originals/licenses, cite course concepts and record actual use. Do not claim missing supporting files were read.
5. Add meaningful behavior and negative-case checks; follow the applicable test-first workflow. Run focused checks, then required broader verification and CI.
6. Follow contribution rules for checkpoints and PR descriptions. Commit/push/open PRs within task authorization. Merge, tag, publish or submit only with explicit authorization and required reviews.

## Efficient execution

- Complete only the assigned task or part. Reuse the documented plan; investigate further when evidence or unresolved decisions require it.
- Read the index once per session, then relevant sections/code. Use targeted searches; avoid dumping whole repositories, evidence directories or long logs.
- Reuse valid checks at the relevant tested revision. Rerun for changed behavior, failures, unresolved risk or required CI; do not repeat every suite at every checkpoint.
- Start Docker/CARLA/native services only for checks that need them. Documentation work normally needs link/format checks, not full-stack startup.
- Avoid unrelated refactoring, dependency upgrades, extra documentation and unnecessary parallel agents. Delegate only when explicitly requested or required by applicable instructions.
- Keep updates and outputs concise while preserving actionable failure details. Efficiency never replaces required testing, reviews or acceptance evidence.

## Runtime, evidence and handoff

Keep deployment local and preserve unrelated workloads, volumes, twins and policies. Do not weaken privileged access to bypass a blocker. Separate synthetic/mock/replay checks from real native/CARLA acceptance; failed dependencies must not become fabricated healthy data.

Preserve source/event identity and timestamp semantics. Dispatch acknowledgement is not observed completion. Record exact tested SHA, configuration, commands, exits, limitations and secret-free artifacts under root `evidence/`; use `docs/findings/` for findings. Skipped/blocked checks are not passes. Preserve historical failures and append dated resolutions.

Finish each task/part with branch, commits/PR, changes, checks and remaining blockers. Save a concise persistent handoff before interruption, including next steps and owned services left running. Keep technical verification, approvals and final delivery gates distinct.

## Optional model preferences

When supported by the runtime: Sol for regular implementation/testing; Luna for straightforward documentation/small edits; Terra for visual/UI inspection; Astra for difficult architecture/integration debugging. These are preferences, not automatic model switches or usage guarantees. Honor the user's model selection; never claim an unconfirmed switch or spawn agents solely to change models.
