import math
import statistics


def summarize_records(
        records,
        experiment_duration_seconds
):
    if not records:
        raise ValueError("At least one measurement record is required")

    if experiment_duration_seconds <= 0:
        raise ValueError("Experiment duration must be greater than zero")
    
    latencies = sorted(
        record["latency_ms"]
        for record in records
    )

    total_messages = len(records)

    successful_messages = sum(
        1 for record in records
        if record["success"]
    )

    failed_messages = (
        total_messages - successful_messages
    )

    success_rate_percent = (
        successful_messages / total_messages
    ) * 100

    p95_index = (
        math.ceil(0.95 * total_messages) - 1
    )

    return {
        "total_messages": total_messages,
        "successful_messages": successful_messages,
        "failed_messages": failed_messages,
        "success_rate_percent": success_rate_percent,
        "min_latency_ms": min(latencies),
        "average_latency_ms": statistics.mean(latencies),
        "median_latency_ms": statistics.median(latencies),
        "p95_latency_ms": latencies[p95_index],
        "max_latency_ms": max(latencies),
        "throughput_messages_per_second":
            total_messages / experiment_duration_seconds,
    }