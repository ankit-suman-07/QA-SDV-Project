"""Representative actual loopback requests, no teammate services."""
import copy
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from scripts.v2_dev.http_mocks import State,handler
from scripts.v2_dev import contract as c

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=State(provider_vehicle='vehicle-003'); cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler(cls.state))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def call(self,path,body=None,method=None,headers=None):
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                    method=method or ('POST' if body is not None else 'GET'),headers=headers or {})
        try: response=urlopen(req,timeout=2)
        except HTTPError as error: response=error
        with response:
            data=response.read()
            self.assertEqual('true',response.headers['X-SDV-Mock'])
            return response.status,json.loads(data) if data else None,response.headers
    def test_loopback_boundaries(self):
        self.assertEqual(3,self.call('/api/v2/fleet')[1]['healthyVehicles'])
        self.assertEqual(404,self.call('/unexpected')[0])
        self.assertEqual(404,self.call('/api/v2/vehicles/vehicle-999/state')[0])
        self.assertEqual(400,self.call('/_mock/clock',{'now':'bad'})[0])
        self.assertEqual('PROJECT_MOCK_NOT_NATIVE_PROTOCOL',self.call('/mock/v2/diagnostics/vehicle-003/faults')[1]['boundary'])
        path='/api/2/things/sdv:vehicle-003/features/v2/properties'
        _,props,headers=self.call(path); props=copy.deepcopy(props)
        props.update(sequence=1,frame=101,eventId='unused',lastEventId='successor',sourceTimestamp='2026-01-01T00:00:00.100Z')
        props.pop('eventId')
        self.assertEqual(428,self.call(path,props,'PUT')[0])
        self.assertEqual(412,self.call(path,props,'PUT',{'If-Match':'"bad"'})[0])
        self.assertEqual(204,self.call(path,props,'PUT',{'If-Match':headers['ETag']})[0])
        self.assertEqual(412,self.call(path,props,'PUT',{'If-Match':headers['ETag']})[0])
        self.assertEqual(412,self.call(path,props,'PUT',{'If-None-Match':'*'})[0])
        current_etag=self.call(path)[2]['ETag']
        self.assertEqual(409,self.call(path,props,'PUT',{'If-Match':current_etag})[0])
        bad=dict(props,vehicleId='vehicle-001')
        self.assertEqual(400,self.call(path,bad,'PUT',{'If-Match':current_etag})[0])
        self.assertEqual(current_etag,self.call(path)[2]['ETag'])
        missing=copy.deepcopy(self.state.twins['vehicle-001']['features'].pop('v2')['properties'])
        create='/api/2/things/sdv:vehicle-001/features/v2/properties'
        self.assertEqual(201,self.call(create,missing,'PUT',{'If-None-Match':'*'})[0])
        req=dict(vehicleId='vehicle-003',actionId='a',traceId='t',action='INJECT_SCENARIO',scenario='LIDAR_OBSTRUCTION')
        self.assertEqual(404,self.call('/api/v1/scenarios/actions',dict(req,vehicleId='vehicle-001'))[0])
        provider=dict(req,actionId='provider')
        code,result,_=self.call('/api/v1/scenarios/actions',provider)
        self.assertEqual(200,code); self.assertTrue(result['active'])
        self.assertEqual(provider['traceId'],result['traceId'])
        clear=dict(provider,actionId='clear',action='CLEAR_SCENARIO')
        self.assertFalse(self.call('/api/v1/scenarios/actions',clear)[1]['active'])
        self.assertEqual(202,self.call('/api/v2/diagnostics/actions',req)[0])
        self.assertEqual(409,self.call('/api/v2/diagnostics/actions',dict(req,traceId='other'))[0])
        self.assertEqual(409,self.call('/_mock/action-result',dict(req,traceId='wrong',status='EXECUTING'))[0])
        for status in ('EXECUTING','SUCCEEDED'):
            self.assertEqual(status,self.call('/_mock/action-result',dict(req,status=status))[1]['status'])
        self.assertEqual(409,self.call('/_mock/action-result',dict(req,status='FAILED'))[0])
        for mode,expected in [('reject',409),('unavailable',503),('timeout',504)]:
            self.call('/_mock/failure',{'mode':mode})
            self.assertEqual(expected,self.call('/api/v1/scenarios/actions',dict(req,actionId=mode))[0])
        self.call('/_mock/failure',{'mode':'none'})
        self.assertEqual(422,self.call('/api/v1/scenarios/actions',dict(req,actionId='restart',action='RESTART_APP'))[0])
        self.call('/_mock/clock',{'now':'2026-01-01T00:01:00Z'})
        self.assertEqual(3,self.call('/api/v2/fleet')[1]['unavailableVehicles'])
        self.assertTrue(self.call('/api/v2/vehicles/vehicle-003/state')[1]['sourceSilent'])

if __name__=='__main__': unittest.main()
