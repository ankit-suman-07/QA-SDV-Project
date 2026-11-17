# SDV project source of truth

## Phase V2 preparation — November 17, 2026

Current V2 allocation follows [final plan](11-FINAL-phase-v2-plan.md),
[technical decisions](12-FINAL-phase-v2-technical-decisions.md) and
[task acceptance](13-FINAL-phase-v2-tasks-and-acceptance.md). Emmanuel owns CARLA,
observations/scenarios/ground truth; Ankit adapter-to-KUKSA, backend/actions,
sole fleet writer, dashboard/integration/evaluation; Bayan health/recovery,
individual twins/history, native diagnostics and coordinated Kanto validation.
These V2 sources supersede older conflicting V2 assignments, preserving V1 history.
Use [V2 contracts](v2-interface-contracts.md), [independent guide](v2-independent-development.md)
and [native feasibility](v2-native-diagnostic-feasibility.md) for preparation.
New bounded defaults are project-lead decisions for affected-owner review, not
formal team approval or implemented features. [Evidence](../evidence/v2/preparation.md).

## Remaining Phase V1 ownership — November 14, 2026

Ankit owns all remaining Phase V1 remediation, integration, verification, fleet CI,
Kanto validation (B5 / V1-09), report/video and release work. Bayan and Emmanuel's
component contributions and original task IDs remain historical attribution, not
assignments of remaining work. Phase V2 ownership is unchanged. The sole fleet
aggregator and fleet-twin materializer are in Spring Boot under Ankit (A5).
V1-09 remains required and separately tracked; a blocked Linux/LAN pilot does not
constitute acceptance. Release still requires all applicable criteria and reviews.
This ownership update does not approve proposed interfaces, freshness defaults,
measurement budgets, authentication subjects or other unresolved decisions.


Use this file as the entry point for SDV project chats. Read the relevant sources before proposing code, tests or architecture. The team's approved Git revisions are authoritative. Use matching copies in ChatGPT Project sources.

| Source to access | Read it for |
|---|---|
| `02-project_objective.md` | Project objective and rationale. |
| `08-project-scope-and-acceptance.md` | Product scope, acceptance IDs and required evidence. Check its phase assignments against the latest approved task distribution. |
| `10-detailed-task-distribution.md` | Current phase allocation, owners and handoffs. |
| `09-architecture-diagrams.md` | Telemetry and diagnostic flows. Check the task distribution for work moved to Phase V1. |
| [v1-interface-contracts.md](v1-interface-contracts.md) | Proposed V1 MQTT, Ditto, Spring Boot and scenario baseline, fixtures and review status. Replaces the missing planned `docs/interface-contracts.md` entry for V1. Obtain affected-owner approval before changing production shared interfaces. |
| [v1-independent-development.md](v1-independent-development.md) | Independent mock-based workflows, commands, verification limits and PR handoffs. |
| `00-github-contribution-guidelines.md` | Branching, review and contribution practices. |
| `evidence/README.md` and `evidence/v1/baseline.md` | Evidence index and verified single-vehicle MVP results. |
| `evidence/v1/skill-sources.md` | Skill provenance and actual usage records. |

Use **Phase V1** and **Phase V2**. The latest split targets about 60% of remaining effort in Phase V1, including the two-vehicle synthetic workflow, basic fleet dashboard, fleet CI and a one-vehicle Kanto pilot. Phase V2 includes CARLA and broader runtime and diagnostic validation. Treat the split as an effort estimate.

## Choose skills by task

| Situation | Read and apply |
|---|---|
| New behavior or a regression fix | Original `test-driven-development` skill. |
| A test or integration fails | Original `systematic-debugging` skill. |
| Before declaring a task complete | Original `verification-before-completion` skill. |

Use the attached skill instructions and relevant supporting files. Phase V1 uses pre-prepared originals. In Phase V2, use the approved customized versions and record the diff, rationale and comparison. If a skill is unavailable, say so and leave its use unclaimed.

## Work against the specs

1. Identify the phase, task owner and acceptance ID. Open only the relevant specifications and skills.
2. Flag missing sources or conflicting requirements before making implementation assumptions. Use the latest approved task distribution for phase allocation. Get team agreement on changes to scope, acceptance criteria or shared interfaces before implementing them.
3. Keep each change tied to the acceptance criterion. For PRs, record the spec revision, implementation link, checks actually run and observed results. Distinguish mocked checks from live integration.
4. Record skill use only when it happens. Link the skill version, task, reviewed output and verification evidence. Mark unverified work as pending.
