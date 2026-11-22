"""Offline C5 regressions through the production ingress and HTTP writer."""

from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import requests

from ditto.mqtt_ingress import EventError, Ingress
from ditto.v1_writer import DittoConfig, DittoError, DittoWriter


FIXTURES = Path(__file__).parent / "fixtures" / "v2"
VEHICLES = ("vehicle-001", "vehicle-002", "vehicle-003")
TARGET = "vehicle-003"
TOPIC = f"sdv/{TARGET}/v2/health"
THING_PATH = f"/api/2/things/sdv:{TARGET}"
FEATURE_PATH = f"{THING_PATH}/features/v2"
PROPERTIES_PATH = f"{FEATURE_PATH}/properties"


def fixture(kind, vehicle):
    value = json.loads((FIXTURES / kind / f"{vehicle}.json").read_text(encoding="utf-8"))
    value.pop("fixtureLabel")
    return value


def properties(event):
    value = deepcopy(event)
    value["lastEventId"] = value.pop("eventId")
    return value


def event_at(sequence, **changes):
    event = fixture("health-events", TARGET)
    offset = timedelta(milliseconds=sequence)
    for field in ("sourceTimestamp", "processingTimestamp"):
        event[field] = (datetime.fromisoformat(event[field]) + offset).isoformat()
    event.update(eventId=f"{event['eventId']}-{sequence}", sequence=sequence,
                 frame=event["frame"] + sequence,
                 simulationSeconds=event["simulationSeconds"] + offset.total_seconds())
    return dict(event, **changes)


def write_properties(path, data):
    payload = json.loads(data)
    assert isinstance(payload, dict)
    if path.endswith("/features/v2"):
        assert set(payload) == {"properties"}
        payload = payload["properties"]
        assert isinstance(payload, dict)
    else:
        assert path.endswith("/features/v2/properties")
    return payload


class DittoHTTP:
    """Model HTTP resources and version preconditions, leaving ordering to production."""

    def __init__(self):
        self.twins = {v: fixture("twins", v) for v in VEHICLES}
        for twin in self.twins.values():
            twin["features"]["v2"]["properties"].pop("fixtureLabel")
        features = self.twins[TARGET]["features"]
        features.pop("v2")
        features["v1"] = {"properties": {"lastEventId": "legacy-event"}}
        features["signals"] = {"properties": {"speedKph": 12}}
        self.twins[TARGET]["attributes"]["fixtureAttribute"] = "preserve"
        self.revisions = dict.fromkeys(VEHICLES, 0)
        self.calls = []
        self.before_put = deque()
        self.lose_reply = False

    def etag(self, vehicle):
        return f'"feature-revision-{self.revisions[vehicle]}"'

    def store(self, vehicle, value):
        feature = self.twins[vehicle]["features"].setdefault("v2", {})
        feature["properties"] = deepcopy(value)
        self.revisions[vehicle] += 1

    def __call__(self, method, url, *, headers, data=None, **kwargs):
        path = urlsplit(url).path
        _, api, version, collection, thing_id, *tail = path.split("/")
        assert (api, version, collection) == ("api", "2", "things")
        vehicle = thing_id.removeprefix("sdv:")
        assert thing_id == self.twins[vehicle]["thingId"]
        self.calls.append((method, path, dict(headers)))
        feature = self.twins[vehicle]["features"].get("v2")
        if method == "GET":
            if not tail:
                return self.response(200, self.twins[vehicle], {"ETag": '"whole-thing"'})
            assert tail == ["features", "v2", "properties"]
            if feature is None:
                return self.response(404)
            return self.response(200, feature["properties"], {"ETag": self.etag(vehicle)})

        assert method == "PUT" and tail in (["features", "v2"], ["features", "v2", "properties"])
        creating = tail == ["features", "v2"]
        if creating:
            assert headers.get("If-None-Match") == "*" and "If-Match" not in headers
        if self.before_put:
            status = self.before_put.popleft()()
            if status is not None:
                return self.response(status)
        feature = self.twins[vehicle]["features"].get("v2")
        if creating:
            if feature is not None:
                return self.response(412)
        elif feature is None:
            return self.response(404, {"status": 404, "error": "things:feature.notfound"})
        elif "If-None-Match" in headers or headers.get("If-Match") != self.etag(vehicle):
            return self.response(412)
        self.store(vehicle, write_properties(path, data))
        if self.lose_reply:
            raise requests.Timeout("fixture: reply lost after commit")
        return self.response(201 if creating else 204)

    @staticmethod
    def response(status, value=None, headers=None):
        return SimpleNamespace(status_code=status, content=json.dumps(value).encode(),
                               headers=headers or {})

    def send(self, event, ingress=None):
        if ingress is None:
            config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
            ingress = Ingress(DittoWriter(config, request=self))
        return ingress.process(TOPIC, json.dumps(event))

    def put_headers(self):
        return [headers for method, path, headers in self.calls if method == "PUT"
                and path in (FEATURE_PATH, PROPERTIES_PATH)]


@pytest.fixture
def http():
    return DittoHTTP()


def test_conditional_create_and_update_preserve_legacy_and_other_twins(http):
    expected = deepcopy(http.twins)
    revisions = http.revisions.copy()
    for sequence in (0, 1):
        event = event_at(sequence)
        old_etag = http.etag(TARGET)
        assert http.send(event) == event
        headers = http.put_headers()[-1]
        if sequence == 0:
            assert headers["If-None-Match"] == "*"
        else:
            assert headers["If-Match"] == old_etag
        expected[TARGET]["features"]["v2"] = {"properties": properties(event)}
        revisions[TARGET] += 1
        assert http.twins == expected
        assert http.revisions == revisions
    assert all(path in {THING_PATH, FEATURE_PATH, PROPERTIES_PATH} for _, path, _ in http.calls)
    assert [path for method, path, _ in http.calls if method == "PUT"] == [
        FEATURE_PATH, PROPERTIES_PATH,
    ]
    assert len(http.put_headers()) == 2


@pytest.mark.parametrize("concurrent_sequence", [1, 3], ids=["still-eligible", "now-stale"])
def test_412_reloads_and_revalidates_against_concurrent_write(http, concurrent_sequence):
    http.send(event_at(0))
    http.calls.clear()
    concurrent = event_at(concurrent_sequence)
    candidate = event_at(2)
    old_etag = http.etag(TARGET)
    http.before_put.append(lambda: http.store(TARGET, properties(concurrent)))

    if concurrent_sequence < candidate["sequence"]:
        assert http.send(candidate) == candidate
        expected = candidate
        assert [h["If-Match"] for h in http.put_headers()] == [
            old_etag, '"feature-revision-2"',
        ]
    else:
        with pytest.raises(EventError, match="^OUT_OF_ORDER$"):
            http.send(candidate)
        expected = concurrent
        assert [h["If-Match"] for h in http.put_headers()] == [old_etag]

    first_put = next(i for i, call in enumerate(http.calls) if call[0] == "PUT")
    assert [(method, path) for method, path, _ in http.calls[first_put + 1:]][:2] == [
        ("GET", THING_PATH), ("GET", PROPERTIES_PATH),
    ]
    assert http.twins[TARGET]["features"]["v2"]["properties"] == properties(expected)


def test_412_exhaustion_never_advances_persisted_state(http):
    http.send(event_at(0))
    expected = deepcopy(http.twins), http.revisions.copy()
    http.calls.clear()
    http.before_put.extend((lambda: 412, lambda: 412))
    with pytest.raises(DittoError, match="^DITTO_CONCURRENT_UPDATE status=412$"):
        http.send(event_at(1))
    assert len(http.put_headers()) == 2
    assert (http.twins, http.revisions) == expected


def test_failed_write_and_lost_reply_are_reconciled_with_persisted_state(http):
    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=http))
    http.send(event_at(0), ingress)
    candidate = event_at(1)
    expected = deepcopy(http.twins), http.revisions.copy()

    http.before_put.append(lambda: 503)
    with pytest.raises(DittoError, match="^DITTO_UNAVAILABLE status=503$"):
        http.send(candidate, ingress)
    assert (http.twins, http.revisions) == expected

    http.lose_reply = True
    with pytest.raises(DittoError, match="^DITTO_TIMEOUT$"):
        http.send(candidate, ingress)
    assert http.twins[TARGET]["features"]["v2"]["properties"] == properties(candidate)
    retries = len(http.put_headers())
    assert http.send(candidate, ingress) == candidate
    assert len(http.put_headers()) == retries


def test_fresh_ingress_reloads_watermark_and_enforces_order_and_session(http):
    latest = event_at(2)
    http.send(latest)
    candidate = event_at(3)
    expected = deepcopy(http.twins), http.revisions.copy()
    for changes, code in (
        ({"sequence": latest["sequence"] - 1}, "OUT_OF_ORDER"),
        ({"frame": latest["frame"] - 1}, "OUT_OF_ORDER"),
        ({"sourceTimestamp": event_at(1)["sourceTimestamp"]}, "OUT_OF_ORDER"),
        ({"eventId": latest["eventId"]}, "EVENT_ID_CONFLICT"),
        ({"sessionGeneration": 2, "sessionId": "unregistered-successor"}, "UNREGISTERED_SESSION"),
    ):
        http.calls.clear()
        with pytest.raises(EventError, match=f"^{code}$"):
            http.send(dict(candidate, **changes))
        assert [(method, path) for method, path, _ in http.calls] == [("GET", THING_PATH)]
        assert (http.twins, http.revisions) == expected

    assert http.send(candidate) == candidate
    assert len(http.put_headers()) == 1
    assert http.twins[TARGET]["features"]["v2"]["properties"] == properties(candidate)


def test_absent_v2_feature_is_created_before_properties_updates(http):
    feature_path = f"{THING_PATH}/features/v2"
    writes = []

    def request(method, url, *, headers, data=None, **kwargs):
        path = urlsplit(url).path
        if method != "PUT":
            return http(method, url, headers=headers, data=data, **kwargs)

        payload = json.loads(data)
        writes.append((path, headers.get("If-None-Match"), headers.get("If-Match"), payload))
        features = http.twins[TARGET]["features"]
        if path == PROPERTIES_PATH and "v2" not in features:
            # Real Ditto 3.9.3 requires the parent feature for a properties PUT.
            return http.response(404, {"status": 404, "error": "things:feature.notfound"})
        if path == feature_path:
            assert headers.get("If-None-Match") == "*" and "If-Match" not in headers
            if "v2" in features:
                return http.response(412)
            assert set(payload) == {"properties"}
            http.store(TARGET, payload["properties"])
            return http.response(201, payload, {"ETag": '"feature-object-tag"'})

        assert path == PROPERTIES_PATH
        return http(method, url, headers=headers, data=data, **kwargs)

    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=request))
    expected = deepcopy(http.twins)
    assert "v2" not in expected[TARGET]["features"]
    assert "v1" in expected[TARGET]["features"] and "signals" in expected[TARGET]["features"]

    first = event_at(0)
    assert http.send(first, ingress) == first
    expected[TARGET]["features"]["v2"] = {"properties": properties(first)}
    assert http.twins == expected
    assert writes == [(feature_path, "*", None, {"properties": properties(first)})]

    second = event_at(1)
    properties_etag = http.etag(TARGET)
    assert http.send(second, ingress) == second
    expected[TARGET]["features"]["v2"]["properties"] = properties(second)
    assert http.twins == expected
    assert writes[1:] == [(PROPERTIES_PATH, None, properties_etag, properties(second))]
    assert ("GET", PROPERTIES_PATH) in [(method, path) for method, path, _ in http.calls]


def test_earlier_event_id_reuse_cannot_advance_v2_watermark(http):
    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=http))
    first, latest = event_at(0), event_at(1)
    assert http.send(first, ingress) == first
    assert http.send(latest, ingress) == latest
    assert http.twins[TARGET]["features"]["v2"]["properties"] == properties(latest)
    before = deepcopy(http.twins), http.revisions.copy()
    writes = http.put_headers()

    unregistered = event_at(2, sessionId="other-session", sessionGeneration=2)
    with pytest.raises(EventError, match="^UNREGISTERED_SESSION$"):
        http.send(unregistered, ingress)
    assert (http.twins, http.revisions) == before
    assert http.put_headers() == writes

    conflicting = event_at(2, eventId=first["eventId"])
    with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
        http.send(conflicting, ingress)
    assert http.put_headers() == writes
    assert (http.twins, http.revisions) == before


def test_v2_invalid_velocity_metadata_is_rejected_before_ditto_access(http):
    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=http))
    velocity = {"x": 1.25, "y": -2, "z": 0}
    valid = event_at(0, velocityMetersPerSecond=velocity)
    assert http.send(valid, ingress) == valid
    assert http.twins[TARGET]["features"]["v2"]["properties"] == properties(valid)
    before = deepcopy(http.twins), http.revisions.copy()
    http.calls.clear()

    invalid = event_at(1, velocityMetersPerSecond={**velocity, "x": "nonnumeric"})
    with pytest.raises(EventError, match="^INVALID_TYPE$"):
        http.send(invalid, ingress)
    assert http.calls == []
    assert (http.twins, http.revisions) == before


@pytest.mark.parametrize(
    ("silent", "started", "error"),
    [
        (True, "2026-01-01T00:00:00.001000001Z", "INVALID_TYPE"),
        (False, "2026-01-01T00:00:00.001000003Z", "INVALID_TIMESTAMP"),
    ],
    ids=["silent-while-recovering", "recovery-start-after-source"],
)
def test_invalid_v2_recovery_never_reaches_ditto(http, silent, started, error):
    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=http))
    first = event_at(0)
    assert http.send(first, ingress) == first
    before = deepcopy(http.twins), http.revisions.copy()
    replay_before = deepcopy(ingress._v2_replay)
    http.calls.clear()

    candidate = event_at(
        1, health="CRITICAL", faults=["LIDAR_OBSTRUCTION"],
        recoveryState="IN_PROGRESS", sourceSilent=silent, recoveryStartedAt=started,
        sourceTimestamp="2026-01-01T00:00:00.001000002+00:00",
    )
    with pytest.raises(EventError, match=f"^{error}$"):
        http.send(candidate, ingress)
    assert http.calls == []
    assert (http.twins, http.revisions) == before
    assert ingress._v2_replay == replay_before

    # Correcting only the recovery fields leaves the same ID eligible.
    corrected = dict(candidate, sourceSilent=False,
                     recoveryStartedAt=candidate["sourceTimestamp"])
    assert http.send(corrected, ingress) == corrected


@pytest.mark.parametrize(
    ("state", "silent", "started", "health", "faults"),
    [
        ("IN_PROGRESS", False, "2026-01-01T00:00:00.001000001Z",
         "CRITICAL", ["LIDAR_OBSTRUCTION"]),
        ("IN_PROGRESS", False, "2026-01-01T00:00:00.0010000020Z",
         "CRITICAL", ["LIDAR_OBSTRUCTION"]),
        ("NONE", True, None, "HEALTHY", []),
    ],
    ids=["earlier-fractional-start", "equal-fractional-start", "silent-without-recovery"],
)
def test_valid_v2_recovery_preserves_wire_timestamps(http, state, silent, started, health, faults):
    candidate = event_at(
        1, health=health, faults=faults, recoveryState=state,
        sourceSilent=silent, recoveryStartedAt=started,
        sourceTimestamp="2026-01-01T00:00:00.001000002+00:00",
    )
    expected = deepcopy(http.twins)
    assert http.send(candidate) == candidate
    expected[TARGET]["features"]["v2"] = {"properties": properties(candidate)}
    assert http.twins == expected


def recovery_fields(distance, health="CRITICAL", fault="LIDAR_OBSTRUCTION"):
    return {
        "lidar": {"distanceMeters": distance, "sensorAvailable": True},
        "health": health,
        "faults": [fault],
        "recoveryState": "IN_PROGRESS",
        "recoveryStartedAt": event_at(0)["sourceTimestamp"],
    }


@pytest.mark.parametrize(
    "changes",
    [
        recovery_fields(3),
        recovery_fields(10),
        recovery_fields(20, health="WARNING", fault="LIDAR_SENSOR_FAILURE"),
        {"actionId": "fixture-action"},
        {"traceId": "fixture-trace"},
        {"simulationSeconds": 10**309},
    ],
    ids=[
        "unsafe-recovery-distance", "recovery-at-ten-meters",
        "warning-sensor-failure", "missing-trace-id", "missing-action-id", "huge-simulation-time",
    ],
)
def test_v2_contract_mismatch_rejected_before_persistence(http, changes):
    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    ingress = Ingress(DittoWriter(config, request=http))
    first = event_at(0)
    assert http.send(first, ingress) == first
    before = deepcopy(http.twins), http.revisions.copy()
    accepted = deepcopy(ingress._v2_replay)
    http.calls.clear()

    result = None
    try:
        result = http.send(event_at(1, **changes), ingress)
    except EventError:
        pass

    assert http.calls == [], f"Rejected event reached Ditto: {http.calls!r}"
    assert (http.twins, http.revisions) == before
    assert ingress._v2_replay == accepted
    assert result is None, "Invalid event returned a successful persistence result"


@pytest.mark.parametrize(
    "changes",
    [
        recovery_fields(10.000001),
        recovery_fields(20, fault="LIDAR_SENSOR_FAILURE"),
        {"actionId": "fixture-action", "traceId": "fixture-trace"},
        {"simulationSeconds": 0},
        {"simulationSeconds": 1.25},
        {"simulationSeconds": float.fromhex("0x1.fffffffffffffp1023")},
    ],
    ids=[
        "recovery-above-ten-meters", "critical-sensor-failure",
        "paired-correlation", "integer-simulation-time", "fractional-simulation-time",
        "largest-finite-double",
    ],
)
def test_v2_contract_valid_controls_preserve_payload(http, changes):
    event = event_at(1, **changes)
    expected = deepcopy(http.twins)
    assert http.send(event) == event
    expected[TARGET]["features"]["v2"] = {"properties": properties(event)}
    assert http.twins == expected
