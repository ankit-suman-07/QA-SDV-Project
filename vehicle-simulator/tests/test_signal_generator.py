import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from signal_generator import initial_state, next_state, parse_interval, NORMAL_RANGES


def test_parse_interval_default_value():
    assert parse_interval("5.0") == 5.0


def test_parse_interval_valid_custom_value():
    assert parse_interval("0.2") == 0.2
    assert parse_interval("1.0") == 1.0


def test_parse_interval_rejects_non_numeric():
    with pytest.raises(ValueError):
        parse_interval("abc")


def test_parse_interval_rejects_zero():
    with pytest.raises(ValueError):
        parse_interval("0")


def test_parse_interval_rejects_negative():
    with pytest.raises(ValueError):
        parse_interval("-1")


def test_normal_signal_generation_stays_within_range():
    state = initial_state()
    for _ in range(200):
        state = next_state(state, fault=False)
        for key, (lo, hi) in NORMAL_RANGES.items():
            assert lo <= state[key] <= hi, f"{key}={state[key]} outside normal range ({lo}, {hi})"


def test_fault_signal_generation_trends_toward_failure():
    state = initial_state()
    state["battery"] = 15.0
    initial_battery = state["battery"]
    initial_engine_temp = state["engine_temp"]
    initial_tire_pressure = state["tire_pressure"]

    for _ in range(20):
        state = next_state(state, fault=True)

    assert state["battery"] <= initial_battery
    assert state["engine_temp"] >= initial_engine_temp
    assert state["tire_pressure"] <= initial_tire_pressure

def test_initial_state_contains_normal_coolant_pressure():
    state = initial_state()

    assert state["coolant_pressure"] == 200.0


def test_fault_generation_reduces_coolant_pressure():
    state = initial_state()
    initial_pressure = state["coolant_pressure"]

    for _ in range(20):
        state = next_state(state, fault=True)

    assert state["coolant_pressure"] < initial_pressure
    assert state["coolant_pressure"] >= 100.0

def test_coolant_pressure_recovers_after_fault_is_cleared():
    state = initial_state()

    for _ in range(30):
        state = next_state(state, fault=True)

    fault_pressure = state["coolant_pressure"]

    for _ in range(50):
        state = next_state(state, fault=False)

    assert fault_pressure < 180.0
    assert state["coolant_pressure"] >= 180.0
    assert state["coolant_pressure"] <= 220.0
