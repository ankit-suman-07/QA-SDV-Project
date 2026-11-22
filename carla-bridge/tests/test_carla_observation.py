"""V2-C2 observation envelopes built from front LiDAR readings."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from carla_observation import build_observation, to_json_line  # noqa: E402
from front_lidar import INVALID_FRAME, NO_FRONT_HIT, FrontReading  # noqa: E402
from scripts.v1_dev.contract import parse_timestamp  # noqa: E402
from scripts.v2_dev.contract import validate  # noqa: E402
from scripts.v2_dev.observation_mapping import prepare_observation  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/v2/observations"
MANIFEST = json.loads((FIXTURES / "session-manifest.json").read_text())
PROCESSED = datetime(2026, 1, 1, 0, 0, 0, 10000, tzinfo=timezone.utc)
DISTANCE = "Vehicle.Automation.Lidar.Front.NearestObstacleDistance"
VALIDITY = "Vehicle.Automation.Lidar.Front.IsHealthy"


def observe(**overrides):
    arguments = dict(
        manifest=MANIFEST,
        vehicle_id="vehicle-001",
        sequence=0,
        frame=100,
        simulation_seconds=100.0,
        reading=FrontReading(20.0, True, None),
        processed_at=PROCESSED,
        velocity={"x": 3.0, "y": -4.0, "z": 0.0},
    )
    arguments.update(overrides)
    return build_observation(**arguments)


def test_matches_the_shared_motion_fixture_apart_from_provenance():
    expected = json.loads((FIXTURES / "vehicle-001-motion.json").read_text())
    del expected["fixtureLabel"]
    expected["provenance"] = "CARLA"
    assert observe() == expected


def test_output_passes_the_shared_contract_validator():
    observation = observe()
    assert validate(observation, topic="sdv/vehicle-001/v2/observations") is observation


def test_unavailable_reading_has_null_distance():
    observation = observe(reading=FrontReading(None, False, INVALID_FRAME))
    assert observation["lidar"] == {"distanceMeters": None, "sensorAvailable": False}


def test_reason_code_is_not_part_of_the_envelope():
    observation = observe(reading=FrontReading(50.0, True, NO_FRONT_HIT))
    assert observation["lidar"] == {"distanceMeters": 50.0, "sensorAvailable": True}


def test_velocity_is_omitted_when_motion_is_unknown():
    assert "velocityMetersPerSecond" not in observe(velocity=None)


def test_event_id_combines_vehicle_generation_and_sequence():
    assert observe(sequence=7)["eventId"] == "vehicle-001-s1-7"


def test_simulation_time_is_rounded_to_milliseconds_and_mapped_to_utc():
    observation = observe(simulation_seconds=100.30000000000001)
    assert (observation["simulationSeconds"], observation["sourceTimestamp"]) == (
        100.3, "2026-01-01T00:00:00.300Z")


def test_vehicle_missing_from_manifest_is_rejected():
    with pytest.raises(ValueError, match="vehicle-009"):
        observe(vehicle_id="vehicle-009")


def test_simulation_time_before_origin_is_rejected():
    with pytest.raises(ValueError, match="before the manifest origin"):
        observe(simulation_seconds=99.9)


def test_non_utc_processing_time_is_rejected():
    with pytest.raises(ValueError, match="UTC"):
        observe(processed_at=datetime(2026, 1, 1))


def test_json_line_is_one_compact_line():
    line = to_json_line(observe())
    assert (line.count("\n"), line.endswith("\n"), json.loads(line) == observe()) == (1, True, True)


def test_ankit_mapper_accepts_two_consecutive_observations():
    first = observe(sequence=0, frame=100, simulation_seconds=100.0)
    second = observe(sequence=1, frame=101, simulation_seconds=100.1,
                     reading=FrontReading(7.77, True, None))
    now = parse_timestamp(second["sourceTimestamp"])
    prepare_observation(to_json_line(first), vehicle_id="vehicle-001",
                        manifest=MANIFEST, now=now)
    envelope, values = prepare_observation(to_json_line(second), vehicle_id="vehicle-001",
                                           manifest=MANIFEST, now=now, previous=first)
    assert (values[VALIDITY], values[DISTANCE], envelope["eventId"]) == (
        True, 7.77, "vehicle-001-s1-1")
