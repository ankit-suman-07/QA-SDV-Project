# SDV Project — Source of Truth

**Updated:** November 17, 2026 · **Active stage:** Phase V2, the final phase · **Technical decision owner:** Ankit, Bayan, Emmanuel

## Purpose and canonical location

Use this document as the authoritative project index for developers, coding agents and project chats. Read the relevant sources before changing implementation, tests or architecture. Repository revisions and explicit decision/review records take precedence over recollections from chats.

**Canonical repository location: `docs/SOURCE-OF-TRUTH.md`.** Existing repository links use this path. Historical revision links remain historical evidence.

Root `AGENTS.md` should direct agents here and contain short workflow instructions, not duplicate product specifications. A root `CLAUDE.md`, if used, should share those instructions rather than define a different scope.

## Objective and phase boundary

Build a reproducible local SDV fleet health-monitoring and diagnostic platform with isolated vehicle state, compact LiDAR observations, individual digital twins, one fleet twin and traceable targeted diagnostics/recovery.

- **MVP:** recorded single-vehicle baseline; preserve its evidence and provenance qualifications.
- **Phase V1:** two synthetic vehicles, live twin/backend/fleet/dashboard integration and recorded same-device Kanto managed-restart evidence. Treat older pending statements as historical where later evidence explicitly supersedes them. Review current findings for remaining approval/release qualifications; do not equate merged code with blanket acceptance.
- **Phase V2:** three CARLA vehicles total, each with front LiDAR; complete diagnostic tracking, agreed native exchanges, CARLA-backed Kanto validation, customized-skill evaluation and final delivery. Target date: December 5, 2026.

The earlier 60/40 effort split is an estimate, not a completion rule. Phase V2 extends the V1 baseline; do not rebuild working functionality unnecessarily.

## Sources and authority

| Source | Governs |
|---|---|
| [Project objective](02-project_objective.md) | Purpose and rationale. |
| [Scope and acceptance](08-project-scope-and-acceptance.md) | Required outcomes, acceptance IDs, exclusions and rubric evidence. |
| [Phase V2 final plan](11-FINAL-phase-v2-plan.md) | Final-phase goals, delivery sequence and revised allocation. |
| [Phase V2 technical decisions](12-FINAL-phase-v2-technical-decisions.md) | Project-lead decisions, health/recovery direction and compatibility checks. |
| [Phase V2 tasks and acceptance](13-FINAL-phase-v2-tasks-and-acceptance.md) | Current owner-specific tasks and completion conditions. |
| [V2 interface contracts](v2-interface-contracts.md) | Versioned payloads, timing/ordering, twin/API/action structures and bounded defaults. |
| [V2 independent-development guide](v2-independent-development.md) | Fixtures, substitutes, owner workflows and exact preparation commands. |
| [Ankit V2 baseline and decisions](v2-ankit-preparation-baseline.md) | Tested V1 reference, prep coverage and proposed companion binding for review. |
| [V2 native diagnostic feasibility](v2-native-diagnostic-feasibility.md) | Supported implementations and unresolved protocol/service bindings. |
| [Architecture](09-architecture-diagrams.md) | Component roles and runtime flows; reconcile historical diagrams with current decisions/contracts. |
| [Detailed task distribution](10-detailed-task-distribution.md) | Historical allocations and continuing handoffs; newer V2 task documents supersede conflicting V2 ownership. |
| [V1 contracts](v1-interface-contracts.md) and [V1 development guide](v1-independent-development.md) | Existing compatibility baseline and preserved V1 workflows. |
| [Contribution guidelines](00-github-contribution-guidelines.md) | Branch, commit, PR and review practices. |
| [Evidence index](../evidence/README.md), [V2 preparation](../evidence/v2/preparation.md), [findings](findings/) | Recorded status, tests, runtime boundaries and unresolved findings. |
| [MVP baseline](../evidence/v1/baseline.md) and [skill records](../evidence/v1/skill-sources.md) | Historical measurements, actual skill use and provenance limitations. |

**Apply authority by subject:** scope controls required outcomes; technical decisions control design direction; interface contracts control wire/data behavior; current task acceptance controls ownership. A proposed/default decision is not formal team approval or proof of implementation. A newer filename or timestamp alone does not authorize an unrelated requirement change.

If these sources disagree, identify the specific conflict and let Ankit record the decision. Continue unaffected work; do not silently choose incompatible interfaces. Missing documents or unresolved native bindings must stay explicit, not be filled with invented APIs or success claims.

## Current Phase V2 ownership

| Owner | Boundary |
|---|---|
| **Emmanuel** | CARLA runtime, actors/front LiDAR, actor-to-vehicle mapping, observation extraction, controlled source scenarios, ground truth and replay inputs. |
| **Ankit** | Adapter-to-KUKSA publication, units/time validation, backend/actions, sole fleet aggregation/materialization, dashboard, integration/CI, measurements and final release/submission coordination. |
| **Bayan** | Velocitas health/recovery, observation/event tests, individual twins/history, native uProtocol/OpenSOVD integration and coordinated CARLA-backed Kanto validation. |
| **All three** | Owned tests/evidence, customized skills and evaluations, interface reviews, actual contribution records and final demonstration support. |

These allocations supersede older conflicting V2 assignments. Preserve original V1 contributions; Ankit's later remediation ownership does not erase them.

## Architectural constraints

- Telemetry flows through CARLA/adapter → per-vehicle KUKSA → per-vehicle Velocitas → MQTT → validated ingress → Ditto → Spring Boot → dashboard.
- Velocitas owns health decisions. Source adapters provide observations and separately labelled ground truth. Keep raw point clouds outside Ditto.
- The **single Spring Boot aggregator** reads individual twins, serves the derived fleet response and materializes the fleet Thing. Bayan owns individual-twin updates; do not add another fleet aggregator/writer.
- Keep stable identities for `vehicle-001`, `vehicle-002` and `vehicle-003`; prevent duplicate publishers. Preserve source/event identity and distinguish observation, processing and dispatch times.
- Keep production and development substitutes explicitly separate. Failed real reads must not fall back to fabricated healthy data.
- Deployment remains local; CARLA can use a separate capable host. Beam, CANought, another sensor type and additional vehicles remain optional. Full autonomous driving is outside scope.

## Independent-development workflow

1. Update main after the shared preparation PR is merged; record the starting SHA and create a focused owner branch. Do not assume a draft PR's files exist on main.
2. Identify the phase, owner and acceptance ID. Read only the relevant contract, fixtures, skills and implementation boundary.
3. Use the shared V2 synthetic fixtures, replay and HTTP substitutes to work without teammate services. Follow the independent guide for their actual locations and commands; do not invent parallel fixture formats.
4. Implement against shared expected results. Cover identity, units, timing, recovery and relevant negative cases; shared-contract changes update contracts, fixtures and tests together under the existing review rules.
5. Record independently implemented/mock-tested status honestly. Real CARLA, native diagnostic and joined three-vehicle acceptance remain separate integration obligations.

The preparation package does not itself establish native uProtocol transport/service binding, OpenSOVD vehicle/provider mapping or live observation-companion binding. Check the feasibility record and close affected decisions before dependent native implementation.

## Skills for Phase V2

| Task | Skill workflow |
|---|---|
| New behavior or regression fix | Use the applicable versioned customized TDD skill; retain the original for baseline comparison. |
| Failure investigation | Use the applicable customized systematic-debugging skill and capture actual evidence. |
| Completion claim | Use the applicable customized verification-before-completion skill and report commands/results. |

Do not assume customized files already exist. Before an evaluated V2 task, preserve the original source/license, create or select the reviewed customization, cite course concepts and record its version/diff. Follow actual repository paths; do not claim missing supporting files were read.

Compare originals/customizations on comparable starting code, tasks and acceptance criteria, recording model/tool settings and human interventions. Capture usage during work, not retrospectively. If a skill is unavailable, report the limitation and leave its use unclaimed; continue independent work where appropriate.

## Verification, evidence and efficient execution

- Link requirement → contract revision → implementation/PR → checks → runtime evidence. Record the exact tested SHA, configuration, dependencies, exits and limitations.
- Distinguish synthetic fixtures, mocks, actual components and joined live acceptance. Skipped/blocked checks are not passes; regression is a purpose that can overlap unit/integration tests.
- Use focused checks first. Reuse valid exact-revision results; rerun broader tests only for changed behavior, failures, required CI or unresolved risk. Do not launch CARLA/full-stack services merely to edit documentation.
- Use persistent worktrees/runtime storage, not `/tmp` for irreplaceable state. Keep secrets out of evidence; preserve unrelated workloads, twins, policies and volumes.
- Never infer approvals from merges, skill usage from file presence or performance improvements from incompatible measurements. Preserve failures and add dated follow-up conclusions.
- Follow repository contribution/review rules and task authorization for commits/pushes/PRs. Do not merge, tag, publish or submit without explicit authorization. Before interruption, save completed work and a concise persistent handoff.

**Final completion:** assess every V2 acceptance criterion using the current scope and actual evidence. Technical verification, required reviews and report/video/release delivery are distinct gates; none is established merely by finishing a prompt.
