# SDV Project — Team Implementation Tasks

Planning date: October 25, 2026

Members: **Ankit, Bayan, Emmanuel**

## 1. Goal and planning boundaries

Complete the existing SDV MVP as an integrated, multi-vehicle system: obtain vehicle telemetry, run vehicle applications, maintain digital twins, expose diagnostics, display fleet status, and reproduce the deployment and demonstration.

The working demonstration already established the Python simulator → KUKSA → Velocitas → MQTT path. Previous reported work includes vehicle-aware backend storage and diagnostic actions, isolated simulator scenarios, synthetic LiDAR signals, and Kanto deployment artifacts. These are starting points, not proof that every final integration works.

Before changing code, inspect the current repository and tests. Documentation may be outdated. Preserve working functionality and extend existing modules where practical. This task list is an implementation plan, not a fresh audit of the repository.

- **Godot is outside this work plan.**
- Ankit owns CARLA integration. Keep the existing Python simulator available as a reproducible fallback and CI signal source.
- Start with **two vehicles and two KUKSA brokers**, one broker per vehicle. This is the agreed deployment design, not a universal KUKSA requirement.
- One CARLA server can host both vehicles; route each actor to the correct vehicle ID and broker.
- Kanto runtime validation requires a Linux environment. Configuration files alone do not demonstrate deployment.
- Begin with basic CI. Add release and deployment automation after manual deployment works.

## 2. Ownership at a glance

| Member | Primary ownership | Main deliverables |
|---|---|---|
| Ankit | CARLA; KUKSA and VSS; live backend signal acquisition and vehicle routing; CI/CD | Two isolated vehicle streams, simulator bridge, real backend state, automated validation and image delivery |
| Bayan | Ditto; fleet dashboard; MQTT/Mosquitto event ingestion | Separate vehicle twins, event-driven updates, live fleet views and diagnostic UI |
| Emmanuel | Velocitas; OpenSOVD; uProtocol; Kanto | Vehicle applications, diagnostic execution and status, real service messaging, verified Linux deployment |
| All | Contracts, integration tests, documentation, PR reviews | A reproducible complete demonstration with evidence for each claimed integration |

The backend is shared: Ankit owns registration, telemetry and routing; Bayan owns event ingestion and twin-facing integration; Emmanuel owns diagnostic execution and action status. Coordinate edits to shared services before starting overlapping PRs.

## 3. Shared agreement before parallel implementation

Complete these as a small contract checkpoint. Each member reviews the agreement before implementing dependent interfaces.

- [ ] List the initial vehicle IDs and their KUKSA endpoints, simulator targets, twin IDs, and application instances.
- [ ] Define the initial signal set, types, units, timestamps and freshness rules.
- [ ] Agree on MQTT topics and payloads, including vehicle identity, schema version and source time.
- [ ] Define command and action messages with `vehicleId`, `actionId` and `traceId`; specify acknowledgements and errors.
- [ ] Define diagnostic status transitions and what qualifies as execution success.
- [ ] Choose which OpenSOVD operations will actually be demonstrated and which real uProtocol request/event exchange will carry them or their results.
- [ ] Define the control path from an application decision back to a simulator actuator.
- [ ] Agree on configuration ownership and environment-variable names; commit examples without credentials.

**Important boundaries:** VSS is a signal schema, MQTT is transport, and uProtocol is a service communication layer. Give each an explicit role. Do not describe a custom HTTP route as OpenSOVD, or an ordinary MQTT event as uProtocol, without implementing and verifying the relevant interface.

**Units:** CARLA velocity is commonly handled in metres per second, while a chosen VSS signal may use another unit. Verify metadata and convert at the adapter boundary. A mapping must include type and unit conversion, not only path renaming.

**Freshness:** An old healthy reading must not be presented as current health. Specify stale/unavailable states separately from healthy and fault states.

## 4. Ankit — CARLA, KUKSA, backend and CI/CD

### A1. Establish the CI baseline

Suggested branch: `ankit/chore/ci-baseline`

Suggested PR: **ci: validate backend, Python and deployment configuration**

- [ ] Inspect existing workflows and extend them instead of creating duplicate checks.
- [ ] Select Java and Python versions compatible with the committed project dependencies.
- [ ] Run backend tests with the repository's Maven setup.
- [ ] Run Python unit tests with integration tests explicitly separated.
- [ ] Validate committed configuration, including Compose configuration and deployment JSON.
- [ ] Check shell-script syntax and changed-line whitespace where appropriate.
- [ ] Build the provider and Velocitas images on a clean runner; expose dependency-resolution failures.
- [ ] Keep jobs bounded by timeouts and publish useful failure logs/test reports.
- [ ] Configure required PR checks once the workflow has passed on a real PR.

Acceptance: a clean checkout passes; an intentionally failing test blocks the PR; ordinary CI needs no developer laptop or CARLA server.

### A2. Implement two-vehicle KUKSA routing

Suggested branch: `ankit/feature/multi-vehicle-kuksa`

Suggested PR: **feat: route independent vehicle streams through separate KUKSA brokers**

- [ ] Add configuration for two broker instances with separate endpoints and no host-port collisions.
- [ ] Reuse the same compatible VSS definitions for both brokers.
- [ ] Define a vehicle-to-broker mapping; remove assumptions that all vehicles share one broker.
- [ ] Run separate Python provider instances or an explicitly routed provider for the initial integration test.
- [ ] Ensure scenario requests reach the provider responsible for the requested vehicle.
- [ ] Coordinate per-vehicle Velocitas endpoint configuration with Emmanuel.
- [ ] Test different values on the same VSS path in both brokers.
- [ ] Verify that injecting a fault into vehicle 2 does not change vehicle 1.
- [ ] Verify that taking one broker offline does not prevent the healthy vehicle from updating.

Acceptance: two live streams remain independent through acquisition and backend reads, including a one-vehicle fault and one-broker outage.

### A3. Replace backend development telemetry with live data

Suggested branch: `ankit/feature/live-vehicle-backend`

Suggested PR: **feat: expose live vehicle telemetry with freshness and failure handling**

- [ ] Inspect current development adapters and select a concrete supported way to acquire KUKSA data.
- [ ] Implement the live adapter or acquisition service; avoid assuming Java already has the required gRPC client.
- [ ] Resolve the broker from vehicle configuration and return the correct vehicle's readings.
- [ ] Preserve source timestamps and handle missing, stale, invalid and unavailable readings.
- [ ] Prevent a scheduler failure for one vehicle from cancelling updates for the fleet.
- [ ] Keep development and live modes explicit; do not silently replace a failed live connection with fabricated data.
- [ ] Document API fields for Bayan, including units, health/freshness meaning and error responses.
- [ ] Add tests for routing, unit conversion, freshness and independent failures.

Acceptance: backend API values can be compared against broker values for both vehicles; missing data is identifiable.

### A4. Connect CARLA and verify the return control path

Suggested branch: `ankit/feature/carla-bridge`

Suggested PR: **feat: bridge CARLA vehicle telemetry and control to the SDV pipeline**

- [ ] Verify a compatible packaged CARLA release and matching Python API on the available machine.
- [ ] Start with one vehicle, a small environment and a limited sensor set; record the tested configuration.
- [ ] Implement a stable mapping between CARLA actor IDs and project vehicle IDs.
- [ ] Acquire speed and the agreed obstacle-distance/sensor-health representation.
- [ ] Document exactly how distance is computed; distinguish geometric ground truth from a LiDAR-derived measurement.
- [ ] Map valid measurements into the appropriate vehicle's KUKSA broker.
- [ ] Mark unsupported signals unavailable; label any deliberately retained synthetic signals with their provenance.
- [ ] Receive targeted throttle/brake/steering commands through the agreed application interface.
- [ ] Validate command bounds, reject unknown vehicles, and implement the agreed timeout behaviour.
- [ ] Coordinate with Emmanuel so an external application makes the braking decision in the final control experiment.
- [ ] Add a second actor only after the single-vehicle path works; verify independent commands.
- [ ] Clean up spawned actors and sensor resources on exit.
- [ ] Keep CARLA-dependent tests separate from normal CI and provide a documented manual validation procedure.

Acceptance: CARLA measurement → broker → application decision → targeted command → observable CARLA vehicle response. Record source timestamps and action/trace identifiers where available.

Hardware checkpoint: determine actual feasibility early. If CARLA cannot run reliably, report it as pending and use the Python source to finish platform integration. Do not claim CARLA validation from synthetic tests.

### A5. Add end-to-end CI and image delivery

Suggested branch: `ankit/feature/image-delivery`

Suggested PR: **ci: validate the integrated pipeline and publish versioned images**

- [ ] Start the synthetic integration environment in CI with readiness checks.
- [ ] Exercise normal, fault and recovery states, with two-vehicle isolation where practical.
- [ ] Guarantee test cleanup and collect container logs on failure.
- [ ] Publish first-party images to GHCR after trusted branch/tag workflows pass.
- [ ] Tag images with immutable commit identifiers; record digests in release evidence.
- [ ] Build/test ARM64 and AMD64 only where dependencies and target deployments support them.
- [ ] Use minimum workflow permissions; do not expose deployment credentials to untrusted PRs.
- [ ] Coordinate an approval-gated deployment workflow with Emmanuel after his manual Kanto deployment passes.
- [ ] Verify rollback to a previously tested image.

Acceptance: a tested commit produces traceable images; integration tests pass automatically; deployment status reflects the actual target result.

## 5. Bayan — Ditto, MQTT events and fleet dashboard

### B1. Establish vehicle event contracts and MQTT ingestion

Suggested branch: `bayan/feature/vehicle-event-ingestion`

Suggested PR: **feat: ingest vehicle-specific application events**

- [ ] Review the existing `sdv/autonomy/status` publisher and agree contract changes with Emmanuel.
- [ ] Include or validate vehicle ID, schema version, source timestamp and the agreed autonomy fields.
- [ ] Decide how consumers detect a silent vehicle: timeouts, availability messages or another documented mechanism.
- [ ] Implement reconnect behaviour without creating duplicate subscriptions or processing loops.
- [ ] Reject malformed messages and unknown identities according to the agreed policy.
- [ ] Handle duplicate and out-of-order events so old updates do not overwrite newer state.
- [ ] Expose received events to the backend/twin update path using agreed interfaces.
- [ ] Test one vehicle's event without changing another's state.
- [ ] Document topic ownership and whether messages are retained; prevent retained stale status from appearing live.

Acceptance: two vehicle event streams are independently ingested; reconnect and stale-message behaviour are verified.

### B2. Implement real Ditto twin synchronisation

Suggested branch: `bayan/feature/fleet-digital-twins`

Suggested PR: **feat: maintain independent live Ditto twins for fleet vehicles**

- [ ] Inspect current Ditto adapters/scripts and identify development-only behaviour.
- [ ] Define stable twin IDs and features for telemetry, autonomy state, timestamps and availability.
- [ ] Configure a real Ditto instance and the policies needed by the project services.
- [ ] Create or initialise a separate twin per configured vehicle using a documented process.
- [ ] Choose one authoritative update path for each field; avoid multiple bridges racing to write the same state.
- [ ] Apply targeted updates without overwriting unrelated features.
- [ ] Preserve timestamps/provenance and reject older updates where required.
- [ ] Handle Ditto downtime and reconnect according to a documented retry/buffering policy.
- [ ] Verify actual Ditto reads after writes; mocks alone do not establish integration.

Acceptance: both twins update from their own vehicles, preserve independent faults, and display meaningful freshness information.

### B3. Build the live fleet dashboard

Suggested branch: `bayan/feature/live-fleet-dashboard`

Suggested PR: **feat: display live fleet telemetry, health and availability**

- [ ] Inspect and reuse existing frontend components and status mappings.
- [ ] Obtain the vehicle list from backend configuration/API rather than a fixed vehicle ID.
- [ ] Add fleet overview and selected-vehicle detail views.
- [ ] Show speed, agreed sensor values, autonomy status, source time and availability.
- [ ] Distinguish healthy, warning, braking, stale and unavailable states.
- [ ] Choose polling or streaming consistent with the backend; handle reconnect/loading/error states.
- [ ] Show units and signal provenance when mixed real/synthetic data is used.
- [ ] Ensure switching vehicles does not retain the previous vehicle's values.
- [ ] Add meaningful UI/API tests for routing and status interpretation.

Acceptance: two live vehicles can be inspected independently, with visible state changes and a correct disconnected state.

### B4. Add diagnostics and twin views to the dashboard

Suggested branch: `bayan/feature/fleet-diagnostic-ui`

Suggested PR: **feat: submit and track vehicle-specific diagnostic actions**

- [ ] Consume Emmanuel's agreed backend diagnostic API.
- [ ] Target the selected vehicle and show allowed diagnostic/scenario actions.
- [ ] Display submission acknowledgement separately from execution completion.
- [ ] Show action ID, trace ID, execution state and readable failure information.
- [ ] Prevent accidental duplicate submissions while a request is pending.
- [ ] Refresh action status and show terminal outcomes without affecting another vehicle's view.
- [ ] Display twin identity and agreed twin state through backend APIs; keep service credentials out of browser code.
- [ ] Test invalid requests, unavailable services and action failure.

Acceptance: a user starts a diagnostic operation from the dashboard and observes its actual final outcome for the selected vehicle.

### B5. Verify event-to-twin-to-dashboard behaviour

Suggested branch: `bayan/test/fleet-views-integration`

Suggested PR: **test: verify fleet event, twin and dashboard consistency**

- [ ] Add integration coverage for event ingestion and twin updates.
- [ ] Capture evidence for healthy → fault/braking → recovery across the relevant views.
- [ ] Verify an unavailable broker/application does not leave an apparently live healthy tile.
- [ ] Document frontend startup, service endpoints and troubleshooting.
- [ ] Supply demo steps and expected screenshots/output to the final integration checklist.

Acceptance: observed broker/application events, twin state and dashboard state agree within the documented update interval.

## 6. Emmanuel — Velocitas, diagnostics, uProtocol and Kanto

### E1. Complete the per-vehicle Velocitas application

Suggested branch: `emmanuel/feature/multi-vehicle-velocitas`

Suggested PR: **feat: run isolated vehicle health applications with targeted control**

- [ ] Inspect the existing app and verify which Velocitas SDK capabilities execute at runtime.
- [ ] Document any direct KUKSA-client workaround; generated models or installed packages alone do not prove SDK integration.
- [ ] Configure the application for a vehicle ID, broker endpoint and event destination.
- [ ] Prefer one app instance per vehicle initially to match broker isolation.
- [ ] Validate signal types, units and freshness before making decisions.
- [ ] Publish the event contract agreed with Bayan.
- [ ] Implement the agreed warning/braking/recovery policy and test threshold boundaries.
- [ ] Publish targeted control requests through the contract agreed with Ankit.
- [ ] Separate a requested brake command from measured actuator/vehicle response.
- [ ] Define response to missing/stale sensors and command delivery failure.
- [ ] Test healthy, obstructed, failed-sensor and recovery states for independent vehicles.

Acceptance: two applications report the correct vehicle state; one vehicle's obstacle produces only that vehicle's control request.

### E2. Implement a concrete OpenSOVD diagnostic path

Suggested branch: `emmanuel/feature/opensovd-diagnostics`

Suggested PR: **feat: execute vehicle-specific diagnostics through OpenSOVD integration**

- [ ] Verify the actual OpenSOVD component/version/API and its supported operations before coding against it.
- [ ] Select a small, demonstrable operation set and document how it maps to project diagnostics.
- [ ] Identify which existing adapters only log or fabricate results and implement the real execution path.
- [ ] Maintain vehicle ID, action ID and trace ID through request, execution and response.
- [ ] Connect backend submissions to the correct diagnostic target.
- [ ] Implement legal state transitions and explicit failure/time-out handling.
- [ ] Mark an action complete only when execution evidence meets the agreed success condition.
- [ ] Keep scenario injection and standards-based diagnostics clearly identified when their semantics differ.
- [ ] Test unknown vehicles, unsupported operations, duplicate requests and disconnected targets.
- [ ] Provide Bayan with sample request/response bodies and status meanings.

Acceptance: a backend/dashboard request reaches a real diagnostic implementation and returns a verifiable terminal status for the correct vehicle.

### E3. Implement and demonstrate uProtocol service communication

Suggested branch: `emmanuel/feature/uprotocol-service-flow`

Suggested PR: **feat: exchange correlated vehicle service messages using uProtocol**

- [ ] Choose the concrete uProtocol implementation and supported transport for this repository.
- [ ] Agree one useful request/response or event flow within the diagnostic/control architecture.
- [ ] Define vehicle/service addressing and message schemas, preserving trace correlation.
- [ ] Use the chosen uProtocol library and its addressing/message semantics.
- [ ] Connect a real sender and receiver across the selected transport.
- [ ] Handle unavailable destinations, timeouts and malformed messages.
- [ ] Avoid duplicating the existing MQTT status path without a documented reason.
- [ ] Add tests plus a reproducible runtime exchange showing sender, destination and result.

Acceptance: a captured exchange demonstrates actual uProtocol communication and a useful effect in the project.

### E4. Validate Kanto on Linux

Suggested branch: `emmanuel/feature/kanto-runtime-validation`

Suggested PR: **feat: validate Kanto application deployment on Linux**

- [ ] Obtain a Linux target through an Ubuntu VM, supported WSL2 setup or remote Linux host.
- [ ] Check current Kanto/runtime requirements and select compatible architecture and versions.
- [ ] Install Kanto and its required container runtime inside that target; do not assume Docker Desktop supplies Kanto.
- [ ] Review existing descriptors, deployment tests and `velocitas-app/kanto/deploy.sh`.
- [ ] Make broker/MQTT addresses reachable from the target; test actual networking rather than using host `localhost` blindly.
- [ ] Use an image available to the target runtime through a registry or a verified import process.
- [ ] Deploy and start the Velocitas application through Kanto.
- [ ] Demonstrate status inspection, restart, logs, update and removal/redeployment as supported.
- [ ] Verify a real application event reaches MQTT after deployment.
- [ ] Coordinate with Ankit to record the immutable image reference and add deployment automation.
- [ ] Document setup, commands, tested architecture and teardown.

Acceptance: evidence includes Linux/Kanto version, image reference, running application status and a fresh vehicle event. If unavailable, label runtime validation pending.

### E5. Verify the diagnostic and edge path together

Suggested branch: `emmanuel/test/diagnostic-edge-integration`

Suggested PR: **test: verify diagnostic execution and deployed vehicle applications**

- [ ] Run the application from the Kanto target against the shared integration environment.
- [ ] Submit a vehicle-specific diagnostic operation and trace the agreed service exchange.
- [ ] Confirm actual response, terminal action state and dashboard update.
- [ ] Verify recovery after an application restart or temporary service outage.
- [ ] Record reproducible evidence and known limitations.

Acceptance: another member can follow the instructions and reproduce the diagnostic/deployment demonstration.

## 7. Git and PR checkpoints for every member

Use the repository's existing contribution rules where present. Branch names above are suggestions, not branches already created.

1. Check `git status --short --branch`; preserve unrelated changes.
2. Update a clean local `main` with `git pull --ff-only origin main`.
3. Create one focused branch from `main`, or document an explicit dependency on another unmerged branch.
4. Open a draft PR after the first meaningful commit so ownership is visible.
5. Commit in reviewable checkpoints: contract/configuration, implementation, meaningful tests, documentation/evidence.
6. Run the relevant tests and `git diff --check` before pushing.
7. In the PR, state the problem, resulting behaviour, validation performed and remaining limitations.
8. Request review from the member consuming the interface.
9. Merge only after required checks and agreed review pass. Refresh dependent branches before further work.

Do not merge another member's unfinished implementation merely to resolve local setup problems. Coordinate edits to Compose files, shared DTOs, application properties and workflow files.

## 8. Suggested implementation sequence

| Checkpoint | Ankit | Bayan | Emmanuel |
|---|---|---|---|
| 1 — Contracts and baseline | CI baseline; broker/vehicle mapping | Event and twin contracts | App, diagnostic and command contracts; identify Linux target |
| 2 — Two live synthetic vehicles | Two brokers and providers; backend telemetry | Event ingestion and Ditto updates | Two app instances; correct event identity |
| 3 — Complete user workflow | Backend availability and simulator routing | Fleet views and diagnostic UI | OpenSOVD operations and uProtocol exchange |
| 4 — Runtime and simulation | CARLA bridge and command routing | Consistency/reconnect validation | Kanto deployment and external control decisions |
| 5 — Delivery and demonstration | End-to-end CI, image publishing and deployment support | Dashboard/twin evidence | Diagnostics/Kanto evidence |

CARLA setup and Linux-target availability should be investigated early, even though their integration PRs may land later. This exposes hardware and environment blockers before final demonstration work.

## 9. Shared final acceptance checklist

- [ ] A clean checkout has clear setup instructions and example configuration.
- [ ] Basic Java/Python CI passes and Docker images build on a clean runner.
- [ ] Two vehicles use separate brokers and remain isolated through the application and backend.
- [ ] Fleet telemetry and twin state reflect actual source data and freshness.
- [ ] The dashboard supports vehicle selection, warnings, unavailable states and diagnostic tracking.
- [ ] A fault in vehicle 2 leaves vehicle 1 unaffected.
- [ ] An external vehicle application issues a control decision and the targeted simulator responds.
- [ ] Real OpenSOVD and uProtocol exchanges are demonstrated for their defined operations.
- [ ] Kanto starts the application on Linux and produces a fresh observable event.
- [ ] CARLA integration is either demonstrated with recorded configuration or explicitly marked pending.
- [ ] The original synthetic demonstration remains available for repeatable testing.
- [ ] Tested images are traceable to a commit; deployment and rollback are documented.
- [ ] Each component's status is labelled accurately: implemented, unit-tested, integration-tested or runtime-validated.

## 10. Instructions for a teammate's AI assistant

Use this document together with the current repository. Read source code, configuration, tests and repository instructions before proposing edits. Identify which tasks already exist, then implement the assigned member's remaining work in small PRs. Follow the agreed ownership and contracts. Verify current third-party APIs and runtime compatibility before using them. Provide complete modified files when guiding manual edits. Report real validation evidence and distinguish it from mocks, prepared configurations and untested claims.
