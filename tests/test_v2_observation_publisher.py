import json
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.v1_dev.contract import ContractError, parse_timestamp
from scripts.v2_dev.observation_mapping import DISTANCE, SPEED, VALIDITY, prepare_observation
from scripts.v2_dev.observation_publisher import DeliveryError, Kuksa, Mqtt, Publisher, broker_for

FIXTURES = Path(__file__).parent / "fixtures/v2/observations"


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((FIXTURES / "session-manifest.json").read_text())
        self.event = json.loads((FIXTURES / "vehicle-001.json").read_text())
        self.now = parse_timestamp(self.event["sourceTimestamp"])
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.kuksa = Mock()
        self.mqtt = Mock()
        self.publisher = self.open_publisher()

    def open_publisher(self, vehicle="vehicle-001", db=None):
        return Publisher(db or self.db, vehicle, self.manifest, self.kuksa, self.mqtt,
                         clock=lambda: self.now, pause=lambda _: None)

    def test_unconfirmed_kuksa_blocks_mqtt_and_keeps_pending_on_restart(self):
        wire = json.dumps(self.event)
        self.kuksa.write.side_effect = DeliveryError("partial or uncertain")
        with self.assertRaises(DeliveryError):
            self.publisher.accept(wire)
        self.mqtt.publish.assert_not_called()
        self.assertEqual(self.publisher.state(), (None, wire, 0))
        self.assertEqual(self.kuksa.write.call_count, 3)

        self.kuksa.write.side_effect = None
        self.open_publisher().resume()
        self.assertEqual(self.kuksa.write.call_count, 4)
        self.mqtt.publish.assert_called_once_with("sdv/vehicle-001/v2/observations", wire)
        self.assertEqual(self.publisher.state(), (wire, None, 0))

    def test_mqtt_uncertainty_retries_unchanged_wire_without_rewriting_kuksa(self):
        wire = json.dumps(self.event, indent=None)
        topic = "sdv/vehicle-001/v2/observations"

        def lose_ack(*_):
            self.kuksa.write.assert_called_once()
            self.assertEqual(self.publisher.state(), (None, wire, 1))
            raise DeliveryError("PUBACK lost")

        self.mqtt.publish.side_effect = lose_ack
        with self.assertRaises(DeliveryError):
            self.publisher.accept(wire)
        next_event = dict(self.event, eventId="next", sequence=1, frame=101,
                          simulationSeconds=100.1, sourceTimestamp="2026-01-01T00:00:00.100Z")
        with self.assertRaises(DeliveryError):
            self.publisher.accept(json.dumps(next_event))

        self.mqtt.publish.side_effect = None
        reopened = self.open_publisher()
        self.assertEqual(reopened.accept(json.dumps(self.event, separators=(",", ":"))), "published")
        self.kuksa.write.assert_called_once()
        self.assertEqual(self.mqtt.publish.call_count, 4)
        self.assertTrue(all(call.args == (topic, wire) for call in self.mqtt.publish.call_args_list))
        self.assertEqual(reopened.accept(wire), "duplicate")
        self.assertEqual(reopened.accept(json.dumps(next_event)), "published")
        with self.assertRaisesRegex(ContractError, "EVENT_ID_CONFLICT"):
            newer = dict(next_event, eventId=self.event["eventId"], sequence=2, frame=102,
                         simulationSeconds=100.2, sourceTimestamp="2026-01-01T00:00:00.200Z")
            reopened.accept(json.dumps(newer))

    def test_vehicle_isolation_and_distinct_brokers(self):
        self.assertEqual(len({broker_for(self.manifest, f"vehicle-00{i}") for i in range(1, 4)}), 3)
        with self.assertRaisesRegex(ValueError, "another vehicle"):
            self.open_publisher("vehicle-002")
        with self.assertRaisesRegex(ContractError, "TARGET_MISMATCH"):
            self.publisher.accept((FIXTURES / "vehicle-002.json").read_text())
        self.kuksa.write.assert_not_called()
        self.mqtt.publish.assert_not_called()

    def test_speed_is_optional_and_valid_during_dropout(self):
        def map_values(event):
            return prepare_observation(json.dumps(event), vehicle_id="vehicle-001",
                                       manifest=self.manifest, now=self.now)[1]

        self.assertNotIn(SPEED, map_values(self.event))
        self.event = json.loads((FIXTURES / "vehicle-001-motion.json").read_text())
        motion = self.event["velocityMetersPerSecond"]
        self.assertEqual(map_values(self.event)[SPEED], 18.0)
        self.event["lidar"] = {"distanceMeters": None, "sensorAvailable": False}
        self.assertEqual(map_values(self.event), {VALIDITY: False, SPEED: 18.0})
        for bad in (False, "3", float("inf"), 1e100, 10**400):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                map_values(dict(self.event, velocityMetersPerSecond=dict(motion, x=bad)))


class ClientTest(unittest.TestCase):
    def test_mqtt_reconnect_cleanup_and_same_qos(self):
        def client(published):
            fake = Mock()
            fake.connect.side_effect = lambda *args, **kwargs: fake.on_connect(fake, None, None, 0, None) or 0
            fake.publish.return_value = SimpleNamespace(rc=0, mid=1)

            def loop(**_):
                if published:
                    fake.on_publish(fake, None, 1, SimpleNamespace(is_failure=False), None)
                    return 0
                return 1  # First connection drops before PUBACK.

            fake.loop.side_effect = loop
            return fake

        first, rejected, second = client(False), client(True), client(True)

        def reject(**_):
            rejected.on_publish(rejected, None, 1, SimpleNamespace(is_failure=True), None)
            return 0

        rejected.loop.side_effect = reject
        mqtt = Mqtt(Mock(side_effect=[first, rejected, second]), "localhost", 1883)
        for _ in range(2):
            with self.assertRaises(DeliveryError):
                mqtt.publish("topic", "original wire")
        mqtt.publish("topic", "original wire")
        mqtt.close()
        for connection in (first, rejected, second):
            connection.publish.assert_called_once_with("topic", "original wire", qos=1, retain=False)
            connection.disconnect.assert_called_once()

    def test_pinned_kuksa_val1_checks_per_path_result_and_reconnects(self):
        from kuksa_client.grpc import DataType, VSSClient, val_v1

        client = VSSClient("localhost", 55555, ensure_startup_connection=False)
        stub = Mock()

        def connect():
            client.connected = True
            client.client_stub_v1 = stub

        client.connect = Mock(side_effect=connect)
        client.get_metadata = Mock(return_value={
            VALIDITY: SimpleNamespace(data_type=DataType.BOOLEAN),
            DISTANCE: SimpleNamespace(data_type=DataType.FLOAT, unit="m"),
        })
        client.get_value_types = Mock(return_value={VALIDITY: DataType.BOOLEAN, DISTANCE: DataType.FLOAT})
        partial = val_v1.SetResponse()
        error = partial.errors.add(path=DISTANCE)
        error.error.code = 403
        stub.Set.side_effect = [partial, val_v1.SetResponse()]
        adapter = Kuksa(client)
        self.addCleanup(adapter.close)
        timestamp = parse_timestamp("2026-01-01T00:00:00.123Z")
        values = {VALIDITY: True, DISTANCE: 3.0}
        with self.assertRaises(DeliveryError):
            adapter.write(values, timestamp)
        self.assertFalse(client.connected)
        adapter.write(values, timestamp)
        self.assertEqual(client.connect.call_count, 2)
        request = stub.Set.call_args.args[0]
        self.assertEqual(stub.Set.call_args.kwargs["timeout"], 2.0)
        self.assertEqual({entry.entry.path for entry in request.updates}, set(values))
        for entry in request.updates:
            self.assertEqual(entry.entry.value.timestamp.ToDatetime(tzinfo=timestamp.tzinfo), timestamp)
        client.get_metadata.return_value[DISTANCE].unit = "cm"
        with self.assertRaises(DeliveryError):
            adapter.write(values, timestamp)
        self.assertEqual(stub.Set.call_count, 2)
