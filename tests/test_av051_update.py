import copy
import importlib
import io
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
    updater = importlib.import_module('update_av051_references')
except ModuleNotFoundError:
    updater = None

OLD, NEW = 'a' * 40, 'b' * 40
PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'
RELEASE = 'docs/releases/v0.51.0.md'
BIZROUTER = 'https://bizrouter.ai/docs/decisions'
DECISION_INDEX = 'https://artificialanalysis.ai/evaluations/decision-index'
URLS = (BIZROUTER, DECISION_INDEX)
IDS = ['url:https://bizrouter.ai/docs/decisions',
       'url:https://artificialanalysis.ai/evaluations/decision-index']


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
        'agentic-vault': {'version': 'v0.50.0', 'commit': OLD},
        'semantic-crosscheck': {'version': 'v0.27.0', 'commit': 'c' * 40}}}
    art = {'count': 1, 'assets': [{'sourceId': source['id'], 'prompt': 'Original unique prompt.',
           'sha256': 'image-hash', 'generationEvidenceUrls': [av['url'], sxc['url']],
           'evidenceUrls': [av['url'], sxc['url']], 'currentEvidenceUrls': [av['url'], sxc['url']]}]}
    texts = {'README.md': ['Inserted line.', av['excerpt']],
             RELEASE: ['# v0.51.0', '| 출처 | 준 것 | 이번 적용 |', '|---|---|---|',
                       '| [BizRouter Decisions API 문서](' + BIZROUTER + ') | API | opt-in |',
                       '| [Google Gemini Decision 1 공개 벤치마크 색인](' + DECISION_INDEX + ') | index | context |'],
             'tests/test_release_metadata.py': ['    SOURCES = ('] + ['        "' + url + '",' for url in URLS]}
    return registry, art, texts


class AV051ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'v0.51.0 Atlas updater is missing')
        patches = [mock.patch.object(updater, 'BASE', {'total': 1, 'citations': 2, 'av': 1}),
                   mock.patch.object(updater, 'EXPECTED_TUPLE', (0, 1, 2, 3, 4))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def prepare(self, registry, art, texts, commit=NEW, tag='v0.51.0'):
        def index(url):
            identity = updater.canonical_key(url)['key']
            return {file: updater.naming_lines(identity, lines) for file, lines in texts.items()
                    if updater.naming_lines(identity, lines)}

        def read(file):
            if file not in texts:
                raise LookupError(file)
            return texts[file]
        return updater.prepare_update(registry, art, read, commit, tag, url_index=index, updated_at='fixed')

    def test_repins_prior_citations_and_preserves_metadata_sxc_and_image_provenance(self):
        registry, art, texts = fixture()
        before = copy.deepcopy((registry, art))
        revised, images, summary = self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        prior = copy.deepcopy(revised['sources'][0])
        prior['uses'][0]['evidence'] = registry['sources'][0]['uses'][0]['evidence']
        self.assertEqual(prior, registry['sources'][0])
        self.assertEqual(revised['snapshots']['semantic-crosscheck'], registry['snapshots']['semantic-crosscheck'])
        self.assertEqual(revised['snapshots']['agentic-vault']['version'], 'v0.51.0')
        self.assertEqual(revised['snapshots']['agentic-vault']['commit'], NEW)
        row = revised['sources'][0]['uses'][0]['evidence'][0]
        self.assertEqual((row['line'], row['url']), (2, PREFIX + NEW + '/README.md#L2'))
        self.assertEqual(images['count'], art['count'])
        for field in ('generationEvidenceUrls', 'prompt', 'sha256'):
            self.assertEqual(images['assets'][0][field], art['assets'][0][field])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'],
                         [PREFIX + NEW + '/README.md#L2', art['assets'][0]['currentEvidenceUrls'][1]])
        added = revised['sources'][1:]
        self.assertEqual([source['id'] for source in added], IDS)
        self.assertEqual([source['url'] for source in added], list(URLS))
        self.assertEqual({source['kind'] for source in added}, {'article'})
        self.assertEqual([source['uses'][0]['role'] for source in added], ['reference', 'background'])
        self.assertEqual([source['year'] for source in added], [None, None])
        for number, source in enumerate(added, start=4):
            rows = source['uses'][0]['evidence']
            self.assertEqual([(row['file'], row['line']) for row in rows], [(RELEASE, number)])
            for row in rows:
                self.assertEqual(row['url'], f"{PREFIX}{NEW}/{row['file']}#L{row['line']}")
                self.assertEqual(row['excerpt'], texts[row['file']][row['line'] - 1].strip()[:220])
            self.assertIn('not copied code', source['note'])
        self.assertEqual(summary['addedSourceIds'], IDS)
        self.assertEqual(summary['newCitationRows'], 2)
        self.assertEqual(summary['priorAgenticVaultCitationsRepinned'], 1)
        self.assertEqual(summary['remappedLines'], 1)
        self.assertEqual(summary['testLinesNotCited'][BIZROUTER], ['tests/test_release_metadata.py#L2'])
        self.assertEqual(summary['uncommissionedSourceIds'], IDS)
        self.assertFalse(set(IDS) & {asset['sourceId'] for asset in images['assets']})

    def test_second_run_is_idempotent_and_cannot_rewrite_a_new_record(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        twice, images2, summary = self.prepare(once, images, texts)
        self.assertEqual((once, images), (twice, images2))
        self.assertEqual((summary['addedSourceIds'], summary['remappedLines']), ([], 0))
        self.assertEqual(summary['priorAgenticVaultCitationsRepinned'], 1)
        once['sources'][-1]['note'] = 'Changed note.'
        with self.assertRaises(ValueError):
            self.prepare(once, images, texts)

    def test_partial_snapshot_and_existing_identity_need_review(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        partial = copy.deepcopy(once)
        partial['sources'].pop()
        with self.assertRaises(ValueError):
            self.prepare(partial, images, texts)
        registry, art, texts = fixture()
        registry['sources'][0]['keys'].append(IDS[1])
        with self.assertRaisesRegex(ValueError, 'reviewed merge'):
            self.prepare(registry, art, texts)

    def test_artwork_for_a_new_source_is_refused(self):
        for identity in IDS:
            registry, art, texts = fixture()
            later = copy.deepcopy(art['assets'][0])
            later['sourceId'] = identity
            art['assets'].append(later)
            art['count'] = len(art['assets'])
            before = copy.deepcopy((registry, art))
            with self.subTest(identity=identity), self.assertRaisesRegex(
                    ValueError, 'Uncommissioned v0.51.0 sources must use text fallback'):
                self.prepare(registry, art, texts)
            self.assertEqual((registry, art), before)

    def test_sha_tag_and_excerpt_mismatch_are_refused(self):
        for commit, tag in [('B' * 40, 'v0.51.0'), ('a' * 39, 'v0.51.0'),
                            (NEW, 'v0.50.0'), (NEW, '../v0.51.0')]:
            with self.subTest(commit=commit, tag=tag), self.assertRaises(ValueError):
                self.prepare(*fixture(), commit=commit, tag=tag)
        registry, art, texts = fixture()
        texts['README.md'] = ['Changed prior excerpt.']
        with self.assertRaisesRegex(ValueError, 'cannot be repinned'):
            self.prepare(registry, art, texts)

    def test_missing_repeated_or_uncatalogued_reference_lines_need_review(self):
        for change in ('missing_release', 'duplicate_line', 'other_document'):
            registry, art, texts = fixture()
            if change == 'missing_release':
                texts[RELEASE] = ['No references.']
            elif change == 'duplicate_line':
                texts[RELEASE].append(texts[RELEASE][3])
            else:
                texts['docs/other.md'] = ['Additional reference ' + DECISION_INDEX]
            with self.subTest(change=change), self.assertRaises((ValueError, LookupError)):
                self.prepare(registry, art, texts)

    def test_test_edits_apply_once_and_keep_the_earlier_lines(self):
        texts = {file: (ROOT / file).read_text(encoding='utf-8') for file in updater.TEST_FILES}
        # Replay the historical reference migration before its later artwork commission.
        # Fixture copied exactly from commit 7b572a4 (172 commissioned sources).
        texts['tests/artwork-uniqueness.test.mjs'] = (
            ROOT / 'tests/fixtures/artwork-v050-before-v051.mjs.txt'
        ).read_text(encoding='utf-8')
        once, applied = updater.edit_tests(texts)
        self.assertGreater(applied, 0)
        twice, applied = updater.edit_tests(once)
        self.assertEqual((twice, applied), (once, 0))
        delivery = once['tests/test_delivery.py']
        self.assertIn("    ('v0.50.0','v0.27.0'):(56,57,22,178,326),\n"
                      "    ('v0.51.0','v0.27.0'):(56,57,24,180,328),\n", delivery)
        self.assertEqual(delivery.count('def test_v051_coverage'), 1)
        self.assertIn('(0,0,2,2,2)', delivery)
        artwork = once['tests/artwork-uniqueness.test.mjs']
        for identity in IDS:
            self.assertEqual(artwork.count(f"'{identity}'"), 1)
        self.assertIn('if(declaredAnyTextFallback(source)) continue;', artwork)
        with self.assertRaisesRegex(ValueError, 'anchor'):
            updater.edit_tests({**texts, 'tests/test_delivery.py': 'no anchor'})

    def test_cli_rejects_apply_without_public_verification_and_stand_in_apply(self):
        for extra in (['--apply'], ['--stand-in', '--apply', '--public-verified'],
                      ['--stand-in', '--apply'], ['--stand-in', '--public-verified'], ['--tag', 'v0.50.0']):
            argv = ['--plugin-root', '.', '--commit', NEW, *extra]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                updater.main(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_actual_local_tag_must_be_annotated_and_match_exact_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            identity = ('-c', 'user.name=Fixture', '-c', 'user.email=')

            def git(*parts):
                return subprocess.check_output(['git', '-C', str(root), *parts], env=env,
                                               stderr=subprocess.DEVNULL).decode().strip()
            git('init', '--quiet')
            (root / 'file.txt').write_text('fixture', encoding='utf-8')
            git('add', 'file.txt')
            git(*identity, 'commit', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                updater.verify_tag(root, commit)
            git('tag', 'v0.51.0')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, commit)
            git('tag', '-d', 'v0.51.0')
            git(*identity, 'tag', '-a', 'v0.51.0', '-m', 'fixture release')
            updater.verify_tag(root, commit)
            (root / 'file.txt').write_text('changed fixture', encoding='utf-8')
            git('add', 'file.txt')
            git(*identity, 'commit', '--quiet', '-m', 'second fixture')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, git('rev-parse', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
