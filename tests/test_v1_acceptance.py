"""Offline harness controls, explicitly not live acceptance."""
import copy
import json
from pathlib import Path
import unittest
from scripts.v1_acceptance.assertions import fleet, preserved

FIXTURES = Path(__file__).parent / 'fixtures/v1'


class AcceptanceControls(unittest.TestCase):
    def summary(self):
        return json.loads((FIXTURES / 'fleet-summary.json').read_text())

    def test_two_vehicle_summary_and_counts(self):
        fleet(self.summary())

    def test_cross_vehicle_corruption_fails(self):
        value = self.summary()
        value['vehicles'][1]['vehicleId'] = 'vehicle-001'
        with self.assertRaises(AssertionError):
            fleet(value)

    def test_stale_must_not_count_healthy(self):
        value = self.summary()
        value['vehicles'][0]['availability'] = 'STALE'
        with self.assertRaises(AssertionError):
            fleet(value)

    def test_source_and_event_preserved(self):
        event = json.loads((FIXTURES / 'vehicle-001-healthy.json').read_text())
        thing = json.loads((FIXTURES / 'ditto-vehicle-001.json').read_text())
        view = copy.deepcopy(self.summary()['vehicles'][0])
        preserved(event, thing, view)
        for key in ('sourceTimestamp', 'lastEventId', 'thingId'):
            broken = copy.deepcopy(view)
            broken[key] = 'corrupted'
            with self.assertRaises(AssertionError, msg=key):
                preserved(event, thing, broken)

    def test_nullable_unavailable_denominator(self):
        value = self.summary()
        value.update(availableVehicles=1, unavailableVehicles=1, healthyVehicles=1)
        value['vehicles'][0].update(availability='UNAVAILABLE', healthStatus=None,
                                    activeFaults=None, lidar=None, sourceTimestamp=None, lastEventId=None)
        fleet(value)
        value['totalVehicles'] = 1
        with self.assertRaises(AssertionError):
            fleet(value)
