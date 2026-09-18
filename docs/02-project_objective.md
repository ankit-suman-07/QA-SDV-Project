# Autonomous-Fleet SDV Platform Enhancement

## Main Project Objective

To develop and evaluate a reproducible open-source Software-Defined Vehicle (SDV) platform for monitoring and diagnosing a fleet of simulated sensor-enabled vehicles, using digital twins to represent individual vehicle states and provide an aggregated fleet-level view.

## Specific Objectives

- Expand the existing system from one hard-coded vehicle to 3–5 independently simulated vehicles.
- Equip the vehicles with simulated camera and/or LiDAR sensors to support autonomous-perception scenarios.
- Process sensor input into useful information such as detected objects, obstacle distance, lane status and sensor health.
- Maintain an individual digital twin for each vehicle containing its telemetry, perception results, health state, active faults and diagnostic history.
- Introduce a fleet-level digital twin that aggregates the condition and operational status of all vehicles.
- Provide a fleet dashboard for monitoring vehicles and performing remote diagnostic actions.
- Use Eclipse Velocitas for standardized vehicle applications, Eclipse Kanto for edge-application deployment and management, and optionally Eclipse CANought for realistic J1939/UDS communication.
- Evaluate scalability, latency, reliability, digital-twin consistency, resource usage, fault detection and recovery under different fleet workloads.
- Provide automated Pytest and JUnit tests, reproducible deployment configurations, experimental datasets and documented procedures.

The project focuses on autonomous sensing and fleet management, not the implementation of a complete self-driving system.
