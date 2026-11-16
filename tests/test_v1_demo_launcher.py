"""Focused orchestration safety controls; real integration is recorded separately."""
import importlib.util
from pathlib import Path
import unittest
import json
import threading
from unittest.mock import patch
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location('demo', Path(__file__).parents[1]/'scripts/v1_demo.py')

class DemoControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.m)

    def test_fault_match_uses_contract_string_faults_and_exact_identity(self):
        root=Path(__file__).parents[1]
        events=[];things={};views={}
        for name in ('vehicle-001-healthy.json','vehicle-002-fault.json'):
            e=json.loads((root/'tests/fixtures/v1'/name).read_text());vehicle=e['vehicleId']
            props=dict(e);props['lastEventId']=props.pop('eventId')
            things[vehicle]={'thingId':'sdv:'+vehicle,'attributes':{'vehicleId':vehicle},'features':{'v1':{'properties':props}}}
            views[vehicle]={'thingId':'sdv:'+vehicle,'vehicleId':vehicle,'lastEventId':e['eventId'],'sourceTimestamp':e['sourceTimestamp'],'healthStatus':e['health'],'activeFaults':e['faults'],'lidar':e['lidar'],'availability':'AVAILABLE'}
            events.append({'event':e})
        demo=self.m.Demo.__new__(self.m.Demo);demo.isolation_failed=False
        demo.lock=threading.Lock();demo.events=events;demo.append=Mock()
        summary={'vehicles':list(views.values())}
        demo.snapshot=Mock(return_value={'things':things,'views':views,'fleetApi':summary,'fleetThing':summary})
        with patch.object(self.m,'observed_status',return_value='PUBLISHING'):
            self.assertTrue(demo.match('CRITICAL'))
            things['vehicle-002']['features']['v1']['properties']['lastEventId']='unmatched'
            self.assertFalse(demo.match('CRITICAL'))

    def test_unverified_kanto_cleanup_never_restores_docker(self):
        demo=self.m.Demo.__new__(self.m.Demo)
        demo.active=False;demo.observer=None;demo.created=True;demo.keep=False
        demo.changed_docker=True;demo.name='pilot';demo.cli=['kanto']
        demo.c={'dockerApp002':'expected'};demo.processes=[];demo.log_threads=[]
        demo.isolation_failed=False;demo.save=Mock();demo.append=Mock()
        demo.command=Mock(side_effect=RuntimeError('stop unverified'))
        self.assertFalse(demo.cleanup())
        demo.command.assert_called_once_with(['kanto','stop','--name','pilot'])

    def test_duplicate_guard_runs_before_lifecycle_mutation(self):
        demo=self.m.Demo.__new__(self.m.Demo)
        demo.thing=Mock(return_value={'features':{'v1':{'properties':{}}}})
        demo.guard=Mock(side_effect=RuntimeError('duplicate publisher'))
        demo.command=Mock()
        with self.assertRaisesRegex(RuntimeError,'publisher'):demo.lifecycle()
        demo.command.assert_not_called()

    def test_provider_identity_is_not_an_application_publisher(self):
        self.assertFalse(self.m.is_publisher('provider-002','vehicle-002'))
        self.assertTrue(self.m.is_publisher('app-002','vehicle-002'))
        self.assertTrue(self.m.is_publisher(None,'vehicle-002'))

    def test_duplicate_docker_publishers_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'publisher'):
            self.m.publisher_guard(['expected', 'unrelated'], False, 'expected')

    def test_docker_and_kanto_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'publisher'):
            self.m.publisher_guard(['expected'], True, 'expected')

    def test_other_docker_publisher_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'publisher'):
            self.m.publisher_guard(['unrelated'], False, 'expected')

    def test_exclusive_docker_or_kanto_allowed(self):
        self.m.publisher_guard(['expected'], False, 'expected')
        self.m.publisher_guard([], True, 'expected')

    def test_failed_readiness_has_deadline_and_keeps_last_failure(self):
        ticks=iter([0,0,1,2])
        check=Mock(side_effect=OSError('dependency unavailable'))
        with self.assertRaisesRegex(RuntimeError, 'readiness'):
            self.m.bounded_wait(check, 1, clock=lambda:next(ticks), pause=lambda _:None)
        self.assertGreater(check.call_count, 0)

    def test_freshness_requires_all_three_boundaries_and_new_identity(self):
        event={'eventId':'new','sourceTimestamp':'2026-11-15T12:00:04Z'}
        self.assertTrue(self.m.post_restart(event,'old','2026-11-15T12:00:01Z','2026-11-15T12:00:02Z','2026-11-15T12:00:03Z'))
        self.assertFalse(self.m.post_restart(event,'new','2026-11-15T12:00:01Z','2026-11-15T12:00:02Z','2026-11-15T12:00:03Z'))
        self.assertFalse(self.m.post_restart(event,'old','2026-11-15T12:00:01Z','2026-11-15T12:00:05Z','2026-11-15T12:00:03Z'))

    def test_source_stale_even_when_container_running(self):
        self.assertEqual(self.m.observed_status(True, '2026-11-15T12:00:00Z', now=self.m.timestamp('2026-11-15T12:00:10Z')), 'STALE')
        self.assertEqual(self.m.observed_status(True), 'RUNNING')
        self.assertEqual(self.m.observed_status(False), 'FAILED')

if __name__=='__main__':unittest.main()
