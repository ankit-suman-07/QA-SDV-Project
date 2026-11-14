import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
    ),
)

from scenario_controller import ScenarioController


VEHICLE_ID = "vehicle-001"
COOLING_FAILURE = "COOLING_SYSTEM_FAILURE"


def test_scenario_is_inactive_by_default():
    controller = ScenarioController()

    assert controller.is_active(
        vehicle_id=VEHICLE_ID,
        scenario=COOLING_FAILURE,
    ) is False


def test_inject_action_activates_scenario():
    controller = ScenarioController()

    controller.execute(
        vehicle_id=VEHICLE_ID,
        action="INJECT_SCENARIO",
        scenario=COOLING_FAILURE,
        action_id="action-001",
        trace_id="trace-001",
    )

    assert controller.is_active(
        vehicle_id=VEHICLE_ID,
        scenario=COOLING_FAILURE,
    ) is True


def test_clear_action_deactivates_scenario():
    controller = ScenarioController()

    controller.execute(
        vehicle_id=VEHICLE_ID,
        action="INJECT_SCENARIO",
        scenario=COOLING_FAILURE,
        action_id="action-001",
        trace_id="trace-001",
    )

    controller.execute(
        vehicle_id=VEHICLE_ID,
        action="CLEAR_SCENARIO",
        scenario=COOLING_FAILURE,
        action_id="action-002",
        trace_id="trace-002",
    )

    assert controller.is_active(
        vehicle_id=VEHICLE_ID,
        scenario=COOLING_FAILURE,
    ) is False


def test_unsupported_action_is_rejected():
    controller = ScenarioController()

    with pytest.raises(
        ValueError,
        match="Unsupported diagnostic action",
    ):
        controller.execute(
            vehicle_id=VEHICLE_ID,
            action="UNKNOWN_ACTION",
            scenario=COOLING_FAILURE,
            action_id="action-001",
            trace_id="trace-001",
        )


def test_unsupported_scenario_is_rejected():
    controller = ScenarioController()

    with pytest.raises(
        ValueError,
        match="Unsupported diagnostic scenario",
    ):
        controller.execute(
            vehicle_id=VEHICLE_ID,
            action="INJECT_SCENARIO",
            scenario="UNKNOWN_SCENARIO",
            action_id="action-001",
            trace_id="trace-001",
        )


def test_scenario_state_preserves_action_context():
    controller = ScenarioController()

    controller.execute(
        vehicle_id=VEHICLE_ID,
        action="INJECT_SCENARIO",
        scenario=COOLING_FAILURE,
        action_id="action-001",
        trace_id="trace-001",
    )

    assert controller.get_state(
        vehicle_id=VEHICLE_ID,
        scenario=COOLING_FAILURE,
    ) == {
        "vehicleId": VEHICLE_ID,
        "scenario": COOLING_FAILURE,
        "active": True,
        "actionId": "action-001",
        "traceId": "trace-001",
        "action": "INJECT_SCENARIO",
    }


def test_scenario_state_is_isolated_by_vehicle():
    controller = ScenarioController()

    controller.execute(
        vehicle_id="vehicle-002",
        action="INJECT_SCENARIO",
        scenario=COOLING_FAILURE,
        action_id="action-002",
        trace_id="trace-002",
    )

    assert controller.is_active(
        vehicle_id="vehicle-002",
        scenario=COOLING_FAILURE,
    ) is True

    assert controller.is_active(
        vehicle_id=VEHICLE_ID,
        scenario=COOLING_FAILURE,
    ) is False


@pytest.mark.parametrize(
    "scenario",
    [
        "LIDAR_OBSTRUCTION",
        "LIDAR_SENSOR_FAILURE",
    ],
)
def test_autonomous_scenarios_are_supported(scenario):
    controller = ScenarioController()

    response = controller.execute(
        vehicle_id=VEHICLE_ID,
        action="INJECT_SCENARIO",
        scenario=scenario,
        action_id="action-003",
        trace_id="trace-003",
    )

    assert response["vehicleId"] == VEHICLE_ID
    assert response["scenario"] == scenario
    assert response["active"] is True

    assert controller.is_active(
        vehicle_id=VEHICLE_ID,
        scenario=scenario,
    ) is True

from scenario_controller import WrongVehicleError  # noqa: E402

ALLOWED = "vehicle-002"


def test_wrong_vehicle_is_rejected_without_state_change():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(
        WrongVehicleError,
        match="provider serves vehicle-002, not vehicle-001",
    ):
        controller.execute(
            vehicle_id="vehicle-001",
            action="INJECT_SCENARIO",
            scenario="LIDAR_OBSTRUCTION",
            action_id="a",
            trace_id="t",
        )
    assert controller.get_state(ALLOWED, "LIDAR_OBSTRUCTION")["actionId"] is None
    with pytest.raises(WrongVehicleError):
        controller.is_active("vehicle-001", "LIDAR_OBSTRUCTION")
    with pytest.raises(WrongVehicleError):
        controller.get_state("vehicle-001", "LIDAR_OBSTRUCTION")


def test_padded_vehicle_id_is_rejected():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(WrongVehicleError):
        controller.is_active(" vehicle-002", "LIDAR_OBSTRUCTION")


@pytest.mark.parametrize("bad", ["", "   ", None, 2, ["vehicle-002"]])
def test_blank_or_non_string_id_is_plain_value_error(bad):
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    with pytest.raises(ValueError) as error:
        controller.is_active(bad, "LIDAR_OBSTRUCTION")
    assert not isinstance(error.value, WrongVehicleError)


def test_allowed_vehicle_executes_normally():
    controller = ScenarioController(allowed_vehicle_id=ALLOWED)
    state = controller.execute(
        vehicle_id=ALLOWED,
        action="INJECT_SCENARIO",
        scenario="LIDAR_OBSTRUCTION",
        action_id="a",
        trace_id="t",
    )
    assert state["active"] is True
    assert controller.allowed_vehicle_id == ALLOWED
