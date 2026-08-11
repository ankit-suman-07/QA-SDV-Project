import unittest
from unittest.mock import Mock

import requests

from ditto.ditto_http import (
    get_json_with_retry,
    put_json_with_retry,
)


class DittoHttpTest(unittest.TestCase):

    def test_retries_after_timeout_and_returns_success(self):
        successful_response = Mock()
        successful_response.ok = True

        request_put = Mock(
            side_effect=[
                requests.Timeout("temporary timeout"),
                successful_response,
            ]
        )
        sleeper = Mock()

        result = put_json_with_retry(
            url="http://localhost/test",
            value={"status": "CRITICAL"},
            auth=("ditto", "ditto"),
            headers={"Content-Type": "application/json"},
            attempts=3,
            timeout_seconds=5,
            retry_delay_seconds=0.1,
            request_put=request_put,
            sleeper=sleeper,
        )

        self.assertIs(successful_response, result)
        self.assertEqual(2, request_put.call_count)
        sleeper.assert_called_once_with(0.1)

    def test_returns_none_when_all_attempts_timeout(self):
        request_put = Mock(
            side_effect=requests.Timeout(
                "Ditto unavailable"
            )
        )
        sleeper = Mock()

        result = put_json_with_retry(
            url="http://localhost/test",
            value={"status": "CRITICAL"},
            auth=("ditto", "ditto"),
            headers={"Content-Type": "application/json"},
            attempts=3,
            timeout_seconds=5,
            retry_delay_seconds=0.1,
            request_put=request_put,
            sleeper=sleeper,
        )

        self.assertIsNone(result)
        self.assertEqual(3, request_put.call_count)
        self.assertEqual(2, sleeper.call_count)

    def test_rejects_non_positive_attempt_count(self):
        with self.assertRaises(ValueError):
            put_json_with_retry(
                url="http://localhost/test",
                value={},
                auth=("ditto", "ditto"),
                headers={},
                attempts=0,
            )

    def test_get_json_returns_action_context(self):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "actionId": "action-001",
            "traceId": "trace-001",
            "active": True,
        }

        request_get = Mock(return_value=response)

        result = get_json_with_retry(
            url=(
                "http://localhost:8090/api/v1/"
                "scenarios/COOLING_SYSTEM_FAILURE"
            ),
            attempts=3,
            timeout_seconds=2,
            request_get=request_get,
        )

        self.assertEqual(
            "action-001",
            result["actionId"],
        )
        self.assertEqual(
            "trace-001",
            result["traceId"],
        )

    def test_get_json_returns_none_after_timeouts(self):
        request_get = Mock(
            side_effect=requests.Timeout(
                "simulator unavailable"
            )
        )
        sleeper = Mock()

        result = get_json_with_retry(
            url="http://localhost:8090/test",
            attempts=2,
            timeout_seconds=2,
            retry_delay_seconds=0.1,
            request_get=request_get,
            sleeper=sleeper,
        )

        self.assertIsNone(result)
        self.assertEqual(2, request_get.call_count)
        sleeper.assert_called_once_with(0.1)


if __name__ == "__main__":
    unittest.main()