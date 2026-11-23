import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_catalog import merge_sources, metrics

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
    ('v0.45.1','v0.21.1'):(56,50,5,144,256),
    ('v0.46.0','v0.21.1'):(56,53,5,147,264),
    ('v0.47.0','v0.21.1'):(56,53,7,149,269),
    ('v0.47.0','v0.24.0'):(56,53,7,153,277),
    ('v0.48.0','v0.24.0'):(56,56,18,167,303),
    ('v0.49.0','v0.24.0'):(56,57,18,168,308),
    ('v0.50.0','v0.24.0'):(56,57,22,172,316),
    ('v0.50.0','v0.27.0'):(56,57,22,178,326),
    ('v0.51.0','v0.27.0'):(56,57,24,180,328),
    ('v0.52.0','v0.27.0'):(60,57,29,189,343),
    ('v0.52.0','v0.28.0'):(60,57,29,190,350),
    ('v0.52.1','v0.28.0'):(60,57,29,190,350),
    ('v0.53.0','v0.28.0'):(62,60,29,195,359),
    ('v0.53.0','v0.29.0'):(62,60,29,195,359),
    ('v0.53.0','v0.30.0'):(62,60,29,196,362),
    ('v0.54.0','v0.30.0'):(62,62,29,197,367),
    ('v0.54.0','v0.31.0'):(62,62,29,205,390),
    ('v0.54.1','v0.31.0'):(64,64,29,209,399),
    ('v0.54.1','v0.31.1'):(64,64,29,220,428),
    ('v0.54.1','v0.32.0'):(64,64,29,227,446),
    ('v0.56.0','v0.32.0'):(64,66,29,229,450),
    ('v0.56.0','v0.33.0'):(64,66,29,229,453),
}

class DeliveryTests(unittest.TestCase):
    def test_workflow_actions_are_full_immutable_commits(self):
        text=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf8')
        pins=re.findall(r'uses:\s*([^\s]+)',text)
        self.assertEqual(len(pins),4)
        for pin in pins:self.assertRegex(pin,r'^[A-Za-z0-9_/-]+@[0-9a-f]{40}$')

    def test_registry_counts_have_not_lost_pinned_plugin_coverage(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        registry = json.loads((ROOT / 'data/registry.source.json').read_text(encoding='utf8'))
        audited = merge_sources(registry['sources'])
        withheld = [s for s in audited if s['kind'] == 'research-name']
        self.assertEqual(catalog['sources'], [s for s in audited if s['kind'] != 'research-name'])
        self.assertEqual(catalog['counts']['total'], len(catalog['sources']))
        self.assertEqual(catalog['counts'], metrics(catalog['sources']))
        for plugin, counts in catalog['countsByPlugin'].items():
            source_count = sum(any(use['plugin'] == plugin for use in source['uses']) for source in catalog['sources'])
            uses = [use for source in catalog['sources'] for use in source['uses'] if use['plugin'] == plugin]
            self.assertEqual(counts['total'], source_count)
            self.assertEqual(counts['citations'], sum(len(use['evidence']) for use in uses))
        versions=tuple(catalog['snapshots'][plugin]['version'] for plugin in ('agentic-vault','semantic-crosscheck'))
        expected=EXPECTED_COVERAGE[versions]
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['paper'],expected[0])
        self.assertEqual(catalog['countsByPlugin']['agentic-vault']['project']+catalog['countsByPlugin']['agentic-vault']['format'],expected[1])
        self.assertEqual(catalog['countsByPlugin']['agentic-vault'].get('article',0),expected[2])
        # Historical coverage includes the name-only rows retained in the audit registry.
        self.assertEqual((len(audited), metrics(audited)['citations']), expected[3:])
        sxc=catalog['countsByPlugin']['semantic-crosscheck']
        sxc_coverage={'v0.19.1':(13,26,41,3),'v0.20.0':(13,28,45,5),
                      'v0.21.0':(14,34,58,5),'v0.21.1':(14,34,58,5),
                      'v0.24.0':(15,38,66,5),
                      'v0.27.0':(15,44,76,5),
                      'v0.28.0':(16,45,83,5),'v0.29.0':(16,45,83,5),
                      'v0.30.0':(16,46,86,6 if versions[0]=='v0.54.0' else 5),
                      'v0.31.0':(21,55,109,7),
                      'v0.31.1':(23,69,138,10),
                      'v0.32.0':(28,76,156,10),
                      'v0.33.0':(28,77,159,11)}
        sxc_withheld = [s for s in withheld if any(u['plugin'] == 'semantic-crosscheck' for u in s['uses'])]
        sxc_withheld_rows = sum(len(u['evidence']) for s in sxc_withheld for u in s['uses']
                                if u['plugin'] == 'semantic-crosscheck')
        audit_shared = catalog['counts']['shared'] + metrics(withheld)['shared']
        self.assertEqual((sxc['paper'], sxc['total'] + len(sxc_withheld),
                          sxc['citations'] + sxc_withheld_rows, audit_shared), sxc_coverage[versions[1]])
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

    def test_v046_coverage_adds_three_format_cards_and_eight_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.45.1','v0.21.1')]
        self.assertEqual(prior,(56,50,5,144,256))
        revised=EXPECTED_COVERAGE[('v0.46.0','v0.21.1')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,3,0,3,8))

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

    def test_v047_coverage_adds_the_release_cited_cards_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.46.0','v0.21.1')]
        self.assertEqual(prior,(56,53,5,147,264))
        revised=EXPECTED_COVERAGE[('v0.47.0','v0.21.1')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,2,2,5))

    def test_public_data_has_no_local_paths_or_credentials(self):
        text=(ROOT/'data/catalog.json').read_text(encoding='utf8')
        pattern=r'(?i)(?<![A-Za-z])[a-z]:[\\/]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|op_u_[A-Za-z0-9]+|sk-[A-Za-z0-9]{16,}'
        self.assertIsNone(re.search(pattern,text),'A credential or local path was found in public data')

    def test_v048_coverage_adds_the_release_cited_cards_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.47.0','v0.24.0')]
        self.assertEqual(prior,(56,53,7,153,277))
        revised=EXPECTED_COVERAGE[('v0.48.0','v0.24.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,3,11,14,26))

    def test_v049_coverage_adds_one_project_and_five_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.48.0','v0.24.0')]
        self.assertEqual(prior,(56,56,18,167,303))
        revised=EXPECTED_COVERAGE[('v0.49.0','v0.24.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,1,0,1,5))

    def test_v050_coverage_adds_four_article_cards_and_eight_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.49.0','v0.24.0')]
        self.assertEqual(prior,(56,57,18,168,308))
        revised=EXPECTED_COVERAGE[('v0.50.0','v0.24.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,4,4,8))

    def test_sxc027_coverage_adds_six_cards_and_ten_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.50.0','v0.24.0')]
        self.assertEqual(prior,(56,57,22,172,316))
        revised=EXPECTED_COVERAGE[('v0.50.0','v0.27.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,0,6,10))

    def test_v051_coverage_adds_two_article_cards_and_two_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.50.0','v0.27.0')]
        self.assertEqual(prior,(56,57,22,178,326))
        revised=EXPECTED_COVERAGE[('v0.51.0','v0.27.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,2,2,2))

    def test_v052_coverage_adds_four_paper_and_five_article_cards_and_fifteen_citations_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.51.0','v0.27.0')]
        self.assertEqual(prior,(56,57,24,180,328))
        revised=EXPECTED_COVERAGE[('v0.52.0','v0.27.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(4,0,5,9,15))

    def test_v0521_repin_keeps_every_card_and_citation_without_rewriting_history(self):
        prior=EXPECTED_COVERAGE[('v0.52.0','v0.28.0')]
        self.assertEqual(prior,(60,57,29,190,350))
        revised=EXPECTED_COVERAGE[('v0.52.1','v0.28.0')]
        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,0,0,0))

    def test_v053_reference_pairs_point_to_the_feature_document_and_release(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['agentic-vault']['version']!='v0.53.0':
            self.skipTest('These citation locations describe the v0.53.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        expected={
            'doi:10.18653/v1/d19-1382':('paper','docs/ko-order-recall.md'),
            'github:google-research-datasets/paws':('project','docs/ko-order-recall.md'),
            'arxiv:2611.02017':('paper','docs/handoff-resume.md'),
            'github:miraclecsc/switch-swe':('project','docs/handoff-resume.md'),
            'github:simplistix/sybil':('project',None),
        }
        for identity,(kind,feature) in expected.items():
            with self.subTest(identity=identity):
                source=indexed[identity]
                self.assertEqual(source['kind'],kind)
                use,=source['uses']
                self.assertEqual((use['plugin'],use['role']),('agentic-vault','reference'))
                files=['docs/releases/v0.53.0.md']
                if feature:
                    files.append(feature)
                self.assertCountEqual([row['file'] for row in use['evidence']],files)
        self.assertEqual(set(indexed['doi:10.18653/v1/d19-1382']['keys']),
                         {'doi:10.18653/v1/d19-1382','arxiv:1908.11828','url:https://aclanthology.org/D19-1382'})

    def test_v054_references_cover_ecc_and_shared_connectome_record(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['agentic-vault']['version']!='v0.54.0':
            self.skipTest('These citation locations describe the v0.54.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        ecc=indexed['github:affaan-m/ecc']
        self.assertEqual(ecc['kind'],'project')
        self.assertEqual(set(ecc['keys']),{'github:affaan-m/ecc','github:affaan-m/everything-claude-code'})
        ecc_use,=ecc['uses']
        self.assertEqual((ecc_use['plugin'],ecc_use['role']),('agentic-vault','reference'))
        self.assertCountEqual(
            [row['file'] for row in ecc_use['evidence']],
            ['docs/releases/v0.54.0.md','skills/agentic-vault/scripts/vault_hook_wiring.py','skills/agentic-vault/scripts/vault_install_state.py'],
        )
        conn=indexed['doi:10.5281/zenodo.24361690']
        self.assertCountEqual([u['plugin'] for u in conn['uses']],['semantic-crosscheck','agentic-vault'])
        av_use=next(u for u in conn['uses'] if u['plugin']=='agentic-vault')
        self.assertCountEqual(
            [row['file'] for row in av_use['evidence']],
            ['docs/releases/v0.54.0.md','scripts/verify_release_claims.py'],
        )

    def test_sxc0310_references_cover_paired_stats_static_linters_and_shared_rulesets(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['semantic-crosscheck']['version']!='v0.31.0':
            self.skipTest('These citation locations describe the v0.31.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        papers=[
            'doi:10.1186/1471-2288-13-91',
            'doi:10.1002/(sici)1097-0258(19981130)17:22<2635::aid-sim954>3.0.co;2-c',
            'doi:10.1162/089976698300017197',
            'doi:10.1002/stvr.1486',
            'doi:10.1145/3243734.3243804',
        ]
        for pid in papers:
            with self.subTest(paper=pid):
                src=indexed[pid]
                self.assertEqual(src['kind'],'paper')
                use,=src['uses']
                self.assertEqual((use['plugin'],use['role']),('semantic-crosscheck','reference'))
                self.assertCountEqual(
                    [row['file'] for row in use['evidence']],
                    ['docs/releases/v0.31.0.md','THIRD_PARTY.md','docs/paired-release.md'],
                )
        for proj in ('github:astral-sh/ruff','github:astral-sh/ty','github:quarylabs/sqruff'):
            with self.subTest(project=proj):
                src=indexed[proj]
                self.assertEqual(src['kind'],'project')
                use,=src['uses']
                self.assertEqual((use['plugin'],use['role']),('semantic-crosscheck','reference'))
                self.assertCountEqual(
                    [row['file'] for row in use['evidence']],
                    ['docs/releases/v0.31.0.md','THIRD_PARTY.md'],
                )
        rulesets=indexed['url:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets']
        self.assertCountEqual([u['plugin'] for u in rulesets['uses']],['agentic-vault','semantic-crosscheck'])
        sxc_use=next(u for u in rulesets['uses'] if u['plugin']=='semantic-crosscheck')
        self.assertCountEqual(
            [row['file'] for row in sxc_use['evidence']],
            ['docs/releases/v0.31.0.md','THIRD_PARTY.md'],
        )

    def test_v0541_references_cover_unicode_hardening_actionlint_and_pillai_reuse(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['agentic-vault']['version']!='v0.54.1':
            self.skipTest('These citation locations describe the v0.54.1 release')
        indexed={source['id']:source for source in catalog['sources']}
        for sid,kind,files in [
            ('url:https://www.usenix.org/conference/usenixsecurity23/presentation/boucher','paper',['docs/releases/v0.54.1.md','SECURITY.md']),
            ('url:https://www.unicode.org/reports/tr39','format',['docs/releases/v0.54.1.md','SECURITY.md']),
            ('arxiv:2106.09898','paper',['docs/releases/v0.54.1.md','SECURITY.md']),
            ('github:rhysd/actionlint','project',['docs/releases/v0.54.1.md','docs/release-integrity.md']),
        ]:
            with self.subTest(source=sid):
                src=indexed[sid]
                self.assertEqual(src['kind'],kind)
                av_use=next(u for u in src['uses'] if u['plugin']=='agentic-vault')
                self.assertEqual(av_use['role'],'reference')
                self.assertCountEqual([row['file'] for row in av_use['evidence']],files)
        pillai=indexed['url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai']
        av_use=next(u for u in pillai['uses'] if u['plugin']=='agentic-vault')
        self.assertCountEqual(
            [row['file'] for row in av_use['evidence']],
            ['docs/releases/v0.42.0.md','docs/releases/v0.54.1.md'],
        )

    def test_sxc0311_references_cover_archive_unicode_collation_sbom_and_ci_hygiene(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['semantic-crosscheck']['version']!='v0.31.1':
            self.skipTest('These citation locations describe the v0.31.1 release')
        indexed={source['id']:source for source in catalog['sources']}
        expected_new=[
            ('url:https://reproducible-builds.org/specs/source-date-epoch','format',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('url:https://www.postgresql.org/docs/17/collation.html','article',['docs/releases/v0.31.1.md','THIRD_PARTY.md','docs/data-rules.md']),
            ('url:https://ecma-international.org/publications-and-standards/standards/ecma-424','format',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('url:https://docs.npmjs.com/cli/v11/commands/npm-sbom','article',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:cyclonedx/cyclonedx-python','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:zizmorcore/zizmor','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:pypa/pip-audit','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('doi:10.1145/3194164.3194186','paper',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:rohaquinlop/complexipy','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:jendrikseipp/vulture','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
            ('github:osprey-oss/deptry','project',['docs/releases/v0.31.1.md','THIRD_PARTY.md']),
        ]
        for sid,kind,files in expected_new:
            with self.subTest(source=sid):
                src=indexed[sid]
                self.assertEqual(src['kind'],kind)
                use,=src['uses']
                self.assertEqual((use['plugin'],use['role']),('semantic-crosscheck','reference'))
                self.assertCountEqual([row['file'] for row in use['evidence']],files)
        for shared_id in (
            'url:https://www.usenix.org/conference/usenixsecurity23/presentation/boucher',
            'url:https://www.unicode.org/reports/tr39',
            'github:rhysd/actionlint',
        ):
            with self.subTest(shared=shared_id):
                src=indexed[shared_id]
                self.assertCountEqual([u['plugin'] for u in src['uses']],['agentic-vault','semantic-crosscheck'])
                sxc_use=next(u for u in src['uses'] if u['plugin']=='semantic-crosscheck')
                self.assertEqual(sxc_use['role'],'reference')
                self.assertCountEqual([row['file'] for row in sxc_use['evidence']],['docs/releases/v0.31.1.md','THIRD_PARTY.md'])

    def test_sxc0320_references_cover_rls_evalues_summarizability_and_function_boundary(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['semantic-crosscheck']['version']!='v0.32.0':
            self.skipTest('These citation locations describe the v0.32.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        expected_new=[
            ('url:https://www.postgresql.org/docs/17/ddl-rowsecurity.html','article',['docs/releases/v0.32.0.md','THIRD_PARTY.md']),
            ('url:https://www.postgresql.org/docs/17/catalog-pg-index.html','article',['docs/releases/v0.32.0.md','THIRD_PARTY.md']),
            ('doi:10.1093/jrsssb/qkae011','paper',['docs/releases/v0.32.0.md','THIRD_PARTY.md','docs/paired-release.md']),
            ('doi:10.1214/23-sts894','paper',['docs/releases/v0.32.0.md','THIRD_PARTY.md','docs/paired-release.md']),
            ('doi:10.1214/20-aos1991','paper',['docs/releases/v0.32.0.md','THIRD_PARTY.md','docs/paired-release.md']),
            ('doi:10.1016/j.datak.2009.07.010','paper',['docs/releases/v0.32.0.md','THIRD_PARTY.md','docs/semantic-preflight.md']),
            ('doi:10.1145/3689031.3696064','paper',['docs/releases/v0.32.0.md','THIRD_PARTY.md']),
        ]
        for sid,kind,files in expected_new:
            with self.subTest(source=sid):
                src=indexed[sid]
                self.assertEqual(src['kind'],kind)
                use,=src['uses']
                self.assertEqual((use['plugin'],use['role']),('semantic-crosscheck','reference'))
                self.assertCountEqual([row['file'] for row in use['evidence']],files)
        self.assertEqual(set(indexed['doi:10.1093/jrsssb/qkae011']['keys']),{'doi:10.1093/jrsssb/qkae011','arxiv:1906.07801'})
        self.assertEqual(set(indexed['doi:10.1214/23-sts894']['keys']),{'doi:10.1214/23-sts894','arxiv:2210.01948'})
        self.assertEqual(set(indexed['doi:10.1214/20-aos1991']['keys']),{'doi:10.1214/20-aos1991','arxiv:1810.08240'})

    def test_av0560_references_cover_stock_team_harness_and_foldboost(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['agentic-vault']['version']!='v0.56.0':
            self.skipTest('These citation locations describe the v0.56.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        expected_new=[
            ('github:seulee26/stock-team-harness','project',['docs/releases/v0.55.0.md','README.md']),
            ('github:ai3inc/foldboost','project',['docs/releases/v0.56.0.md','README.md']),
        ]
        for sid,kind,files in expected_new:
            with self.subTest(source=sid):
                src=indexed[sid]
                self.assertEqual(src['kind'],kind)
                av_use=next(u for u in src['uses'] if u['plugin']=='agentic-vault')
                self.assertEqual(av_use['role'],'reference')
                self.assertCountEqual([row['file'] for row in av_use['evidence']],files)

    def test_sxc0330_references_cover_shared_foldboost(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        if catalog['snapshots']['semantic-crosscheck']['version']!='v0.33.0':
            self.skipTest('These citation locations describe the v0.33.0 release')
        indexed={source['id']:source for source in catalog['sources']}
        src=indexed['github:ai3inc/foldboost']
        self.assertEqual(src['kind'],'project')
        self.assertCountEqual([u['plugin'] for u in src['uses']],['agentic-vault','semantic-crosscheck'])
        sxc_use=next(u for u in src['uses'] if u['plugin']=='semantic-crosscheck')
        self.assertEqual(sxc_use['role'],'reference')
        self.assertCountEqual(
            [row['file'] for row in sxc_use['evidence']],
            ['docs/releases/v0.33.0.md','THIRD_PARTY.md','docs/paired-release.md'],
        )

if __name__=='__main__':unittest.main()
