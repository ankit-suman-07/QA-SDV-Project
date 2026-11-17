# Native diagnostic feasibility — November 17, 2026

Preparation/source inspection only. **No native exchange or live fault read was
executed.** Independent project mocks do not close V2-06.

## uProtocol selected-vehicle health

Keep the repository pin `org.eclipse.uprotocol:up-java:1.5.8` and protobuf 3.25.3
in [pom.xml](../uprotocol/pom.xml). Official tag is **up-java-1.5.8**, not v1.5.8.
The current repository publisher is serialization-oriented, not an RPC transport.
No Maven executable or cached 1.5.8 artifact was available on this preparation host;
no dependency installation/build was attempted.

Verified directly against official tagged source:

- [RpcClient](https://github.com/eclipse-uprotocol/up-java/blob/up-java-1.5.8/src/main/java/org/eclipse/uprotocol/rpc/RpcClient.java): `invokeMethod(UUri, UPayload, CallOptions)` returns `CompletionStage<UMessage>`.
- [RpcServer](https://github.com/eclipse-uprotocol/up-java/blob/up-java-1.5.8/src/main/java/org/eclipse/uprotocol/rpc/RpcServer.java): register/unregister an `URpcListener` at a method URI, returning UStatus.
- [CallOptions](https://github.com/eclipse-uprotocol/up-java/blob/up-java-1.5.8/src/main/java/org/eclipse/uprotocol/rpc/CallOptions.java): builder timeout is milliseconds; project budget 2000 ms.
- [UTransport](https://github.com/eclipse-uprotocol/up-java/blob/up-java-1.5.8/src/main/java/org/eclipse/uprotocol/transport/UTransport.java): send UMessage and register/unregister UListener at UUri; this is an interface, not a configured network implementation.

Selected functional shape: one health request to one registered vehicle service,
protobuf project payload carrying vehicleId/actionId/traceId; response preserves
those fields and source observation identity/health/availability. Native request
and response UMessage metadata must correlate per the chosen transport/spec
revision. Do not copy APIs from newer 2.x/3.x documentation or use arbitrary JSON
as a native message. Topic/URI allocation, concrete transport artifact/version,
protobuf service/payload and metadata-correlation wiring remain **blocked pending
Bayan's minimal sender/receiver spike**. Ankit reviews the project result mapping.
The library interfaces support the pattern, but do not prove a transport works.

Close blocker with a pinned transport dependency, compile/run instructions,
request/response native metadata trace (redacted), wrong vehicle/correlation,
listener failure and 2 s timeout evidence. A custom in-memory implementation may
help SDK tests but must be labelled as such; no deployment acceptance inferred.

## OpenSOVD vehicle-specific fault read

The repository has no pinned native gateway dependency. Its
[mapper/readme](../opensovd/README.md) explicitly describes a read-only mock gateway
and standalone custom adapters. That is not actual project-fault integration.

Inspected official opensovd-core revision **7688efa** from its release page: the
[component client](https://github.com/eclipse-opensovd/opensovd-core/blob/7688efa/opensovd-client/src/entities/component.rs)
exposes data and relationships; that inspected interface alone does not establish
a project fault-read endpoint. Do not infer `/faults` from `/data` support.

Selected feasibility candidate (source pin, not installed project dependency):
**Eclipse OpenSOVD classic-diagnostic-adapter**, commit
`9bc2eccca3c4fc2126231326a1b8b8b01381556c`.
Its [README](https://github.com/eclipse-opensovd/classic-diagnostic-adapter/blob/9bc2eccca3c4fc2126231326a1b8b8b01381556c/README.md)
maps MDD ECU identities to `/vehicle/v15/components/{ecu}` and lists fault
subresources. The [fault handler and tests](https://github.com/eclipse-opensovd/classic-diagnostic-adapter/blob/9bc2eccca3c4fc2126231326a1b8b8b01381556c/cda-sovd/src/sovd/components/ecu/faults.rs)
implement a secured GET using the ECU DTC provider, returning a response with
`items` of fault records (code, scope, optional display code/name/severity/status).
Thus a supported candidate operation is GET
`{vehicleSpecificCdaBase}/vehicle/v15/components/{configuredEcu}/faults`.
Discover actual component IDs; do not invent vehicle IDs as CDA ECU names.

**Exact blocker:** CDA requires MDD/ODX configuration and a supported ECU/DTC
provider. This project has CARLA LiDAR project faults, no such provider or numeric
DTC allocation. No validated mapping connects three vehicle namespaces to CDA
instances/ECUs. Installing CDA would not establish that mapping. Bayan must verify
an appropriate provider/implementation and permissions, or bring Ankit the smallest
supported alternative; do not silently add a fake ECU or claim the historical
gateway supports vehicle faults. No release upgrade or installation in this PR.

Needed live evidence: pinned implementation/config, selected vehicle/component
mapping, actual healthy/fault read, unknown target/auth/service errors and agreement
with source faults. No custom field in our fixtures is claimed as native SOVD.

## Independent boundary while blocked

[Contract V2-C6](v2-interface-contracts.md) and diagnostic fixtures define a
**PROJECT_MOCK_NOT_NATIVE_PROTOCOL** health/fault boundary. HTTP substitutes expose
`/mock/v2/diagnostics/{vehicleId}/health` and `/faults`. They preserve project IDs,
fault meaning and correlation for backend/UI work. Native addressing, transport,
security and wire mapping remain separate reviewed work. All owners can build
against this boundary now; final diagnostic integration still depends on the
native spikes above. No formal teammate approval is asserted.
