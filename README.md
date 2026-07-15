### Contributors, please read the contribution guidelines thoroughly here: [Link](https://github.com/ankit-suman-07/QA-SDV-Project/blob/main/docs/TEAM_GUIDELINES.md)

----

# Software-Defined Vehicle Health Monitoring and Diagnostic System

## Project Overview

This graduate project designs and evaluates a **Software-Defined Vehicle (SDV) Health Monitoring and Diagnostic System** by integrating Eclipse Kuksa, Eclipse uProtocol, Eclipse Ditto, and Eclipse OpenSOVD.

The system simulates signals for one virtual vehicle, detects abnormal operating conditions, maintains a synchronized digital twin, communicates vehicle events through standardized messages, exposes diagnostic information, and presents the vehicle's current condition through a web dashboard.

The project focuses on more than component connectivity. It introduces custom fault-injection, health-classification, diagnostic, and state-synchronization behaviour and evaluates the resulting pipeline through functional tests and measurable non-functional metrics.

## Project Scope

The minimum viable implementation includes:

- One simulated vehicle: `vehicle-001`
- Four categories of vehicle signals:
  - Speed
  - Battery level
  - Vehicle temperature
  - Tire pressure
- Three fault scenarios:
  - Low battery
  - High temperature
  - Low tire pressure
- Three health classifications:
  - `HEALTHY`
  - `WARNING`
  - `CRITICAL`
- A synchronized Eclipse Ditto digital twin
- uProtocol vehicle-status and fault events
- OpenSOVD-compatible diagnostic information
- A browser-based monitoring dashboard
- Automated functional, API, integration, and end-to-end tests
- End-to-end fault-propagation latency measurement

Multi-vehicle simulation, advanced analytics, and additional fault types are optional extensions and are not part of the initial scope.

## System Components

### Vehicle Simulator

The vehicle simulator generates changing values for the supported signals and publishes them to Eclipse Kuksa. It also provides repeatable fault-injection scenarios for testing abnormal operating conditions and subsequent recovery.

### Eclipse Kuksa

**Role:** Vehicle data abstraction layer and vehicle-side state store

Eclipse Kuksa receives and exposes the simulated vehicle signals using an agreed vehicle-data model. It serves as the primary source of current vehicle-side state for the integration backend.

Its responsibilities include:

- Receiving simulated signal updates
- Representing signals through agreed VSS/Kuksa paths
- Providing current vehicle data to the backend
- Supporting abnormal and degraded signal scenarios
- Validating that published values are stored accurately

### Eclipse uProtocol

**Role:** Standardized event and communication layer

Eclipse uProtocol provides transport-independent message structures for communication between vehicle services. The project defines a limited set of events that correspond to observable system behaviour.

Planned events include:

- `VehicleStatusUpdated`
- `HealthStatusChanged`
- `FaultDetected`
- `FaultCleared`

Events include traceability information such as the vehicle ID, event ID, timestamp, severity, and relevant signal or fault values.

### Spring Boot Integration Backend

**Role:** Business logic, component integration, APIs, and measurement

The Java Spring Boot backend acts as the central integration service. It reads normalized vehicle data from Kuksa, applies the vehicle health rules, publishes appropriate uProtocol events, synchronizes the Ditto digital twin, maps faults to diagnostic information, and exposes data to the frontend.

Its responsibilities include:

- Reading and validating Kuksa signals
- Mapping component-specific data into a shared vehicle model
- Detecting and clearing vehicle faults
- Calculating the overall vehicle health status
- Publishing uProtocol vehicle and fault events
- Updating the Eclipse Ditto digital twin
- Integrating diagnostic information with Eclipse OpenSOVD
- Exposing REST and real-time dashboard APIs
- Recording timestamps for latency measurement
- Providing structured logging and error handling

### Eclipse Ditto

**Role:** Backend digital-twin and state management

Eclipse Ditto maintains the external digital representation of `vehicle-001`. The backend updates the twin whenever the relevant vehicle state, health status, or active fault list changes.

The digital twin contains information such as:

- Current vehicle signals
- Overall health status
- Active faults and fault count
- Signal and diagnostic timestamps
- Last-known synchronized state

### Eclipse OpenSOVD

**Role:** Standardized vehicle diagnostic interface

Eclipse OpenSOVD exposes diagnostic information derived from vehicle state and health-engine results. The project limits its initial diagnostic scope to information required for the selected fault scenarios.

Diagnostic information includes:

- Vehicle information
- Current health status
- Active and cleared faults
- Fault codes and severity
- Fault detection timestamps
- Diagnostic query results

### Web Dashboard

**Role:** Real-time monitoring and diagnostic visualization

The dashboard is developed with HTML, CSS, and JavaScript. It consumes backend APIs rather than connecting directly to every Eclipse component.

The dashboard displays:

- Live vehicle signals
- Digital-twin synchronization status
- Overall vehicle health
- Active and cleared faults
- Diagnostic information
- Last-update timestamps
- Loading, disconnected, and error states

## Runtime Architecture

```text
Vehicle Simulator
        |
        v
Eclipse Kuksa
        |
        v
Spring Boot Integration Backend
        |----------------------> Vehicle Health Engine
        |----------------------> Eclipse uProtocol Events
        |----------------------> Eclipse Ditto Digital Twin
        |----------------------> Eclipse OpenSOVD Diagnostics
        |
        v
Web Dashboard
```

The diagram represents runtime responsibilities rather than implying that every component forms a mandatory linear chain. The Spring Boot backend coordinates data transformation and communication between the component-specific interfaces.

## Shared Vehicle Model

The components use a shared logical data contract similar to the following example:

```json
{
  "vehicleId": "vehicle-001",
  "timestamp": "2026-07-12T18:30:00Z",
  "speedKph": 60.0,
  "batteryPercent": 75.0,
  "temperatureCelsius": 85.0,
  "tirePressurePsi": {
    "frontLeft": 32.0,
    "frontRight": 32.0,
    "rearLeft": 31.0,
    "rearRight": 32.0
  },
  "healthStatus": "HEALTHY",
  "activeFaults": []
}
```

The final field names, signal paths, units, data types, fault thresholds, and component mappings are maintained in the project's vehicle-data contract.

## Planned Functional Modifications

### Fault Injection

The simulator introduces controlled abnormal values for low battery, high temperature, and low tire pressure. Each scenario can be activated and cleared independently so the same tests can be repeated.

### Vehicle Health Engine

The backend converts raw vehicle signals into health classifications and structured fault records. Rules include activation thresholds, severity, fault codes, and recovery conditions. Recovery margins may be used to prevent rapid switching between faulty and healthy states.

### Digital-Twin Extension

The Ditto model is extended beyond raw signal storage to include calculated health, active faults, diagnostic timestamps, and synchronization information.

### Diagnostic Mapping

Detected faults are converted into an agreed OpenSOVD-compatible diagnostic representation containing the fault code, description, severity, affected signal, detected value, threshold, and timestamp.

### Standardized Events

The team defines and tests uProtocol schemas for state updates and fault lifecycles. Events are generated only at the appropriate points, such as a detected fault, changed health state, or cleared fault.

## Testing and Measurement

### Functional Testing

The project validates:

- Correct publication and retrieval of Kuksa signals
- Correct detection of all three fault scenarios
- Accurate health classification and fault clearing
- Correct uProtocol serialization and event propagation
- Consistency between backend state and the Ditto twin
- Correct OpenSOVD diagnostic responses
- Accurate dashboard updates
- Complete end-to-end fault propagation

### Non-Functional Testing

The primary metric is end-to-end fault-propagation latency:

```text
Fault propagation latency = dashboard update time - fault injection time
```

Where possible, the results will include:

- Minimum latency
- Average latency
- 95th-percentile latency
- Maximum latency
- Successful event-delivery rate
- Missing or duplicate event count

These results will be reported as measured observations rather than assumed performance claims.

## Technology Stack

- **Backend:** Java, Spring Boot, Maven
- **Testing:** JUnit, Mockito, Postman/Newman
- **Vehicle data:** Eclipse Kuksa
- **Messaging:** Eclipse uProtocol, Protocol Buffers
- **Digital twin:** Eclipse Ditto
- **Diagnostics:** Eclipse OpenSOVD
- **Frontend:** HTML, CSS, JavaScript, Fetch API or Axios
- **Containerization:** Docker and Docker Compose
- **Continuous integration:** Jenkins
- **Version control:** Git and GitHub

## Team Responsibilities

| Team Member | Primary Role | Major Responsibilities |
|---|---|---|
| **Ankit Suman** | Backend Integration and Quality Lead | Design the architecture; develop the Spring Boot backend and APIs; implement the vehicle health engine and component adapters; create automated integration and end-to-end tests; measure latency; coordinate final integration. |
| **Emmanuel Adegboye** | Eclipse Kuksa and Vehicle Simulation Lead | Configure Kuksa; simulate vehicle signals; publish sensor data; implement repeatable fault-injection scenarios; validate signal accuracy and updates. |
| **Benjamin Emeshili** | Eclipse uProtocol, OpenSOVD Support, and CI Lead | Define uProtocol schemas and events; implement and test serialization and propagation; assist with OpenSOVD integration; configure the Jenkins pipeline. |
| **Atharva Rajadhyaksha** | Eclipse Ditto and Diagnostics Lead | Configure Ditto; design and extend the digital-twin model; implement state synchronization; configure OpenSOVD; implement diagnostic commands and fault handling. |
| **Mehtaj** | Frontend Dashboard and API Validation Lead | Develop the dashboard; display live signals, health, and diagnostics; integrate backend APIs; create Postman collections; perform frontend and API validation. |

## Project Goal

The goal is to design, integrate, and evaluate a fault-aware health-monitoring and diagnostic pipeline for a simulated software-defined vehicle.

The completed system will demonstrate how:

- Simulated vehicle signals can be represented through Eclipse Kuksa
- Vehicle state can be transformed into standardized uProtocol events
- Custom health logic can detect and clear abnormal conditions
- Eclipse Ditto can maintain a synchronized external digital twin
- Eclipse OpenSOVD can expose diagnostic information
- A web dashboard can present live health and diagnostic state
- Functional correctness and propagation latency can be evaluated through repeatable tests

## Current Status

The project is under active development. Setup instructions, API documentation, the vehicle-data contract, testing procedures, and measured results will be added as implementation progresses.