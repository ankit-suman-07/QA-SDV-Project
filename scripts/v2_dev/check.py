"""Bounded fixture integrity, offline expectation and local Markdown link checks."""
import json
import re
import unittest
from pathlib import Path
from . import contract as c

ROOT=Path(__file__).resolve().parents[2]

def main():
    paths=sorted((ROOT/'tests/fixtures/v2').rglob('*.json'))
    for path in paths:
        fixture=c.decode_event(path.read_bytes())
        assert fixture['fixtureLabel']=='SYNTHETIC',path
    docs=[ROOT/'docs'/p for p in ('v2-interface-contracts.md','v2-native-diagnostic-feasibility.md','v2-independent-development.md')]
    docs += [ROOT/'tests/fixtures/v2/README.md',ROOT/'evidence/v2/preparation.md']
    for doc in docs:
        text=doc.read_text()
        assert not re.search(r'^#{1,6}[^ #\n]',text,re.M),doc
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in link and not link.startswith('#'):
                assert (doc.parent/link.split('#')[0]).exists(),(doc,link)
    suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_v2_prep')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    print(f'{len(paths)} SYNTHETIC JSON files; local Markdown links checked')
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__': main()
