"""Transport regression: v1 publisher -> real Mosquitto -> merged ingress.

Runs only with a broker: set V1_MQTT_TEST_HOST (and V1_MQTT_TEST_PORT).
Uses the real ditto.mqtt_subscriber.Subscriber with a recording ingress in
place of the Ditto writer. A QoS 0 negative control must be rejected.
"""

import asyncio
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

pytestmark = pytest.mark.integration

HOST = os.getenv("V1_MQTT_TEST_HOST")
PORT = int(os.getenv("V1_MQTT_TEST_PORT", "1883"))

if not HOST:
    pytest.skip("set V1_MQTT_TEST_HOST to run", allow_module_level=True)

mqtt = pytest.importorskip("paho.mqtt.client")

from ditto.mqtt_subscriber import MqttConfig, Subscriber  # noqa: E402
from v1_event import build_v1_event, new_event_id, serialize, topic  # noqa: E402
from v1_publisher import publish_v1_event  # noqa: E402


class RecordingIngress:
    def __init__(self):
        self.processed = []

    def process(self, mqtt_topic, payload):
        self.processed.append((mqtt_topic, bytes(payload)))


def _wait_for(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def ingress():
    recording = RecordingIngress()
    config = MqttConfig(
        host=HOST,
        port=PORT,
        client_id=f"v1-qos-test-{uuid.uuid4().hex[:8]}",
    )
    subscriber = Subscriber(recording, config)
    deliveries = []
    original = subscriber.client.on_message

    def record(client, userdata, message):
        deliveries.append((message.topic, message.qos, message.retain))
        original(client, userdata, message)

    subscriber.client.on_message = record
    thread = threading.Thread(target=subscriber.run, daemon=True)
    thread.start()
    assert _wait_for(lambda: subscriber._connected), "ingress did not connect"
    time.sleep(0.5)  # subscription acknowledged
    yield recording, deliveries
    subscriber.stop()
    thread.join(timeout=5)


@pytest.fixture
def publisher():
    # Same construction as velocitas-sdk 0.15.7: a default paho client with
    # its network loop running.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(HOST, PORT)
    client.loop_start()
    assert _wait_for(client.is_connected)
    yield client
    client.loop_stop()
    client.disconnect()


def _event(vehicle_id):
    return build_v1_event(
        vehicle_id,
        datetime.now(timezone.utc),
        3.0,
        True,
        new_event_id(vehicle_id),
    )


def test_v1_event_reaches_ingress_at_qos1(ingress, publisher):
    recording, deliveries = ingress
    event = _event("vehicle-002")
    payload = serialize(event)

    assert asyncio.run(publish_v1_event(publisher, topic("vehicle-002"), payload))

    assert _wait_for(lambda: recording.processed)
    assert recording.processed == [(topic("vehicle-002"), payload.encode())]
    assert (topic("vehicle-002"), 1, False) in deliveries


def test_qos0_negative_control_is_rejected(ingress, publisher):
    recording, deliveries = ingress
    payload = serialize(_event("vehicle-001"))

    publisher.publish(topic("vehicle-001"), payload).wait_for_publish(2)

    assert _wait_for(lambda: deliveries)
    assert deliveries == [(topic("vehicle-001"), 0, False)]
    time.sleep(0.5)
    assert recording.processed == []
