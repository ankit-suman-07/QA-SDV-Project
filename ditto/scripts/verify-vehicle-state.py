"""
Ditto vehicle-001 state verifier.

Queries the Ditto digital twin for vehicle-001, validates required signal
and health fields are present and correctly typed, checks correlated-fault
consistency (docs/10-iteration-3-contract.md), and detects missing or
stale values using the staleness formula from
docs/04-vehicle-health-contracts.md Section 6:
max(3 x expected update interval, 5 seconds).

Usage:
    python ditto/scripts/verify-vehicle-state.py
    python ditto/scripts/verify-vehicle-state.py --publication-interval-seconds 0.2
    python ditto/scripts/verify-vehicle-state.py --max-age-seconds 10

Exit code 0 on success, 1 on any validation failure.
"""
import argparse
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

DEFAULT_DITTO_URL = "http://localhost:8080"
DEFAULT_THING_ID = "sdv:vehicle-001"
DEFAULT_MAX_AGE_SECONDS = 30.0

REQUIRED_SIGNAL_FIELDS = [
    "speedKph", "batteryPercent", "temperatureCelsius", "coolantPressureKpa",
    "tirePressurePsi", "sourceTimestamp",
]
REQUIRED_TIRE_FIELDS = ["frontLeft", "frontRight", "rearLeft", "rearRight"]
REQUIRED_HEALTH_FIELDS = ["status", "activeFaults", "faultCount", "processedTimestamp"]
VALID_HEALTH_STATUSES = {"HEALTHY", "WARNING", "CRITICAL"}

# Must be finite numbers, not booleans, per docs/10 "Signal Validation
# Rules". tirePressurePsi wheels are checked separately since nested.
NUMERIC_SIGNAL_FIELDS = ["speedKph", "batteryPercent", "temperatureCelsius", "coolantPressureKpa"]

# Matches docs/10-iteration-3-contract.md "Correlated Health Rule". Only
# the complete recovery conjunction is checked - see validate_correlated_faults.
CORRELATED_FAULT_RULES = {
    "COOLING_SYSTEM_FAILURE": {
        "temperatureCelsius": {"activation_threshold": 105.0, "recovery_threshold": 100.0, "direction": "above"},
        "coolantPressureKpa": {"activation_threshold": 150.0, "recovery_threshold": 180.0, "direction": "below"},
    },
}

# Required per docs/10 Fault Contract for an ACTIVE fault. clearedAt is
# excluded - required only after clearing, not while active.
REQUIRED_ACTIVE_FAULT_DETAIL_FIELDS = [
    "code", "description", "severity", "status",
    "affectedSignals", "observedValues",
    "activationThresholds", "recoveryThresholds", "detectedAt",
]


@dataclass
class VerificationResult:
    ok: bool
    errors: list = field(default_factory=list)
    thing: dict = None

    def add_error(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def fetch_thing(ditto_url: str, thing_id: str, auth=("ditto", "ditto"), timeout: float = 5.0) -> dict:
    response = requests.get(f"{ditto_url}/api/2/things/{thing_id}", auth=auth, timeout=timeout)
    response.raise_for_status()
    return response.json()


def compute_max_age_seconds(publication_interval_seconds=None, explicit_max_age_seconds=None) -> float:
    """Per docs/04 Section 6: max(3 x expected interval, 5 seconds)."""
    for value in (publication_interval_seconds, explicit_max_age_seconds):
        if value is not None and (not _is_valid_number(value) or value <= 0):
            raise ValueError('Freshness intervals must be finite positive numbers')
    if explicit_max_age_seconds is not None:
        return explicit_max_age_seconds
    if publication_interval_seconds is not None:
        return max(3 * publication_interval_seconds, 5.0)
    return DEFAULT_MAX_AGE_SECONDS


def _is_valid_number(value) -> bool:
    """True only for a finite int/float. Explicitly rejects bool, since
    Python's bool is a subclass of int and would otherwise pass silently."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _parse_timestamp(value):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError('Expected timezone-aware ISO 8601 timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp must include a timezone')
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError as error:
        raise ValueError('Timestamp is outside the supported UTC range') from error


def _is_valid_iso8601(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        _parse_timestamp(value)
        return True
    except ValueError:
        return False


def validate_signals(thing: dict, result: VerificationResult) -> None:
    signals = thing.get("features", {}).get("signals", {}).get("properties")
    if signals is None:
        result.add_error("Missing 'signals' feature entirely")
        return
    for field_name in REQUIRED_SIGNAL_FIELDS:
        if field_name not in signals or signals[field_name] is None:
            result.add_error(f"Missing signal field: {field_name}")

    for field_name in NUMERIC_SIGNAL_FIELDS:
        value = signals.get(field_name)
        if value is not None and not _is_valid_number(value):
            result.add_error(f"Signal field {field_name} is not a valid finite number: {value!r}")

    source_ts = signals.get("sourceTimestamp")
    if source_ts is not None and not _is_valid_iso8601(source_ts):
        result.add_error(f"sourceTimestamp is not valid ISO 8601: {source_ts!r}")

    tire = signals.get("tirePressurePsi")
    if isinstance(tire, dict):
        for wheel in REQUIRED_TIRE_FIELDS:
            if wheel not in tire or tire[wheel] is None:
                result.add_error(f"Missing tire pressure field: {wheel}")
            elif not _is_valid_number(tire[wheel]):
                result.add_error(f"Tire pressure field {wheel} is not a valid finite number: {tire[wheel]!r}")
    elif tire is not None:
        result.add_error("tirePressurePsi is present but not an object")


def validate_health(thing: dict, result: VerificationResult) -> None:
    health = thing.get("features", {}).get("health", {}).get("properties")
    if health is None:
        result.add_error("Missing 'health' feature entirely")
        return
    for field_name in REQUIRED_HEALTH_FIELDS:
        if field_name not in health or (health[field_name] is None and field_name != "activeFaults"):
            result.add_error(f"Missing health field: {field_name}")

    status = health.get("status")
    if status is not None and (not isinstance(status, str) or status not in VALID_HEALTH_STATUSES):
        result.add_error(f"Unrecognized health status: {status!r}")
    if status in ("WARNING", "CRITICAL") and not health.get("activeFaults"):
        result.add_error(f"health.status is {status} but activeFaults is empty")

    fault_count = health.get("faultCount")
    active_faults = health.get("activeFaults")
    if type(fault_count) is not int or fault_count < 0:
        result.add_error('faultCount must be a nonnegative integer')
    if not isinstance(active_faults, list) or not all(isinstance(code, str) and code for code in active_faults):
        result.add_error('activeFaults must be an array of nonempty fault codes')
    elif len(set(active_faults)) != len(active_faults):
        result.add_error('activeFaults must contain unique codes')
    if status == 'HEALTHY' and active_faults:
        result.add_error('health.status is HEALTHY but activeFaults is not empty')
    if fault_count is not None and isinstance(active_faults, list) and fault_count != len(active_faults):
        result.add_error(
            f"faultCount ({fault_count}) does not match activeFaults length ({len(active_faults)})"
        )


def validate_correlated_faults(thing: dict, result: VerificationResult) -> None:
    """Checks an active correlated fault hasn't fully recovered while
    still being reported as active ('Correlated-fault status matches the
    signal values', docs/10).

    Only flags the case where BOTH recovery conditions are already met -
    that's the one unambiguous inconsistency a single snapshot can prove.
    Does NOT flag the hysteresis zone (between recovery and activation
    thresholds) or a fully-abnormal state, since the contract's own
    hysteresis design means a fault legitimately stays active through
    both of those - flagging them would be a false positive, not a
    real defect.
    """
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    signals = thing.get("features", {}).get("signals", {}).get("properties", {})
    active_faults = health.get("activeFaults", [])

    for code, rules in CORRELATED_FAULT_RULES.items():
        if code not in active_faults:
            continue

        recovery_checks = []
        for signal_name, rule in rules.items():
            value = signals.get(signal_name)
            if value is None or not _is_valid_number(value):
                result.add_error(
                    f"Correlated fault {code} is active but {signal_name} is missing or invalid"
                )
                recovery_checks.append(False)
                continue
            recovered = (
                value <= rule["recovery_threshold"]
                if rule["direction"] == "above"
                else value >= rule["recovery_threshold"]
            )
            recovery_checks.append(recovered)
        if all(recovery_checks):
            result.add_error(
                f"Correlated fault {code} is active but both temperatureCelsius "
                "and coolantPressureKpa have recovered past their thresholds"
            )


def validate_active_fault_details(thing: dict, result: VerificationResult) -> None:
    """For each active correlated fault, checks diagnostics.activeFaultDetails
    has a matching, complete record per docs/10's Fault Contract.

    Scoped to correlated faults only - single-signal faults (BATTERY_LOW,
    etc.) predate this feature and aren't required to populate it.
    """
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    diagnostics = thing.get("features", {}).get("diagnostics", {}).get("properties", {})
    active_faults = health.get("activeFaults", [])
    details = diagnostics.get("activeFaultDetails", [])

    for code in CORRELATED_FAULT_RULES:
        if code not in active_faults:
            continue
        detail = next((d for d in details if isinstance(d, dict) and d.get("code") == code), None)
        if detail is None:
            result.add_error(
                f"Correlated fault {code} is active but no matching entry exists "
                f"in diagnostics.activeFaultDetails"
            )
            continue
        for field_name in REQUIRED_ACTIVE_FAULT_DETAIL_FIELDS:
            if field_name not in detail or detail[field_name] is None:
                result.add_error(f"activeFaultDetails[{code}] is missing field: {field_name}")
        for field_name in ('observedValues', 'activationThresholds', 'recoveryThresholds'):
            if field_name in detail and not isinstance(detail[field_name], dict):
                result.add_error(f'activeFaultDetails[{code}].{field_name} must be an object')
        if 'affectedSignals' in detail and (not isinstance(detail['affectedSignals'], list) or
                not all(isinstance(signal, str) for signal in detail['affectedSignals'])):
            result.add_error(f'activeFaultDetails[{code}].affectedSignals must be an array of strings')

        detected_at = detail.get("detectedAt")
        if detected_at is not None and not _is_valid_iso8601(detected_at):
            result.add_error(f"activeFaultDetails[{code}].detectedAt is not valid ISO 8601: {detected_at!r}")


def validate_freshness(thing: dict, result: VerificationResult, max_age_seconds: float, now: datetime = None) -> None:
    now = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime):
        result.add_error('Evaluation clock must return a timezone-aware datetime')
        return
    try:
        now = _parse_timestamp(now.isoformat())
    except ValueError:
        result.add_error('Evaluation clock must be timezone-aware')
        return
    for feature, field_name in [('signals', 'sourceTimestamp'), ('health', 'processedTimestamp')]:
        raw_ts = thing['features'].get(feature, {}).get('properties', {}).get(field_name)
        try:
            timestamp = _parse_timestamp(raw_ts)
        except (ValueError, TypeError):
            result.add_error(f'{field_name} is missing or not timezone-aware ISO 8601')
            continue
        age_seconds = (now - timestamp).total_seconds()
        if age_seconds < -1:
            result.add_error(f'{field_name} is more than 1 second in the future')
        elif age_seconds > max_age_seconds:
            result.add_error(f'Stale digital twin: {field_name} is {age_seconds:.1f}s old (max allowed {max_age_seconds}s)')
    details = thing['features'].get('diagnostics', {}).get('properties', {}).get('activeFaultDetails', [])
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            result.add_error(f'activeFaultDetails[{index}] must be an object')
            continue
        for field_name in ('detectedAt', 'clearedAt'):
            if detail.get(field_name) is None:
                continue  # detectedAt is required above for an active correlated record
            try:
                timestamp = _parse_timestamp(detail[field_name])
            except (ValueError, TypeError):
                result.add_error(f'activeFaultDetails[{index}].{field_name} must be timezone-aware ISO 8601')
                continue
            if (timestamp - now).total_seconds() > 1:
                result.add_error(f'activeFaultDetails[{index}].{field_name} is more than 1 second in the future')


def verify_vehicle_state(
    ditto_url: str = DEFAULT_DITTO_URL,
    thing_id: str = DEFAULT_THING_ID,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    *,
    clock=None,
) -> VerificationResult:
    result = VerificationResult(ok=True)
    if not _is_valid_number(max_age_seconds) or max_age_seconds <= 0:
        result.add_error('max_age_seconds must be a finite positive number')
        return result
    try:
        thing = fetch_thing(ditto_url, thing_id)
    except (requests.RequestException, ValueError):
        result.add_error('Failed to query Ditto or decode its JSON response')
        return result

    result.thing = thing
    if not isinstance(thing, dict):
        result.add_error('Thing must be an object')
        return result
    vehicle_id = thing_id.removeprefix('sdv:') if isinstance(thing_id, str) else None
    if (vehicle_id not in ('vehicle-001', 'vehicle-002') or thing_id != f'sdv:{vehicle_id}' or
            thing.get('thingId') != thing_id or not isinstance(thing.get('attributes'), dict) or
            thing['attributes'].get('vehicleId') != vehicle_id):
        result.add_error('Requested and returned vehicle/Thing identity do not match')
        return result
    features = thing.get('features')
    if not isinstance(features, dict):
        result.add_error('features must be an object')
        return result
    for name in ('signals', 'health', 'diagnostics'):
        if name in features and (not isinstance(features[name], dict) or
                not isinstance(features[name].get('properties'), dict)):
            result.add_error(f'{name}.properties must be an object')
    if not result.ok:
        return result
    health = features.get('health', {}).get('properties', {})
    details = features.get('diagnostics', {}).get('properties', {}).get('activeFaultDetails', [])
    if not isinstance(health.get('activeFaults', []), list) or not isinstance(details, list):
        result.add_error('activeFaults and activeFaultDetails must be arrays')
        return result
    validate_signals(thing, result)
    validate_health(thing, result)
    validate_correlated_faults(thing, result)
    validate_active_fault_details(thing, result)
    validate_freshness(thing, result, max_age_seconds,
                       now=clock() if clock else datetime.now(timezone.utc))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ditto-url", default=DEFAULT_DITTO_URL)
    parser.add_argument("--thing-id", default=DEFAULT_THING_ID)
    parser.add_argument("--publication-interval-seconds", type=float, default=None)
    parser.add_argument("--max-age-seconds", type=float, default=None)
    args = parser.parse_args()

    try:
        max_age = compute_max_age_seconds(args.publication_interval_seconds, args.max_age_seconds)
    except ValueError as error:
        parser.error(str(error))
    result = verify_vehicle_state(args.ditto_url, args.thing_id, max_age)

    if result.ok:
        print(f"OK: {args.thing_id} is valid and fresh (<= {max_age:.1f}s old)")
        return 0

    print(f"FAILED: {args.thing_id} validation errors:")
    for error in result.errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
