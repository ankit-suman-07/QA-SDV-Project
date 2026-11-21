# Ankit V2 preparation baseline

Fetched main and task starting SHA: `e3b4a6af5421a3b9c88e2c16f51d78f929052990`.
It includes shared prep PR #52 (`596b38694ed2b1f50769557586801ce27ff98124`)
and Bayan's native feasibility handoff PR #53
(`2680bf665f9b6a853ad0f43839b6cef01d4f5be6`).

Verified V1 implementation reference: `4afbbd8c11425a9e0e1701fea66b7ed13731abfe`.
The exact-main record covers a two-synthetic-vehicle run and three same-device
Kanto managed cycles. It retains an aggregate wrapper failure with separately
reviewed gate results. Human acceptance, B5 remote LAN wording, production
permissions/freshness/timing, skill provenance and release/delivery remain
qualified or open in the V1 findings.
[Exact-main run](../evidence/v1/merged-main-20261115/README.md) ·
[V1 readiness findings](findings/v1-release-readiness.md)

The tracked source index is hyphenated, as required by root AGENTS and referenced
by the technical decisions. Its prior underscore rename instruction conflicted
with that workflow. Current V2 task ownership governs over historical allocations.
Emmanuel supplies actor/source identity, extraction, scenario execution and
replay. Ankit owns validation and KUKSA writes, backend actions and the sole
Spring fleet aggregator/writer. Bayan owns health/recovery, individual twins
and history, native diagnostics and coordinated Kanto validation.
[Source index](SOURCE-OF-TRUTH.md) · [V2 plan](11-FINAL-phase-v2-plan.md) ·
[Technical decisions](12-FINAL-phase-v2-technical-decisions.md) ·
[Task acceptance](13-FINAL-phase-v2-tasks-and-acceptance.md)

## What the shared prep covers

| Area | Specified and checked offline | Pending owner decision or proof |
|---|---|---|
| C1–C2 identity and time | Synthetic manifest pins three vehicles and maps simulation origin 100 to UTC midnight. Event IDs survive retries. Sequences exercise duplicate/equal/late events and explicit successor registration, including rejection before registration and after retirement. Replay preserves simulation time and shifts UTC together. | Emmanuel supplies real actor/sensor mapping and anchor uncertainty. Ankit and Bayan review how trusted registration is provisioned and restored, including persisted generation/watermark and newer UTC. Fixture registration is a harness control. |
| C2–C4 cadence, dropout and recovery | 10 Hz nominal and 0.5 s inclusive maximum healthy gap are prep defaults. Recovery/clock sequences exercise the 0.5 s boundary and greater-than gap, reset on dropout/stale/future input, and retain severity until 2 s of continuous healthy samples. Unavailable has null distance and false sensor validity. Health events carry recoveryState, recoveryStartedAt and sourceSilent. Clock-only silence retains last-known health and cancels recovery. | Emmanuel and Bayan review nominal cadence, gap and detection reasons. The fixtures exercise source/evaluation time. Live monotonic receipt gaps, clock sync and the exact wire representation of the C2 dropout reason still need review. Observation examples use the lidar pair without a reason key. |
| C4–C6 freshness and budgets | Literal cases bracket 5 s and 30 s age and 1 s future tolerance. Diagnostic cases anchor inject/clear execution at 10 s and exercise lifecycle and correlation. | Preserve freshness behavior and review the defaults separately from measured budgets. The 2 s native request and provider acceptance limits and 30 s managed restart limit need real deadline evidence. Mock timeout is a controlled result. |

See [C1–C7](v2-interface-contracts.md), [fixture coverage](../tests/fixtures/v2/README.md)
and [offline commands](v2-independent-development.md).

## Authorized observation companion binding

Ankit Suman authorized implementation in the PR #56 continuation instruction.
This supersedes the initial proposal and motion-input gap for implementation.
Bayan's review of consumer behavior, registry and ACLs and Emmanuel's review
of source motion, timing and rollover remain pending under C7.

Use `sdv/{vehicleId}/v2/observations`, QoS 1, retain false, and the unchanged
C2 envelope. Serialize one publisher per vehicle, with a distinct KUKSA
endpoint and MQTT client ID. The adapter uses KUKSA Client 0.5.1 VAL v1 Set
with a deadline and checks the response for top-level and per-path errors.
Only after confirmed writes can it send the companion. Partial or uncertain
KUKSA writes leave the batch pending. After confirmation the adapter retries
only the companion. An uncertain MQTT acknowledgement can cause redelivery
with the original identity. The receiver must deduplicate. There is no
cross-system atomicity and PUBACK confirms broker acceptance only.

The adapter supplies source UTC in each KUKSA request. The isolated 0.7.0
broker stamped write time on readback, so consumers use the companion's
original source UTC and identity. The companion identifies the exact mapped
write input for that vehicle. A cached broker value may have been superseded
or lost and cannot attest to sample identity or freshness.

Velocitas owns the 100 ms silence timer and strictly greater than 0.5 s gap
rule. A separate versioned status message must preserve the last genuine
observation identity and time and carry independently ordered status.
Bayan's scheduler and status ingress are separate work. The adapter emits no
observation on silence, and a status transition must never go through as a
fresh observation. Backend source freshness remains independent.

[Configuration, recovery behavior and verification](../evidence/v2/ankit/observation-kuksa-adapter/README.md#publication-continuation)

## Diagnostic project handoff

Use the existing [Bayan feasibility record](v2-native-diagnostic-feasibility.md)
and C6 project fixtures pending native binding review.

- Selected-vehicle health request carries vehicleId/actionId/traceId. Check
  those against the returned IDs and native request/response correlation.
  Project result preserves source observation identity/time, health and
  availability. Deadline is 2 s. Bayan owns the pinned transport, URI,
  protobuf and native metadata binding.
- Selected-vehicle fault read uses a configured native vehicle/component
  binding and a least-privilege read subject. Project projection preserves
  lidar-obstruction or lidar-sensor-failure, severity, first/last seen, source
  session/event and correlation. Preserve metres and 5/10 m thresholds for
  obstruction, null distance and unavailable sensor for failure, and empty
  faults for a successful healthy read. Unknown target, denied access and
  unavailable provider remain errors. Bayan must prove the provider/ECU mapping
  and native permission model. The project still needs an explicit reviewed
  bounded OpenSOVD read deadline.
- Authorize backend dispatch per vehicle/action. Ankit tracks vehicleId,
  actionId and traceId, rejects any mismatch, and records acceptance within
  2 s separately from execution (10 s scenario, 30 s managed restart).
  Target only the configured scenario executor or Kanto lifecycle executor as
  appropriate. Timeout preserves uncertainty and late evidence cannot rewrite
  terminal state. Clear completion is separate from observed recovery. Restart
  success requires lifecycle and fresh post-start observation evidence.
- Ankit owns backend and KUKSA privileges, Bayan owns native service and
  per-vehicle MQTT permissions, Emmanuel owns CARLA scenario permissions.
  Review concrete subject grants and TLS with the affected owners under C7.
  Loopback mocks support independent mapping tests while native work is pending.
