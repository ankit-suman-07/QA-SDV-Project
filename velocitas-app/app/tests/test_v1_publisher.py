import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from v1_event import Observation, ObservationGate  # noqa: E402
from v1_publisher import (  # noqa: E402
    ACK_TIMEOUT_SECONDS,
    deliver,
    pub_client_of,
    publish_v1_event,
)

TOPIC = "sdv/vehicle-002/health"
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(seconds=1)


class FakeInfo:
    def __init__(self, rc=0, published=True, wait_error=None):
        self.rc = rc
        self._published = published
        self._wait_error = wait_error
        self.wait_timeouts = []

    def wait_for_publish(self, timeout=None):
        self.wait_timeouts.append(timeout)
        if self._wait_error is not None:
            raise self._wait_error

    def is_published(self):
        return self._published


class FakeClient:
    def __init__(self, info=None, publish_error=None):
        self.info = info if info is not None else FakeInfo()
        self.publish_error = publish_error
        self.calls = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.calls.append((topic, payload, qos, retain))
        if self.publish_error is not None:
            raise self.publish_error
        return self.info


def run(coro):
    return asyncio.run(coro)


def test_publishes_at_qos1_without_retain_and_waits_for_ack():
    client = FakeClient()
    assert run(publish_v1_event(client, TOPIC, "{}")) is True
    assert client.calls == [(TOPIC, "{}", 1, False)]
    assert client.info.wait_timeouts == [ACK_TIMEOUT_SECONDS]


def test_unacknowledged_publish_is_a_failure():
    client = FakeClient(FakeInfo(published=False))
    assert run(publish_v1_event(client, TOPIC, "{}")) is False


def test_error_return_code_is_a_failure_without_waiting():
    client = FakeClient(FakeInfo(rc=4))
    assert run(publish_v1_event(client, TOPIC, "{}")) is False
    assert client.info.wait_timeouts == []


@pytest.mark.parametrize(
    "client",
    [
        FakeClient(publish_error=OSError("socket closed")),
        FakeClient(FakeInfo(wait_error=RuntimeError("publish failed"))),
        FakeClient(FakeInfo(wait_error=ValueError("not queued"))),
    ],
)
def test_publish_or_ack_errors_are_failures(client):
    assert run(publish_v1_event(client, TOPIC, "{}")) is False


def test_pub_client_of_returns_sdk_publisher_connection():
    class SdkClient:
        _pub_client = object()

    assert pub_client_of(SdkClient()) is SdkClient._pub_client


def test_pub_client_of_fails_clearly_without_sdk_publisher():
    with pytest.raises(RuntimeError, match="velocitas-sdk 0.15.7"):
        pub_client_of(object())


def _pending_event(gate):
    gate.next_event(Observation(35.0, True, T0))  # primes
    return gate.next_event(Observation(3.0, True, T1))


def test_failed_delivery_keeps_same_pending_event():
    gate = ObservationGate("vehicle-002")
    event = _pending_event(gate)

    ok = run(deliver(gate, event, FakeClient(FakeInfo(published=False)), TOPIC))

    assert ok is False
    retry = gate.next_event(Observation(3.0, True, T1))
    assert retry == event
    assert retry["eventId"] == event["eventId"]
    assert retry["sourceTimestamp"] == event["sourceTimestamp"]


def test_successful_delivery_clears_pending_event():
    gate = ObservationGate("vehicle-002")
    event = _pending_event(gate)
    client = FakeClient()

    assert run(deliver(gate, event, client, TOPIC)) is True
    assert client.calls[0][2:] == (1, False)
    assert gate.next_event(Observation(3.0, True, T1)) is None


def test_pinned_sdk_exposes_paho_publisher():
    mqtt = pytest.importorskip("velocitas_sdk.native.mqtt")
    sdk_client = mqtt.MqttClient("localhost", 1883)
    publisher = pub_client_of(sdk_client)
    assert callable(publisher.publish)
