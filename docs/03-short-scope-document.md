# SDV Autonomous-Fleet Platform — Project Scope

## Objective

Develop and evaluate a reproducible open-source SDV platform that monitors and diagnoses multiple simulated, sensor-enabled vehicles through individual vehicle digital twins and an aggregated fleet-level digital twin.

## In Scope

- Support 3–5 independently simulated vehicles.
- Add one primary autonomous sensor type: camera or LiDAR.
- Process sensor input into information such as detected objects, obstacle distance, lane status and sensor health.
- Maintain independent telemetry, health status, faults, diagnostic history and perception results for every vehicle.
- Create a fleet-level digital twin that aggregates vehicle status.
- Provide fleet monitoring, vehicle selection and remote diagnostic actions through the dashboard.
- Use Eclipse Velocitas for standardized vehicle applications and Eclipse Kanto for edge deployment and application management.
- Add automated unit, integration and end-to-end tests using Pytest and JUnit.
- Evaluate latency, scalability, reliability, resource usage, digital-twin consistency, fault detection and recovery.

## Optional Scope

- Add a second autonomous sensor type.
- Integrate Eclipse CANought for J1939/UDS translation.
- Run higher-volume simulations beyond the demonstrated 3–5 vehicles.

## Out of Scope

- Complete autonomous-driving or route-planning functionality.
- Physical vehicles or automotive hardware.
- Storing raw camera video or LiDAR point clouds directly in the digital twin.
- Production-grade automotive safety certification.

## Deliverables

- Working multi-vehicle SDV platform and fleet dashboard.
- Individual vehicle twins and one fleet-level digital twin.
- Sensor-processing, health-monitoring and diagnostic workflows.
- Reproducible containerized deployment and configuration.
- Automated test suite, experimental data and evaluation report.

## Eight-Week Schedule

- **Weeks 1–2:** Multi-vehicle architecture and simulation.
- **Weeks 3–4:** Sensor processing, digital twins, Velocitas and Kanto integration.
- **Weeks 5–6:** Dashboard integration and automated testing.
- **Weeks 7–8:** Experiments, analysis, documentation and publication preparation.
