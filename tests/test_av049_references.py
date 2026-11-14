import copy
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    updater = importlib.import_module('update_av049_references')
except ModuleNotFoundError:
    updater = None

OLD, NEW = 'a' * 40, 'b' * 40
PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'
URL = 'https://github.com/Q00/ouroboros'
RELEASE = 'docs/releases/v0.49.0.md'


def fixture():
    av = {'file': 'README.md', 'line': 1, 'url': PREFIX + OLD + '/README.md#L1',
          'excerpt': 'Prior project reference.'}
    sxc = {'file': 'docs/prior.md', 'line': 2,
           'url': 'https://github.com/Technoetic/semantic-crosscheck/blob/' + 'c' * 40 + '/docs/prior.md#L2',
           'excerpt': 'Prior independent use.'}
    source = {'id': 'github:example/prior', 'kind': 'project', 'title': 'Prior project',
              'url': 'https://github.com/example/prior', 'year': None,
              'keys': ['github:example/prior'], 'aliases': ['Earlier name'], 'tags': ['preserved'],
              'note': 'Preserve this exact note.',
              'uses': [{'plugin': 'agentic-vault', 'role': 'background', 'evidence': [av]},
                       {'plugin': 'semantic-crosscheck', 'role': 'reference', 'evidence': [sxc]}]}
    registry = {'schemaVersion': 1, 'updatedAt': 'before', 'sources': [source], 'snapshots': {
        'agentic-vault': {'version': 'v0.48.0', 'commit': OLD},
        'semantic-crosscheck': {'version': 'v0.24.0', 'commit': 'c' * 40}}}
    art = {'count': 1, 'assets': [{'sourceId': source['id'], 'prompt': 'Original unique prompt.',
           'sha256': 'image-hash', 'generationEvidenceUrls': [av['url'], sxc['url']],
           'evidenceUrls': [av['url'], sxc['url']], 'currentEvidenceUrls': [av['url'], sxc['url']]}]}
    texts = {'README.md': ['Inserted line.', av['excerpt']], RELEASE: [
        '# v0.49.0', '[Q00/ouroboros](' + URL + ') v0.60.0',
        '| Task provenance | [ledger](' + URL + '/blob/54dad8e1dd93aee31858bde72493cd7a0f938739/ledger.py) |',
        '| Evaluation | [models](' + URL + '/blob/54dad8e1dd93aee31858bde72493cd7a0f938739/models.py) |',
        '| Stop rules | [convergence](' + URL + '/blob/54dad8e1dd93aee31858bde72493cd7a0f938739/convergence.py) |',
        'Upstream is [MIT](' + URL + '/blob/54dad8e1dd93aee31858bde72493cd7a0f938739/LICENSE).'],
        'tests/test_task_workflow_release.py': ['self.assertIn("' + URL + '", release)']}
    return registry, art, texts


class AV049ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'v0.49.0 Atlas updater is missing')
        self.base = mock.patch.object(updater, 'BASE', {'total': 1, 'citations': 2, 'av': 1})
        self.base.start()
        self.addCleanup(self.base.stop)

    def prepare(self, registry, art, texts, commit=NEW, tag='v0.49.0'):
        def index(url):
            return {file: updater.naming_lines('github:q00/ouroboros', lines)
                    for file, lines in texts.items()
                    if updater.naming_lines('github:q00/ouroboros', lines)}
        return updater.prepare_update(registry, art, texts.__getitem__, commit, tag,
                                      url_index=index, updated_at='fixed')

    def test_repins_prior_citations_and_preserves_metadata_sxc_and_image_provenance(self):
        registry, art, texts = fixture()
        before = copy.deepcopy((registry, art))
        revised, images, summary = self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        prior = copy.deepcopy(revised['sources'][0])
        prior['uses'][0]['evidence'] = registry['sources'][0]['uses'][0]['evidence']
        self.assertEqual(prior, registry['sources'][0])
        self.assertEqual(revised['snapshots']['semantic-crosscheck'], registry['snapshots']['semantic-crosscheck'])
        self.assertEqual(revised['sources'][0]['uses'][0]['evidence'][0]['line'], 2)
        self.assertIn('/' + NEW + '/', revised['sources'][0]['uses'][0]['evidence'][0]['url'])
        self.assertEqual(images['count'], art['count'])
        self.assertEqual(images['assets'][0]['generationEvidenceUrls'], art['assets'][0]['generationEvidenceUrls'])
        self.assertEqual(images['assets'][0]['prompt'], art['assets'][0]['prompt'])
        self.assertEqual(images['assets'][0]['sha256'], art['assets'][0]['sha256'])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'][1], art['assets'][0]['currentEvidenceUrls'][1])
        source = revised['sources'][-1]
        self.assertEqual((source['id'], source['kind'], source['title']),
                         ('github:q00/ouroboros', 'project', 'Ouroboros'))
        self.assertEqual(source['aliases'], ['Q00/ouroboros', 'Ouroboros'])
        self.assertEqual(source['uses'][0]['role'], 'reference')
        self.assertEqual([row['line'] for row in source['uses'][0]['evidence']], [2, 3, 4, 5, 6])
        for row in source['uses'][0]['evidence']:
            self.assertEqual(row['excerpt'], texts[RELEASE][row['line'] - 1].strip()[:220])
        self.assertEqual(summary['newCitationRows'], 5)
        self.assertEqual(summary['testLinesNotCited'], ['tests/test_task_workflow_release.py#L1'])
        self.assertEqual(summary['uncommissionedSourceIds'], ['github:q00/ouroboros'])
        self.assertFalse(any(asset['sourceId'] == source['id'] for asset in images['assets']))

    def test_second_run_is_idempotent_and_cannot_rewrite_new_record(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        twice, images2, summary = self.prepare(once, images, texts)
        self.assertEqual((once, images), (twice, images2))
        self.assertEqual(summary['addedSourceIds'], [])
        once['sources'][-1]['note'] = 'Changed note.'
        with self.assertRaises(ValueError):
            self.prepare(once, images, texts)

    def test_sha_tag_and_excerpt_mismatch_are_refused(self):
        for commit, tag in [('B' * 40, 'v0.49.0'), ('a' * 39, 'v0.49.0'),
                            (NEW, 'v0.48.0'), (NEW, '../v0.49.0')]:
            with self.subTest(commit=commit, tag=tag), self.assertRaises(ValueError):
                self.prepare(*fixture(), commit=commit, tag=tag)
        registry, art, texts = fixture()
        texts['README.md'] = ['Changed prior excerpt.']
        with self.assertRaisesRegex(ValueError, 'cannot be repinned'):
            self.prepare(registry, art, texts)

    def test_missing_repeated_or_uncatalogued_reference_lines_need_review(self):
        for change in ('missing', 'duplicate_excerpt', 'other_document'):
            registry, art, texts = fixture()
            if change == 'missing':
                texts[RELEASE] = ['No references.']
            elif change == 'duplicate_excerpt':
                texts[RELEASE].append(texts[RELEASE][1])
            else:
                texts['docs/other.md'] = ['Additional reference ' + URL]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.prepare(registry, art, texts)

    def test_cli_rejects_apply_without_public_verification_and_stand_in_apply(self):
        for extra in (['--apply'], ['--stand-in', '--apply', '--public-verified'],
                      ['--stand-in', '--apply'], ['--tag', 'v0.48.0']):
            argv = ['--plugin-root', '.', '--commit', NEW, '--tag', 'v0.49.0', *extra]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                updater.main(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_actual_local_tag_must_be_annotated_and_match_exact_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            def git(*parts):
                return subprocess.check_output(['git', '-C', str(root), *parts], env=env,
                                               stderr=subprocess.DEVNULL).decode().strip()
            git('init', '--quiet')
            (root / 'file.txt').write_text('fixture', encoding='utf-8')
            git('add', 'file.txt')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org',
                'commit', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                updater.verify_tag(root, commit, 'v0.49.0')
            git('tag', 'v0.49.0')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, commit, 'v0.49.0')
            git('tag', '-d', 'v0.49.0')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org',
                'tag', '-a', 'v0.49.0', '-m', 'fixture release')
            updater.verify_tag(root, commit, 'v0.49.0')
            (root / 'file.txt').write_text('changed fixture', encoding='utf-8')
            git('add', 'file.txt')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org',
                'commit', '--quiet', '-m', 'second fixture')
            newer = git('rev-parse', 'HEAD')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, newer, 'v0.49.0')


if __name__ == '__main__':
    unittest.main()
