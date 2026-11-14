# SDV project evidence

Use this index to connect each Course V1 acceptance criterion to implementation and observed results. Criteria follow `09-project-scope-and-acceptance.md`. Add the PR or commit, verification result and demo timestamp where applicable.

| Criterion | Evidence to collect | Lead | Status / links |
|---|---|---|---|
| V1-01 | Two synthetic vehicles publish independently through separate brokers and apps. | Emmanuel | Edge publication verified live (E1); twin/API integration pending. [E1 record](v1/E1-two-vehicle-edge.md) |
| V1-02 | Live MQTT events update the correct Ditto twins. Invalid inputs leave both twins intact. | Bayan | Pending |
| V1-03 | Vehicle 002 faults and recovers in Ditto and the API. Vehicle 001 stays healthy. | Ankit, with Emmanuel and Bayan | [A3 mock-backed routing evidence](v1/scenario-routing.md); real provider/MQTT/twin cycle pending |
| V1-04 | API reads match live twin state and identify stale or missing data. | Ankit | [A2 implementation and backend-to-mock checks](v1/live-twin-api.md); live Ditto verification pending |
| V1-05 | Baseline regression and relevant tests pass. Identify mocked and live dependencies. | Ankit, with component owners | Pending |
| V1-06 | Record skill source, task, human review and verification against the spec. | All teammates | E1 entry recorded; other tasks pending. [Skill usage](v1/skill-sources.md#e1-two-vehicle-edge-publication-v1-01) |
| V1-07 | Reproduce the tagged V1 and submit the demo, report and contribution evidence. | Ankit, with all teammates | Pending |
| V1-08 | Fleet API, materialized summary and dashboard agree for both individual twins. | Ankit | [A5 component and Java/browser mock-backed checks](v1/fleet-dashboard.md); live integrated acceptance pending |

- [MVP baseline](v1/baseline.md)
- [V1 skill sources and usage](v1/skill-sources.md)

- [A2 live twin API setup and verification](v1/live-twin-api.md) — component checks executed; real Ditto and affected-owner review pending.

- [A3 scenario routing setup and verification](v1/scenario-routing.md) — actual Spring Boot to prepared mocks; live propagation pending.

- [A5 fleet dashboard setup and verification](v1/fleet-dashboard.md) — Java API/writer and Chrome checks executed with controlled HTTP substitutes; real Ditto/MQTT acceptance pending.
