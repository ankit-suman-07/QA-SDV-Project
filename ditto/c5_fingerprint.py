"""Standalone strict C5 wire validation and RFC 8785 fingerprints."""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import rfc8785

from .mqtt_ingress import (
    EventError,
    MAX_PAYLOAD_BYTES,
    V2_VEHICLES,
    _require,
    parse_timestamp,
    validate_v2_health,
)

_MAX_SAFE_INTEGER = 2**53 - 1
_HEALTH_REQUIRED = frozenset("""
    schemaVersion vehicleId eventId sessionId sessionGeneration sequence frame
    simulationSeconds sourceTimestamp processingTimestamp provenance lidar
    health faults recoveryState recoveryStartedAt sourceSilent
""".split())
_HEALTH_OPTIONAL = frozenset({"actionId", "traceId", "velocityMetersPerSecond"})
_STATUS_REQUIRED = frozenset("""
    schemaVersion vehicleId sessionId sessionGeneration statusEventId
    statusRevision evaluationTimestamp observationRef recoveryState
    recoveryStartedAt sourceSilent health faults
""".split())
_OBSERVATION_REF = frozenset({"eventId", "sequence", "frame", "sourceTimestamp"})
_STATUS_FAULTS = {
    "HEALTHY": ([],),
    "WARNING": (["LIDAR_OBSTRUCTION"],),
    "CRITICAL": (["LIDAR_OBSTRUCTION"], ["LIDAR_SENSOR_FAILURE"]),
}


@dataclass(frozen=True)
class EnvelopeFingerprint:
    """Decoded wire fields and the digest of the scoped canonical bytes."""

    envelope: dict
    canonical_bytes: bytes
    sha256: str


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _safe_integer(token):
    _require(len(token.lstrip("-")) <= 16, "UNSAFE_INTEGER")
    value = int(token)
    _require(abs(value) <= _MAX_SAFE_INTEGER, "UNSAFE_INTEGER")
    return value


def _finite_float(token):
    value = float(token)
    _require(math.isfinite(value), "NUMERIC_OVERFLOW")
    significand = token.lower().split("e", 1)[0]
    _require(value != 0 or not any(c in "123456789" for c in significand),
             "NUMERIC_UNDERFLOW")
    return value


def _reject_nonfinite(_token):
    raise EventError("NONFINITE_NUMBER")


def _decode(raw):
    """Decode UTF-8 bytes without losing integer token kinds or duplicate keys."""
    _require(isinstance(raw, bytes), "INVALID_TYPE")
    _require(len(raw) <= MAX_PAYLOAD_BYTES, "MALFORMED_JSON")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_int=_safe_integer,
            parse_float=_finite_float,
            parse_constant=_reject_nonfinite,
        )
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                pending.extend(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, str):
                item.encode("utf-8")
    except UnicodeError as error:
        raise EventError("INVALID_UNICODE") from error
    except (json.JSONDecodeError, RecursionError) as error:
        raise EventError("MALFORMED_JSON") from error
    return value


def _fingerprint(value):
    try:
        canonical = rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, RecursionError) as error:
        raise EventError("MALFORMED_JSON") from error
    return canonical, sha256(canonical).hexdigest()


def canonicalize_json(raw: bytes) -> tuple[bytes, str]:
    """Canonicalize a strict JSON value independent of the C5 envelope schemas."""
    return _fingerprint(_decode(raw))


def _object_fields(value, required, optional=(), *, invalid="INVALID_TYPE",
                   missing="MISSING_FIELD"):
    _require(isinstance(value, dict), invalid)
    _require(not value.keys() - required - set(optional), "UNKNOWN_FIELD")
    _require(required <= value.keys(), missing)


def _identifier(value):
    return isinstance(value, str) and bool(value) and value.strip() == value


def _validate_status(topic, event):
    _object_fields(event, _STATUS_REQUIRED)
    _require(event["schemaVersion"] == "2.0.0", "UNSUPPORTED_VERSION")
    vehicle = event["vehicleId"]
    _require(vehicle in V2_VEHICLES, "UNKNOWN_VEHICLE")
    _require(topic == f"sdv/{vehicle}/v2/status", "TOPIC_MISMATCH")
    for field in ("sessionId", "statusEventId"):
        _require(_identifier(event[field]), "INVALID_TYPE")
    for field in ("sessionGeneration", "statusRevision"):
        _require(type(event[field]) is int and event[field] >= 1, "INVALID_TYPE")
    parse_timestamp(event["evaluationTimestamp"])

    ref = event["observationRef"]
    _object_fields(ref, _OBSERVATION_REF, invalid="INVALID_OBSERVATION_REF",
                   missing="INVALID_OBSERVATION_REF")
    _require(_identifier(ref["eventId"]), "INVALID_OBSERVATION_REF")
    for field in ("sequence", "frame"):
        _require(type(ref[field]) is int and ref[field] >= 0, "INVALID_OBSERVATION_REF")
    parse_timestamp(ref["sourceTimestamp"])

    _require(event["recoveryState"] == "NONE" and event["recoveryStartedAt"] is None,
             "INVALID_TYPE")
    _require(type(event["sourceSilent"]) is bool, "INVALID_TYPE")
    health = event["health"]
    _require(isinstance(health, str) and health in _STATUS_FAULTS, "INVALID_HEALTH")
    _require(event["faults"] in _STATUS_FAULTS[health], "HEALTH_FAULT_MISMATCH")


def validate_status_reference(event: dict, accepted: dict, *, source_silent: bool) -> None:
    """Validate a new, schema-checked status against caller-supplied accepted state.

    Call after exact-retry reconciliation. This check does not authorize
    sessions, look up history, advance revisions, or modify either input.
    """
    fields = ("vehicleId", "sessionId", "sessionGeneration", "observationRef")
    _require(isinstance(accepted, dict) and type(source_silent) is bool, "INVALID_TYPE")
    _require(all(field in accepted for field in (*fields, "health", "faults")), "MISSING_FIELD")
    _require(type(accepted["vehicleId"]) is str and accepted["vehicleId"] in V2_VEHICLES,
             "INVALID_TYPE")
    _require(type(accepted["sessionId"]) is str and _identifier(accepted["sessionId"]),
             "INVALID_TYPE")
    generation = accepted["sessionGeneration"]
    _require(type(generation) is int and 1 <= generation <= _MAX_SAFE_INTEGER, "INVALID_TYPE")

    ref = accepted["observationRef"]
    _object_fields(ref, _OBSERVATION_REF, invalid="INVALID_OBSERVATION_REF",
                   missing="INVALID_OBSERVATION_REF")
    _require(type(ref["eventId"]) is str and _identifier(ref["eventId"]),
             "INVALID_OBSERVATION_REF")
    for field in ("sequence", "frame"):
        value = ref[field]
        _require(type(value) is int and 0 <= value <= _MAX_SAFE_INTEGER, "INVALID_OBSERVATION_REF")
    parse_timestamp(ref["sourceTimestamp"])

    health = accepted["health"]
    _require(type(health) is str and health in _STATUS_FAULTS, "INVALID_HEALTH")
    _require(accepted["faults"] in _STATUS_FAULTS[health], "HEALTH_FAULT_MISMATCH")

    # The status envelope is already schema-checked. The context above has
    # now passed the same identity and integer type checks before equality.
    _require(all(event[field] == accepted[field] for field in fields), "REFERENCE_MISMATCH")
    _require((event["health"], event["faults"]) == (accepted["health"], accepted["faults"]),
             "HEALTH_FAULT_MISMATCH")
    _require(event["sourceSilent"] or not source_silent, "INVALID_TYPE")


def fingerprint_envelope(topic: str, raw: bytes) -> EnvelopeFingerprint:
    """Validate wire shape and fingerprint health or status without side effects.

    Stateful status reference checks are separate so a historical exact retry
    can be reconciled before checking the current accepted observation.
    """
    _require(isinstance(topic, str), "TOPIC_MISMATCH")
    event = _decode(raw)
    if topic.endswith("/v2/health"):
        _object_fields(event, _HEALTH_REQUIRED, _HEALTH_OPTIONAL)
        _object_fields(event["lidar"], {"sensorAvailable", "distanceMeters"})
        if "velocityMetersPerSecond" in event:
            _object_fields(event["velocityMetersPerSecond"], {"x", "y", "z"},
                           missing="INVALID_TYPE")
        validate_v2_health(topic, event)
        for field in ("eventId", "sessionId"):
            _require(_identifier(event[field]), "INVALID_TYPE")
        message_type = "v2-health-observation"
    elif topic.endswith("/v2/status"):
        _validate_status(topic, event)
        message_type = "v2-status"
    else:
        raise EventError("TOPIC_MISMATCH")

    scoped = {
        "messageType": message_type,
        "schemaVersion": event["schemaVersion"],
        "payload": {key: value for key, value in event.items() if key != "schemaVersion"},
    }
    canonical, digest = _fingerprint(scoped)
    return EnvelopeFingerprint(event, canonical, digest)
