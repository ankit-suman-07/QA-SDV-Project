"""Provisioning boundary: no external Ditto required."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'v1_fleet_provision.py'

class FleetProvisioningTest(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.exists(), 'fleet provisioning script must exist')
        spec = importlib.util.spec_from_file_location('fleet_provision', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_provisions_policy_before_thing_with_separate_service_subject(self):
        module = self.module()
        requests = []
        def send(request, timeout):
            requests.append(request)
            self.assertEqual(timeout, 5)
            class Reply:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                status = 201
            return Reply()
        with patch.object(module, 'urlopen', side_effect=send):
            module.provision('http://localhost:8080', 'admin', 'secret', 'nginx:admin', 'nginx:fleet-service')
        self.assertEqual([r.full_url for r in requests], [
            'http://localhost:8080/api/2/policies/sdv:fleet-v1-policy',
            'http://localhost:8080/api/2/things/sdv:fleet-v1'])
        for request in requests:
            self.assertEqual(request.method, 'PUT')
            self.assertEqual(request.get_header('Authorization'), 'Basic YWRtaW46c2VjcmV0')
            self.assertEqual(request.get_header('If-none-match'), '*')
        policy = json.loads(requests[0].data)
        writer = policy['entries']['fleet-writer']
        self.assertEqual(list(writer['subjects']), ['nginx:fleet-service'])
        self.assertEqual(writer['resources'], {'thing:/features/summary/properties': {'grant': ['READ', 'WRITE'], 'revoke': []}})
        thing = json.loads(requests[1].data)
        self.assertEqual(thing['policyId'], 'sdv:fleet-v1-policy')
        self.assertEqual(thing['attributes'], {'kind': 'fleet', 'vehicleIds': ['vehicle-001', 'vehicle-002']})
        self.assertNotIn('properties', thing.get('features', {}).get('summary', {}))

    def test_rejects_missing_credentials_and_unsafe_configuration_without_requests(self):
        module = self.module()
        for values in [('', 'pw', 'nginx:admin', 'nginx:service'),
                       ('admin', '', 'nginx:admin', 'nginx:service'),
                       ('admin', 'pw', 'nginx:same', 'nginx:same')]:
            with self.subTest(values=values), patch.object(module, 'urlopen') as send:
                with self.assertRaises(ValueError):
                    module.provision('http://localhost:8080', *values)
                send.assert_not_called()
        with patch.object(module, 'urlopen') as send:
            with self.assertRaises(ValueError):
                module.provision('http://user:pw@localhost:8080', 'admin', 'pw', 'nginx:admin', 'nginx:service')
            send.assert_not_called()

if __name__ == '__main__': unittest.main()
