from threading import RLock


class ScenarioController:

    SUPPORTED_ACTIONS = {
        "INJECT_SCENARIO",
        "CLEAR_SCENARIO",
    }

    SUPPORTED_SCENARIOS = {
        "COOLING_SYSTEM_FAILURE",
    }

    def __init__(self):
        self._scenario_states = {}
        self._active_scenarios = set()
        self._lock = RLock()

    def execute(
        self,
        action,
        scenario,
        action_id,
        trace_id,
    ):
        if action not in self.SUPPORTED_ACTIONS:
            raise ValueError(
                f"Unsupported diagnostic action: {action}"
            )

        if scenario not in self.SUPPORTED_SCENARIOS:
            raise ValueError(
                f"Unsupported diagnostic scenario: {scenario}"
            )

        with self._lock:
            if action == "INJECT_SCENARIO":
                self._active_scenarios.add(scenario)
            else:
                self._active_scenarios.discard(scenario)

            state = {
                "scenario": scenario,
                "active": (
                    scenario in self._active_scenarios
                ),
                "actionId": action_id,
                "traceId": trace_id,
                "action": action,
            }

            self._scenario_states[scenario] = state

            return dict(state)

    def is_active(self, scenario):
        with self._lock:
            return scenario in self._active_scenarios

    def get_state(self, scenario):
        if scenario not in self.SUPPORTED_SCENARIOS:
            raise ValueError(
                f"Unsupported diagnostic scenario: {scenario}"
            )

        with self._lock:
            state = self._scenario_states.get(scenario)

            if state is None:
                return {
                    "scenario": scenario,
                    "active": False,
                    "actionId": None,
                    "traceId": None,
                    "action": None,
                }

            return dict(state)