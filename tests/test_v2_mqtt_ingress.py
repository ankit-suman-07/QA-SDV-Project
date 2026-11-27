"""Offline V2 health ingress regression using the shared synthetic fixtures."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ditto.mqtt_ingress import EventError, Ingress
from scripts.v2_dev.contract import validate_health


FIXTURES = Path(__file__).parent / "fixtures" / "v2"


def test_v2_vehicle_003_health_updates_only_its_individual_twin():
    expected_twins = {}
    for vehicle_id in ("vehicle-001", "vehicle-002", "vehicle-003"):
        twin = json.loads((FIXTURES / "twins" / f"{vehicle_id}.json").read_text(encoding="utf-8"))
        twin.pop("fixtureLabel")
        twin["features"]["v2"]["properties"].pop("fixtureLabel")
        expected_twins[vehicle_id] = twin

    vehicle_id = "vehicle-003"
    event = json.loads(
        (FIXTURES / "health-events" / f"{vehicle_id}.json").read_text(encoding="utf-8")
    )
    event.pop("fixtureLabel")
    validate_health(event)
    payload = json.dumps(event).encode("utf-8")
    # V2-C5 defines the health topic and individual v2 feature.
    twins = deepcopy(expected_twins)
    twins[vehicle_id]["features"].pop("v2")
    writes = []
    reads = []

    class TwinStore:
        def load_watermark(self, target):
            reads.append(target)
            properties = twins[target]["features"].get("v2", {}).get("properties")
            if properties is not None:
                return properties["lastEventId"], properties["sourceTimestamp"]
            return None

        def persist(self, target, properties):
            writes.append(twins[target]["thingId"])
            twins[target]["features"]["v2"] = {"properties": deepcopy(properties)}

    ingress = Ingress(TwinStore())
    accepted = ingress.process(f"sdv/{vehicle_id}/v2/health", payload)
    assert accepted == event
    assert writes == [expected_twins[vehicle_id]["thingId"]]
    assert twins == expected_twins

    before = reads.copy(), writes.copy()
    with pytest.raises(EventError, match="^TOPIC_MISMATCH$"):
        ingress.process("sdv/vehicle-002/v2/health", payload)
    assert (reads, writes) == before
    assert twins == expected_twins


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"health": "WARNING", "faults": ["LIDAR_SENSOR_FAILURE"]}, "HEALTH_FAULT_MISMATCH"),
        ({"lidar": {"distanceMeters": 10**309, "sensorAvailable": True}}, "UNSAFE_INTEGER"),
    ],
    ids=["warning-sensor-failure-none", "distance-overflows-double"],
)
def test_v2_backend_invalid_snapshot_never_reaches_ditto(changes, error):
    from test_v2_ditto_writer import DittoHTTP, event_at

    http = DittoHTTP()
    before = deepcopy(http.twins), http.revisions.copy()
    with pytest.raises(EventError, match=f"^{error}$"):
        http.send(event_at(0, **changes))
    assert http.calls == []
    assert http.put_headers() == []
    assert (http.twins, http.revisions) == before


@pytest.mark.parametrize(
    ("health", "fault"),
    [
        ("WARNING", "LIDAR_OBSTRUCTION"),
        ("CRITICAL", "LIDAR_OBSTRUCTION"),
        ("CRITICAL", "LIDAR_SENSOR_FAILURE"),
    ],
)
def test_v2_backend_valid_retained_fault_snapshot_is_persisted(health, fault):
    from test_v2_ditto_writer import DittoHTTP, TARGET, event_at, properties

    http = DittoHTTP()
    event = event_at(0, health=health, faults=[fault])
    assert event["lidar"]["distanceMeters"] > 10
    assert event["recoveryState"] == "NONE"
    expected = deepcopy(http.twins)
    expected[TARGET]["features"]["v2"] = {"properties": properties(event)}
    assert http.send(event) == event
    assert len(http.put_headers()) == 1
    assert http.twins == expected


def make_v2_ingress(http):
    from ditto.v1_writer import DittoConfig, DittoWriter

    config = DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1)
    return Ingress(DittoWriter(config, request=http))


@pytest.mark.parametrize(("change", "code"), [
    (lambda e: b'{"eventId":', "MALFORMED_JSON"),
    (lambda e: b'{"eventId":"duplicate",' + json.dumps(e).encode()[1:], "DUPLICATE_KEY"),
    (lambda e: json.dumps(dict(e, packetId=1)).encode(), "UNKNOWN_FIELD"),
    (lambda e: json.dumps(dict(e, lidar=dict(e["lidar"], extra=0))).encode(), "UNKNOWN_FIELD"),
    (lambda e: json.dumps(dict(e, actionId="unpaired")).encode(), "MISSING_FIELD"),
    (lambda e: json.dumps(dict(e, actionId=None, traceId=None)).encode(), "INVALID_TYPE"),
    (lambda e: json.dumps(dict(e, lidar={"sensorAvailable": False})).encode(), "MISSING_FIELD"),
])
def test_strict_v2_raw_health_is_rejected_before_storage(change, code):
    from test_v2_ditto_writer import DittoHTTP, TOPIC, event_at

    http = DittoHTTP()
    ingress = make_v2_ingress(http)
    before = deepcopy(http.twins)
    with pytest.raises(EventError, match=f"^{code}$"):
        ingress.process(TOPIC, change(event_at(0)))
    assert http.calls == []
    assert http.twins == before


def test_v2_health_keeps_original_fingerprint_separate_from_ditto_and_replay():
    from test_v2_ditto_writer import DittoHTTP, TARGET, TOPIC, properties

    suite = json.loads((FIXTURES / "status" / "envelope-vectors.json").read_bytes())
    by_id = {case["id"]: case for case in suite["cases"]}
    original = by_id["health-minimal-optionals-absent"]
    raw = original["inputJson"].encode()
    event = json.loads(raw)
    http = DittoHTTP()
    ingress = make_v2_ingress(http)
    expected_twins = deepcopy(http.twins)
    expected_twins[TARGET]["features"]["v2"] = {"properties": properties(event)}

    accepted = ingress.process_v2_health(TOPIC, raw)
    assert accepted.envelope == event == json.loads(raw)
    assert accepted.canonical_bytes.hex() == original["expected"]["canonicalUtf8Hex"]
    assert accepted.sha256 == original["expected"]["sha256"]
    assert http.twins == expected_twins

    reordered = by_id["health-reordered-retry"]["inputJson"].encode()
    retry = ingress.process_v2_health(TOPIC, reordered)
    assert retry == accepted
    with pytest.raises(EventError, match="^EVENT_ID_CONFLICT$"):
        ingress.process(TOPIC, json.dumps(dict(event, processingTimestamp=event["sourceTimestamp"])))
    assert len(http.put_headers()) == 1
    assert http.twins == expected_twins
    assert accepted.envelope == event


def test_v2_unavailable_lidar_accepts_required_null():
    from test_v2_ditto_writer import DittoHTTP, TARGET, TOPIC, event_at, properties

    http = DittoHTTP()
    ingress = make_v2_ingress(http)
    event = event_at(0, lidar={"sensorAvailable": False, "distanceMeters": None},
                     health="CRITICAL", faults=["LIDAR_SENSOR_FAILURE"])
    expected_twins = deepcopy(http.twins)
    expected_twins[TARGET]["features"]["v2"] = {"properties": properties(event)}
    assert ingress.process(TOPIC, json.dumps(event)) == event
    assert http.twins == expected_twins


@pytest.mark.parametrize(("topic", "changes", "code", "ids"), [
    ("sdv/vehicle-002/v2/health", {}, "TOPIC_MISMATCH", ("vehicle-003", "vehicle-003-s1-0")),
    ("sdv/vehicle-003/v2/health", {"packetId": 1}, "UNKNOWN_FIELD",
     ("vehicle-003", "vehicle-003-s1-0")),
    ("sdv/vehicle-003/v2/health", {"vehicleId": 3, "eventId": True}, "UNKNOWN_VEHICLE",
     (None, None)),
    ("sdv/vehicle-003/v2/health", {"eventId": " padded "}, "INVALID_TYPE",
     ("vehicle-003", None)),
    ("sdv/vehicle-003/v2/health", {"eventId": "line\nbreak", "packetId": 1}, "UNKNOWN_FIELD",
     ("vehicle-003", None)),
])
def test_v2_rejection_correlates_only_safe_payload_ids(topic, changes, code, ids):
    from ditto.mqtt_ingress import decode_v2_health

    event = json.loads((FIXTURES / "health-events" / "vehicle-003.json").read_bytes())
    event.pop("fixtureLabel")
    event["eventId"] = "vehicle-003-s1-0"
    event.update(changes)
    with pytest.raises(EventError, match=f"^{code}$") as exc:
        decode_v2_health(topic, json.dumps(event).encode())
    assert (exc.value.vehicle_id, exc.value.event_id) == ids


@pytest.mark.parametrize(("payload", "code"), [
    (b'{"vehicleId":"vehicle-003","eventId":"unclosed"', "MALFORMED_JSON"),
    (b'{"vehicleId":"vehicle-003","eventId":"one","eventId":"two"}', "DUPLICATE_KEY"),
    (b'{"vehicleId":"vehicle-003","eventId":"one","lidar":{"x":1,"x":2}}', "DUPLICATE_KEY"),
])
def test_v2_unparseable_or_ambiguous_input_has_no_diagnostics(payload, code):
    from ditto.mqtt_ingress import decode_v2_health

    with pytest.raises(EventError, match=f"^{code}$") as exc:
        decode_v2_health("sdv/vehicle-003/v2/health", payload)
    assert (exc.value.vehicle_id, exc.value.event_id) == (None, None)
