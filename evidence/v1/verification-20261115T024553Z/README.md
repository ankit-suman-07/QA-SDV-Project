# Phase V1 repeated real-service verification — 20261115T024553Z

Independent launcher recorded **exit 0**. All ten implemented real core gates
passed on the same committed harness revision `2118300`. Five fault and five
recovery trials reached MQTT, twin, API, derived fleet API, materialized fleet Thing
and actual dashboard. Freshness/null, negative/restart, denied writes and reconnect
checks passed. The 12s KUKSA outage again recovered in this 1s provider workload;
historical F01 and unmerged #38 remain open. Kanto remains BLOCKED and required.

This uses the explicitly prepared isolated deployment: normalize Accept-Encoding
in nginx and bootstrap each initial feature from its first real MQTT observation
before starting ingress. No mock substitutes, shared resets or concurrent writers.
These preparation requirements remain production setup gaps, not accepted fixes.

[Manifest](manifest.json) · [Launcher/exact exit](launcher.json) · [Results](results.json)
· [Commands/exits](commands.json) · [Raw measurements](measurements.json)
· [n/median/range](statistics.json) · [CPU/memory](resources.jsonl)
· [Limitations](measurement-limitations.json) · [Artifact hashes](artifact-sha256.json).

Screenshots and twin/API/fleet snapshots are saved for every trial. Baseline and
language/SDK regression results were recorded separately in the preceding prepared
run's [external checks](../verification-20261115T024001Z/external-checks.json).
[Full dated findings](../../../docs/findings/v1-implementation-verification.md#follow-up--2026-11-15-utc-integrated-acceptance-on-an-isolated-prepared-deployment)
retain the failed earlier attempts and exact remaining release/Kanto prerequisites.

Text command/service outputs were authentication-redacted and trailing whitespace
normalized before durable tracking; source/event IDs, timestamps, results and exits
are preserved. Hashes cover the reviewed secret-free artifacts.
