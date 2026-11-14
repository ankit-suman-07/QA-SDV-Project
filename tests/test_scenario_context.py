"""Mock provider/context tests; no simulator or shared service is contacted."""
import ast
import importlib
from pathlib import Path
import unittest
from unittest.mock import Mock

import requests


class ScenarioContextTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/scenario_context.py').exists(),
                        'import-safe scenario context caller is missing')
        self.m = importlib.import_module('ditto.scenario_context')
        self.context = dict(vehicleId='vehicle-001', scenario='COOLING_SYSTEM_FAILURE',
                            actionId='action', traceId='trace', active=True, action='INJECT_SCENARIO')

    def test_vehicle_specific_route_and_context_preserved(self):
        for vehicle in ['vehicle-001', 'vehicle-002']:
            context = dict(self.context, vehicleId=vehicle)
            response = Mock(ok=True)
            response.json.return_value = context
            get = Mock(return_value=response)
            self.assertEqual(context, self.m.get_scenario_context('http://provider/', vehicle, request_get=get))
            get.assert_called_once_with('http://provider/api/v1/vehicles/' + vehicle +
                                        '/scenarios/COOLING_SYSTEM_FAILURE', timeout=2)

    def test_wrong_identity_malformed_and_invalid_context_fail_closed(self):
        cases = [None, [], {}, dict(self.context, vehicleId='vehicle-002'),
                 dict(self.context, scenario='LIDAR_OBSTRUCTION'), dict(self.context, active='true'),
                 dict(self.context, traceId=''), dict(self.context, actionId=123)]
        for context in cases:
            response = Mock(ok=True)
            response.json.return_value = context
            with self.subTest(context=context):
                self.assertEqual({}, self.m.get_scenario_context('http://provider', request_get=Mock(return_value=response)))

    def test_timeouts_and_bad_json_are_bounded_and_return_no_context(self):
        for error in [requests.Timeout('timeout'), requests.ConnectionError('offline'), ValueError('JSON')]:
            get = Mock(side_effect=error)
            self.assertEqual({}, self.m.get_scenario_context('http://provider', request_get=get, sleeper=lambda _: None))
            self.assertEqual(3, get.call_count)
        get = Mock(return_value=Mock(ok=False))
        self.assertEqual({}, self.m.get_scenario_context('http://provider', request_get=get))
        get.assert_called_once()

    def test_default_inactive_context_allows_unknown_command_ids(self):
        response = Mock(ok=True)
        context = dict(self.context, active=False, action=None, actionId=None, traceId=None)
        response.json.return_value = context
        self.assertEqual(context, self.m.get_scenario_context('http://provider', request_get=Mock(return_value=response)))

    def test_actual_bridge_caller_uses_import_safe_helper(self):
        path = Path(__file__).parents[1] / 'ditto/scripts/interim-kuksa-to-ditto-bridge.py'
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_cooling_scenario_context')
        helper = Mock(return_value=self.context)
        namespace = {'fetch_scenario_context': helper, 'SIMULATOR_CONTROL_URL': 'http://provider'}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        self.assertEqual(self.context, namespace['get_cooling_scenario_context']())
        helper.assert_called_once_with('http://provider', vehicle_id='vehicle-001', scenario='COOLING_SYSTEM_FAILURE')
