import unittest
from unittest.mock import patch, MagicMock

import requests

from opensovd.action_adapter import (
    validate_action_request,
    submit_diagnostic_action,
    get_diagnostic_action_status,
)


class ValidateActionRequestTest(unittest.TestCase):

    def test_valid_request_passes(self):
        error = validate_action_request("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertIsNone(error)

    def test_blank_vehicle_id_rejected(self):
        error = validate_action_request("", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(400, error["status"])
        self.assertEqual("INVALID_REQUEST", error["error"])

    def test_unknown_vehicle_id_rejected(self):
        error = validate_action_request("vehicle-999", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(404, error["status"])
        self.assertEqual("VEHICLE_NOT_FOUND", error["error"])

    def test_unsupported_action_rejected(self):
        error = validate_action_request("vehicle-001", "REBOOT_VEHICLE", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(400, error["status"])
        self.assertEqual("INVALID_DIAGNOSTIC_ACTION", error["error"])

    def test_unsupported_scenario_rejected(self):
        error = validate_action_request("vehicle-001", "INJECT_SCENARIO", "ENGINE_FIRE")
        self.assertEqual(400, error["status"])
        self.assertEqual("INVALID_SCENARIO", error["error"])

    def test_blank_action_rejected(self):
        error = validate_action_request("vehicle-001", "", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(400, error["status"])

    def test_blank_scenario_rejected(self):
        error = validate_action_request("vehicle-001", "INJECT_SCENARIO", "")
        self.assertEqual(400, error["status"])


class SubmitDiagnosticActionTest(unittest.TestCase):

    @patch("opensovd.action_adapter.requests.post")
    def test_valid_request_forwards_and_returns_backend_response(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=202,
            json=lambda: {"actionId": "abc-123", "status": "ACCEPTED"},
        )
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual("ACCEPTED", result["status"])
        mock_post.assert_called_once()

    def test_invalid_request_never_calls_backend(self):
        with patch("opensovd.action_adapter.requests.post") as mock_post:
            result = submit_diagnostic_action("vehicle-999", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
            self.assertEqual(404, result["status"])
            mock_post.assert_not_called()

    @patch("opensovd.action_adapter.requests.post")
    def test_backend_timeout_returns_504(self, mock_post):
        mock_post.side_effect = requests.Timeout()
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(504, result["status"])
        self.assertEqual("COMPONENT_TIMEOUT", result["error"])

    @patch("opensovd.action_adapter.requests.post")
    def test_backend_unreachable_returns_503(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("connection refused")
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(503, result["status"])
        self.assertEqual("COMPONENT_UNAVAILABLE", result["error"])

    @patch("opensovd.action_adapter.requests.post")
    def test_backend_5xx_returns_502(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500)
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(502, result["status"])
        self.assertEqual("COMPONENT_COMMUNICATION_FAILURE", result["error"])

    @patch("opensovd.action_adapter.requests.post")
    def test_backend_4xx_passes_through_backend_error_body(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=409,
            json=lambda: {"status": 409, "error": "SCENARIO_STATE_CONFLICT"},
        )
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(409, result["status"])
        self.assertEqual("SCENARIO_STATE_CONFLICT", result["error"])

    @patch("opensovd.action_adapter.requests.post")
    def test_malformed_backend_response_returns_502(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=MagicMock(side_effect=ValueError()))
        result = submit_diagnostic_action("vehicle-001", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE")
        self.assertEqual(502, result["status"])
        self.assertEqual("COMPONENT_COMMUNICATION_FAILURE", result["error"])


class GetDiagnosticActionStatusTest(unittest.TestCase):

    @patch("opensovd.action_adapter.requests.get")
    def test_valid_action_id_returns_status(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"actionId": "abc-123", "status": "COMPLETED"},
        )
        result = get_diagnostic_action_status("abc-123")
        self.assertEqual("COMPLETED", result["status"])

    def test_blank_action_id_rejected_without_calling_backend(self):
        with patch("opensovd.action_adapter.requests.get") as mock_get:
            result = get_diagnostic_action_status("")
            self.assertEqual(400, result["status"])
            mock_get.assert_not_called()

    @patch("opensovd.action_adapter.requests.get")
    def test_unknown_action_id_returns_404(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        result = get_diagnostic_action_status("does-not-exist")
        self.assertEqual(404, result["status"])
        self.assertEqual("ACTION_NOT_FOUND", result["error"])

    @patch("opensovd.action_adapter.requests.get")
    def test_backend_timeout_returns_504(self, mock_get):
        mock_get.side_effect = requests.Timeout()
        result = get_diagnostic_action_status("abc-123")
        self.assertEqual(504, result["status"])


if __name__ == "__main__":
    unittest.main()