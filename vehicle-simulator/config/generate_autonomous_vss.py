import json
from pathlib import Path


CONFIG_DIRECTORY = Path(__file__).resolve().parent

SOURCE_PATH = (
    CONFIG_DIRECTORY
    / "vss-with-coolant-pressure.json"
)

OUTPUT_PATH = (
    CONFIG_DIRECTORY
    / "vss-with-autonomous-sensors.json"
)


def branch(description):
    return {
        "type": "branch",
        "description": description,
        "children": {},
    }


def sensor(
    datatype,
    description,
    unit=None,
    minimum=None,
    maximum=None,
):
    definition = {
        "type": "sensor",
        "datatype": datatype,
        "description": description,
    }

    if unit is not None:
        definition["unit"] = unit

    if minimum is not None:
        definition["min"] = minimum

    if maximum is not None:
        definition["max"] = maximum

    return definition


def generate_configuration():
    source = json.loads(
        SOURCE_PATH.read_text(encoding="utf-8")
    )

    vehicle_children = source["Vehicle"].setdefault(
        "children",
        {},
    )

    automation = branch(
        "Project-specific autonomous vehicle "
        "monitoring signals."
    )

    lidar = branch(
        "Synthetic LiDAR sensor state."
    )

    lidar_front = branch(
        "Front-facing synthetic LiDAR sensor."
    )

    lidar_front["children"][
        "NearestObstacleDistance"
    ] = sensor(
        datatype="float",
        unit="m",
        minimum=0.0,
        maximum=250.0,
        description=(
            "Distance to the nearest obstacle detected "
            "by the front LiDAR sensor."
        ),
    )

    lidar_front["children"]["IsHealthy"] = sensor(
        datatype="boolean",
        description=(
            "Indicates whether the front LiDAR sensor "
            "is operating correctly."
        ),
    )

    lidar["children"]["Front"] = lidar_front

    obstacle_warning = branch(
        "Autonomous obstacle-warning state."
    )

    obstacle_warning["children"]["IsActive"] = sensor(
        datatype="boolean",
        description=(
            "Indicates that an obstacle is within the "
            "configured warning distance."
        ),
    )

    autonomous_braking = branch(
        "Autonomous emergency-braking state."
    )

    autonomous_braking["children"]["IsActive"] = sensor(
        datatype="boolean",
        description=(
            "Indicates that autonomous emergency "
            "braking is currently active."
        ),
    )

    automation["children"]["Lidar"] = lidar
    automation["children"][
        "ObstacleWarning"
    ] = obstacle_warning
    automation["children"][
        "AutonomousBraking"
    ] = autonomous_braking

    vehicle_children["Automation"] = automation

    OUTPUT_PATH.write_text(
        json.dumps(
            source,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return source


if __name__ == "__main__":
    generate_configuration()

    print(
        "Generated autonomous VSS configuration: "
        f"{OUTPUT_PATH}"
    )