import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
# AV paper, project+format, article, catalog sources, catalog citations.
EXPECTED_COVERAGE={
    ('v0.40.1','v0.19.1'):(42,33,0,102,165),
    ('v0.41.0','v0.19.1'):(42,34,1,104,169),
    ('v0.41.0','v0.20.0'):(42,34,1,104,173),
    ('v0.42.0','v0.20.0'):(44,37,1,109,181),
    ('v0.43.0','v0.20.0'):(50,49,5,131,233),
    ('v0.43.0','v0.21.0'):(50,49,5,137,246),
    ('v0.43.0','v0.21.1'):(50,49,5,137,246),
    ('v0.44.0','v0.21.1'):(53,49,5,140,250),
    ('v0.45.0','v0.21.1'):(56,50,5,144,256),
}

class DeliveryTests(unittest.TestCase):
    def test_workflow_actions_are_full_immutable_commits(self):
        text=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf8')
        pins=re.findall(r'uses:\s*([^\s]+)',text)
        self.assertEqual(len(pins),4)
        for pin in pins:self.assertRegex(pin,r'^[A-Za-z0-9_/-]+@[0-9a-f]{40}$')

    def test_registry_counts_have_not_lost_pinned_plugin_coverage(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(catalog['counts']['total'],len(catalog['sources']))
        versions=tuple(catalog['snapshots'][plugin]['version'] for plugin in ('agentic-vault','semantic-crosscheck'))
        expected=EXPECTED_COVERAGE[versions]
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['paper'],expected[0])
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['project']+catalog['countsByPlugin']['agentic-vault']['format'],expected[1])
        self.assertEqual(catalog['countsByPlugin']['agentic-vault'].get('article',0),expected[2])
        self.assertEqual((catalog['counts']['total'],catalog['counts']['citations']),expected[3:])
        sxc=catalog['countsByPlugin']['semantic-crosscheck']
        sxc_coverage={'v0.19.1':(13,26,41,3),'v0.20.0':(13,28,45,5),
                      'v0.21.0':(14,34,58,5),'v0.21.1':(14,34,58,5)}
        self.assertEqual((sxc['paper'],sxc['total'],sxc['citations'],catalog['counts']['shared']),sxc_coverage[versions[1]])
        self.assertEqual(sum(x['citations'] for x in catalog['countsByPlugin'].values()),catalog['counts']['citations'])

    def test_v042_coverage_adds_two_papers_three_projects_and_eight_citations_without_rewriting_history(self):
        self.assertEqual(EXPECTED_COVERAGE[('v0.40.1','v0.19.1')],(42,33,0,102,165))
        self.assertEqual(EXPECTED_COVERAGE[('v0.41.0','v0.19.1')],(42,34,1,104,169))
        prior=EXPECTED_COVERAGE[('v0.41.0','v0.20.0')]
        self.assertEqual(prior,(42,34,1,104,173))
        revised=EXPECTED_COVERAGE[('v0.42.0','v0.20.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(2,3,0,5,8))

    def test_v043_coverage_adds_22_cards_and_52_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.42.0','v0.20.0')]
        self.assertEqual(prior,(44,37,1,109,181))
        revised=EXPECTED_COVERAGE[('v0.43.0','v0.20.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(6,12,4,22,52))

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
