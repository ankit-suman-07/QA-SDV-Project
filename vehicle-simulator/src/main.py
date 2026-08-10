import os
import time
from datetime import datetime

from dotenv import load_dotenv
from kuksa_client.grpc import Datapoint

from get_kuksa_client import get_client
from signal_generator import initial_state, next_state, parse_interval

load_dotenv()

FAULT_MODE = os.getenv("INJECT_FAULT") == "1"
raw = os.getenv("PUBLISH_INTERVAL_SECONDS")
PUBLISH_INTERVAL_SECONDS = parse_interval(raw) if raw is not None else 5.0

SIGNAL_PATHS = {
    "speed": "Vehicle.Speed",
    "battery": "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
    "engine_temp": "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature",
    "tire_pressure": "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure",
    "coolant_pressure": "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Pressure",
}

def main():
    state = initial_state()
    if FAULT_MODE:
        state["battery"] = 15.0
    with get_client() as client:
        while True:
            state = next_state(state, fault=FAULT_MODE)

            client.set_current_values({
                path: Datapoint(state[key]) for key, path in SIGNAL_PATHS.items()
            })

            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] mode={'FAULT' if FAULT_MODE else 'normal'} interval={PUBLISH_INTERVAL_SECONDS} " +
                  " ".join(f"{k}={v:.1f}" for k, v in state.items()))

            time.sleep(PUBLISH_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()