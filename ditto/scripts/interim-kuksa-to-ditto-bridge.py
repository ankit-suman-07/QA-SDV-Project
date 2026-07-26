import os
import sys
import time
from pathlib import Path

import requests
from kuksa_client.grpc import VSSClient
from datetime import datetime, timezone

_REPO_ROOT = Path(__file__).resolve().parents[2]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.pipeline_evaluator import PipelineEvaluator
from experiments.result_summary import summarize_records
from uprotocol.transport import (
    publish_vehicle_status,
    receive_vehicle_status,
)

DITTO_URL = "http://localhost:8080/api/2/things/sdv:vehicle-001"
AUTH = ("ditto", "ditto")
HEADERS = {"Content-Type": "application/json"}

EXPERIMENT_ID = os.getenv(
    "EXPERIMENT_ID",
    "pipeline-evaluation",
)

PUBLICATION_INTERVAL_SECONDS = float(
    os.getenv("PUBLISH_INTERVAL_SECONDS", "5.0")
)

EXPERIMENT_EVENT_LIMIT = int(
    os.getenv("EXPERIMENT_EVENT_LIMIT", "30")
)

RESULTS_FILE = os.getenv(
    "EXPERIMENT_RESULTS_FILE",
    f"experiments/results/{EXPERIMENT_ID}.csv",
)

BATTERY_LOW_THRESHOLD = 20
BATTERY_RECOVER_THRESHOLD = 25

PATHS = {
    "speed": "Vehicle.Speed",
    "battery":
        "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
    "temperature":
        "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature",
    "tire_fl":
        "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure",
}

evaluator = PipelineEvaluator(
    experiment_id=EXPERIMENT_ID,
    publication_interval_seconds=(
        PUBLICATION_INTERVAL_SECONDS
    ),
)

completed_event_count = 0
experiment_start_time = time.perf_counter()

print(
    f"[Experiment] id={EXPERIMENT_ID} "
    f"interval={PUBLICATION_INTERVAL_SECONDS}s "
    f"eventLimit={EXPERIMENT_EVENT_LIMIT}"
)

with VSSClient("127.0.0.1", 55556) as client:
    fault_active = False

    while True:
        values = client.get_current_values(
            list(PATHS.values())
        )

        speed = values[PATHS["speed"]].value or 0
        battery = values[PATHS["battery"]].value
        temperature = (
            values[PATHS["temperature"]].value or 0
        )
        tire_fl = values[PATHS["tire_fl"]].value or 0

        if battery is None:
            print(
                "[wait] no battery value published yet, "
                "retrying..."
            )
            time.sleep(2)
            continue

        pipeline_start_time = time.perf_counter()
        serialized_event = publish_vehicle_status(
            vehicle_id="vehicle-001",
            speed_kph=float(speed),
            battery_percent=float(battery),
            temperature_celsius=float(temperature),
            tire_pressure_psi=float(tire_fl),
        )

        received_event = receive_vehicle_status(
            serialized_event
        )

        event_id = received_event.metadata.event_id

        evaluator.start_event(
            event_id=event_id,
            start_time=pipeline_start_time,
        )

        speed = received_event.speed_kph
        battery = received_event.battery_percent
        temperature = received_event.temperature_celsius
        tire_fl = (
            received_event.tire_pressure_psi.front_left
        )

        if (
                battery < BATTERY_LOW_THRESHOLD
                and not fault_active
        ):
            fault_active = True
            print(
                f"[Rule] battery={battery:.1f} "
                f"< {BATTERY_LOW_THRESHOLD} "
                "-> WARNING, BATTERY_LOW"
            )

        elif (
                battery >= BATTERY_RECOVER_THRESHOLD
                and fault_active
        ):
            fault_active = False
            print(
                f"[Rule] battery={battery:.1f} "
                f">= {BATTERY_RECOVER_THRESHOLD} "
                "-> HEALTHY, fault cleared"
            )

        health_status = (
            "WARNING" if fault_active else "HEALTHY"
        )

        active_faults = (
            ["BATTERY_LOW"] if fault_active else []
        )

        processed_timestamp = (
            datetime.now(timezone.utc).isoformat()
        )

        ditto_updates = [
            (
                (
                    f"{DITTO_URL}/features/signals/"
                    "properties/speedKph"
                ),
                speed,
            ),
            (
                (
                    f"{DITTO_URL}/features/signals/"
                    "properties/batteryPercent"
                ),
                round(battery, 1),
            ),
            (
                (
                    f"{DITTO_URL}/features/signals/"
                    "properties/temperatureCelsius"
                ),
                temperature,
            ),
            (
                (
                    f"{DITTO_URL}/features/signals/properties/"
                    "tirePressurePsi/frontLeft"
                ),
                tire_fl,
            ),
            (
                (
                    f"{DITTO_URL}/features/signals/"
                    "properties/sourceTimestamp"
                ),
                received_event.metadata.source_timestamp,
            ),
            (
                (
                    f"{DITTO_URL}/features/health/"
                    "properties/status"
                ),
                health_status,
            ),
            (
                (
                    f"{DITTO_URL}/features/health/"
                    "properties/activeFaults"
                ),
                active_faults,
            ),
            (
                (
                    f"{DITTO_URL}/features/health/"
                    "properties/faultCount"
                ),
                len(active_faults),
            ),
            (
                (
                    f"{DITTO_URL}/features/health/"
                    "properties/processedTimestamp"
                ),
                processed_timestamp,
            ),
        ]

        responses = [
            requests.put(
                url,
                json=value,
                auth=AUTH,
                headers=HEADERS,
                timeout=5,
            )
            for url, value in ditto_updates
        ]

        ditto_success = all(
            response.ok for response in responses
        )

        record = evaluator.complete_event(
            event_id=event_id,
            success=ditto_success,
            health_status=health_status,
        )

        completed_event_count += 1

        print(
            f"[Metrics] eventId={event_id} "
            f"latencyMs={record['latency_ms']:.3f} "
            f"success={ditto_success}"
        )

        print(
            f"[Ditto] speed={speed} "
            f"battery={battery:.1f} "
            f"temp={temperature} "
            f"tireFL={tire_fl} "
            f"health={health_status}"
        )

        if completed_event_count >= EXPERIMENT_EVENT_LIMIT:
            experiment_duration = (
                time.perf_counter()
                - experiment_start_time
            )

            results_path = Path(RESULTS_FILE)

            if not results_path.is_absolute():
                results_path = _REPO_ROOT / results_path

            evaluator.recorder.export_csv(
                results_path
            )

            summary = summarize_records(
                records=evaluator.recorder.records,
                experiment_duration_seconds=(
                    experiment_duration
                ),
            )

            print(
                f"[Experiment Complete] "
                f"results={results_path}"
            )

            print(
                f"[Summary] "
                f"messages={summary['total_messages']} "
                f"successRate="
                f"{summary['success_rate_percent']:.2f}% "
                f"averageLatencyMs="
                f"{summary['average_latency_ms']:.3f} "
                f"p95LatencyMs="
                f"{summary['p95_latency_ms']:.3f} "
                f"throughput="
                f"{summary['throughput_messages_per_second']:.3f}"
            )

            break

        time.sleep(
            PUBLICATION_INTERVAL_SECONDS
        )