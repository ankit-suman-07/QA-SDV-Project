import os
import time
from datetime import datetime

from dotenv import load_dotenv
from kuksa_client.grpc import Datapoint

from control_server import start_control_server
from get_kuksa_client import get_client
from scenario_controller import ScenarioController
from signal_generator import (
    initial_state,
    next_state,
    parse_interval,
)

load_dotenv()

SIMULATED_VEHICLE_ID = os.getenv(
    "SIMULATED_VEHICLE_ID",
    "vehicle-001",
).strip()

if not SIMULATED_VEHICLE_ID:
    raise ValueError(
        "SIMULATED_VEHICLE_ID must not be blank"
    )

INITIAL_FAULT_MODE = os.getenv("INJECT_FAULT") == "1"

raw_interval = os.getenv("PUBLISH_INTERVAL_SECONDS")
PUBLISH_INTERVAL_SECONDS = (
    parse_interval(raw_interval)
    if raw_interval is not None
    else 5.0
)

CONTROL_HOST = os.getenv(
    "SIMULATOR_CONTROL_HOST",
    "0.0.0.0",
)

CONTROL_PORT = int(
    os.getenv(
        "SIMULATOR_CONTROL_PORT",
        "8090",
    )
)

COOLING_FAILURE = "COOLING_SYSTEM_FAILURE"
LIDAR_OBSTRUCTION = "LIDAR_OBSTRUCTION"
LIDAR_SENSOR_FAILURE = "LIDAR_SENSOR_FAILURE"

SIGNAL_PATHS = {
    "speed": "Vehicle.Speed",
    "battery": (
        "Vehicle.Powertrain.TractionBattery."
        "StateOfCharge.Current"
    ),
    "engine_temp": (
        "Vehicle.Powertrain.CombustionEngine."
        "EngineCoolant.Temperature"
    ),
    "tire_pressure": (
        "Vehicle.Chassis.Axle.Row1.Wheel.Left."
        "Tire.Pressure"
    ),
    "coolant_pressure": (
        "Vehicle.Powertrain.CombustionEngine."
        "EngineCoolant.Pressure"
    ),
    "lidar_distance_m": (
        "Vehicle.Automation.Lidar.Front."
        "NearestObstacleDistance"
    ),
    "lidar_sensor_healthy": (
        "Vehicle.Automation.Lidar.Front.IsHealthy"
    ),
    "obstacle_warning": (
        "Vehicle.Automation.ObstacleWarning.IsActive"
    ),
    "autonomous_braking": (
        "Vehicle.Automation.AutonomousBraking.IsActive"
    ),
}


def create_scenario_controller():
    controller = ScenarioController(
        allowed_vehicle_id=SIMULATED_VEHICLE_ID,
    )

    if INITIAL_FAULT_MODE:
        controller.execute(
            vehicle_id=SIMULATED_VEHICLE_ID,
            action="INJECT_SCENARIO",
            scenario=COOLING_FAILURE,
            action_id="startup-fault",
            trace_id="startup-fault",
        )

    return controller


def scenario_is_active(controller, scenario):
    return controller.is_active(
        vehicle_id=SIMULATED_VEHICLE_ID,
        scenario=scenario,
    )


def describe_modes(
    cooling_failure,
    lidar_obstruction,
    lidar_failure,
):
    active_modes = []

    if cooling_failure:
        active_modes.append("COOLING_FAILURE")

    if lidar_obstruction:
        active_modes.append("LIDAR_OBSTRUCTION")

    if lidar_failure:
        active_modes.append("LIDAR_FAILURE")

    if not active_modes:
        return "normal"

    return ",".join(active_modes)


def format_signal_value(key, value):
    if isinstance(value, bool):
        return f"{key}={str(value).lower()}"

    return f"{key}={value:.1f}"


def publication_values(state):
    """Generator tire state is psi; VSS Tire.Pressure is uint16 kPa.

    Quantize once at the source boundary, never mutate/reconvert simulator state.
    """
    values = {path: Datapoint(state[key]) for key, path in SIGNAL_PATHS.items()}
    values[SIGNAL_PATHS["tire_pressure"]] = Datapoint(
        round(state["tire_pressure"] * 6.894757293168)
    )
    return values


def main():
    controller = create_scenario_controller()

    control_server = start_control_server(
        controller=controller,
        host=CONTROL_HOST,
        port=CONTROL_PORT,
    )

    print(
        f"[Control] vehicle={SIMULATED_VEHICLE_ID} "
        f"listening on {CONTROL_HOST}:{CONTROL_PORT}"
    )

    state = initial_state()

    try:
        with get_client() as client:
            while True:
                cooling_failure = scenario_is_active(
                    controller,
                    COOLING_FAILURE,
                )

                lidar_obstruction = scenario_is_active(
                    controller,
                    LIDAR_OBSTRUCTION,
                )

                lidar_failure = scenario_is_active(
                    controller,
                    LIDAR_SENSOR_FAILURE,
                )

                state = next_state(
                    state,
                    fault=cooling_failure,
                    obstacle=lidar_obstruction,
                    lidar_failure=lidar_failure,
                )

                client.set_current_values(
                    publication_values(state)
                )

                timestamp = datetime.now().isoformat()
                mode = describe_modes(
                    cooling_failure,
                    lidar_obstruction,
                    lidar_failure,
                )

                signal_summary = " ".join(
                    format_signal_value(key, value)
                    for key, value in state.items()
                )

                print(
                    f"[{timestamp}] "
                    f"vehicle={SIMULATED_VEHICLE_ID} "
                    f"mode={mode} "
                    f"interval={PUBLISH_INTERVAL_SECONDS} "
                    f"{signal_summary}"
                )

                time.sleep(
                    PUBLISH_INTERVAL_SECONDS
                )
    finally:
        control_server.shutdown()
        control_server.server_close()


if __name__ == "__main__":
    main()