import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    updater = importlib.import_module('update_sxc027_references')
except ModuleNotFoundError:
    updater = None

OLD, NEW, AV = 'a' * 40, 'b' * 40, 'c' * 40
PREFIX = 'https://github.com/Technoetic/semantic-crosscheck/blob/'
AV_PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'
RELEASE = 'docs/releases/v0.27.0.md'
README = 'README.md'
README_TEST = 'tests/test_docs_readme.py'
THREAD = 'https://www.postgresql.org/list/pgsql-hackers/since/202607270000/'
PEP = 'https://peps.python.org/pep-0664/'
POSTGRES = 'https://www.postgresql.org/support/versioning/'
ADOPTIUM = 'https://adoptium.net/support/'
NODE = 'https://github.com/nodejs/Release'
DIATAXIS = 'https://diataxis.fr/'
URLS = (THREAD, PEP, POSTGRES, ADOPTIUM, NODE, DIATAXIS)
IDS = ['url:https://www.postgresql.org/list/pgsql-hackers/since/202607270000',
       'url:https://peps.python.org/pep-0664',
       'url:https://www.postgresql.org/support/versioning',
       'url:https://adoptium.net/support',
       'github:nodejs/release',
       'url:https://diataxis.fr/']
# Exact copies of the two tracked tests at a3fb1d0, before this update's edits.
DELIVERY_FIXTURE = ROOT / 'tests/fixtures/delivery-v050-before-sxc027.py.txt'
ARTWORK_FIXTURE = ROOT / 'tests/fixtures/artwork-v050-before-sxc027.mjs.txt'


def fixture():
    av = {'file': 'README.md', 'line': 1, 'url': AV_PREFIX + AV + '/README.md#L1',
          'excerpt': 'Agentic-vault use stays pinned.'}
    sxc = {'file': 'THIRD_PARTY.md', 'line': 2, 'url': PREFIX + OLD + '/THIRD_PARTY.md#L2',
           'excerpt': 'Prior independent use.'}
    source = {'id': 'github:example/prior', 'kind': 'project', 'title': 'Prior project',
              'url': 'https://github.com/example/prior', 'year': None,
              'keys': ['github:example/prior'], 'aliases': ['Earlier name'], 'tags': ['preserved'],
              'note': 'Preserve this exact note.',
              'uses': [{'plugin': 'agentic-vault', 'role': 'background', 'evidence': [av]},
                       {'plugin': 'semantic-crosscheck', 'role': 'reference', 'evidence': [sxc]}]}
    registry = {'schemaVersion': 1, 'updatedAt': 'before', 'sources': [source], 'snapshots': {
        'agentic-vault': {'name': 'Agentic Vault', 'version': 'v0.50.0', 'commit': AV},
        'semantic-crosscheck': {'name': 'Semantic Crosscheck', 'version': 'v0.24.0', 'commit': OLD}}}
    art = {'count': 1, 'assets': [{'sourceId': source['id'], 'prompt': 'Original unique prompt.',
           'sha256': 'image-hash', 'generationEvidenceUrls': [av['url'], sxc['url']],
           'evidenceUrls': [av['url'], sxc['url']], 'currentEvidenceUrls': [av['url'], sxc['url']]}]}
    texts = {'THIRD_PARTY.md': ['# Third-party notices', 'Inserted line.', sxc['excerpt']],
             README: ['## Requirements', '| Component | Minimum | End of support |', '|---|---|---|',
                      '| Python | 3.11 | 2027-10 · [PEP 664](' + PEP + ') |',
                      '| PostgreSQL | 17 | 2029-11-08 · [PostgreSQL 버전 정책](' + POSTGRES + ') |',
                      '| Java | 11 | 2027-10 · [Adoptium 지원 일정](' + ADOPTIUM + ') |',
                      '| Node.js | 22 | 2027-04-30 · [Node.js 릴리스 일정](' + NODE + ') |'],
             RELEASE: ['# v0.27.0', '## References', '| Source | Used for |', '|---|---|',
                       '| pgsql-hackers thread "timestamp vs. timestamptz", 2026-07-27 to 2026-07-31 '
                       '([list archive from 2026-07-27](' + THREAD + ')) | The pitfall. |',
                       '| [GitHub Advisory Database](https://github.com/advisories) | Advisories. |',
                       '| [PEP 664](' + PEP + '), [PostgreSQL versioning policy](' + POSTGRES + '), '
                       '[Adoptium support page](' + ADOPTIUM + '), [Node.js release schedule](' + NODE + ') '
                       '| The end-of-support dates. |',
                       '| [Diátaxis](' + DIATAXIS + ") | Separating the README's reference sections. |"],
             README_TEST: ['    ROWS = {"Python": ("2027-10", "' + PEP + '"),',
                           '            "PostgreSQL": ("2029-11-08", "' + POSTGRES + '"),',
                           '            "Java": ("2027-10", "' + ADOPTIUM + '"),',
                           '            "Node.js": ("2027-04-30", "' + NODE + '")}']}
    return registry, art, texts


class SXC027ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'semantic-crosscheck v0.27.0 Atlas updater is missing')
        patches = [mock.patch.object(updater, 'BASE', {'total': 1, 'citations': 2, 'sxc': 1, 'av': 1}),
                   mock.patch.object(updater, 'EXPECTED_TUPLE', (0, 1, 0, 7, 12)),
                   mock.patch.object(updater, 'EXPECTED_SXC', (0, 7, 11, 1))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def prepare(self, registry, art, texts, commit=NEW, tag='v0.27.0'):
        def index(url):
            identity = updater.canonical_key(url)['key']
            return {file: updater.naming_lines(identity, lines) for file, lines in texts.items()
                    if updater.naming_lines(identity, lines)}

        def read(file):
            if file not in texts:
                raise LookupError(file)
            return texts[file]
        return updater.prepare_update(registry, art, read, commit, tag, url_index=index, updated_at='fixed')

    def test_repins_prior_rows_and_adds_six_sources_with_exact_rows(self):
        registry, art, texts = fixture()
        before = copy.deepcopy((registry, art))
        revised, images, summary = self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        prior = copy.deepcopy(revised['sources'][0])
        prior['uses'][1]['evidence'] = registry['sources'][0]['uses'][1]['evidence']
        self.assertEqual(prior, registry['sources'][0])
        row = revised['sources'][0]['uses'][1]['evidence'][0]
        self.assertEqual((row['line'], row['url'], row['excerpt']),
                         (3, PREFIX + NEW + '/THIRD_PARTY.md#L3', 'Prior independent use.'))
        self.assertEqual(revised['snapshots']['agentic-vault'], registry['snapshots']['agentic-vault'])
        self.assertEqual(revised['snapshots']['semantic-crosscheck'],
                         {'name': 'Semantic Crosscheck', 'version': 'v0.27.0', 'commit': NEW,
                          'url': 'https://github.com/Technoetic/semantic-crosscheck/tree/' + NEW})
        self.assertEqual(revised['updatedAt'], 'fixed')
        self.assertEqual(images['count'], art['count'])
        for field in ('generationEvidenceUrls', 'prompt', 'sha256'):
            self.assertEqual(images['assets'][0][field], art['assets'][0][field])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'],
                         [art['assets'][0]['currentEvidenceUrls'][0], PREFIX + NEW + '/THIRD_PARTY.md#L3'])
        added = revised['sources'][1:]
        self.assertEqual([source['id'] for source in added], IDS)
        self.assertEqual([source['url'] for source in added], list(URLS))
        self.assertEqual([source['kind'] for source in added],
                         ['article', 'article', 'article', 'article', 'project', 'article'])
        self.assertEqual([source['year'] for source in added], [2026, 2021, None, None, None, None])
        self.assertEqual([source['title'] for source in added],
                         ['timestamp vs. timestamptz comparisons inconsistently ordered under DST',
                          'PEP 664 – Python 3.11 Release Schedule', 'PostgreSQL: Versioning Policy',
                          'Temurin™ Support', 'nodejs/Release', 'Diátaxis'])
        self.assertEqual({use['plugin'] for source in added for use in source['uses']}, {'semantic-crosscheck'})
        self.assertEqual({use['role'] for source in added for use in source['uses']}, {'reference'})
        expected_rows = [[(RELEASE, 5)], [(RELEASE, 7), (README, 4)], [(RELEASE, 7), (README, 5)],
                         [(RELEASE, 7), (README, 6)], [(RELEASE, 7), (README, 7)], [(RELEASE, 8)]]
        for source, rows in zip(added, expected_rows):
            evidence = source['uses'][0]['evidence']
            self.assertEqual([(row['file'], row['line']) for row in evidence], rows)
            for row in evidence:
                self.assertEqual(row['url'], f"{PREFIX}{NEW}/{row['file']}#L{row['line']}")
                self.assertEqual(row['excerpt'], texts[row['file']][row['line'] - 1].strip()[:220])
            self.assertIn('not copied code, a runtime dependency or reproduced results', source['note'])
            self.assertTrue(source['note'].startswith('No earlier agentic-vault or semantic-crosscheck use'))
            self.assertNotIn('@', json.dumps(source, ensure_ascii=False))
        self.assertIn('Message-ID', added[0]['note'])
        self.assertEqual(summary['addedSourceIds'], IDS)
        self.assertEqual(summary['newCitationRows'], 10)
        self.assertEqual(summary['priorSemanticCrosscheckCitationsRepinned'], 1)
        self.assertEqual(summary['movedRows'], [{'sourceId': 'github:example/prior', 'file': 'THIRD_PARTY.md',
                                                 'from': 2, 'to': 3}])
        self.assertEqual(summary['testLinesNotCited'][PEP], [README_TEST + '#L1'])
        self.assertEqual(summary['testLinesNotCited'][DIATAXIS], [])
        self.assertEqual(summary['citedAddressLines'][NODE], [README + '#L7', RELEASE + '#L7'])
        self.assertEqual(summary['uncommissionedSourceIds'], IDS)
        self.assertEqual([entry['url'] for entry in summary['notCatalogued']], ['https://github.com/advisories'])
        self.assertFalse(set(IDS) & {asset['sourceId'] for asset in images['assets']})

    def test_rows_that_cannot_be_repinned_are_all_listed_not_guessed(self):
        registry, art, texts = fixture()
        texts['THIRD_PARTY.md'] = ['Changed prior excerpt.']
        with self.assertRaisesRegex(ValueError, r'1 semantic-crosscheck row\(s\) cannot be repinned: '
                                                r'github:example/prior / THIRD_PARTY.md#L2 .*on 0 lines'):
            self.prepare(registry, art, texts)
        texts['THIRD_PARTY.md'] = ['Prior independent use.'] * 2
        with self.assertRaisesRegex(ValueError, 'on 2 lines'):
            self.prepare(registry, art, texts)
        del texts['THIRD_PARTY.md']
        with self.assertRaisesRegex(ValueError, 'absent at the new revision'):
            self.prepare(registry, art, texts)

    def test_every_non_test_line_naming_a_new_source_needs_a_row(self):
        for change in ('other_document', 'schemeless_address', 'missing_release', 'missing_readme',
                       'duplicate_line'):
            registry, art, texts = fixture()
            if change == 'other_document':
                texts['docs/reference/cli.md'] = ['See ' + DIATAXIS + ' for the split.']
            elif change == 'schemeless_address':
                texts['docs/other.md'] = ['Schedule: peps.python.org/pep-0664']
            elif change == 'missing_release':
                texts[RELEASE] = texts[RELEASE][:-1]
            elif change == 'missing_readme':
                texts[README] = texts[README][:-1]
            else:
                texts[README].append(texts[README][3])
            with self.subTest(change=change), self.assertRaises((ValueError, LookupError)):
                self.prepare(registry, art, texts)

    def test_agentic_vault_snapshot_and_rows_stay_unchanged_and_other_versions_are_refused(self):
        registry, art, texts = fixture()
        revised, _, summary = self.prepare(registry, art, texts)
        self.assertEqual(revised['sources'][0]['uses'][0], registry['sources'][0]['uses'][0])
        self.assertEqual(summary['unchangedAgenticVaultSnapshot'], registry['snapshots']['agentic-vault'])
        self.assertEqual(summary['agenticVaultRows'], 1)
        for plugin, version in (('agentic-vault', 'v0.51.0'), ('semantic-crosscheck', 'v0.26.0')):
            registry, art, texts = fixture()
            registry['snapshots'][plugin]['version'] = version
            with self.subTest(plugin=plugin), self.assertRaises(ValueError):
                self.prepare(registry, art, texts)

    def test_second_run_is_idempotent_and_cannot_rewrite_a_new_record(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        twice, images2, summary = self.prepare(once, images, texts)
        self.assertEqual((once, images), (twice, images2))
        self.assertEqual((summary['addedSourceIds'], summary['remappedLines']), ([], 0))
        self.assertEqual(summary['priorSemanticCrosscheckCitationsRepinned'], 1)
        once['sources'][-1]['note'] = 'Changed note.'
        with self.assertRaisesRegex(ValueError, 'manual review'):
            self.prepare(once, images, texts)

    def test_partial_snapshot_and_existing_identity_need_review(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        partial = copy.deepcopy(once)
        partial['sources'].pop()
        with self.assertRaises(ValueError):
            self.prepare(partial, images, texts)
        registry, art, texts = fixture()
        registry['sources'][0]['keys'].append(IDS[4])
        with self.assertRaisesRegex(ValueError, 'reviewed merge'):
            self.prepare(registry, art, texts)

    def test_artwork_for_a_new_source_is_refused(self):
        for identity in IDS:
            registry, art, texts = fixture()
            later = copy.deepcopy(art['assets'][0])
            later['sourceId'] = identity
            art['assets'].append(later)
            art['count'] = len(art['assets'])
            with self.subTest(identity=identity), self.assertRaisesRegex(
                    ValueError, 'Uncommissioned v0.27.0 sources must use text fallback'):
                self.prepare(registry, art, texts)

    def test_no_address_or_message_id_reaches_a_new_record(self):
        registry, art, texts = fixture()
        texts[RELEASE][4] = texts[RELEASE][4].replace('The pitfall.', 'Thread start <id.1@example.org>.')
        with self.assertRaisesRegex(ValueError, 'address, Message-ID'):
            self.prepare(registry, art, texts)

    def test_the_advisory_database_address_has_no_identity_and_stays_uncatalogued(self):
        self.assertIsNone(updater.canonical_key('https://github.com/advisories'))
        registry, art, texts = fixture()
        with mock.patch.object(updater, 'UNCATALOGUED', ({'url': 'https://github.com/github/advisory-database',
                                                           'name': 'x', 'reason': 'y'},)):
            with self.assertRaisesRegex(ValueError, 'now has a catalog identity'):
                self.prepare(registry, art, texts)

    def test_sha_and_tag_mismatch_are_refused(self):
        for commit, tag in [('B' * 40, 'v0.27.0'), ('a' * 39, 'v0.27.0'),
                            (NEW, 'v0.24.0'), (NEW, '../v0.27.0')]:
            with self.subTest(commit=commit, tag=tag), self.assertRaises(ValueError):
                self.prepare(*fixture(), commit=commit, tag=tag)

    def test_test_edits_apply_once_on_the_v050_files_and_keep_the_earlier_lines(self):
        texts = {'tests/test_delivery.py': DELIVERY_FIXTURE.read_text(encoding='utf-8'),
                 'tests/artwork-uniqueness.test.mjs': ARTWORK_FIXTURE.read_text(encoding='utf-8')}
        self.assertEqual(set(texts), set(updater.TEST_FILES))
        once, applied = updater.edit_tests(texts)
        self.assertEqual(applied, len(updater.TEST_EDITS))
        twice, applied = updater.edit_tests(once)
        self.assertEqual((twice, applied), (once, 0))
        delivery = once['tests/test_delivery.py']
        self.assertIn("    ('v0.49.0','v0.24.0'):(56,57,18,168,308),\n"
                      "    ('v0.50.0','v0.24.0'):(56,57,22,172,316),\n"
                      "    ('v0.50.0','v0.27.0'):(56,57,22,178,326),\n", delivery)
        self.assertIn("'v0.24.0':(15,38,66,5),\n                      'v0.27.0':(15,44,76,5)}\n", delivery)
        self.assertEqual(delivery.count('def test_sxc027_coverage'), 1)
        self.assertIn('(0,0,0,6,10)', delivery)
        compile(delivery, 'test_delivery.py', 'exec')
        artwork = once['tests/artwork-uniqueness.test.mjs']
        for identity in IDS:
            self.assertEqual(artwork.count(f"'{identity}'"), 1)
        self.assertIn('if(declaredSxc027TextFallback(source)) continue;', artwork)
        self.assertIn("const published=['v0.24.0','v0.27.0'].includes(", artwork)
        node = shutil.which('node')
        if node:
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'artwork-uniqueness.test.mjs'
                path.write_text(artwork, encoding='utf-8')
                result = subprocess.run([node, '--check', str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaisesRegex(ValueError, 'anchor'):
            updater.edit_tests({**texts, 'tests/test_delivery.py': 'no anchor'})

    def test_cli_rejects_apply_without_public_verification_and_stand_in_apply(self):
        for extra in (['--apply'], ['--stand-in', '--apply', '--public-verified'],
                      ['--stand-in', '--apply'], ['--stand-in', '--public-verified'], ['--tag', 'v0.26.0']):
            argv = ['--plugin-root', '.', '--commit', NEW, *extra]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                updater.main(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_actual_local_tag_must_be_annotated_and_match_exact_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git = _git_runner(root)
            git('init', '--quiet')
            (root / 'file.txt').write_text('fixture', encoding='utf-8')
            git('add', 'file.txt')
            git(*IDENTITY, 'commit', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                updater.verify_tag(root, commit)
            git('tag', 'v0.27.0')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, commit)
            git('tag', '-d', 'v0.27.0')
            git(*IDENTITY, 'tag', '-a', 'v0.27.0', '-m', 'fixture release')
            updater.verify_tag(root, commit)
            (root / 'file.txt').write_text('changed fixture', encoding='utf-8')
            git('add', 'file.txt')
            git(*IDENTITY, 'commit', '--quiet', '-m', 'second fixture')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, git('rev-parse', 'HEAD'))

    def test_cli_dry_run_writes_nothing_and_apply_needs_the_annotated_tag(self):
        registry, art, texts = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            plugin, atlas = Path(temporary) / 'plugin', Path(temporary) / 'atlas'
            plugin.mkdir()
            git = _git_runner(plugin)
            git('init', '--quiet')
            for file, lines in texts.items():
                (plugin / file).parent.mkdir(parents=True, exist_ok=True)
                (plugin / file).write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
            git('add', '.')
            git(*IDENTITY, 'commit', '--quiet', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            image = b'RIFF\x00\x00\x00\x00WEBPfixture'
            art['assets'][0].update(output='media/cards/card-001.webp', bytes=len(image),
                                    sha256=hashlib.sha256(image).hexdigest())
            files = {'data/registry.source.json': json.dumps(registry).encode('utf-8'),
                     'docs/card-artwork-unique-prompts.json': json.dumps(art).encode('utf-8'),
                     'media/cards/card-001.webp': image,
                     'tests/test_delivery.py': DELIVERY_FIXTURE.read_bytes(),
                     'tests/artwork-uniqueness.test.mjs': ARTWORK_FIXTURE.read_bytes()}
            for name, raw in files.items():
                (atlas / name).parent.mkdir(parents=True, exist_ok=True)
                (atlas / name).write_bytes(raw)
            snapshot = lambda: {name: (atlas / name).read_bytes() for name in files}
            base = ['--plugin-root', str(plugin), '--commit', commit, '--atlas-root', str(atlas)]

            def call(*extra):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = updater.main([*base, *extra])
                return code, out.getvalue(), err.getvalue()
            original = snapshot()
            code, out, _ = call('--stand-in')
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertEqual((result['mode'], result['publishable'], result['testEditsApplied']), ('dry-run', False, 9))
            self.assertEqual(result['notCatalogued'][0]['lines'], [RELEASE + '#L6'])
            self.assertEqual(snapshot(), original)
            code, _, err = call('--apply', '--public-verified')
            self.assertEqual((code, json.loads(err)['status']), (1, 'error'))
            self.assertEqual(snapshot(), original)
            git('tag', 'v0.27.0')
            self.assertEqual(call('--apply', '--public-verified')[0], 1)
            self.assertEqual(snapshot(), original)
            git('tag', '-d', 'v0.27.0')
            git(*IDENTITY, 'tag', '-a', 'v0.27.0', '-m', 'fixture release')
            code, out, _ = call('--apply', '--public-verified')
            self.assertEqual((code, json.loads(out)['mode']), (0, 'applied'))
            applied = snapshot()
            for name in ('data/registry.source.json', 'docs/card-artwork-unique-prompts.json',
                         'tests/test_delivery.py', 'tests/artwork-uniqueness.test.mjs'):
                self.assertNotEqual(applied[name], original[name], name)
            self.assertEqual(applied['media/cards/card-001.webp'], image)
            written = json.loads(applied['data/registry.source.json'])
            self.assertEqual(written['snapshots']['semantic-crosscheck']['commit'], commit)
            self.assertEqual([source['id'] for source in written['sources'][1:]], IDS)
            code, out, _ = call('--apply', '--public-verified')
            self.assertEqual((code, json.loads(out)['testEditsApplied']), (0, 0))
            self.assertEqual(snapshot(), applied)


IDENTITY = ('-c', 'user.name=Fixture', '-c', 'user.email=')


def _git_runner(root):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)

    def git(*parts):
        return subprocess.check_output(['git', '-C', str(root), *parts], env=env,
                                       stderr=subprocess.DEVNULL).decode().strip()
    return git


if __name__ == '__main__':
    unittest.main()
