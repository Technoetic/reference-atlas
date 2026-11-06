import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('update_sxc_preflight_references'):
    import update_sxc_preflight_references as updater
else:
    updater = None

OLD, NEW, AV = 'a' * 40, 'b' * 40, 'c' * 40
ARTICLE = 'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/'
ARTICLE_ID = 'url:' + ARTICLE.rstrip('/')
PROJECT_ID = 'github:nvidia/auto-ontology'
PIN = 'https://github.com/NVIDIA/auto-ontology/tree/c4495670947eb7b4616f0dd9900e5ced2a48ca1e'


def evidence(plugin, commit, file, line, excerpt):
    return {'file': file, 'line': line, 'excerpt': excerpt,
            'url': f'https://github.com/Technoetic/{plugin}/blob/{commit}/{file}#L{line}'}


def fixture():
    sources = []
    for identifier, kind, title, url, plugin, role, line in [
        ('github:example/prior', 'project', 'Prior', 'https://github.com/example/prior', 'semantic-crosscheck', 'reference', 1),
        (ARTICLE_ID, 'article', 'NVIDIA article', ARTICLE, 'agentic-vault', 'background', 1),
        (PROJECT_ID, 'project', 'NVIDIA Auto Ontology', 'https://github.com/NVIDIA/auto-ontology', 'agentic-vault', 'reference', 2),
    ]:
        row = evidence(plugin, OLD if plugin == 'semantic-crosscheck' else AV,
                       'README.md' if plugin == 'semantic-crosscheck' else 'docs/ontology-contracts.md',
                       line, 'Existing exact citation' if plugin == 'semantic-crosscheck' else title)
        sources.append({'id': identifier, 'kind': kind, 'title': title, 'url': url,
                        'year': None, 'keys': [identifier], 'aliases': [], 'tags': [],
                        'uses': [{'plugin': plugin, 'role': role, 'evidence': [row]}],
                        'note': 'Prior application and upstream pin remain recorded.'})
    registry = {'schemaVersion': 1, 'updatedAt': '2026-11-05T00:00:00+00:00',
                'snapshots': {'agentic-vault': {'version': 'v0.41.0', 'commit': AV},
                              'semantic-crosscheck': {'version': 'v0.19.1', 'commit': OLD}},
                'sources': sources}
    artwork = {'schemaVersion': 1, 'count': 3, 'policy': 'preserve', 'assets': []}
    for index, source in enumerate(sources, 1):
        urls = [row['url'] for use in source['uses'] for row in use['evidence']]
        artwork['assets'].append({'index': index, 'sourceId': source['id'],
            'output': f'media/cards/card-{index}.webp', 'sha256': str(index) * 64,
            'bytes': index * 100, 'dimensions': [600, 400], 'prompt': 'Original source-specific prompt ' + str(index),
            'factualConcept': 'Original concept ' + str(index),
            'generationEvidenceUrls': ['https://example.org/original/' + str(index)],
            'evidenceUrls': copy.deepcopy(urls), 'currentEvidenceUrls': copy.deepcopy(urls)})
    texts = {'README.md': ['Inserted heading', 'Inserted context', 'Existing exact citation'],
             'docs/semantic-preflight.md': ['Scope', f'[Article]({ARTICLE})', f'[Project]({PIN})'],
             'THIRD_PARTY.md': [f'[Context]({ARTICLE})', f'[Conceptual reference]({PIN})']}
    return registry, artwork, texts


class SxcPreflightUpdateTests(unittest.TestCase):
    def apply(self, registry, artwork, texts, commit=NEW, tag='v0.20.0'):
        self.assertIsNotNone(updater, 'The SXC source-bound update helper is not implemented')
        return updater.prepare_update(registry, artwork, texts.__getitem__, commit, tag,
                                      updated_at='2026-11-06T00:00:00+00:00')

    def test_shifted_prior_sxc_excerpt_is_refound_without_changing_av(self):
        registry, artwork, texts = fixture()
        before = copy.deepcopy((registry, artwork))
        revised, images, summary = self.apply(registry, artwork, texts)
        row = revised['sources'][0]['uses'][0]['evidence'][0]
        self.assertEqual((row['line'], row['excerpt']), (3, 'Existing exact citation'))
        self.assertEqual(row['url'], f'https://github.com/Technoetic/semantic-crosscheck/blob/{NEW}/README.md#L3')
        self.assertEqual(revised['snapshots']['agentic-vault'], registry['snapshots']['agentic-vault'])
        for old, new in zip(registry['sources'][1:], revised['sources'][1:]):
            self.assertEqual(new['uses'][0], old['uses'][0])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'], [row['url']])
        self.assertEqual((registry, artwork), before)
        self.assertEqual((summary['priorSxcCitations'], summary['repinnedCitations'], summary['remappedLines']), (1, 1, 1))

    def test_known_nvidia_sources_gain_four_citations_without_new_sources(self):
        registry, artwork, texts = fixture()
        revised, images, summary = self.apply(registry, artwork, texts)
        self.assertEqual([s['id'] for s in revised['sources']], [s['id'] for s in registry['sources']])
        for source, role in zip(revised['sources'][1:], ['background', 'reference']):
            self.assertEqual(len(source['uses']), 2)
            use = source['uses'][1]
            self.assertEqual((use['plugin'], use['role']), ('semantic-crosscheck', role))
            self.assertEqual([row['file'] for row in use['evidence']], ['docs/semantic-preflight.md', 'THIRD_PARTY.md'])
            for row in use['evidence']:
                self.assertEqual(row['excerpt'], texts[row['file']][row['line'] - 1].strip()[:220])
            self.assertTrue(source['note'].startswith(registry['sources'][1]['note']))
        self.assertEqual((summary['counts']['total'], summary['counts']['shared'], summary['counts']['citations']), (3, 2, 7))
        self.assertEqual(summary['addedCitations'], 4)
        self.assertEqual(summary['addedSourceIds'], [])

    def test_artwork_history_prompts_and_image_identity_are_preserved(self):
        registry, artwork, texts = fixture()
        revised, images, _ = self.apply(registry, artwork, texts)
        self.assertEqual({k: v for k, v in images.items() if k != 'assets'},
                         {k: v for k, v in artwork.items() if k != 'assets'})
        for original, current, source in zip(artwork['assets'], images['assets'], revised['sources']):
            protected = {k: v for k, v in original.items() if k not in {'evidenceUrls', 'currentEvidenceUrls'}}
            self.assertEqual({k: current[k] for k in protected}, protected)
            urls = [row['url'] for use in source['uses'] for row in use['evidence']]
            self.assertEqual(current['evidenceUrls'], urls)
            self.assertEqual(current['currentEvidenceUrls'], urls)

    def test_missing_or_ambiguous_prior_excerpt_cannot_authorize_update(self):
        for lines in ([], ['Inserted', 'Existing exact citation', 'Existing exact citation']):
            registry, artwork, texts = fixture()
            texts['README.md'] = lines
            before = copy.deepcopy((registry, artwork))
            with self.assertRaisesRegex(ValueError, 'unique exact match'):
                self.apply(registry, artwork, texts)
            self.assertEqual((registry, artwork), before)

    def test_missing_existing_source_or_artwork_is_not_silently_recreated(self):
        for part in ('source', 'artwork'):
            registry, artwork, texts = fixture()
            (registry['sources'] if part == 'source' else artwork['assets']).pop()
            with self.assertRaises(ValueError):
                self.apply(registry, artwork, texts)

    def test_new_source_urls_must_be_unique_in_each_exact_git_blob(self):
        for lines in ([], [f'[Article]({ARTICLE})'] * 2):
            registry, artwork, texts = fixture()
            texts['docs/semantic-preflight.md'] = lines
            with self.assertRaisesRegex(ValueError, 'unique exact URL'):
                self.apply(registry, artwork, texts)

    def test_unmatched_artwork_evidence_cannot_be_promoted_to_current(self):
        registry, artwork, texts = fixture()
        unknown = evidence('semantic-crosscheck', OLD, 'unknown.md', 1, 'Unknown')['url']
        artwork['assets'][0]['evidenceUrls'] = [unknown]
        artwork['assets'][0]['currentEvidenceUrls'] = [unknown]
        with self.assertRaisesRegex(ValueError, 'current citation'):
            self.apply(registry, artwork, texts)

    def test_same_sha_rerun_is_idempotent_including_timestamp_and_notes(self):
        revised, images, _ = self.apply(*fixture())
        texts = fixture()[2]
        again, current, summary = self.apply(revised, images, texts)
        self.assertEqual((again, current), (revised, images))
        self.assertEqual((summary['addedCitations'], summary['repinnedCitations']), (0, 0))

    def test_invalid_commit_or_different_tag_is_refused(self):
        for commit, tag in [('main', 'v0.20.0'), (NEW, 'v0.19.1')]:
            with self.assertRaises(ValueError):
                self.apply(*fixture(), commit=commit, tag=tag)

    def test_cli_dry_run_uses_exact_tag_without_writing_inputs(self):
        self.assertIsNotNone(updater, 'The SXC source-bound update helper is not implemented')
        registry, artwork, texts = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for file, lines in texts.items():
                path = root / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('\n'.join(lines) + '\n', encoding='utf8')
            def git(*arguments):
                return subprocess.run(['git', '-C', str(root), *arguments], capture_output=True, check=True)
            git('init', '--quiet')
            git('add', '--', *texts)
            git('-c', 'user.name=Atlas Test', '-c', 'user.email=atlas@example.invalid', 'commit', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD').stdout.decode().strip()
            git('branch', 'v0.20.0')
            for name, value in [('data/registry.source.json', registry), ('docs/card-artwork-unique-prompts.json', artwork)]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding='utf8')
            before = {name: (root / name).read_bytes() for name in ['data/registry.source.json', 'docs/card-artwork-unique-prompts.json']}
            with patch.object(updater, 'ROOT', root), self.assertRaises(subprocess.CalledProcessError):
                updater.main(['--plugin-root', str(root), '--commit', commit, '--tag', 'v0.20.0'])
            git('tag', 'v0.20.0')
            output = StringIO()
            with patch.object(updater, 'ROOT', root), redirect_stdout(output):
                code = updater.main(['--plugin-root', str(root), '--commit', commit, '--tag', 'v0.20.0'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())['mode'], 'dry-run')
            self.assertEqual({name: (root / name).read_bytes() for name in before}, before)


if __name__ == '__main__':
    unittest.main()
