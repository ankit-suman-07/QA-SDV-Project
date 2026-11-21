# MVP, V1 and V2 stage comparison

November 21, 2026. V2 implementation review starts at merged main
`c5b358f824ce6230342c12a99a35cbf3b84eb3e5`. No live V2 measurement run
was available. The published comparison preserves the original evidence
boundaries.

| Stage | Features and architecture | Verification and measurements |
|---|---|---|
| MVP | One synthetic vehicle. Simulator → KUKSA → Velocitas → MQTT status, direct obstruction inject and clear. | Historical single-vehicle functional record with missing console corroboration. Separate CSV has five passing command-to-observed-MQTT trials for vehicle-001, median **12.075 s** inject (8.035–42.427 s), **10.063 s** clear (10.043–16.097 s). Timing SHA, full run configuration and resource samples were not recorded. [Baseline](../../evidence/v1/baseline.md) · [Raw timings](../../evidence/v1/mvp-timings-20261108T010116457743Z.csv) · [Qualifications](mvp-to-v1-comparison.md#mvp-baseline-and-revision-discrepancy) |
| V1 | Two synthetic vehicles, independent brokers/edge instances, MQTT ingress into individual Ditto Things, Spring state/fleet and dashboard. Same-device Kanto managed restart evidenced separately. | Exact-main engineering evidence exists at `4afbbd8c11425a9e0e1701fea66b7ed13731abfe`. An earlier prepared-stack campaign recorded five inject and five clear trials, zero failed, with command-to-observed-MQTT medians **3.688 s** inject, **2.409 s** clear, and separate twin/API/fleet/browser completion samples. Docker stats are workload observations. The campaign includes scenario and polling delays and has no measured UTC error budget. [Verified main](../../evidence/v1/merged-main-20261115/README.md) · [Campaign statistics](../../evidence/v1/verification-20261115T024001Z/statistics.json) · [Raw measurements](../../evidence/v1/verification-20261115T024001Z/measurements.json) · [Limits](../../evidence/v1/verification-20261115T024001Z/measurement-limitations.json) |
| V2 | Targets three CARLA/front-LiDAR actors. Merged publisher preserves source identity on the companion topic. Spring's sole fleet writer supports V2 projections, durable targeted action tracking and a V2 dashboard. Reviewed live CARLA source and Velocitas/ingress wiring remain prerequisites. | Publisher component probe used real KUKSA/MQTT with synthetic input. Backend/dashboard checks used controlled HTTP boundaries. Bayan's native fixture probes establish feasibility at their documented scope. Joined source-to-browser, real selected-vehicle native diagnostics and CARLA-backed Kanto remain blocked. Live latency, update coverage, CPU and memory remain pending. [Integration readiness](../../evidence/v2/ankit/three-vehicle-integration/README.md) · [V2 measurement procedure](../../evidence/v2/ankit/measurements-comparison/README.md) · [Native feasibility evidence](../../evidence/v2/task-1/README.md) |

The historical MQTT runs use different workloads, progression, endpoints and
trial environments. Their medians describe each recorded campaign. There is
no matched performance delta or percentile estimate. V2 reports source
detection, each observed propagation boundary and the separate recovery
window. Its resource series has a specific workload and scope. Preserve
older stage evidence as recorded when comparing features or coverage.
