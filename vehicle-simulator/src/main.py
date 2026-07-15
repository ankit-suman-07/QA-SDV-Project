import os
import time
from dotenv import load_dotenv
from kuksa_client.grpc import Datapoint

from get_kuksa_client import get_client
from signal_generator import initial_state, next_state

load_dotenv()

FAULT_MODE = os.getenv("INJECT_FAULT") == "1"

SIGNAL_PATHS = {
    "speed": "Vehicle.Speed",
    "battery": "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
    "engine_temp": "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature",
    "tire_pressure": "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure",
}

def main():
    state = initial_state()
    with get_client() as client:
        while True:
            state = next_state(state, fault=FAULT_MODE)

            client.set_current_values({
                path: Datapoint(state[key]) for key, path in SIGNAL_PATHS.items()
            })

            print(f"[{'FAULT' if FAULT_MODE else 'normal'}] " +
                  " ".join(f"{k}={v:.1f}" for k, v in state.items()))

            time.sleep(5)

if __name__ == "__main__":
    main()