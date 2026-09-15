# SDV Enhancement Project Scope

## Resilient Edge-to-Cloud Persistence and Digital-Twin Synchronization for Software-Defined Vehicle Health Monitoring

**Duration:** Eight weeks  
**Team:** Three members  
**Target:** Publication-ready study and industry-grade project

---

## 1. Existing Project

The completed project is an end-to-end SDV health-monitoring and diagnostic system for one simulated vehicle. It currently:

- Generates speed, battery, tire-pressure, coolant-temperature, and coolant-pressure signals.
- Publishes standardized vehicle signals through Eclipse Kuksa.
- Uses Protobuf-based uProtocol-style messaging.
- Synchronizes vehicle state and detailed faults with Eclipse Ditto.
- Produces OpenSOVD-compatible diagnostic records.
- Detects battery warnings and a correlated cooling-system failure.
- Supports runtime fault injection and recovery through Spring Boot APIs and a web frontend.
- Propagates event, trace, and action identifiers.
- Includes automated tests, demonstrations, and performance measurements.

The enhancement will extend this system rather than replace it.

---

## 2. Project Goal

The enhanced project will add durable local persistence and automatic recovery when Eclipse Ditto or the network is unavailable.

The system will:

1. Store events locally before cloud delivery.
2. Continue processing vehicle signals during an outage.
3. Replay pending events after connectivity returns.
4. Prevent duplicate and out-of-order events from corrupting the digital twin.
5. Verify that Ditto eventually matches the correct vehicle state.
6. Compare the enhanced design with the existing direct-transmission baseline.

---

## 3. Principal Components

### Existing Eclipse components

- **Eclipse Kuksa:** Vehicle-signal access.
- **uProtocol-style layer:** Protobuf event serialization and transport abstraction.
- **Eclipse Ditto:** Cloud-side digital twin.
- **OpenSOVD-compatible mapper:** Standardized diagnostic representation.

### Added AOSA systems

- **Berkeley DB:** Embedded transactional outbox for pending events.
- **SQLAlchemy:** Relational persistence for history, audit records, fault lifecycles, and experiment metadata.

### Supporting technologies

- Python, Java, and Spring Boot.
- PostgreSQL behind SQLAlchemy.
- Docker Compose.
- Pytest and JUnit.
- Jenkins for continuous integration.
- Existing web frontend.

---

## 4. Required Work

- Refactor the Python bridge into clear ingestion, health, persistence, delivery, and monitoring modules.
- Define a versioned event envelope containing event ID, vehicle ID, trace ID, sequence number, timestamp, type, and priority.
- Implement a Berkeley DB persist-before-send transactional outbox.
- Implement retry, replay, exponential backoff, and dead-letter handling.
- Add event ordering, idempotency, and stale-update protection.
- Create SQLAlchemy models for delivery history, faults, actions, synchronization sessions, and experiments.
- Complete diagnostic-action states from `ACCEPTED` to `IN_PROGRESS`, then `COMPLETED` or `FAILED`.
- Add synchronization status APIs and a small frontend status panel.
- Automate outage, restart, duplicate, and recovery scenarios.
- Add unit, integration, recovery, API, regression, and end-to-end tests.
- Add a focused Jenkins pipeline for builds, tests, reports, and a bounded integration check.
- Run repeatable experiments comparing the baseline and enhanced systems.
- Produce updated documentation, reproducible results, and a publication-style paper.

---

## 5. Optional Work

Complete these only after all required work is on schedule:

- Telemetry compaction during long outages.
- Priority replay for critical diagnostic events.
- Queue-size limits and backpressure.
- Additional packet-loss and jitter experiments.
- Small multi-vehicle scalability experiment.
- Hosted recruiter demonstration.

---

## 6. Out of Scope

- Complete production uProtocol or OpenSOVD deployments.
- Additional Eclipse components.
- ZeroMQ, Open MPI, Zenoh, or Selenium as research components.
- Kubernetes or complex cloud orchestration.
- Berkeley DB replication.
- Machine learning or autonomous-driving functions.
- Physical vehicle testing.
- Production-scale fleet simulation.
- Complete frontend redesign.
- Rewriting the existing project from scratch.

---

## 7. Research Evaluation

### Primary research question

> How effectively can a lightweight Berkeley DB and SQLAlchemy persistence architecture preserve and synchronize SDV telemetry and diagnostic state during intermittent edge-to-cloud connectivity?

### Compared configurations

1. Existing direct transmission without durable buffering.
2. Enhanced transmission with Berkeley DB, SQLAlchemy, replay, ordering, and idempotency.

### Test conditions

- Normal operation without an outage.
- Short, medium, and long outages.
- At least two telemetry publication rates.
- Ditto unavailability.
- Bridge restart.
- Duplicate and out-of-order delivery.

### Metrics

- Event-loss rate.
- Duplicate and ordering errors.
- Persistence and end-to-end latency.
- Replay throughput and queue-drain time.
- Digital-twin staleness and convergence time.
- Final-state correctness.
- CPU, memory, and storage overhead.

Experiments must be automated, repeated, and supported by saved raw data and analysis scripts.

---

## 8. Eight-Week Plan

| Week | Scope |
|---|---|
| **1** | Freeze baseline; complete literature review, research gap, architecture, and repository cleanup |
| **2** | Define event contracts, database schemas, test plan, experiment matrix, and baseline measurements |
| **3** | Implement and test the Berkeley DB transactional outbox |
| **4** | Add SQLAlchemy persistence and complete bridge modularization |
| **5** | Implement replay, retry, ordering, idempotency, action lifecycle, and recovery tests |
| **6** | Add frontend observability, failure automation, Jenkins, and full integration testing |
| **7** | Execute repeated experiments and analyse results |
| **8** | Reproduce findings, stabilize the release, and complete the paper, documentation, and demonstration |

Weeks 7 and 8 are reserved for evaluation and publication work, not major new features.

---


## 9. Required Deliverables

- Working enhanced SDV system.
- Berkeley DB transactional outbox.
- SQLAlchemy/PostgreSQL history and audit layer.
- Unified delivery and replay service.
- Synchronization APIs and frontend status view.
- Automated failure and recovery scenarios.
- Comprehensive automated tests and Jenkins pipeline.
- Baseline and enhanced experimental datasets.
- Analysis scripts, charts, and tables.
- Updated README and reproduction guide.
- Publication-ready manuscript.
- Final demonstration and tagged repository release.

---

## 10. Completion Criteria

The project is complete when:

- Existing health-monitoring and diagnostic behaviour still works.
- Committed critical events survive the required outages and bridge restart.
- Pending events replay automatically after reconnection.
- Duplicate and stale events do not corrupt final state.
- Fault activation and recovery remain correctly ordered.
- Ditto converges to the expected vehicle state.
- The frontend accurately displays synchronization status.
- Automated tests and the Jenkins pipeline pass.
- Baseline and enhanced experiments are repeatable.
- Raw data, analysis, documentation, and the final paper support every reported claim.

The team will prioritize a complete, rigorously evaluated resilience contribution over additional incomplete features.
