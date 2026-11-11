"""Keep the independent-work package navigable and task ownership complete."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class DevelopmentDocumentationTests(unittest.TestCase):
    def test_local_links_resolve(self):
        files = [DOCS / 'SOURCE-OF-TRUTH.md', DOCS / '10-detailed-task-distribution.md',
                 DOCS / 'v1-interface-contracts.md', DOCS / 'v1-independent-development.md',
                 DOCS / 'findings/2026-11-11-v1-preparation-validation.md',
                 ROOT / 'tests/fixtures/v1/README.md']
        for path in files:
            self.assertTrue(path.exists(), str(path))
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if not re.match(r'^[a-z]+://', target):
                    with self.subTest(file=path.name, target=target):
                        self.assertTrue((path.parent / target.split('#')[0]).exists())

    def test_every_v1_task_has_all_independent_execution_fields(self):
        text = (DOCS / '10-detailed-task-distribution.md').read_text()
        cards = dict(re.findall(r'^### ([ABE]\d) — .*?\n(.*?)(?=\n### |\n## |\Z)', text, re.M | re.S))
        expected = {'A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'B3', 'B5', 'E1', 'E2'}
        self.assertEqual(expected, set(cards))
        fields = ['Owner', 'Objective', 'Files/components likely involved', 'Inputs required',
                  'Shared contract references', 'Mock or fixture to use', 'Independent implementation steps',
                  'Independent tests', 'Completion criteria', 'Evidence to capture',
                  'Real integration handoff', 'Acceptance criteria mapping']
        for task, card in cards.items():
            for field in fields:
                with self.subTest(task=task, field=field):
                    self.assertIn('**' + field + ':**', card)

    def test_all_task_ids_deadlines_and_v2_responsibilities_remain(self):
        text = (DOCS / '10-detailed-task-distribution.md').read_text()
        for prefix, count in [('A', 7), ('B', 7), ('E', 5)]:
            for index in range(1, count + 1):
                self.assertIn('| ' + prefix + str(index) + ' · Phase V', text)
        for task in ['A6', 'A7', 'B4', 'B6', 'B7', 'E3', 'E4', 'E5']:
            self.assertIn('| ' + task + ' · Phase V2', text)
        self.assertIn('November 16, 2026', text)
        self.assertIn('December 5, 2026', text)
        for criterion in range(1, 10):
            self.assertIn('V1-' + str(criterion).zfill(2), text)
        self.assertIn('sole fleet aggregation implementation in Spring Boot', text)


if __name__ == '__main__':
    unittest.main()
