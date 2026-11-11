"""Read-only fixture checks, independent of PR #30 and live services."""
import copy
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

FIXTURES = Path(__file__).parent / 'fixtures/v1'
NOW = datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc)


def twin(vehicle='vehicle-002', name=None):
    if name:
        props = json.loads((FIXTURES / (name + '.json')).read_text())
        props['lastEventId'] = props.pop('eventId')
        return {'thingId': 'sdv:' + vehicle, 'attributes': {'vehicleId': vehicle},
                'features': {'v1': {'properties': props}}}
    return json.loads((FIXTURES / ('ditto-' + vehicle + '.json')).read_text())


class ConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/twin_consistency.py').exists(),
                        'B3 consistency checks are missing')
        self.m = importlib.import_module('ditto.twin_consistency')

    def test_valid_snapshot_and_availability_boundaries(self):
        for second, expected in [(5, 'AVAILABLE'), (6, 'STALE'), (30, 'STALE'), (31, 'UNAVAILABLE')]:
            now = datetime.fromtimestamp(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() + second, timezone.utc)
            result = self.m.inspect_v1_twin('vehicle-001', twin('vehicle-001'), now=now)
            self.assertEqual(expected, result['availability'])

    def test_direct_nonfinite_extensions_are_rejected(self):
        for value in [float('nan'), float('inf'), float('-inf')]:
            thing = twin()
            thing['features']['v1']['properties']['extension'] = value
            with self.subTest(value=value):
                with self.assertRaises(self.m.ConsistencyError) as caught:
                    self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
                self.assertEqual('NON_FINITE_VALUE', caught.exception.code)

    def test_nested_dictionary_and_array_nonfinite_extensions_are_rejected(self):
        for value in [float('nan'), float('inf'), float('-inf')]:
            for extension in [{'nested': {'number': value}}, [0, value],
                              {'nested': [True, None, {'numbers': [1, value]}]}]:
                thing = twin()
                thing['features']['v1']['properties']['extension'] = extension
                with self.subTest(extension=extension):
                    with self.assertRaises(self.m.ConsistencyError) as caught:
                        self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
                    self.assertEqual('NON_FINITE_VALUE', caught.exception.code)

    def test_valid_finite_extensions_preserve_values_without_wire_budget(self):
        thing = twin()
        extension = {'values': [0, -2, 1.25, 1e300, True, False, None, 'NaN', 'Infinity'],
                     'nested': {'text': '\u00e9' * 80000, 'integer': 10 ** 400}}
        thing['features']['v1']['properties']['extension'] = extension
        result = self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
        self.assertEqual(extension, result['properties']['extension'])
        self.assertEqual('AVAILABLE', result['availability'])
        result['properties']['extension']['values'].append(9)
        self.assertEqual(9, len(thing['features']['v1']['properties']['extension']['values']))

    def test_rejected_nonfinite_snapshot_does_not_initialize_sequence(self):
        sequence = self.m.TwinSequence()
        bad = twin(name='vehicle-002-fault')
        bad['features']['v1']['properties']['extension'] = float('nan')
        with self.assertRaises(self.m.ConsistencyError):
            sequence.observe('vehicle-002', bad, now=NOW)
        # This earlier valid snapshot must still initialize, not be rejected late.
        self.assertEqual('INITIAL', sequence.observe('vehicle-002', twin(name='vehicle-002-healthy'), now=NOW))

    def test_nonfinite_rejection_preserves_previous_sequence_and_later_progress(self):
        sequence = self.m.TwinSequence()
        initial = twin(name='vehicle-002-healthy')
        sequence.observe('vehicle-001', twin('vehicle-001'), now=NOW)
        sequence.observe('vehicle-002', initial, now=NOW)
        for value in [float('nan'), float('inf'), float('-inf')]:
            bad = twin(name='vehicle-002-fault')
            bad['features']['v1']['properties']['extension'] = {'array': [value]}
            with self.subTest(value=value), self.assertRaises(self.m.ConsistencyError):
                sequence.observe('vehicle-002', bad, now=NOW)
            self.assertEqual('DUPLICATE_EVENT', sequence.observe('vehicle-002', initial, now=NOW))
            self.assertEqual('DUPLICATE_EVENT', sequence.observe('vehicle-001', twin('vehicle-001'), now=NOW))
        self.assertEqual('UPDATED', sequence.observe('vehicle-002', twin(name='vehicle-002-fault'), now=NOW))
        self.assertEqual('UPDATED', sequence.observe('vehicle-002', twin(name='vehicle-002-recovered'), now=NOW))

    def test_three_identity_locations_and_nested_shapes(self):
        for path in ['thingId', 'attributes', 'features']:
            thing = twin()
            thing[path] = []
            with self.subTest(path=path), self.assertRaises(self.m.ConsistencyError):
                self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
        thing = twin()
        thing['features']['v1']['properties']['vehicleId'] = 'vehicle-001'
        with self.assertRaises(self.m.ConsistencyError):
            self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)

    def test_required_fields_types_time_and_classification(self):
        for key, value in [('schemaVersion', '2'), ('lastEventId', ''), ('health', []),
                           ('sourceTimestamp', '2026-01-01T00:00:00'),
                           ('sourceTimestamp', '2026-01-01T00:00:06Z'),
                           ('faults', ['LIDAR_OBSTRUCTION']), ('lidar', None), ('traceId', '')]:
            thing = twin()
            thing['features']['v1']['properties'][key] = value
            with self.subTest(key=key), self.assertRaises(self.m.ConsistencyError):
                self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)

    def test_missing_fields_and_duplicate_faults_fail(self):
        for key in ('vehicleId', 'schemaVersion', 'lastEventId', 'sourceTimestamp', 'health', 'faults', 'lidar'):
            thing = twin()
            del thing['features']['v1']['properties'][key]
            with self.subTest(key=key), self.assertRaises(self.m.ConsistencyError):
                self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
        thing = twin(name='vehicle-002-fault')
        thing['features']['v1']['properties']['faults'] *= 2
        with self.assertRaises(self.m.ConsistencyError):
            self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)

    def test_sequence_duplicate_late_conflicting_and_rejected_state(self):
        sequence = self.m.TwinSequence()
        sequence.observe('vehicle-001', twin('vehicle-001'), now=NOW)
        initial = twin(name='vehicle-002-healthy')
        self.assertEqual('INITIAL', sequence.observe('vehicle-002', initial, now=NOW))
        self.assertEqual('DUPLICATE_EVENT', sequence.observe('vehicle-002', initial, now=NOW))
        fault = twin(name='vehicle-002-fault')
        self.assertEqual('UPDATED', sequence.observe('vehicle-002', fault, now=NOW))
        with self.assertRaises(self.m.ConsistencyError) as caught:
            sequence.observe('vehicle-002', initial, now=NOW)
        self.assertEqual('OUT_OF_ORDER', caught.exception.code)
        changed = copy.deepcopy(fault)
        changed['features']['v1']['properties']['lidar']['distanceMeters'] = 2
        with self.assertRaises(self.m.ConsistencyError) as caught:
            sequence.observe('vehicle-002', changed, now=NOW)
        self.assertEqual('CONFLICTING_EVENT', caught.exception.code)
        self.assertEqual('UPDATED', sequence.observe('vehicle-002', twin(name='vehicle-002-recovered'), now=NOW))
        self.assertEqual('DUPLICATE_EVENT', sequence.observe('vehicle-001', twin('vehicle-001'), now=NOW))

    def test_equal_timestamps_reject_other_ids_and_submicrosecond_times_order(self):
        sequence = self.m.TwinSequence()
        thing = twin()
        props = thing['features']['v1']['properties']
        props['sourceTimestamp'] = '2026-01-01T00:00:00.000000001Z'
        sequence.observe('vehicle-002', thing, now=NOW)
        props['lastEventId'] = 'other'
        with self.assertRaises(self.m.ConsistencyError):
            sequence.observe('vehicle-002', thing, now=NOW)
        props['sourceTimestamp'] = '2026-01-01T00:00:00.000000002Z'
        self.assertEqual('UPDATED', sequence.observe('vehicle-002', thing, now=NOW))

    def test_lidar_sensor_failures_types_and_thresholds(self):
        for distance, sensor, health, faults in [
            (5, True, 'CRITICAL', ['LIDAR_OBSTRUCTION']),
            (10, True, 'WARNING', ['LIDAR_OBSTRUCTION']),
            (10.01, True, 'HEALTHY', []),
            (None, False, 'CRITICAL', ['LIDAR_SENSOR_FAILURE'])]:
            thing = twin()
            props = thing['features']['v1']['properties']
            props.update(lidar={'distanceMeters': distance, 'sensorAvailable': sensor}, health=health, faults=faults)
            self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)
        for distance in [True, -1, float('nan'), float('inf'), '3', None]:
            thing = twin()
            thing['features']['v1']['properties']['lidar']['distanceMeters'] = distance
            with self.subTest(distance=distance), self.assertRaises(self.m.ConsistencyError):
                self.m.inspect_v1_twin('vehicle-002', thing, now=NOW)

    def test_isolation_across_fault_and_recovery_without_mutating_snapshots(self):
        before = {'vehicle-001': twin('vehicle-001'), 'vehicle-002': twin(name='vehicle-002-healthy')}
        original = copy.deepcopy(before)
        for name in ['vehicle-002-fault', 'vehicle-002-recovered']:
            after = copy.deepcopy(before)
            after['vehicle-002'] = twin(name=name)
            self.m.verify_isolation(before, after, now=NOW)
            before = after
        self.assertEqual(original['vehicle-001'], before['vehicle-001'])
        bad = copy.deepcopy(before)
        bad['vehicle-001']['attributes']['unexpected'] = True
        with self.assertRaises(self.m.ConsistencyError):
            self.m.verify_isolation(before, bad, now=NOW)
