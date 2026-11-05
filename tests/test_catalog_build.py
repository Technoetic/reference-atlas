import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_catalog import merge_sources,metrics

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

if __name__=='__main__':unittest.main()
