import os
import sys
import time
from datetime import datetime, timezone
from ditto.ditto_http import put_json_with_retry
from pathlib import Path

import requests
from kuksa_client.grpc import VSSClient

_REPO_ROOT = Path(__file__).resolve().parents[2]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ditto.fault_details import (
    build_active_fault_detail,
    is_activation_condition,
    is_recovery_condition,
)
from experiments.pipeline_evaluator import PipelineEvaluator
from experiments.result_summary import summarize_records
from uprotocol.transport import (
    publish_correlated_fault_cleared,
    publish_correlated_fault_detected,
    publish_vehicle_status,
    receive_correlated_fault_cleared,
    receive_correlated_fault_detected,
    receive_vehicle_status,
    vehicle_diagnostic_pb2,
    vehicle_fault_pb2,
)

DITTO_URL = (
    "http://localhost:8080/api/2/things/"
    "sdv:vehicle-001"
)

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
    (
        f"experiments/results/"
        f"{EXPERIMENT_ID}.csv"
    ),
)

BATTERY_LOW_THRESHOLD = 20.0
BATTERY_RECOVER_THRESHOLD = 25.0

PATHS = {
    "speed": "Vehicle.Speed",
    "battery": (
        "Vehicle.Powertrain.TractionBattery."
        "StateOfCharge.Current"
    ),
    "temperature": (
        "Vehicle.Powertrain.CombustionEngine."
        "EngineCoolant.Temperature"
    ),
    "tire_fl": (
        "Vehicle.Chassis.Axle.Row1.Wheel.Left."
        "Tire.Pressure"
    ),
    "coolant_pressure": (
        "Vehicle.Powertrain.CombustionEngine."
        "EngineCoolant.Pressure"
    ),
}


def optional_action_id(metadata):
    try:
        if metadata.HasField("action_id"):
            return metadata.action_id
    except ValueError:
        pass

    return None


def put_ditto_property(path, value):
    return put_json_with_retry(
        url=f"{DITTO_URL}/{path}",
        value=value,
        auth=AUTH,
        headers=HEADERS,
        attempts=3,
        timeout_seconds=5,
        retry_delay_seconds=0.2,
    )


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
    battery_fault_active = False
    cooling_fault_active = False
    active_fault_details = []

    while True:
        values = client.get_current_values(
            list(PATHS.values())
        )

        speed = values[PATHS["speed"]].value
        battery = values[PATHS["battery"]].value
        temperature = values[
            PATHS["temperature"]
        ].value
        tire_fl = values[PATHS["tire_fl"]].value
        coolant_pressure = values[
            PATHS["coolant_pressure"]
        ].value

        required_values = (
            speed,
            battery,
            temperature,
            tire_fl,
            coolant_pressure,
        )

        if any(
            value is None
            for value in required_values
        ):
            print(
                "[wait] required Kuksa values have "
                "not been published yet, retrying..."
            )
            time.sleep(2)
            continue

        pipeline_start_time = time.perf_counter()

        serialized_event = publish_vehicle_status(
            vehicle_id="vehicle-001",
            speed_kph=float(speed),
            battery_percent=float(battery),
            temperature_celsius=float(
                temperature
            ),
            coolant_pressure_kpa=float(
                coolant_pressure
            ),
            tire_pressure_psi=float(tire_fl),
        )

        received_event = receive_vehicle_status(
            serialized_event
        )

        event_id = received_event.metadata.event_id
        trace_id = received_event.metadata.trace_id
        action_id = optional_action_id(
            received_event.metadata
        )

        evaluator.start_event(
            event_id=event_id,
            start_time=pipeline_start_time,
        )

        signals = received_event.signals

        speed = signals.speed_kph
        battery = signals.battery_percent
        temperature = signals.temperature_celsius
        coolant_pressure = (
            signals.coolant_pressure_kpa
        )
        tire_fl = (
            signals.tire_pressure_psi.front_left
        )

        processed_timestamp = (
            datetime.now(timezone.utc).isoformat()
        )

        if (
            battery < BATTERY_LOW_THRESHOLD
            and not battery_fault_active
        ):
            battery_fault_active = True

            print(
                f"[Rule] battery={battery:.1f} "
                f"< {BATTERY_LOW_THRESHOLD:.1f} "
                "-> WARNING, BATTERY_LOW"
            )

        elif (
            battery >= BATTERY_RECOVER_THRESHOLD
            and battery_fault_active
        ):
            battery_fault_active = False

            print(
                f"[Rule] battery={battery:.1f} "
                f">= {BATTERY_RECOVER_THRESHOLD:.1f} "
                "-> BATTERY_LOW cleared"
            )

        if (
            not cooling_fault_active
            and is_activation_condition(
                temperature_celsius=temperature,
                coolant_pressure_kpa=(
                    coolant_pressure
                ),
            )
        ):
            cooling_fault_active = True

            fault_payload, _ = (
                publish_correlated_fault_detected(
                    vehicle_id="vehicle-001",
                    fault_code=(
                        vehicle_diagnostic_pb2
                        .COOLING_SYSTEM_FAILURE
                    ),
                    description=(
                        "High temperature correlated "
                        "with low coolant pressure"
                    ),
                    severity=(
                        vehicle_fault_pb2
                        .FAULT_CRITICAL
                    ),
                    affected_signals=[
                        "temperatureCelsius",
                        "coolantPressureKpa",
                    ],
                    observed_values={
                        "temperatureCelsius": (
                            float(temperature)
                        ),
                        "coolantPressureKpa": (
                            float(coolant_pressure)
                        ),
                    },
                    activation_thresholds={
                        "temperatureCelsius": 105.0,
                        "coolantPressureKpa": 150.0,
                    },
                    trace_id=trace_id,
                    action_id=action_id,
                )
            )

            fault_event = (
                receive_correlated_fault_detected(
                    fault_payload
                )
            )

            fault_action_id = optional_action_id(
                fault_event.metadata
            )

            active_fault_details = [
                build_active_fault_detail(
                    temperature_celsius=(
                        temperature
                    ),
                    coolant_pressure_kpa=(
                        coolant_pressure
                    ),
                    detected_at=(
                        fault_event.detected_at
                    ),
                    event_id=(
                        fault_event.metadata.event_id
                    ),
                    trace_id=(
                        fault_event.metadata.trace_id
                    ),
                    action_id=fault_action_id,
                )
            ]

            print(
                "[Rule] correlated cooling fault "
                "detected -> CRITICAL, "
                "COOLING_SYSTEM_FAILURE"
            )

        elif (
            cooling_fault_active
            and is_recovery_condition(
                temperature_celsius=temperature,
                coolant_pressure_kpa=(
                    coolant_pressure
                ),
            )
        ):
            cleared_payload = (
                publish_correlated_fault_cleared(
                    vehicle_id="vehicle-001",
                    fault_code=(
                        vehicle_diagnostic_pb2
                        .COOLING_SYSTEM_FAILURE
                    ),
                    affected_signals=[
                        "temperatureCelsius",
                        "coolantPressureKpa",
                    ],
                    observed_values={
                        "temperatureCelsius": (
                            float(temperature)
                        ),
                        "coolantPressureKpa": (
                            float(coolant_pressure)
                        ),
                    },
                    recovery_thresholds={
                        "temperatureCelsius": 100.0,
                        "coolantPressureKpa": 180.0,
                    },
                    trace_id=trace_id,
                    action_id=action_id,
                )
            )

            receive_correlated_fault_cleared(
                cleared_payload
            )

            cooling_fault_active = False
            active_fault_details = []

            print(
                "[Rule] correlated cooling fault "
                "cleared -> recovery thresholds met"
            )

        active_faults = []

        if battery_fault_active:
            active_faults.append("BATTERY_LOW")

        if cooling_fault_active:
            active_faults.append(
                "COOLING_SYSTEM_FAILURE"
            )

        if cooling_fault_active:
            health_status = "CRITICAL"
        elif battery_fault_active:
            health_status = "WARNING"
        else:
            health_status = "HEALTHY"

        ditto_updates = [
            (
                (
                    "features/signals/properties/"
                    "speedKph"
                ),
                speed,
            ),
            (
                (
                    "features/signals/properties/"
                    "batteryPercent"
                ),
                round(battery, 1),
            ),
            (
                (
                    "features/signals/properties/"
                    "temperatureCelsius"
                ),
                temperature,
            ),
            (
                (
                    "features/signals/properties/"
                    "coolantPressureKpa"
                ),
                coolant_pressure,
            ),
            (
                (
                    "features/signals/properties/"
                    "tirePressurePsi/frontLeft"
                ),
                tire_fl,
            ),
            (
                (
                    "features/signals/properties/"
                    "sourceTimestamp"
                ),
                (
                    received_event
                    .metadata
                    .source_timestamp
                ),
            ),
            (
                (
                    "features/health/properties/"
                    "status"
                ),
                health_status,
            ),
            (
                (
                    "features/health/properties/"
                    "activeFaults"
                ),
                active_faults,
            ),
            (
                (
                    "features/health/properties/"
                    "faultCount"
                ),
                len(active_faults),
            ),
            (
                (
                    "features/health/properties/"
                    "processedTimestamp"
                ),
                processed_timestamp,
            ),
            (
                (
                    "features/diagnostics/"
                    "properties/activeFaultDetails"
                ),
                active_fault_details,
            ),
        ]

        responses = [
            put_ditto_property(path, value)
            for path, value in ditto_updates
        ]

        ditto_success = all(
            response is not None and response.ok
            for response in responses
        )

        if not ditto_success:
            failed_responses = [
                (
                    "NO_RESPONSE",
                    "Ditto request failed after retries",
                )
                if response is None
                else (
                    response.status_code,
                    response.text,
                )
                for response in responses
                if response is None or not response.ok
            ]

            print(
                "[Ditto Error] "
                f"{failed_responses}"
            )

        record = evaluator.complete_event(
            event_id=event_id,
            success=ditto_success,
            health_status=health_status,
        )

        completed_event_count += 1

        print(
            f"[Metrics] eventId={event_id} "
            f"latencyMs="
            f"{record['latency_ms']:.3f} "
            f"success={ditto_success}"
        )

        print(
            f"[Ditto] speed={speed:.1f} "
            f"battery={battery:.1f} "
            f"temp={temperature:.1f} "
            f"coolantPressure="
            f"{coolant_pressure:.1f} "
            f"tireFL={tire_fl:.1f} "
            f"health={health_status} "
            f"faults={active_faults}"
        )

        if (
            completed_event_count
            >= EXPERIMENT_EVENT_LIMIT
        ):
            experiment_duration = (
                time.perf_counter()
                - experiment_start_time
            )

            results_path = Path(RESULTS_FILE)

            if not results_path.is_absolute():
                results_path = (
                    _REPO_ROOT / results_path
                )

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
                "[Experiment Complete] "
                f"results={results_path}"
            )

            print(
                "[Summary] "
                f"messages="
                f"{summary['total_messages']} "
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