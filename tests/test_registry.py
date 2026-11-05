import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO,StringIO
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reference_identity import canonical_key,find_matches,validate_catalog
from check_references import main

def fixture():
    return {'schemaVersion':1,'sources':[{
        'id':'arxiv:2502.12110','kind':'paper','title':'A-MEM: Agentic Memory',
        'url':'https://arxiv.org/abs/2502.12110','year':2025,'tags':['memory'],
        'keys':['arxiv:2502.12110'],'aliases':['A-MEM'],
        'uses':[{'plugin':'agentic-vault','role':'reference','evidence':[{'url':'https://github.com/Technoetic/agentic-vault/blob/'+('a'*40)+'/docs/x.md#L1','file':'docs/x.md','line':1,'excerpt':'A-MEM'}]}]
    }]}

class IdentityTests(unittest.TestCase):
    def test_cross_language_contract_cases(self):
        for case in json.loads((ROOT/'tests/fixtures/identity-cases.json').read_text(encoding='utf8')):
            with self.subTest(input=case['input']):
                result=canonical_key(case['input'])
                self.assertEqual(None if result is None else result['key'],case['key'])

    def test_known_version_is_found_without_changing_registry(self):
        catalog=fixture();before=json.dumps(catalog)
        result=find_matches(catalog,'https://arxiv.org/pdf/2502.12110v8')
        self.assertEqual(result['status'],'known');self.assertEqual(len(result['matches']),1)
        self.assertEqual(json.dumps(catalog),before)

    def test_title_alias_is_possible_not_identity_certainty(self):
        self.assertEqual(find_matches(fixture(),'a-mem')['status'],'possible')

    def test_unknown_is_not_labeled_new(self):
        result=find_matches(fixture(),'https://arxiv.org/abs/2502.12111')
        self.assertEqual(result['status'],'not_found');self.assertEqual(result['matches'],[])

    def test_invalid_is_not_reported_as_an_unknown_source(self):
        self.assertEqual(find_matches(fixture(),'javascript:alert(1)')['status'],'invalid')

    def test_malformed_and_duplicate_identity_catalogs_fail_closed(self):
        for bad in [{},{'schemaVersion':1,'sources':[{}]}]:
            with self.assertRaises(ValueError):validate_catalog(bad)
        bad=fixture();bad['sources'].append(dict(bad['sources'][0]))
        with self.assertRaises(ValueError):validate_catalog(bad)

    def test_incomplete_or_unbound_evidence_cannot_certify_a_known_reference(self):
        for mutate in [lambda s:s.update(id=''),lambda s:s.update(title=4),
                       lambda s:s['uses'][0].update(evidence=[{}]),
                       lambda s:s['uses'][0]['evidence'][0].update(line=True),
                       lambda s:s['uses'][0]['evidence'][0].update(file='../outside.md')]:
            catalog=fixture();mutate(catalog['sources'][0])
            with self.subTest(source=catalog['sources'][0]['id']):
                with self.assertRaises(ValueError):validate_catalog(catalog)

    def test_cli_known_exit_and_multiline_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            catalog=Path(temp)/'catalog.json';catalog.write_text(json.dumps(fixture()),encoding='utf8')
            candidates=Path(temp)/'candidates.txt';candidates.write_text('https://arxiv.org/pdf/2502.12110v3\nhttps://arxiv.org/abs/2502.12111\n',encoding='utf8')
            cmd=[sys.executable,str(ROOT/'scripts/check_references.py'),'--catalog',str(catalog),'--input',str(candidates),'--json']
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual([x['status'] for x in json.loads(result.stdout)['results']],['known','not_found'])
            guarded=subprocess.run(cmd+['--fail-on-known'],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(guarded.returncode,3,guarded.stderr)

    def test_cli_bad_catalog_is_a_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            catalog=Path(temp)/'catalog.json';catalog.write_text('{}',encoding='utf8')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/check_references.py'),'--catalog',str(catalog),'--url','A-MEM','--json'],capture_output=True,text=True,encoding='utf8')
            self.assertNotEqual(result.returncode,0)

    def test_published_mode_fetches_only_the_registry_not_the_candidate(self):
        candidate='https://arxiv.org/pdf/2502.12110v9.pdf'
        output=StringIO()
        with patch('check_references.urlopen',return_value=BytesIO(json.dumps(fixture()).encode('utf8'))) as request:
            with redirect_stdout(output):result=main(['--published','--url',candidate,'--json'])
        self.assertEqual(result,0)
        target=request.call_args.args[0].full_url
        self.assertTrue(target.startswith('https://technoetic.github.io/reference-atlas/data/catalog.json?'))
        self.assertNotIn('2502.12110',target)
        self.assertEqual(json.loads(output.getvalue())['results'][0]['status'],'known')

if __name__=='__main__':unittest.main()
