import unittest

from experiments.latency_recorder import LatencyRecorder


class LatencyRecorderTest(unittest.TestCase):

    def test_should_record_successful_event_latency(self):
        recorder = LatencyRecorder(
            experiment_id="baseline",
            publication_interval_seconds=5.0,
        )

        record = recorder.record(
            event_id="event-001",
            start_time=100.0,
            end_time=100.25,
            success=True,
            health_status="HEALTHY",
        )

        self.assertEqual("baseline", record["experiment_id"])
        self.assertEqual("event-001", record["event_id"])
        self.assertEqual(
            5.0,
            record["publication_interval_seconds"]
        )
        self.assertAlmostEqual(250.0, record["latency_ms"])
        self.assertTrue(record["success"])
        self.assertEqual("HEALTHY", record["health_status"])

    def test_should_reject_non_positive_publication_interval(self):
        with self.assertRaisesRegex(
                ValueError,
                "Publication interval must be greater than zero"
        ):
            LatencyRecorder(
                experiment_id="invalid",
                publication_interval_seconds=0,
            )

    def test_should_reject_end_time_before_start_time(self):
        recorder = LatencyRecorder(
            experiment_id="baseline",
            publication_interval_seconds=5.0,
        )

        with self.assertRaisesRegex(
                ValueError,
                "End time cannot be before start time"
        ):
            recorder.record(
                event_id="event-002",
                start_time=100.5,
                end_time=100.0,
                success=False,
                health_status="UNKNOWN",
            )


if __name__ == "__main__":
    unittest.main()