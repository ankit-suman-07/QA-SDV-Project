# Reproduction instructions

Ask the evidence owner for the approved protocol bundles in an authorized review channel. Archive identifiers are listed below. Use fresh scratch copies, from the directory containing the named script. Keep existing evidence logs intact.

| Archive | Command | Prerequisites and expected result |
| --- | --- | --- |
| `uprotocol-native-rpc-2026-11-17` | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./run-probe.ps1` | Windows ARM64, Docker Desktop Linux ARM64, Compose v2, required registries, archived Cargo.lock and pinned image references. Expect healthy and fault responses with matched correlation and a bounded DeadlineExceeded with the server stopped. |
| `opensovd-arm64-build-2026-11-17` | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./build-arm64.ps1` | Extract the approved pinned upstream tree alongside the script and Dockerfiles. Expect two builds and two linux/arm64 image inspections. No services should start. |
| `opensovd-native-fault-read-2026-11-17` | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./run-probe.ps1` | Use the exact CDA and simulator tags and image IDs recorded in the runtime archive, plus its Compose, MDD and overlay configuration. The runner rejects image-ID mismatches. Expect the VIN gate, HTTP 200 empty/active results and HTTP 504 offline, with recorded UDS evidence. |

The child PowerShell execution-policy flag applies to the archived runners for that process. Follow host policy. Record Docker and Compose versions, runtime logs, commands, exit codes and the image IDs or digests. Local images are not bundled; build-time OS packages and the broker tag impose reproducibility limits. These commands exercise isolated fixtures.

For a V2-07 evidence review, use the archived frozen benchmark and approved offline CPython 3.12.10 ARM64 environment. The benchmark base was `4abc30f93c77fb05f6cecce16659fc603a33e6b5`. The evidence owner holds the restricted coordinator inputs and raw transcripts. Independent grading used disposable corrected copies and identical commands. The shared regression command was:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_mqtt_ingress.py tests/test_mqtt_subscriber.py tests/test_mqtt_poison_inputs.py tests/test_ditto_v1_writer.py tests/test_ditto_v1_cli.py tests/test_ditto_http.py tests/test_v1_contracts.py
```

Use the approved dependency lock and local loopback-capable grading environment, with automatic pytest plugin loading and bytecode writes disabled. Keep any coordinator-only material outside agent workspaces. See the [evaluation](skill-evaluation.md) for results and limitations.
