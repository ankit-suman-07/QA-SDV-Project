import copy
import json
from pathlib import Path

import pytest

from ditto.c5_fingerprint import (
    EventError,
    canonicalize_json,
    fingerprint_envelope,
    validate_status_reference,
)

FIXTURES = Path(__file__).parent / "fixtures/v2/status"
ORIGINAL = json.loads((FIXTURES / "fingerprint-vectors.json").read_bytes())
ENVELOPES = json.loads((FIXTURES / "envelope-vectors.json").read_bytes())
HEALTH = "sdv/vehicle-003/v2/health"
STATUS = "sdv/vehicle-003/v2/status"


def evaluate(case, context):
    raw = case["inputJson"].encode("utf-8")
    if case.get("kind") == "jcs":
        return canonicalize_json(raw)
    topic = case.get("topic") or (STATUS if case["kind"] == "status" else HEALTH)
    result = fingerprint_envelope(topic, raw)
    if topic == STATUS:
        validate_status_reference(result.envelope, context, source_silent=False)
    return result.canonical_bytes, result.sha256


@pytest.mark.parametrize("case", ORIGINAL["accepted"], ids=lambda x: x["id"])
def test_original_accepted(case):
    assert evaluate(case, ORIGINAL["statusContext"]) == (
        bytes.fromhex(case["canonicalUtf8Hex"]), case["sha256"]
    )


@pytest.mark.parametrize("case", ORIGINAL["rejected"], ids=lambda x: x["id"])
def test_original_rejected(case):
    with pytest.raises(EventError) as exc:
        evaluate(case, ORIGINAL["statusContext"])
    assert exc.value.code == case["reason"]


@pytest.mark.parametrize("case", ENVELOPES["cases"], ids=lambda x: x["id"])
def test_strict_envelope(case):
    expected = case["expected"]
    if expected["validation"] == "REJECT":
        with pytest.raises(EventError) as exc:
            evaluate(case, ENVELOPES["statusContext"])
        assert exc.value.code == expected["reason"]
    else:
        assert evaluate(case, ENVELOPES["statusContext"]) == (
            bytes.fromhex(expected["canonicalUtf8Hex"]), expected["sha256"]
        )


def test_unavailable_lidar_requires_explicit_null():
    case = next(x for x in ENVELOPES["cases"] if x["id"] == "health-required-null-distance")
    envelope = json.loads(case["inputJson"])
    assert fingerprint_envelope(HEALTH, case["inputJson"].encode()).envelope == envelope
    del envelope["lidar"]["distanceMeters"]
    with pytest.raises(EventError) as exc:
        fingerprint_envelope(HEALTH, json.dumps(envelope).encode())
    assert exc.value.code == "MISSING_FIELD"


def test_wire_input_and_reference_are_unchanged_by_fingerprinting():
    raw = next(x for x in ENVELOPES["cases"] if x["id"] == "health-minimal-optionals-absent")["inputJson"].encode()
    original = json.loads(raw)
    health = fingerprint_envelope(HEALTH, raw)
    status_raw = next(x for x in ENVELOPES["cases"] if x["id"] == "status-minimal")["inputJson"].encode()
    status = fingerprint_envelope(STATUS, status_raw)
    context = copy.deepcopy(ENVELOPES["statusContext"])
    validate_status_reference(status.envelope, context, source_silent=False)
    assert context == ENVELOPES["statusContext"]
    assert health.envelope == original == json.loads(raw)
    assert status.envelope == json.loads(status_raw)
    assert health.sha256 != status.sha256


def test_invalid_utf8_is_rejected():
    with pytest.raises(EventError) as exc:
        canonicalize_json(b'{"key":"\xff"}')
    assert exc.value.code == "INVALID_UNICODE"


def test_oversized_wire_body_is_rejected():
    with pytest.raises(EventError) as exc:
        fingerprint_envelope(HEALTH, b" " * 65537)
    assert exc.value.code == "MALFORMED_JSON"


@pytest.fixture
def status_reference_inputs():
    case = next(x for x in ENVELOPES["cases"] if x["id"] == "status-minimal")
    return json.loads(case["inputJson"]), copy.deepcopy(ENVELOPES["statusContext"])


@pytest.mark.parametrize("path,value,code", [
    (("sessionGeneration",), True, "INVALID_TYPE"),
    (("sessionGeneration",), 0, "INVALID_TYPE"),
    (("sessionGeneration",), 2**53, "INVALID_TYPE"),
    (("observationRef", "sequence"), False, "INVALID_OBSERVATION_REF"),
    (("observationRef", "sequence"), -1, "INVALID_OBSERVATION_REF"),
    (("observationRef", "sequence"), 2**53, "INVALID_OBSERVATION_REF"),
    (("observationRef", "frame"), True, "INVALID_OBSERVATION_REF"),
    (("observationRef", "frame"), 100.0, "INVALID_OBSERVATION_REF"),
    (("sessionId",), " session-1", "INVALID_TYPE"),
    (("vehicleId",), [], "INVALID_TYPE"),
    (("observationRef",), [], "INVALID_OBSERVATION_REF"),
    (("observationRef", "eventId"), "", "INVALID_OBSERVATION_REF"),
    (("observationRef", "sourceTimestamp"), 0, "INVALID_TIMESTAMP"),
    (("health",), [], "INVALID_HEALTH"),
    (("faults",), "LIDAR_SENSOR_FAILURE", "HEALTH_FAULT_MISMATCH"),
])
def test_accepted_context_rejects_invalid_values(status_reference_inputs, path, value, code):
    event, accepted = status_reference_inputs
    parent = accepted if len(path) == 1 else accepted[path[0]]
    parent[path[-1]] = value
    before = copy.deepcopy((event, accepted))
    with pytest.raises(EventError) as exc:
        validate_status_reference(event, accepted, source_silent=False)
    assert exc.value.code == code
    assert (event, accepted) == before


@pytest.mark.parametrize("field", [
    "vehicleId", "sessionId", "sessionGeneration", "observationRef", "health", "faults",
])
def test_accepted_context_requires_each_field(status_reference_inputs, field):
    event, accepted = status_reference_inputs
    del accepted[field]
    with pytest.raises(EventError) as exc:
        validate_status_reference(event, accepted, source_silent=False)
    assert exc.value.code == "MISSING_FIELD"


@pytest.mark.parametrize("accepted,code", [
    ({}, "MISSING_FIELD"), (None, "INVALID_TYPE"), ([], "INVALID_TYPE"),
])
def test_accepted_context_rejects_malformed_mapping(status_reference_inputs, accepted, code):
    event, _ = status_reference_inputs
    with pytest.raises(EventError) as exc:
        validate_status_reference(event, accepted, source_silent=False)
    assert exc.value.code == code


def test_accepted_context_requires_nested_fields(status_reference_inputs):
    event, accepted = status_reference_inputs
    del accepted["observationRef"]["frame"]
    with pytest.raises(EventError) as exc:
        validate_status_reference(event, accepted, source_silent=False)
    assert exc.value.code == "INVALID_OBSERVATION_REF"


@pytest.mark.parametrize("matches", [True, False])
def test_accepted_context_comparison_preserves_inputs(status_reference_inputs, matches):
    event, accepted = status_reference_inputs
    if not matches:
        accepted["observationRef"]["frame"] += 1
    before = copy.deepcopy((event, accepted))
    if matches:
        validate_status_reference(event, accepted, source_silent=False)
    else:
        with pytest.raises(EventError) as exc:
            validate_status_reference(event, accepted, source_silent=False)
        assert exc.value.code == "REFERENCE_MISMATCH"
    assert (event, accepted) == before
