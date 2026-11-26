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
    def test_connectome_software_record_resolves_from_archive_and_repository_identifiers(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        identifier='doi:10.5281/zenodo.24361690'
        for candidate in ('10.5281/zenodo.24361690', '10.5281/zenodo.24355565',
                          'https://zenodo.org/records/24361690',
                          'https://github.com/ai3inc/connectome-cognition-benchmark/tree/v1.1.0'):
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(identifier,'project'))
        self.assertEqual(find_matches(catalog,'connectome-cognition-benchmark')['status'],'possible')

    def test_ecc_repository_and_former_name_alias_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        for candidate in ('https://github.com/affaan-m/ECC',
                          'https://github.com/affaan-m/everything-claude-code',
                          'https://github.com/affaan-m/ECC/tree/v2.2.3'):
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),('github:affaan-m/ecc','project'))

    def test_sxc0310_paired_stats_and_static_linters_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://doi.org/10.1186/1471-2288-13-91','doi:10.1186/1471-2288-13-91','paper'),
            ('10.1002/(SICI)1097-0258(19981130)17:22<2635::AID-SIM954>3.0.CO;2-C','doi:10.1002/(sici)1097-0258(19981130)17:22<2635::aid-sim954>3.0.co;2-c','paper'),
            ('https://doi.org/10.1002/%28SICI%291097-0258%2819981130%2917:22%3C2635::AID-SIM954%3E3.0.CO;2-C','doi:10.1002/(sici)1097-0258(19981130)17:22<2635::aid-sim954>3.0.co;2-c','paper'),
            ('https://doi.org/10.1162/089976698300017197','doi:10.1162/089976698300017197','paper'),
            ('https://doi.org/10.1002/stvr.1486','doi:10.1002/stvr.1486','paper'),
            ('https://doi.org/10.1145/3243734.3243804','doi:10.1145/3243734.3243804','paper'),
            ('https://github.com/astral-sh/ruff','github:astral-sh/ruff','project'),
            ('https://github.com/astral-sh/ty','github:astral-sh/ty','project'),
            ('https://github.com/quarylabs/sqruff','github:quarylabs/sqruff','project'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))

    def test_av0541_unicode_hardening_and_actionlint_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://www.usenix.org/conference/usenixsecurity23/presentation/boucher',
             'url:https://www.usenix.org/conference/usenixsecurity23/presentation/boucher','paper'),
            ('https://www.unicode.org/reports/tr39/',
             'url:https://www.unicode.org/reports/tr39','format'),
            ('https://arxiv.org/abs/2106.09898v2','arxiv:2106.09898','paper'),
            ('https://github.com/rhysd/actionlint','github:rhysd/actionlint','project'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))

    def test_sxc0311_archive_collation_sbom_and_ci_hygiene_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://reproducible-builds.org/specs/source-date-epoch/','url:https://reproducible-builds.org/specs/source-date-epoch','format'),
            ('https://www.postgresql.org/docs/17/collation.html','url:https://www.postgresql.org/docs/17/collation.html','article'),
            ('https://ecma-international.org/publications-and-standards/standards/ecma-424/','url:https://ecma-international.org/publications-and-standards/standards/ecma-424','format'),
            ('https://docs.npmjs.com/cli/v11/commands/npm-sbom','url:https://docs.npmjs.com/cli/v11/commands/npm-sbom','article'),
            ('https://github.com/CycloneDX/cyclonedx-python','github:cyclonedx/cyclonedx-python','project'),
            ('https://github.com/zizmorcore/zizmor','github:zizmorcore/zizmor','project'),
            ('https://github.com/pypa/pip-audit','github:pypa/pip-audit','project'),
            ('https://doi.org/10.1145/3194164.3194186','doi:10.1145/3194164.3194186','paper'),
            ('https://github.com/rohaquinlop/complexipy','github:rohaquinlop/complexipy','project'),
            ('https://github.com/jendrikseipp/vulture','github:jendrikseipp/vulture','project'),
            ('https://github.com/osprey-oss/deptry','github:osprey-oss/deptry','project'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))

    def test_sxc0320_rls_evalues_summarizability_and_function_boundary_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://www.postgresql.org/docs/17/ddl-rowsecurity.html','url:https://www.postgresql.org/docs/17/ddl-rowsecurity.html','article'),
            ('https://www.postgresql.org/docs/17/catalog-pg-index.html','url:https://www.postgresql.org/docs/17/catalog-pg-index.html','article'),
            ('https://doi.org/10.1093/jrsssb/qkae011','doi:10.1093/jrsssb/qkae011','paper'),
            ('https://arxiv.org/abs/1906.07801','doi:10.1093/jrsssb/qkae011','paper'),
            ('https://doi.org/10.1214/23-STS894','doi:10.1214/23-sts894','paper'),
            ('https://arxiv.org/abs/2210.01948','doi:10.1214/23-sts894','paper'),
            ('https://doi.org/10.1214/20-AOS1991','doi:10.1214/20-aos1991','paper'),
            ('https://arxiv.org/abs/1810.08240','doi:10.1214/20-aos1991','paper'),
            ('https://doi.org/10.1016/j.datak.2009.07.010','doi:10.1016/j.datak.2009.07.010','paper'),
            ('https://doi.org/10.1145/3689031.3696064','doi:10.1145/3689031.3696064','paper'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))

    def test_av0560_stock_team_harness_and_foldboost_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://github.com/seulee26/stock-team-harness','github:seulee26/stock-team-harness','project'),
            ('https://github.com/seulee26/stock-team-harness/tree/v2.4.0','github:seulee26/stock-team-harness','project'),
            ('https://github.com/ai3inc/foldboost','github:ai3inc/foldboost','project'),
            ('https://github.com/ai3inc/foldboost/tree/v0.3.0','github:ai3inc/foldboost','project'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))
        self.assertEqual(find_matches(catalog,'FoldBoost')['status'],'possible')
        self.assertEqual(find_matches(catalog,'stock-team-harness')['status'],'possible')
        if catalog['snapshots']['semantic-crosscheck']['version']=='v0.33.0':
            fb,=find_matches(catalog,'https://github.com/ai3inc/foldboost')['matches']
            self.assertCountEqual([u['plugin'] for u in fb['uses']],['agentic-vault','semantic-crosscheck'])

    def test_av0570_opentoolsearch_resolves(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        for candidate in (
            'https://github.com/ai3inc/opentoolsearch',
            'https://github.com/ai3inc/opentoolsearch/tree/v0.2.1',
        ):
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),('github:ai3inc/opentoolsearch','project'))
        self.assertEqual(find_matches(catalog,'OpenToolSearch')['status'],'possible')

    def test_sxc0340_pg17_catalog_docs_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://www.postgresql.org/docs/17/catalog-pg-class.html',
             'url:https://www.postgresql.org/docs/17/catalog-pg-class.html','article'),
            ('https://www.postgresql.org/docs/17/catalog-pg-constraint.html',
             'url:https://www.postgresql.org/docs/17/catalog-pg-constraint.html','article'),
            ('https://www.postgresql.org/docs/17/ddl-partitioning.html',
             'url:https://www.postgresql.org/docs/17/ddl-partitioning.html','article'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))

    def test_av0580_hidden_markup_holm_ppi_and_skillcfi_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://arxiv.org/abs/2611.28763','arxiv:2611.28763','paper'),
            ('https://arxiv.org/abs/2611.28763v1','arxiv:2611.28763','paper'),
            ('https://doi.org/10.2307/4615733','doi:10.2307/4615733','paper'),
            ('https://doi.org/10.1126/science.adi6000','doi:10.1126/science.adi6000','paper'),
            ('https://arxiv.org/abs/2311.01453','arxiv:2311.01453','paper'),
            ('https://arxiv.org/abs/2311.01453v2','arxiv:2311.01453','paper'),
            ('https://arxiv.org/abs/2601.18777','arxiv:2601.18777','paper'),
            ('https://arxiv.org/abs/2611.24185','arxiv:2611.24185','paper'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))
        self.assertEqual(find_matches(catalog,'SkillCFI')['status'],'possible')
        self.assertEqual(find_matches(catalog,'PRECISE')['status'],'possible')

    def test_sxc0350_pg17_view_collation_symmetry_and_dominators_resolve(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        cases=[
            ('https://www.postgresql.org/docs/17/sql-createview.html',
             'url:https://www.postgresql.org/docs/17/sql-createview.html','article'),
            ('https://www.postgresql.org/docs/17/rules-privileges.html',
             'url:https://www.postgresql.org/docs/17/rules-privileges.html','article'),
            ('https://www.postgresql.org/docs/17/catalog-pg-database.html',
             'url:https://www.postgresql.org/docs/17/catalog-pg-database.html','article'),
            ('https://www.postgresql.org/docs/17/catalog-pg-collation.html',
             'url:https://www.postgresql.org/docs/17/catalog-pg-collation.html','article'),
            ('https://doi.org/10.1609/aaai.v39i11.33217',
             'doi:10.1609/aaai.v39i11.33217','paper'),
            ('https://arxiv.org/abs/2502.10155',
             'doi:10.1609/aaai.v39i11.33217','paper'),
            ('https://arxiv.org/abs/2502.10155v1',
             'doi:10.1609/aaai.v39i11.33217','paper'),
            ('https://doi.org/10.1145/2950290.2950322',
             'doi:10.1145/2950290.2950322','paper'),
        ]
        for candidate,expected_id,expected_kind in cases:
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),(expected_id,expected_kind))
        self.assertEqual(find_matches(catalog,'Dominator Mutants')['status'],'possible')

    def test_av0590_openai_math_resolves(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        for candidate in (
            'https://github.com/openai/math',
            'https://github.com/openai/math/tree/3344da59',
        ):
            with self.subTest(candidate=candidate):
                result=find_matches(catalog,candidate)
                self.assertEqual(result['status'],'known')
                source,=result['matches']
                self.assertEqual((source['id'],source['kind']),('github:openai/math','project'))
        self.assertEqual(find_matches(catalog,'openai/math')['status'],'possible')

    def test_sxc0360_openai_math_shared_cross_plugin_lookup(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        result=find_matches(catalog,'https://github.com/openai/math')
        self.assertEqual(result['status'],'known')
        source,=result['matches']
        self.assertEqual((source['id'],source['kind']),('github:openai/math','project'))
        self.assertCountEqual([u['plugin'] for u in source['uses']],['agentic-vault','semantic-crosscheck'])

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
