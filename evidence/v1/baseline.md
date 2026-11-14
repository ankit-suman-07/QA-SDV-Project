# MVP baseline — single-vehicle rerun

**Status:** Runtime rerun passed on November 7, 2026. The exact previous-term submission revision remains unconfirmed.

| Field | Recorded evidence |
|---|---|
| Repository and revision | QA-SDV-Project, tested at `098fd2ebf4fe04b08f0e965e494e03415b2aa673`. The pre-run working tree was clean. The October report separately identifies PR #27 merge `7736b6e` as a historical candidate. |
| Environment | Local Docker Compose stack on a MacBook Pro. The log shows KUKSA Databroker 0.7.0, Eclipse Mosquitto 2, the Python simulator provider, and the Velocitas autonomous health application. Host Docker and Python versions were not recorded. |
| Startup and demo | From the repository root, run `SIMULATED_VEHICLE_ID=vehicle-001 bash scripts/run-autonomous-mvp-demo.sh`. The script builds and recreates the Compose services, then waits for the simulator control API and Velocitas app. |
| Expected behavior | Start healthy, inject `LIDAR_OBSTRUCTION` on `vehicle-001`, observe emergency braking on MQTT, then clear the obstruction and observe recovery. |
| Observed result | MQTT published `HEALTHY` at 06:34:38 UTC, `EMERGENCY_BRAKING` at 06:35:23 UTC with `autonomousBraking: true`, and `HEALTHY` at 06:35:34 UTC with braking inactive. Both simulator action responses identified `vehicle-001`. The script printed its success message. The uploaded log does not include a separate shell exit code. |
| Runtime evidence | [Console log](mvp-demo.log) records the live simulator → KUKSA → Velocitas → Mosquitto path. |
| Historical CI | The [October Testing and DevOps Report](https://chatgpt.com/library?file_id=libfile_6e6d9fdc09a48191a778ee3ee9339f59&account_id=personal) reports six passing checks for PR #27, including the scenario and nine live KUKSA signal checks. This rerun records the demo only. |
| Performance measurements | A separate timing run passed all five trials for `vehicle-001`. See the results below. |

Keep two-vehicle isolation and live Ditto and Spring Boot checks in the separate Phase V1 evidence.

## MVP timing results

[Raw timing CSV](mvp-timings-20261108T010116457743Z.csv) · Run started November 7, 2026, at 8:01 p.m. EST (November 8 at 01:01 UTC). The Git revision for this separate timing run was not recorded in the CSV.

| Metric | Median | Min–max |
|---|---:|---:|
| Inject `LIDAR_OBSTRUCTION` → receive `EMERGENCY_BRAKING` on MQTT | 12.08 s | 8.03–42.43 s |
| Clear `LIDAR_OBSTRUCTION` → receive `HEALTHY` on MQTT | 10.06 s | 10.04–16.10 s |

### How the timing evidence was collected

1. Start Docker Desktop and wait for Docker to be ready.
2. Open a terminal in the repository root and activate the Python environment.
3. Run the timing-enabled demo script:
   `bash scripts/run-autonomous-mvp-demo-measure.sh`
4. Keep the generated `mvp-timings-<timestamp>.csv` in `evidence/v1/`
   and link it from this document.

The script starts the Docker Compose stack, then injects and clears a
LiDAR obstruction in each trial. It measures elapsed time from each HTTP
command to receipt of the expected MQTT status for `vehicle-001`.

The updated demo script uses one host monotonic clock to measure elapsed time from immediately before the HTTP request to receipt of the expected MQTT status for the selected vehicle. These times include the simulated scenario's progression and the status delivery path. All five trials are included. The first fault trial took 42.43 s, and the CSV does not establish the cause.

## Clarification — November 14, 2026 UTC

The referenced `mvp-demo.log` is missing from the inspected repository and has no tracked history at that path. The run description above is preserved as the historical record, not newly reproduced verification. `mvp-revision.txt` contains `f06aa9583d23d1aee0ff87313186d1398f05fe7a`; `098fd2e` is its direct child and changes only evidence scaffolding, so their implementation code is identical. The exact previous-term submission and the separate timing run's tested revision remain unresolved. Neither hash has been overwritten or assigned to that timing run. See the [MVP → Phase V1 comparison](../../docs/findings/mvp-to-v1-comparison.md) for history, exact recalculated statistics and evidence limitations.
