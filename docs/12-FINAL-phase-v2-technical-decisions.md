# Phase V2 — Technical Decisions and Implementation Baseline

**Version:** 1.0 · **Date:** November 17, 2026 · **Decision owner:** Ankit, Bayan, Emmanuel

**Purpose:** Give Ankit, Bayan and Emmanuel one technical direction for the final phase. This records project-lead decisions, not approval on behalf of other members or evidence that an integration already works. Add this document to `SOURCE-OF-TRUTH.md` and align the V2 contracts/task distribution before dependent code changes. Preserve the verified V1 baseline and historical evidence.

## 1. Final objective and architecture

Deliver a reproducible local platform for **three CARLA vehicles total**, monitoring LiDAR health, maintaining isolated individual twins and one fleet twin, and supporting traceable diagnostic actions and recovery. Complete customized-skill evaluation and final submission evidence.

**Telemetry:** CARLA → observation adapter → per-vehicle KUKSA → per-vehicle Velocitas app → Mosquitto/MQTT → validated ingress → Ditto → Spring Boot → dashboard.

Spring Boot owns the **single fleet aggregator and fleet-twin writer**. The fleet API derives its summary from individual twins; the materialized fleet Thing stores the derived summary. Bayan owns individual-twin ingestion, not a second fleet aggregator. Kanto manages the selected Linux edge application.

## 2. Decisions to follow

| Area | Decision |
|---|---|
| Fleet and identity | Use `vehicle-001`, `vehicle-002` and `vehicle-003`, each mapped to one CARLA actor, one front LiDAR, one KUKSA broker and one vehicle app. Keep mappings stable within a run and record them. Never run duplicate publishers for one identity. |
| LiDAR observations | Publish compact nearest-obstacle distance in metres and sensor availability. Agree the front region/filter and invalid-frame behavior in the adapter contract before coding; use the same definition in tests and ground truth. Keep raw point clouds outside Ditto. |
| Supporting telemetry | Derive speed from CARLA motion. Battery, temperature and tire pressure may remain synthetic; label their source explicitly. Use documented units consistently: speed km/h, battery %, temperature °C and VSS tire pressure kPa. Convert explicitly for any legacy psi boundary. |
| Identity and timing | Preserve vehicle ID, unique event ID and original observation time through the pipeline. Keep CARLA simulation time distinct from UTC; document their mapping and clock assumptions. Processing/publish time must never make an old observation appear fresh. Preserve action/trace context where available. |
| Health classification | Keep V1 LiDAR distance thresholds: **≤5 m CRITICAL**, **>5 m to ≤10 m WARNING**, **>10 m HEALTHY**. Explicit unavailable/invalid sensor input must not be treated as a healthy long-distance reading. Velocitas owns health decisions; the simulator supplies observations and separate ground truth. |
| Recovery window | After a fault, require **two seconds of continuous valid healthy observations** before clearing it. Do not infer continuity by repeatedly reading one cached sample. A renewed fault, invalid input or observation gap resets the recovery window. During recovery, retain the fault and expose a separate recovery state through the revised V2 contract. |
| Freshness | Retain V1 defaults: age **≤5 s AVAILABLE**, **>5 s to ≤30 s STALE**, **>30 s UNAVAILABLE**, with existing one-second future tolerance. Evaluate source silence separately from sensor classification. Stale/unavailable vehicles must not count as currently healthy. |
| Diagnostics | Support vehicle-targeted obstruction inject, clear and managed application restart. Track **ACCEPTED → EXECUTING → SUCCEEDED / FAILED / TIMED_OUT**, retaining action/trace IDs and evidence. Acknowledgement is not execution success; clearing an action does not establish observed recovery. Preserve V1 dispatch/failure semantics through an explicit V2 mapping. |
| uProtocol | Implement one correlated vehicle-health request/response using a supported uProtocol implementation. Keep MQTT as the established telemetry path. Demonstrate actual sender/receiver behavior and failure handling, not just serialization helpers. |
| OpenSOVD | Implement one supported read of vehicle-specific diagnostic faults through the selected implementation. Map actual project faults consistently. Do not label a custom mapper or ordinary REST endpoint as full OpenSOVD integration. |
| Kanto | Repeat managed launch/stop/start for a selected CARLA-backed app on Linux. Require clean lifecycle results and a fresh post-start observation matching MQTT and the real twin. Restore a suppressed upstream sensor separately; restart alone cannot restore absent input. |
| Deployment | Use local hosts/containers. CARLA may run on a separate capable host. Record pinned versions/images, LAN endpoint mappings where used, persistent runtime paths and secret-free configuration. Preserve synthetic runs for CI and regression. |

**Required contract detail:** Observation cadence/gap limits, sensor-dropout signaling, recovery fields, diagnostic transport deadlines and execution budgets must be recorded in the V2 interface contract with their rationale before dependent work. Do not choose different values independently in each component or silently alter V1 fixtures/schemas.

## 3. Integration checks before freezing APIs

The uProtocol/OpenSOVD operations above are selected functional targets, not claims about a particular SDK's API. **Bayan** verifies supported implementations, versions, operation paths and failure behavior using a minimal working exchange. **Ankit** records the request/result mapping, permissions and bounded timeout behavior. Document compatible custom adapters accurately.

If an operation is unsupported, record the evidence and bring the smallest supported alternative to Ankit for a decision. Do not silently replace it with a mock or claim completion. Review authenticated read/write subjects, permissions and any cross-host TLS requirements without embedding credentials in contracts or evidence.

## 4. Ownership and completion order

| Owner | Implementation focus |
|---|---|
| **Emmanuel** | CARLA runtime, actors/LiDAR, stable mapping, extraction of observations, basic controlled scenarios, ground truth and sample/replay inputs. |
| **Ankit** | Adapter-to-KUKSA publication, units/timing validation, backend/action tracking, fleet/UI integration, CI, measurements and final acceptance/release coordination. |
| **Bayan** | Velocitas health/recovery logic, observation/event tests, three-twin ingestion and history, uProtocol/OpenSOVD integration and coordinated Kanto validation. |

1. Record V1 baseline; align this document, ownership and V2 contracts. Save original skill versions.
2. Agree one observation/replay fixture and prove one CARLA vehicle through the real pipeline. Prototype the selected diagnostic exchanges in parallel.
3. Extend to three vehicles, add recovery/action tracking and exercise the CARLA-backed Kanto lifecycle.
4. Run repeatable positive/negative integration cases, measurements and skill comparisons; then finalize evidence, reviews, report/video and release.

## 5. Evaluation and change control

- Record labelled scenario input, detection/recovery, propagation, observed update success, isolation and CPU/memory. Retain failures, sample counts and variability. Use adequate samples for any P95/P99 claim; report measurement boundaries and clock uncertainty. Do not claim an MVP speedup from unlike scenarios.
- Each member customizes relevant skills using cited course concepts. Compare original/customized versions on comparable starting code, tasks and acceptance criteria; record model/tool settings and human intervention. Capture the comparison during development, not retrospectively.
- Completion requires real three-vehicle twin/API/fleet/dashboard agreement, diagnostic success/failure/timeout evidence, CARLA-backed Kanto evidence and reproducible release material. Label mocked, synthetic and live boundaries explicitly.
- Use focused PRs. Update the contract, fixtures/tests and this decision record together when a shared decision changes; record the reason and review before dependent merges. Existing repository review rules remain in effect.

**Out of scope:** full autonomous driving, physical vehicles, safety certification and raw continuous point-cloud storage in Ditto. Beam, CANought, a second sensor type and additional vehicles remain optional.
