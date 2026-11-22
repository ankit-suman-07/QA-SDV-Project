"""Per-vehicle frame handling and real-time pacing for the CARLA fleet runner."""

import os
import struct
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from front_lidar import INVALID_FRAME  # noqa: E402
from run_manifest import build_manifest  # noqa: E402
from vehicle_stream import NO_SENSOR_DATA, STALE_FRAME, VehicleStream, pace_delay  # noqa: E402

NOW = datetime(2026, 11, 21, 15, 0, 1, tzinfo=timezone.utc)
MANIFEST = build_manifest(
    session_id="carla-test", generation=1,
    utc_origin=datetime(2026, 11, 21, 15, 0, 0, tzinfo=timezone.utc), simulation_origin=10.0,
    actors=[("vehicle-001", 1, 4), ("vehicle-002", 2, 5), ("vehicle-003", 3, 6)],
    run={"map": "test"})
OBSTACLE_AT_8 = struct.pack("<4f", 8.0, 0.0, 0.0, 1.0)
VELOCITY = {"x": 1.0, "y": 0.0, "z": 0.0}


def stream():
    return VehicleStream(MANIFEST, "vehicle-002")


def test_first_frame_becomes_sequence_zero_with_the_extracted_distance():
    observation, log = stream().on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    assert (observation["eventId"], observation["lidar"]["distanceMeters"], log["reason"]) == (
        "vehicle-002-s1-0", 8.0, None)


def test_next_frame_advances_the_sequence():
    vehicle = stream()
    vehicle.on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    observation, _ = vehicle.on_frame(101, 10.2, OBSTACLE_AT_8, VELOCITY, NOW)
    assert (observation["sequence"], observation["frame"]) == (1, 101)


def test_missing_sensor_data_emits_no_observation_and_keeps_the_sequence():
    vehicle = stream()
    vehicle.on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    log = vehicle.on_missing(101, 10.2)
    observation, _ = vehicle.on_frame(102, 10.3, OBSTACLE_AT_8, VELOCITY, NOW)
    assert (log["reason"], log["vehicleId"], observation["sequence"]) == (NO_SENSOR_DATA, "vehicle-002", 1)


def test_a_repeated_frame_is_dropped():
    vehicle = stream()
    vehicle.on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    observation, log = vehicle.on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    assert (observation, log["reason"]) == (None, STALE_FRAME)


def test_an_older_frame_is_dropped():
    vehicle = stream()
    vehicle.on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    observation, log = vehicle.on_frame(99, 10.0, OBSTACLE_AT_8, VELOCITY, NOW)
    assert (observation, log["reason"]) == (None, STALE_FRAME)


def test_invalid_frame_is_published_as_unavailable_with_its_reason_logged():
    observation, log = stream().on_frame(100, 10.1, b"", VELOCITY, NOW)
    assert (observation["lidar"], log["reason"]) == (
        {"distanceMeters": None, "sensorAvailable": False}, INVALID_FRAME)


def test_log_entry_carries_identity_frame_and_measured_distance():
    _, log = stream().on_frame(100, 10.1, OBSTACLE_AT_8, VELOCITY, NOW)
    assert log == {"vehicleId": "vehicle-002", "eventId": "vehicle-002-s1-0", "frame": 100,
                   "simulationSeconds": 10.1, "distanceMeters": 8.0, "sensorAvailable": True,
                   "reason": None}


def test_pacing_waits_while_simulation_is_ahead_of_the_wall_clock():
    assert pace_delay(simulation_elapsed=2.5, wall_elapsed=2.0) == 0.5


def test_pacing_does_not_wait_when_the_wall_clock_is_ahead():
    assert pace_delay(simulation_elapsed=2.0, wall_elapsed=2.5) == 0.0
