import copy
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('update_ontology_references'):
    from update_ontology_references import prepare_update, write_update
else:
    prepare_update = None

OLD = 'a' * 40
NEW = 'b' * 40
UPSTREAM = '2a24f5d34ef6b6e168a7f22d308504d3ab36a198'
ARTICLE = 'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/'


def fixture():
    evidence = {'file': 'README.md', 'line': 1,
                'url': f'https://github.com/Technoetic/agentic-vault/blob/{OLD}/README.md#L1',
                'excerpt': 'Existing exact citation'}
    source = {'id': 'github:example/prior', 'kind': 'project', 'title': 'Prior',
              'url': 'https://github.com/example/prior', 'year': None,
              'keys': ['github:example/prior'], 'aliases': [], 'tags': [],
              'uses': [{'plugin': 'agentic-vault', 'role': 'reference', 'evidence': [evidence]}]}
    registry = {'schemaVersion': 1, 'updatedAt': '2026-11-05T00:00:00+00:00',
                'snapshots': {'agentic-vault': {'commit': OLD, 'version': 'v0.40.1'}},
                'sources': [source]}
    artwork = {'schemaVersion': 1, 'count': 3, 'assets': [
        {'sourceId': source['id'], 'evidenceUrls': [evidence['url']]},
        {'sourceId': 'url:' + ARTICLE.rstrip('/'), 'evidenceUrls': [ARTICLE]},
        {'sourceId': 'github:nvidia/auto-ontology', 'evidenceUrls': []},
    ]}
    texts = {'README.md': ['Inserted heading', evidence['excerpt']],
             'docs/ontology-contracts.md': [f'Article [context]({ARTICLE})',
                 f'Project [design](https://github.com/NVIDIA/auto-ontology/tree/{UPSTREAM})'],
             'docs/releases/v0.41.0.md': [f'[Official article]({ARTICLE})',
                 f'[Auto Ontology](https://github.com/NVIDIA/auto-ontology/tree/{UPSTREAM})']}
    return registry, artwork, texts


class OntologyUpdateTests(unittest.TestCase):
    def apply(self, registry, artwork, texts):
        self.assertIsNotNone(prepare_update, 'The source-bound update helper is not implemented')
        return prepare_update(registry, artwork, texts.__getitem__, NEW, 'v0.41.0',
                              updated_at='2026-11-06T00:00:00+00:00')

    def test_shifted_prior_citations_and_active_artwork_repin_to_exact_new_lines(self):
        registry, artwork, texts = fixture()
        before = copy.deepcopy((registry, artwork))
        revised, images, summary = self.apply(registry, artwork, texts)
        row = revised['sources'][0]['uses'][0]['evidence'][0]
        self.assertEqual((row['line'], row['url']), (2,
            f'https://github.com/Technoetic/agentic-vault/blob/{NEW}/README.md#L2'))
        self.assertEqual(images['assets'][0]['evidenceUrls'], [row['url']])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'], [row['url']])
        self.assertEqual(images['assets'][0]['generationEvidenceUrls'],
                         [before[1]['assets'][0]['evidenceUrls'][0]])
        self.assertEqual((registry, artwork), before, 'Preparation must not mutate input objects')
        self.assertEqual(summary['priorAgenticVaultCitations'], 1)
        self.assertEqual(summary['remappedLines'], 1)

    def test_article_and_project_have_distinct_strong_identities_and_four_public_citations(self):
        revised, images, summary = self.apply(*fixture())
        added = {source['id']: source for source in revised['sources'][1:]}
        article = added['url:' + ARTICLE.rstrip('/')]
        project = added['github:nvidia/auto-ontology']
        self.assertEqual((article['kind'], article['uses'][0]['role']), ('article', 'background'))
        self.assertEqual((project['kind'], project['uses'][0]['role']), ('project', 'reference'))
        self.assertNotIn(project['id'], article['keys'])
        self.assertNotIn(article['id'], project['keys'])
        self.assertEqual(sum(len(s['uses'][0]['evidence']) for s in added.values()), 4)
        for source in added.values():
            self.assertEqual(len(next(a for a in images['assets'] if a['sourceId'] == source['id'])['evidenceUrls']), 2)
        self.assertEqual(summary['counts']['total'], 3)

    def test_missing_or_ambiguous_prior_excerpt_fails_without_mutating_inputs(self):
        for lines in [[], ['Existing exact citation'] * 3]:
            registry, artwork, texts = fixture()
            registry['sources'][0]['uses'][0]['evidence'][0]['line'] = 4
            registry['sources'][0]['uses'][0]['evidence'][0]['url'] = f'https://github.com/Technoetic/agentic-vault/blob/{OLD}/README.md#L4'
            texts['README.md'] = lines
            before = copy.deepcopy((registry, artwork))
            self.assertIsNotNone(prepare_update)
            with self.assertRaisesRegex(ValueError, 'unique'):
                prepare_update(registry, artwork, texts.__getitem__, NEW, 'v0.41.0')
            self.assertEqual((registry, artwork), before)

    def test_unsupported_release_or_invalid_commit_cannot_be_written(self):
        registry, artwork, texts = fixture()
        self.assertIsNotNone(prepare_update)
        for commit, tag in [('master', 'v0.41.0'), (NEW, 'v0.42.0')]:
            with self.assertRaises(ValueError):
                prepare_update(registry, artwork, texts.__getitem__, commit, tag)

    def test_same_sha_rerun_preserves_generation_history_without_adding_duplicate_sources(self):
        registry, artwork, texts = fixture()
        revised, images, _ = self.apply(registry, artwork, texts)
        again, current, summary = self.apply(revised, images, texts)
        self.assertEqual(again, revised)
        self.assertEqual(current, images)
        self.assertEqual(summary['addedSourceIds'], [])

    def test_same_named_branch_is_not_accepted_as_a_release_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.run(['git', '-C', directory, *args], capture_output=True, check=True)
            git('init', '--quiet')
            git('-c', 'user.name=Atlas Test', '-c', 'user.email=atlas@example.invalid',
                'commit', '--allow-empty', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD').stdout.decode().strip()
            git('branch', 'v0.41.0')
            checked = subprocess.run([sys.executable, str(ROOT / 'scripts/update_ontology_references.py'),
                '--plugin-root', directory, '--commit', commit, '--tag', 'v0.41.0'], capture_output=True)
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn(b'refs/tags/v0.41.0', checked.stderr)

    def test_apply_failure_restores_both_input_files_instead_of_leaving_split_snapshots(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ['registry.json', 'artwork.json']]
            for path in paths:
                path.write_bytes(b'original bytes\r\n')
            original_replace = os.replace
            calls = 0
            def fail_second(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('second replacement failed')
                return original_replace(source, target)
            with patch('update_ontology_references.os.replace', side_effect=fail_second):
                with self.assertRaisesRegex(OSError, 'second replacement failed'):
                    write_update([(path, {'changed': True}) for path in paths])
            self.assertEqual([p.read_bytes() for p in paths], [b'original bytes\r\n'] * 2)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['artwork.json', 'registry.json'])


if __name__ == '__main__':
    unittest.main()
