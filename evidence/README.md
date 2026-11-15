# SDV project evidence

## Current engineering checkpoint — November 15, 2026

[Release-readiness assessment](../docs/findings/v1-release-readiness.md) supersedes
outdated blocker statements in the historical matrix below. PR #43 is merged;
same-device V1-09 managed restart passed. Draft fixes #44/#45/#46 close F03/F04/
shutdown at their recorded boundaries; all eight CI checks pass at each exact head.
[UNMERGED INTEGRATION CANDIDATE](v1/release-candidate-20261115/README.md) passed
clean initialization without telemetry bootstrap, original-nginx HTTP compatibility,
five routed fault/clear trials through real twins/API/fleet/dashboard, aging,
negative/restart/denied-write checks and affected MQTT reconnect. Changed lifecycle
also passed three actual Kanto cycles with exit0. These are not merged-main or
full-V1 acceptance claims. Approvals/provenance qualifications, final merged-SHA
checks, release decision and report/video deliverables remain pending. Report/video
creation/recording/submission were excluded from this work. Historical results below
are retained with their original dates and limitations.


Use this index to connect each Phase V1 acceptance criterion to implementation and observed results. Criteria follow [scope and acceptance](../docs/08-project-scope-and-acceptance.md). Add the PR or commit, verification result and demo timestamp where applicable.

Status clarification — November 14, 2026 UTC: component merges do not establish complete live acceptance. See the [MVP → Phase V1 comparison](../docs/findings/mvp-to-v1-comparison.md) for the assessed main SHA, evidence boundaries, recalculated timings and unresolved provenance.

| Criterion | Evidence to collect | Lead | Status / links |
|---|---|---|---|
| V1-01 | Two synthetic vehicles publish independently through separate brokers and apps. | Emmanuel | LIVE-VERIFIED on the prepared isolated two-edge deployment; source/event identity checked. One 12s KUKSA outage recovered in the 1s workload; historical F01/#38 remains open. [New run](v1/verification-20261115T024001Z/README.md). |
| V1-02 | Live MQTT events update the correct Ditto twins. Invalid inputs leave both twins intact. | Bayan | LIVE-VERIFIED on prepared real Ditto: invalid/unknown/mismatched/duplicate/equal/late invariance, policy-denied writes and persisted-watermark restart. Initial feature bootstrap remains a production setup gap. [Dated results](../docs/findings/v1-implementation-verification.md#follow-up--2026-11-15-utc-integrated-acceptance-on-an-isolated-prepared-deployment). |
| V1-03 | Vehicle 002 faults and recovers in Ditto and the API. Vehicle 001 stays healthy. | Ankit, with Emmanuel and Bayan | Five real A3 fault/clear trials reached MQTT, twin, API, fleet Thing and browser with 001 isolated on the prepared stack. Dispatch is separate from completion. [Trials](v1/verification-20261115T024001Z/measurements.json). Full V1 remains unaccepted. |
| V1-04 | API reads match live twin state and identify stale or missing data. | Ankit | LIVE-VERIFIED source-derived aging and explicit unavailable/null fields on prepared real Ditto; unmodified Spring/proxy header compatibility remains unresolved. [Run](v1/verification-20261115T024001Z/README.md). |
| V1-05 | Baseline regression and relevant tests pass. Identify mocked and live dependencies. | Ankit, with component owners | Java21/Python/frontend, existing live baseline, KUKSA and isolated MQTT checks passed locally; new real two-vehicle CI job and artifacts added in draft #41. Final-SHA live CI status must be checked; no blanket CI pass claimed. [Commands/exits](v1/verification-20261115T024001Z/external-checks.json). |
| V1-06 | Record skill source, task, human review and verification against the spec. | All teammates | E1/E2 and A5 usage recorded in [skill usage](v1/skill-sources.md); A2/A3 examples in their evidence records. Complete provenance and human-review evidence PENDING. |
| V1-07 | Reproduce the tagged V1 and submit the demo, report and contribution evidence. | Ankit, with all teammates | Pending |
| V1-08 | Fleet API, materialized summary and dashboard agree for both individual twins. | Ankit | LIVE-VERIFIED prepared deployment: five fault/recovery trials, counts/materialized fleet Thing/browser and fleet-write denial/recovery. Setup compatibility preparation and production remediation remain open. [Run/screenshots](v1/verification-20261115T024001Z/README.md). |
| V1-09 | Linux/Kanto restarts app-002 and a fresh event reaches its live twin. | Bayan | BLOCKED / REQUIRED: no genuine Linux/Kanto launch/restart-to-fresh-MQTT-and-real-twin evidence. Ankit owns remaining validation. [Exact prerequisites](../docs/findings/v1-implementation-verification.md#ci-kanto-and-release-prerequisites). |

- [MVP baseline](v1/baseline.md)
- [Phase V1 skill sources and usage](v1/skill-sources.md)

- [A2 live twin API setup and verification](v1/live-twin-api.md) — component checks executed; real Ditto and affected-owner review pending.

- [A3 scenario routing setup and verification](v1/scenario-routing.md) — actual Spring Boot to prepared mocks; live propagation pending.

- [A5 fleet dashboard setup and verification](v1/fleet-dashboard.md) — Java API/writer and Chrome checks executed with controlled HTTP substitutes; real Ditto/MQTT acceptance pending.

Dated update — November 15, 2026 UTC: Ankit owns **all remaining** Phase V1
remediation, integration, Kanto and release work. Lead names above preserve component
contribution history. The prepared-deployment results do not close unmodified setup
failures, #38/#39, V1-09, approvals or submission gates. Original findings/evidence
remain preserved. [Latest dated verification](../docs/findings/v1-implementation-verification.md#follow-up--2026-11-15-utc-integrated-acceptance-on-an-isolated-prepared-deployment).
