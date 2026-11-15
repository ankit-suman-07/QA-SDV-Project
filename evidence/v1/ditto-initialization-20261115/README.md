# V1-F03 — safe first-observation feature initialization

Ankit; Phase V1 V1-02, supporting V1-03/04/05. Baseline main
`6a965bb` (merged PR #43), original checkout clean at `4bead79`, fetched/switched
main and `git pull --ff-only` succeeded before branch creation. No existing task
branch/PR was found. Persistent worktree: `$HOME/.local/share/qa-sdv-v1/worktrees/ditto-initialization`.
Independent branch: `ankit/fix/v1-ditto-feature-initialization`, based on main only.

## Actual correction

Authenticate and validate the existing Thing, then GET the V1 feature. A failed
Thing/feature read is not absence or permission to write. Only a real feature 404
allows conditional feature PUT with `If-None-Match: *`. This endpoint cannot create
a missing Thing. Later updates validate persisted identity/schema/watermark, preserve
feature metadata and use the feature GET ETag with `If-Match`. Missing ETag or
concurrent 412 fails closed. No whole-Thing replacement or fabricated health.
Uncertain/conflicting persistence invalidates the ingress cache, preserves MQTT
pending semantics and reloads the stored watermark before retry/rejection.

Feature-level READ/WRITE permission is required. This corrects persistence behavior,
not approval of production authentication subjects or the proposed shared contract.
No application defaults, wire schema or Thing/vehicle identities were changed.

## Test-first and actual verification

- [Red](red.txt): 4 new behavior failures, 5 passes, against old production writer.
  Path-accurate substitutes reproduce real Ditto's missing-parent 404.
- [Targeted green](green.txt): 66 tests and 40 subtests passed. Covers first fault
  observation/context, legacy preservation, restart replay, creator/update races,
  failed authorization/missing/transport responses, absent ETag and uncertain commit.
- [First broader regression](python-regression.txt): 19 failures, 516 passes,
  376 subtests, 2 skips, 9 deselections. Deep-input MemoryHTTP returned whole Things
  for every GET and nested any PUT under properties; it did not model subresources.
  Updated that test substitute to model real feature paths and conditional headers;
  no poison-input validation/ACK assertion removed or relaxed.
- [Final documented Python regression](python-regression-final.txt): **531 passed,
  386 subtests, 2 explicit skips, 9 integration tests deselected**. SDK-native unit
  and externally configured publisher integration are the skips, not live passes.
- [Real Ditto result](live.json): new uniquely named test-owned Things/policies in
  existing real Ditto 3.8.4, no shared reset. Starts with V1 absent; actual captured
  vehicle-001 MQTT observations initialize then conditionally update V1. Exact event,
  source, properties match; test legacy feature survives. A new Ingress object
  reloads the watermark and rejects replay. [First](twin-0.json)/[next](twin-1.json).
  Observer-only namespace mapping isolates logical vehicle IDs from shared sdv twins.
  This is real-resource verification, not a newly deployed full Ditto stack and not
  a repeated end-to-end fleet/fault harness. [Non-mutating preflight error](preflight-failure.json)
  retains the initial invalid observer namespace rejection before any resources existed.

Reproduction: run `live_initialization.py` with the documented persistent Python3.12
environment from this worktree, existing MQTT 18883 and Ditto18080. It derives the
sample auth in memory from the restored official source and creates a fresh namespace
on each run. Namespaced resources are retained for inspection; no shared twin/policy
or volume is deleted. No new ingress or publisher/service was started/stopped.
Historical evidence and existing workloads remain intact.

Applied repository TDD, systematic-debugging and verification-before-completion
instructions. Their exact current files remain in Git at the baseline; unavailable
supporting technique/writing-good-tests files are not claimed. Human review pending.
Combined candidate, exact-head CI and release approval remain separate work.

The acceptance launcher now starts the sole ingress without manual telemetry
bootstrap. Its complete clean-start integrated execution is reserved for Part D.
