import unittest

from experiments.pipeline_evaluator import PipelineEvaluator


class PipelineEvaluatorTest(unittest.TestCase):

    def test_should_measure_completed_pipeline_event(self):
        timestamps = iter([10.000, 10.125])

        evaluator = PipelineEvaluator(
            experiment_id="interval-1s",
            publication_interval_seconds=1.0,
            clock=lambda: next(timestamps),
        )

        evaluator.start_event("event-001")

        record = evaluator.complete_event(
            event_id="event-001",
            success=True,
            health_status="HEALTHY",
        )

        self.assertEqual("event-001", record["event_id"])
        self.assertAlmostEqual(125.0, record["latency_ms"])
        self.assertTrue(record["success"])
        self.assertEqual("HEALTHY", record["health_status"])

    def test_should_reject_event_that_was_not_started(self):
        evaluator = PipelineEvaluator(
            experiment_id="interval-1s",
            publication_interval_seconds=1.0,
        )

        with self.assertRaisesRegex(
                ValueError,
                "Event was not started: missing-event"
        ):
            evaluator.complete_event(
                event_id="missing-event",
                success=False,
                health_status="UNKNOWN",
            )

    def test_should_accept_an_explicit_start_time(self):
        evaluator = PipelineEvaluator(
            experiment_id="interval-1s",
            publication_interval_seconds=1.0,
            clock=lambda: 20.250,
        )

        evaluator.start_event(
            event_id="event-002",
            start_time=20.000,
        )

        record = evaluator.complete_event(
            event_id="event-002",
            success=True,
            health_status="WARNING",
        )

        self.assertAlmostEqual(250.0, record["latency_ms"])
        self.assertEqual("WARNING", record["health_status"])


if __name__ == "__main__":
    unittest.main()