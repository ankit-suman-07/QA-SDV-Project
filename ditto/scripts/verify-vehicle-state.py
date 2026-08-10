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
# the activation side is checked - see validate_correlated_faults.
CORRELATED_FAULT_RULES = {
    "COOLING_SYSTEM_FAILURE": {
        "temperatureCelsius": {"activation_threshold": 105.0, "direction": "above"},
        "coolantPressureKpa": {"activation_threshold": 150.0, "direction": "below"},
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
    return math.isfinite(value)


def _is_valid_iso8601(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
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
    if status is not None and status not in VALID_HEALTH_STATUSES:
        result.add_error(f"Unrecognized health status: {status!r}")
    if status in ("WARNING", "CRITICAL") and not health.get("activeFaults"):
        result.add_error(f"health.status is {status} but activeFaults is empty")

    fault_count = health.get("faultCount")
    active_faults = health.get("activeFaults")
    if fault_count is not None and isinstance(active_faults, list) and fault_count != len(active_faults):
        result.add_error(
            f"faultCount ({fault_count}) does not match activeFaults length ({len(active_faults)})"
        )


def validate_correlated_faults(thing: dict, result: VerificationResult) -> None:
    """Checks an active correlated fault is justified by current signal
    values ('Correlated-fault status matches the signal values', docs/10).

    Only the activation direction is checked. Checking the reverse would
    false-positive: the contract's hysteresis design lets signals sit
    between activation and recovery thresholds while a fault stays active
    - correct behaviour, not a violation.
    """
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    signals = thing.get("features", {}).get("signals", {}).get("properties", {})
    active_faults = health.get("activeFaults", [])

    for code, rules in CORRELATED_FAULT_RULES.items():
        if code not in active_faults:
            continue
        for signal_name, rule in rules.items():
            value = signals.get(signal_name)
            if value is None or not _is_valid_number(value):
                result.add_error(
                    f"Correlated fault {code} is active but {signal_name} is missing or invalid"
                )
                continue
            breached = (
                value >= rule["activation_threshold"]
                if rule["direction"] == "above"
                else value <= rule["activation_threshold"]
            )
            if not breached:
                result.add_error(
                    f"Correlated fault {code} is active but {signal_name}={value} "
                    f"does not meet its activation threshold ({rule['direction']} "
                    f"{rule['activation_threshold']})"
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

        detected_at = detail.get("detectedAt")
        if detected_at is not None and not _is_valid_iso8601(detected_at):
            result.add_error(f"activeFaultDetails[{code}].detectedAt is not valid ISO 8601: {detected_at!r}")


def validate_freshness(thing: dict, result: VerificationResult, max_age_seconds: float, now: datetime = None) -> None:
    now = now if now is not None else datetime.now(timezone.utc)
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    raw_ts = health.get("processedTimestamp")
    if not raw_ts:
        return  # already reported by validate_health
    try:
        processed_ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
    except ValueError:
        result.add_error(f"processedTimestamp is not valid ISO 8601: {raw_ts!r}")
        return
    age_seconds = (now - processed_ts).total_seconds()
    if age_seconds > max_age_seconds:
        result.add_error(
            f"Stale digital twin: processedTimestamp is {age_seconds:.1f}s old "
            f"(max allowed {max_age_seconds}s)"
        )


def verify_vehicle_state(
    ditto_url: str = DEFAULT_DITTO_URL,
    thing_id: str = DEFAULT_THING_ID,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
) -> VerificationResult:
    result = VerificationResult(ok=True)
    try:
        thing = fetch_thing(ditto_url, thing_id)
    except requests.RequestException as exc:
        result.add_error(f"Failed to query Ditto: {exc}")
        return result

    result.thing = thing
    validate_signals(thing, result)
    validate_health(thing, result)
    validate_correlated_faults(thing, result)
    validate_active_fault_details(thing, result)
    validate_freshness(thing, result, max_age_seconds)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ditto-url", default=DEFAULT_DITTO_URL)
    parser.add_argument("--thing-id", default=DEFAULT_THING_ID)
    parser.add_argument("--publication-interval-seconds", type=float, default=None)
    parser.add_argument("--max-age-seconds", type=float, default=None)
    args = parser.parse_args()

    max_age = compute_max_age_seconds(args.publication_interval_seconds, args.max_age_seconds)
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