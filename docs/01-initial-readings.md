# Reading Guide for the SDV Project Enhancement

## Proposed Research Topic

**Resilient Edge-to-Cloud Data Persistence and Digital-Twin Synchronization for Software-Defined Vehicle Health Monitoring**

## 1. Project Enhancement Context

The completed project is a Software-Defined Vehicle (SDV) health-monitoring and diagnostic platform. It uses a vehicle simulator, Eclipse Kuksa, Protobuf-based uProtocol-style messaging, Eclipse Ditto, an OpenSOVD-compatible diagnostic mapper, a Java/Spring Boot backend, and a web frontend. The system monitors vehicle signals, detects correlated faults, synchronizes digital-twin state, and supports runtime fault injection and recovery.

The proposed enhancement adds a resilient persistence layer using the AOSA systems **Berkeley DB** and **SQLAlchemy**:

- **Berkeley DB** will act as a lightweight embedded store for buffering telemetry and diagnostic events when Ditto or the network is unavailable.
- **SQLAlchemy** will manage structured historical telemetry, fault records, delivery attempts, and synchronization metadata in a relational database.
- A synchronization worker will replay buffered events after connectivity is restored.
- The enhanced system will be evaluated under controlled outages, delays, crashes, duplicate deliveries, and out-of-order events.

The literature review should therefore cover four connected areas:

1. Berkeley DB and SQLAlchemy architecture.
2. Store-and-forward communication and disconnected operation.
3. Digital-twin synchronization in vehicular systems.
4. Consistency, event ordering, fault tolerance, and experimental evaluation.

---

## 2. Essential Readings

These six sources should be read first.

### 2.1 Berkeley DB

**M. Seltzer and K. Bostic, “Berkeley DB,” _The Architecture of Open Source Applications, Volume 1_.**  
[Read the Berkeley DB chapter](https://aosabook.org/en/v1/bdb.html)

This chapter explains why Berkeley DB is an embedded library rather than a standalone database server. It covers:

- Key/value and sequential access.
- B-tree, hash, queue, and record-number access methods.
- Transactions and write-ahead logging.
- Locking, concurrency, checkpoints, and recovery.
- Modularity and API boundaries.
- Replication and architectural evolution.

**Questions to answer while reading:**

- Which Berkeley DB access method best represents an ordered event buffer?
- What durability settings are necessary to survive a process crash?
- How should records transition from `PENDING` to `DELIVERED`?
- How can deletion occur safely only after Ditto confirms delivery?

### 2.2 SQLAlchemy

**M. Bayer, “SQLAlchemy,” _The Architecture of Open Source Applications, Volume 2_.**  
[Read the SQLAlchemy chapter](https://aosabook.org/en/v2/sqlalchemy.html)

The chapter explains SQLAlchemy's Core and ORM layers, its unit-of-work pattern, database abstraction, schema mapping, connection pooling, and transaction handling.

**Questions to answer while reading:**

- Should the project use SQLAlchemy ORM, Core, or a combination?
- Where should transaction boundaries be placed?
- Which tables are required for events, faults, replay attempts, and experiments?
- How should relationships and indexes support trace-ID and time-range queries?

Also consult the current [SQLAlchemy 2.0 Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) before implementation.

### 2.3 Vehicular Digital-Twin Synchronization

**X. Yang et al., “Data Synchronization for Vehicular Digital Twin Network,” _IEEE GLOBECOM_, 2022.**  
[View the paper on IEEE Xplore](https://ieeexplore.ieee.org/document/10000831/)

This paper studies the synchronization of vehicle data with digital twins under time-varying network conditions. Focus on how synchronization performance is defined and how network variability affects the accuracy and freshness of the twin.

**Relevance to this project:** Your enhancement addresses what happens when synchronization is not merely delayed but temporarily impossible, and how the system recovers afterward.

### 2.4 Synchronization Cost and Freshness

**J. Zheng et al., “Data Synchronization in Vehicular Digital Twin Network: A Game Theoretic Approach,” _IEEE Transactions on Wireless Communications_, vol. 22, no. 11, 2023.**  
[Open the paper using its DOI](https://doi.org/10.1109/TWC.2023.3254158)

This work studies trade-offs between synchronization frequency, communication cost, and digital-twin performance.

**Questions to consider:**

- Does every signal require the same update frequency?
- Can critical diagnostic events receive higher replay priority than routine telemetry?
- How should the project measure digital-twin staleness during an outage?

### 2.5 Fault-Tolerant Edge–Cloud Architecture

**A. Javed et al., “CEFIoT: A Fault-Tolerant IoT Architecture for Edge and Cloud,” _IEEE World Forum on Internet of Things_, 2018.**  
[Open the paper using its DOI](https://doi.org/10.1109/WF-IoT.2018.8355149)

CEFIoT presents an edge/cloud architecture intended to tolerate network and hardware failures. It uses technologies such as Kafka and container orchestration.

**Use it as a comparison:** CEFIoT represents a comparatively infrastructure-heavy fault-tolerance approach. Your project can evaluate whether an embedded Berkeley DB buffer provides sufficient reliability with lower deployment and resource overhead for a small SDV diagnostic pipeline.

### 2.6 IoT Data Delivery and Storage

**A. Barron et al., “On the Efficient Delivery and Storage of IoT Data in Edge–Fog–Cloud Environments,” _Sensors_, vol. 22, no. 18, 2022.**  
[Read the open-access paper](https://doi.org/10.3390/s22187016)

This paper provides an evaluated data-management approach across IoT, edge, fog, and cloud environments.

**Focus on:**

- The experimental architecture.
- Data-delivery and storage decisions.
- Performance metrics and baselines.
- How results and threats to validity are reported.

---

## 3. Distributed-Systems Foundations

### 3.1 Disconnected Operation and Conflict Resolution

**D. B. Terry et al., “Managing Update Conflicts in Bayou, a Weakly Connected Replicated Storage System,” _Proceedings of SOSP_, 1995.**  
[Open the Bayou paper](https://dl.acm.org/doi/10.1145/224056.224070)

Bayou is highly relevant because it was designed for weakly connected environments. It discusses operation logs, eventual consistency, tentative updates, conflict detection, and reconciliation.

Apply its ideas to these project questions:

- What happens if local and cloud state both change during disconnection?
- Which copy is authoritative?
- How can replay be deterministic?
- How should irreconcilable updates be recorded and exposed?

### 3.2 Event Ordering

**L. Lamport, “Time, Clocks, and the Ordering of Events in a Distributed System,” _Communications of the ACM_, vol. 21, no. 7, 1978.**  
[Open Lamport's paper](https://dl.acm.org/doi/10.1145/359545.359563)

This is the foundational reading for understanding causal ordering in distributed systems.

Use it to reason about:

- Event timestamps versus sequence numbers.
- Events generated during an outage.
- Multiple events with identical or unreliable wall-clock times.
- Preventing an older replayed event from overwriting newer twin state.

### 3.3 Tunable Consistency

**D. Perkins et al., “Simba: Tunable End-to-End Data Consistency for Mobile Apps,” _Proceedings of EuroSys_, 2015.**  
[Open the Simba paper](https://dl.acm.org/doi/10.1145/2741948.2741974)

Simba demonstrates that different data can require different consistency guarantees.

For example:

- A critical cooling-system fault may require durable, ordered delivery.
- High-frequency temperature samples may tolerate batching or replacement.
- A recovery action must not be applied before its corresponding fault action.

### 3.4 Delay-Tolerant Store-and-Forward Communication

**S. Burleigh et al., “Bundle Protocol Version 7,” RFC 9171, 2022.**  
[Read RFC 9171](https://www.rfc-editor.org/rfc/rfc9171.html)

The project does not need to implement Bundle Protocol. However, its store-carry-forward model provides useful principles for communication when an end-to-end path is temporarily unavailable.

Pay attention to:

- Persistent storage of undelivered data.
- Message lifetime and expiry.
- Duplicate handling.
- Delivery status and custody concepts.
- Recovery after delayed connectivity.

---

## 4. Project-Specific Technical Documentation

These sources connect the research concepts to the implemented platform:

- [Eclipse Ditto documentation](https://eclipse.dev/ditto/): digital twins, Things, policies, messages, connectivity, and event handling.
- [Eclipse Ditto Connections](https://eclipse.dev/ditto/basic-connections.html): external messaging and connection behaviour.
- [Eclipse Kuksa documentation](https://eclipse-kuksa.github.io/kuksa-databroker/): vehicle-signal access and the Kuksa Data Broker.
- [COVESA Vehicle Signal Specification](https://covesa.github.io/vehicle_signal_specification/): standardized vehicle-signal names and schemas.
- [Oracle Berkeley DB documentation](https://docs.oracle.com/en/database/other-databases/berkeley-db/): transactions, recovery, durability, locking, deadlocks, and backup.
- [SQLAlchemy 2.0 documentation](https://docs.sqlalchemy.org/en/20/): current ORM, Core, engine, session, and transaction APIs.

When reading product documentation, distinguish **implemented functionality** from **possible platform functionality**. The research paper should claim only the behaviour implemented and experimentally verified in this project.

---

## 5. Preliminary Research Gap

The following is a **provisional gap inferred from the readings** and must be confirmed through a systematic literature search:

> Existing vehicular digital-twin studies frequently optimize synchronization scheduling, wireless-resource allocation, update frequency, or data freshness. General edge–cloud studies often use comparatively heavy distributed platforms for fault tolerance. There appears to be less experimental evidence on lightweight, application-level, durable store-and-forward synchronization in an open-source SDV diagnostic pipeline—particularly regarding diagnostic-state correctness after outages, duplicate suppression, event ordering, replay latency, and digital-twin convergence.

The contribution should not be described merely as “adding two databases.” The publishable contribution should be the **architecture, recovery protocol, and empirical evaluation** of resilient SDV digital-twin synchronization.

---

## 6. Candidate Research Questions

### Primary research question

> How effectively can a lightweight Berkeley DB and SQLAlchemy persistence architecture preserve and synchronize SDV telemetry and diagnostic state during intermittent edge-to-cloud connectivity?

### Supporting research questions

**RQ1 — Reliability**  
How does persistent store-and-forward delivery affect telemetry and diagnostic-event loss compared with direct transmission?

**RQ2 — Recovery**  
How do outage duration and event rate affect replay latency and time to digital-twin convergence?

**RQ3 — Correctness**  
Can idempotency keys, sequence numbers, and replay rules prevent duplicates, invalid ordering, and incorrect diagnostic-state transitions?

**RQ4 — Performance cost**  
What latency, storage, CPU, and memory overhead does the persistence layer introduce during normal operation?

**RQ5 — Storage design**  
What practical roles are best assigned to Berkeley DB and the SQLAlchemy-managed relational database within the same SDV pipeline?

---

## 7. Suggested Experimental Design

### 7.1 Compared configurations

1. **Baseline:** Direct transmission to Ditto without durable buffering.
2. **Berkeley DB buffering:** Failed events are stored locally and replayed.
3. **Enhanced persistence:** Berkeley DB buffering plus SQLAlchemy-managed history, synchronization metadata, idempotency, and recovery reporting.

### 7.2 Independent variables

- Outage duration: for example, 0, 5, 15, 30, and 60 seconds.
- Telemetry publication rate.
- Buffer size and number of queued events.
- Failure type: network loss, Ditto unavailability, bridge restart, or database restart.
- Event type: routine telemetry, fault activation, diagnostic action, or recovery.
- Replay policy: FIFO, priority-based, individual delivery, or batched delivery.

### 7.3 Dependent variables

- Event-loss percentage.
- Duplicate-event count.
- Out-of-order-event count.
- Local persistence latency.
- End-to-end delivery latency.
- Replay throughput.
- Recovery and convergence time.
- Digital-twin staleness.
- Final twin-state correctness.
- CPU, memory, and storage overhead.

### 7.4 Correctness invariants

The system should enforce and test rules such as:

- Every event has a stable event ID and trace ID.
- A successfully acknowledged event is not replayed unnecessarily.
- Replaying an event more than once does not change the correct final state.
- Events from one vehicle do not alter another vehicle's twin.
- An older telemetry event cannot overwrite a newer value without an explicit reconciliation rule.
- A recovery event cannot incorrectly erase a newer active fault.
- The final Ditto state matches the expected vehicle state after the queue is drained.

---

## 8. Literature-Review Search Strategy

Search IEEE Xplore, ACM Digital Library, Scopus, Web of Science, SpringerLink, and Google Scholar using combinations of:

- `vehicular digital twin synchronization`
- `software-defined vehicle digital twin`
- `vehicle telemetry intermittent connectivity`
- `edge cloud store-and-forward IoT`
- `disconnected edge persistence`
- `digital twin consistency recovery`
- `fault-tolerant vehicle telemetry`
- `event replay idempotency IoT`
- `out-of-order telemetry digital twin`
- `embedded database edge computing`
- `Berkeley DB event queue`
- `SQLAlchemy IoT telemetry persistence`

Use backward and forward snowballing:

1. Examine the references of each strong paper.
2. Use “cited by” to find newer work.
3. Record the architecture, failure model, dataset, metrics, baselines, and limitations of every relevant study.
4. Stop treating a gap as valid if another paper has already evaluated essentially the same contribution.

---

## 9. Literature Matrix Template

Maintain a table like this while reading:

| Source | Domain | Problem | Architecture | Failure model | Dataset/workload | Metrics | Main result | Limitation | Relevance to our work |
|---|---|---|---|---|---|---|---|---|---|
| Yang et al. (2022) | Vehicular DT | Synchronization | Vehicle–network–twin | Variable network | Simulation | Add paper-specific metrics | Add finding | Add limitation | Defines synchronization context |
| Javed et al. (2018) | Edge–cloud IoT | Fault tolerance | Kafka-based edge/cloud | Network/hardware failure | Add from paper | Add metrics | Add finding | Infrastructure complexity | Comparison architecture |
| Terry et al. (1995) | Replicated storage | Weak connectivity | Replicated update log | Disconnection/conflict | Application scenarios | Consistency behaviour | Add finding | Not automotive-specific | Replay and reconciliation concepts |

Do not copy abstracts into this matrix. Record the information in your own words and include page or section numbers for later citation.

---

## 10. Journals and Venues to Monitor

The following venues regularly publish work related to connected vehicles, IoT, digital twins, distributed systems, and software architecture:

- **IEEE Internet of Things Journal**
- **IEEE Transactions on Intelligent Transportation Systems**
- **IEEE Transactions on Vehicular Technology**
- **IEEE Transactions on Wireless Communications**
- **ACM Transactions on Internet Technology**
- **Future Generation Computer Systems**
- **Journal of Systems Architecture**
- **Software: Practice and Experience**
- **Internet of Things (Elsevier)**
- **Sensors**

Publication venue should be selected only after the contribution, experimental scale, and paper maturity are clear. A focused workshop, student research conference, or applied systems venue may be more realistic for an eight-week study than a top-tier archival journal.

---

## 11. Recommended Reading Order

### Week 1 — Architecture and storage

1. Berkeley DB AOSA chapter.
2. SQLAlchemy AOSA chapter.
3. Current SQLAlchemy session and transaction documentation.
4. Berkeley DB transaction and recovery documentation.

### Week 2 — Domain and research problem

5. Yang et al. on vehicular digital-twin synchronization.
6. Zheng et al. on synchronization cost and freshness.
7. Barron et al. on edge–fog–cloud data storage.
8. CEFIoT on edge/cloud fault tolerance.

### Week 3 — Correctness foundations

9. Bayou on disconnected updates and reconciliation.
10. Lamport on event ordering.
11. Simba on tunable consistency.
12. RFC 9171 for delay-tolerant store-and-forward principles.

By the end of Week 3, the team should have:

- A completed literature matrix.
- A refined and defensible research gap.
- Final research questions and hypotheses.
- A system architecture and failure model.
- Defined baselines, variables, metrics, and correctness invariants.
- An experiment plan agreed upon before extensive implementation begins.

---

## 12. Expected Research Direction

The strongest direction is not to redesign the complete SDV platform. Retain the completed telemetry, diagnostic, digital-twin, and frontend workflow as the baseline. Add the persistence and recovery extension at the bridge's edge-to-cloud boundary, then evaluate it rigorously.

A credible final contribution would include:

1. A lightweight dual-storage architecture using Berkeley DB and SQLAlchemy.
2. A documented store-and-forward recovery protocol.
3. Idempotency and ordering rules for telemetry and diagnostic events.
4. Automated fault-injection and outage experiments.
5. Reproducible datasets, scripts, configurations, and statistical analysis.
6. An explicit comparison with the existing direct-transmission baseline.
7. Discussion of trade-offs, limitations, threats to validity, and applicability to real SDV deployments.

This turns the enhancement from a technology demonstration into an empirical software and distributed-systems study with a plausible publication contribution.
