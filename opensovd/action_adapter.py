"""
opensovd/action_adapter.py

OpenSOVD-compatible diagnostic action adapter. Per
docs/10-iteration-3-contract.md task 7 (Atharva): since the available
OpenSOVD gateway is confirmed read-only (see
docs/evidence/iteration-2/07-opensovd-confirmed-read-only.png, and
Iteration 3 re-confirmation that /sovd/v1/apps/diagnostics is likewise
read-only with no operations resource), this adapter does not talk to a
real OpenSOVD action interface - none exists to talk to. It validates and
forwards diagnostic action requests to the Spring Boot API instead,
returning contract-shaped responses either way.

This is NOT a complete production OpenSOVD implementation - see
docs/10-iteration-3-contract.md's "OpenSOVD-Compatible Diagnostic
Contract" section, which explicitly requires this distinction to be
documented.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

DEFAULT_BACKEND_URL = "http://localhost:8081"
ACTIONS_PATH = "/api/v1/diagnostics/actions"

SUPPORTED_ACTIONS = {"INJECT_SCENARIO", "CLEAR_SCENARIO"}
SUPPORTED_SCENARIOS = {"COOLING_SYSTEM_FAILURE"}
SUPPORTED_VEHICLE_IDS = {"vehicle-001"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _error_response(status: int, error: str, message: str, path: str, trace_id: Optional[str] = None) -> dict:
    """Builds an error response matching docs/10's Error Contract shape."""
    return {
        "timestamp": _now_iso(),
        "status": status,
        "error": error,
        "message": message,
        "path": path,
        "traceId": trace_id,
    }


def validate_action_request(vehicle_id: str, action: str, scenario: str) -> Optional[dict]:
    """Validates a diagnostic action request against docs/10's 'Request
    Validation' rules. Returns an error response dict if invalid, or None
    if the request is valid and may be forwarded."""
    if not vehicle_id or not vehicle_id.strip():
        return _error_response(400, "INVALID_REQUEST", "vehicleId is required", ACTIONS_PATH)
    if vehicle_id not in SUPPORTED_VEHICLE_IDS:
        return _error_response(404, "VEHICLE_NOT_FOUND", f"Unsupported vehicle ID: {vehicle_id!r}", ACTIONS_PATH)

    if not action or not action.strip():
        return _error_response(400, "INVALID_REQUEST", "action is required", ACTIONS_PATH)
    if action not in SUPPORTED_ACTIONS:
        return _error_response(400, "INVALID_DIAGNOSTIC_ACTION", f"Unsupported diagnostic action: {action!r}", ACTIONS_PATH)

    if not scenario or not scenario.strip():
        return _error_response(400, "INVALID_REQUEST", "scenario is required", ACTIONS_PATH)
    if scenario not in SUPPORTED_SCENARIOS:
        return _error_response(400, "INVALID_SCENARIO", f"Unsupported scenario: {scenario!r}", ACTIONS_PATH)

    return None


def submit_diagnostic_action(
    vehicle_id: str,
    action: str,
    scenario: str,
    backend_url: str = DEFAULT_BACKEND_URL,
    timeout: float = 5.0,
) -> dict:
    """Validates and forwards a diagnostic action request to Spring Boot.
    Always returns a dict - either the backend's accepted-action response,
    or a structured error response. Never raises for expected failure
    modes (unavailable backend, timeout, malformed response)."""
    validation_error = validate_action_request(vehicle_id, action, scenario)
    if validation_error is not None:
        return validation_error

    payload = {"vehicleId": vehicle_id, "action": action, "scenario": scenario}

    try:
        response = requests.post(f"{backend_url}{ACTIONS_PATH}", json=payload, timeout=timeout)
    except requests.Timeout:
        return _error_response(504, "COMPONENT_TIMEOUT", "Diagnostic action request timed out", ACTIONS_PATH)
    except requests.RequestException as exc:
        return _error_response(503, "COMPONENT_UNAVAILABLE", f"Diagnostics service unavailable: {exc}", ACTIONS_PATH)

    if response.status_code >= 500:
        return _error_response(502, "COMPONENT_COMMUNICATION_FAILURE",
                                f"Backend returned {response.status_code}", ACTIONS_PATH)
    if response.status_code >= 400:
        try:
            return response.json()
        except ValueError:
            return _error_response(response.status_code, "INVALID_REQUEST",
                                    "Backend rejected the request", ACTIONS_PATH)

    try:
        return response.json()
    except ValueError:
        return _error_response(502, "COMPONENT_COMMUNICATION_FAILURE",
                                "Backend returned an invalid response body", ACTIONS_PATH)


def get_diagnostic_action_status(
    action_id: str,
    backend_url: str = DEFAULT_BACKEND_URL,
    timeout: float = 5.0,
) -> dict:
    """Validates and forwards an action-status query to Spring Boot."""
    path = f"{ACTIONS_PATH}/{action_id}"

    if not action_id or not action_id.strip():
        return _error_response(400, "INVALID_REQUEST", "actionId is required", path)

    try:
        response = requests.get(f"{backend_url}{path}", timeout=timeout)
    except requests.Timeout:
        return _error_response(504, "COMPONENT_TIMEOUT", "Action status request timed out", path)
    except requests.RequestException as exc:
        return _error_response(503, "COMPONENT_UNAVAILABLE", f"Diagnostics service unavailable: {exc}", path)

    if response.status_code == 404:
        return _error_response(404, "ACTION_NOT_FOUND", f"Unknown action ID: {action_id!r}", path)
    if response.status_code >= 500:
        return _error_response(502, "COMPONENT_COMMUNICATION_FAILURE",
                                f"Backend returned {response.status_code}", path)

    try:
        return response.json()
    except ValueError:
        return _error_response(502, "COMPONENT_COMMUNICATION_FAILURE",
                                "Backend returned an invalid response body", path)