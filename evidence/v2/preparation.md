# V2 independent-development preparation evidence

Package 2.0.0-prep.1; November 17, 2026. Main baseline
`140e6ffe4b939cb643654d862e46cd5a83be4d74`; branch
`ankit/docs/v2-independent-development-prep`. Clean starting tree; fetched origin,
no existing preparation branch/PR found. No AGENTS.md found in repository/ancestors.

Scope: development docs, synthetic inputs/independent expected JSON, reference
oracle, loopback HTTP and CLI feeder only. No production implementations changed.
V1 strict decoder, timestamps, availability/classification reused via imports;
V1 fixture/tool behavior remains untouched. No existing shared development source
changed, so V1 regression reruns were unnecessary. Python 3.14 was used on Linux;
3.10+ compatibility is based on the standard-library features used, not an OS matrix run.

## Checks and limits

| Command/check | Result |
|---|---|
| `python -m scripts.v2_dev.check` | Passed: 22 labelled JSON fixtures, 8 offline tests (validation, health/recovery/silence/ordering/clock/fleet/actions), local Markdown links/heading syntax |
| `python -m unittest tests.test_v2_http -q` | Passed, actual ephemeral loopback: reads, unknown target/routes, invalid clock, conditional feature initialization/update (201/204/412/428), correlation/state rejection, provider identity/V1 200 active-flag semantics, 409/503/504 and fleet aging |
| `python -m scripts.v2_dev.replay --ack-development-only --sequence recovery --vehicle vehicle-003` | Passed: 7 deterministic observation deliveries; health mode 7; silence mode 2 observations + 3 clock controls |
| `git diff --check` | Passed; 7 new Python files also parsed with ast; local links in the 3 updated source documents resolve |
| Optional MQTT | Not run: mosquitto_pub/sub unavailable; no install, image pull or broker launch needed |
| Optional KUKSA/native SDK/live checks | Not run; no local Maven/cached up-java artifact, no selected native transport/provider. See feasibility record |

Sandbox initially disallowed socket binding; the exact HTTP test passed with
loopback permission. No unrelated process was stopped. No CARLA, Kanto daemon,
full-stack startup, system install, image build or benchmark was performed.

Initial development check correctly failed because the V2 module did not yet
exist; not claimed as a completed assertion-based TDD red cycle. An actual later
failure exposed a clock-test assumption: rebasing changes UTC expected values as
well as input, so the assertion now compares the rebased committed expectation.
Added assertion-based red tests for missing silence evaluation and retained
sensor-failure fault; both failed before implementation and passed afterward.
The health feeder was corrected to preserve the retained fault during recovery.
No production code was changed to satisfy a fixture. Repo TDD,
systematic-debugging and verification-before-completion instructions were read;
user's focused-check scope overrides their full-suite advice. Supporting
writing-good-tests/root-cause-tracing skill files are absent; use unclaimed.
Original skill files preserved; no customization or V2 skill evaluation claimed.

## Review and handoff

[Contracts](../../docs/v2-interface-contracts.md), [owner matrix/commands](../../docs/v2-independent-development.md),
[native source inspection/blockers](../../docs/v2-native-diagnostic-feasibility.md).
New defaults (cadence, gap, extraction, session registration, history bound,
action deadlines) need affected-owner review before production use. Remaining
bindings: live observation companion delivery, native uProtocol transport/service
addressing/protobuf, native OpenSOVD vehicle/provider/DTC mapping and deployment auth.
Fixtures and mocks intentionally do not resolve these by pretending native support.

Resume if interrupted: keep this branch, inspect git status and recorded commits;
focused checks are complete. Finish publication if still pending; avoid duplicate PRs.
Do not merge/tag or start production features. After merge record resulting main
SHA and have all owners branch from that same preparation commit; squash SHA may
differ from this branch tip. Mock-tested is not live V2 acceptance.
