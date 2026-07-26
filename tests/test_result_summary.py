import unittest

from experiments.result_summary import summarize_records


class ResultSummaryTest(unittest.TestCase):

    def test_should_calculate_experiment_statistics(self):
        records = [
            {"latency_ms": 100.0, "success": True},
            {"latency_ms": 200.0, "success": True},
            {"latency_ms": 300.0, "success": False},
            {"latency_ms": 400.0, "success": True},
        ]

        summary = summarize_records(
            records=records,
            experiment_duration_seconds=2.0,
        )

        self.assertEqual(4, summary["total_messages"])
        self.assertEqual(3, summary["successful_messages"])
        self.assertEqual(1, summary["failed_messages"])
        self.assertAlmostEqual(
            75.0,
            summary["success_rate_percent"]
        )
        self.assertAlmostEqual(
            100.0,
            summary["min_latency_ms"]
        )
        self.assertAlmostEqual(
            250.0,
            summary["average_latency_ms"]
        )
        self.assertAlmostEqual(
            250.0,
            summary["median_latency_ms"]
        )
        self.assertAlmostEqual(
            400.0,
            summary["p95_latency_ms"]
        )
        self.assertAlmostEqual(
            400.0,
            summary["max_latency_ms"]
        )
        self.assertAlmostEqual(
            2.0,
            summary["throughput_messages_per_second"]
        )

    def test_should_reject_empty_records(self):
        with self.assertRaisesRegex(
                ValueError,
                "At least one measurement record is required"
        ):
            summarize_records(
                records=[],
                experiment_duration_seconds=10.0,
            )

    def test_should_reject_non_positive_duration(self):
        records = [
            {"latency_ms": 100.0, "success": True}
        ]

        with self.assertRaisesRegex(
                ValueError,
                "Experiment duration must be greater than zero"
        ):
            summarize_records(
                records=records,
                experiment_duration_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()