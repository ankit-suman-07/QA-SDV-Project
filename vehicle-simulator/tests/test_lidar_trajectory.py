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

from lidar_trajectory import (  # noqa: E402
    HOLD_STEP,
    LADDER,
    distance,
    next_step,
)


def test_ladder_values_are_fixed():
    assert LADDER == (35.0, 20.0, 8.0, 3.0)
    assert HOLD_STEP == 3


def test_obstruction_climbs_one_rung_per_tick_and_holds():
    assert [next_step(s, True) for s in (0, 1, 2, 3)] == [1, 2, 3, 3]


def test_clear_descends_one_rung_per_tick_and_stops_at_zero():
    assert [next_step(s, False) for s in (3, 2, 1, 0)] == [2, 1, 0, 0]


def test_full_cycle_distance_sequence():
    step, seen = 0, [distance(0)]
    for obstructed in [True] * 4 + [False] * 3:
        step = next_step(step, obstructed)
        seen.append(distance(step))
    assert seen == [35.0, 20.0, 8.0, 3.0, 3.0, 8.0, 20.0, 35.0]


def test_reversal_mid_climb():
    step = next_step(next_step(0, True), True)  # 8 m
    assert distance(next_step(step, False)) == 20.0
