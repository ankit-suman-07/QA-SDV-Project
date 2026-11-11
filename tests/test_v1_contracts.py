"""Development-contract checks only. Passing does not prove live V1 acceptance."""
import copy
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/v1'


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text())


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'scripts/v1_dev/contract.py').exists(),
                        'V1 executable contract is not implemented')
        self.c = importlib.import_module('scripts.v1_dev.contract')
        self.now = self.c.parse_timestamp('2026-01-01T00:00:04Z')

    def test_all_requested_fixtures_are_valid_json(self):
        expected = ['vehicle-001-healthy', 'vehicle-002-healthy', 'vehicle-002-fault',
                    'vehicle-002-recovered', 'vehicle-002-stale', 'vehicle-unknown',
                    'event-malformed', 'event-out-of-order', 'ditto-vehicle-001',
                    'ditto-vehicle-002', 'fleet-summary', 'scenario-inject-request',
                    'scenario-clear-request']
        for name in expected:
            with self.subTest(name=name):
                self.assertIsInstance(fixture(name), dict)

    def test_valid_events_and_topic_identity(self):
        for name in ['vehicle-001-healthy', 'vehicle-002-healthy', 'vehicle-002-fault',
                     'vehicle-002-recovered', 'vehicle-002-stale']:
            e = fixture(name)
            self.assertEqual(e, self.c.validate_event(self.c.topic(e['vehicleId']), e))
        with self.assertRaisesRegex(self.c.ContractError, 'TOPIC_MISMATCH'):
            self.c.validate_event(self.c.topic('vehicle-001'), fixture('vehicle-002-fault'))

    def test_negative_fixtures_have_expected_failures(self):
        for name, code in [('vehicle-unknown', 'UNKNOWN_VEHICLE'),
                           ('event-malformed', 'MISSING_FIELD')]:
            e = fixture(name)
            with self.subTest(name=name), self.assertRaisesRegex(self.c.ContractError, code):
                self.c.validate_event('sdv/' + e['vehicleId'] + '/health', e)

    def test_required_fields_and_strict_types(self):
        e = fixture('vehicle-002-healthy')
        for key in e:
            bad = copy.deepcopy(e); del bad[key]
            with self.subTest(missing=key), self.assertRaises(self.c.ContractError):
                self.c.validate_event(self.c.topic('vehicle-002'), bad)
        for key, value in [('schemaVersion', '2.0.0'), ('eventId', ''), ('faults', 'fault'),
                           ('health', 'SENSOR_FAILURE'), ('lidar', []), ('vehicleId', 2)]:
            bad = copy.deepcopy(e); bad[key] = value
            with self.subTest(key=key), self.assertRaises(self.c.ContractError):
                self.c.validate_event(self.c.topic('vehicle-002'), bad)
        for value in [True, -1, float('nan'), float('inf'), '35']:
            bad = copy.deepcopy(e); bad['lidar']['distanceMeters'] = value
            with self.subTest(distance=value), self.assertRaises(self.c.ContractError):
                self.c.validate_event(self.c.topic('vehicle-002'), bad)
        for value in [None, 1, 'true']:
            bad = copy.deepcopy(e); bad['lidar']['sensorAvailable'] = value
            with self.subTest(available=value), self.assertRaises(self.c.ContractError):
                self.c.validate_event(self.c.topic('vehicle-002'), bad)

    def test_invalid_timestamps(self):
        for value in [None, '', 42, 'yesterday', '2026-01-01T00:00:00',
                      '2026-01-01', '2026-01-01T01:00:00+01:00']:
            bad = fixture('vehicle-002-healthy'); bad['sourceTimestamp'] = value
            with self.subTest(value=value), self.assertRaises(self.c.ContractError):
                self.c.validate_event(self.c.topic('vehicle-002'), bad)

    def test_ordering_is_per_vehicle_and_duplicates_do_not_advance(self):
        stream = self.c.EventStream()
        healthy = fixture('vehicle-002-healthy'); fault = fixture('vehicle-002-fault')
        stream.accept(self.c.topic('vehicle-002'), healthy)
        stream.accept(self.c.topic('vehicle-002'), fault)
        for name, code in [('vehicle-002-fault', 'DUPLICATE_EVENT'),
                           ('event-out-of-order', 'OUT_OF_ORDER')]:
            with self.assertRaisesRegex(self.c.ContractError, code):
                stream.accept(self.c.topic('vehicle-002'), fixture(name))
        self.assertEqual(fault, stream.latest['vehicle-002'])
        stream.accept(self.c.topic('vehicle-001'), fixture('vehicle-001-healthy'))
        same_time = copy.deepcopy(fault); same_time['eventId'] = 'different-id'
        with self.assertRaisesRegex(self.c.ContractError, 'OUT_OF_ORDER'):
            stream.accept(self.c.topic('vehicle-002'), same_time)

    def test_health_thresholds_match_existing_generator(self):
        for distance, health, faults in [(35, 'HEALTHY', []), (10.01, 'HEALTHY', []),
                 (10, 'WARNING', ['LIDAR_OBSTRUCTION']), (5.01, 'WARNING', ['LIDAR_OBSTRUCTION']),
                 (5, 'CRITICAL', ['LIDAR_OBSTRUCTION']), (0, 'CRITICAL', ['LIDAR_OBSTRUCTION'])]:
            self.assertEqual((health, faults), self.c.classify(distance, True))
        self.assertEqual(('CRITICAL', ['LIDAR_SENSOR_FAILURE']), self.c.classify(None, False))
        bad = fixture('vehicle-002-fault'); bad['health'] = 'HEALTHY'
        with self.assertRaisesRegex(self.c.ContractError, 'HEALTH_FAULT_MISMATCH'):
            self.c.validate_event(self.c.topic('vehicle-002'), bad)
        bad = fixture('vehicle-002-healthy'); bad['faults'] = ['UNKNOWN']
        with self.assertRaises(self.c.ContractError):
            self.c.validate_event(self.c.topic('vehicle-002'), bad)

    def test_freshness_boundaries_missing_failure_and_future(self):
        ts = self.c.parse_timestamp('2026-01-01T00:00:00Z')
        for seconds, result in [(5, 'AVAILABLE'), (5.001, 'STALE'), (30, 'STALE'),
                                (30.001, 'UNAVAILABLE')]:
            self.assertEqual(result, self.c.availability(ts, ts + self.c.timedelta(seconds=seconds)))
        self.assertEqual('UNAVAILABLE', self.c.availability(None, self.now))
        self.assertEqual('UNAVAILABLE', self.c.availability(ts, self.now, reachable=False))
        self.assertEqual('UNAVAILABLE', self.c.availability(self.now + self.c.timedelta(seconds=2), self.now))
        self.assertEqual('AVAILABLE', self.c.availability(ts, ts + self.c.timedelta(seconds=7), stale_after=10))

    def test_ditto_identity_and_no_healthy_fallback(self):
        for v in self.c.VEHICLES:
            twin = fixture('ditto-' + v)
            view = self.c.vehicle_view(v, twin, self.now)
            self.assertEqual(v, view['vehicleId']); self.assertEqual('AVAILABLE', view['availability'])
        twin = fixture('ditto-vehicle-002')
        with self.assertRaisesRegex(self.c.ContractError, 'TWIN_IDENTITY'):
            self.c.vehicle_view('vehicle-001', twin, self.now)
        for reachable in [True, False]:
            view = self.c.vehicle_view('vehicle-002', None, self.now, reachable=reachable)
            self.assertEqual('UNAVAILABLE', view['availability']); self.assertIsNone(view['healthStatus'])

    def test_fleet_counts_exclude_stale_health(self):
        views = [self.c.vehicle_view(v, fixture('ditto-' + v), self.now) for v in self.c.VEHICLES]
        self.assertEqual(fixture('fleet-summary'), self.c.fleet_summary(views, self.now))
        views[1]['availability'] = 'STALE'; views[1]['healthStatus'] = 'CRITICAL'
        result = self.c.fleet_summary(views, self.now)
        self.assertEqual(1, result['healthyVehicles']); self.assertEqual(0, result['criticalVehicles'])
        self.assertEqual(1, result['staleVehicles'])
        views[1]['availability'] = 'UNAVAILABLE'
        self.assertEqual(1, self.c.fleet_summary(views, self.now)['unavailableVehicles'])
        for health, field in [('WARNING', 'warningVehicles'), ('CRITICAL', 'criticalVehicles')]:
            views[1]['availability'] = 'AVAILABLE'; views[1]['healthStatus'] = health
            self.assertEqual(1, self.c.fleet_summary(views, self.now)[field])

    def test_rebase_preserves_staleness_and_order(self):
        anchor = self.c.parse_timestamp('2031-03-04T05:00:00Z')
        e = self.c.rebase_event(fixture('vehicle-002-stale'), anchor)
        self.assertEqual('STALE', self.c.availability(self.c.parse_timestamp(e['sourceTimestamp']),
                                                    anchor + self.c.timedelta(seconds=4)))

    def test_capture_requires_real_fault_then_recovery_and_vehicle_one_isolation(self):
        capture = self.c.Capture()
        for name in ['vehicle-001-healthy', 'vehicle-002-healthy', 'vehicle-002-fault']:
            e = fixture(name); capture.accept(self.c.topic(e['vehicleId']), e)
        self.assertFalse(capture.cycle_complete())
        e = fixture('vehicle-002-recovered'); capture.accept(self.c.topic(e['vehicleId']), e)
        self.assertTrue(capture.cycle_complete())
        bad = fixture('vehicle-002-fault'); bad['vehicleId'] = 'vehicle-001'
        with self.assertRaisesRegex(self.c.ContractError, 'ISOLATION_FAILURE'):
            capture.accept(self.c.topic('vehicle-001'), bad)

class WireDecodingTests(unittest.TestCase):
    def test_wire_decoder_rejects_duplicate_keys_nonfinite_and_oversize(self):
        from scripts.v1_dev import contract as c
        self.assertTrue(hasattr(c, 'decode_event'), 'strict MQTT wire decoder is missing')
        for wire in ['{"vehicleId":"vehicle-001","vehicleId":"vehicle-002"}',
                     '{"distance":NaN}', 'x' * 65537, 'not-json']:
            with self.subTest(wire=wire[:40]), self.assertRaises(c.ContractError):
                c.decode_event(wire)


if __name__ == '__main__':
    unittest.main()
