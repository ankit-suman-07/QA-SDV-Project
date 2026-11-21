# Reproducible V2 measurements and comparison

Starting main `c5b358f824ce6230342c12a99a35cbf3b84eb3e5` includes merged
integration PR #60. PR #54 was still open and draft, local Python found no
CARLA module, no nvidia-smi or pidstat was on PATH, and Docker reported only
the existing V1 prerequisite containers. No agreed live V2 runtime was
available. Live trials, raw V2 performance values, and resource samples
are **BLOCKED**. No services were started or changed.
[Integration readiness](../three-vehicle-integration/README.md) ·
[Stage comparison](../../../../docs/findings/mvp-v1-v2-comparison.md)

## Trial procedure once the joined gate is met

1. Complete the [one- and three-actor trace check](../../../../scripts/v2_acceptance/README.md)
   on the exact implementation. Save all owner SHAs, image digests, host/CPU
   and RAM layout, CARLA/client versions, actor/sensor mapping, map, seed,
   LiDAR settings, 10 Hz target and actual cadence, publisher and polling
   settings, simulation-to-UTC anchor, and sample capture locations. Pin
   the load and resource target list before the first trial.
2. Use three registered vehicles with two untouched peers. After a bounded
   warm-up of 15 s at steady load, perform five trials with an isolated
   obstruction and clear on vehicle-002. Use the same initial geometry,
   actual motion, scenario script and polling rates each time, with a
   maximum 60 s from inject to final recovery capture. Re-establish the
   initial state between trials. Report precondition failures, deadline
   exits and interruptions as observed. Do not retry them out of the
   denominator. Use a separate workload file for dropout or restart.
3. Record actual independent CARLA ground-truth transition timestamps,
   using the same manifest mapping as the observations. Preserve source UTC
   and vehicle/event IDs from C2. Save host UTC synchronization observations
   and max pairwise uncertainty before and after, including source anchor
   uncertainty; record monotonic sampling and UTC offset on each observer.
   Same-host elapsed measurements may use local monotonic differences.
   Never subtract clocks from unrelated hosts without a measured bound.
   Record a separate missing-data finding if a bound cannot be established.
4. Retain sanitized source, MQTT, confirmed twin-write and independently
   sampled API/browser artifacts. Select each trial's closed observation
   window and eligible source IDs ahead of aggregation. Use the same
   observer cutoff across stages and report its drain duration; choose the
   source inclusion portion so all eligible events have that observation
   opportunity. Link evidence for detection and recovery event selection,
   proving at least two seconds of continuous healthy evidence and the
   maximum permitted gap. The calculator computes intervals from the
   selected events. It does not reclassify health or prove recovery continuity.

## Boundaries and calculation

| Quantity | Start and end |
|---|---|
| Detection | Actual obstruction ground truth → source UTC of first matching fault classified by Velocitas. Keeps scenario command/dispatch delay outside the metric. |
| Propagation | Original eligible source UTC → first same-identity observation at each capture stage. Separate companion MQTT, Velocitas health MQTT, confirmed Ditto commit, API response and browser render. API and browser observations include poll/scheduling overhead. This is observed latency by stage, not pure network transport. |
| Observed recovery | Actual ground-truth clear → source UTC of first recovered observation. Also report first eligible continuously healthy source sample → recovered source UTC. Measure browser arrival separately through propagation. |
| Delivery/update coverage | At each stage, unique matched (vehicleId,eventId) pairs divided by eligible unique source identities from the trial, also split by vehicle. Report companion receipt, classified health receipt, confirmed Ditto write and API/browser observation separately. Report unmatched and duplicate samples. Empty captured stage means zero matches; omitted stage means not captured. API/browser ratios include polling undersampling and do not estimate packet loss. |
| CPU and memory | Sample named owned containers around 2 s apart, bounded by the trial window and deadline. Preserve actual sample UTC and timing. Use Docker stats CPU percent (100% can mean one fully used CPU) and the used-memory side of MemUsage as shown by Docker. Normalize MiB/GiB to bytes, preserving the original display and its precision. Record Docker version, limits and host. Process RSS or remote CARLA may be measured separately where tooling exists; keep method and host distinct and leave missing targets blank. |

For raw Docker collection on a provisioned host, pass only recorded container
names to `timeout 8s docker stats --no-stream --format '{{json .}}' "$@"`.
Attempt at most 30 samples per trial. Save capture-start/end UTC and command
exit for each attempt. Attribute a successful sample to its end UTC; retain
failed/unparseable tool output separately. A slow stats call may lower actual
sample frequency. Do not replace failed reads with zeros or estimate CARLA
resource use from other containers.

## Input and rerun

Keep the capture manifest and raw traces from the acceptance run. Create one
normalized JSON file per workload under a run-specific evidence directory.
Top-level keys are `scope` (`JOINED_CARLA` or `SYNTHETIC_CHECK`),
`implementationSha`, `clockUncertaintyMs` (worst-case pairwise error),
and `trials` (1–20 unique trial IDs). A trial object contains:

- `id`, `target`, `windowStart`, `windowEnd`, `status` (PASS, FAILED or
  TIMED_OUT), and `reason` for failures/timeouts. Retain available
  evidence on every failed trial.
- `source` containing eligible rows with vehicleId/eventId/sourceTimestamp.
  `stages` maps any captured boundary (`companion`, `health`, `twin`,
  `api`, `browser`) to rows with vehicleId/eventId/observedAt. Normalize
  lastEventId from downstream records without changing source identity.
  Use actual observer UTC for observedAt, not sourceTimestamp or generatedAt.
- Optional UTC `obstructionAt`, `clearAt`, and target `faultEventId`,
  `firstHealthyEventId`, `recoveredEventId`. Omit an unavailable marker
  and retain the reason with the trial evidence.
- Optional `resources` with target/sampledAt/cpuPercent/memoryBytes.
  Retain the raw stats or local process samples separately for review.

```bash
python -m scripts.v2_acceptance.measure "$sdv_v2_trial_capture" > "$sdv_v2_measurement_summary"
```

Extract the first receipt for each identity and preserve duplicates in the raw
data. The summary reports per-trial n, median, min/max and sample standard
deviation where n ≥2. Across-trial variability uses trial medians with one
vote per trial, across recorded partial successes as well as completed trials
where samples exist. Check the reported n against all statuses. Negative UTC
intervals beyond the uncertainty bound appear as clock conflicts and are
excluded from timing statistics; values inside that bound are retained.
Exit 0 means the input was summarized and says nothing about whether the
trial succeeded. Exit 1 indicates invalid data and exit 2 missing input.
No percentile or speedup claim follows from five trials.

## Dated verification-skill comparison

On November 21, 2026, used both versions on the
[planned case](../../../../skills/v2/ankit/verification-before-completion/README.md)
with the same Git-exported `e3b4a6af5421a3b9c88e2c16f51d78f929052990`
checkout, Python 3.14.10, read scope and offline commands. The original and
customized assessments and actual command outputs are preserved here.
[Original](skill-original.txt) · [Customized v1.0.0](skill-customized.txt)

One Codex coding session executed the original first and the customized
follow-up second. No separate workers or human edits intervened. The exact
model ID, sampling settings and independent per-arm time budget were not
exposed or established. Self-review used the planned five criteria.

| Criterion | Original | Customized |
|---|---|---|
| Unregistered successor rejected | Met | Met |
| Registered successor retains CRITICAL in recovery | Met | Met |
| Retired delivery rejected | Met | Met |
| Command, SHA and observed result traceable | Met | Met |
| Synthetic proof and live binding/approval distinguished | Met | Met |

Both arms passed the checker, with the same number of commands and no
observed product defect or correction on this case. The customized assessment
made the requirement-to-assertion mapping explicit. The assessments tied on
coverage. Shared session context and order can influence the difference;
there is no historical baseline or independent human review claim. This
bounded comparison is recorded while the planned independent evaluation and
review remain open.

## Verification

Tested `5bd5506c06d6d2fa335a9bc6d46bd0fcace81752`. Applied Ankit
verification-before-completion v1.0.0 to the collector's expected counts,
clock conflict, retained timeout and process evidence boundaries.

- `python -m unittest tests.test_v2_measure tests.test_v2_trace -q` exited 0,
  eight tests. A separate CLI smoke serialized the measurement unit test's
  temporary synthetic input, confirmed its scope, one PASS trial and two
  duplicates, and observed BLOCKED/exit 2 for an absent input.
- `python -m scripts.v2_dev.check` exited 0, eight tests and 23 fixture files
  plus referenced guide links.
- Python 3.12 CI-equivalent `python -m pytest -q -ra -m "not integration"`
  with the five existing protobuf modules generated into a temporary
  PYTHONPATH exited 0 with 581 passed, 461 subtests passed, 2 skipped
  (V1 MQTT host and native SDK), and 9 deselected.
- Local comparison, skill and evidence links resolved.
  `git diff --check origin/main HEAD` passed. No Java, frontend or
  production runtime files changed. No owned services remain running.
