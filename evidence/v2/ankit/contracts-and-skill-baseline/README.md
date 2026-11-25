# Ankit V2 preparation verification

Tested revision: `5c151c7a4510bc26c99f2919b848e9c5d87a3e63`, from fetched main
`e3b4a6af5421a3b9c88e2c16f51d78f929052990`. Default synthetic epoch and loopback
HTTP configuration. The follow-up commit adds evidence and index links only.

| Requirement or check | Command and result | Evidence boundary |
|---|---|---|
| C1–C7 substitute and literal fixtures | `python -m scripts.v2_dev.check` → exit 0, 8 tests, 22 synthetic JSON files and guide links checked. The session vector rejects unregistered and retired input and permits the registered successor to enter recovery. Silence stays false at 0.500 s and becomes true at 0.501 s. | Synthetic reference implementation |
| C5–C6 conditional writes and diagnostic mapping | `python -m unittest tests.test_v2_http -q` → exit 0, 1 loopback test including negative routes, preconditions and provider failures. | HTTP substitute |
| C2 recovery input identity | `python -m scripts.v2_dev.replay --ack-development-only --sequence recovery --vehicle vehicle-003` → exit 0, seven JSONL observations on the vehicle-003 topic with 3 m then 20 m, source times spanning 2.1 s. | Immediate synthetic replay, no MQTT or KUKSA |
| Documentation links | Python regex scan of Markdown link targets in the new baseline and skill README and added source-index link, resolving relative paths from each file → exit 0, 15 local links. The final documentation check also covers this record and the added evidence-index links. | Local link targets |
| Skill archive and diff | `gh api 'repos/obra/superpowers/contents/skills/verification-before-completion/SKILL.md?ref=22f0b463e7a5e579904dd6211a520321035526f7' --jq .sha` matched `git hash-object skills/verification-before-completion.md`, blob `7d45333cc4a49c57a80df6c1fe2fa777a207afbc`. `cmp` confirmed the copy of the archived MIT notice. `git apply --check` initially rejected the zero-context patch. `git apply --check --unidiff-zero skills/v2/ankit/verification-before-completion/v1.0.0.diff` exited 0. | Provenance and patch review |
| Scope and formatting | `git diff --check origin/main HEAD` → exit 0. `git diff --name-only origin/main HEAD` reviewed. Only prep documentation and skill artifacts at the tested revision. | Branch review |

Applied [Ankit verification v1.0.0](../../../../skills/v2/ankit/verification-before-completion/README.md)
to match contract clauses to literal outcomes and record commands, exits and
proof boundaries. The paired evaluation and human review remain pending. The
[decision record](../../../../docs/v2-ankit-preparation-baseline.md) lists
pending binding and owner decisions. Production component builds, real MQTT
and KUKSA, CARLA, native protocols and joined integration were not run.
No owned services remain running.
