# Course V1 skill sources and usage

These are candidate pre-prepared skills from the [Superpowers repository](https://github.com/obra/superpowers). Pin the upstream commit and preserve the original files and license when adopting a skill. Record actual usage as work happens.

| Skill | Planned use | Upstream URL | Status |
|---|---|---|---|
| `test-driven-development` | Add behavior checks for vehicle-specific routing and invalid targets. | [Link](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md) | Candidate |
| `verification-before-completion` | Verify the live fault and recovery flow in Ditto and Spring Boot. | [Link](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) | Candidate |
| `systematic-debugging` | Trace a failure across Velocitas, Mosquitto, Ditto and Spring Boot when needed. | [Link](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) | Optional candidate |

## Usage entry template

- **Task and acceptance ID:**
- **Skill, upstream commit and invocation evidence:**
- **Spec revision and expected behavior:**
- **Generated output and human review:** Record what was accepted or corrected and why.
- **Verification:** Record the command, observed result, and test or CI link.
- **Implementation reference:** Link the PR or commit.
- **Limitations:** Note mocked dependencies or checks that remain pending.

## A5 actual usage — November 12, 2026

- Task/acceptance: A5, primarily V1-08, supporting V1-03/04/05/06/07.
- Read/applied the repository copies of `skills/test-driven-development.md`,
  `skills/systematic-debugging.md` and `skills/verification-before-completion.md`
  from baseline `2803429`; no upstream revision pin is claimed.
- Red/green fleet endpoint, materialization, provisioning, frontend state and
  scheduler interference checks are recorded in [A5 evidence](fleet-dashboard.md).
- Missing supporting files: `skills/writing-good-tests.md` and the supporting
  technique files referenced by systematic debugging. Their usage is not claimed.
- Human affected-owner review remains pending. Java, browser and controlled HTTP
  checks verify components; no live fleet/MQTT acceptance is claimed.
