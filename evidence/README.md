# SDV project evidence

Use this index to connect each Phase V1 acceptance criterion to implementation and observed results. Criteria follow [scope and acceptance](../docs/08-project-scope-and-acceptance.md). Add the PR or commit, verification result and demo timestamp where applicable.

Status clarification — November 14, 2026 UTC: component merges do not establish complete live acceptance. See the [MVP → Phase V1 comparison](../docs/findings/mvp-to-v1-comparison.md) for the assessed main SHA, evidence boundaries, recalculated timings and unresolved provenance.

| Criterion | Evidence to collect | Lead | Status / links |
|---|---|---|---|
| V1-01 | Two synthetic vehicles publish independently through separate brokers and apps. | Emmanuel | Edge publication verified live (E1); twin/API integration pending. [E1 record](v1/E1-two-vehicle-edge.md) |
| V1-02 | Live MQTT events update the correct Ditto twins. Invalid inputs leave both twins intact. | Bayan | IMPLEMENTED + MOCK-VERIFIED ingress/writer (#30/#31); real twin persistence and negative-input acceptance PENDING. [Twin handoff](../ditto/V1-TWINS.md) |
| V1-03 | Vehicle 002 faults and recovers in Ditto and the API. Vehicle 001 stays healthy. | Ankit, with Emmanuel and Bayan | [A3 mock-backed routing evidence](v1/scenario-routing.md); edge fault/recovery cycle verified live ([E2 record](v1/E2-lidar-cycle.md)); full backend → provider → MQTT → twin cycle pending |
| V1-04 | API reads match live twin state and identify stale or missing data. | Ankit | [A2 implementation and backend-to-mock checks](v1/live-twin-api.md); live Ditto verification pending |
| V1-05 | Baseline regression and relevant tests pass. Identify mocked and live dependencies. | Ankit, with component owners | Current-main CI and single-vehicle pipeline passed; two-vehicle live acceptance CI PENDING. Exact revision/runs in the [comparison](../docs/findings/mvp-to-v1-comparison.md). |
| V1-06 | Record skill source, task, human review and verification against the spec. | All teammates | E1/E2 and A5 usage recorded in [skill usage](v1/skill-sources.md); A2/A3 examples in their evidence records. Complete provenance and human-review evidence PENDING. |
| V1-07 | Reproduce the tagged V1 and submit the demo, report and contribution evidence. | Ankit, with all teammates | Pending |
| V1-08 | Fleet API, materialized summary and dashboard agree for both individual twins. | Ankit | [A5 component and Java/browser mock-backed checks](v1/fleet-dashboard.md); live integrated acceptance pending |
| V1-09 | Linux/Kanto restarts app-002 and a fresh event reaches its live twin. | Bayan | Static preparation IMPLEMENTED; live launch/restart-to-twin acceptance PENDING. [Pilot scope and limitations](../velocitas-app/kanto/V1-PILOT.md) |

- [MVP baseline](v1/baseline.md)
- [Phase V1 skill sources and usage](v1/skill-sources.md)

- [A2 live twin API setup and verification](v1/live-twin-api.md) — component checks executed; real Ditto and affected-owner review pending.

- [A3 scenario routing setup and verification](v1/scenario-routing.md) — actual Spring Boot to prepared mocks; live propagation pending.

- [A5 fleet dashboard setup and verification](v1/fleet-dashboard.md) — Java API/writer and Chrome checks executed with controlled HTTP substitutes; real Ditto/MQTT acceptance pending.
