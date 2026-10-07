import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from get_kuksa_client import get_client

import pytest

pytestmark = pytest.mark.integration

def test_speed_is_published_and_in_range():
    with get_client() as client:
        result = client.get_current_values(["Vehicle.Speed"])
        value = result["Vehicle.Speed"].value
        assert value is not None
        assert 0 <= value <= 120


def test_battery_is_published_and_in_range():
    with get_client() as client:
        result = client.get_current_values(["Vehicle.Powertrain.TractionBattery.StateOfCharge.Current"])
        value = result["Vehicle.Powertrain.TractionBattery.StateOfCharge.Current"].value
        assert value is not None
        assert 40 <= value <= 100


def test_engine_temperature_is_published_and_in_range():
    with get_client() as client:
        result = client.get_current_values(["Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature"])
        value = result["Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature"].value
        assert value is not None
        assert 85 <= value <= 95


def test_tire_pressure_is_published_and_in_range():
    with get_client() as client:
        result = client.get_current_values(["Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure"])
        value = result["Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure"].value
        assert value is not None
        assert 30 <= value <= 34


def test_coolant_pressure_is_published_and_in_range():
    with get_client() as client:
        result = client.get_current_values(["Vehicle.Powertrain.CombustionEngine.EngineCoolant.Pressure"])
        value = result["Vehicle.Powertrain.CombustionEngine.EngineCoolant.Pressure"].value
        assert value is not None
        assert isinstance(value, (int, float))
        assert 100 <= value <= 220