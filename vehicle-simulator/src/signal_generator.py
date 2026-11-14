import random

from lidar_trajectory import distance, next_step


NORMAL_LIDAR_DISTANCE_M = 35.0
LIDAR_WARNING_DISTANCE_M = 10.0
AUTONOMOUS_BRAKING_DISTANCE_M = 5.0

NORMAL_RANGES = {
    "speed": (0, 120),
    "battery": (40, 100),
    "engine_temp": (85, 95),
    "tire_pressure": (30, 34),
    "coolant_pressure": (180, 220),
    "lidar_distance_m": (12, 80),
}


def initial_state():
    return {
        "speed": 60.0,
        "battery": 80.0,
        "engine_temp": 90.0,
        "tire_pressure": 32.0,
        "coolant_pressure": 200.0,
        "lidar_distance_m": NORMAL_LIDAR_DISTANCE_M,
        "lidar_step": 0,
        "lidar_sensor_healthy": True,
        "obstacle_warning": False,
        "autonomous_braking": False,
    }


def next_state(
    state,
    fault=False,
    obstacle=False,
    lidar_failure=False,
):
    (
        lidar_distance,
        lidar_step,
        lidar_sensor_healthy,
        obstacle_warning,
        autonomous_braking,
    ) = _next_lidar_state(
        state,
        obstacle=obstacle,
        lidar_failure=lidar_failure,
    )

    speed = _next_speed(
        state["speed"],
        cooling_fault=fault,
        autonomous_braking=autonomous_braking,
    )

    if fault:
        battery = max(
            0,
            state["battery"]
            - random.uniform(0.5, 1.5),
        )

        engine_temp = min(
            150,
            state["engine_temp"]
            + random.uniform(0.5, 1.5),
        )

        tire_pressure = max(
            0,
            state["tire_pressure"]
            - random.uniform(0.1, 0.3),
        )

        coolant_pressure = max(
            100,
            state["coolant_pressure"]
            - random.uniform(2, 5),
        )
    else:
        battery = _bounded_random_change(
            state["battery"],
            "battery",
            -0.2,
            0.7,
        )

        engine_temp = _bounded_random_change(
            state["engine_temp"],
            "engine_temp",
            -0.5,
            0.5,
        )

        tire_pressure = _bounded_random_change(
            state["tire_pressure"],
            "tire_pressure",
            -0.1,
            0.1,
        )

        coolant_pressure = _recover_coolant_pressure(
            state["coolant_pressure"]
        )

    return {
        "speed": speed,
        "battery": battery,
        "engine_temp": engine_temp,
        "tire_pressure": tire_pressure,
        "coolant_pressure": coolant_pressure,
        "lidar_distance_m": lidar_distance,
        "lidar_step": lidar_step,
        "lidar_sensor_healthy": lidar_sensor_healthy,
        "obstacle_warning": obstacle_warning,
        "autonomous_braking": autonomous_braking,
    }


def _next_speed(
    current_speed,
    cooling_fault,
    autonomous_braking,
):
    if autonomous_braking:
        return max(
            0,
            current_speed - random.uniform(8, 15),
        )

    if cooling_fault:
        return max(
            0,
            current_speed + random.uniform(-1, 1),
        )

    lo, hi = NORMAL_RANGES["speed"]

    return min(
        hi,
        max(
            lo,
            current_speed + random.uniform(-3, 5),
        ),
    )


def _next_lidar_state(
    state,
    obstacle,
    lidar_failure,
):
    # The ladder rung is kept separately from the published distance, so a
    # sensor failure pauses the scenario instead of resetting it.
    lidar_step = state.get("lidar_step", 0)

    if lidar_failure:
        lidar_distance = 0.0
        lidar_sensor_healthy = False
    else:
        lidar_step = next_step(lidar_step, obstacle)
        lidar_distance = distance(lidar_step)
        lidar_sensor_healthy = True

    obstacle_warning = (
        not lidar_sensor_healthy
        or lidar_distance <= LIDAR_WARNING_DISTANCE_M
    )

    autonomous_braking = (
        not lidar_sensor_healthy
        or lidar_distance
        <= AUTONOMOUS_BRAKING_DISTANCE_M
    )

    return (
        lidar_distance,
        lidar_step,
        lidar_sensor_healthy,
        obstacle_warning,
        autonomous_braking,
    )


def _bounded_random_change(
    current_value,
    range_name,
    minimum_change,
    maximum_change,
):
    lo, hi = NORMAL_RANGES[range_name]

    return min(
        hi,
        max(
            lo,
            current_value
            + random.uniform(
                minimum_change,
                maximum_change,
            ),
        ),
    )


def _recover_coolant_pressure(current_pressure):
    if current_pressure < 200:
        return min(
            200,
            current_pressure + random.uniform(2, 5),
        )

    return _bounded_random_change(
        current_pressure,
        "coolant_pressure",
        -1,
        1,
    )


def parse_interval(raw_value, default=5.0):
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(
            "Invalid PUBLISH_INTERVAL_SECONDS: "
            f"{raw_value!r} is not numeric"
        )

    if value <= 0:
        raise ValueError(
            "Invalid PUBLISH_INTERVAL_SECONDS: "
            f"{raw_value!r} must be positive"
        )

    return value