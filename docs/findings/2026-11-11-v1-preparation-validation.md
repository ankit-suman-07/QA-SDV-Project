# V1 independent-development preparation — validation record

Date: November 11, 2026. Branch: `docs/v1-independent-development`. Base revision: `162f32807d6e5cb2b503dddad9e3790030fca75c`. Local commit identities are available through `git log` on this branch; this document describes the preparation worktree and its validation, not a deployed release.

## Delivered boundary

- [Proposed V1 contract 1.0.0](../v1-interface-contracts.md), [independent guide](../v1-independent-development.md), and updated [task distribution](../10-detailed-task-distribution.md).
- Thirteen JSON fixtures plus explanatory expected outcomes; standard-library reference contract/HTTP mocks; Mosquitto CLI replay/capture; isolated optional test-broker configuration.
- Automated fixture/contract, actual request-handler, transport/tool and documentation checks.
- Eleven V1 task cards with twelve fields each; A1–A7, B1–B7 and E1–E5 retained, including all eight V2 tasks. Deadlines remain November 16 and December 5, 2026.
- Sole Spring Boot aggregation assigned to Ankit; B3 repurposed explicitly as individual-twin consistency/handoff. The required fleet twin remains Ankit's materialized output. No production behavior or root README changed.

## Observed checks

| Check | Observed result / evidence |
|---|---|
| `python3 -B -m unittest discover -s tests -p 'test_v1_*.py' -v` | 31 tests collected: 25 passed, 6 skipped because local socket creation is forbidden. No failure/error in final run. |
| Existing baseline modules loaded with standard-library unittest | 80 passed, zero failures/errors: fault mapper/details, result summary, pipeline evaluator, latency recorder, twin verifier, Ditto HTTP and action adapter. External HTTP calls are mocked. |
| Render cycle piped to offline `check --expect-cycle` | Accepted 4 events; cycleComplete=true. Validates the tool/fixtures, not a live MQTT pipeline. |
| Both tool `--help` commands | Exit 0; command-line interfaces available without external services. |
| Optional mock broker `docker compose ... config --quiet` | Exit 0; configuration parsing only, no broker started. |
| JSON parsing | 28 JSON files valid: 14 existing, 13 V1 fixtures and one endpoint example. Negative fixtures are semantically invalid, not broken JSON syntax. |
| Python AST parsing | 52 existing/new Python files parse successfully. |
| Local documentation links / task completeness | Automated checks cover the edited source-of-truth/task documents, new contract/guide, fixture guide and this record; all local targets resolve, all eleven V1 cards have twelve fields, task IDs and dates remain. |
| `git diff --check` | Passed for the preparation changes. |
| Full `python3 -B -m pytest -q -ra -m 'not integration'` | Could not start: `No module named pytest`. This is an environment limitation, not a passing full suite. |

The six skipped tests are in `tests/test_v1_mocks.py`: Ditto read/feature identity; state/clock freshness; provider routing/context/clear; provider rejection/timeout/refused connection; backend preview counts/actions; invalid controls. Their request-routing and state assertions are additionally exercised without sockets in `tests/test_v1_mock_handlers.py`. Actual bind/listen/client transport remains unverified here and must run without skips on a normal developer host.

Tests were introduced before the executable contract/mocks. Initial runs failed because the components were absent; subsequent green runs validated the implementations. Additional red/green cases covered strict wire decoding and the versioned preview API. This is development-tool verification, not evidence of live V1 acceptance.

## Environment and unverified work

Python 3.14.3 is installed; CI uses 3.12. Pytest, KUKSA client, Protobuf/grpc_tools and Mosquitto CLI clients are absent. Docker Compose parses configuration, but Docker daemon access is denied. Local `socket.socket` creation raises PermissionError. Java 25 is installed rather than the backend/CI target Java 21; no usable system/cached Maven was found. Node is unavailable.

Consequently, these were not verified: real MQTT broker/client replay/capture; bound HTTP server startup and transport tests; Java 21 Maven checks; production Docker builds; live KUKSA/Velocitas/Ditto/Spring/dashboard integration; fleet-twin persistence; Linux Kanto restart. No services, registries or deployment targets were changed. Commands for those activities in the guide are explicitly labelled unverified.

## Skills and unrelated worktree changes

Applied the repository copies of test-driven-development, verification-before-completion and systematic-debugging. The initial copies used `skills/SKILL-*.md`; during the task an external worktree edit renamed them to `skills/test-driven-development.md`, `skills/verification-before-completion.md` and `skills/systematic-debugging.md`. Those unrelated renames are not part of these commits. The referenced `writing-good-tests.md` support file is absent; its use is unclaimed. Upstream provenance is not pinned by this task, and this entry does not establish V1-06 completion for the three developers.

## Remaining decisions and completion limits

- Contract is proposed for affected-owner review. Historical approval provenance of the scope is unconfirmed; no runtime shared interface was changed.
- The user explicitly directs Ankit's aggregation ownership. This adjusts B3 transparently; the older scope/architecture continue as historical context pending team review.
- The five-second freshness threshold is configurable. The proposed thirty-second unavailable threshold, one-second future tolerance and two-second dispatch/update budgets require review and measurement.
- Exact deployed ports, credentials, image versions and clock synchronization must be recorded during implementation/integration. Example endpoint JSON is not a production configuration loader.
- Baseline context URL, tire-pressure units, timestamp preservation, verifier correctness and identity/routing defects are assigned to owners in task cards; they are not fixed in production by this PR.
- Actual two-vehicle CI, live acceptance, fleet twin/dashboard agreement, Kanto evidence, original-skill use/review, tagged release, report/video and contributions remain outstanding. V2 features and responsibilities remain intact.

No full V1 completion is claimed. No push or merge is authorized/performed by this preparation task.
