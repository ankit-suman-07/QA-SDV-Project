"""Frame selection and outcome accounting for the V2-C3 review probe (v3)."""

import importlib.util
import queue
import unittest
from collections import namedtuple
from pathlib import Path

PROBE = Path(__file__).resolve().parents[1] / "evidence/v2/c3-extraction-review/c3_region_probe_v3.py"
spec = importlib.util.spec_from_file_location("c3_region_probe_v3", PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

Scan = namedtuple("Scan", "frame")
Point = namedtuple("Point", "x y z tag")


def feed(*frames):
    items = queue.Queue()
    for frame in frames:
        items.put(Scan(frame))
    return items.get


class ScanForTest(unittest.TestCase):
    def test_returns_the_requested_frame_after_discarding_older_ones(self):
        self.assertEqual(probe.scan_for(feed(8, 9, 10), 10, 0.01), (Scan(10), None))

    def test_later_frame_does_not_substitute_for_a_missing_one(self):
        self.assertEqual(probe.scan_for(feed(9, 11), 10, 0.01), (None, 11))

    def test_no_callback_is_missing(self):
        self.assertEqual(probe.scan_for(feed(), 10, 0.01), (None, None))


class ClassifyTest(unittest.TestCase):
    def test_empty_scan_is_its_own_outcome(self):
        self.assertEqual(probe.classify([], -1.0)["outcome"], "EMPTY_SCAN")

    def test_nothing_in_region_is_no_front_hit(self):
        row = probe.classify([Point(10, 5, 0, 10)], -1.0)
        self.assertEqual(row["outcome"], "NO_FRONT_HIT")

    def test_nearest_road_point_is_a_false_surface(self):
        row = probe.classify([Point(20, 0, 0, 10), Point(4, 0, -0.9, 1)], -1.0)
        self.assertEqual((row["outcome"], row["cls"], row["x"]), ("FALSE_SURFACE", "Roads", 4))

    def test_lower_bound_excludes_points_below_zmin(self):
        row = probe.classify([Point(4, 0, -0.9, 1)], -0.5)
        self.assertEqual(row["outcome"], "NO_FRONT_HIT")


class SummarizeTest(unittest.TestCase):
    def test_valid_scans_exclude_empty_missing_mismatched_and_failed_spawns(self):
        outcomes = ["NO_FRONT_HIT", "OBJECT", "FALSE_SURFACE", "EMPTY_SCAN",
                    "MISSING_SCAN", "FRAME_MISMATCH", "SPAWN_FAILED"]
        summary = probe.summarize([{"outcome": o} for o in outcomes])
        self.assertEqual(summary["validScans"], 3)
        self.assertEqual(summary["spawnPoints"], 7)
        self.assertEqual(summary["EMPTY_SCAN"], 1)
