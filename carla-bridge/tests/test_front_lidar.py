"""V2-C3 front-region extraction from raw sensor.lidar.ray_cast bytes."""

import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from front_lidar import (  # noqa: E402
    INVALID_FRAME,
    NO_FRONT_HIT,
    RANGE_METERS,
    FrontReading,
    extract_front,
)

CASES = Path(__file__).resolve().parents[2] / "tests/fixtures/v2/observations/cases.json"


def raw(points):
    """Pack [x, y, z, intensity] tuples the way CARLA's ray_cast raw_data does."""
    return b"".join(struct.pack("<4f", *point) for point in points)


def fixture_case(case_id):
    cases = json.loads(CASES.read_text())["cases"]
    return next(case for case in cases if case["id"] == case_id)


# Contract V2-C3 synthetic tuples, via the shared fixture file.

def test_nearest_front_point_wins_and_side_and_rear_points_are_ignored():
    case = fixture_case("front")
    assert extract_front(raw(case["input"])) == FrontReading(5.0, True, None)


def test_region_bounds_are_inclusive_and_points_below_minus_one_are_ignored():
    case = fixture_case("inclusive")
    assert extract_front(raw(case["input"])) == FrontReading(10.0, True, None)


def test_valid_scan_with_nothing_ahead_is_censored_at_range():
    case = fixture_case("no-hit")
    assert extract_front(raw(case["input"])) == FrontReading(50.0, True, NO_FRONT_HIT)


def test_empty_frame_is_unavailable():
    assert extract_front(b"") == FrontReading(None, False, INVALID_FRAME)


# Byte-level rules the fixtures cannot express as JSON.

def test_byte_length_not_multiple_of_16_is_invalid():
    assert extract_front(raw([[5, 0, 0, 1]]) + b"\x00") == FrontReading(None, False, INVALID_FRAME)


def test_one_nonfinite_coordinate_invalidates_the_whole_frame():
    frame = raw([[5, 0, 0, 1], [float("nan"), 0, 0, 1]])
    assert extract_front(frame) == FrontReading(None, False, INVALID_FRAME)


def test_nonfinite_intensity_invalidates_the_whole_frame():
    frame = raw([[5, 0, 0, float("inf")]])
    assert extract_front(frame) == FrontReading(None, False, INVALID_FRAME)


def test_point_exactly_at_range_is_selected():
    assert extract_front(raw([[50, 0, 0, 1]])) == FrontReading(50.0, True, None)


def test_point_beyond_range_is_not_selected():
    assert extract_front(raw([[50.5, 0, 0, 1]])) == FrontReading(50.0, True, NO_FRONT_HIT)


def test_point_at_x_zero_is_not_in_front():
    assert extract_front(raw([[0, 0, 0, 1]])) == FrontReading(50.0, True, NO_FRONT_HIT)


def test_point_just_outside_lateral_bound_is_ignored():
    assert extract_front(raw([[4, -1.51, 0, 1]])) == FrontReading(50.0, True, NO_FRONT_HIT)


def test_point_above_upper_bound_is_ignored():
    assert extract_front(raw([[4, 0, 1.01, 1]])) == FrontReading(50.0, True, NO_FRONT_HIT)


def test_range_constant_is_fifty_metres():
    assert RANGE_METERS == 50.0
