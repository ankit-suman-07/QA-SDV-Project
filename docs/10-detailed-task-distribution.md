# SDV fleet enhancement — Detailed task distribution

Course V1 is due **November 16** and uses two synthetic vehicles. Course V2 is due **December 5** and extends that workflow to three CARLA vehicles with front LiDAR. Task IDs below map to acceptance criteria in [09-project-scope-and-acceptance.md](09-project-scope-and-acceptance.md). Runtime flows are in [10-architecture-diagrams.md](10-architecture-diagrams.md).

## Ankit — Architecture, Spring Boot integration and quality

| Task | Work | Done when |
|---|---|---|
| A1 · V1 contracts | Lead agreement on vehicle-to-provider/broker/twin mappings, event payloads, health states, API responses and fault/clear requests. Give both teammates sample payloads and expected results. | The team approves examples for normal, fault and recovery states and can develop against them independently. |
| A2 · V1 live state API | Add or connect the Ditto client and expose vehicle-specific health through Spring Boot. Use source timestamps to distinguish fresh, stale and missing state. | API responses match live Ditto for both vehicles, including a stale or unavailable source case. Covers V1-04. |
| A3 · V1 scenario routing | Route inject/clear requests by registered vehicle ID to Emmanuel’s provider endpoints. Validate unsupported vehicles/actions and surface failures. | A request for vehicle-002 reaches only its provider. Rejection and provider failure have observable outcomes. Supports V1-03. |
| A4 · V1 integration and submission | Assemble the local stack with both owners. Run the baseline regression and a repeatable fleet fault/clear test. Capture API responses, twin state and correlated events. Tag V1 and coordinate the video and report. | Vehicle-002 changes healthy → fault → healthy. Vehicle-001 stays healthy. Record the exact commands, revision and test/CI results. Covers V1-03, V1-05 and V1-07. |
| A5 · V2 fleet views | Integrate individual and fleet twins into the APIs and dashboard. Show vehicle health, availability, active faults and diagnostic history. | Dashboard and API agree with live Ditto during a fault, recovery and availability change. Supports V2-03. |
| A6 · V2 diagnostic backend | Define the request/result contract with Bayan. Validate dashboard requests, route to the agreed diagnostic service and correlate acceptance, execution result, timeout and failure using vehicle/action/trace IDs. | A selected action reaches the correct vehicle, produces observable execution evidence and shows its outcome on the dashboard. Covers V2-04. |
| A7 · V2 evaluation and release | Own system integration, CI and repeatable measurements. Collect detection, propagation and recovery timings and resource use under recorded workloads. Compare MVP, V1 and V2 and consolidate the report. | A clean local rerun reproduces the demo and recorded measurements. Tests and reports label synthetic, mocked and live evidence. Covers V2-08. |

## Bayan — Messaging, Ditto and edge deployment

| Task | Work | Done when |
|---|---|---|
| B1 · V1 MQTT ingress | Subscribe to Velocitas events through Mosquitto. Validate identity and required fields and preserve event ID and source time. Coordinate sample events with Emmanuel. | A valid event reaches the bridge. Malformed events and unknown IDs cannot alter either twin. |
| B2 · V1 twin routing | Provision two live Ditto twins. Map vehicle IDs to twin IDs and write the agreed health/fault fields. Give Ankit twin IDs, read examples and startup instructions. | Events for both vehicles land in their respective twins. A vehicle-002 fault and clear update only its fault state. Covers V1-02 and supports V1-03. |
| B3 · V2 fleet twins | Provision the third vehicle twin and implement fleet aggregation, fault history, and duplicate/out-of-order handling. Agree how freshness and availability affect fleet counts with Ankit. | Individual twins and fleet counts agree for healthy, faulted, recovered and unavailable vehicles. Duplicate or late events cannot undo newer state. Supports V2-03. |
| B4 · V2 diagnostics integration | With Ankit, select one real uProtocol exchange and one supported OpenSOVD operation. Document addressing, request/result mapping and correlation. Capture runtime evidence for each. | Both agreed operations execute against their selected implementations. Record exact operations, failure handling and any adapter limitations. Covers V2-06. |
| B5 · V2 Kanto | Deploy the selected Velocitas app on Linux with Kanto. Confirm access to its broker and MQTT, then restart the app and capture fresh events. | Kanto status and logs show launch/restart, and a fresh event reaches the correct twin afterward. Covers V2-05. |

## Emmanuel — Simulation, LiDAR and Velocitas

| Task | Work | Done when |
|---|---|---|
| E1 · V1 two-vehicle edge | Configure two synthetic providers, two KUKSA brokers and two Velocitas apps. Assign unique IDs and non-conflicting endpoints. Document the signal fields and units. | Both edge instances publish independently and their events carry the agreed vehicle IDs. Covers V1-01. |
| E2 · V1 fault and clear | Supply a deterministic LiDAR fault/clear scenario for vehicle-002 and give Ankit the provider command contract. Give Bayan examples of the healthy, fault and recovery events. | The scenario can be rerun locally. Vehicle-002 emits the expected transitions and vehicle-001 receives no injected fault. Supports V1-03. |
| E3 · V2 CARLA adapter | Set up CARLA and connect three actors with front LiDAR to their respective edge instances. Preserve actor/vehicle mapping, source timestamps, units and labelled injection timing. Document startup and cleanup. | All three vehicles publish identifiable LiDAR observations through their correct brokers. A reproducible configuration and runtime evidence cover V2-01. |
| E4 · V2 sensor diagnosis | Implement controlled degradation and dropout scenarios. In Velocitas, evaluate observation age and agreed health thresholds, then apply the recovery window once valid input resumes. | Labelled runs and boundary tests establish when a fault is raised and cleared, with other vehicles unaffected. Covers V2-02. |
| E5 · V2 runtime handoff | Give Bayan the app build/configuration and Ankit the scenario commands, ground truth and runtime observations. Keep the synthetic scenario available for CI and comparison. | Both teammates can reproduce a fault and recovery with documented inputs and identify the source of each measured transition. |

## Integration order and reviews

1. **V1 contracts first.** Ankit coordinates. Emmanuel supplies publisher and simulator examples. Bayan supplies twin IDs and a representative read response. Agree the command, event and state fields before connecting services.
2. **V1 build in parallel.** Emmanuel runs the edge instances, Bayan tests the bridge against representative events and Ankit tests API/command behavior against the agreed contracts. Then run one live fault/clear scenario through the full stack before recording.
3. **V2 validate the runtime early.** Emmanuel verifies CARLA and LiDAR acquisition. Bayan verifies Kanto on Linux and identifies supported diagnostic operations. Ankit freezes backend contracts once those interfaces are clear.
4. **V2 integrate telemetry before actions.** Prove three-vehicle telemetry and fleet views, then verify targeted diagnostic outcomes and Kanto restart. Run measurement trials after the integrated workflow is repeatable.
5. **Review at handoffs.** Bayan reviews Emmanuel’s event contract, Ankit reviews Bayan’s twin/diagnostic interface, and Emmanuel reviews Ankit’s scenario targeting. Each owner verifies their component. Ankit coordinates cross-system acceptance.

## Evidence and spec-driven development

Save evidence under `evidence/v1/` and `evidence/v2/`. Each owner adds a short entry with the task/acceptance ID, PR or commit, reproduction command, expected and observed result, and a log, CI or demo link. Use `evidence/README.md` as the index. Ankit consolidates the reports and records gaps or partial results explicitly.

For V1, each teammate records an actual use of a pre-prepared skill, its source/version, the acceptance criteria, and how they reviewed and verified the output. For V2, record a customized skill diff, course concept and comparable original/customized evaluation. Track which checks caught meaningful defects or changed the result. These entries support V1-06 and V2-07.

The exact uProtocol exchange and OpenSOVD operation are V2 contract decisions. Report synthetic fallback and Docker-only runs as partial evidence for CARLA and Kanto respectively. Beam remains optional.
