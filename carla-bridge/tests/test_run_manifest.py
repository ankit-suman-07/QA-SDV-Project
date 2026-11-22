"""V2-C1/C2 run manifest: identity mapping, clock origins and run settings."""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from carla_observation import build_observation, to_json_line  # noqa: E402
from front_lidar import FrontReading  # noqa: E402
from run_manifest import build_manifest  # noqa: E402
from scripts.v1_dev.contract import parse_timestamp  # noqa: E402
from scripts.v2_dev.observation_mapping import prepare_observation  # noqa: E402

ORIGIN_UTC = datetime(2026, 11, 21, 15, 0, 0, 123456, tzinfo=timezone.utc)
ACTORS = [("vehicle-001", 24, 27), ("vehicle-002", 25, 28), ("vehicle-003", 26, 29)]
RUN = {"map": "Carla/Maps/Town10HD_Opt", "fixedDeltaSeconds": 0.1}


def manifest(**overrides):
    arguments = dict(session_id="carla-20261121T150000Z", generation=1,
                     utc_origin=ORIGIN_UTC, simulation_origin=12.3456,
                     actors=ACTORS, run=RUN)
    arguments.update(overrides)
    return build_manifest(**arguments)


def test_maps_each_vehicle_to_its_actor_sensor_and_edge_targets():
    assert manifest()["vehicles"][1] == {
        "vehicleId": "vehicle-002", "actorId": 25, "sensorId": 28,
        "provider": "provider-002", "broker": "kuksa-002", "brokerPort": 55555,
        "app": "app-002", "twinId": "sdv:vehicle-002",
    }


def test_clock_origins_are_rounded_to_milliseconds():
    result = manifest()
    assert (result["utcOrigin"], result["simulationOrigin"]) == ("2026-11-21T15:00:00.123Z", 12.346)


def test_session_identity_and_run_settings_are_recorded():
    result = manifest()
    assert (result["sessionId"], result["sessionGeneration"], result["provenance"], result["run"]) == (
        "carla-20261121T150000Z", 1, "CARLA", RUN)


def test_vehicles_are_sorted_by_vehicle_id():
    shuffled = [ACTORS[2], ACTORS[0], ACTORS[1]]
    ids = [row["vehicleId"] for row in manifest(actors=shuffled)["vehicles"]]
    assert ids == ["vehicle-001", "vehicle-002", "vehicle-003"]


def test_a_missing_vehicle_is_rejected():
    with pytest.raises(ValueError, match="vehicle-001, vehicle-002 and vehicle-003"):
        manifest(actors=ACTORS[:2])


def test_a_duplicate_vehicle_is_rejected():
    with pytest.raises(ValueError, match="vehicle-001, vehicle-002 and vehicle-003"):
        manifest(actors=[ACTORS[0], ACTORS[0], ACTORS[2]])


def test_a_reused_actor_id_is_rejected():
    reused = [("vehicle-001", 24, 27), ("vehicle-002", 24, 28), ("vehicle-003", 26, 29)]
    with pytest.raises(ValueError, match="actor"):
        manifest(actors=reused)


def test_generation_below_one_is_rejected():
    with pytest.raises(ValueError, match="generation"):
        manifest(generation=0)


def test_ankit_mapper_accepts_an_observation_under_this_manifest():
    result = manifest()
    observation = build_observation(
        manifest=result, vehicle_id="vehicle-003", sequence=0, frame=500,
        simulation_seconds=14.0, reading=FrontReading(8.0, True, None),
        processed_at=ORIGIN_UTC)
    now = parse_timestamp(observation["sourceTimestamp"])
    envelope, _ = prepare_observation(to_json_line(observation), vehicle_id="vehicle-003",
                                      manifest=result, now=now)
    assert envelope["sourceTimestamp"] == "2026-11-21T15:00:01.777Z"
