"""Static checks of the two-vehicle V1 edge deployment (E1, contract C2).

Uses `docker compose config` to resolve the file exactly as Compose will run
it. Skipped when the Docker CLI is not available.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPOSITORY_ROOT / "vehicle-simulator" / "docker-compose.v1.yml"
VEHICLES = ("001", "002")


@pytest.fixture(scope="module")
def services():
    if shutil.which("docker") is None:
        pytest.skip("docker CLI not available")
    result = subprocess.run(
        [
            "docker", "compose", "-f", str(COMPOSE_FILE),
            "config", "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["services"]


def published_ports(service):
    return [int(port["published"]) for port in service.get("ports", [])]


def test_each_vehicle_uses_only_its_own_broker(services):
    for n in VEHICLES:
        app = services[f"app-{n}"]["environment"]
        provider = services[f"provider-{n}"]["environment"]

        assert app["SIMULATED_VEHICLE_ID"] == f"vehicle-{n}"
        assert provider["SIMULATED_VEHICLE_ID"] == f"vehicle-{n}"
        assert app["DATABROKER_HOST"] == f"kuksa-{n}"
        assert provider["DATABROKER_HOST"] == f"kuksa-{n}"
        assert app["DATABROKER_PORT"] == "55555"
        assert provider["DATABROKER_PORT"] == "55555"
        assert (
            app["SDV_VEHICLEDATABROKER_ADDRESS"]
            == f"grpc://kuksa-{n}:55555"
        )
        assert app["SDV_MQTT_ADDRESS"] == "mqtt://mqtt:1883"


def test_default_host_ports_match_contract_and_do_not_collide(services):
    ports = [
        port
        for service in services.values()
        for port in published_ports(service)
    ]

    assert sorted(ports) == [8091, 8092, 18883, 55556, 55557]
    assert published_ports(services["mqtt"]) == [18883]
    assert published_ports(services["kuksa-001"]) == [55556]
    assert published_ports(services["kuksa-002"]) == [55557]
    assert published_ports(services["provider-001"]) == [8091]
    assert published_ports(services["provider-002"]) == [8092]


def test_apps_restart_and_depend_on_own_broker_and_mqtt(services):
    for n, other in (("001", "002"), ("002", "001")):
        app = services[f"app-{n}"]
        depends_on = set(app["depends_on"])

        assert app["restart"] == "unless-stopped"
        assert {f"kuksa-{n}", "mqtt", f"provider-{n}"} <= depends_on
        assert f"kuksa-{other}" not in depends_on
        assert f"provider-{other}" not in depends_on
