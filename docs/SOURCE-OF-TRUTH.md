# SDV project source of truth

Use this file as the entry point for SDV project chats. Read the relevant sources before proposing code, tests or architecture. The team's approved Git revisions are authoritative. Use matching copies in ChatGPT Project sources.

| Source to access | Read it for |
|---|---|
| `02-project_objective.md` | Project objective and rationale. |
| `08-project-scope-and-acceptance.md` | Product scope, acceptance IDs and required evidence. Check its phase assignments against the latest approved task distribution. |
| `10-detailed-task-distribution.md` | Current phase allocation, owners and handoffs. |
| `09-architecture-diagrams.md` | Telemetry and diagnostic flows. Check the task distribution for work moved to Phase V1. |
| `docs/interface-contracts.md` | Shared MQTT, Ditto, Spring Boot and scenario command behavior. Planned. Until approved, ask for the agreed contract before changing a shared interface. |
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
