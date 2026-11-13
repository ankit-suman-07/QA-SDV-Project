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

from signal_generator import (
    AUTONOMOUS_BRAKING_DISTANCE_M,
    LIDAR_WARNING_DISTANCE_M,
    NORMAL_LIDAR_DISTANCE_M,
    NORMAL_RANGES,
    initial_state,
    next_state,
    parse_interval,
)


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
        state = next_state(state)

        for key, (lo, hi) in NORMAL_RANGES.items():
            assert lo <= state[key] <= hi, (
                f"{key}={state[key]} outside "
                f"normal range ({lo}, {hi})"
            )


def test_fault_signal_generation_trends_toward_failure():
    state = initial_state()
    state["battery"] = 15.0

    initial_battery = state["battery"]
    initial_engine_temp = state["engine_temp"]
    initial_tire_pressure = state["tire_pressure"]

    for _ in range(20):
        state = next_state(
            state,
            fault=True,
        )

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
        state = next_state(
            state,
            fault=True,
        )

    assert state["coolant_pressure"] < initial_pressure
    assert state["coolant_pressure"] >= 100.0


def test_coolant_pressure_recovers_after_fault_is_cleared():
    state = initial_state()

    for _ in range(30):
        state = next_state(
            state,
            fault=True,
        )

    fault_pressure = state["coolant_pressure"]

    for _ in range(50):
        state = next_state(state)

    assert fault_pressure < 180.0
    assert 180.0 <= state["coolant_pressure"] <= 220.0


def test_initial_state_contains_healthy_lidar_signals():
    state = initial_state()

    assert (
        state["lidar_distance_m"]
        == NORMAL_LIDAR_DISTANCE_M
    )
    assert state["lidar_sensor_healthy"] is True
    assert state["obstacle_warning"] is False
    assert state["autonomous_braking"] is False


def test_approaching_obstacle_triggers_warning_and_braking():
    state = initial_state()
    initial_speed = state["speed"]

    for _ in range(20):
        state = next_state(
            state,
            obstacle=True,
        )

    assert (
        state["lidar_distance_m"]
        <= AUTONOMOUS_BRAKING_DISTANCE_M
    )
    assert state["lidar_sensor_healthy"] is True
    assert state["obstacle_warning"] is True
    assert state["autonomous_braking"] is True
    assert state["speed"] < initial_speed


def test_obstacle_state_recovers_when_path_clears():
    state = initial_state()

    for _ in range(20):
        state = next_state(
            state,
            obstacle=True,
        )

    for _ in range(20):
        state = next_state(state)

    assert (
        state["lidar_distance_m"]
        > LIDAR_WARNING_DISTANCE_M
    )
    assert state["obstacle_warning"] is False
    assert state["autonomous_braking"] is False


def test_lidar_failure_activates_fail_safe_braking():
    state = next_state(
        initial_state(),
        lidar_failure=True,
    )

    assert state["lidar_distance_m"] == 0.0
    assert state["lidar_sensor_healthy"] is False
    assert state["obstacle_warning"] is True
    assert state["autonomous_braking"] is True

def test_idle_lidar_distance_is_exactly_35():
    state = initial_state()
    for _ in range(50):
        state = next_state(state)
        assert state["lidar_distance_m"] == 35.0
        assert state["lidar_step"] == 0


def test_obstruction_cycle_publishes_exact_distances():
    state, seen = initial_state(), []
    for obstructed in [True] * 4 + [False] * 3:
        state = next_state(state, obstacle=obstructed)
        seen.append(state["lidar_distance_m"])
    assert seen == [20.0, 8.0, 3.0, 3.0, 8.0, 20.0, 35.0]


def test_flags_follow_ladder_thresholds():
    state = initial_state()
    flags = []
    for _ in range(3):
        state = next_state(state, obstacle=True)
        flags.append(
            (state["obstacle_warning"], state["autonomous_braking"])
        )
    assert flags == [(False, False), (True, False), (True, True)]


def test_sensor_failure_keeps_rung_and_resumes():
    state = next_state(
        next_state(initial_state(), obstacle=True), obstacle=True
    )  # 8 m, step 2
    failed = next_state(state, obstacle=True, lidar_failure=True)
    assert failed["lidar_distance_m"] == 0.0
    assert failed["lidar_sensor_healthy"] is False
    assert failed["lidar_step"] == 2
    assert next_state(failed, obstacle=True)["lidar_distance_m"] == 3.0


def test_inject_during_sensor_failure_climbs_after_failure_clears():
    state = initial_state()
    for _ in range(3):
        state = next_state(state, obstacle=True, lidar_failure=True)
    assert state["lidar_step"] == 0
    assert next_state(state, obstacle=True)["lidar_distance_m"] == 20.0
