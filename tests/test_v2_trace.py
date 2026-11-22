import copy
import json
import unittest
from pathlib import Path

from scripts.v2_acceptance.verify_trace import BOUNDARIES, MissingCapture, verify
from scripts.v2_dev.contract import VEHICLES
from scripts.v2_dev.observation_mapping import prepare_observation
from scripts.v1_dev.contract import parse_timestamp

ROOT = Path(__file__).parent / "fixtures/v2"


def fixture(path):
    return json.loads((ROOT / path).read_bytes())


class TraceTest(unittest.TestCase):
    def setUp(self):
        self.manifest = fixture("observations/session-manifest.json")
        self.rows = []
        for vehicle in VEHICLES:
            source = fixture(f"observations/{vehicle}.json")
            health = fixture(f"health-events/{vehicle}.json")
            twin = fixture(f"twins/{vehicle}.json")["features"]["v2"]["properties"]
            twin["thingId"] = f"sdv:{vehicle}"
            api = dict(twin, healthStatus=twin["health"], activeFaults=twin["faults"], availability="AVAILABLE")
            _, signals = prepare_observation(json.dumps(source), vehicle_id=vehicle, manifest=self.manifest,
                                             now=parse_timestamp(source["sourceTimestamp"]))
            kuksa = dict(source, signals=signals, allWritesConfirmed=True,
                         brokerTimestamp="2026-01-01T00:00:00.123Z")
            for boundary, payload in zip(BOUNDARIES, (source, kuksa, source, health, twin, api, dict(api))):
                capture = {"boundary": boundary, "payload": payload}
                if boundary in {"companion", "health"}:
                    suffix = "observations" if boundary == "companion" else "health"
                    capture["topic"] = f"sdv/{vehicle}/v2/{suffix}"
                self.rows.append(capture)

    def test_three_joins_independently_of_capture_order_or_broker_clock(self):
        result = verify(self.manifest, reversed(self.rows), VEHICLES, synthetic=True)
        self.assertEqual(set(result), set(VEHICLES))
        self.assertEqual(result["vehicle-003"], ["vehicle-003-s1-0"])

    def test_missing_boundary_is_blocked_for_its_vehicle_only(self):
        rows = self.rows[:-1]
        one_actor = copy.deepcopy(self.manifest)
        for mapping in one_actor["vehicles"][1:]:
            mapping.update(actorId=None, sensorId=None)
        self.assertEqual(set(verify(one_actor, rows, ["vehicle-001"], synthetic=True)), {"vehicle-001"})
        with self.assertRaisesRegex(MissingCapture, "vehicle-003"):
            verify(self.manifest, rows, VEHICLES, synthetic=True)

    def test_complete_join_with_bad_context_or_browser_state_fails(self):
        for index, change in ((4, {"sequence": 99}), (6, {"availability": "STALE"})):
            rows = copy.deepcopy(self.rows)
            rows[index]["payload"].update(change)
            with self.assertRaisesRegex(ValueError, "changed observation context|browser does not match"):
                verify(self.manifest, rows, VEHICLES, synthetic=True)

    def test_mqtt_topic_cannot_be_used_for_another_vehicle(self):
        self.rows[2]["topic"] = "sdv/vehicle-002/v2/observations"
        with self.assertRaisesRegex(ValueError, "companion topic mismatch"):
            verify(self.manifest, self.rows, VEHICLES, synthetic=True)

    def test_fixture_cannot_pass_as_carla_or_share_a_target(self):
        with self.assertRaisesRegex(ValueError, "fixture manifest"):
            verify(self.manifest, self.rows, VEHICLES)
        self.manifest["vehicles"][1]["broker"] = self.manifest["vehicles"][0]["broker"]
        with self.assertRaisesRegex(ValueError, "broker endpoints"):
            verify(self.manifest, self.rows, VEHICLES, synthetic=True)
