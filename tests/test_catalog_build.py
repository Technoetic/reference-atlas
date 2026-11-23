import csv
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_catalog import build,merge_sources,metrics

def source(plugin,key='arxiv:2502.12110',title='A-MEM'):
    return {'id':key,'kind':'paper','title':title,'url':'https://arxiv.org/abs/2502.12110','year':2025,
            'keys':[key],'aliases':[],'tags':['memory'],'uses':[{'plugin':plugin,'role':'reference',
            'evidence':[{'file':'docs/test.md','line':1,'url':'https://github.com/Technoetic/'+plugin+'/blob/'+('a'*40)+'/docs/test.md#L1','excerpt':'A-MEM'}]}]}

class MergeTests(unittest.TestCase):
    def test_same_paper_across_two_plugins_is_one_source_with_both_citations(self):
        merged=merge_sources([source('agentic-vault'),source('semantic-crosscheck')])
        self.assertEqual(len(merged),1)
        self.assertEqual({x['plugin'] for x in merged[0]['uses']},{'agentic-vault','semantic-crosscheck'})
        self.assertEqual(metrics(merged)['shared'],1)

    def test_same_title_does_not_merge_different_identifiers(self):
        merged=merge_sources([source('agentic-vault'),source('semantic-crosscheck','arxiv:2502.12111')])
        self.assertEqual(len(merged),2)

    def test_multiple_evidence_rows_for_one_plugin_do_not_inflate_use_count(self):
        a=source('agentic-vault');b=source('agentic-vault')
        b['uses'][0]['evidence'][0]['line']=2
        b['uses'][0]['evidence'][0]['url']=b['uses'][0]['evidence'][0]['url'].replace('#L1','#L2')
        merged=merge_sources([a,b])
        self.assertEqual(len(merged[0]['uses']),1)
        self.assertEqual(len(merged[0]['uses'][0]['evidence']),2)

    def test_kind_conflict_for_the_same_strong_identity_is_rejected(self):
        a=source('agentic-vault');b=source('semantic-crosscheck');b['kind']='project'
        with self.assertRaises(ValueError):merge_sources([a,b])

    def test_missing_evidence_cannot_be_published(self):
        a=source('agentic-vault');a['uses'][0]['evidence']=[]
        with self.assertRaises(ValueError):merge_sources([a])

    def test_official_article_and_its_related_project_stay_separate(self):
        article=source('agentic-vault','url:https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit','NVIDIA Agent Toolkit article')
        article.update(kind='article',url='https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/')
        article['uses'][0]['role']='background'
        project=source('agentic-vault','github:nvidia/auto-ontology','Auto Ontology')
        project.update(kind='project',url='https://github.com/NVIDIA/auto-ontology')
        merged=merge_sources([article,project])
        counts=metrics(merged)
        self.assertEqual(len(merged),2)
        self.assertEqual(counts['article'],1)
        self.assertEqual(counts['project'],1)
        self.assertEqual(counts['format'],0)
        self.assertEqual(counts['citations'],2)

    def test_public_exports_withhold_unresolved_uses_and_include_a_subsequently_identified_paper(self):
        known = source('agentic-vault', 'name:identified paper', 'Identified paper')
        pending = source('semantic-crosscheck', 'name:pending title', 'Pending title')
        pending.update(kind='research-name', url=pending['uses'][0]['evidence'][0]['url'])
        pending['uses'][0]['role'] = 'unresolved'
        registry = {'schemaVersion': 1, 'sources': [known, pending], 'snapshots': {
            plugin: {'commit': 'a' * 40} for plugin in ('agentic-vault', 'semantic-crosscheck')}}
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data'
            data.mkdir()
            audit_file = data / 'registry.source.json'
            for identified in (False, True):
                with self.subTest(identified=identified):
                    if identified:
                        pending.update(kind='paper', url='https://arxiv.org/abs/2502.12111')
                        pending['keys'].append('arxiv:2502.12111')
                        pending['uses'][0]['role'] = 'reference'
                    original = json.dumps(registry)
                    audit_file.write_text(original, encoding='utf-8')
                    build(root)
                    self.assertEqual(audit_file.read_text(encoding='utf-8'), original)
                    catalog = json.loads((data / 'catalog.json').read_text(encoding='utf-8'))
                    with (data / 'catalog.csv').open(encoding='utf-8-sig', newline='') as stream:
                        rows = list(csv.DictReader(stream))
                    expected = [known, pending] if identified else [known]
                    self.assertEqual(catalog['sources'], expected)
                    self.assertEqual([row['id'] for row in rows], [s['id'] for s in expected])
                    self.assertEqual([row['evidence_urls'] for row in rows],
                                     [s['uses'][0]['evidence'][0]['url'] for s in expected])
                    self.assertEqual(catalog['counts']['total'], len(expected))
                    self.assertEqual(catalog['counts']['citations'], len(expected))
                    self.assertEqual(catalog['counts']['research-name'], 0)
                    self.assertEqual(catalog['countsByPlugin']['agentic-vault']['total'], 1)
                    sxc = catalog['countsByPlugin']['semantic-crosscheck']
                    self.assertEqual((sxc['total'], sxc['citations']), (int(identified), int(identified)))

if __name__=='__main__':unittest.main()
