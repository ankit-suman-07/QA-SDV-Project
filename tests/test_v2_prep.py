"""Development boundaries only; production owners must run these vectors on their code."""
import copy
import json
import unittest
from pathlib import Path
from scripts.v2_dev import contract as c

ROOT = Path(__file__).parent / 'fixtures/v2'

def load(path):
    return json.loads((ROOT / path).read_text())

class FixtureTests(unittest.TestCase):
    def test_independent_vectors(self):
        for case in load('observations/cases.json')['cases']:
            with self.subTest(case=case['id']):
                self.assertEqual(case['expected'], c.evaluate_case(case))

    def test_sequence_expectations(self):
        for path in sorted((ROOT / 'sequences').glob('*.json')):
            with self.subTest(sequence=path.name):
                self.assertEqual([], c.check_sequence(json.loads(path.read_text())))

    def test_silence_resets_recovery_without_new_source(self):
        self.assertTrue(hasattr(c.Sequence, 'silence'), 'source-silence evaluator missing')
        sequence=c.Sequence()
        steps=load('sequences/recovery.json')['steps']
        for step in steps[:2]:
            sequence.accept(step['observation'],c.parse_timestamp(step['now']))
        latest=copy.deepcopy(sequence.latest)
        self.assertEqual(['CRITICAL','IN_PROGRESS',False],sequence.silence(c.EPOCH+c.timedelta(seconds=.6)))
        self.assertEqual(['CRITICAL','NONE',True],sequence.silence(c.EPOCH+c.timedelta(seconds=.601)))
        self.assertEqual(latest,sequence.latest)

    def test_sensor_failure_is_retained_during_recovery(self):
        sequence=c.Sequence()
        failed=copy.deepcopy(load('observations/vehicle-002.json'))
        failed['lidar']={'distanceMeters':None,'sensorAvailable':False}
        sequence.accept(failed,c.EPOCH)
        next_event=load('sequences/recovery.json')['steps'][1]['observation']
        self.assertEqual(['CRITICAL','IN_PROGRESS'],sequence.accept(next_event,c.parse_timestamp(next_event['sourceTimestamp'])))
        self.assertEqual(['LIDAR_SENSOR_FAILURE'],getattr(sequence,'faults',None))

    def test_fleet_denominator(self):
        for case in load('twins/fleet-cases.json')['cases']:
            self.assertEqual(case['expected'], c.counts(case['availability'],case['health']))

    def test_diagnostic_outcomes(self):
        fixture=load('diagnostics/cases.json')
        for case in fixture['cases']:
            with self.subTest(case=case['id']):
                action=c.Action(fixture['request'],c.EPOCH)
                for status in case['statuses'][1:]:
                    action.update(dict(fixture['request'],status=status),c.EPOCH)
                if 'result' in case:
                    with self.assertRaisesRegex(c.ContractError,case['expected']):
                        action.update(case['result'],c.EPOCH)
                else:
                    action.expire(c.EPOCH+c.timedelta(seconds=case.get('advanceSeconds',0)))
                    self.assertEqual(case['expected'],action.status)

    def test_fixture_identity_and_projection(self):
        for path in (ROOT/'health-events').glob('*.json'):
            c.validate_health(json.loads(path.read_text()))
        manifest=load('observations/session-manifest.json')
        self.assertEqual(list(c.VEHICLES),[v['vehicleId'] for v in manifest['vehicles']])
        for vehicle in c.VEHICLES:
            obs=load(f'observations/{vehicle}.json'); c.validate(obs)
            event=load(f'health-events/{vehicle}.json'); c.validate_health(event)
            twin=load(f'twins/{vehicle}.json')
            self.assertEqual('sdv:'+vehicle,twin['thingId'])
            self.assertEqual(event['eventId'],twin['features']['v2']['properties']['lastEventId'])

    def test_rebase_preserves_stale_future_and_simulation(self):
        case=load('observations/cases.json')['cases']
        shifted=c.rebase(case,c.EPOCH+c.timedelta(days=400))
        for original,rebased in zip(case,shifted):
            self.assertEqual(rebased['expected'],c.evaluate_case(rebased))
        obs=load('observations/vehicle-001.json')
        self.assertEqual(obs['simulationSeconds'],c.rebase(obs,c.EPOCH+c.timedelta(days=1))['simulationSeconds'])

if __name__ == '__main__': unittest.main()
