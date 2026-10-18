import json
from pathlib import Path


CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "vss-with-autonomous-sensors.json"
)


def load_configuration():
    return json.loads(
        CONFIG_PATH.read_text(encoding="utf-8")
    )


def get_node(configuration, signal_path):
    current = configuration

    for path_part in signal_path.split("."):
        if path_part == "Vehicle":
            current = current[path_part]
        else:
            current = current["children"][path_part]

    return current


def test_autonomous_vss_configuration_contains_required_signals():
    configuration = load_configuration()

    distance = get_node(
        configuration,
        (
            "Vehicle.Automation.Lidar.Front."
            "NearestObstacleDistance"
        ),
    )

    lidar_health = get_node(
        configuration,
        "Vehicle.Automation.Lidar.Front.IsHealthy",
    )

    obstacle_warning = get_node(
        configuration,
        (
            "Vehicle.Automation.ObstacleWarning."
            "IsActive"
        ),
    )

    autonomous_braking = get_node(
        configuration,
        (
            "Vehicle.Automation.AutonomousBraking."
            "IsActive"
        ),
    )

    coolant_pressure = get_node(
        configuration,
        (
            "Vehicle.Powertrain.CombustionEngine."
            "EngineCoolant.Pressure"
        ),
    )

    assert distance["type"] == "sensor"
    assert distance["datatype"] == "float"
    assert distance["unit"] == "m"

    assert lidar_health["datatype"] == "boolean"
    assert obstacle_warning["datatype"] == "boolean"
    assert autonomous_braking["datatype"] == "boolean"

    assert coolant_pressure["datatype"] == "float"
    assert coolant_pressure["unit"] == "kPa"