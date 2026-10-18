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
}


def create_scenario_controller():
    controller = ScenarioController()

    if INITIAL_FAULT_MODE:
        controller.execute(
            vehicle_id=SIMULATED_VEHICLE_ID,
            action="INJECT_SCENARIO",
            scenario=COOLING_FAILURE,
            action_id="startup-fault",
            trace_id="startup-fault",
        )

    return controller


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
                fault_active = controller.is_active(
                    vehicle_id=SIMULATED_VEHICLE_ID,
                    scenario=COOLING_FAILURE,
                )

                state = next_state(
                    state,
                    fault=fault_active,
                )

                client.set_current_values(
                    {
                        path: Datapoint(state[key])
                        for key, path
                        in SIGNAL_PATHS.items()
                    }
                )

                timestamp = datetime.now().isoformat()
                mode = (
                    "FAULT"
                    if fault_active
                    else "normal"
                )

                print(
                    f"[{timestamp}] "
                    f"vehicle={SIMULATED_VEHICLE_ID} "
                    f"mode={mode} "
                    f"interval="
                    f"{PUBLISH_INTERVAL_SECONDS} "
                    + " ".join(
                        f"{key}={value:.1f}"
                        for key, value
                        in state.items()
                    )
                )

                time.sleep(
                    PUBLISH_INTERVAL_SECONDS
                )
    finally:
        control_server.shutdown()
        control_server.server_close()


if __name__ == "__main__":
    main()