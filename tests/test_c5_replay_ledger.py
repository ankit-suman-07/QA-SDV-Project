import json
from copy import deepcopy

import pytest

from ditto.c5_fingerprint import fingerprint_envelope
from ditto.c5_replay_ledger import load_ledger, new_ledger, record_observation
from ditto.mqtt_ingress import EventError, WatermarkError, decode_v2_health, encode_json


VEHICLE = "vehicle-003"


def observation(sequence=0, *, vehicle=VEHICLE, generation=1, **changes):
    event = {
        "schemaVersion": "2.0.0", "vehicleId": vehicle,
        "sessionId": f"session-{generation}", "sessionGeneration": generation,
        "eventId": f"{vehicle}-s{generation}-{sequence}", "sequence": sequence,
        "frame": sequence, "simulationSeconds": sequence, "provenance": "SYNTHETIC",
        "sourceTimestamp": f"2026-01-01T00:00:00.{sequence:03d}Z",
        "processingTimestamp": "2026-01-01T00:00:01Z",
        "lidar": {"sensorAvailable": True, "distanceMeters": 20},
        "health": "CRITICAL", "faults": ["LIDAR_SENSOR_FAILURE"],
        "recoveryState": "IN_PROGRESS", "recoveryStartedAt": "2026-01-01T00:00:00Z",
        "sourceSilent": False,
    }
    event.update(changes)
    return fingerprint_envelope(f"sdv/{vehicle}/v2/health", json.dumps(event).encode())


def record(ledger, candidate, **limits):
    return record_observation(ledger, candidate, **({"max_observations": 3} | limits))


def reload(ledger):
    return load_ledger(json.loads(json.dumps(ledger)))


def test_first_observation_records_identity_and_fingerprint_without_mutation():
    ledger = new_ledger(VEHICLE, "session-1", 1)
    candidate = observation()
    before = deepcopy((ledger, candidate))
    saved = record(ledger, candidate)
    assert saved["observationCount"] == 1
    assert saved["latest"]["fingerprint"] == candidate.sha256
    assert saved["latest"]["eventId"] == candidate.envelope["eventId"]
    assert saved["latest"]["sourceTimestamp"] == candidate.envelope["sourceTimestamp"]
    assert saved["latest"]["sequence"] == 0 and saved["latest"]["frame"] == 0
    assert (ledger, candidate) == before


def test_exact_retry_is_a_noop_at_capacity_after_reload():
    candidate = observation()
    saved = reload(record(new_ledger(VEHICLE, "session-1", 1), candidate))
    assert record(saved, candidate, max_observations=1) is None


@pytest.mark.parametrize("historical", [False, True])
def test_conflicting_id_cannot_be_reused_after_reload(historical):
    first = observation()
    saved = record(new_ledger(VEHICLE, "session-1", 1), first)
    if historical:
        saved = record(saved, observation(1))
    saved = reload(saved)
    candidate = observation(2, eventId=first.envelope["eventId"])
    with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
        record(saved, candidate)


def test_stale_distinct_observation_cannot_advance_watermark():
    saved = record(new_ledger(VEHICLE, "session-1", 1), observation(1))
    with pytest.raises(EventError, match="^OUT_OF_ORDER$"):
        record(saved, observation())


def pending_successor():
    # Model an already persisted cutover snapshot. The ledger has no API
    # for granting authorization or applying a control-plane decision.
    prior = record(new_ledger(VEHICLE, "session-1", 1), observation(1))
    return reload(dict(prior, sessionId="session-2", sessionGeneration=2,
                       transitionId="transition-2", pendingSuccessor=True,
                       observationIds={}, observationCount=0))


def test_unregistered_successor_is_rejected():
    ledger = new_ledger(VEHICLE, "session-1", 1)
    with pytest.raises(EventError, match="^UNREGISTERED_SESSION$"):
        record(ledger, observation(generation=2))


def test_fence_rejects_retired_exact_retry_while_successor_is_pending():
    ledger = pending_successor()
    with pytest.raises(EventError, match="^OUT_OF_ORDER$"):
        record(ledger, observation(1))


def test_pending_successor_preserves_predecessor_until_strictly_newer_source():
    ledger = pending_successor()
    before = deepcopy(ledger)
    with pytest.raises(EventError, match="^OUT_OF_ORDER$"):
        record(ledger, observation(1, generation=2))
    accepted = record(ledger, observation(2, generation=2))
    assert ledger == before
    assert not accepted["pendingSuccessor"]
    assert accepted["transitionId"] == "transition-2"
    assert accepted["latest"]["sessionGeneration"] == 2
    assert accepted["observationCount"] == 1
    with pytest.raises(EventError, match="^OUT_OF_ORDER$"):
        record(reload(accepted), observation(1))


@pytest.mark.parametrize("change", [
    {"version": True}, {"sessionGeneration": True},
    {"observationIds": {}}, {"observationCount": False},
    {"observationIds": {"bad-hash": True}}, {"latest": None},
    {"pendingSuccessor": True}, {"unexpected": "field"},
])
def test_reload_rejects_malformed_or_incomplete_state(change):
    saved = record(new_ledger(VEHICLE, "session-1", 1), observation())
    with pytest.raises(WatermarkError, match="^INVALID_C5_REPLAY_STATE$"):
        load_ledger(dict(saved, **change))


def test_reload_rejects_invalid_latest_timestamp():
    saved = record(new_ledger(VEHICLE, "session-1", 1), observation())
    saved["latest"]["sourceTimestamp"] = "invalid"
    with pytest.raises(WatermarkError, match="^INVALID_C5_REPLAY_STATE$"):
        load_ledger(saved)


@pytest.mark.parametrize("limits", [{"max_observations": 1}, {"max_membership_bytes": 73}])
def test_capacity_rejection_never_evicts_or_mutates(limits):
    accepted = record(new_ledger(VEHICLE, "session-1", 1), observation())
    before = deepcopy(accepted)
    with pytest.raises(WatermarkError, match="^C5_REPLAY_CAPACITY$"):
        record(accepted, observation(1), **limits)
    assert accepted == before
    assert record(accepted, observation(), **limits) is None


def test_three_vehicles_are_isolated():
    vehicles = ["vehicle-001", "vehicle-002", "vehicle-003"]
    states = {v: new_ledger(v, "session-1", 1) for v in vehicles}
    events = {v: observation(vehicle=v, eventId="shared-id") for v in vehicles}
    for v in vehicles:
        accepted = record(states[v], events[v])
        for other in set(vehicles) - {v}:
            with pytest.raises(EventError, match="^TOPIC_MISMATCH$"):
                record(accepted, events[other])
            assert states[other]["observationCount"] == 0
        assert accepted["observationCount"] == 1


def test_status_overlay_does_not_replace_original_health_fingerprint():
    original = observation()
    saved = record(new_ledger(VEHICLE, "session-1", 1), original)
    projection = deepcopy(original.envelope)
    projection.update(recoveryState="NONE", recoveryStartedAt=None, sourceSilent=True)
    modified = fingerprint_envelope(f"sdv/{VEHICLE}/v2/health", json.dumps(projection).encode())
    assert modified.sha256 != original.sha256
    assert reload(saved)["latest"]["fingerprint"] == original.sha256
    assert record(reload(saved), original) is None
    with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
        record(reload(saved), modified)


def test_reload_returns_independent_state():
    saved = record(new_ledger(VEHICLE, "session-1", 1), observation())
    detached = load_ledger(saved)
    detached["latest"]["frame"] = 10
    detached["observationIds"].clear()
    assert saved["latest"]["frame"] == 0
    assert len(saved["observationIds"]) == 1


@pytest.mark.parametrize(("sequence", "frame"), [(0, 0), (0, 1), (1, 0)])
def test_reload_rejects_history_larger_than_ordering_watermark(sequence, frame):
    from hashlib import sha256

    saved = record(new_ledger(VEHICLE, "session-1", 1), observation(sequence, frame=frame))
    saved["observationIds"][sha256(b"impossible-predecessor").hexdigest()] = True
    saved["observationCount"] = 2
    with pytest.raises(WatermarkError, match="^INVALID_C5_REPLAY_STATE$"):
        reload(saved)


def test_reload_accepts_initial_multi_observation_and_pending_states():
    initial = new_ledger(VEHICLE, "session-1", 1)
    saved = record(record(initial, observation()), observation(1))
    assert reload(initial) == initial
    assert reload(saved) == saved
    pending = pending_successor()
    assert reload(pending) == pending
    assert record(reload(saved), observation(1)) is None


@pytest.mark.parametrize("latest", [True, False])
def test_modified_envelope_cannot_reuse_stale_fingerprint(latest):
    original = observation()
    saved = record(new_ledger(VEHICLE, "session-1", 1), original)
    candidate = original if latest else observation(1)
    candidate.envelope["lidar"]["distanceMeters"] = 21
    before = deepcopy((saved, candidate))
    expected = "EVENT_ID_CONFLICT" if latest else "INVALID_TYPE"
    with pytest.raises(EventError, match=f"^{expected}$"):
        record(reload(saved), candidate)
    assert (saved, candidate) == before
    assert record(saved, observation()) is None


@pytest.mark.parametrize("candidate", [None, {}, {"envelope": {}}, []])
def test_invalid_candidate_type_raises_controlled_error(candidate):
    with pytest.raises(EventError, match="^INVALID_TYPE$"):
        record(new_ledger(VEHICLE, "session-1", 1), candidate)


@pytest.mark.parametrize("envelope", [None, [], {"vehicleId": VEHICLE}, {
    "vehicleId": VEHICLE, "lidar": {"distanceMeters": object()},
}])
def test_invalid_fingerprint_envelope_mapping_raises_controlled_error(envelope):
    from dataclasses import replace

    candidate = replace(observation(), envelope=envelope)
    with pytest.raises(EventError):
        record(new_ledger(VEHICLE, "session-1", 1), candidate)


def test_invalid_nested_application_value_cannot_be_coerced_to_json():
    original = observation()
    original.envelope["faults"] = tuple(original.envelope["faults"])
    with pytest.raises(EventError, match="^MALFORMED_JSON$"):
        record(new_ledger(VEHICLE, "session-1", 1), original)


def test_wire_limit_applies_before_revalidation_of_decoded_envelope():
    topic = f"sdv/{VEHICLE}/v2/health"
    event = observation(eventId="x").envelope

    def scientific_wire():
        return encode_json(event).replace(b'"simulationSeconds":0', b'"simulationSeconds":1e9')

    event["eventId"] += "x" * (65536 - len(scientific_wire()))
    raw = scientific_wire()
    assert len(raw) == 65536 and b'"simulationSeconds":1e9' in raw
    candidate = fingerprint_envelope(topic, raw)
    assert decode_v2_health(topic, raw) == candidate.envelope
    assert len(encode_json(candidate.envelope)) == 65545
    oversized = raw + b" "
    assert len(oversized) == 65537
    with pytest.raises(EventError, match="^MALFORMED_JSON$"):
        decode_v2_health(topic, oversized)

    initial = new_ledger(VEHICLE, "session-1", 1)
    before = deepcopy((initial, candidate))
    saved = record(initial, candidate, max_observations=1)
    assert saved["latest"]["fingerprint"] == candidate.sha256
    assert record(reload(saved), candidate, max_observations=1) is None
    assert (initial, candidate) == before
