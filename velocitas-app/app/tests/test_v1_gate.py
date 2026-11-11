import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from v1_event import (  # noqa: E402
    Observation,
    ObservationGate,
    observation_from_datapoints,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(seconds=1)
T2 = T0 + timedelta(seconds=2)


@dataclass
class FakeDp:
    value: object
    timestamp: object


def make_gate():
    ids = iter(["id-1", "id-2", "id-3"])
    return ObservationGate("vehicle-002", id_factory=lambda vehicle: next(ids))


def obs(at, distance=35.0, available=True):
    return Observation(distance, available, at)


def test_observation_time_is_later_of_two_timestamps():
    result = observation_from_datapoints(FakeDp(7.0, T1), FakeDp(True, T2))
    assert result == Observation(7.0, True, T2)
    assert observation_from_datapoints(None, FakeDp(True, T2)).observed_at is None
    assert observation_from_datapoints(FakeDp(7.0, T1), None).observed_at is None
    assert (
        observation_from_datapoints(FakeDp(7.0, None), FakeDp(True, T2)).observed_at
        is None
    )


def test_gate_primes_on_first_observation_without_publishing():
    gate = make_gate()
    assert gate.next_event(obs(T0)) is None
    event = gate.next_event(obs(T1))
    assert event["eventId"] == "id-1"
    assert event["sourceTimestamp"] == "2026-01-01T00:00:01Z"
    assert event["vehicleId"] == "vehicle-002"


def test_gate_repeated_observation_returns_nothing_after_publish():
    gate = make_gate()
    gate.next_event(obs(T0))
    event = gate.next_event(obs(T1))
    gate.mark_published(event)
    assert gate.next_event(obs(T1)) is None


def test_gate_retries_pending_event_unchanged():
    gate = make_gate()
    gate.next_event(obs(T0))
    first = gate.next_event(obs(T1))
    again = gate.next_event(obs(T1))
    assert again == first
    assert again["eventId"] == "id-1"


def test_gate_newer_observation_replaces_pending():
    gate = make_gate()
    gate.next_event(obs(T0))
    gate.next_event(obs(T1))
    newer = gate.next_event(obs(T2, distance=3.0))
    assert newer["eventId"] == "id-2"
    assert newer["sourceTimestamp"] == "2026-01-01T00:00:02Z"
    assert newer["health"] == "CRITICAL"


def test_gate_ignores_observation_older_than_last_published():
    gate = make_gate()
    gate.next_event(obs(T0))
    gate.mark_published(gate.next_event(obs(T2)))
    assert gate.next_event(obs(T1)) is None


def test_gate_skips_invalid_observation_but_keeps_pending():
    gate = make_gate()
    gate.next_event(obs(T0))
    pending = gate.next_event(obs(T1))
    assert gate.next_event(Observation(True, True, T2)) == pending
    assert gate.next_event(Observation(5.0, True, None)) == pending


def test_gate_does_not_prime_on_invalid_observation():
    gate = make_gate()
    assert gate.next_event(Observation("bad", True, T0)) is None
    assert gate.next_event(obs(T1)) is None  # first valid observation primes
    assert gate.next_event(obs(T2))["eventId"] == "id-1"
