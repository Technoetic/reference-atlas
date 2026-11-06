import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]

class DeliveryTests(unittest.TestCase):
    def test_workflow_actions_are_full_immutable_commits(self):
        text=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf8')
        pins=re.findall(r'uses:\s*([^\s]+)',text)
        self.assertEqual(len(pins),4)
        for pin in pins:self.assertRegex(pin,r'^[A-Za-z0-9_/-]+@[0-9a-f]{40}$')

    def test_registry_counts_have_not_lost_pinned_plugin_coverage(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(catalog['counts']['total'],len(catalog['sources']))
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['paper'],42)
        versions=tuple(catalog['snapshots'][plugin]['version'] for plugin in ('agentic-vault','semantic-crosscheck'))
        expected={('v0.40.1','v0.19.1'):(33,0,102,165),
                  ('v0.41.0','v0.19.1'):(34,1,104,169),
                  ('v0.41.0','v0.20.0'):(34,1,104,173)}[versions]
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['project']+catalog['countsByPlugin']['agentic-vault']['format'],expected[0])
        self.assertEqual(catalog['countsByPlugin']['agentic-vault'].get('article',0),expected[1])
        self.assertEqual((catalog['counts']['total'],catalog['counts']['citations']),expected[2:])
        self.assertEqual(catalog['countsByPlugin']['semantic-crosscheck']['paper'],13)
        sxc=catalog['countsByPlugin']['semantic-crosscheck']
        self.assertEqual((sxc['total'],sxc['citations']), (28,45) if versions[1]=='v0.20.0' else (26,41))
        self.assertEqual(catalog['counts']['shared'],5 if versions[1]=='v0.20.0' else 3)
        self.assertEqual(sum(x['citations'] for x in catalog['countsByPlugin'].values()),catalog['counts']['citations'])

    def test_every_source_has_public_commit_bound_evidence(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        for source in catalog['sources']:
            for use in source['uses']:
                snapshot=catalog['snapshots'][use['plugin']]
                for evidence in use['evidence']:
                    expected=f"https://github.com/Technoetic/{use['plugin']}/blob/{snapshot['commit']}/{evidence['file']}#L{evidence['line']}"
                    self.assertEqual(evidence['url'],expected)
                    self.assertGreater(evidence['line'],0)
                    self.assertLessEqual(len(evidence['excerpt']),220)

    def test_public_data_has_no_local_paths_or_credentials(self):
        text=(ROOT/'data/catalog.json').read_text(encoding='utf8')
        pattern=r'(?i)(?<![A-Za-z])[a-z]:[\\/]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|op_u_[A-Za-z0-9]+|sk-[A-Za-z0-9]{16,}'
        self.assertIsNone(re.search(pattern,text),'A credential or local path was found in public data')

if __name__=='__main__':unittest.main()
