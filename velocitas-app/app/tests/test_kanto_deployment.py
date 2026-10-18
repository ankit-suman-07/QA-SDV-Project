import json
from pathlib import Path


VELOCITAS_ROOT = (
    Path(__file__).resolve().parents[2]
)

APP_MANIFEST_PATH = (
    VELOCITAS_ROOT
    / "app"
    / "AppManifest.json"
)

KANTO_DESCRIPTOR_PATH = (
    VELOCITAS_ROOT
    / "kanto"
    / "autonomous-health-app.json"
)


def load_json(path):
    with path.open(
        encoding="utf-8"
    ) as source:
        return json.load(source)


def environment_as_dict(descriptor):
    entries = descriptor["config"]["env"]

    return dict(
        entry.split("=", 1)
        for entry in entries
    )


def test_kanto_descriptor_matches_app_manifest():
    manifest = load_json(APP_MANIFEST_PATH)
    descriptor = load_json(
        KANTO_DESCRIPTOR_PATH
    )

    expected_name = manifest["name"].lower()

    assert (
        descriptor["container_name"]
        == expected_name
    )

    assert (
        descriptor["image"]["name"]
        == (
            "localhost:12345/"
            f"{expected_name}:local"
        )
    )


def test_kanto_container_uses_safe_edge_settings():
    descriptor = load_json(
        KANTO_DESCRIPTOR_PATH
    )

    host_config = descriptor["host_config"]

    assert host_config["network_mode"] == "host"
    assert host_config["privileged"] is False

    assert (
        host_config["restart_policy"]["type"]
        == "unless-stopped"
    )


def test_kanto_container_connects_to_runtime_services():
    descriptor = load_json(
        KANTO_DESCRIPTOR_PATH
    )

    environment = environment_as_dict(
        descriptor
    )

    assert (
        environment[
            "SDV_VEHICLEDATABROKER_ADDRESS"
        ]
        == "grpc://127.0.0.1:55555"
    )

    assert (
        environment["SDV_MQTT_ADDRESS"]
        == "mqtt://127.0.0.1:1883"
    )

    assert (
        environment["DATABROKER_HOST"]
        == "127.0.0.1"
    )

    assert (
        environment["DATABROKER_PORT"]
        == "55555"
    )

    assert (
        environment["SIMULATED_VEHICLE_ID"]
        == "vehicle-001"
    )