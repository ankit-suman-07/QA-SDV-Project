# Phase V1 skill sources and usage

These are candidate pre-prepared skills from the [Superpowers repository](https://github.com/obra/superpowers). Pin the upstream commit and preserve the original files and license when adopting a skill. Record actual usage as work happens.

| Skill | Planned use | Upstream URL | Status |
|---|---|---|---|
| `test-driven-development` | Add behavior checks for vehicle-specific routing and invalid targets. | [Link](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md) | Used in E1 (see below) |
| `verification-before-completion` | Verify the live fault and recovery flow in Ditto and Spring Boot. | [Link](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) | Candidate |
| `systematic-debugging` | Trace a failure across Velocitas, Mosquitto, Ditto and Spring Boot when needed. | [Link](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) | Optional candidate |
| `brainstorming` | Clarify scope and write the design before code. | [Link](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) | Used in E1 |
| `writing-plans` | Turn an approved spec into TDD tasks. | [Link](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md) | Used in E1 |
| `executing-plans` | Run the plan and finish with a whole-branch review. | [Link](https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md) | Used in E1 |
| `finishing-a-development-branch` | Decide merge, PR or keep. | [Link](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md) | Used in E1 |

## Usage entry template

- **Task and acceptance ID:**
- **Skill, upstream commit and invocation evidence:**
- **Spec revision and expected behavior:**
- **Generated output and human review:** Record what was accepted or corrected and why.
- **Verification:** Record the command, observed result, and test or CI link.
- **Implementation reference:** Link the PR or commit.
- **Limitations:** Note mocked dependencies or checks that remain pending.

## Usage entries

### E1: two-vehicle edge publication (V1-01)

- **Task and acceptance ID:** E1, V1-01. Branch `emmanuel/feature/v1-two-vehicle-edge`, owner Emmanuel.
- **Skill, upstream commit and invocation evidence:** Superpowers plugin, release **6.4.2** ([obra/superpowers](https://github.com/obra/superpowers), MIT). The installed copy has no git metadata, so the exact upstream commit still has to be looked up from the 6.4.2 tag. All skills ran in a Claude Code session, invoked through its Skill tool:

  | Skill | Use in E1 | Output |
  |---|---|---|
  | `brainstorming` | Clarified scope, compared approaches and wrote the design | Spec `cb976cb` |
  | `writing-plans` | Turned the approved spec into 5 TDD tasks and a Review Focus list | Plan `48510a6` |
  | `executing-plans` | Ran the plan in one session, then ran one fresh-context review of the whole branch | `7347614`..`1a6f50d` |
  | `test-driven-development` | Every behaviour started as a failing test, including the review fixes | Tests in `velocitas-app/app/tests/`, `tests/test_v1_edge_compose.py` |
  | `finishing-a-development-branch` | Merge, PR or keep decision; the branch goes through a PR so ingress can review it | No merge or push without the owner's request |

- **Spec revision and expected behavior:** [design](../../docs/superpowers/specs/2026-11-11-v1-two-vehicle-edge-design.md) at `cb976cb`, against [v1-interface-contracts.md](../../docs/v1-interface-contracts.md) 1.0.0, sections C2–C4 and C9. Two vehicles each have their own provider, KUKSA broker and app. Each publishes C3 events to `sdv/<vehicleId>/health` with C4 health, and `sourceTimestamp` is the observation time.
- **Generated output and human review:** Emmanuel made these decisions:
  - scope: E1 only
  - a new Compose file instead of editing the baseline one
  - the feature first, with every fix on its own branch
  - approach A
  - approval of the spec, then the choice of in-session execution

  The final review raised four Important findings:

  | Finding | Outcome | Evidence |
  |---|---|---|
  | A KUKSA reconnect leaked the old gRPC channel | Fixed | Test-first in `1a6f50d` (`kuksa_reconnect.py`) |
  | When the observation time went backwards, the app stopped publishing without logging why | Fixed | Test-first in `1a6f50d` (gate `last_skip`, warning logged once per change) |
  | The publish result code might not be returned by the SDK | Refuted | The Velocitas SDK 0.15.7 source returns paho's `MQTTMessageInfo` |
  | Events are published with QoS 0, but the contract says QoS 1 | Left open, then fixed | The PR #33 review showed the merged ingress rejects QoS 0. Fixed test-first in `a3e20c1` (branch `emmanuel/fix/v1-qos1-publication`) and re-checked live into the real ingress |

  During live testing, a clash between the Compose project names showed up and was fixed (`a0b8e05`).
- **Verification:** see [E1 record](E1-two-vehicle-edge.md):
  - unit tests: 42 passed
  - Compose tests: 4 passed on the host
  - live capture: 24 contract-valid events, 12 per vehicle, exit 0
  - isolation run: vehicle-001 kept publishing while provider-002 was stopped
  - baseline MVP demo: passed
  - full suite: 192 passed, 4 skipped
- **Implementation reference:** commits `cb976cb`..`1a6f50d` on `emmanuel/feature/v1-two-vehicle-edge`, [PR #33](https://github.com/ankit-suman-07/QA-SDV-Project/pull/33).
- **Limitations:**
  - QoS 0 publishing, fixed later in `a3e20c1`.
  - After a restart, the first event can be delayed by up to 5 s.
  - The reconnect path is covered by unit tests only. A live KUKSA restart recovered without it being triggered.
  - Fault/recovery (E2) and Ditto/API integration are not covered.

### E2: deterministic vehicle-002 LiDAR fault and recovery (V1-03, edge part)

- **Task and acceptance ID:** E2, V1-03 (edge part). Branch `emmanuel/feature/v1-lidar-scenarios`, owner Emmanuel.
- **Skill, upstream commit and invocation evidence:** the same Superpowers 6.4.2 plugin as E1, invoked through Claude Code's Skill tool:

  | Skill | Use in E2 | Output |
  |---|---|---|
  | `brainstorming` | Scope, three approaches, design in three approved parts | Spec `2df2826` |
  | `writing-plans` | 6 TDD tasks with a Review Focus list of five uncovered cases | Plan `2fcac7c` |
  | `executing-plans` | Ran the plan in one session with a per-task ledger, then one fresh-context review of the whole branch | `f4a9b8e`..`516b2f3` |
  | `test-driven-development` | Every behaviour change started as a failing test, including the review fixes | Tests in `vehicle-simulator/tests/`, `tests/test_v1_lidar_cycle_script.py` |
  | `finishing-a-development-branch` | Merge, PR or keep decision; the branch was kept for a PR | No merge or push without the owner's request |

- **Spec revision and expected behavior:** [design](../../docs/superpowers/specs/2026-11-11-v1-lidar-scenarios-design.md) at `2df2826`, against contract 1.0.0 sections C2, C4, C5, C8 and C9. Inject on vehicle-002 steps the LiDAR distance `35 → 20 → 8 → 3` m, one rung per tick; clear steps it back. vehicle-001 stays HEALTHY. A provider returns 409 for any other vehicle ID.
- **Generated output and human review:** Emmanuel chose:
  - a fixed ramp over an instant jump or a seeded random ramp
  - a fixed 35 m idle distance
  - approach A (a separate trajectory module and an identity check in the controller)
  - approval of each design part and of the spec, then in-session execution

  Three implementer rulings are recorded in the PR: test helper shapes, waiting for a real HEALTHY event before injecting, and loading the provider's `main.py` by path. The final review found one Important issue: the script's exit trap could miss an applied inject. It was fixed test-first in `1b58120`. Two Minor findings were fixed test-first afterwards in `6ad55b4` (request time limits, a `FAIL:` line when the provider is unreachable). The other four are listed in the PR as deferred.
- **Verification:** see [E2 record](E2-lidar-cycle.md):
  - two live cycles with `cycleComplete: true` and the same distances
  - a 409 for the wrong vehicle
  - the interrupt and stack-down checks
  - a third live cycle after merging `main`, at `6ad55b4`
  - full suite after merging `main`: 472 passed, 5 skipped
- **Implementation reference:** branch `emmanuel/feature/v1-lidar-scenarios`. The PR link is still to be added.
- **Limitations:**
  - Spring Boot, Ditto and the UI were not part of this run.
  - `LIDAR_SENSOR_FAILURE` is covered by unit tests only.
  - Publisher QoS was 0 during the first runs; fixed in E1 (`a3e20c1`) and re-run at QoS 1.

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
