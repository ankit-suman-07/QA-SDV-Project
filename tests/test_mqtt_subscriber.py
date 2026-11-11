"""Subscriber lifecycle tests with a client fake and real persistence boundary."""
import importlib
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_mqtt_ingress import FakeWriter, fixture
from ditto.mqtt_ingress import Ingress


class SubscriberTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/mqtt_subscriber.py').exists(),
                        'production B1 subscriber is missing')
        self.m = importlib.import_module('ditto.mqtt_subscriber')
        self.writer = FakeWriter()
        self.client = Mock()
        self.client.subscribe.return_value = (0, 1)
        self.client.ack.return_value = 0
        self.subscriber = self.m.Subscriber(Ingress(self.writer), self.m.MqttConfig(),
                                            client=self.client)
        self.addCleanup(self.subscriber.stop)

    def message(self, event=None, mid=1, **kwargs):
        event = event or fixture()
        message = SimpleNamespace(topic='sdv/' + event['vehicleId'] + '/health',
                                  payload=json.dumps(event).encode(), qos=1, mid=mid, retain=False)
        for key, value in kwargs.items():
            setattr(message, key, value)
        return message

    def connect(self):
        self.subscriber.on_connect(self.client, None, {}, 0, None)

    def test_reconnect_resubscribes_only_after_success(self):
        self.subscriber.on_connect(self.client, None, {}, 5, None)
        self.client.subscribe.assert_not_called()
        self.connect()
        self.connect()
        self.assertEqual(2, self.client.subscribe.call_count)
        self.client.subscribe.assert_called_with('sdv/+/health', qos=1)

    def test_late_connect_callback_after_stop_cannot_resubscribe(self):
        self.subscriber.stop()
        self.connect()
        self.client.subscribe.assert_not_called()

    def test_acknowledges_only_after_persistence_and_rejects_duplicates(self):
        self.connect()
        self.subscriber.on_message(self.client, None, self.message())
        self.subscriber.wait_idle()
        self.assertEqual(1, len(self.writer.writes))
        self.client.ack.assert_called_once_with(1, 1)
        self.subscriber.on_message(self.client, None, self.message(mid=2))
        self.subscriber.wait_idle()
        self.assertEqual(1, len(self.writer.writes))
        self.assertEqual(2, self.client.ack.call_count)

    def test_bad_messages_are_acknowledged_without_writer_calls(self):
        self.connect()
        for mid, payload in enumerate([b'{', b'{"vehicleId":"unknown"}'], 1):
            self.subscriber.on_message(self.client, None, self.message(mid=mid, payload=payload))
        self.subscriber.wait_idle()
        self.assertEqual([], self.writer.writes)
        self.assertEqual(2, self.client.ack.call_count)

    def test_failed_vehicle_retries_without_ack_while_other_vehicle_continues(self):
        entered = threading.Event()
        release = threading.Event()
        original = self.writer.persist
        def persist(vehicle, properties):
            if vehicle == 'vehicle-002':
                entered.set()
                release.wait(2)
                if not release.is_set():
                    raise OSError('blocked test writer')
            original(vehicle, properties)
        self.writer.persist = persist
        self.addCleanup(release.set)
        self.connect()
        self.subscriber.on_message(self.client, None, self.message())
        self.assertTrue(entered.wait(1))
        self.client.ack.assert_not_called()
        done = threading.Event()
        def ack(mid, qos):
            if mid == 2:
                done.set()
            return 0
        self.client.ack.side_effect = ack
        self.subscriber.on_message(self.client, None, self.message(fixture('vehicle-001-healthy'), mid=2))
        self.assertTrue(done.wait(1))
        self.assertEqual('vehicle-001', self.writer.writes[0][0])
        release.set()
        self.subscriber.wait_idle()
        self.assertEqual(2, len(self.writer.writes))

    def test_writer_failure_is_retried_without_committing(self):
        self.connect()
        failed = threading.Event()
        original = self.writer.persist
        def persist(vehicle, properties):
            if not failed.is_set():
                failed.set()
                raise OSError('transient')
            original(vehicle, properties)
        self.writer.persist = persist
        self.subscriber.on_message(self.client, None, self.message())
        self.subscriber.wait_idle()
        self.assertTrue(failed.is_set())
        self.assertEqual(1, len(self.writer.writes))
        self.client.ack.assert_called_once_with(1, 1)

    def test_retained_or_wrong_qos_input_is_rejected(self):
        self.connect()
        self.subscriber.on_message(self.client, None, self.message(retain=True))
        self.subscriber.on_message(self.client, None, self.message(qos=0))
        self.subscriber.wait_idle()
        self.assertEqual([], self.writer.writes)

    def test_subscription_failure_disconnects(self):
        self.client.subscribe.return_value = (4, None)
        self.connect()
        self.client.disconnect.assert_called_once()

    def test_suback_denial_or_qos_downgrade_stops_delivery(self):
        self.subscriber.on_subscribe(self.client, None, 1, [0], None)
        self.client.disconnect.assert_called_once()
        self.subscriber.on_message(self.client, None, self.message())
        self.assertEqual([], self.writer.writes)

    def test_queue_overflow_stops_without_acknowledging_dropped_work(self):
        self.subscriber.stop()
        config = self.m.MqttConfig(queue_size=1)
        self.subscriber = self.m.Subscriber(Ingress(self.writer), config, client=self.client)
        self.addCleanup(self.subscriber.stop)
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def blocked(vehicle, properties):
            entered.set()
            release.wait(2)
        self.writer.persist = blocked
        self.connect()
        self.subscriber.on_message(self.client, None, self.message())
        self.assertTrue(entered.wait(1))
        self.subscriber.on_message(self.client, None, self.message(mid=2))
        self.subscriber.on_message(self.client, None, self.message(mid=3))
        self.client.ack.assert_not_called()
        self.assertEqual('QUEUE_FULL', self.subscriber._fatal)
        release.set()
        self.subscriber.stop()
        self.client.ack.assert_not_called()

    def test_auth_and_tls_configuration(self):
        config = self.m.MqttConfig(username='user', password='secret', tls_ca='ca.pem')
        client = Mock()
        subscriber = self.m.Subscriber(Ingress(self.writer), config, client=client)
        self.addCleanup(subscriber.stop)
        client.username_pw_set.assert_called_once_with('user', 'secret')
        client.tls_set.assert_called_once_with(ca_certs='ca.pem')

    @unittest.skipUnless(importlib.util.find_spec('paho'), 'optional paho-mqtt not installed')
    def test_real_paho_client_and_version2_suback_reason_codes(self):
        from paho.mqtt.reasoncodes import ReasonCode
        from paho.mqtt.packettypes import PacketTypes
        client = self.m.create_client(self.m.MqttConfig(client_id='b1-test'))
        subscriber = self.m.Subscriber(Ingress(self.writer), client=client)
        self.addCleanup(subscriber.stop)
        self.assertEqual(subscriber.on_message, client.on_message)
        subscriber.on_subscribe(client, None, 1,
                                [ReasonCode(PacketTypes.SUBACK, 'Granted QoS 1')], None)
        self.assertIsNone(subscriber._fatal)
        subscriber.on_subscribe(client, None, 1,
                                [ReasonCode(PacketTypes.SUBACK, 'Not authorized')], None)
        self.assertEqual('SUBSCRIBE_QOS_REJECTED', subscriber._fatal)

    def test_old_connection_work_cannot_ack_reused_message_id(self):
        entered, release = threading.Event(), threading.Event()
        original = self.writer.persist
        def persist(vehicle, properties):
            entered.set()
            release.wait(2)
            original(vehicle, properties)
        self.writer.persist = persist
        self.addCleanup(release.set)
        self.connect()
        self.subscriber.on_message(self.client, None, self.message())
        self.assertTrue(entered.wait(1))
        self.subscriber.on_disconnect(self.client, None, {}, 1, None)
        self.connect()
        release.set()
        self.subscriber.wait_idle()
        self.client.ack.assert_not_called()
        self.subscriber.on_message(self.client, None, self.message())
        self.subscriber.wait_idle()
        self.client.ack.assert_called_once_with(1, 1)

    def test_environment_configuration_and_invalid_values(self):
        config = self.m.MqttConfig.from_env({'SDV_MQTT_HOST': 'broker', 'SDV_MQTT_PORT': '8883',
            'SDV_MQTT_CLIENT_ID': 'ingress-1', 'SDV_MQTT_USERNAME': 'user',
            'SDV_MQTT_PASSWORD': 'secret', 'SDV_MQTT_TLS_CA': 'ca.pem'})
        self.assertEqual(('broker', 8883, 'ingress-1'), (config.host, config.port, config.client_id))
        self.assertNotIn('secret', repr(config))
        for values in [{'SDV_MQTT_PORT': '0'}, {'SDV_MQTT_PORT': 'bad'},
                       {'SDV_MQTT_CLIENT_ID': ''}, {'SDV_MQTT_HOST': ''},
                       {'SDV_MQTT_QUEUE_SIZE': '0'}, {'SDV_MQTT_RETRY_SECONDS': 'nan'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.m.MqttConfig.from_env(values)

    def test_run_configures_persistent_client_and_reconnect_backoff(self):
        self.subscriber.run()
        self.client.manual_ack_set.assert_called_once_with(True)
        self.client.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=30)
        self.client.connect_async.assert_called_once_with('localhost', 1883, 60)
        self.client.loop_forever.assert_called_once_with(retry_first_connection=True)


if __name__ == '__main__':
    unittest.main()
