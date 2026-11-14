import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.v1_dev import contract  # noqa: E402  (test-only oracle)
from v1_event import (  # noqa: E402
    build_v1_event,
    classify,
    format_timestamp,
    new_event_id,
    serialize,
    topic,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "distance,expected",
    [
        (10.01, ("HEALTHY", [])),
        (10.0, ("WARNING", ["LIDAR_OBSTRUCTION"])),
        (5.01, ("WARNING", ["LIDAR_OBSTRUCTION"])),
        (5.0, ("CRITICAL", ["LIDAR_OBSTRUCTION"])),
        (0.0, ("CRITICAL", ["LIDAR_OBSTRUCTION"])),
    ],
)
def test_classify_boundaries(distance, expected):
    assert classify(distance, True) == expected


def test_sensor_failure_has_priority():
    assert classify(3.0, False) == ("CRITICAL", ["LIDAR_SENSOR_FAILURE"])


def test_topic():
    assert topic("vehicle-002") == "sdv/vehicle-002/health"


def test_format_timestamp_converts_to_utc_z():
    t = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    assert format_timestamp(t) == "2026-01-01T00:00:00Z"


def test_format_timestamp_keeps_microseconds():
    t = datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
    assert format_timestamp(t) == "2026-01-01T00:00:00.123456Z"


def test_format_timestamp_rejects_naive_datetime():
    with pytest.raises(ValueError):
        format_timestamp(datetime(2026, 1, 1))


@pytest.mark.parametrize(
    "vehicle,distance,available",
    [
        ("vehicle-001", 35.0, True),
        ("vehicle-002", 7.5, True),
        ("vehicle-002", 3.0, True),
        ("vehicle-001", 12.0, False),
    ],
)
def test_built_events_pass_shared_contract_oracle(vehicle, distance, available):
    event = build_v1_event(vehicle, T0, distance, available, "e-1")
    decoded = contract.decode_event(serialize(event))
    assert contract.validate_event(topic(vehicle), decoded) == event


def test_built_event_fields_and_order():
    event = build_v1_event("vehicle-002", T0, 3.0, True, "vehicle-002-abc")
    assert list(event) == [
        "schemaVersion",
        "eventId",
        "vehicleId",
        "sourceTimestamp",
        "health",
        "faults",
        "lidar",
    ]
    assert event["schemaVersion"] == "1.0.0"
    assert event["eventId"] == "vehicle-002-abc"
    assert event["sourceTimestamp"] == "2026-01-01T00:00:00Z"
    assert event["health"] == "CRITICAL"
    assert event["faults"] == ["LIDAR_OBSTRUCTION"]
    assert event["lidar"] == {"distanceMeters": 3.0, "sensorAvailable": True}


def test_unavailable_sensor_publishes_null_distance():
    event = build_v1_event("vehicle-001", T0, 12.0, False, "e")
    assert event["lidar"] == {"distanceMeters": None, "sensorAvailable": False}


@pytest.mark.parametrize(
    "bad", [True, "3.0", float("nan"), float("inf"), -0.1, None]
)
def test_build_rejects_bool_string_nan_and_negative_distance(bad):
    with pytest.raises(ValueError):
        build_v1_event("vehicle-001", T0, bad, True, "e")


def test_build_rejects_non_bool_sensor_flag():
    with pytest.raises(ValueError):
        build_v1_event("vehicle-001", T0, 3.0, 1, "e")


def test_serialize_is_compact_and_rejects_nan():
    assert " " not in serialize({"a": 1, "b": [1, 2]})
    with pytest.raises(ValueError):
        serialize({"a": float("nan")})


def test_event_ids_unique_and_prefixed():
    ids = {new_event_id("vehicle-001") for _ in range(100)}
    assert len(ids) == 100
    assert all(i.startswith("vehicle-001-") for i in ids)
