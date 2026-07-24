import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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

    def test_should_export_records_to_csv(self):
        recorder = LatencyRecorder(
            experiment_id="baseline",
            publication_interval_seconds=5.0,
        )

        recorder.record(
            event_id="event-001",
            start_time=100.0,
            end_time=100.25,
            success=True,
            health_status="HEALTHY",
        )

        with TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory) / "measurements.csv"
            )

            returned_path = recorder.export_csv(output_path)

            self.assertEqual(output_path, returned_path)
            self.assertTrue(output_path.exists())

            with output_path.open(
                    mode="r",
                    encoding="utf-8",
                    newline=""
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(1, len(rows))
            self.assertEqual("baseline", rows[0]["experiment_id"])
            self.assertEqual("event-001", rows[0]["event_id"])
            self.assertEqual("250.0", rows[0]["latency_ms"])
            self.assertEqual("True", rows[0]["success"])
            self.assertEqual("HEALTHY", rows[0]["health_status"])

    def test_should_export_header_when_no_records_exist(self):
        recorder = LatencyRecorder(
            experiment_id="empty",
            publication_interval_seconds=1.0,
        )

        with TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory) / "empty.csv"
            )

            recorder.export_csv(output_path)

            with output_path.open(
                    mode="r",
                    encoding="utf-8",
                    newline=""
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual([], rows)

    def test_should_export_multiple_records_in_order(self):
        recorder = LatencyRecorder(
            experiment_id="high-load",
            publication_interval_seconds=0.2,
        )

        recorder.record(
            event_id="event-001",
            start_time=100.0,
            end_time=100.10,
            success=True,
            health_status="HEALTHY",
        )

        recorder.record(
            event_id="event-002",
            start_time=101.0,
            end_time=101.30,
            success=False,
            health_status="WARNING",
        )

        with TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory) / "multiple.csv"
            )

            recorder.export_csv(output_path)

            with output_path.open(
                    mode="r",
                    encoding="utf-8",
                    newline=""
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(2, len(rows))
            self.assertEqual("event-001", rows[0]["event_id"])
            self.assertEqual("event-002", rows[1]["event_id"])
            self.assertEqual("False", rows[1]["success"])


if __name__ == "__main__":
    unittest.main()