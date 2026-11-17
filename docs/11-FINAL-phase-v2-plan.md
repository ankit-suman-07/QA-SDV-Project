# Phase V2 — Final Delivery Plan

**Due:** December 5, 2026. **Team:** Ankit Suman, Bayan Sayyadifar and Emmanuel Adegboye.

This working plan redistributes supporting CARLA work so Emmanuel can focus on the simulator. Align the source-of-truth, scope and task distribution with this allocation before dependent implementation; preserve completed V1 contributions and evidence.

## 1. Goal and objective

Complete a reproducible local SDV fleet health-monitoring and diagnostic platform for **three CARLA vehicles total**, each with front LiDAR. Maintain isolated individual twins and one fleet twin; demonstrate targeted diagnostics and recovery; and evaluate customized development skills against their pre-prepared originals.

Extend the verified V1 pipeline: CARLA/adapter → KUKSA → Velocitas → MQTT → validated ingress → Ditto → Spring Boot → dashboard. Spring Boot retains the sole fleet aggregator and fleet-twin writer. Kanto manages a selected Linux edge app; one agreed real uProtocol exchange and one supported OpenSOVD operation complete the diagnostic integration.

## 2. Remaining work

- **CARLA and observations:** deploy three actors, map stable vehicle IDs and publish compact front-LiDAR observations with source timestamps. Keep raw point clouds outside Ditto. Record ground truth separately.
- **Telemetry mapping:** retain existing signals where supported. Derive speed from CARLA motion; agree whether battery, temperature and tire pressure remain synthetic, label their provenance and validate units.
- **Health and recovery:** implement agreed degradation/dropout and recovery-window behavior; verify boundaries, freshness and vehicle isolation using deterministic scenarios and replay fixtures.
- **Twins and fleet views:** extend ingestion to the third twin; complete required history and diagnostic records; verify individual twins, fleet counts/materialization and dashboard through healthy, faulty, recovering and unavailable states.
- **Diagnostics and lifecycle:** track selected actions through acceptance, execution, success/failure and timeout using correlated IDs. Demonstrate agreed uProtocol/OpenSOVD operations and repeat Kanto launch/restart with fresh CARLA-backed data reaching the correct twin.
- **Skills and evaluation:** customize skills using cited course concepts; retain original/customized versions and compare outputs on comparable tasks. Measure detection, propagation, recovery, delivery/update success and CPU/memory under recorded workloads, reporting sample counts and variability.
- **Final delivery:** preserve synthetic regression/CI, run real three-vehicle acceptance, consolidate MVP–V1–V2 evidence, document contributions and limitations, and finish the final report, video and reviewed release.

## 3. Task distribution

| Member | Remaining responsibility |
|---|---|
| **Emmanuel — CARLA and sensor source** | Own CARLA installation/run configuration, three actors and front-LiDAR sensors, actor-to-vehicle mapping and extraction of compact observations. Supply basic controlled degradation/dropout/restoration scenarios, separate ground truth, a sample observation and replay fixture. Record source versions, settings and component evidence. |
| **Ankit — adapter integration, backend and final quality** | Own adapter-to-KUKSA publication, units/timestamp validation and telemetry provenance. Extend backend, the single fleet aggregator/writer and dashboard to three vehicles; implement diagnostic action status/history and correlate results from Bayan's services. Lead integration, CI, runtime measurements, stage comparison, evidence consolidation and final release/submission. |
| **Bayan — edge health, twins and diagnostics** | Own Velocitas health/recovery rules and observation-to-event tests, including sensor dropout/restoration. Extend individual-twin ingestion/routing and required history to three vehicles; verify ordering, consistency and isolation. Implement the agreed uProtocol exchange and OpenSOVD operation; coordinate CARLA-backed Kanto validation with Ankit. Do not build another fleet aggregator. |
| **All three** | Agree shared contracts and bounded diagnostic operations; customize relevant skills with course references and comparable evaluation cases; review interfaces/PRs, supply owned tests/evidence and document actual contributions. |

## 4. Suggested completion order

1. **Freeze the baseline and interfaces:** record the tested V1 reference, close or explicitly carry forward open findings/decisions, agree observation/recovery/diagnostic contracts and the revised ownership. Save original skills before customization.
2. **Prove one CARLA vehicle end to end:** Emmanuel supplies observations; Ankit connects KUKSA/backend; Bayan validates health events/twin ingestion. Use replay fixtures so supporting work can proceed independently of CARLA uptime.
3. **Develop in parallel:** Emmanuel extends scenarios/actors; Ankit completes adapter, action tracking and fleet/UI changes; Bayan completes health rules, third-twin support and uProtocol/OpenSOVD integration. Capture skill evaluations during real development, not retrospectively.
4. **Integrate all three vehicles:** run targeted fault/recovery, isolation, stale/unavailable, diagnostic failure/timeout and CARLA-backed Kanto restart checks. Preserve the synthetic fallback as labelled regression evidence, not CARLA acceptance.
5. **Evaluate and finish:** collect repeated measurements and original/customized-skill comparisons; complete traceability, report/video, contribution records, reviews and the final reproducible release.

**Completion means recorded acceptance evidence, not merged code alone.** Keep deployment local; CARLA may run on a separate capable host. Beam, CANought, a second sensor type and fourth/fifth vehicles remain optional. Full autonomous driving is outside scope.
