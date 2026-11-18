# Native uProtocol health RPC feasibility

Recorded November 17, 2026 on Docker Desktop with Linux ARM64 containers. Two independent processes used `up-rust 0.9.0` and `up-transport-mqtt5 0.4.0`, with `Mqtt5Transport` through Mosquitto 2.0.23 (MQTT 5). The RPC classes are named `InMemoryRpcClient` and `InMemoryRpcServer`; their underlying transport in this run was the broker-backed transport. `GetVehicleHealth` was registered at `up://bayan.probe/A001/1/A0`. The archived Rust image reference carries a `1.94.0-bookworm` tag and a pinned digest. The actual compiler reported 1.94.1 on AArch64.

| Fixture case | Observed outcome | Native request ID |
| --- | --- | --- |
| Healthy | HEALTHY / NONE, correlation matched | `01a1ecbc-50fc-7aa1-ba03-60e3198dba6c` |
| Fault | CRITICAL / LIDAR_OBSTRUCTION, correlation matched | `01a1ecbc-512b-7795-b22d-7d1e719931a4` |
| Server stopped, broker running | DeadlineExceeded at 1,506 ms, with a 1,500 ms TTL | `01a1ecbc-7d8e-7b04-96a7-05cd28552f32` |

The server logged both successful native request IDs. The client used SDK correlation and checked the echoed request ID. The separate response-envelope message ID was not recorded. The transcript shows cleanup of the isolated project. The operator reported exit zero; the transcript does not separately capture the parent PowerShell exit value.

The values for `vehicle-001` came from synthetic program fixtures. This did not validate a live observation companion, CARLA, KUKSA or Ditto data. The 1,500 ms TTL is a probe parameter; the project request budget documented in the V2 preparation remains 2 s. Production URI and payload mappings and the integrated timeout check remain pending. Full V2-06 acceptance is open. [Earlier source inspection](../../../docs/v2-native-diagnostic-feasibility.md) ? [Reproduction](reproduction.md)
