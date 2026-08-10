import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.client import HTTPConnection

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "src"),
)

from control_server import start_control_server
from scenario_controller import ScenarioController


@pytest.fixture
def running_server():
    controller = ScenarioController()
    server = start_control_server(
        controller=controller,
        host="127.0.0.1",
        port=0,
    )

    yield server, controller

    server.shutdown()
    server.server_close()


def post_json(server, path, payload):
    host, port = server.server_address
    request = Request(
        url=f"http://{host}:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=2) as response:
        return response.status, json.load(response)


def test_health_endpoint_returns_ok(running_server):
    server, _ = running_server
    host, port = server.server_address

    with urlopen(
        f"http://{host}:{port}/health",
        timeout=2,
    ) as response:
        body = json.load(response)

    assert response.status == 200
    assert body == {"status": "UP"}


def test_post_action_injects_scenario(running_server):
    server, controller = running_server

    status, body = post_json(
        server,
        "/api/v1/scenarios/actions",
        {
            "actionId": "action-001",
            "traceId": "trace-001",
            "action": "INJECT_SCENARIO",
            "scenario": "COOLING_SYSTEM_FAILURE",
        },
    )

    assert status == 200
    assert body["active"] is True
    assert controller.is_active(
        "COOLING_SYSTEM_FAILURE"
    ) is True


def test_invalid_action_returns_bad_request(running_server):
    server, _ = running_server

    with pytest.raises(HTTPError) as error:
        post_json(
            server,
            "/api/v1/scenarios/actions",
            {
                "actionId": "action-001",
                "traceId": "trace-001",
                "action": "UNKNOWN_ACTION",
                "scenario": "COOLING_SYSTEM_FAILURE",
            },
        )

    assert error.value.code == 400

def test_chunked_post_action_injects_scenario(
    running_server,
):
    server, controller = running_server
    host, port = server.server_address

    payload = json.dumps(
        {
            "actionId": "action-001",
            "traceId": "trace-001",
            "action": "INJECT_SCENARIO",
            "scenario": "COOLING_SYSTEM_FAILURE",
        }
    ).encode("utf-8")

    connection = HTTPConnection(
        host,
        port,
        timeout=2,
    )

    connection.request(
        method="POST",
        url="/api/v1/scenarios/actions",
        body=iter([payload]),
        headers={
            "Content-Type": "application/json",
        },
        encode_chunked=True,
    )

    response = connection.getresponse()
    body = json.loads(
        response.read().decode("utf-8")
    )
    connection.close()

    assert response.status == 200
    assert body["active"] is True
    assert controller.is_active(
        "COOLING_SYSTEM_FAILURE"
    ) is True