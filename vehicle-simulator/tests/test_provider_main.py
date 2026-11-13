import importlib
import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "src"),
)

from scenario_controller import WrongVehicleError  # noqa: E402


@pytest.fixture
def provider_main(monkeypatch):
    monkeypatch.setenv("SIMULATED_VEHICLE_ID", "vehicle-002")
    monkeypatch.delenv("INJECT_FAULT", raising=False)
    sys.modules.pop("main", None)
    module = importlib.import_module("main")
    yield module
    sys.modules.pop("main", None)


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
