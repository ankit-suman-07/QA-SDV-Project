"""Offline V2 QoS 1 regressions at the production subscriber's Paho boundary."""

from copy import deepcopy
import json
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest

from ditto.mqtt_ingress import Ingress
from ditto.mqtt_subscriber import MqttConfig, Subscriber
from ditto.v1_writer import DittoConfig, DittoWriter
from test_v2_ditto_writer import DittoHTTP, TARGET, TOPIC, event_at, properties, write_properties


@pytest.fixture
def transport():
    http = DittoHTTP()
    client = Mock()
    client.subscribe.return_value = (0, 1)
    client.ack.return_value = 0
    acked = Event()
    snapshots = []

    def ack(mid, qos):
        snapshots.append((mid, qos, deepcopy(http.twins)))
        acked.set()
        return 0

    client.ack.side_effect = ack
    writer = DittoWriter(
        DittoConfig("http://ditto.invalid", "fixture", "fixture", attempts=1),
        request=lambda *args, **kwargs: request(*args, **kwargs),
    )
    request = http
    subscriber = Subscriber(Ingress(writer), MqttConfig(retry_seconds=0.001), client=client)
    subscriber.on_connect(client, None, {}, 0, None)
    release = Event()

    def deliver(mid, topic=TOPIC, *, event=None):
        event = event_at(0) if event is None else event
        acked.clear()
        subscriber.on_message(client, None, SimpleNamespace(
            topic=topic, payload=json.dumps(event).encode(), mid=mid, qos=1, retain=False,
        ))

    def replace_request(callback):
        nonlocal request
        request = callback

    try:
        yield http, client, acked, snapshots, release, deliver, replace_request
    finally:
        release.set()
        subscriber.stop()


def test_subscriber_requests_v2_health_at_qos_1_with_manual_ack(transport):
    _, client, *_ = transport
    client.manual_ack_set.assert_called_once_with(True)
    client.subscribe.assert_any_call("sdv/+/v2/health", qos=1)


def test_vehicle_003_ack_follows_persistence_and_exact_retry_skips_write(transport):
    http, client, acked, snapshots, release, deliver, _ = transport
    entered_put = Event()
    before = deepcopy(http.twins)

    def hold_put():
        entered_put.set()
        assert release.wait(5), "test did not release the pending write"

    http.before_put.append(hold_put)
    deliver(31)
    client.ack.assert_not_called()
    assert entered_put.wait(2), "valid V2 delivery did not reach the writer"
    client.ack.assert_not_called()
    assert http.twins == before

    release.set()
    assert acked.wait(2), "successful persistence did not trigger a transport ACK"
    expected = deepcopy(before)
    expected[TARGET]["features"]["v2"] = {"properties": properties(event_at(0))}
    assert snapshots == [(31, 1, expected)]

    deliver(32)
    assert acked.wait(2), "exact retry did not trigger a transport ACK"
    assert snapshots == [(31, 1, expected), (32, 1, expected)]
    assert len(http.put_headers()) == 1
    assert http.twins == expected


@pytest.mark.parametrize("failure", ["http-503", "lost-reply"])
def test_v2_delivery_remains_unacknowledged_until_persistence_is_confirmed(transport, failure):
    http, client, acked, snapshots, release, deliver, replace_request = transport
    retry_read = Event()
    before = deepcopy(http.twins)
    if failure == "http-503":
        http.before_put.append(lambda: 503)
    else:
        http.lose_reply = True

    def hold_retry(method, url, **kwargs):
        if method == "GET" and http.put_headers() and not retry_read.is_set():
            retry_read.set()
            assert release.wait(5), "test did not release the retry read"
        return http(method, url, **kwargs)

    replace_request(hold_retry)
    deliver(41)
    client.ack.assert_not_called()
    assert retry_read.wait(2), "write failure did not trigger a fresh storage read"
    client.ack.assert_not_called()
    expected = deepcopy(before)
    expected[TARGET]["features"]["v2"] = {"properties": properties(event_at(0))}
    assert http.twins == (before if failure == "http-503" else expected)

    release.set()
    assert acked.wait(2), "confirmed write or verified exact retry did not trigger ACK"
    assert snapshots == [(41, 1, expected)]
    assert len(http.put_headers()) == (2 if failure == "http-503" else 1)


def test_v2_topic_mismatch_is_rejected_before_ditto_access(transport, caplog):
    http, client, _, _, _, deliver, _ = transport
    before = deepcopy(http.twins)
    deliver(51, "sdv/vehicle-002/v2/health")
    assert http.calls == []
    assert http.twins == before
    assert "event_rejected code=TOPIC_MISMATCH" in caplog.text
    # Existing subscriber policy disposes of invalid QoS 1 deliveries by ACK.
    client.ack.assert_called_once_with(51, 1)


@pytest.mark.parametrize("old_outcome", ["success", "http-503", "lost-reply"])
def test_reused_mid_cannot_ack_new_delivery_from_old_worker(transport, old_outcome):
    http, client, acked, snapshots, release_old, deliver, replace_request = transport
    old, new = event_at(0), event_at(1)
    old_put, new_put, release_new = Event(), Event(), Event()
    before = deepcopy(http.twins)

    def request(method, url, **kwargs):
        if method != "PUT":
            return http(method, url, **kwargs)
        event_id = write_properties(urlsplit(url).path, kwargs["data"])["lastEventId"]
        if event_id == old["eventId"] and not old_put.is_set():
            old_put.set()
            assert release_old.wait(5)
            if old_outcome == "http-503":
                http.before_put.append(lambda: 503)
            http.lose_reply = old_outcome == "lost-reply"
            try:
                return http(method, url, **kwargs)
            finally:
                http.lose_reply = False
        if event_id == new["eventId"]:
            new_put.set()
            assert release_new.wait(5)
        return http(method, url, **kwargs)

    replace_request(request)
    try:
        deliver(19, event=old)
        assert old_put.wait(2)
        client.ack.assert_not_called()
        client.on_disconnect(client, None, {}, 1, None)
        client.on_connect(client, None, {}, 0, None)
        deliver(19, event=new)
        client.ack.assert_not_called()

        release_old.set()
        # The shared vehicle worker reaches the second PUT only after it has
        # completed the old delivery, including any retry and ACK decision.
        assert new_put.wait(2)
        client.ack.assert_not_called()
        expected = deepcopy(before)
        expected[TARGET]["features"]["v2"] = {"properties": properties(old)}
        assert http.twins == expected
        assert len(http.put_headers()) == (2 if old_outcome == "http-503" else 1)

        release_new.set()
        assert acked.wait(2)
        expected[TARGET]["features"]["v2"]["properties"] = properties(new)
        assert snapshots == [(19, 1, expected)]
        assert http.twins == expected
        assert http.revisions[TARGET] == 2
        client.ack.assert_called_once_with(19, 1)
    finally:
        release_old.set()
        release_new.set()


def test_reused_mid_after_reconnect_is_isolated_across_vehicles(transport):
    http, client, acked, snapshots, release_old, deliver, replace_request = transport
    old_put = Event()
    old = event_at(0)
    other = "vehicle-001"
    new = event_at(1, vehicleId=other, eventId="vehicle-001-reconnected")
    before = deepcopy(http.twins)

    def request(method, url, **kwargs):
        if method == "PUT" and write_properties(urlsplit(url).path, kwargs["data"])["lastEventId"] == old["eventId"]:
            old_put.set()
            assert release_old.wait(5)
        return http(method, url, **kwargs)

    replace_request(request)
    deliver(19, event=old)
    assert old_put.wait(2)
    client.on_disconnect(client, None, {}, 1, None)
    client.on_connect(client, None, {}, 0, None)
    deliver(19, f"sdv/{other}/v2/health", event=new)
    assert acked.wait(2), "vehicle-001 was blocked by vehicle-003's pending write"
    expected = deepcopy(before)
    expected[other]["features"]["v2"]["properties"] = properties(new)
    assert snapshots == [(19, 1, expected)]

    release_old.set()
    client.on_message.__self__.wait_idle()
    expected[TARGET]["features"]["v2"] = {"properties": properties(old)}
    assert http.twins == expected
    assert http.revisions == {"vehicle-001": 1, "vehicle-002": 0, "vehicle-003": 1}
    client.ack.assert_called_once_with(19, 1)


def test_v2_suback_denial_preserves_v1_delivery_and_persistence_gated_ack(caplog):
    from paho.mqtt.packettypes import PacketTypes
    from paho.mqtt.reasoncodes import ReasonCode
    from test_ditto_v1_writer import FakeDitto
    from test_mqtt_ingress import fixture as v1_fixture

    http = FakeDitto()
    client = Mock()
    client.subscribe.side_effect = [(0, 11), (0, 12)]
    entered, release, acked = Event(), Event(), Event()
    vehicle_id = "vehicle-002"
    thing_id = f"sdv:{vehicle_id}"
    persisted_on_ack = []

    def request(method, url, **kwargs):
        if method == "PUT" and url.endswith(f"/things/{thing_id}/features/v1"):
            entered.set()
            assert release.wait(5), "test did not release V1 write"
        return http(method, url, **kwargs)

    def ack(mid, qos):
        if mid == 21:
            persisted_on_ack.append(deepcopy(http.things[thing_id].get("features", {})))
            acked.set()
        return 0

    client.ack.side_effect = ack
    writer = DittoWriter(DittoConfig("http://ditto.invalid", "fixture", "fixture"), request=request)
    writer.provision("nginx:fixture")
    before = deepcopy(http.things)
    http.calls.clear()
    subscriber = Subscriber(Ingress(writer), MqttConfig(), client=client)
    try:
        client.on_connect(client, None, {}, 0, None)
        client.subscribe.assert_any_call("sdv/+/health", qos=1)
        client.subscribe.assert_any_call("sdv/+/v2/health", qos=1)
        client.on_subscribe(client, None, 11, [ReasonCode(PacketTypes.SUBACK, identifier=1)], None)
        # MQTT 3.1.1 SUBACK 0x80 is exposed by Paho v2 callbacks as Unspecified error.
        client.on_subscribe(client, None, 12, [ReasonCode(PacketTypes.SUBACK, identifier=128)], None)
        client.disconnect.assert_not_called()

        client.on_message(client, None, SimpleNamespace(
            topic=TOPIC, payload=json.dumps(event_at(0)).encode(), qos=1, mid=20, retain=False,
        ))
        event = v1_fixture("vehicle-002-healthy")
        client.on_message(client, None, SimpleNamespace(
            topic=f"sdv/{vehicle_id}/health", payload=json.dumps(event).encode(),
            qos=1, mid=21, retain=False,
        ))
        assert entered.wait(2), "V1 delivery stopped after V2 subscription denial"
        assert not acked.is_set()
        assert http.things == before

        release.set()
        assert acked.wait(2), "V1 successful persistence did not trigger an ACK"
        expected = deepcopy(before)
        expected[thing_id]["features"] = {"v1": {"properties": properties(event)}}
        assert http.things == expected
        assert persisted_on_ack == [expected[thing_id]["features"]]
        assert [args for args, _ in client.ack.call_args_list if args[0] == 21] == [(21, 1)]
        assert all(f"/things/{thing_id}" in url for _, url, _ in http.calls)
        assert any("v2" in record.getMessage().lower() and "subscr" in record.getMessage().lower()
                   for record in caplog.records)
    finally:
        release.set()
        subscriber.stop()
