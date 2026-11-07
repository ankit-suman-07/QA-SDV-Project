# SDV fleet enhancement architecture

Target architecture for Course V1 and V2, based on [project scope and acceptance](09-project-scope-and-acceptance.md). Both milestones run locally using host processes or containers. The diagrams describe delivery targets.

## Course V1 — Two synthetic vehicles

One KUKSA broker and one Velocitas app serve each vehicle. The shared MQTT broker delivers vehicle-specific events to the twin bridge. Spring Boot reads live Ditto state and routes simulator fault commands by vehicle ID.

```mermaid
flowchart TD
    subgraph V1["vehicle-001"]
        S1["Synthetic provider 001"] --> K1["KUKSA broker 001"]
        K1 --> A1["Velocitas app 001"]
    end
    subgraph V2["vehicle-002"]
        S2["Synthetic provider 002"] --> K2["KUKSA broker 002"]
        K2 --> A2["Velocitas app 002"]
    end
    A1 --> M["Mosquitto"]
    A2 --> M
    M --> B["Twin bridge"]
    B -->|"Validate and route by vehicle ID"| D["Ditto vehicle twins 001 and 002"]
    D -->|"Live state reads"| API["Spring Boot API"]
    API -->|"Demo vehicle health"| C["API client"]
    C -->|"Inject or clear fault on vehicle-002"| API
    API -->|"Targeted HTTP scenario command"| S2
```

**Acceptance run.** Start both vehicles healthy. Inject a LiDAR fault into `vehicle-002`, observe the fault in its twin and API response, then clear it and observe recovery. Verify that `vehicle-001` stays healthy and receives no corresponding fault.

## Course V2 — CARLA fleet telemetry

The CARLA adapter maps three actors to three project vehicle IDs. It sends compact front LiDAR observations to the matching edge instance and records the injection timeline separately for evaluation.

```mermaid
flowchart TD
    C["CARLA with three front LiDAR vehicles"] --> A["CARLA adapter and actor mapping"]
    A -->|"Per-vehicle observations"| K
    subgraph E["Vehicle edge — one instance per vehicle"]
        K["KUKSA broker"] --> V["Velocitas health app"]
        KA["Kanto on Linux"] -.->|"Launch and restart"| V
    end
    V -->|"Health, fault and recovery events"| M["Mosquitto"]
    M --> B["Twin bridge"]
    B --> D["Ditto individual vehicle twins"]
    D --> F["Fleet aggregator"]
    F --> T["Ditto fleet twin"]
    D --> API["Spring Boot fleet and vehicle APIs"]
    T --> API
    API --> UI["Fleet dashboard"]
```

Velocitas classifies LiDAR health. The bridge validates identity and freshness and applies the agreed duplicate and ordering rules. Fleet aggregation derives counts, availability and alerts from individual twin state. Store compact observations and diagnostic records in Ditto. Keep raw point clouds and labelled experiment inputs separately.

## Course V2 — Diagnostic commands and outcomes

```mermaid
sequenceDiagram
    participant U as Dashboard
    participant B as Spring Boot
    participant D as Diagnostic integration
    participant T as Selected vehicle target
    U->>B: Submit action for vehicle ID
    B->>B: Validate target and assign action and trace IDs
    B-->>U: Return action ID and acceptance status
    B->>D: Dispatch correlated action
    D->>T: Execute supported operation
    T-->>D: Return execution result
    D-->>B: Correlated result or timeout
    U->>B: Read action status
    B-->>U: Return execution outcome
```

Demonstrate one real uProtocol exchange and one supported OpenSOVD operation. Their exact placement and operation are open contract decisions. Kanto restart is an application lifecycle action. Verify fresh events after restart. For a CARLA input dropout, restore input and verify recovery separately through the telemetry path.

## Integration handoffs

| Owner | Provides | Used by |
|---|---|---|
| Emmanuel | Vehicle IDs, signal definitions, synthetic/CARLA adapters, fault scenarios and Velocitas events | Bayan’s ingestion and Ankit’s scenario routing and verification |
| Bayan | Event validation, twin IDs and schemas, fleet state, diagnostic exchange and Kanto deployment evidence | Ankit’s live APIs, action tracking and dashboard |
| Ankit | Shared contracts, Spring Boot integration, fleet dashboard, CI and end-to-end acceptance evidence | Team integration and milestone demonstrations |

Agree vehicle-to-broker/provider/twin mappings, event IDs and source timestamps, fault and recovery thresholds, and command acknowledgements before implementing dependent interfaces. Preserve the synthetic workflow for CI and repeatable tests. Beam is optional.
