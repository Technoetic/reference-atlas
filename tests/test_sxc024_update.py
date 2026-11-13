"""The v0.24 updater preserves curation and requires exact, pinned public evidence."""
import copy
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_delivery as delivery

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('update_sxc024_references'):
    import update_sxc024_references as updater
else:
    updater = None

# Provisional commit values belong only to these synthetic test fixtures.
OLD, NEW, AV = 'a' * 40, 'b' * 40, 'c' * 40
IDENTITIES = {
    'github:stryker-mutator/stryker-js': ('project', 'reference',
        'https://github.com/stryker-mutator/stryker-js/blob/959127763e5bbe2eb65f5341a8161780d6d8a476/packages/api/schema/stryker-core.json#L499-L503', 'docs/mutation-matrix.md'),
    'github:stryker-mutator/mutation-testing-elements': ('format', 'reference',
        'https://github.com/stryker-mutator/mutation-testing-elements/blob/4b5b62cc6bf81f23dd9521447131abeb51f895db/packages/report-schema/src/mutation-testing-report-schema.json#L43-L100', 'docs/mutation-matrix.md'),
    'arxiv:2004.00481': ('paper', 'reference', 'https://arxiv.org/abs/2004.00481v2', 'docs/join-aggregate-fixtures.md'),
    'github:georgia-tech-db/spes': ('project', 'background',
        'https://github.com/georgia-tech-db/spes/tree/8049f98d8e64a5c2c43d1ed581e7d5b6e0a006e2', 'docs/join-aggregate-fixtures.md'),
}


def texts_for(registry):
    texts = {}
    for source in registry['sources']:
        for use in source['uses']:
            if use['plugin'] != 'semantic-crosscheck':
                continue
            for row in use['evidence']:
                lines = texts.setdefault(row['file'], [])
                lines.extend(['unused line'] * max(0, row['line'] - len(lines)))
                lines[row['line'] - 1] = row['excerpt']
    for identity, (_, _, url, doc) in IDENTITIES.items():
        for file in ('THIRD_PARTY.md', doc):
            texts.setdefault(file, []).append(f'[{identity}]({url})')
    return texts


def fixture():
    prior = {'id': 'github:example/prior', 'kind': 'project', 'title': 'Prior source',
             'url': 'https://github.com/example/prior', 'year': None,
             'keys': ['github:example/prior', 'name:prior source'],
             'aliases': ['Historical alias'], 'tags': [], 'note': 'Preserve prior scope.',
             'uses': [{'plugin': 'agentic-vault', 'role': 'reference', 'evidence': [
                 {'file': 'README.md', 'line': 9, 'excerpt': 'AV original',
                  'url': f'https://github.com/Technoetic/agentic-vault/blob/{AV}/README.md#L9'}]},
                 {'plugin': 'semantic-crosscheck', 'role': 'background', 'evidence': [
                 {'file': 'README.md', 'line': 1, 'excerpt': 'Prior exact citation',
                  'url': f'https://github.com/Technoetic/semantic-crosscheck/blob/{OLD}/README.md#L1'}]}]}
    registry = {'schemaVersion': 1, 'updatedAt': '2026-11-12T00:00:00Z',
                'method': {'scope': 'Keep established scope.'},
                'snapshots': {'agentic-vault': {'version': 'v0.47.0', 'commit': AV},
                              'semantic-crosscheck': {'version': 'v0.21.1', 'commit': OLD}},
                'sources': [prior]}
    urls = [row['url'] for use in prior['uses'] for row in use['evidence']]
    artwork = {'schemaVersion': 1, 'count': 1, 'assets': [{
        'index': 1, 'sourceId': prior['id'], 'output': 'media/cards/card-001.webp',
        'sha256': '1' * 64, 'bytes': 123, 'dimensions': [960, 640],
        'prompt': 'Unique historical artwork concept',
        'generationEvidenceUrls': ['https://example.org/original-citation'],
        'evidenceUrls': urls, 'currentEvidenceUrls': copy.deepcopy(urls)}]}
    return registry, artwork, texts_for(registry)


class Sxc024UpdateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'The dry-run v0.24 source-bound updater must exist')

    def prepare(self, registry, artwork, texts, **kwargs):
        return updater.prepare_update(registry, artwork, texts.__getitem__, NEW,
                                      updated_at='2026-11-13T00:00:00Z', **kwargs)

    def test_literals_add_four_distinct_identities_and_eight_exact_citations(self):
        registry, images, summary = self.prepare(*fixture())
        added = {s['id']: s for s in registry['sources'][1:]}
        self.assertEqual(set(added), set(IDENTITIES))
        self.assertEqual((summary['addedCitations'], summary['counts']['total']), (8, 5))
        for identifier, (kind, role, url, doc) in IDENTITIES.items():
            source = added[identifier]
            self.assertEqual((source['kind'], source['uses'][0]['role']), (kind, role))
            self.assertEqual({r['file'] for r in source['uses'][0]['evidence']}, {'THIRD_PARTY.md', doc})
            for row in source['uses'][0]['evidence']:
                self.assertEqual(row['excerpt'], fixture()[2][row['file']][row['line'] - 1].strip()[:220])
            self.assertTrue(all('/blob/' + NEW + '/' in r['url'] for r in source['uses'][0]['evidence']))
        self.assertEqual(registry['snapshots']['semantic-crosscheck']['version'], 'v0.24.0')

    def test_existing_uses_aliases_artwork_and_av_snapshot_survive_and_inputs_are_immutable(self):
        registry, artwork, texts = fixture()
        before = copy.deepcopy((registry, artwork))
        texts['README.md'].insert(0, 'Inserted public heading')
        revised, images, summary = self.prepare(registry, artwork, texts)
        self.assertEqual((registry, artwork), before)
        self.assertEqual(revised['snapshots']['agentic-vault'], registry['snapshots']['agentic-vault'])
        prior, updated = registry['sources'][0], revised['sources'][0]
        self.assertEqual({k:v for k,v in prior.items() if k != 'uses'},
                         {k:v for k,v in updated.items() if k != 'uses'})
        self.assertEqual(prior['uses'][0], updated['uses'][0])
        self.assertEqual(updated['uses'][1]['role'], 'background')
        self.assertEqual(updated['uses'][1]['evidence'][0]['line'], 2)
        self.assertEqual(summary['priorSxcCitations'], 1)
        self.assertEqual({k:v for k,v in artwork['assets'][0].items() if k not in ('evidenceUrls','currentEvidenceUrls')},
                         {k:v for k,v in images['assets'][0].items() if k not in ('evidenceUrls','currentEvidenceUrls')})
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'],
                         [r['url'] for u in updated['uses'] for r in u['evidence']])

    def test_published_identity_set_and_all_prior_raw_records_are_preserved(self):
        registry = json.loads((ROOT / 'data/registry.source.json').read_text(encoding='utf8'))
        artwork = json.loads((ROOT / 'docs/card-artwork-unique-prompts.json').read_text(encoding='utf8'))
        if registry['snapshots']['agentic-vault']['version'] != 'v0.47.0':
            # The reconstruction below removes only this update's sources, so it describes the catalog this update
            # was published on (agentic-vault v0.47.0). agentic-vault v0.48.0 adds text-fallback sources without
            # artwork and repins every agentic-vault row; tests/test_av048_update.py covers that update.
            self.skipTest('The live catalog is past the agentic-vault v0.47.0 snapshot this reconstruction assumes')
        # Retain the complete original identity set when tests run after application too.
        registry['sources'] = [s for s in registry['sources'] if s['id'] not in IDENTITIES]
        artwork['assets'] = [a for a in artwork['assets'] if a['sourceId'] not in IDENTITIES]
        artwork['count'] = len(artwork['assets'])
        old = copy.deepcopy(registry)
        texts = texts_for(registry)
        revised, images, _ = self.prepare(registry, artwork, texts)
        self.assertEqual(len({s['id'] for s in old['sources']}), 149)
        self.assertEqual(revised['sources'][:len(old['sources'])], [
            {**s, 'uses': [{**u, 'evidence': [
                {**r, 'url': f"https://github.com/Technoetic/semantic-crosscheck/blob/{NEW}/{r['file']}#L{r['line']}"}
                for r in u['evidence']]} if u['plugin'] == 'semantic-crosscheck' else u for u in s['uses']]}
            for s in old['sources']])
        self.assertEqual(images['count'], 149)
        pending = json.loads((ROOT / 'docs/sxc024-card-artwork.pending.json').read_text(encoding='utf8'))
        revised, images, _ = self.prepare(registry, artwork, texts, pending_artwork=pending)
        from build_catalog import build
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for folder in ('data', 'docs', 'scripts', 'tests'):
                (target / folder).mkdir()
            for relative, document in (('data/registry.source.json', revised),
                                       ('docs/card-artwork-unique-prompts.json', images),
                                       ('docs/sxc024-card-artwork.pending.json', pending)):
                (target / relative).write_text(json.dumps(document), encoding='utf8')
            catalog = build(target)
            self.assertEqual((catalog['counts']['total'], catalog['counts']['citations']), (153, 277))
            self.assertEqual((catalog['countsByPlugin']['semantic-crosscheck']['paper'],
                              catalog['countsByPlugin']['semantic-crosscheck']['total'],
                              catalog['countsByPlugin']['semantic-crosscheck']['citations']), (15, 38, 66))
            with patch('test_delivery.ROOT', target):
                delivery.DeliveryTests().test_registry_counts_have_not_lost_pinned_plugin_coverage()
            for folder in ('src', 'styles', 'media'):
                shutil.copytree(ROOT / folder, target / folder)
            shutil.copyfile(ROOT / 'index.html', target / 'index.html')
            for file in ('build.mjs', 'build-identity.mjs'):
                shutil.copyfile(ROOT / 'scripts' / file, target / 'scripts' / file)
            for file in ('artwork-uniqueness.test.mjs', 'sxc024-artwork.test.mjs'):
                shutil.copyfile(ROOT / 'tests' / file, target / 'tests' / file)
            result = subprocess.run(['node', '--test'], cwd=target, capture_output=True, text=True, encoding='utf8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(['node', 'scripts/build.mjs'], cwd=target, capture_output=True, text=True, encoding='utf8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deployment = json.loads((target / 'dist/deployment-manifest.json').read_text(encoding='utf8'))
            for asset in pending['assets']:
                stem = Path(asset['output']).with_suffix('').as_posix()
                built_path = f"assets/{stem}.{deployment['buildId']}.webp"
                self.assertEqual(deployment['files'][built_path]['sha256'], asset['sha256'])

    def test_duplicate_reapplication_is_idempotent_including_timestamp_and_curation(self):
        registry, images, _ = self.prepare(*fixture())
        registry['sources'][-1]['aliases'].append('Reviewed additional alias')
        registry['sources'][-1]['note'] += ' Historical review.'
        again, same, summary = self.prepare(registry, images, fixture()[2])
        self.assertEqual((again, same), (registry, images))
        self.assertEqual((summary['addedCitations'], summary['repinnedCitations'], summary['addedSourceIds']), (0, 0, []))

    def test_missing_ambiguous_wrong_identity_or_unpinned_new_evidence_is_rejected(self):
        for mutate in (
            lambda t: t.update({'README.md': ['changed']}),
            lambda t: t.update({'README.md': ['Prior exact citation'] * 2}),
            lambda t: t.update({'docs/mutation-matrix.md': []}),
            lambda t: t.update({k: [line.replace('stryker-js/blob/', 'stryker-js-wrong/blob/') for line in v] for k,v in t.items()}),
            lambda t: t.update({k: [line.replace('2004.00481v2', '2004.00481v3') for line in v] for k,v in t.items()}),
            lambda t: t.update({k: [line.replace('959127763e5bbe2eb65f5341a8161780d6d8a476', 'main') for line in v] for k,v in t.items()}),
        ):
            registry, artwork, texts = fixture()
            before = copy.deepcopy((registry, artwork))
            mutate(texts)
            with self.assertRaises(ValueError):
                self.prepare(registry, artwork, texts)
            self.assertEqual((registry, artwork), before)

    def test_changed_excerpt_requires_exact_sha_bound_explicit_review(self):
        registry, artwork, texts = fixture()
        texts['README.md'] = ['Reviewed replacement citation']
        reviews = {'sxc_commit': NEW, 'reviews': [{
            'source_id': 'github:example/prior', 'file': 'README.md',
            'old_excerpt': 'Prior exact citation', 'new_excerpt': 'Reviewed replacement citation',
            'reason': 'Reviewed published wording changed while retaining the source use.'}]}
        revised, _, summary = self.prepare(registry, artwork, texts, reviewed_excerpts=reviews)
        self.assertEqual(revised['sources'][0]['uses'][1]['evidence'][0]['excerpt'], texts['README.md'][0])
        self.assertEqual(len(summary['reviewedExcerptChanges']), 1)
        for bad in ({**reviews, 'sxc_commit': OLD},
                    {**reviews, 'reviews': [{**reviews['reviews'][0], 'reason': ''}]},
                    {**reviews, 'reviews': [reviews['reviews'][0]] * 2}):
            with self.assertRaises(ValueError):
                self.prepare(registry, artwork, texts, reviewed_excerpts=bad)
        with self.assertRaises(ValueError):
            self.prepare(*fixture(), reviewed_excerpts=reviews)

    def test_reapplying_the_same_review_document_is_idempotent_at_its_bound_commit(self):
        registry, artwork, texts = fixture()
        texts['README.md'] = ['Reviewed replacement citation']
        reviews = {'sxc_commit': NEW, 'reviews': [{
            'source_id': 'github:example/prior', 'file': 'README.md',
            'old_excerpt': 'Prior exact citation', 'new_excerpt': 'Reviewed replacement citation',
            'reason': 'Reviewed public wording replacement.'}]}
        revised, images, _ = self.prepare(registry, artwork, texts, reviewed_excerpts=reviews)
        again, same, summary = self.prepare(revised, images, texts, reviewed_excerpts=reviews)
        self.assertEqual((again, same), (revised, images))
        self.assertEqual(summary['repinnedCitations'], 0)

    def test_reapply_preserves_four_separately_commissioned_artwork_records(self):
        registry, artwork, _ = self.prepare(*fixture())
        for index, source in enumerate(registry['sources'][1:], 2):
            urls = [row['url'] for use in source['uses'] for row in use['evidence']]
            artwork['assets'].append({
                'index': index, 'sourceId': source['id'], 'output': f'media/cards/card-{index}.webp',
                'sha256': str(index) * 64, 'bytes': index * 100, 'dimensions': [960, 640],
                'prompt': 'Separately commissioned source-specific visual ' + source['id'],
                'generationEvidenceUrls': urls, 'evidenceUrls': urls, 'currentEvidenceUrls': urls})
        artwork['count'] = 5
        revised, images, summary = self.prepare(registry, artwork, fixture()[2])
        self.assertEqual((revised, images), (registry, artwork))
        self.assertEqual(summary['pendingArtworkSourceIds'], [])

    def test_pending_commission_attaches_only_to_verified_source_rows_and_is_idempotent(self):
        pending = json.loads((ROOT / 'docs/sxc024-card-artwork.pending.json').read_text(encoding='utf8'))
        registry, artwork, texts = fixture()
        revised, images, summary = self.prepare(registry, artwork, texts, pending_artwork=pending)
        self.assertEqual((images['count'], summary['pendingArtworkSourceIds']), (5, []))
        by_id = {s['id']: s for s in revised['sources']}
        for asset, original in zip(images['assets'][1:], pending['assets']):
            self.assertEqual(asset['generationEvidenceUrls'], original['generationEvidenceUrls'])
            self.assertEqual(asset['sha256'], original['sha256'])
            self.assertEqual(asset['currentEvidenceUrls'],
                             [r['url'] for u in by_id[asset['sourceId']]['uses'] for r in u['evidence']])
        again, same, _ = self.prepare(revised, images, texts, pending_artwork=pending)
        self.assertEqual((again, same), (revised, images))
        for mutate in (lambda p: p['assets'][0].update(sourceId='github:wrong/source'),
                       lambda p: p['assets'][0].update(sha256='1' * 64),
                       lambda p: p['assets'][0].update(generationEvidenceUrls=[]),
                       lambda p: p.update(count=3),
                       lambda p: p['assets'][0].update(output='../outside.webp')):
            wrong = copy.deepcopy(pending)
            mutate(wrong)
            with self.assertRaises(ValueError):
                self.prepare(registry, artwork, texts, pending_artwork=wrong)

    def test_alias_collision_partial_update_and_corrupt_artwork_are_rejected(self):
        for mutate in (
            lambda r,a: r['sources'][0]['keys'].append('github:stryker-mutator/stryker-js'),
            lambda r,a: a['assets'][0].update(currentEvidenceUrls=[]),
            lambda r,a: a['assets'][0].update(generationEvidenceUrls=[]),
            lambda r,a: a.update(count=0),
            lambda r,a: a['assets'].append(copy.deepcopy(a['assets'][0])),
        ):
            registry, artwork, texts = fixture()
            mutate(registry, artwork)
            with self.assertRaises(ValueError):
                self.prepare(registry, artwork, texts)
        registry, artwork, _ = self.prepare(*fixture())
        registry['sources'].pop()
        with self.assertRaises(ValueError):
            self.prepare(registry, artwork, fixture()[2])

    def test_invalid_commit_is_rejected_before_reading_sources(self):
        for commit in ('main', 'B' * 40, 'b' * 39):
            with self.assertRaises(ValueError):
                updater.prepare_update(*fixture()[:2], lambda _: self.fail('must not read'), commit)

    def test_cli_reads_only_annotated_tag_blobs_and_defaults_to_no_writes(self):
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
                target.write_text(('\n' if file == 'README.md' else '') + '\n'.join(lines) + '\n', encoding='utf8')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'commit', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'tag', '-a', 'v0.24.0', '-m', 'fixture tag')
            paths = ['data/registry.source.json', 'docs/card-artwork-unique-prompts.json']
            for name, content in zip(paths, (registry, artwork)):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(content), encoding='utf8')
            pending_path = root / 'docs/sxc024-card-artwork.pending.json'
            pending_path.write_bytes((ROOT / 'docs/sxc024-card-artwork.pending.json').read_bytes())
            pending = json.loads(pending_path.read_text(encoding='utf8'))
            for asset in pending['assets']:
                target = root / asset['output']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / asset['output'], target)
            before = [(root / name).read_bytes() for name in paths]
            (plugin / 'THIRD_PARTY.md').write_text('Uncommitted incorrect worktree', encoding='utf8')
            args = ['--plugin-root', str(plugin), '--sxc-commit', commit,
                    '--pending-artwork', str(pending_path)]
            output = StringIO()
            with patch.object(updater, 'ROOT', root), redirect_stdout(output):
                self.assertEqual(updater.main(args), 0)
            self.assertEqual(json.loads(output.getvalue())['mode'], 'dry-run')
            self.assertEqual(before, [(root / name).read_bytes() for name in paths])
            with patch.object(updater, 'ROOT', root), redirect_stdout(StringIO()):
                with self.assertRaises(ValueError):
                    updater.main(['--plugin-root', str(plugin), '--sxc-commit', NEW, '--apply'])
            self.assertEqual(before, [(root / name).read_bytes() for name in paths])
            with patch.object(updater, 'ROOT', root), redirect_stdout(StringIO()):
                updater.main(args + ['--apply'])
            applied = [(root / name).read_bytes() for name in paths]
            self.assertNotEqual(before[0], applied[0])
            self.assertEqual(json.loads(applied[0])['sources'][0]['uses'][1]['evidence'][0]['line'], 2)
            self.assertEqual(json.loads(applied[1])['count'], 5)
            with patch.object(updater, 'ROOT', root), redirect_stdout(StringIO()):
                updater.main(args + ['--apply'])
            self.assertEqual(applied, [(root / name).read_bytes() for name in paths])
            (root / pending['assets'][0]['output']).write_bytes(b'corrupted image')
            with patch.object(updater, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'Actual pending WebP bytes'):
                    updater.main(args + ['--apply'])
            self.assertEqual(applied, [(root / name).read_bytes() for name in paths])
            git('tag', '-d', 'v0.24.0')
            git('tag', 'v0.24.0')
            with patch.object(updater, 'ROOT', root):
                with self.assertRaises(ValueError):
                    updater.main(args)


if __name__ == '__main__':
    unittest.main()
