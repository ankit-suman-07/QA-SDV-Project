import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
    ),
)

from get_kuksa_client import get_client


pytestmark = pytest.mark.integration

SPEED_PATH = "Vehicle.Speed"

BATTERY_PATH = (
    "Vehicle.Powertrain.TractionBattery."
    "StateOfCharge.Current"
)

ENGINE_TEMPERATURE_PATH = (
    "Vehicle.Powertrain.CombustionEngine."
    "EngineCoolant.Temperature"
)

TIRE_PRESSURE_PATH = (
    "Vehicle.Chassis.Axle.Row1.Wheel.Left."
    "Tire.Pressure"
)

COOLANT_PRESSURE_PATH = (
    "Vehicle.Powertrain.CombustionEngine."
    "EngineCoolant.Pressure"
)

LIDAR_DISTANCE_PATH = (
    "Vehicle.Automation.Lidar.Front."
    "NearestObstacleDistance"
)

LIDAR_HEALTH_PATH = (
    "Vehicle.Automation.Lidar.Front.IsHealthy"
)

OBSTACLE_WARNING_PATH = (
    "Vehicle.Automation.ObstacleWarning.IsActive"
)

AUTONOMOUS_BRAKING_PATH = (
    "Vehicle.Automation.AutonomousBraking.IsActive"
)


def read_signal(signal_path):
    with get_client() as client:
        result = client.get_current_values(
            [signal_path]
        )

    datapoint = result[signal_path]
    return datapoint.value


def test_speed_is_published_and_in_range():
    value = read_signal(SPEED_PATH)

    assert value is not None
    assert 0 <= value <= 120


def test_battery_is_published_and_in_range():
    value = read_signal(BATTERY_PATH)

    assert value is not None
    assert 0 <= value <= 100


def test_engine_temperature_is_published_and_in_range():
    value = read_signal(ENGINE_TEMPERATURE_PATH)

    assert value is not None
    assert 0 <= value <= 150


def test_tire_pressure_is_published_and_in_range():
    value = read_signal(TIRE_PRESSURE_PATH)

    assert value is not None
    # Published VSS path is integer kPa, not the generator's internal psi.
    assert 0 <= value <= round(34 * 6.894757293168)


def test_coolant_pressure_is_published_and_in_range():
    value = read_signal(COOLANT_PRESSURE_PATH)

    assert value is not None
    assert isinstance(value, (int, float))
    assert 100 <= value <= 220


def test_lidar_distance_is_published_and_in_range():
    value = read_signal(LIDAR_DISTANCE_PATH)

    assert value is not None
    assert isinstance(value, (int, float))
    assert 0 <= value <= 250


def test_lidar_health_is_published_as_boolean():
    value = read_signal(LIDAR_HEALTH_PATH)

    assert value is not None
    assert isinstance(value, bool)


def test_obstacle_warning_is_published_as_boolean():
    value = read_signal(OBSTACLE_WARNING_PATH)

    assert value is not None
    assert isinstance(value, bool)


def test_autonomous_braking_is_published_as_boolean():
    value = read_signal(AUTONOMOUS_BRAKING_PATH)

    assert value is not None
    assert isinstance(value, bool)