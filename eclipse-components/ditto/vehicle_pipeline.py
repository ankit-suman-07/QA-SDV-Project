import time
import requests
from kuksa_client.grpc import VSSClient

from uprotocol_transport import (
    publish_vehicle_status,
    receive_vehicle_status,
)

DITTO_URL = "http://localhost:8080/api/2/things/sdv:vehicle-001"
AUTH = ("ditto", "ditto")
HEADERS = {"Content-Type": "application/json"}

BATTERY_LOW_THRESHOLD = 20
BATTERY_RECOVER_THRESHOLD = 25

PATHS = {
    "speed": "Vehicle.Speed",
    "battery": "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
    "temperature": "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature",
    "tire_fl": "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure",
}

with VSSClient("127.0.0.1", 55556) as client:
    fault_active = False
    while True:
        values = client.get_current_values(list(PATHS.values()))

        speed = values[PATHS["speed"]].value or 0
        battery = values[PATHS["battery"]].value
        temperature = values[PATHS["temperature"]].value or 0
        tire_fl = values[PATHS["tire_fl"]].value or 0

        if battery is None:
            print("[wait] no battery value published yet, retrying...")
            time.sleep(2)
            continue

        serialized_event = publish_vehicle_status(
            vehicle_id="vehicle-001",
            speed_kph=float(speed),
            battery_percent=float(battery),
            temperature_celsius=float(temperature),
            tire_pressure_psi=float(tire_fl),
        )

        received_event = receive_vehicle_status(serialized_event)

        speed = received_event.speed_kph
        battery = received_event.battery_percent
        temperature = received_event.temperature_celsius
        tire_fl = received_event.tire_pressure_psi.front_left

        if battery < BATTERY_LOW_THRESHOLD and not fault_active:
            fault_active = True
            print(f"[Rule] battery={battery:.1f} < {BATTERY_LOW_THRESHOLD} -> WARNING, BATTERY_LOW")
        elif battery >= BATTERY_RECOVER_THRESHOLD and fault_active:
            fault_active = False
            print(f"[Rule] battery={battery:.1f} >= {BATTERY_RECOVER_THRESHOLD} -> HEALTHY, fault cleared")

        health_status = "WARNING" if fault_active else "HEALTHY"
        active_faults = ["BATTERY_LOW"] if fault_active else []

        requests.put(f"{DITTO_URL}/features/signals/properties/speedKph", json=speed, auth=AUTH, headers=HEADERS)
        requests.put(f"{DITTO_URL}/features/signals/properties/batteryPercent", json=round(battery, 1), auth=AUTH, headers=HEADERS)
        requests.put(f"{DITTO_URL}/features/signals/properties/temperatureCelsius", json=temperature, auth=AUTH, headers=HEADERS)
        requests.put(f"{DITTO_URL}/features/signals/properties/tirePressurePsi/frontLeft", json=tire_fl, auth=AUTH, headers=HEADERS)
        requests.put(f"{DITTO_URL}/features/health/properties/status", json=health_status, auth=AUTH, headers=HEADERS)
        requests.put(f"{DITTO_URL}/features/health/properties/activeFaults", json=active_faults, auth=AUTH, headers=HEADERS)

        print(f"[Ditto] speed={speed} battery={battery:.1f} temp={temperature} tireFL={tire_fl} health={health_status}")
        time.sleep(2)