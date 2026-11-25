"""Persisted, strictly increasing session generation per V2-C2 restarts."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from session_state import claim_session  # noqa: E402

T0 = datetime(2026, 11, 25, 12, 0, 0, 500000, tzinfo=timezone.utc)


def test_first_session_is_generation_one(tmp_path):
    assert claim_session(tmp_path / "state.json", session_id="a", utc_origin=T0) == 1


def test_each_later_session_gets_the_next_generation(tmp_path):
    path = tmp_path / "state.json"
    claim_session(path, session_id="a", utc_origin=T0)
    claim_session(path, session_id="b", utc_origin=T0 + timedelta(seconds=60))
    assert claim_session(path, session_id="c", utc_origin=T0 + timedelta(seconds=120)) == 3


def test_claim_is_persisted_before_returning(tmp_path):
    path = tmp_path / "state.json"
    claim_session(path, session_id="a", utc_origin=T0)
    assert json.loads(path.read_text()) == {
        "sessionGeneration": 1, "sessionId": "a", "utcOrigin": "2026-11-25T12:00:00.500000Z"}


def test_utc_origin_must_not_roll_backwards(tmp_path):
    path = tmp_path / "state.json"
    claim_session(path, session_id="a", utc_origin=T0)
    with pytest.raises(ValueError, match="UTC"):
        claim_session(path, session_id="b", utc_origin=T0)
    assert json.loads(path.read_text())["sessionGeneration"] == 1


def test_reused_session_id_is_rejected(tmp_path):
    path = tmp_path / "state.json"
    claim_session(path, session_id="a", utc_origin=T0)
    with pytest.raises(ValueError, match="session"):
        claim_session(path, session_id="a", utc_origin=T0 + timedelta(seconds=1))


def test_corrupt_state_is_not_reset_to_one(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json")
    with pytest.raises(ValueError):
        claim_session(path, session_id="a", utc_origin=T0)
