"""Offline tests against the existing Ditto HTTP resource fake."""

from copy import deepcopy
import json

import pytest
import requests

from ditto.c5_ditto_store import C5HealthStore
from ditto.c5_fingerprint import fingerprint_envelope
from ditto.mqtt_ingress import EventError, WatermarkError, encode_json
from ditto.v1_writer import DittoConfig, DittoError
from test_v2_ditto_writer import DittoHTTP, FEATURE_PATH, PROPERTIES_PATH, TARGET, TOPIC, event_at


def store(http, **overrides):
    options = dict(initial_sessions={v: "session-1" for v in http.twins},
                   max_observations=3, request=http)
    return C5HealthStore(DittoConfig("http://ditto.invalid", "fixture", "fixture"), **(options | overrides))


def send(writer, sequence=0, **changes):
    return writer.persist_health(TOPIC, json.dumps(event_at(sequence, **changes)).encode())


def saved(http, vehicle=TARGET):
    return http.twins[vehicle]["features"]["v2"]["properties"]


def test_conditional_create_and_update_commit_projection_and_metadata_together():
    http = DittoHTTP()
    original = deepcopy(http.twins)
    writer = store(http)
    for sequence in (0, 1):
        event = event_at(sequence)
        raw = json.dumps(event).encode()
        result = writer.persist_health(TOPIC, raw)
        assert result == fingerprint_envelope(TOPIC, raw)
        assert json.loads(raw) == event == result.envelope
        props = saved(http)
        assert props["lastEventId"] == props["_ingress"]["latest"]["eventId"] == event["eventId"]
        assert props["_ingress"]["latest"]["fingerprint"] == result.sha256
        assert props["_ingress"]["observationCount"] == sequence + 1
        assert {k: v for k, v in props.items() if k not in {"_ingress", "lastEventId"}} == {
            k: v for k, v in event.items() if k != "eventId"
        }
    writes = [(path, headers) for method, path, headers in http.calls if method == "PUT"]
    assert [path for path, _ in writes] == [FEATURE_PATH, PROPERTIES_PATH]
    assert writes[0][1]["If-None-Match"] == "*"
    assert writes[1][1]["If-Match"] == '"feature-revision-1"'
    actual = deepcopy(http.twins)
    actual[TARGET]["features"].pop("v2")
    assert actual == original


def test_restart_exact_retry_uses_original_digest_after_status_overlay():
    http = DittoHTTP()
    original = send(store(http), health="CRITICAL", faults=["LIDAR_OBSTRUCTION"],
                    recoveryState="IN_PROGRESS", recoveryStartedAt=event_at(0)["sourceTimestamp"])
    projected = deepcopy(saved(http))
    projected.update(sourceSilent=True, recoveryState="NONE", recoveryStartedAt=None)
    http.store(TARGET, projected)
    restarted = store(http)
    assert restarted.persist_health(TOPIC, json.dumps(original.envelope).encode()) == original
    assert len(http.put_headers()) == 1
    assert saved(http) == projected


@pytest.mark.parametrize("historical", [False, True])
def test_restart_rejects_conflicting_event_id(historical):
    http = DittoHTTP()
    first = send(store(http))
    if historical:
        send(store(http), 1)
    before = deepcopy(saved(http))
    writes = len(http.put_headers())
    with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
        send(store(http), 2, eventId=first.envelope["eventId"])
    assert saved(http) == before and len(http.put_headers()) == writes


def test_412_reloads_and_retries_conditionally():
    http = DittoHTTP()
    send(store(http))
    http.before_put.append(lambda: 412)
    result = send(store(http), 1)
    assert saved(http)["_ingress"]["latest"]["fingerprint"] == result.sha256
    assert len(http.put_headers()) == 3
    assert [method for method, _, _ in http.calls][-6:] == ["GET", "GET", "PUT", "GET", "GET", "PUT"]


@pytest.mark.parametrize("same_content", [True, False])
def test_concurrent_creator_requires_authoritative_reconciliation(same_content):
    http = DittoHTTP()
    competing = store(http)
    changes = {} if same_content else {"simulationSeconds": 51}
    http.before_put.append(lambda: (send(competing, **changes), 412)[1])
    if same_content:
        assert send(store(http)) == fingerprint_envelope(TOPIC, json.dumps(event_at(0)).encode())
    else:
        with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
            send(store(http))
    assert saved(http)["simulationSeconds"] == event_at(0, **changes)["simulationSeconds"]
    assert len(http.put_headers()) == 2


def test_412_exhaustion_never_reports_acceptance():
    http = DittoHTTP()
    http.before_put.extend([lambda: 412] * 2)
    with pytest.raises(DittoError, match="^DITTO_CONCURRENT_UPDATE status=412$"):
        send(store(http))
    assert len(http.put_headers()) == 2
    assert "v2" not in http.twins[TARGET]["features"]


@pytest.mark.parametrize("committed", [False, True])
def test_timeout_requires_durable_confirmation(committed):
    http = DittoHTTP()

    def timeout():
        raise requests.Timeout("simulated timeout")

    if committed:
        http.lose_reply = True
        result = send(store(http))
        assert saved(http)["_ingress"]["latest"]["fingerprint"] == result.sha256
    else:
        http.before_put.append(timeout)
        with pytest.raises(DittoError, match="^C5_WRITE_UNRESOLVED$"):
            send(store(http))
        assert "v2" not in http.twins[TARGET]["features"]
    assert len(http.put_headers()) == 1


def test_capacity_preserves_membership_and_exact_retry():
    http = DittoHTTP()
    writer = store(http, max_observations=1)
    first = send(writer)
    before = deepcopy(saved(http))
    with pytest.raises(WatermarkError, match="^C5_REPLAY_CAPACITY$"):
        send(writer, 1)
    assert send(writer) == first
    assert len(http.put_headers()) == 1 and saved(http) == before


def test_legacy_v2_feature_never_initializes_a_new_ledger():
    http = DittoHTTP()
    http.store(TARGET, {"lastEventId": "legacy"})
    with pytest.raises(DittoError, match="^C5_LEGACY_STATE$"):
        send(store(http))
    assert http.put_headers() == [] and saved(http) == {"lastEventId": "legacy"}


@pytest.mark.parametrize("mutation", [
    lambda p: p["_ingress"].update(version=2),
    lambda p: p["_ingress"]["observationIds"].clear(),
    lambda p: p.update(sequence=9),
])
def test_invalid_persisted_state_fails_closed(mutation):
    http = DittoHTTP()
    send(store(http))
    mutation(saved(http))
    before = deepcopy(saved(http))
    with pytest.raises(WatermarkError, match="^(INVALID_C5_REPLAY_STATE|INVALID_PERSISTED_STATE)$"):
        send(store(http), 1)
    assert saved(http) == before and len(http.put_headers()) == 1


def test_unverified_session_and_successor_are_rejected():
    http = DittoHTTP()
    with pytest.raises(EventError, match="^UNREGISTERED_SESSION$"):
        send(store(http), sessionId="publisher-selected")
    with pytest.raises(EventError, match="^UNREGISTERED_SESSION$"):
        send(store(http), sessionId="session-2", sessionGeneration=2)
    assert http.put_headers() == []


def test_definite_persistence_error_never_reports_acceptance():
    http = DittoHTTP()
    http.before_put.append(lambda: 403)
    with pytest.raises(DittoError, match="^DITTO_AUTH_FAILURE status=403$"):
        send(store(http))
    assert "v2" not in http.twins[TARGET]["features"]


@pytest.mark.parametrize("extra", [0, 1])
def test_complete_metadata_byte_budget_exact_boundary(extra):
    probe = DittoHTTP()
    send(store(probe), eventId="observation-?")
    size = len(encode_json(saved(probe)["_ingress"]))
    http = DittoHTTP()
    writer = store(http, max_metadata_bytes=size - extra)
    before = deepcopy(http.twins)
    if extra:
        with pytest.raises(WatermarkError, match="^C5_REPLAY_CAPACITY$"):
            send(writer, eventId="observation-?")
        assert http.twins == before and http.put_headers() == []
    else:
        first = send(writer, eventId="observation-?")
        assert len(encode_json(saved(http)["_ingress"])) == size
        assert send(writer, eventId="observation-?") == first
        assert len(http.put_headers()) == 1
        assert all(http.twins[v] == before[v] for v in before if v != TARGET)


def test_412_reloads_concurrent_membership_before_checking_metadata_budget():
    probe = DittoHTTP()
    send(store(probe), 1)
    limit = len(encode_json(saved(probe)["_ingress"]))
    http = DittoHTTP()
    competing = store(http)
    http.before_put.append(lambda: (send(competing), 412)[1])
    writer = store(http, max_metadata_bytes=limit)
    with pytest.raises(WatermarkError, match="^C5_REPLAY_CAPACITY$"):
        send(writer, 1)
    assert len(http.put_headers()) == 2  # Failed create and winning create only.
    assert saved(http)["_ingress"]["observationCount"] == 1
    assert send(writer).envelope["eventId"] == event_at(0)["eventId"]
    assert len(http.put_headers()) == 2


def test_properties_precondition_does_not_guard_unrelated_thing_growth():
    http = DittoHTTP()
    send(store(http))
    revision = http.etag(TARGET)
    attributes = http.twins[TARGET]["attributes"]

    def grow_unrelated_attribute():
        attributes["concurrentGrowth"] = "x" * 1024
        assert http.etag(TARGET) == revision

    http.before_put.append(grow_unrelated_attribute)
    send(store(http), 1)
    assert http.put_headers()[-1]["If-Match"] == revision
    assert len(attributes["concurrentGrowth"]) == 1024
