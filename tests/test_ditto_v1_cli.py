"""CLI wiring tests with fake downstream services, not live integration."""
import importlib
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class CliTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'ditto/v1.py').exists(), 'B2 CLI is missing')
        self.m = importlib.import_module('ditto.v1')
        self.writer = Mock()
        self.factory = Mock(return_value=self.writer)

    @patch.dict(os.environ, {'SDV_DITTO_USERNAME': 'u', 'SDV_DITTO_PASSWORD': 'p'}, clear=True)
    def test_run_wires_real_ingress_to_writer_and_subscriber(self):
        subscriber = Mock()
        subscriber_factory = Mock(return_value=subscriber)
        self.assertEqual(0, self.m.main(['run'], writer_factory=self.factory,
                                       subscriber_factory=subscriber_factory))
        ingress, config = subscriber_factory.call_args.args
        self.assertIs(self.writer, ingress.writer)
        self.assertEqual('localhost', config.host)
        subscriber.run.assert_called_once()
        subscriber.stop.assert_called_once()

    @patch.dict(os.environ, {'SDV_DITTO_USERNAME': 'u', 'SDV_DITTO_PASSWORD': 'p'}, clear=True)
    def test_provision_requires_explicit_subject_and_uses_writer(self):
        self.assertEqual(0, self.m.main(['provision', '--subject', 'nginx:u'], writer_factory=self.factory))
        self.writer.provision.assert_called_once_with('nginx:u')

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_fails_without_network(self):
        self.assertEqual(1, self.m.main(['run'], writer_factory=self.factory))
        self.factory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
