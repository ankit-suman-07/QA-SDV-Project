import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "src"),
)

from scenario_controller import ScenarioController


def test_scenario_is_inactive_by_default():
    controller = ScenarioController()

    assert controller.is_active(
        "COOLING_SYSTEM_FAILURE"
    ) is False


def test_inject_action_activates_scenario():
    controller = ScenarioController()

    controller.execute(
        action="INJECT_SCENARIO",
        scenario="COOLING_SYSTEM_FAILURE",
        action_id="action-001",
        trace_id="trace-001",
    )

    assert controller.is_active(
        "COOLING_SYSTEM_FAILURE"
    ) is True


def test_clear_action_deactivates_scenario():
    controller = ScenarioController()

    controller.execute(
        action="INJECT_SCENARIO",
        scenario="COOLING_SYSTEM_FAILURE",
        action_id="action-001",
        trace_id="trace-001",
    )

    controller.execute(
        action="CLEAR_SCENARIO",
        scenario="COOLING_SYSTEM_FAILURE",
        action_id="action-002",
        trace_id="trace-002",
    )

    assert controller.is_active(
        "COOLING_SYSTEM_FAILURE"
    ) is False


def test_unsupported_action_is_rejected():
    controller = ScenarioController()

    with pytest.raises(
        ValueError,
        match="Unsupported diagnostic action",
    ):
        controller.execute(
            action="UNKNOWN_ACTION",
            scenario="COOLING_SYSTEM_FAILURE",
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
            action="INJECT_SCENARIO",
            scenario="UNKNOWN_SCENARIO",
            action_id="action-001",
            trace_id="trace-001",
        )

def test_scenario_state_preserves_action_context():
    controller = ScenarioController()

    controller.execute(
        action="INJECT_SCENARIO",
        scenario="COOLING_SYSTEM_FAILURE",
        action_id="action-001",
        trace_id="trace-001",
    )

    assert controller.get_state(
        "COOLING_SYSTEM_FAILURE"
    ) == {
        "scenario": "COOLING_SYSTEM_FAILURE",
        "active": True,
        "actionId": "action-001",
        "traceId": "trace-001",
        "action": "INJECT_SCENARIO",
    }