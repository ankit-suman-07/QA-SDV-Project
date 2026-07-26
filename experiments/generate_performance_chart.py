import csv
from pathlib import Path

import matplotlib.pyplot as plt


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

SUMMARY_FILE = (
    REPOSITORY_ROOT
    / "experiments"
    / "results"
    / "experiment-summary.csv"
)

OUTPUT_FILE = (
    REPOSITORY_ROOT
    / "experiments"
    / "results"
    / "pipeline-performance-comparison.png"
)


def load_results():
    with SUMMARY_FILE.open(
            encoding="utf-8",
            newline=""
    ) as file:
        return list(csv.DictReader(file))


def generate_chart():
    rows = load_results()

    interval_labels = [
        f"{row['publication_interval_seconds']} s"
        for row in rows
    ]

    average_latency = [
        float(row["average_latency_ms"])
        for row in rows
    ]

    p95_latency = [
        float(row["p95_latency_ms"])
        for row in rows
    ]

    throughput = [
        float(row["throughput_messages_per_second"])
        for row in rows
    ]

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(12, 5),
    )

    positions = range(len(rows))
    bar_width = 0.35

    axes[0].bar(
        [position - bar_width / 2 for position in positions],
        average_latency,
        width=bar_width,
        label="Average latency",
        color="#3674B5",
    )

    axes[0].bar(
        [position + bar_width / 2 for position in positions],
        p95_latency,
        width=bar_width,
        label="95th-percentile latency",
        color="#D95F59",
    )

    axes[0].set_title("Pipeline Processing Latency")
    axes[0].set_xlabel("Publication interval")
    axes[0].set_ylabel("Latency (ms)")
    axes[0].set_xticks(list(positions))
    axes[0].set_xticklabels(interval_labels)
    axes[0].legend()
    axes[0].grid(
        axis="y",
        linestyle="--",
        alpha=0.4,
    )

    throughput_bars = axes[1].bar(
        interval_labels,
        throughput,
        color="#4C956C",
    )

    axes[1].set_title("Observed Pipeline Throughput")
    axes[1].set_xlabel("Publication interval")
    axes[1].set_ylabel("Processed messages per second")
    axes[1].grid(
        axis="y",
        linestyle="--",
        alpha=0.4,
    )

    axes[1].bar_label(
        throughput_bars,
        fmt="%.3f",
        padding=3,
    )

    figure.suptitle(
        "SDV Pipeline Performance Comparison",
        fontsize=14,
        fontweight="bold",
    )

    figure.tight_layout()
    figure.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight",
    )

    print(f"Chart created: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_chart()