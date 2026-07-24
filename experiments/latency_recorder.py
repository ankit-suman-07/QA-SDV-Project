class LatencyRecorder:

    def __init__(
            
            self,
            experiment_id,
            publication_interval_seconds
    ):
        if publication_interval_seconds <= 0:
            raise ValueError(
                "Publication interval must be greater than zero"
            )

        self.experiment_id = experiment_id
        self.publication_interval_seconds = (
            publication_interval_seconds
        )
        self.records = []

    def record(
            self,
            event_id,
            start_time,
            end_time,
            success,
            health_status
    ):
        if end_time < start_time:
            raise ValueError(
                "End time cannot be before start time"
            )

        latency_ms = (end_time - start_time) * 1000

        record = {
            "experiment_id": self.experiment_id,
            "event_id": event_id,
            "publication_interval_seconds":
                self.publication_interval_seconds,
            "latency_ms": latency_ms,
            "success": success,
            "health_status": health_status,
        }

        self.records.append(record)

        return record