# SDV project evidence

Use this index to connect each Course V1 acceptance criterion to implementation and observed results. Criteria follow `09-project-scope-and-acceptance.md`. Add the PR or commit, verification result and demo timestamp where applicable.

| Criterion | Evidence to collect | Lead | Status / links |
|---|---|---|---|
| V1-01 | Two synthetic vehicles publish independently through separate brokers and apps. | Emmanuel | Edge publication verified live (E1); twin/API integration pending. [E1 record](v1/E1-two-vehicle-edge.md) |
| V1-02 | Live MQTT events update the correct Ditto twins. Invalid inputs leave both twins intact. | Bayan | Pending |
| V1-03 | Vehicle 002 faults and recovers in Ditto and the API. Vehicle 001 stays healthy. | Ankit, with Emmanuel and Bayan | Edge cycle verified (E2); backend/Ditto/UI run pending. [E2 record](v1/E2-lidar-cycle.md) |
| V1-04 | API reads match live twin state and identify stale or missing data. | Ankit | Pending |
| V1-05 | Baseline regression and relevant tests pass. Identify mocked and live dependencies. | Ankit, with component owners | Pending |
| V1-06 | Record skill source, task, human review and verification against the spec. | All teammates | E1 entry recorded; other tasks pending. [Skill usage](v1/skill-sources.md#e1-two-vehicle-edge-publication-v1-01) |
| V1-07 | Reproduce the tagged V1 and submit the demo, report and contribution evidence. | Ankit, with all teammates | Pending |

- [MVP baseline](v1/baseline.md)
- [V1 skill sources and usage](v1/skill-sources.md)
