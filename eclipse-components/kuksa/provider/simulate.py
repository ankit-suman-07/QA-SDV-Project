import os
import random
import time
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get("DATABROKER_HOST", "127.0.0.1")
port = int(os.environ.get("DATABROKER_PORT", 55555))

from kuksa_client.grpc import VSSClient, Datapoint

FAULT_MODE = os.getenv('INJECT_FAULT') == '1'

with VSSClient(host, port) as client:
    speed = 100.0
    battery = 80.0
    engine_temp = 90.0
    tire_pressure = 32.0

    print(f"Fault Mode: {FAULT_MODE}")
    while True:
        if FAULT_MODE:
            engine_temp = min(150, engine_temp + random.uniform(0.5, 1.5))
            battery = max(0, battery - random.uniform(0.5, 1.5))
            tire_pressure = max(0, tire_pressure - random.uniform(0.1, 0.3))
            speed = max(0, speed + random.uniform(-1, 1))

        else:
            engine_temp = min(95, max(85, engine_temp + random.uniform(-0.5, 0.5)))
            battery = min(100, max(40, battery + random.uniform(-0.2, 0.2)))
            tire_pressure = min(34, max(30, tire_pressure + random.uniform(-0.1, 0.1)))
            speed = min(120, max(0, speed + random.uniform(-2, 2)))

        client.set_current_values({
            'Vehicle.Speed': Datapoint(speed),
            'Vehicle.Powertrain.TractionBattery.StateOfCharge.Current': Datapoint(battery),
            'Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature': Datapoint(engine_temp),
            'Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure': Datapoint(tire_pressure),
        })
        time.sleep(5)
        print(f"speed={speed:.1f} battery={battery:.1f}% ect={engine_temp:.1f} tire={tire_pressure:.1f}")