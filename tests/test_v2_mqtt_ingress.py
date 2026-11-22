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
        ({"lidar": {"distanceMeters": 10**309, "sensorAvailable": True}}, "INVALID_TYPE"),
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
