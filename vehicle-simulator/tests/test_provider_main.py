import importlib.util
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)

from scenario_controller import WrongVehicleError  # noqa: E402


@pytest.fixture
def provider_main(monkeypatch):
    monkeypatch.setenv("SIMULATED_VEHICLE_ID", "vehicle-002")
    monkeypatch.delenv("INJECT_FAULT", raising=False)
    # Load by path: other test packages also have a main.py on sys.path.
    spec = importlib.util.spec_from_file_location(
        "provider_main",
        os.path.join(SRC, "main.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


def test_production_controller_enforces_configured_vehicle(provider_main):
    controller = provider_main.create_scenario_controller()

    with pytest.raises(WrongVehicleError):
        controller.execute(
            vehicle_id="vehicle-001",
            action="INJECT_SCENARIO",
            scenario="LIDAR_OBSTRUCTION",
            action_id="a",
            trace_id="t",
        )

    state = controller.execute(
        vehicle_id="vehicle-002",
        action="INJECT_SCENARIO",
        scenario="LIDAR_OBSTRUCTION",
        action_id="a",
        trace_id="t",
    )
    assert state["active"] is True


def test_ladder_step_is_not_published_to_kuksa(provider_main):
    assert "lidar_step" not in provider_main.SIGNAL_PATHS
