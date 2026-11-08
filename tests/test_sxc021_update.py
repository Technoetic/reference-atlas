import copy
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('update_sxc021_references'):
    import update_sxc021_references as updater
else:
    updater = None

OLD, NEW, AV = 'a' * 40, 'b' * 40, 'c' * 40
NEW_IDENTITIES = {
    'github:datacontract/datacontract-cli': 'https://github.com/datacontract/datacontract-cli',
    'github:bitol-io/open-data-contract-standard': 'https://github.com/bitol-io/open-data-contract-standard',
    'github:pganalyze/libpg_query': 'https://github.com/pganalyze/libpg_query',
    'github:lelit/pglast': 'https://github.com/lelit/pglast',
    'arxiv:2504.12058': 'https://arxiv.org/abs/2504.12058v3',
    'github:pierresenellart/provenance-lean': 'https://github.com/PierreSenellart/provenance-lean',
}


def evidence(plugin, sha, file, line, excerpt):
    return {'file': file, 'line': line, 'excerpt': excerpt,
            'url': f'https://github.com/Technoetic/{plugin}/blob/{sha}/{file}#L{line}'}


def fixture():
    sources = []
    for identifier, title, role in [
        ('github:example/prior', 'Prior source', 'reference'),
        ('github:pierresenellart/provsql', 'ProvSQL', 'background'),
    ]:
        excerpt = title + ' original citation'
        source = {'id': identifier, 'kind': 'project', 'title': title,
                  'url': 'https://github.com/' + identifier[7:], 'year': None,
                  'keys': [identifier, 'name:' + title.lower()],
                  'aliases': [title + ' legacy alias'], 'tags': ['평가·테스트'],
                  'uses': [{'plugin': 'semantic-crosscheck', 'role': role,
                            'evidence': [evidence('semantic-crosscheck', OLD, 'README.md',
                                                  len(sources) + 1, excerpt)]}],
                  'note': 'Existing scope must survive.'}
        if not sources:
            source['uses'].insert(0, {'plugin': 'agentic-vault', 'role': 'reference',
                                     'evidence': [evidence('agentic-vault', AV, 'docs/prior.md',
                                                           9, 'AV citation') ]})
        sources.append(source)
    registry = {'schemaVersion': 1, 'updatedAt': '2026-11-07T00:00:00Z',
                'method': {'absence': 'Not proof of novelty.', 'scope': 'Prior scope.'},
                'snapshots': {'agentic-vault': {'version': 'v0.43.0', 'commit': AV},
                              'semantic-crosscheck': {'version': 'v0.20.0', 'commit': OLD}},
                'sources': sources}
    artwork = {'schemaVersion': 1, 'count': 2, 'policy': 'No borrowed artwork.', 'assets': []}
    for index, source in enumerate(sources, 1):
        urls = [row['url'] for use in source['uses'] for row in use['evidence']]
        artwork['assets'].append({'index': index, 'sourceId': source['id'],
            'output': f'media/cards/card-{index}.webp', 'sha256': str(index) * 64,
            'bytes': index * 100, 'dimensions': [600, 400], 'prompt': 'Unique concept ' + str(index),
            'generationEvidenceUrls': ['https://example.org/original/' + str(index)],
            'evidenceUrls': copy.deepcopy(urls), 'currentEvidenceUrls': copy.deepcopy(urls)})
    urls = list(NEW_IDENTITIES.values())
    texts = {'README.md': ['Inserted heading', 'Prior source original citation', 'ProvSQL original citation'],
             'docs/contract-report.md': [f'[Contract CLI]({urls[0]})', f'[ODCS]({urls[1]})'],
             'docs/sql-structure.md': [f'[libpg_query]({urls[2]}#license)', f'[pglast]({urls[3]}/tree/v7.22)'],
             'docs/provenance-fixtures.md': [f'[Paper]({urls[4]})',
                 f'[Scope]({urls[5]}/blob/92af5cf2a057dfb46aab0a364d4ade5fde9c5699/Provenance/QueryAdequacy.lean#L17-L46)',
                 f'[Counterexample]({urls[5]}/blob/92af5cf2a057dfb46aab0a364d4ade5fde9c5699/Provenance/QueryAdequacy.lean#L411-L452)'],
             'THIRD_PARTY.md': [f'[Reference {i}]({url})' for i, url in enumerate(urls)]}
    return registry, artwork, texts


class Sxc021UpdateTests(unittest.TestCase):
    def apply(self, registry, artwork, texts, commit=NEW, tag='v0.21.0'):
        self.assertIsNotNone(updater, 'The v0.21.0 source-bound updater is not implemented')
        return updater.prepare_update(registry, artwork, texts.__getitem__, commit, tag,
                                      updated_at='2026-11-08T00:00:00Z')

    def test_existing_keys_aliases_roles_and_av_uses_survive_exact_repin(self):
        registry, artwork, texts = fixture()
        before = copy.deepcopy((registry, artwork))
        revised, images, summary = self.apply(registry, artwork, texts)
        self.assertEqual((registry, artwork), before)
        self.assertEqual(revised['snapshots']['agentic-vault'], registry['snapshots']['agentic-vault'])
        for old, new in zip(registry['sources'], revised['sources']):
            for field in ('id', 'keys', 'aliases', 'tags', 'title', 'note'):
                self.assertEqual(new[field], old[field])
            self.assertEqual([use['role'] for use in new['uses']], [use['role'] for use in old['uses']])
            for old_use, new_use in zip(old['uses'], new['uses']):
                if old_use['plugin'] == 'agentic-vault':
                    self.assertEqual(new_use, old_use)
                else:
                    row = new_use['evidence'][0]
                    self.assertEqual(row['line'], old_use['evidence'][0]['line'] + 1)
                    self.assertIn('/blob/' + NEW + '/', row['url'])
                    self.assertEqual(row['excerpt'], texts['README.md'][row['line'] - 1])
        self.assertEqual((summary['priorSxcCitations'], summary['repinnedCitations'], summary['remappedLines']), (2, 2, 2))

    def test_separate_curated_rows_for_a_shared_identity_keep_both_plugins_and_notes(self):
        registry, artwork, texts = fixture()
        original = registry['sources'][0]
        sxc = copy.deepcopy(original)
        sxc.update(aliases=['Separate SXC alias'], note='Separate SXC scope.')
        sxc['uses'] = [sxc['uses'][1]]
        original['uses'] = [original['uses'][0]]
        registry['sources'].append(sxc)
        before = copy.deepcopy(registry['sources'])
        revised, images, summary = self.apply(registry, artwork, texts)
        self.assertEqual(len(revised['sources']), 9)
        self.assertEqual(revised['sources'][0], before[0])
        for field in ('keys', 'aliases', 'note'):
            self.assertEqual(revised['sources'][2][field], before[2][field])
        self.assertEqual(summary['counts']['total'], 8)
        self.assertEqual(summary['counts']['shared'], 1)
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'], [
            f'https://github.com/Technoetic/agentic-vault/blob/{AV}/docs/prior.md#L9',
            f'https://github.com/Technoetic/semantic-crosscheck/blob/{NEW}/README.md#L2'])

    def test_six_distinct_canonical_sources_gain_public_evidence_without_artwork(self):
        revised, images, summary = self.apply(*fixture())
        new_sources = {source['id']: source for source in revised['sources'][2:]}
        self.assertEqual(set(new_sources), set(NEW_IDENTITIES))
        self.assertEqual(summary['addedSourceIds'], sorted(NEW_IDENTITIES))
        self.assertEqual((summary['counts']['total'], summary['addedCitations'], images['count']), (8, 13, 2))
        self.assertEqual(new_sources['arxiv:2504.12058']['kind'], 'paper')
        self.assertEqual(new_sources['github:bitol-io/open-data-contract-standard']['kind'], 'format')
        self.assertEqual(new_sources['github:lelit/pglast']['kind'], 'project')
        for source in new_sources.values():
            self.assertEqual(source['uses'][0]['role'], 'reference')
            self.assertNotIn(source['id'], {asset['sourceId'] for asset in images['assets']})
            for row in source['uses'][0]['evidence']:
                self.assertIn('/blob/' + NEW + '/', row['url'])
                self.assertTrue(row['excerpt'])

    def test_artwork_generation_assignments_and_all_image_fields_are_preserved(self):
        registry, artwork, texts = fixture()
        revised, images, _ = self.apply(registry, artwork, texts)
        self.assertEqual({k: v for k, v in images.items() if k != 'assets'},
                         {k: v for k, v in artwork.items() if k != 'assets'})
        for old, new, source in zip(artwork['assets'], images['assets'], revised['sources']):
            protected = {k: v for k, v in old.items() if k not in {'evidenceUrls', 'currentEvidenceUrls'}}
            self.assertEqual({k: new[k] for k in protected}, protected)
            expected = [row['url'] for use in source['uses'] for row in use['evidence']]
            self.assertEqual(new['evidenceUrls'], expected)
            self.assertEqual(new['currentEvidenceUrls'], expected)

    def test_missing_or_ambiguous_relocated_prior_excerpt_fails_without_mutation(self):
        for lines in ([], ['Changed', 'Prior source original citation', 'Prior source original citation']):
            registry, artwork, texts = fixture()
            texts['README.md'] = lines
            before = copy.deepcopy((registry, artwork))
            with self.assertRaisesRegex(ValueError, 'unique exact match'):
                self.apply(registry, artwork, texts)
            self.assertEqual((registry, artwork), before)

    def test_missing_or_extra_new_citation_does_not_silently_authorize_use(self):
        for lines in ([], fixture()[2]['docs/contract-report.md'] * 2):
            registry, artwork, texts = fixture()
            texts['docs/contract-report.md'] = lines
            with self.assertRaisesRegex(ValueError, 'Expected 1 exact citation'):
                self.apply(registry, artwork, texts)

    def test_similarly_named_repo_or_other_paper_version_is_not_the_expected_citation(self):
        for file, old, wrong in [
            ('docs/contract-report.md', 'https://github.com/datacontract/datacontract-cli',
             'https://github.com/datacontract/datacontract-cli-different'),
            ('docs/provenance-fixtures.md', 'https://arxiv.org/abs/2504.12058v3',
             'https://arxiv.org/abs/2504.12058v31'),
        ]:
            registry, artwork, texts = fixture()
            texts[file] = [line.replace(old, wrong) for line in texts[file]]
            with self.assertRaisesRegex(ValueError, 'Expected 1 exact citation'):
                self.apply(registry, artwork, texts)

    def test_existing_strong_alias_collision_is_not_added_as_a_new_reference(self):
        registry, artwork, texts = fixture()
        registry['sources'][0]['keys'].append('github:lelit/pglast')
        with self.assertRaisesRegex(ValueError, 'already belongs'):
            self.apply(registry, artwork, texts)

    def test_unmatched_artwork_source_or_current_evidence_is_refused(self):
        for mutate in (lambda art: art['assets'][0].update(sourceId='github:missing/source'),
                       lambda art: art['assets'][0].update(currentEvidenceUrls=[]),
                       lambda art: art['assets'][0].update(generationEvidenceUrls=[]),
                       lambda art: art['assets'].pop()):
            registry, artwork, texts = fixture()
            mutate(artwork)
            with self.assertRaises(ValueError):
                self.apply(registry, artwork, texts)

    def test_bad_commit_hash_or_release_tag_is_refused(self):
        for commit, tag in [('main', 'v0.21.0'), ('b' * 39, 'v0.21.0'), ('B' * 40, 'v0.21.0'),
                            (NEW, 'v0.20.0')]:
            with self.assertRaises(ValueError):
                self.apply(*fixture(), commit=commit, tag=tag)

    def test_repeated_same_commit_is_idempotent_with_no_fake_art_generation(self):
        revised, images, _ = self.apply(*fixture())
        again, same_images, summary = self.apply(revised, images, fixture()[2])
        self.assertEqual((again, same_images), (revised, images))
        self.assertEqual((summary['addedCitations'], summary['repinnedCitations'], summary['addedSourceIds']), (0, 0, []))

    def commissioned(self, identifiers):
        registry, artwork, _ = self.apply(*fixture())
        sources = {source['id']: source for source in registry['sources']}
        for index, identifier in enumerate(identifiers, 3):
            urls = [row['url'] for use in sources[identifier]['uses'] for row in use['evidence']]
            artwork['assets'].append({'index': index, 'sourceId': identifier,
                'output': f'media/cards/card-{index}.webp', 'sha256': f'{index:064x}',
                'bytes': index * 100, 'dimensions': [960, 640],
                'prompt': 'Separately generated concept for ' + identifier,
                'generationEvidenceUrls': copy.deepcopy(urls),
                'evidenceUrls': copy.deepcopy(urls), 'currentEvidenceUrls': copy.deepcopy(urls)})
        artwork['count'] = len(artwork['assets'])
        return registry, artwork, fixture()[2]

    def test_reapply_preserves_all_six_commissioned_images_and_is_idempotent(self):
        registry, artwork, texts = self.commissioned(NEW_IDENTITIES)
        before = copy.deepcopy((registry, artwork))
        revised, images, summary = self.apply(registry, artwork, texts)
        self.assertEqual((revised, images), before)
        self.assertEqual((registry, artwork), before)
        self.assertEqual((summary['artworkCount'], summary['textFallbackSourceIds']), (8, []))
        again, same_images, repeated = self.apply(revised, images, texts)
        self.assertEqual((again, same_images), before)
        self.assertEqual((repeated['repinnedCitations'], repeated['addedCitations']), (0, 0))

    def test_partial_commission_reports_only_the_actual_remaining_fallbacks(self):
        registry, artwork, texts = self.commissioned([
            'github:datacontract/datacontract-cli', 'github:lelit/pglast'])
        revised, images, summary = self.apply(registry, artwork, texts)
        self.assertEqual(images, artwork)
        self.assertEqual(summary['textFallbackSourceIds'], [
            'arxiv:2504.12058', 'github:bitol-io/open-data-contract-standard',
            'github:pganalyze/libpg_query', 'github:pierresenellart/provenance-lean'])

    def test_commissioned_new_artwork_rejects_unknown_duplicate_missing_and_bad_evidence(self):
        for mutation in ('unknown', 'duplicate', 'missing-prior', 'evidence', 'current', 'both-current', 'generation'):
            with self.subTest(mutation=mutation):
                registry, artwork, texts = self.commissioned(NEW_IDENTITIES)
                if mutation == 'unknown':
                    artwork['assets'][-1]['sourceId'] = 'github:missing/source'
                elif mutation == 'duplicate':
                    artwork['assets'].append(copy.deepcopy(artwork['assets'][-1]))
                    artwork['count'] += 1
                elif mutation == 'missing-prior':
                    artwork['assets'].pop(0)
                    artwork['count'] -= 1
                elif mutation == 'both-current':
                    urls = copy.deepcopy(artwork['assets'][0]['evidenceUrls'])
                    artwork['assets'][-1].update(evidenceUrls=urls, currentEvidenceUrls=urls)
                else:
                    key = {'evidence': 'evidenceUrls', 'current': 'currentEvidenceUrls',
                           'generation': 'generationEvidenceUrls'}[mutation]
                    artwork['assets'][-1][key] = []
                before = copy.deepcopy((registry, artwork))
                with self.assertRaises(ValueError):
                    self.apply(registry, artwork, texts)
                self.assertEqual((registry, artwork), before)

    def test_new_id_artwork_without_an_existing_catalog_source_is_refused(self):
        registry, artwork, texts = fixture()
        asset = copy.deepcopy(artwork['assets'][0])
        asset['sourceId'] = 'github:lelit/pglast'
        artwork['assets'].append(asset)
        artwork['count'] += 1
        before = copy.deepcopy((registry, artwork))
        with self.assertRaises(ValueError):
            self.apply(registry, artwork, texts)
        self.assertEqual((registry, artwork), before)

    def test_corrective_release_repins_commissioned_artwork_without_changing_generation_history(self):
        registry, artwork, texts = self.commissioned(NEW_IDENTITIES)
        before = copy.deepcopy(artwork)
        for file in texts:
            texts[file].insert(0, 'Corrective release heading')
        revised, images, summary = self.apply(registry, artwork, texts, commit='d' * 40, tag='v0.21.1')
        for old, new in zip(before['assets'], images['assets']):
            self.assertEqual({k: v for k, v in old.items() if k not in {'evidenceUrls', 'currentEvidenceUrls'}},
                             {k: v for k, v in new.items() if k not in {'evidenceUrls', 'currentEvidenceUrls'}})
            self.assertTrue(any('/blob/' + 'd' * 40 + '/' in url for url in new['currentEvidenceUrls']))
        self.assertEqual(summary['textFallbackSourceIds'], [])

    def test_corrective_release_repins_existing_six_without_losing_source_history(self):
        revised, images, _ = self.apply(*fixture())
        for source in revised['sources'][2:]:
            source['keys'].append('name:reviewed ' + source['id'])
            source['aliases'].append('Prior reviewed alias for ' + source['id'])
            source['note'] += ' Prior review history must survive the patch release.'
        before_sources = copy.deepcopy(revised['sources'])
        before_images = copy.deepcopy(images)
        texts = fixture()[2]
        for file in texts:
            texts[file].insert(0, 'Corrective release heading')
        patch_sha = 'd' * 40
        patched, patched_images, summary = self.apply(revised, images, texts, commit=patch_sha, tag='v0.21.1')
        self.assertEqual(len(patched['sources']), 8)
        self.assertEqual((summary['priorSxcCitations'], summary['repinnedCitations'], summary['addedCitations']), (15, 15, 0))
        self.assertEqual(summary['addedSourceIds'], [])
        self.assertEqual(patched['snapshots']['semantic-crosscheck']['version'], 'v0.21.1')
        for old, new in zip(before_sources, patched['sources']):
            self.assertEqual({k:v for k,v in old.items() if k!='uses'},
                             {k:v for k,v in new.items() if k!='uses'})
            for use in new['uses']:
                if use['plugin']=='semantic-crosscheck':
                    self.assertTrue(all('/blob/'+patch_sha+'/' in row['url'] for row in use['evidence']))
        for old, new in zip(before_images['assets'], patched_images['assets']):
            self.assertEqual({k:v for k,v in old.items() if k not in {'evidenceUrls','currentEvidenceUrls'}},
                             {k:v for k,v in new.items() if k not in {'evidenceUrls','currentEvidenceUrls'}})
        again, again_images, repeated = self.apply(patched, patched_images, texts, commit=patch_sha, tag='v0.21.1')
        self.assertEqual((again, again_images), (patched, patched_images))
        self.assertEqual((repeated['repinnedCitations'], repeated['addedCitations'], repeated['addedSourceIds']), (0, 0, []))

    def test_corrective_release_refuses_a_changed_existing_source_role(self):
        revised, images, _ = self.apply(*fixture())
        revised['sources'][2]['uses'][0]['role']='background'
        with self.assertRaisesRegex(ValueError, 'identity or cited use'):
            self.apply(revised, images, fixture()[2], commit='d'*40, tag='v0.21.1')

    def test_cli_reads_tagged_git_blobs_and_dry_run_never_writes(self):
        self.assertIsNotNone(updater, 'The v0.21.0 source-bound updater is not implemented')
        registry, artwork, texts = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plugin = root / 'plugin'
            plugin.mkdir()
            def git(*args):
                return subprocess.run(['git', '-C', str(plugin), *args], check=True,
                                      capture_output=True, text=True, encoding='utf8').stdout.strip()
            git('init')
            for file, lines in texts.items():
                target = plugin / file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('\n'.join(lines) + '\n', encoding='utf8')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'commit', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            git('tag', 'v0.21.0')
            git('tag', 'v0.21.1')
            for name, document in [('data/registry.source.json', registry), ('docs/card-artwork-unique-prompts.json', artwork)]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(document), encoding='utf8')
            # The worktree can change; citations must still use the tagged immutable blob.
            (plugin / 'docs/contract-report.md').write_text('Uncommitted unrelated content', encoding='utf8')
            before = [(root / file).read_bytes() for file in ['data/registry.source.json', 'docs/card-artwork-unique-prompts.json']]
            output = StringIO()
            with patch.object(updater, 'ROOT', root), redirect_stdout(output):
                self.assertEqual(updater.main(['--plugin-root', str(plugin), '--commit', commit, '--tag', 'v0.21.0']), 0)
            result = json.loads(output.getvalue())
            self.assertEqual((result['mode'], result['snapshot']['commit']), ('dry-run', commit))
            patch_output = StringIO()
            with patch.object(updater, 'ROOT', root), redirect_stdout(patch_output):
                self.assertEqual(updater.main(['--plugin-root', str(plugin), '--commit', commit, '--tag', 'v0.21.1']), 0)
            self.assertEqual(json.loads(patch_output.getvalue())['snapshot']['version'], 'v0.21.1')
            self.assertEqual(before, [(root / file).read_bytes() for file in ['data/registry.source.json', 'docs/card-artwork-unique-prompts.json']])
            with patch.object(updater, 'ROOT', root), redirect_stdout(StringIO()):
                with self.assertRaisesRegex(ValueError, 'tag'):
                    updater.main(['--plugin-root', str(plugin), '--commit', NEW, '--tag', 'v0.21.0', '--apply'])
            self.assertEqual(before, [(root / file).read_bytes() for file in ['data/registry.source.json', 'docs/card-artwork-unique-prompts.json']])


if __name__ == '__main__':
    unittest.main()
