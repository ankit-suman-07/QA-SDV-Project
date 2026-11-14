# PR #33 — E1 two-vehicle edge merge-readiness review

| PR | Reviewed SHA | CI/tests | Verdict |
|---|---|---|---|
| [#33](https://github.com/ankit-suman-07/QA-SDV-Project/pull/33) | `c5dcbe796365dd8c4444786dce5bc3e6eb44fd97` | 6/6 CI checks green; 449 local tests passed; live QoS incompatibility reproduced | **CHANGES REQUIRED** |

Current main reviewed: `80a781fef519bfe66a2086866598737440e4bcbf`.

All source line numbers below refer to the exact reviewed PR head unless otherwise stated. Results describe the completed review, not a new verification run performed when this report was saved.

## Scope and authoritative requirements

The review covered Phase V1 and E1's actual scope. It consulted the current `docs/SOURCE-OF-TRUTH.md`, relevant scope/task/architecture and contribution specifications, `docs/v1-interface-contracts.md`, `docs/v1-independent-development.md`, E1 design/plan and evidence, and the merged ingress/backend interfaces. No applicable AGENTS.md was found. Repository verification-before-completion and systematic-debugging instructions were consulted.

The PR description, complete changed-file diff, discussion/review endpoints, and exact-head Actions results were inspected. GitHub returned no comments or reviews. The head and base SHAs were unchanged at the final metadata refresh.

## Confirmed finding

### PR33-F01 — P1: Both vehicles' V1 publications are rejected by the merged ingress

**Location:** `velocitas-app/app/src/main.py:170`; pending state is cleared at line 183. Consumer boundary: `ditto/mqtt_subscriber.py:140`.

The actual publication path is:

1. `publish_v1()` calls the pinned SDK's `pubsub_client.publish_event(topic, data)`.
2. Velocitas SDK **0.15.7**, `velocitas_sdk/native/mqtt.py:92`, calls Paho's `publish(topic, data)` without QoS or retain arguments.
3. Paho defaults to **QoS 0, retain=false**.
4. Main's `ditto/mqtt_subscriber.py:140` rejects any delivery whose QoS is not 1.

This was reproduced using real Mosquitto and two real KUKSA 0.7.0 brokers, executing the PR's exact publication method with the pinned SDK:

- Both vehicle topics arrived with **QoS 0**.
- The real ingress logged `INVALID_MQTT_DELIVERY` for both.
- The mock twin writer received **zero persistence calls**.
- Both publisher gates nevertheless cleared their pending events.
- A QoS 1 positive control through the same broker reached persistence.

**Impact:** E1 publications cannot update either individual twin through the implementation already merged into main. Subscribing at QoS 1 cannot upgrade a QoS 0 publication.

**Smallest practical correction:** add a V1 publication adapter that explicitly calls Paho with `qos=1, retain=False`, retaining the existing legacy publication behavior. The SDK's public method does **not** accept a QoS argument; simply adding one to the current call will not work. Handle failed publication/acknowledgement without losing the pending event's ID and source timestamp, and add an actual transport-to-ingress regression.

C3 still requires QoS 1. No recorded approved contract change permitting QoS 0 was found. The implementation plan's “where the SDK allows it” qualification does not override the shared contract.

No other confirmed runtime blocker was found.

## Compatibility with current main

- Bayan's **#30, #31 and #32 are all merged**. Ankit's A2/A3/A5 implementations are also present.
- #33 includes current main as an ancestor. Git's merge calculation succeeds; there are **no current merge conflicts**.
- `evidence/v1/skill-sources.md` preserves **both E1 and A5 records**.
- Compose defines exactly **two vehicle edges**, each with its own provider, KUKSA broker and application, sharing one MQTT broker. Vehicle IDs, internal DNS names and default ports agree.
- The separate `qa-sdv-v1` project avoids container-name/project interference. Its default KUKSA port 55556 still overlaps the baseline deployment; simultaneous operation requires port overrides, as documented.
- C4 classification, ordinary C3 payload fields, UUID event IDs and strictly newer observation gating pass their tests.
- No individual-twin writer or fleet writer was introduced. Ownership remains Bayan for individual ingress/twins and Ankit for fleet aggregation/materialization.
- Optional action/trace context is omitted. This E1 implementation does not establish E2 command correlation or fault/recovery completion.

The shared contract remains marked **proposed for affected-owner review**, and #33 has no recorded GitHub reviews or approvals. Bayan must review the publisher/ingress boundary; Ankit must review the provider mapping and integration handoff.

## Observation time and restart delay

`sourceTimestamp` comes from KUKSA datapoints, not the application's polling or publication clock. The live probe confirmed that KUKSA 0.7.0 replaces a supplied historical timestamp with broker time. For this synchronous synthetic provider, that is a documented observation-time approximation; it does not prove preservation of arbitrary upstream acquisition timestamps.

At `velocitas-app/app/src/v1_event.py:153`, the first valid observation primes the gate without publication. Repeated readings do not generate new events, and older readings are suppressed.

**The restart delay is not itself a demonstrated C5 violation.** C5 classifies availability using source age; it does not require immediate publication after startup. Waiting for a new observation can legitimately leave the vehicle stale or unavailable temporarily.

However, “up to five seconds” is not a strict restart-to-event bound: the default two-second application poll can add latency after the next five-second provider update, with additional startup/reconnect time possible. Measure the complete restart timeline and verify truthful availability rather than treating five seconds as a guaranteed recovery deadline.

## Verification and evidence assessment

| Check | Result |
|---|---|
| Full Python suite, Python 3.12.16 with pinned dependencies and generated Protobuf | **449 passed**, 385 subtests; **9 integration tests deselected** |
| Focused E1 event/gate/reconnect and Compose tests | **40 passed**, including all four Compose tests |
| V1 Compose configuration | Passed |
| Recorded 24-event capture revalidation | 24 valid events; 12 per vehicle; 24 unique IDs; all HEALTHY |
| Live publication boundary | Confirmed QoS 0 rejection; QoS 1 control accepted |
| Diff whitespace | Passed |

Representative commands run in the isolated PR worktree:

```bash
python -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated \
  uprotocol/proto/common.proto uprotocol/proto/health_status.proto \
  uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto \
  uprotocol/proto/vehicle_diagnostic.proto
python -B -m pytest -q -ra -p no:cacheprovider -m 'not integration'
python -B -m pytest -q -ra -p no:cacheprovider \
  velocitas-app/app/tests/test_v1_event.py \
  velocitas-app/app/tests/test_v1_gate.py \
  velocitas-app/app/tests/test_kuksa_reconnect.py tests/test_v1_edge_compose.py
docker compose -f vehicle-simulator/docker-compose.v1.yml config --quiet
git diff --check origin/main...HEAD
```

Both [CI](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43547359190) and [synthetic integration](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43547359201) report success for the **exact reviewed SHA**. The integration workflow verifies the existing baseline, not complete two-vehicle ingress acceptance.

The capture supports payload validity and two independent streams during its observation window. It records no MQTT QoS metadata, so it cannot establish C3 transport compliance. `cycleComplete:false` correctly reflects that no E2 fault/recovery cycle occurred.

The provider-stop isolation and baseline-demo results are documented historical observations; their raw logs are not attached alongside the capture. Also, `evidence/v1/E1-two-vehicle-edge.md:8` says application code is unchanged since `a0b8e05`, but subsequent commits changed reconnect and gate/logging code. Update that provenance statement and distinguish historical live checks from later unit-tested changes.

### Live review check and limitations

The live check used actual KUKSA/MQTT, the extracted unchanged publication method and SDK, real ingress, and a **mock twin writer**. It did not launch the complete application images or verify real Ditto/API behavior. Java 21 backend verification was observed in CI, not rerun locally.

Review services used project `qa-sdv-review33`, MQTT host port 28883 and KUKSA host ports 56556/56557. Only the review MQTT and two KUKSA services were started. Temporary review containers and their network were removed after verification.

Observed boundary output:

```text
event_rejected code=INVALID_MQTT_DELIVERY topic='sdv/vehicle-001/health'
event_rejected code=INVALID_MQTT_DELIVERY topic='sdv/vehicle-002/health'
LIVE SDK/PR33 publication: both vehicle topics delivered at QoS 0
REAL ingress boundary: persist calls=0; publisher gates cleared=True
POSITIVE QoS1 control: persist calls=1
```

## Remaining corrections and live checks

1. Fix QoS 1 publication and add a regression proving delivery reaches the merged ingress.
2. Verify publication failure, broker disconnect/reconnect and retry identity with the corrected transport.
3. Rerun both complete edge applications; capture QoS/retain metadata, identity, ordering and source timestamps.
4. Repeat source-silence, provider restart and application restart checks while observing A2 availability and vehicle-001 isolation.
5. Correct evidence provenance and obtain Bayan/Ankit's affected-boundary approvals.
6. Keep E2 fault/recovery and real Ditto/API/fleet acceptance separately pending.

## Merge recommendation and integrity

**Do not merge #33 yet.** The confirmed QoS mismatch blocks its intended handoff to current main despite green CI. Re-review the corrected head and rerun its checks before merging.

The review did not change project source, commit, push, merge, or post GitHub content. This report was subsequently saved in `docs/findings` at the user's explicit request; saving it did not rerun the review or refresh remote state.
