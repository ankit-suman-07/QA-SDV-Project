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
| C1–C2 identity and time | Synthetic manifest pins three vehicles and maps simulation origin 100 to UTC midnight. Event IDs survive retries. Sequences exercise duplicate/equal/late events and explicit successor registration, including rejection before registration and after retirement. Replay preserves simulation time and shifts UTC together. | Emmanuel supplies real actor/sensor mapping and anchor uncertainty. Ankit and Bayan agree how trusted registration is provisioned and restored, including persisted generation/watermark and newer UTC. Fixture registration is a harness control. |
| C2–C4 cadence, dropout and recovery | 10 Hz nominal and 0.5 s inclusive maximum healthy gap are prep defaults. Recovery/clock sequences exercise the 0.5 s boundary and greater-than gap, reset on dropout/stale/future input, and retain severity until 2 s of continuous healthy samples. Unavailable has null distance and false sensor validity. Health events carry recoveryState, recoveryStartedAt and sourceSilent. Clock-only silence retains last-known health and cancels recovery. | Emmanuel and Bayan review nominal cadence, gap and detection reasons. The fixtures exercise source/evaluation time. Live monotonic receipt gaps, clock sync and the exact wire representation of the C2 dropout reason still need review. Observation examples use the lidar pair without a reason key. |
| C4–C6 freshness and budgets | Literal cases bracket 5 s and 30 s age and 1 s future tolerance. Diagnostic cases anchor inject/clear execution at 10 s and exercise lifecycle and correlation. | Preserve freshness behavior and review the defaults separately from measured budgets. The 2 s native request and provider acceptance limits and 30 s managed restart limit need real deadline evidence. Mock timeout is a controlled result. |

See [C1–C7](v2-interface-contracts.md), [fixture coverage](../tests/fixtures/v2/README.md)
and [offline commands](v2-independent-development.md).

## Proposed live companion binding for review

Use the existing C5 topic `sdv/{vehicleId}/v2/observations` with the C2 envelope,
QoS 1, retain false and the 64 KiB wire limit. Use one adapter publisher and one
health consumer per vehicle. Configure the same vehicle ID, topic, session
registry and per-vehicle KUKSA endpoint on both sides. Configure the MQTT
endpoint, distinct client IDs, local credential references and TLS for
authenticated cross-host traffic. Grant the adapter publish and the health app
subscribe only on that vehicle's observation topic. Bayan's health output uses
its separate C5 health topic.

Validate the observation before side effects. Serialize each vehicle's writes.
Build the KUKSA LiDAR update and companion from the same validated object.
The update carries original source UTC in supported broker sample metadata.
Publish the companion only after successful KUKSA acknowledgement for all
required writes. For unavailable input, write false validity and publish the
original unavailable envelope. Any earlier cached distance is invalid under
false validity. The envelope preserves vehicle/session/generation/sequence/frame/
sourceTimestamp/eventId and the exact distance/validity for that acknowledged
write. The envelope is the health app's fresh LiDAR input. The broker sample
can be correlated by per-vehicle broker, source UTC and corresponding values,
with the full identity carried in the envelope. A newer broker write may
already have replaced the value when MQTT delivers the earlier observation.
Review must verify broker timestamp support and acknowledgement behavior on
the selected broker/SDK before enabling this binding. Cross-system atomicity
is unavailable. A write failure emits no companion. A successful write with
failed MQTT delivery leaves a gap detectable by the consumer.

Apply the C2/C5 validation and persisted per-vehicle ordering rules. Ignore
exact retries and reject conflicting or retired identities before updating
health or receipt timers. Use clean MQTT sessions with no offline backlog.
Reconnect and resubscribe to the configured topic, retaining the persisted
ordering watermark and registered session. Discard queued disconnected samples.
Allow QoS retransmission of the same valid in-flight envelope without changing
its identity/time. Losing the receipt clock across a process restart resets
the recovery window. A source UTC gap or monotonic receipt gap greater than
0.5 s resets recovery. A local timer marks silence without a new envelope or
source timestamp. Enforce freshness on delivery independently of receipt
interval. Disconnect, broker cache reads and rejected deliveries cannot refresh
source age or count toward recovery.

Ankit and Bayan review registry provisioning, topic ACLs, broker metadata and
reconnect behavior. Emmanuel reviews source cadence, episode rollover and
clock mapping. Record decisions before dependent production integration under
C7. Review proof should include equal-value successive samples with distinct
identities, unsuccessful writes, duplicates, disconnect/reconnect, a retired
session, unaffected peers and silence at either side of 0.5 s.

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
