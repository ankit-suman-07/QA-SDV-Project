from threading import RLock


class ScenarioController:

    SUPPORTED_ACTIONS = {
        "INJECT_SCENARIO",
        "CLEAR_SCENARIO",
    }

    SUPPORTED_SCENARIOS = {
        "COOLING_SYSTEM_FAILURE",
        "LIDAR_OBSTRUCTION",
        "LIDAR_SENSOR_FAILURE",
    }

    def __init__(self):
        self._scenario_states = {}
        self._active_scenarios = set()
        self._lock = RLock()

    def execute(
        self,
        vehicle_id,
        action,
        scenario,
        action_id,
        trace_id,
    ):
        vehicle_id = self._validate_vehicle_id(vehicle_id)

        if action not in self.SUPPORTED_ACTIONS:
            raise ValueError(
                f"Unsupported diagnostic action: {action}"
            )

        if scenario not in self.SUPPORTED_SCENARIOS:
            raise ValueError(
                f"Unsupported diagnostic scenario: {scenario}"
            )

        scenario_key = (vehicle_id, scenario)

        with self._lock:
            if action == "INJECT_SCENARIO":
                self._active_scenarios.add(scenario_key)
            else:
                self._active_scenarios.discard(
                    scenario_key
                )

            state = {
                "vehicleId": vehicle_id,
                "scenario": scenario,
                "active": (
                    scenario_key
                    in self._active_scenarios
                ),
                "actionId": action_id,
                "traceId": trace_id,
                "action": action,
            }

            self._scenario_states[scenario_key] = state

            return dict(state)

    def is_active(self, vehicle_id, scenario):
        vehicle_id = self._validate_vehicle_id(vehicle_id)
        scenario_key = (vehicle_id, scenario)

        with self._lock:
            return scenario_key in self._active_scenarios

    def get_state(self, vehicle_id, scenario):
        vehicle_id = self._validate_vehicle_id(vehicle_id)

        if scenario not in self.SUPPORTED_SCENARIOS:
            raise ValueError(
                f"Unsupported diagnostic scenario: {scenario}"
            )

        scenario_key = (vehicle_id, scenario)

        with self._lock:
            state = self._scenario_states.get(
                scenario_key
            )

            if state is None:
                return {
                    "vehicleId": vehicle_id,
                    "scenario": scenario,
                    "active": False,
                    "actionId": None,
                    "traceId": None,
                    "action": None,
                }

            return dict(state)

    @staticmethod
    def _validate_vehicle_id(vehicle_id):
        if (
            not isinstance(vehicle_id, str)
            or not vehicle_id.strip()
        ):
            raise ValueError(
                "Vehicle ID must not be blank"
            )

        return vehicle_id.strip()