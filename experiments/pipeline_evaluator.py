import time

from experiments.latency_recorder import LatencyRecorder


class PipelineEvaluator:

    def __init__(
            self,
            experiment_id,
            publication_interval_seconds,
            clock=time.perf_counter
    ):
        self.clock = clock
        self.start_times = {}

        self.recorder = LatencyRecorder(
            experiment_id=experiment_id,
            publication_interval_seconds=publication_interval_seconds,
        )

    def start_event(self, event_id):
        self.start_times[event_id] = self.clock()

    def complete_event(
            self,
            event_id,
            success,
            health_status
    ):
        if event_id not in self.start_times:
            raise ValueError(
                f"Event was not started: {event_id}"
            )
        start_time = self.start_times.pop(event_id)
        end_time = self.clock()

        return self.recorder.record(
            event_id=event_id,
            start_time=start_time,
            end_time=end_time,
            success=success,
            health_status=health_status,
        )