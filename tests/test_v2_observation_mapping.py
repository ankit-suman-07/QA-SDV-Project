import json
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.v2_dev.observation_mapping import prepare_observation
from scripts.v1_dev.contract import ContractError, parse_timestamp

FIXTURES = Path(__file__).parent / "fixtures/v2/observations"
DISTANCE = "Vehicle.Automation.Lidar.Front.NearestObstacleDistance"
VALIDITY = "Vehicle.Automation.Lidar.Front.IsHealthy"


class ObservationMappingTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((FIXTURES / "session-manifest.json").read_text())
        self.event = json.loads((FIXTURES / "vehicle-001.json").read_text())
        self.now = parse_timestamp(self.event["sourceTimestamp"])

    def prepare(self, event=None, target="vehicle-001", previous=None, now=None):
        return prepare_observation(
            json.dumps(self.event if event is None else event), vehicle_id=target,
            manifest=self.manifest, now=now or self.now, previous=previous,
        )

    def test_each_vehicle_maps_only_its_lidar_values(self):
        for index in range(1, 4):
            vehicle = f"vehicle-00{index}"
            with self.subTest(vehicle=vehicle):
                event = json.loads((FIXTURES / f"{vehicle}.json").read_text())
                envelope, signals = self.prepare(event, target=vehicle)
                self.assertEqual(envelope, event)
                self.assertIs(signals[VALIDITY], event["lidar"]["sensorAvailable"])
                if signals[VALIDITY]:
                    self.assertEqual(signals, {DISTANCE: event["lidar"]["distanceMeters"], VALIDITY: True})
                    self.assertIs(type(signals[DISTANCE]), float)
                else:
                    self.assertEqual(signals, {VALIDITY: False})
        with self.assertRaisesRegex(ContractError, "TARGET_MISMATCH"):
            self.prepare(target="vehicle-002")

    def test_dropout_writes_only_false_validity(self):
        self.event["lidar"] = {"distanceMeters": None, "sensorAvailable": False}
        envelope, signals = self.prepare()
        self.assertEqual(envelope, self.event)
        self.assertEqual(signals, {VALIDITY: False})

    def test_rejects_malformed_and_incomplete_input(self):
        for wire in ('{"x":1,"x":2}', '{"x":', '{"x":NaN}', '{"x":1e999}'):
            with self.subTest(wire=wire), self.assertRaises(ContractError):
                prepare_observation(wire, vehicle_id="vehicle-001", manifest=self.manifest, now=self.now)
        for key, value in (
            ("sequence", True), ("simulationSeconds", float("inf")),
            ("lidar", {"sensorAvailable": False}), ("processingTimestamp", "invalid"),
            ("actionId", "unpaired"), ("sessionGeneration", 2),
            ("sourceTimestamp", "2026-01-01T00:00:02Z"),
        ):
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.prepare(dict(self.event, **{key: value}))

    def test_replay_preserves_source_time_and_checks_mapping_and_future(self):
        envelope, _ = self.prepare(now=self.now + timedelta(days=1))
        self.assertEqual(envelope, self.event)
        with self.assertRaisesRegex(ContractError, "CLOCK_MAPPING"):
            self.prepare(dict(self.event, simulationSeconds=101))
        with self.assertRaisesRegex(ContractError, "FUTURE_SOURCE"):
            self.prepare(now=self.now - timedelta(seconds=2))

    def test_duplicate_conflict_and_late_input(self):
        self.assertIsNone(self.prepare(previous=self.event))
        with self.assertRaisesRegex(ContractError, "EVENT_ID_CONFLICT"):
            self.prepare(dict(self.event, processingTimestamp=self.event["sourceTimestamp"]), previous=self.event)
        with self.assertRaisesRegex(ContractError, "OUT_OF_ORDER"):
            self.prepare(dict(self.event, eventId="different"), previous=self.event)

    def test_registered_successor_and_retired_session(self):
        fixture = FIXTURES.parent / "sequences/sessions.json"
        steps = json.loads(fixture.read_text())["steps"]
        earlier, unregistered, registered, retired = [step["observation"] for step in steps]
        vehicle = earlier["vehicleId"]
        with self.assertRaisesRegex(ContractError, "UNREGISTERED_SESSION"):
            self.prepare(unregistered, target=vehicle, previous=earlier)
        self.manifest.update(sessionGeneration=2, sessionId="session-2")
        envelope, _ = self.prepare(registered, target=vehicle, previous=earlier)
        self.assertEqual(envelope, registered)
        with self.assertRaisesRegex(ContractError, "UNREGISTERED_SESSION"):
            self.prepare(retired, target=vehicle, previous=envelope)
