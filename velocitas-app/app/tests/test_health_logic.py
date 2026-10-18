import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
    ),
)

from health_logic import (
    build_status_event,
    classify_autonomous_health,
)


def test_healthy_state():
    assert classify_autonomous_health(
        lidar_sensor_healthy=True,
        obstacle_warning=False,
        autonomous_braking=False,
    ) == "HEALTHY"


def test_obstacle_warning_state():
    assert classify_autonomous_health(
        lidar_sensor_healthy=True,
        obstacle_warning=True,
        autonomous_braking=False,
    ) == "WARNING"


def test_autonomous_braking_state():
    assert classify_autonomous_health(
        lidar_sensor_healthy=True,
        obstacle_warning=True,
        autonomous_braking=True,
    ) == "EMERGENCY_BRAKING"


def test_lidar_failure_has_highest_priority():
    assert classify_autonomous_health(
        lidar_sensor_healthy=False,
        obstacle_warning=True,
        autonomous_braking=True,
    ) == "SENSOR_FAILURE"


def test_status_event_contains_vehicle_context():
    event = build_status_event(
        vehicle_id="vehicle-001",
        speed=25.0,
        lidar_distance_m=4.0,
        lidar_sensor_healthy=True,
        obstacle_warning=True,
        autonomous_braking=True,
    )

    assert event["vehicleId"] == "vehicle-001"
    assert event["healthStatus"] == "EMERGENCY_BRAKING"
    assert event["speed"] == 25.0
    assert event["lidarDistanceMeters"] == 4.0
    assert event["autonomousBraking"] is True
    assert event["timestamp"]