"""Pure C5 observation replay state. Callers own authorization and durable writes."""

from hashlib import sha256
import re

from .c5_fingerprint import EnvelopeFingerprint, fingerprint_decoded_envelope
from .mqtt_ingress import EventError, V2_VEHICLES, WatermarkError, timestamp_key

_MAX_SAFE_INTEGER = 2**53 - 1
_DIGEST = re.compile(r"[0-9a-f]{64}")
_STATE_FIELDS = {
    "version", "vehicleId", "sessionId", "sessionGeneration", "transitionId",
    "pendingSuccessor", "observationCount", "observationIds", "latest",
}
_REFERENCE_FIELDS = (
    "eventId", "sessionId", "sessionGeneration", "sequence", "frame", "sourceTimestamp",
)


def _identifier(value):
    if type(value) is not str or not value or value.strip() != value:
        return False
    return not any(0xD800 <= ord(char) <= 0xDFFF for char in value)


def _integer(value, minimum):
    return type(value) is int and minimum <= value <= _MAX_SAFE_INTEGER


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _id_key(event_id):
    return sha256(event_id.encode("utf-8")).hexdigest()


def _state_require(condition):
    if not condition:
        raise WatermarkError("INVALID_C5_REPLAY_STATE")


def _valid_reference(value):
    return (
        _identifier(value["eventId"])
        and _identifier(value["sessionId"])
        and _integer(value["sessionGeneration"], 1)
        and _integer(value["sequence"], 0)
        and _integer(value["frame"], 0)
        and type(value["sourceTimestamp"]) is str
    )


def new_ledger(vehicle_id: str, session_id: str, generation: int) -> dict:
    """Initialize an empty, externally provisioned initial generation."""
    return load_ledger({
        "version": 1,
        "vehicleId": vehicle_id,
        "sessionId": session_id,
        "sessionGeneration": generation,
        "transitionId": None,
        "pendingSuccessor": False,
        "observationCount": 0,
        "observationIds": {},
        "latest": None,
    })


def load_ledger(state: dict) -> dict:
    """Validate and detach stored version-1 state without establishing trust in it."""
    _state_require(type(state) is dict and state.keys() == _STATE_FIELDS)
    _state_require(type(state["version"]) is int and state["version"] == 1)
    _state_require(type(state["vehicleId"]) is str and state["vehicleId"] in V2_VEHICLES)
    _state_require(_identifier(state["sessionId"]))
    generation = state["sessionGeneration"]
    _state_require(_integer(generation, 1))
    transition = state["transitionId"]
    _state_require(transition is None if generation == 1 else _identifier(transition))
    pending = state["pendingSuccessor"]
    _state_require(type(pending) is bool)

    ids = state["observationIds"]
    count = state["observationCount"]
    _state_require(type(ids) is dict and _integer(count, 0) and count == len(ids))
    _state_require(all(_digest(key) and flag is True for key, flag in ids.items()))
    latest = state["latest"]
    if latest is None:
        _state_require(not pending and not ids and generation == 1)
    else:
        _state_require(type(latest) is dict and latest.keys() == {*_REFERENCE_FIELDS, "fingerprint"})
        _state_require(_valid_reference(latest) and _digest(latest["fingerprint"]))
        try:
            timestamp_key(latest["sourceTimestamp"])
        except EventError as error:
            raise WatermarkError("INVALID_C5_REPLAY_STATE") from error
        if pending:
            _state_require(not ids and latest["sessionGeneration"] < generation
                           and latest["sessionId"] != state["sessionId"])
        else:
            _state_require(latest["sessionGeneration"] == generation
                           and latest["sessionId"] == state["sessionId"]
                           and count <= min(latest["sequence"], latest["frame"]) + 1
                           and _id_key(latest["eventId"]) in ids)

    return dict(state, observationIds=ids.copy(), latest=None if latest is None else latest.copy())


def record_observation(
    state: dict,
    observation: EnvelopeFingerprint,
    *,
    max_observations: int,
    max_membership_bytes: int | None = None,
) -> dict | None:
    """Return prospective state, or None for an exact latest-observation retry.

    Supply a health fingerprint and a trusted ledger snapshot. The supplied
    digest is checked against a fresh fingerprint of the envelope. A result
    does not authorize a generation, commit data or permit an ACK. Projection
    and status state are outside this observation model.
    """
    if not _integer(max_observations, 1) or (
        max_membership_bytes is not None and not _integer(max_membership_bytes, 1)
    ):
        raise WatermarkError("INVALID_C5_REPLAY_CAPACITY")

    next_state = load_ledger(state)
    if not isinstance(observation, EnvelopeFingerprint) or type(observation.envelope) is not dict:
        raise EventError("INVALID_TYPE")
    event = observation.envelope
    if event.get("vehicleId") != next_state["vehicleId"]:
        raise EventError("TOPIC_MISMATCH")
    if not all(field in event for field in _REFERENCE_FIELDS) or not _valid_reference(event):
        raise EventError("INVALID_TYPE")
    if not _digest(observation.sha256):
        raise EventError("INVALID_TYPE")
    generation = event["sessionGeneration"]
    if generation < next_state["sessionGeneration"]:
        raise EventError("OUT_OF_ORDER")
    if generation != next_state["sessionGeneration"] or event["sessionId"] != next_state["sessionId"]:
        raise EventError("UNREGISTERED_SESSION")

    latest = next_state["latest"]
    pending = next_state["pendingSuccessor"]
    ids = next_state["observationIds"]
    verified = fingerprint_decoded_envelope(f"sdv/{next_state['vehicleId']}/v2/health", event)
    event = verified.envelope
    key = _id_key(event["eventId"])
    if verified.sha256 != observation.sha256 or verified.canonical_bytes != observation.canonical_bytes:
        raise EventError("EVENT_ID_CONFLICT" if key in ids else "INVALID_TYPE")

    source = timestamp_key(event["sourceTimestamp"])
    if key in ids:
        if (latest["fingerprint"] == verified.sha256
                and all(latest[field] == event[field] for field in _REFERENCE_FIELDS)):
            return None
        raise EventError("EVENT_ID_CONFLICT")
    if latest is not None and (
        source <= timestamp_key(latest["sourceTimestamp"]) or (
            not pending and (event["sequence"] <= latest["sequence"] or event["frame"] <= latest["frame"])
        )
    ):
        raise EventError("OUT_OF_ORDER")

    count = next_state["observationCount"] + 1
    # Compact JSON for a nonempty map of 64-hex keys to true uses 72n + 1 bytes.
    if count > max_observations or (
        max_membership_bytes is not None and 72 * count + 1 > max_membership_bytes
    ):
        raise WatermarkError("C5_REPLAY_CAPACITY")

    ids[key] = True
    next_state["observationCount"] = count
    next_state["latest"] = {
        **{field: event[field] for field in _REFERENCE_FIELDS},
        "fingerprint": verified.sha256,
    }
    next_state["pendingSuccessor"] = False
    return next_state
