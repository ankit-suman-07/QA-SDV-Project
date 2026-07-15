import random

NORMAL_RANGES = {
    "speed": (0, 120),
    "battery": (40, 100),
    "engine_temp": (85, 95),
    "tire_pressure": (30, 34),
}

def initial_state():
    return {
        "speed": 60.0,
        "battery": 80.0,
        "engine_temp": 90.0,
        "tire_pressure": 32.0,
    }

def next_state(state, fault=False):
    if fault:
        return {
            "speed": max(0, state["speed"] + random.uniform(-1, 1)),
            "battery": max(0, state["battery"] - random.uniform(0.5, 1.5)),
            "engine_temp": min(150, state["engine_temp"] + random.uniform(0.5, 1.5)),
            "tire_pressure": max(0, state["tire_pressure"] - random.uniform(0.1, 0.3)),
        }

    lo, hi = NORMAL_RANGES["speed"]
    speed = min(hi, max(lo, state["speed"] + random.uniform(-3, 5)))

    lo, hi = NORMAL_RANGES["battery"]
    battery = min(hi, max(lo, state["battery"] + random.uniform(-0.2, 0.7)))

    lo, hi = NORMAL_RANGES["engine_temp"]
    engine_temp = min(hi, max(lo, state["engine_temp"] + random.uniform(-0.5, 0.5)))

    lo, hi = NORMAL_RANGES["tire_pressure"]
    tire_pressure = min(hi, max(lo, state["tire_pressure"] + random.uniform(-0.1, 0.1)))

    return {
        "speed": speed,
        "battery": battery,
        "engine_temp": engine_temp,
        "tire_pressure": tire_pressure,
    }