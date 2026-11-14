"""Import-safe legacy cooling context caller; no KUKSA/Protobuf startup side effects."""
from urllib.parse import urlsplit

from ditto.ditto_http import get_json_with_retry


def get_scenario_context(base_url, vehicle_id='vehicle-001', scenario='COOLING_SYSTEM_FAILURE',
                         *, request_get=None, sleeper=None):
    """Return only trusted matching context; unavailable/invalid responses yield {}.

    The provider's initial inactive state legitimately has null command IDs.
    Missing context never manufactures an action acknowledgment or command IDs.
    """
    if vehicle_id not in ('vehicle-001', 'vehicle-002') or scenario != 'COOLING_SYSTEM_FAILURE':
        raise ValueError('Unsupported vehicle/scenario for legacy cooling context')
    parsed = urlsplit(base_url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or
            parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError('Expected provider HTTP(S) base URL without credentials/query/fragment')
    context = get_json_with_retry(
        url=f'{base_url.rstrip("/")}/api/v1/vehicles/{vehicle_id}/scenarios/{scenario}',
        attempts=3, timeout_seconds=2, retry_delay_seconds=0.2,
        request_get=request_get, sleeper=sleeper)
    if (not isinstance(context, dict) or context.get('vehicleId') != vehicle_id or
            context.get('scenario') != scenario or type(context.get('active')) is not bool):
        return {}
    for key in ('actionId', 'traceId'):
        value = context.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            return {}
    if context.get('action') not in (None, 'INJECT_SCENARIO', 'CLEAR_SCENARIO'):
        return {}
    return context
