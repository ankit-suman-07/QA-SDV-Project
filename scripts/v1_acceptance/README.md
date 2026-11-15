# Phase V1 real acceptance

Run from a clean checkout of this branch with Java 21, Python 3.12, Docker Compose,
Git, a supported browser and at least the upstream Ditto requirements (2 CPU/4 GB),
plus capacity for both edges and the observer. Port 3000 must be free (the existing
backend CORS allowlist). No shared deployment is targeted. The runner obtains the
official Ditto 3.8.4 source at `5dbb05e6294e5ac0103506102baff9eab755d180`, verifies
its SHA, uses its nginx authentication and pins Ditto images to 3.8.4. Actual image
identities are captured; mutable third-party image tags are a remaining limitation.

Inspect `docker ps -a`, `docker compose ls`, and local Ditto configuration first.
Use the legitimate credentials from that **local sample's** authentication setup,
through `SDV_ACCEPTANCE_DITTO_USERNAME`, `SDV_ACCEPTANCE_DITTO_PASSWORD`, and
`SDV_ACCEPTANCE_DITTO_SUBJECT`; do not paste them into commands, evidence or PRs.
The runner requires all three and records no environment dump. It never uses a
shared endpoint, fabricates a credential or resets an existing Thing/policy.
The isolated stack intentionally uses the one supplied sample subject for reads,
individual writes and fleet writes; production separation of authenticated subjects
and permissions still needs review. Policy failures revoke only selected writes on
new test-owned policies, restoring the original policy in `finally`.

```bash
python3.12 -m venv /tmp/v1-acceptance-env
/tmp/v1-acceptance-env/bin/pip install -r requirements-test.txt -r scripts/v1_acceptance/requirements.txt
/tmp/v1-acceptance-env/bin/python -m playwright install chromium
(cd backend && bash ./mvnw --batch-mode --no-transfer-progress clean verify)
# Securely export the three local-sample credential variables before this command.
/tmp/v1-acceptance-env/bin/python -B -m scripts.v1_acceptance.run
```

Each invocation requires a new output directory (default UTC
`evidence/v1/verification-<timestamp>/`). Reuses the production two-edge Compose,
real ingress/writer, packaged Java and dashboard. No HTTP recording writer, simulated
Ditto or mock control endpoint participates. Missing service/runtime/auth/browser
blocks readiness (exit 2); assertion failures exit 1. All required live gates must
pass for exit 0. That exit excludes separately tracked baseline and Kanto gates and
**does not mean all Phase V1 accepted**. Existing baseline CI remains required.

Read `results.json`: unreached boundaries remain BLOCKED. The runner collects
manifest/SHA/dirty state, secret-free rendered configuration, command exits/outputs,
process logs, MQTT, correlated twin/API/fleet snapshots, screenshots, resources and
raw trials/statistics with hashes. Track a reviewed secret-free run durably, or cite
the exact Actions run/artifact ID and retention. Do not link ignored/untracked logs
as durable evidence. Never upload raw environment or Docker inspect credentials.

Fault/clear enters actual A3; dispatch acknowledgement and health completion are
separate. All command boundaries share one observer monotonic clock; polling and
scenario progression are included. Source-to-twin timestamps assume container/source
and observer share the host kernel UTC clock, with no measured clock error bound;
they are observations, not pure transport latency. Trials retain timeouts. API and
scheduled fleet materialization evaluate at different times: compare count invariants
and event identities, not blindly equal `generatedAt` fields. The dashboard is read
through a real headless browser with no intercepted API responses.

Apps are stopped for isolated synthetic negative/replay probes; these are labelled
component integration, separate from real-provider trials. Exactly two production
vehicle identities remain configured. Invalid/unknown/mismatched, duplicate/equal/late
inputs are checked individually, followed by a persisted-watermark restart and valid
successor. Individual write denial must leave its snapshot unchanged while the other
vehicle progresses. Fleet denial must preserve individual reads and resume writing.
Source silence exercises source-derived aging and removal of the isolated feature
exercises explicit unavailable/null fields. MQTT reconnect and an actual KUKSA outage
exercise recovery; provider recovery never manually starts the provider to pass.

Cleanup restores test-induced stopped brokers, clears test-owned scenarios, stops
owned processes and runs `down` on unique projects without volume deletion. It does
not stop unrelated services. SIGTERM/interrupt takes the cleanup path; SIGKILL cannot
run cleanup, so recover using the recorded project/configuration commands. Docker
images/caches and anonymous stopped-stack data may remain; no shared volume resets.

Pending wording alignment: the independent docs PR assigns all remaining V1 work to
Ankit and corrects the architecture read path. This branch uses current main's C1–C10
without importing those commits or approving proposed defaults. Kanto/V1-09, affected
owner approvals, original-skill provenance, report/video/contributions and release
tag are separate release prerequisites. Provider F01 and tire-unit F02 remain open
on main until their fix PRs merge and regressions pass.

CI prerequisite: configure Actions secrets `V1_LOCAL_DITTO_USERNAME` and
`V1_LOCAL_DITTO_PASSWORD` from the pinned local sample's existing authentication,
and variable `V1_LOCAL_DITTO_SUBJECT` with its nginx subject. No production/shared
endpoint or credentials are needed. Missing values produce a BLOCKED readiness
artifact and a failed job; there is no skip or mock substitution. The pre-existing
single-vehicle pipeline workflow remains unchanged and required. Artifacts use the
exact Actions run/attempt identifier and 30-day retention; attach durable copies
before that retention expires.

## Explicit local deployment preparation and open defects

The unmodified official stack run found two further release blockers, retained in
`verification-20261115T023435Z`: the existing individual provisioning CLI creates no
`v1` feature (Ditto properties-only PUT returns 404), and the packaged Spring client
sends duplicate `Accept-Encoding` fields (Ditto returns
`gateway:duplicate.header.field`, HTTP 400). Direct Java HTTP clients do not
reproduce the second error; the packaged Spring client does.

To make subsequent boundaries testable without changing application code, this
isolated deployment explicitly normalizes `Accept-Encoding` at nginx and bootstraps
the initial individual feature from the **first real MQTT observation** for each
vehicle, before starting ingress. `bootstrap-real-observations.json` retains those
source/event IDs. These seed writes are provisioning, not ingress success evidence;
subsequent real observations and all fault/recovery transitions must traverse the
actual ingress. No observation or healthy value is invented, and no concurrent
writer is introduced. This prepared configuration does not demonstrate that the
unmodified provisioning workflow or unmodified proxy stack works. Release needs
approved production provisioning and proxy/client compatibility remediation with
regressions, in addition to the two already open fix PRs and Kanto. The compatibility
preparation is part of the recorded configuration, not a silently accepted contract
change or a resolution of those defects.

Text evidence is authentication-redacted before command outputs are retained and
again before final hashing/upload. Fresh text output trailing whitespace is
normalized. Source/event IDs, timestamps, results and exits are preserved; reviewed
hashes identify these secret-free artifacts. Do not upload older raw service logs
without applying the same review/redaction.


## HTTP compatibility correction — November 15, 2026

The Ditto reader and fleet writer now explicitly advertise one `Accept-Encoding:
gzip, deflate` field. Spring 7.0.8's automatic compression otherwise supplies two
values that the JDK emits separately; original nginx forwards them and Ditto rejects
the duplicate fields. Compression decoding, timeouts, authentication and TLS remain
unchanged. The acceptance launcher now mounts upstream nginx unchanged. The earlier
prepared-deployment normalization below/above is historical. Feature initialization
is a separate independent fix and its historical bootstrap is not closed by this PR.
