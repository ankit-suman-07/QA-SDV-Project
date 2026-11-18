# Native OpenSOVD fault-read feasibility

Eclipse OpenSOVD Classic Diagnostic Adapter (CDA) and the official DoIP simulator were built and inspected as Linux ARM64 at upstream commit `c52b062c6e8d3dcfe4be05583f233ee5a2ec9d3f`. CDA used Rust and Cargo 1.88.0. The simulator used Temurin 21.0.9+10-LTS and Gradle 8.14.3. Build and inspection exited zero for both images. No services were started in the build run. [Pinned CDA source](https://github.com/eclipse-opensovd/classic-diagnostic-adapter/tree/c52b062c6e8d3dcfe4be05583f233ee5a2ec9d3f)

| Local artifact reused for runtime | Image ID |
| --- | --- |
| CDA, build suffix `20261117-225712-da26dc611a4b` | `sha256:3b4ce18ab38c46305eb5b1d065a18dbb9da9885a53606323fc2cfa0f12bd7add` |
| ECU simulator, same build suffix | `sha256:4f4e5cd3432ca1d86e1ee4bbd9cd859edf02dfe5b94af015cda80ac1e4f82081` |

Native runtime run `bayan-cda-345f95800268` verified the fixture VIN and then invoked `GET /vehicle/v15/components/flxc1000/faults?status[testFailed]=true` with upstream test authorization. CDA used the FLXC1000 MDD and communicated over DoIP/UDS with logical address `0x1000`. The isolated bridge published no host ports.

| Fixture case | Result |
| --- | --- |
| No active fault | HTTP 200 and `{"items":[]}`. UDS `19 02 01` returned `59 02 FF` without a DTC record. |
| Active fault | HTTP 200 with active `01E240`, mask `29`. The simulator recorder captured `19 02 01`; simulator and CDA logs corroborate `59 02 FF 01 E2 40 29`. |
| Provider unavailable | With the simulator stopped and CDA running, HTTP 504 with SOVD `not-responding` arrived within the 15-second client deadline. |

The filter checks the active-fault view. It excludes zero-status MDD catalogue entries that can appear in an unfiltered collection. No conclusion about historical fault memory follows. The VIN, injected code and authorization are test fixtures. Project fault-to-DTC mapping, permissions and live selected-vehicle reads still require verification. This CDA evidence is distinct from the [earlier gateway and custom adapters](../../../opensovd/README.md). Full V2-06 acceptance remains pending. [Reproduction](reproduction.md)
