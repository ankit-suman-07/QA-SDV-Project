# Reading Guide for the Autonomous Multi-Vehicle SDV Project Enhancement

## Proposed Research Topic

**Design and Evaluation of a Reproducible Open-Source Digital-Twin Platform for Monitoring and Diagnosing Sensor-Enabled Vehicle Fleets**

## 1. Updated Project Context

The completed project is a single-vehicle Software-Defined Vehicle health-monitoring and diagnostic platform. It uses a vehicle simulator, Eclipse Kuksa, Protobuf-based uProtocol-style messaging, Eclipse Ditto, an OpenSOVD-compatible diagnostic mapper, a Java/Spring Boot backend and a web frontend. It monitors vehicle signals, detects correlated faults, synchronizes a vehicle digital twin and supports runtime diagnostic actions.

The enhancement will extend this system into a multi-vehicle platform that:

- Simulates 3–5 independently identifiable vehicles.
- Adds a camera or LiDAR sensor to each simulated vehicle.
- Processes sensor data into observations such as detected objects, obstacle distance, lane status and sensor health.
- Maintains one detailed digital twin per vehicle.
- Maintains one fleet-level digital twin that aggregates the state of all vehicles.
- Provides fleet-wide monitoring and vehicle-specific remote diagnostics.
- Uses Eclipse Velocitas for standardized vehicle applications.
- Uses Eclipse Kanto for deployment and lifecycle management at the simulated vehicle edge.
- Optionally uses Eclipse CANought for J1939 and UDS translation.
- Evaluates scalability, latency, reliability, consistency, diagnostic behaviour and resource usage.

The project concerns **autonomous sensing and fleet monitoring**, not full autonomous driving, motion planning or vehicle control.

The literature review should cover five connected areas:

1. Digital twins for connected and autonomous vehicles.
2. Multi-vehicle and fleet-level digital-twin modelling.
3. Camera and LiDAR simulation, perception and data abstraction.
4. Vehicle-edge application deployment and management.
5. Scalability, synchronization, reliability and experimental evaluation.

---

## 2. Essential Readings

These sources should be read first because they most closely match the proposed architecture and evaluation.

### 2.1 Edge-Based Digital Twins for Connected and Autonomous Vehicles

**C. Campolo et al., “An Edge-Based Digital Twin Framework for Connected and Autonomous Vehicles: Design and Evaluation,” _IEEE Access_, vol. 12, 2024.**  
[Open using the DOI](https://doi.org/10.1109/ACCESS.2024.3382001)

This paper proposes an edge-based digital-twin framework connecting onboard sensing, vehicle-edge processing and remote applications. It is the closest architectural reference for the enhancement.

**Questions to answer while reading:**

- Which data is processed at the vehicle edge, and which data is forwarded remotely?
- How are sensor observations represented semantically?
- Which communication and computation costs are measured?
- Which parts of the architecture can be reproduced with Kuksa, Velocitas, Kanto and Ditto?

### 2.2 CARLA: Autonomous-Vehicle and Sensor Simulation

**A. Dosovitskiy et al., “CARLA: An Open Urban Driving Simulator,” _Proceedings of the Conference on Robot Learning_, 2017.**  
[Read the open-access paper](https://proceedings.mlr.press/v78/dosovitskiy17a.html)

CARLA is an open-source simulator developed for autonomous-driving research. It supports multiple vehicles, cameras, LiDAR and configurable driving environments.

**Questions to answer while reading:**

- Can CARLA provide the required multi-vehicle and sensor workload within available hardware limits?
- Which sensor outputs are necessary for this project?
- Should the platform process raw sensor data or use simulator-provided ground-truth observations?
- How can simulations be seeded and repeated for reproducible experiments?

CARLA is a candidate simulator, not a mandatory choice. A lighter deterministic sensor simulator may be selected if CARLA creates excessive hardware or integration cost.

### 2.3 Vehicular Digital-Twin Synchronization

**X. Yang et al., “Data Synchronization for Vehicular Digital Twin Network,” _IEEE GLOBECOM_, 2022.**  
[Open the paper on IEEE Xplore](https://ieeexplore.ieee.org/document/10000831/)

This paper studies synchronization between physical vehicles and their digital twins under changing network conditions.

**Questions to answer while reading:**

- How is synchronization performance defined?
- How should twin freshness and staleness be measured?
- How do increasing vehicles and update rates affect synchronization?
- Which assumptions differ from the proposed open-source implementation?

### 2.4 Synchronization Frequency and Communication Cost

**J. Zheng et al., “Data Synchronization in Vehicular Digital Twin Network: A Game Theoretic Approach,” _IEEE Transactions on Wireless Communications_, vol. 22, no. 11, 2023.**  
[Open using the DOI](https://doi.org/10.1109/TWC.2023.3254158)

This paper examines trade-offs among synchronization frequency, communication cost and digital-twin performance.

Use it to consider:

- Whether all vehicle and sensor attributes need the same update rate.
- Whether critical faults should have higher priority than routine observations.
- How the fleet twin can remain useful without copying every individual-twin update.

### 2.5 Cooperative Perception and Traffic Digital Twins

**“Towards Cooperative Perception Services for ITS: Digital Twin in the Automotive Edge Computing Context,” _Energies_, vol. 14, no. 18, 2021.**  
[Read the open-access article](https://doi.org/10.3390/en14185930)

This work demonstrates a cooperative-perception prototype that maintains a digital representation of road activity using perception information.

Focus on:

- The division between perception, edge processing and the digital twin.
- How detected objects are represented.
- Communication rates and freshness requirements.
- The difference between cooperative perception and the proposed fleet-health use case.

### 2.6 Connecting Vehicle Perception to Cloud Digital Twins

**“Bridging Edge Vehicle Perception and Cloud Digital Twins to Enhance Road Safety,” _Smart Cities_, vol. 8, no. 6, 2025.**  
[Read the open-access article](https://doi.org/10.3390/smartcities8060197)

This paper connects onboard perception and edge processing to a cloud-hosted digital twin. It is useful for deciding which camera or LiDAR results should be sent to the platform.

**Questions to answer while reading:**

- Which perception outputs are forwarded rather than raw sensor streams?
- What delays occur between observation and twin update?
- Which failure cases and evaluation metrics are included?
- What remains unexplored for multiple vehicles and open-source SDV components?

### 2.7 Testing and Validation of Autonomous-Vehicle Systems

**P. Koopman and M. Wagner, “Challenges in Autonomous Vehicle Testing and Validation,” _SAE International Journal of Transportation Safety_, 2016.**  
[Open using the DOI](https://doi.org/10.4271/2016-01-0128)

The project does not attempt to validate a complete autonomous-driving system. This paper is useful for understanding why scenario diversity, repeatability, edge cases and explicit safety claims matter when evaluating autonomous-vehicle software.

---

## 3. Architecture and Systems Foundations

### 3.1 Edge Computing

**W. Shi et al., “Edge Computing: Vision and Challenges,” _IEEE Internet of Things Journal_, vol. 3, no. 5, 2016.**  
[Open using the DOI](https://doi.org/10.1109/JIOT.2016.2579198)

Use this paper to justify why high-volume or latency-sensitive sensor processing should occur near the vehicle rather than inside the remote digital-twin platform.

Apply it to these design decisions:

- Process camera or LiDAR data in the simulated vehicle-edge environment.
- Send compact observations and health information to Ditto.
- Keep the cloud/platform side responsible for fleet aggregation, historical views and remote diagnostics.

### 3.2 Hierarchical Digital-Twin Modelling

The proposed system uses two levels:

1. **Individual vehicle twins:** detailed telemetry, perception results, health, faults and diagnostic history.
2. **Fleet twin:** aggregate vehicle counts, fleet health, alerts and references to individual twins.

The literature review should compare this hierarchical design with a monolithic design that embeds all vehicles inside one large twin. Evaluate the expected effects on isolation, update contention, query complexity, scalability and fault containment.

### 3.3 Data Abstraction

Continuous raw camera video and complete LiDAR point clouds should not be stored directly in Eclipse Ditto. The research should examine how raw sensor streams can be transformed into compact twin properties, such as:

- Object count and object classes.
- Nearest-obstacle distance.
- Lane-departure state.
- Sensor availability and confidence.
- Observation timestamp and sequence number.
- Reference to an externally stored sample, when required.

This boundary should be documented as part of the architecture and evaluated through message size, update latency and resource usage.

---

## 4. Project-Specific Technical Documentation

These official sources connect the research concepts to implementation:

- [Eclipse Ditto documentation](https://eclipse.dev/ditto/): Things, features, policies, messages, connectivity and digital-twin updates.
- [Eclipse Kuksa Data Broker documentation](https://eclipse-kuksa.github.io/kuksa-databroker/): standardized vehicle-signal access.
- [COVESA Vehicle Signal Specification](https://covesa.github.io/vehicle_signal_specification/): standardized signal names and schemas.
- [Eclipse Velocitas development model](https://eclipse.dev/velocitas/docs/concepts/development_model/): development of containerized vehicle applications and typed vehicle-model access.
- [Velocitas Kanto runtime guide](https://eclipse.dev/velocitas/docs/tutorials/vehicle_app_runtime/kanto_runtime/): deployment of Velocitas applications using Kanto.
- [Eclipse Kanto container management](https://eclipse.dev/kanto/docs/concepts/container-management/): container lifecycle, monitoring, restart policies and resource management at the edge.
- [Eclipse CANought project scope](https://projects.eclipse.org/projects/iot.kanto.canought/governance): optional J1939 and UDS translator services for automotive communication.
- [Eclipse OpenSOVD repository](https://github.com/eclipse-opensovd/opensovd): service-oriented vehicle diagnostics.
- [CARLA sensor documentation](https://carla.readthedocs.io/en/latest/ref_sensors/): camera, LiDAR and other simulated sensors.

When reading documentation, separate **available platform features** from **features actually implemented and experimentally verified**. The final paper must make only evidence-supported claims.

---

## 5. Preliminary Research Gap

The following is a provisional gap and must be validated through a systematic literature search:

> Existing research examines autonomous-vehicle simulation, vehicular digital-twin synchronization, cooperative perception and edge-based digital-twin frameworks. However, there appears to be limited reproducible experimental evidence showing how a modular, fully open-source SDV stack behaves when multiple sensor-enabled vehicles, individual twins and a fleet-level twin are integrated with vehicle application and edge-lifecycle frameworks. In particular, the combined effects on twin consistency, update latency, diagnostic correctness, vehicle isolation, recovery and resource usage require further empirical evaluation.

The contribution is not simply adding three Eclipse components or increasing the vehicle count. The publishable contribution should be:

1. A reproducible hierarchical digital-twin architecture for a sensor-enabled vehicle fleet.
2. A documented method for converting vehicle and perception data into individual and fleet-level twin state.
3. An empirical evaluation of scalability, consistency, fault detection, recovery and resource cost.
4. Evidence explaining the benefits and overheads introduced by Velocitas, Kanto and optional CANought integration.

---

## 6. Candidate Research Questions

### Primary research question

> How effectively can a reproducible open-source hierarchical digital-twin architecture monitor and diagnose a fleet of simulated sensor-enabled vehicles under increasing workloads and component failures?

### Supporting research questions

**RQ1 — Scalability**  
How do vehicle count and signal-update rate affect latency, throughput, message loss and resource usage?

**RQ2 — Twin consistency**  
How accurately and quickly do individual vehicle twins and the fleet twin converge after telemetry, perception, fault and recovery events?

**RQ3 — Sensor-data abstraction**  
What are the communication and computation effects of forwarding processed perception observations rather than high-volume raw sensor data?

**RQ4 — Reliability and isolation**  
Can the system preserve correct vehicle-specific state when sensors, applications or communication paths fail, recover or produce concurrent events?

**RQ5 — Edge-management overhead**  
What deployment, recovery and resource-use effects result from running vehicle applications through Velocitas and Kanto compared with the completed baseline?

**RQ6 — Fleet aggregation**  
What latency and consistency overhead is introduced by maintaining a fleet-level twin in addition to individual vehicle twins?

---

## 7. Suggested Experimental Design

### 7.1 Compared configurations

1. **Completed baseline:** One vehicle using the existing simulator-to-Ditto pipeline.
2. **Multi-vehicle configuration:** Multiple vehicles and individual twins without autonomous-sensor observations.
3. **Sensor-enabled configuration:** Multiple vehicles with camera or LiDAR observations and hierarchical twins.
4. **Managed-edge configuration:** Sensor-enabled configuration with Velocitas applications and Kanto lifecycle management.
5. **Optional automotive-communication configuration:** Managed-edge configuration with CANought integration.

### 7.2 Independent variables

- Vehicle count: for example, 1, 3, 5, 10 and 20 simulated vehicles.
- Fully demonstrated vehicles: 3–5.
- Telemetry and perception-event publication rate.
- Camera or LiDAR observation size and frequency.
- Concurrent diagnostic-action count.
- Fault type: vehicle fault, sensor failure, communication loss or application crash.
- Kanto restart or redeployment event.
- Network latency and temporary unavailability.
- Fleet-aggregation frequency.

### 7.3 Dependent variables

- Average, P95 and P99 end-to-end latency.
- Throughput and message-loss rate.
- Twin-update success rate.
- Individual-twin and fleet-twin staleness.
- Fleet-twin convergence time.
- Fault-detection and recovery time.
- Diagnostic-action success rate.
- Cross-vehicle state-contamination count.
- CPU, memory, network and storage usage.
- Container restart and application-recovery time.

### 7.4 Correctness invariants

The system should enforce and test rules such as:

- Every event contains a valid `vehicleId`, event ID, timestamp and trace ID.
- Events from one vehicle never modify another vehicle's twin.
- The fleet twin never reports a state inconsistent with the latest accepted individual-twin states beyond a defined convergence window.
- Older events do not silently overwrite newer vehicle or sensor state.
- A diagnostic command is applied only to the selected vehicle.
- A sensor failure is distinguishable from a real zero-value observation.
- Restarting a vehicle application does not corrupt another vehicle's state.
- The final twin state matches the expected simulated state after each scenario completes.

### 7.5 Reproducibility requirements

- Versioned source code, container images and configuration.
- Fixed simulation seeds and documented scenarios.
- Automated startup, execution, teardown and result-collection scripts.
- Machine-readable experiment results.
- Repeated trials for every configuration.
- Reported hardware, software versions and resource limits.
- Statistical summaries with confidence intervals where appropriate.

---

## 8. Literature-Review Search Strategy

Search IEEE Xplore, ACM Digital Library, Scopus, Web of Science, SpringerLink and Google Scholar using combinations of:

- `autonomous vehicle digital twin edge architecture`
- `multi vehicle digital twin fleet monitoring`
- `vehicle fleet hierarchical digital twin`
- `connected autonomous vehicle digital twin synchronization`
- `camera LiDAR digital twin vehicle`
- `edge vehicle perception cloud digital twin`
- `cooperative perception digital twin`
- `software-defined vehicle fleet architecture`
- `vehicle digital twin consistency`
- `multi vehicle telemetry scalability`
- `digital twin fault detection autonomous vehicle`
- `open source software-defined vehicle evaluation`
- `Eclipse Velocitas Kuksa Kanto`
- `CARLA multi vehicle sensor simulation`

Use backward and forward snowballing:

1. Examine the references of each relevant paper.
2. Use “cited by” to identify newer work.
3. Record architecture, fleet size, sensors, workloads, metrics, baselines and limitations.
4. Reject or refine the proposed gap if prior work already evaluates essentially the same contribution.

---

## 9. Literature Matrix Template

| Source | Domain | Architecture | Vehicles | Sensors | Twin model | Workload | Metrics | Main result | Limitation | Relevance |
|---|---|---|---:|---|---|---|---|---|---|---|
| Campolo et al. (2024) | Connected/autonomous vehicles | Edge vehicle to remote DT | Add from paper | Onboard sensing | Edge-based DT | Add from paper | Communication and computation footprint | Add after reading | Add after reading | Closest architecture reference |
| Yang et al. (2022) | Vehicular DT network | Vehicle-network-twin | Add from paper | Vehicle data | Per-vehicle DT | Synchronization workload | Add paper-specific metrics | Add after reading | Add after reading | Defines synchronization evaluation |
| Dosovitskiy et al. (2017) | AV simulation | CARLA simulator | Multiple | Camera/LiDAR | Not primary focus | Driving scenarios | Simulation and agent performance | Add after reading | Simulator resource cost | Candidate sensor simulator |

Record findings in your own words and include page, section or figure numbers for later verification.

---

## 10. Journals and Venues to Monitor

- **IEEE Internet of Things Journal**
- **IEEE Transactions on Intelligent Transportation Systems**
- **IEEE Transactions on Vehicular Technology**
- **IEEE Transactions on Services Computing**
- **ACM Transactions on Internet Technology**
- **Journal of Systems Architecture**
- **Future Generation Computer Systems**
- **Internet of Things (Elsevier)**
- **Software: Practice and Experience**
- **Sensors**
- **Smart Cities**

The target venue should be selected after the contribution, experimental scale and results are known. An applied systems workshop, student research conference or focused automotive-software venue may be more realistic than a top-tier journal for an eight-week study.

---

## 11. Recommended Reading Order

### Week 1 — Architecture and domain

1. Campolo et al. on an edge-based CAV digital-twin framework.
2. Yang et al. on vehicular digital-twin synchronization.
3. Eclipse Ditto, Kuksa and VSS documentation.
4. Existing project architecture and final report.

### Week 2 — Sensors and edge applications

5. CARLA paper and sensor documentation.
6. Cooperative-perception digital-twin paper.
7. Edge-perception-to-cloud-digital-twin paper.
8. Velocitas and Kanto documentation.

### Week 3 — Evaluation and research design

9. Zheng et al. on synchronization cost and freshness.
10. Shi et al. on edge computing.
11. Koopman and Wagner on AV testing and validation.
12. CANought documentation if the optional integration is approved.

By the end of Week 3, the project should have:

- A completed literature matrix.
- A validated research gap.
- Final research questions and hypotheses.
- A fixed sensor and simulator choice.
- A finalized individual-twin and fleet-twin schema.
- Defined configurations, workloads, metrics and correctness invariants.
- An experiment plan agreed upon before full implementation.

---

## 12. Expected Research Direction

Retain the completed telemetry, diagnostic, Ditto, Spring Boot and frontend workflow as the experimental baseline. Generalize it for multiple vehicles, add one autonomous-sensor modality, introduce individual and fleet-level twins, then integrate Velocitas and Kanto. CANought should remain optional until the required architecture works reliably.

A credible final contribution would include:

1. A reproducible open-source multi-vehicle SDV architecture.
2. Autonomous-sensor observations integrated into vehicle digital twins.
3. A hierarchical individual-vehicle and fleet-twin model.
4. Standardized vehicle applications managed at the simulated edge.
5. Automated multi-vehicle, sensor-fault, application-failure and diagnostic tests.
6. Controlled experiments with repeated trials and statistical analysis.
7. An explicit comparison with the completed single-vehicle baseline.
8. Discussion of architectural trade-offs, limitations, threats to validity and applicability to real SDV fleets.

This direction turns the completed single-vehicle demonstration into an empirical study of multi-vehicle scalability, autonomous-sensor abstraction, hierarchical digital-twin consistency and edge-managed reliability.
