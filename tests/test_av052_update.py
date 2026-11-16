import copy
import importlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    updater = importlib.import_module('update_av052_references')
except ModuleNotFoundError:
    updater = None
# The release's own tuples, read before setUp patches the expectation for the small fixture.
REAL_TUPLES = (updater.PRIOR_TUPLE, updater.EXPECTED_TUPLE) if updater else None

OLD, NEW = 'a' * 40, 'b' * 40
PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'
RELEASE = 'docs/releases/v0.52.0.md'
SECURITY = 'SECURITY.md'
INTEGRITY = 'docs/release-integrity.md'
COPY = 'antigravity/docs/release-integrity.md'
METADATA_TEST = 'tests/test_release_metadata.py'
SPOTLIGHTING = 'https://arxiv.org/abs/2403.14720'
ATTACKER = 'https://arxiv.org/abs/2510.09023'
DIVERGENCE = 'https://docs.jj-vcs.dev/latest/guides/divergence/'
JURY = 'https://arxiv.org/abs/2607.10139'
CASCADING = 'https://arxiv.org/abs/2407.02348'
SLSA = 'https://slsa.dev/spec/v1.2/source-requirements'
REPORTING = ('https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/'
             'configure-vulnerability-reporting/configure-for-a-repository')
RULESETS = 'https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/'
ABOUT = RULESETS + 'about-rulesets'
AVAILABLE = RULESETS + 'available-rules-for-rulesets'
URLS = (SPOTLIGHTING, ATTACKER, DIVERGENCE, JURY, CASCADING, SLSA, REPORTING, ABOUT, AVAILABLE)
IDS = ['arxiv:2403.14720', 'arxiv:2510.09023', 'url:https://docs.jj-vcs.dev/latest/guides/divergence',
       'arxiv:2607.10139', 'arxiv:2407.02348', 'url:https://slsa.dev/spec/v1.2/source-requirements',
       'url:' + REPORTING, 'url:' + ABOUT, 'url:' + AVAILABLE]
KINDS = ['paper', 'paper', 'article', 'paper', 'paper', 'article', 'article', 'article', 'article']
ROLES = ['reference', 'reference', 'reference', 'reference', 'background', 'reference', 'reference', 'reference',
         'reference']
YEARS = [2024, 2025, None, 2026, 2024, None, None, None, None]
# The fixture's release table starts at line 4; docs/release-integrity.md names SLSA twice (lines 2 and 5).
ROWS = [[(RELEASE, 4)], [(RELEASE, 5), (SECURITY, 2)], [(RELEASE, 6)], [(RELEASE, 7)], [(RELEASE, 8)],
        [(RELEASE, 9), (INTEGRITY, 2), (INTEGRITY, 5)], [(RELEASE, 10), (INTEGRITY, 4)],
        [(RELEASE, 11), (INTEGRITY, 3)], [(RELEASE, 11), (INTEGRITY, 3)]]
PRIVATE = r'(?i)(?<![A-Za-z])[a-z]:[\\/]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|op_u_[A-Za-z0-9]+|sk-[A-Za-z0-9]{16,}'


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
        'agentic-vault': {'version': 'v0.51.0', 'commit': OLD},
        'semantic-crosscheck': {'version': 'v0.27.0', 'commit': 'c' * 40}}}
    art = {'count': 1, 'assets': [{'sourceId': source['id'], 'prompt': 'Original unique prompt.',
           'sha256': 'image-hash', 'generationEvidenceUrls': [av['url'], sxc['url']],
           'evidenceUrls': [av['url'], sxc['url']], 'currentEvidenceUrls': [av['url'], sxc['url']]}]}
    integrity = ['# 릴리스 무결성',
                 '- **SLSA Source 트랙:** [SLSA v1.2 Source 요구사항](' + SLSA + ')은 태그 이동·삭제 금지를 요구한다.',
                 '- [About rulesets](' + ABOUT + ')·[Available rules for rulesets](' + AVAILABLE + '):',
                 '- [Configuring private vulnerability reporting for a repository](' + REPORTING + '):',
                 '- [SLSA v1.2 Source requirements](' + SLSA + '): 태그 이동·삭제 금지(L2부터)']
    texts = {'README.md': ['Inserted line.', av['excerpt']],
             RELEASE: ['# v0.52.0', '| 출처 | 준 것 | 이번 적용 |', '|---|---|---|',
                       '| [Spotlighting](' + SPOTLIGHTING + ')(2024) | delimiting | 2번 |',
                       '| [The Attacker Moves Second](' + ATTACKER + ')(2025) | adaptive | 2번 |',
                       '| [Jujutsu: Divergent changes](' + DIVERGENCE + ') | divergent | 1번 |',
                       '| [LLMs as a Jury](' + JURY + ')(2026, 부록 I) | agreement | 3번 |',
                       '| [Agreement-Based Cascading](' + CASCADING + ')(2024) | cascade | 3번 |',
                       '| [SLSA v1.2 Source requirements](' + SLSA + ') | tags | 4번 |',
                       '| [GitHub Docs: private vulnerability reporting](' + REPORTING + ') | form | 4번 |',
                       '| [GitHub Docs: About rulesets](' + ABOUT + ') · [Available rules](' + AVAILABLE + ') | rules | 4번 |'],
             SECURITY: ['# Security', '  defences they tested ([The Attacker Moves Second](' + ATTACKER + ')).'],
             INTEGRITY: integrity,
             COPY: list(integrity),
             METADATA_TEST: ['    SOURCES = ('] + ['        "' + url + '",' for url in URLS]}
    return registry, art, texts


class AV052ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'v0.52.0 Atlas updater is missing')
        patches = [mock.patch.object(updater, 'BASE', {'total': 1, 'citations': 2, 'av': 1}),
                   mock.patch.object(updater, 'EXPECTED_TUPLE', (4, 1, 5, 10, 17))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def prepare(self, registry, art, texts, commit=NEW, tag='v0.52.0'):
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
        self.assertEqual(revised['snapshots']['agentic-vault'],
                         {'name': 'Agentic Vault', 'version': 'v0.52.0', 'commit': NEW,
                          'url': 'https://github.com/Technoetic/agentic-vault/tree/' + NEW})
        self.assertEqual(revised['updatedAt'], 'fixed')
        row = revised['sources'][0]['uses'][0]['evidence'][0]
        self.assertEqual((row['line'], row['url']), (2, PREFIX + NEW + '/README.md#L2'))
        self.assertEqual(images['count'], art['count'])
        for field in ('generationEvidenceUrls', 'prompt', 'sha256'):
            self.assertEqual(images['assets'][0][field], art['assets'][0][field])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'],
                         [PREFIX + NEW + '/README.md#L2', art['assets'][0]['currentEvidenceUrls'][1]])
        self.assertEqual(images['assets'][0]['evidenceUrls'], images['assets'][0]['currentEvidenceUrls'])
        added = revised['sources'][1:]
        self.assertEqual([source['id'] for source in added], IDS)
        self.assertEqual([source['url'] for source in added], list(URLS))
        self.assertEqual([source['kind'] for source in added], KINDS)
        self.assertEqual([source['year'] for source in added], YEARS)
        self.assertEqual([source['uses'][0]['role'] for source in added], ROLES)
        for source in added:
            self.assertEqual(source['keys'], [source['id']])
            self.assertEqual(source['tags'], [])
            self.assertEqual([use['plugin'] for use in source['uses']], ['agentic-vault'])
            self.assertTrue(source['note'].startswith(updater.FIRST))
            self.assertTrue(source['note'].endswith(updater.NO_CLAIM))
            self.assertIn('not copied code', source['note'])
        self.assertEqual(summary['addedSourceIds'], IDS)
        self.assertEqual(summary['newCitationRows'], 15)
        self.assertEqual(summary['priorAgenticVaultCitationsRepinned'], 1)
        self.assertEqual(summary['remappedLines'], 1)
        self.assertEqual(summary['agenticVaultRows'], 16)
        self.assertEqual(summary['coverageTuple'], [4, 1, 5, 10, 17])
        self.assertEqual(summary['uncommissionedSourceIds'], IDS)
        self.assertFalse(set(IDS) & {asset['sourceId'] for asset in images['assets']})

    def test_each_source_cites_every_non_test_line_that_names_it(self):
        registry, art, texts = fixture()
        revised, _, summary = self.prepare(registry, art, texts)
        for source, expected in zip(revised['sources'][1:], ROWS):
            rows = source['uses'][0]['evidence']
            with self.subTest(source=source['id']):
                self.assertEqual([(row['file'], row['line']) for row in rows], expected)
                for row in rows:
                    self.assertEqual(row['url'], f"{PREFIX}{NEW}/{row['file']}#L{row['line']}")
                    self.assertEqual(row['excerpt'], texts[row['file']][row['line'] - 1].strip()[:220])
        self.assertEqual(summary['rowsPerNewSource'], dict(zip(IDS, [len(rows) for rows in ROWS])))
        self.assertEqual(summary['citedAddressLines'][SLSA],
                         [INTEGRITY + '#L2', INTEGRITY + '#L5', RELEASE + '#L9'])
        # The generated package copies its source document line for line: reported, not cited.
        self.assertEqual(summary['generatedCopyLines'][SLSA], [COPY + '#L2', COPY + '#L5'])
        self.assertEqual(summary['generatedCopyLines'][ABOUT], [COPY + '#L3'])
        self.assertEqual(summary['generatedCopyLines'][SPOTLIGHTING], [])
        self.assertEqual(summary['testLinesNotCited'][ATTACKER], [METADATA_TEST + '#L3'])
        self.assertEqual(summary['testLinesNotCited'][AVAILABLE], [METADATA_TEST + '#L10'])

    def test_second_run_is_idempotent_and_cannot_rewrite_a_new_record(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        twice, images2, summary = self.prepare(once, images, texts)
        self.assertEqual((once, images), (twice, images2))
        self.assertEqual((summary['addedSourceIds'], summary['remappedLines']), ([], 0))
        self.assertEqual(summary['priorAgenticVaultCitationsRepinned'], 1)
        once['sources'][-1]['note'] = 'Changed note.'
        with self.assertRaisesRegex(ValueError, 'manual review'):
            self.prepare(once, images, texts)

    def test_partial_snapshot_known_source_and_existing_identity_need_review(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        partial = copy.deepcopy(once)
        partial['sources'].pop()
        with self.assertRaises(ValueError):
            self.prepare(partial, images, texts)
        # A new address that another record already holds needs a reviewed merge, not a second card.
        for identity in (IDS[1], IDS[5]):
            registry, art, texts = fixture()
            registry['sources'][0]['keys'].append(identity)
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, 'reviewed merge'):
                self.prepare(registry, art, texts)
        # A v0.51.0 baseline that already holds one of the new cards is not the published baseline.
        registry, art, texts = fixture()
        known = copy.deepcopy(once['sources'][1])
        known['uses'][0]['evidence'][0]['url'] = PREFIX + OLD + '/' + RELEASE + '#L4'
        registry['sources'].append(known)
        with self.assertRaisesRegex(ValueError, 'baseline'):
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
                    ValueError, 'Uncommissioned v0.52.0 sources must use text fallback'):
                self.prepare(registry, art, texts)
            self.assertEqual((registry, art), before)

    def test_sha_tag_and_excerpt_mismatch_are_refused(self):
        for commit, tag in [('B' * 40, 'v0.52.0'), ('a' * 39, 'v0.52.0'),
                            (NEW, 'v0.51.0'), (NEW, '../v0.52.0')]:
            with self.subTest(commit=commit, tag=tag), self.assertRaises(ValueError):
                self.prepare(*fixture(), commit=commit, tag=tag)
        registry, art, texts = fixture()
        texts['README.md'] = ['Changed prior excerpt.']
        with self.assertRaisesRegex(ValueError, 'cannot be repinned'):
            self.prepare(registry, art, texts)
        registry, art, texts = fixture()
        registry['snapshots']['semantic-crosscheck']['version'] = 'v0.26.0'
        with self.assertRaisesRegex(ValueError, 'semantic-crosscheck'):
            self.prepare(registry, art, texts)

    def test_missing_repeated_or_uncatalogued_reference_lines_need_review(self):
        for change in ('missing_release', 'duplicate_line', 'other_document', 'missing_security',
                       'second_security_line', 'changed_copy', 'missing_integrity_line'):
            registry, art, texts = fixture()
            if change == 'missing_release':
                texts[RELEASE] = ['No references.']
            elif change == 'duplicate_line':
                texts[RELEASE].append(texts[RELEASE][4])
            elif change == 'other_document':
                texts['docs/other.md'] = ['Additional reference ' + SLSA.removeprefix('https://')]
            elif change == 'missing_security':
                del texts[SECURITY]
            elif change == 'second_security_line':
                texts[SECURITY].append('See also https://arxiv.org/abs/2510.09023v2 for the attack.')
            elif change == 'changed_copy':
                texts[COPY][2] = texts[COPY][2] + ' (changed in the package)'
            else:
                texts[INTEGRITY] = [line for line in texts[INTEGRITY] if 'Source requirements]' not in line]
                texts[COPY] = list(texts[INTEGRITY])
            with self.subTest(change=change), self.assertRaises((ValueError, LookupError)):
                self.prepare(registry, art, texts)

    def test_release_table_constants_are_consistent(self):
        self.assertEqual(updater.NEW_IDS, IDS)
        self.assertEqual([row[3] for row in updater.REFERENCES], list(URLS))
        self.assertEqual([row[1] for row in updater.REFERENCES], KINDS)
        self.assertEqual([row[6] for row in updater.REFERENCES], ROLES)
        self.assertEqual([len(row[8]) for row in updater.REFERENCES], [len(rows) for rows in ROWS])
        self.assertEqual(updater.NEW_CITATIONS, 15)
        self.assertEqual([row[8][0][0] for row in updater.REFERENCES], [RELEASE] * len(IDS))
        for row in updater.REFERENCES:
            self.assertEqual(updater.canonical_key(row[3])['key'], row[0])
            self.assertIsNone(re.search(PRIVATE, row[7]), row[0])
            self.assertNotIn(row[2], row[5])
        papers = sum(kind == 'paper' for kind in KINDS)
        articles = sum(kind == 'article' for kind in KINDS)
        prior, expected = REAL_TUPLES
        self.assertEqual((prior, expected), ((56, 57, 24, 180, 328), (60, 57, 29, 189, 343)))
        self.assertEqual(tuple(new - old for old, new in zip(prior, expected)),
                         (papers, 0, articles, len(IDS), updater.NEW_CITATIONS))

    def test_test_edits_apply_once_and_keep_the_earlier_lines(self):
        texts = {file: (ROOT / file).read_text(encoding='utf-8') for file in updater.TEST_FILES}
        once, _ = updater.edit_tests(texts)
        twice, applied = updater.edit_tests(once)
        self.assertEqual((twice, applied), (once, 0))
        delivery = once['tests/test_delivery.py']
        self.assertIn("    ('v0.51.0','v0.27.0'):(56,57,24,180,328),\n"
                      "    ('v0.52.0','v0.27.0'):(60,57,29,189,343),\n", delivery)
        self.assertEqual(delivery.count('def test_v052_coverage'), 1)
        self.assertEqual(delivery.count('def test_v051_coverage'), 1)
        self.assertIn('(4,0,5,9,15)', delivery)
        artwork = once['tests/artwork-uniqueness.test.mjs']
        for identity, kind in zip(IDS, KINDS):
            self.assertEqual(artwork.count(f"['{identity}','{kind}']"), 1)
        self.assertIn('    if(declaredAv052TextFallback(source)) continue;\n', artwork)
        self.assertEqual(artwork.count("test('only the declared agentic-vault v0.52.0 sources"), 1)
        self.assertIn(updater._IMMUTABLE_172, artwork)
        self.assertEqual(artwork.count(updater._FULL_172), 1)
        self.assertIn('assert.deepEqual(record.generationEvidenceUrls.map(pinnedFile),citations.map(pinnedFile));',
                      artwork)
        for file, text in texts.items():
            removed = set(text.split('\n')) - set(once[file].split('\n'))
            with self.subTest(file=file):
                if file == 'tests/test_delivery.py':
                    self.assertEqual(removed, set())
                else:
                    self.assertLessEqual(len(removed), 5)
        with self.assertRaisesRegex(ValueError, 'anchor'):
            updater.edit_tests({**texts, 'tests/test_delivery.py': 'no anchor'})

    def test_cli_rejects_apply_without_public_verification_and_stand_in_apply(self):
        for extra in (['--apply'], ['--stand-in', '--apply', '--public-verified'],
                      ['--stand-in', '--apply'], ['--stand-in', '--public-verified'], ['--tag', 'v0.51.0']):
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
            git('tag', 'v0.52.0')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, commit)
            git('tag', '-d', 'v0.52.0')
            git(*identity, 'tag', '-a', 'v0.52.0', '-m', 'fixture release')
            updater.verify_tag(root, commit)
            (root / 'file.txt').write_text('changed fixture', encoding='utf-8')
            git('add', 'file.txt')
            git(*identity, 'commit', '--quiet', '-m', 'second fixture')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, git('rev-parse', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
