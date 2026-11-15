# Fresh merged-main verification — November 15, 2026

Tested **main `4afbbd8c11425a9e0e1701fea66b7ed13731abfe`**, initially clean detached
persistent worktree `~/.local/share/qa-sdv-v1/worktrees/merged-main-verification`.
[Baseline and merge SHAs](baseline.json). Only new untracked evidence/tooling was
present during execution; no tracked implementation changes. Earlier candidate
results retain their original labels and SHAs.

## Fresh results

- [Python](python.txt):541 passed +386 subtests;2 explicit skips (host native SDK
  absent and optional external MQTT test unset),9 integration deselections. Actual
  packaged SDK/MQTT are exercised live below; skips are not counted as passes.
- [Java21 clean verify](java.txt):209 tests,0 failures/errors/skips; packaged executable
  jar built from this exact main. Includes actual transport header regressions.
- [Frontend](frontend.txt):7 tests pass. Both Compose configurations pass, and the
  implementation tree equals the previously tested candidate at49f8b8d. See
  [checks](checks.json), [command outcomes](commands-summary.json),
  [versions/clock/source identities](versions-and-state.json).
- [Focused real smoke](../merged-main-live-20261115T191503Z/selected-gates-review.json):
  all four selected gates PASS: readiness, clean real first-observation initialization,
  packaged Spring individual reads/fleet writes/dashboard, one routed fault/clear
  with001 isolation, persisted watermark/ingress restart controls. The upstream
  Ditto3.8.4 nginx is mounted unchanged; no header normalization or telemetry seeding.
  [Before publishers](../merged-main-live-20261115T191503Z/clean-before-publishers.json)
  proves V1 absent on both Things. Unique project/network/DB, create-only provisioning;
  no shared twin/policy reset. Raw commands, images, screenshots and boundaries are
  retained in that directory. The Spring process runs the freshly packaged jar.
- [Actual Kanto](../merged-main-kanto-live-20261115T191810Z/independent-review.json):
  three managed restart cycles PASS plus final cleanup, all application exits0,
  four completed shutdown log entries, exact MQTT/event/full Ditto properties match.
  Each fresh source exceeds previous source, start request and Kanto runtime start;
  source/runtime margins1.350233s,0.873631s,5.490585s.174 final healthy001 twin samples
  (168 before cleanup); maximum observed sampling gap0.426044s. Old sampled PIDs
  absent, Docker app002 remained stopped and namespace preflight excluded other
  running apps. Final managed state stopped/pid-1, no overlapping publisher observed.
  [Fresh main image](image.json), [OCI index](image-index.json), [build](image-build.txt).
  Operator used normal sudo; no permissions changed. Raw commands/states/logs retained.

## Verification-tool summary correction

The fresh live wrapper erroneously required the result dictionary to contain only
four entries; the underlying harness preallocates other unselected gates. Therefore
its original [console](live-console.txt), process exit1 and raw aggregate FAIL are
**preserved**. All four selected per-gate results passed independently. The
[offline reviewer](review_results.py) checks those named gates and the Kanto raw
artifacts; it passed. [Original wrapper](live_smoke-original-summary.py) and
[corrected wrapper](live_smoke.py) are both saved. Correction affects summary
selection only; no implementation change or service rerun. Unselected BLOCKED/not-
reached entries are honest coverage limits, not failures of executed product gates.

## Inherited scope and remaining gates

Broader five-trial distributions, source aging/null, denied writes, dependency
outages and legacy regression evidence remain inherited from explicitly labelled
candidate/fix runs. Main implementation equivalence plus fresh exact-main CI
(baseline pipeline and real two-vehicle acceptance) is recorded in [final state](final-state.json).
This is focused post-merge verification, not repetition of the full experiment.

No remote-LAN or automatic crash restart verified; no full V1 acceptance or release.
C1–C10, production authentication/TLS, freshness/timing/clock and LAN wording need
actual owners; historical skill provenance and missing raw-log qualifications stay
open. Report/video creation, recording/submission excluded and pending.

## Cleanup and durability

Only owned smoke projects were taken down without deleting volumes; original edge,
app001, Ditto/MongoDB and sole ingress remain active. Dedicated Kanto daemon remains;
new pilot is stopped and retained. Original Docker app002 stays stopped. Original
policies/twins/volumes, historical evidence and docker_default preserved. Raw stop
exits of third-party services are retained, not relabelled as clean app exits.

All essential text/JSON/screenshots are tracked in PR47. The large OCI archive is
retained at the persistent runtime path with its SHA256 in image.json and reproducible
build command; it is not a release artifact. Authentication redaction and whitespace
normalization are recorded in [normalization metadata](text-normalization.json).
No credentials are required in tracked artifacts.

The harness's original artifact-sha256 manifest is retained. Additional redaction
passes transformed its source/config snapshots; text-normalization.json records
before/after hashes. final-artifact-sha256.json identifies the final reviewed bytes;
validate_artifacts.py verifies original hashes or the exact recorded transformation.
