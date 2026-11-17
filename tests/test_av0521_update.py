import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_catalog  # noqa: E402 - the catalog's own builder, after the path line above

try:
    updater = importlib.import_module('update_av0521_references')
except ModuleNotFoundError:
    updater = None
# The release's own constants, read before setUp patches them for the small fixture.
REAL = (updater.AV_ROWS, updater.AV_COVERAGE, updater.PRIOR_COMMIT, updater.REVIEWED_EXCERPTS) if updater else None

OLD, NEW, LATER = 'a' * 40, 'b' * 40, 'e' * 40
PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'
TREE = 'https://github.com/Technoetic/agentic-vault/tree/'
CANDIDATE = 'docs/releases/v0.52.0.md'
RELEASE = 'docs/releases/v0.52.1.md'
INTEGRITY = 'docs/release-integrity.md'
DELIVERY_FILE = 'tests/test_delivery.py'
ARTWORK_FILE = 'tests/artwork-uniqueness.test.mjs'
SPOTLIGHTING = 'https://arxiv.org/abs/2403.14720'
SLSA = 'https://slsa.dev/spec/v1.2/source-requirements'
README_ROW = 'Prior project reference.'
REWORDED = 'Prior project reference, reworded by the release.'
SPOT_ROW = '| [Spotlighting](' + SPOTLIGHTING + ')(2024) | delimiting | 2번 |'
SLSA_ROW = '| [SLSA v1.2 Source requirements](' + SLSA + ') | tags | 4번 |'
INTEGRITY_ROW = '- [SLSA v1.2 Source requirements](' + SLSA + '): 태그 이동·삭제 금지(L2부터)'
IMAGE = b'RIFF fixture image bytes'
DATA_FILES = ['data/catalog.csv', 'data/catalog.json', 'data/registry.source.json',
              'docs/card-artwork-unique-prompts.json']
SMALL = (1, 1, 1, 3, 5)  # coverage of the small fixture: one AV paper, project and article; 3 sources, 5 citations
V052_END = "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(4,0,5,9,15))\n"
MAIN = "\nif __name__=='__main__':unittest.main()\n"
PRIVATE = r'(?i)(?<![A-Za-z])[a-z]:[\\/]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|op_u_[A-Za-z0-9]+|sk-[A-Za-z0-9]{16,}'


PINNED_LINE = ("const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/')"
               ".replace(new RegExp('#L[0-9]+$'),'');\n")
GENERATION_ASSERT = ("    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
                     "    assert.deepEqual(record.generationEvidenceUrls,citations);\n"
                     "    assert.deepEqual(record.delivery.sourceDimensions,[1536,1024]);\n")


def artwork():
    """tests/artwork-uniqueness.test.mjs in miniature, with both anchors of the update."""
    return ("const avCatalogVersion=catalog.snapshots['agentic-vault'].version;\n" + PINNED_LINE +
            "test('older images',()=>{\n"
            "    if(avCatalogVersion==='v0.47.0') assert.deepEqual(record.generationEvidenceUrls,citations);\n"
            "    else assert.deepEqual(record.generationEvidenceUrls.map(pinnedFile),citations.map(pinnedFile));\n"
            "});\n"
            "test('the ten images',()=>{\n"
            "    assert.deepEqual(record.evidenceUrls,citations);\n" + GENERATION_ASSERT + "});\n")


def delivery(other='v0.27.0', coverage=SMALL):
    """A tracked tests/test_delivery.py in miniature: the v0.52.0 coverage line and the v0.52.0 history test last."""
    tup = '(' + ','.join(map(str, coverage)) + ')'
    return ("import unittest\n\nEXPECTED_COVERAGE={\n"
            "    ('v0.51.0','v0.27.0'):(56,57,24,180,328),\n"
            f"    ('v0.52.0','{other}'):{tup},\n"
            "}\n\nclass DeliveryTests(unittest.TestCase):\n"
            "    def test_v052_coverage(self):\n"
            "        prior=EXPECTED_COVERAGE[('v0.51.0','v0.27.0')]\n"
            "        revised=(60,57,29,189,343)\n" + V052_END + MAIN)


def fixture():
    """Three records at the candidate's commit and the plugin text at the released commit.

    The candidate's note quotes its table on lines 4 and 5 in the catalog; at the released commit the same lines
    stand on lines 7 and 8 of the candidate's note and on lines 9 and 10 of the released note.
    """
    def av(file, line, excerpt):
        return {'file': file, 'line': line, 'url': f'{PREFIX}{OLD}/{file}#L{line}', 'excerpt': excerpt}
    sxc = {'file': 'docs/prior.md', 'line': 2,
           'url': 'https://github.com/Technoetic/semantic-crosscheck/blob/' + 'c' * 40 + '/docs/prior.md#L2',
           'excerpt': 'Prior independent use.'}
    prior = {'id': 'github:example/prior', 'kind': 'project', 'title': 'Prior project',
             'url': 'https://github.com/example/prior', 'year': None,
             'keys': ['github:example/prior'], 'aliases': ['Earlier name'], 'tags': ['preserved'],
             'note': 'Preserve this exact note.',
             'uses': [{'plugin': 'agentic-vault', 'role': 'background', 'evidence': [av('README.md', 1, README_ROW)]},
                      {'plugin': 'semantic-crosscheck', 'role': 'reference', 'evidence': [sxc]}]}
    paper = {'id': 'arxiv:2403.14720', 'kind': 'paper', 'title': 'Spotlighting', 'url': SPOTLIGHTING, 'year': 2024,
             'keys': ['arxiv:2403.14720'], 'aliases': [], 'tags': [],
             'note': 'The v0.52.0 release note cites it; this note is not rewritten by a repin.',
             'uses': [{'plugin': 'agentic-vault', 'role': 'reference', 'evidence': [av(CANDIDATE, 4, SPOT_ROW)]}]}
    article = {'id': 'url:' + SLSA, 'kind': 'article', 'title': 'SLSA v1.2 Source requirements', 'url': SLSA,
               'year': None, 'keys': ['url:' + SLSA], 'aliases': [], 'tags': [],
               'note': 'The v0.52.0 release note cites it; this note is not rewritten by a repin.',
               'uses': [{'plugin': 'agentic-vault', 'role': 'reference',
                         'evidence': [av(CANDIDATE, 5, SLSA_ROW), av(INTEGRITY, 2, INTEGRITY_ROW)]}]}
    registry = {'schemaVersion': 1, 'updatedAt': 'before', 'snapshots': {
        'agentic-vault': {'name': 'Agentic Vault', 'version': 'v0.52.0', 'commit': OLD, 'url': TREE + OLD},
        'semantic-crosscheck': {'name': 'Semantic Crosscheck', 'version': 'v0.27.0', 'commit': 'c' * 40}},
        'method': {'scope': 'fixture'}, 'sources': [prior, paper, article], 'identityResolutions': {'renames': []}}
    art = {'count': 1, 'assets': [{
        'sourceId': prior['id'], 'index': 1, 'output': 'media/cards/card-001.webp', 'bytes': len(IMAGE),
        'sha256': hashlib.sha256(IMAGE).hexdigest(), 'prompt': 'Original unique prompt.',
        'generationEvidenceUrls': [PREFIX + 'd' * 40 + '/README.md#L9', sxc['url']],
        'evidenceUrls': [prior['uses'][0]['evidence'][0]['url'], sxc['url']],
        'currentEvidenceUrls': [prior['uses'][0]['evidence'][0]['url'], sxc['url']]}]}
    texts = {'README.md': ['Inserted line.', README_ROW],
             CANDIDATE: ['# v0.52.0 — 미공개 후보', '', '이 후보는 릴리스로 게시하지 않았다.', '',
                         '| 출처 | 준 것 | 이번 적용 |', '|---|---|---|', SPOT_ROW, SLSA_ROW],
             RELEASE: ['# v0.52.1', '', '## v0.52.0 후보에서 고친 시험', '', '긴 TEMP 경로.', '',
                       '| 출처 | 준 것 | 이번 적용 |', '|---|---|---|', SPOT_ROW, SLSA_ROW],
             INTEGRITY: ['# 릴리스 무결성', '현재 판은 0.52.1이다.', INTEGRITY_ROW]}
    return registry, art, texts


def moved_base(registry, art):
    """The fixture after a semantic-crosscheck-only catalog update: a new version, one new record, one more citation.

    As such an update does, it pins every semantic-crosscheck row (and the current artwork evidence) to its new commit.
    """
    registry = json.loads(json.dumps(registry).replace('c' * 40, 'f' * 40))
    for asset in art['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [url.replace('c' * 40, 'f' * 40) for url in asset[field]]
    registry['snapshots']['semantic-crosscheck']['version'] = 'v0.28.0'
    registry['sources'].append({
        'id': 'github:example/other', 'kind': 'project', 'title': 'Other project', 'url': 'https://github.com/example/other',
        'year': None, 'keys': ['github:example/other'], 'aliases': [], 'tags': [], 'note': 'Cited by the other plugin.',
        'uses': [{'plugin': 'semantic-crosscheck', 'role': 'reference', 'evidence': [{
            'file': 'README.md', 'line': 3,
            'url': 'https://github.com/Technoetic/semantic-crosscheck/blob/' + 'f' * 40 + '/README.md#L3',
            'excerpt': 'Other project use.'}]}]})
    return registry, art


def av_rows(registry):
    return [row for source in registry['sources'] for use in source['uses'] if use['plugin'] == 'agentic-vault'
            for row in use['evidence']]


V0521_LINE = re.compile(r"^    \('v0\.52\.1','(v\d+\.\d+\.\d+)'\):\((\d+(?:,\d+){4})\),$", re.M)


def recorded_pairs(text):
    """The coverage lines of this update: each ('v0.52.1', X) line whose ('v0.52.0', X) line has the same tuple.

    A later catalog update adds a ('v0.52.1', Y) key of its own (the next semantic-crosscheck version) without such a
    v0.52.0 twin; that line is not this update's and is not counted.
    """
    return [(other, tuple(int(value) for value in counts.split(','))) for other, counts in V0521_LINE.findall(text)
            if re.search(r"^    \('v0\.52\.0','" + re.escape(other) + r"'\):\(" + counts + r"\),$", text, re.M)]


class SmallCatalogCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(updater, 'v0.52.1 Atlas updater is missing')
        patches = [mock.patch.object(updater, 'AV_ROWS', 4),
                   mock.patch.object(updater, 'AV_COVERAGE', (1, 1, 1)),
                   mock.patch.object(updater, 'PRIOR_COMMIT', OLD)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def prepare(self, registry, art, texts, commit=NEW, tag='v0.52.1', updated_at='fixed'):
        def read(file):
            if file not in texts:
                raise LookupError(file)
            return texts[file]
        return updater.prepare_update(registry, art, read, commit, tag, updated_at=updated_at)


class AV0521RepinTests(SmallCatalogCase):
    def test_repins_every_row_and_keeps_records_sxc_and_image_provenance(self):
        registry, art, texts = fixture()
        before = copy.deepcopy((registry, art))
        revised, images, summary = self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        self.assertEqual(list(revised), list(registry))
        self.assertEqual({key: revised[key] for key in ('schemaVersion', 'method', 'identityResolutions')},
                         {key: registry[key] for key in ('schemaVersion', 'method', 'identityResolutions')})
        self.assertEqual(revised['updatedAt'], 'fixed')
        self.assertEqual(revised['snapshots']['semantic-crosscheck'], registry['snapshots']['semantic-crosscheck'])
        self.assertEqual(revised['snapshots']['agentic-vault'],
                         {'name': 'Agentic Vault', 'version': 'v0.52.1', 'commit': NEW, 'url': TREE + NEW})
        self.assertEqual(list(revised['snapshots']['agentic-vault']), ['name', 'version', 'commit', 'url'])
        # No record is added, removed or reordered, and nothing but the rows of agentic-vault changes.
        self.assertEqual([source['id'] for source in revised['sources']],
                         [source['id'] for source in registry['sources']])
        for old, new in zip(registry['sources'], revised['sources']):
            self.assertEqual({key: value for key, value in new.items() if key != 'uses'},
                             {key: value for key, value in old.items() if key != 'uses'})
            self.assertEqual([(use['plugin'], use['role'], len(use['evidence'])) for use in new['uses']],
                             [(use['plugin'], use['role'], len(use['evidence'])) for use in old['uses']])
        self.assertEqual(revised['sources'][0]['uses'][1], registry['sources'][0]['uses'][1])
        rows = av_rows(revised)
        self.assertEqual([row['excerpt'] for row in rows], [row['excerpt'] for row in av_rows(registry)])
        for row in rows:
            self.assertEqual(list(row), ['file', 'line', 'url', 'excerpt'])
            self.assertEqual(row['url'], f"{PREFIX}{NEW}/{row['file']}#L{row['line']}")
            self.assertEqual(texts[row['file']][row['line'] - 1].strip()[:220], row['excerpt'])
        self.assertEqual([(row['file'], row['line']) for row in rows],
                         [('README.md', 2), (RELEASE, 9), (RELEASE, 10), (INTEGRITY, 3)])
        self.assertNotIn(OLD, json.dumps(revised))
        # The image keeps how it was made; only the current evidence follows the rows.
        self.assertEqual(images['count'], art['count'])
        for field in ('sourceId', 'index', 'output', 'bytes', 'sha256', 'prompt', 'generationEvidenceUrls'):
            self.assertEqual(images['assets'][0][field], art['assets'][0][field])
        self.assertEqual(images['assets'][0]['currentEvidenceUrls'],
                         [PREFIX + NEW + '/README.md#L2', art['assets'][0]['currentEvidenceUrls'][1]])
        self.assertEqual(images['assets'][0]['evidenceUrls'], images['assets'][0]['currentEvidenceUrls'])
        self.assertEqual((summary['addedSourceIds'], summary['newCitationRows']), ([], 0))
        self.assertEqual((summary['priorAgenticVaultCitationsRepinned'], summary['repinnedRowsTotal'],
                          summary['citationUrlsChanged'], summary['remappedLines'], summary['agenticVaultRows']),
                         (4, 4, 4, 4, 4))
        self.assertEqual((summary['coverageTuple'], summary['artworkCount']), (list(SMALL), 1))
        self.assertEqual(summary['semanticCrosscheckVersion'], 'v0.27.0')
        self.assertEqual((summary['excerptChanges'], summary['keptOnCandidateNote']), ([], []))
        self.assertEqual(summary['previousSnapshot'], registry['snapshots']['agentic-vault'])
        self.assertEqual(summary['snapshot'], revised['snapshots']['agentic-vault'])

    def test_candidate_note_rows_move_to_the_released_note_when_the_excerpt_stands_there_once(self):
        registry, art, texts = fixture()
        revised, _, summary = self.prepare(registry, art, texts)
        self.assertEqual(summary['movedToReleaseNote'], [
            {'sourceId': 'arxiv:2403.14720', 'from': CANDIDATE + '#L4', 'to': RELEASE + '#L9',
             'candidateNoteLine': 7},
            {'sourceId': 'url:' + SLSA, 'from': CANDIDATE + '#L5', 'to': RELEASE + '#L10', 'candidateNoteLine': 8}])
        self.assertEqual([row['file'] for row in av_rows(revised)].count(CANDIDATE), 0)
        # The candidate's note may have lost the line; the released note alone decides the move.
        registry, art, texts = fixture()
        texts[CANDIDATE] = texts[CANDIDATE][:6]
        _, _, summary = self.prepare(registry, art, texts)
        self.assertEqual([move['candidateNoteLine'] for move in summary['movedToReleaseNote']], [None, None])

    def test_candidate_note_rows_stay_and_are_listed_when_the_released_note_lacks_or_repeats_the_excerpt(self):
        for change, occurrences in (('reworded', 0), ('repeated', 2), ('absent', None)):
            registry, art, texts = fixture()
            if change == 'reworded':
                texts[RELEASE][9] = SLSA_ROW.replace('tags', 'tags, reworded')
            elif change == 'repeated':
                texts[RELEASE].append(SLSA_ROW)
            else:
                del texts[RELEASE]
            with self.subTest(change=change):
                revised, _, summary = self.prepare(registry, art, texts)
                row = revised['sources'][2]['uses'][0]['evidence'][0]
                self.assertEqual((row['file'], row['line'], row['excerpt']), (CANDIDATE, 8, SLSA_ROW))
                self.assertEqual(row['url'], PREFIX + NEW + '/' + CANDIDATE + '#L8')
                kept = [{'sourceId': 'url:' + SLSA, 'from': CANDIDATE + '#L5', 'to': CANDIDATE + '#L8',
                         'releaseNoteOccurrences': occurrences}]
                if change == 'absent':
                    kept.insert(0, {'sourceId': 'arxiv:2403.14720', 'from': CANDIDATE + '#L4',
                                    'to': CANDIDATE + '#L7', 'releaseNoteOccurrences': None})
                self.assertEqual(summary['keptOnCandidateNote'], kept)
                self.assertEqual(len(summary['movedToReleaseNote']), 0 if change == 'absent' else 1)
                self.assertEqual(summary['excerptChanges'], [])

    def test_a_row_whose_excerpt_is_not_found_exactly_once_is_listed_and_never_guessed(self):
        registry, art, texts = fixture()
        before = copy.deepcopy((registry, art))
        texts['README.md'] = ['Inserted line.', REWORDED, 'Another line.']
        with self.assertRaisesRegex(ValueError, 'cannot be repinned') as raised:
            self.prepare(registry, art, texts)
        self.assertIsInstance(raised.exception, updater.UnresolvedRows)
        self.assertEqual((registry, art), before)
        self.assertEqual(len(raised.exception.rows), 1)
        row = raised.exception.rows[0]
        self.assertEqual({key: row[key] for key in ('sourceId', 'file', 'line', 'excerpt', 'reviewedExcerpt')},
                         {'sourceId': 'github:example/prior', 'file': 'README.md', 'line': 1,
                          'excerpt': README_ROW, 'reviewedExcerpt': None})
        self.assertEqual(row['searched'], [{'file': 'README.md', 'occurrences': 0}])
        self.assertEqual((row['candidates'][0]['file'], row['candidates'][0]['line'], row['candidates'][0]['excerpt']),
                         ('README.md', 2, REWORDED))
        self.assertTrue(0.5 < row['candidates'][0]['similarity'] < 1)
        self.assertEqual(len(row['candidates']), 3)
        # A repeated line is as undecidable as a missing one; both copies are shown.
        registry, art, texts = fixture()
        texts['README.md'] = [README_ROW, 'Between.', README_ROW]
        with self.assertRaises(updater.UnresolvedRows) as raised:
            self.prepare(registry, art, texts)
        row = raised.exception.rows[0]
        self.assertEqual(row['searched'], [{'file': 'README.md', 'occurrences': 2}])
        self.assertEqual([(found['line'], found['similarity']) for found in row['candidates'][:2]], [(1, 1.0), (3, 1.0)])
        # A file that the release removed has no candidates.
        registry, art, texts = fixture()
        del texts['README.md']
        with self.assertRaises(updater.UnresolvedRows) as raised:
            self.prepare(registry, art, texts)
        self.assertEqual((raised.exception.rows[0]['searched'], raised.exception.rows[0]['candidates']),
                         ([{'file': 'README.md', 'occurrences': None}], []))
        # A note row whose excerpt stands on neither note, or twice on the candidate's note, is undecided too.
        for released, candidate in (([], []), ([], [SPOT_ROW, SPOT_ROW])):
            registry, art, texts = fixture()
            texts[RELEASE] = [line for line in texts[RELEASE] if line != SPOT_ROW] + released
            texts[CANDIDATE] = [line for line in texts[CANDIDATE] if line != SPOT_ROW] + candidate
            with self.subTest(candidate=len(candidate)), self.assertRaises(updater.UnresolvedRows) as raised:
                self.prepare(registry, art, texts)
            self.assertEqual(raised.exception.rows[0]['searched'],
                             [{'file': RELEASE, 'occurrences': 0}, {'file': CANDIDATE, 'occurrences': len(candidate)}])

    def test_every_undecided_row_is_reported_together_and_note_rows_search_both_notes(self):
        registry, art, texts = fixture()
        texts['README.md'] = ['Inserted line.', REWORDED]
        for file in (RELEASE, CANDIDATE):
            texts[file] = [line.replace('delimiting', 'delimiting alone') for line in texts[file]]
        with self.assertRaises(updater.UnresolvedRows) as raised:
            self.prepare(registry, art, texts)
        rows = raised.exception.rows
        self.assertEqual([(row['sourceId'], row['file'], row['line']) for row in rows],
                         [('github:example/prior', 'README.md', 1), ('arxiv:2403.14720', CANDIDATE, 4)])
        self.assertEqual(rows[1]['searched'], [{'file': RELEASE, 'occurrences': 0}, {'file': CANDIDATE, 'occurrences': 0}])
        self.assertEqual({(found['file'], found['line']) for found in rows[1]['candidates'][:2]},
                         {(RELEASE, 9), (CANDIDATE, 7)})
        self.assertIn('2 agentic-vault row(s)', str(raised.exception))
        self.assertIn('github:example/prior / README.md#L1', str(raised.exception))

    def test_a_reviewed_excerpt_replaces_only_a_row_that_no_longer_resolves(self):
        entry = ('github:example/prior', 'README.md', README_ROW, REWORDED)
        registry, art, texts = fixture()
        texts['README.md'] = ['Inserted line.', REWORDED]
        with mock.patch.object(updater, 'REVIEWED_EXCERPTS', (entry,)):
            revised, images, summary = self.prepare(registry, art, texts)
            row = revised['sources'][0]['uses'][0]['evidence'][0]
            self.assertEqual((row['file'], row['line'], row['excerpt']), ('README.md', 2, REWORDED))
            self.assertEqual(summary['excerptChanges'], [{'sourceId': 'github:example/prior', 'from': 'README.md#L1',
                                                          'to': 'README.md#L2', 'before': README_ROW, 'after': REWORDED}])
            self.assertEqual(summary['reviewedExcerptsUnused'], [])
            self.assertEqual(images['assets'][0]['currentEvidenceUrls'][0], PREFIX + NEW + '/README.md#L2')
            # Applied once: the second run finds the reviewed excerpt in place and reports the entry as unused.
            again, same, summary = self.prepare(revised, images, texts, updated_at='later')
            self.assertEqual((again, same), (revised, images))
            self.assertEqual((summary['excerptChanges'], summary['remappedLines']), ([], 0))
            self.assertEqual(summary['reviewedExcerptsUnused'],
                             [{'sourceId': 'github:example/prior', 'file': 'README.md', 'excerpt': README_ROW}])
            # A replacement for a row that still resolves is refused instead of rewriting a valid citation.
            with self.assertRaisesRegex(ValueError, 'still resolves'):
                self.prepare(*fixture())
            # A replacement that does not stand exactly once is as undecided as the row itself.
            registry, art, texts = fixture()
            texts['README.md'] = ['Inserted line.', REWORDED, REWORDED]
            with self.assertRaises(updater.UnresolvedRows) as raised:
                self.prepare(registry, art, texts)
            self.assertEqual(raised.exception.rows[0]['reviewedExcerpt'], REWORDED)
        for entries in ((entry, entry), (entry[:3] + ('x' * 221,),), (entry[:3] + (' padded ',),), (entry[:3] + ('',),)):
            with self.subTest(entries=len(entries)), mock.patch.object(updater, 'REVIEWED_EXCERPTS', entries), \
                    self.assertRaisesRegex(ValueError, 'REVIEWED_EXCERPTS'):
                self.prepare(*fixture())

    def test_second_run_is_idempotent_and_a_later_commit_moves_every_row_again(self):
        registry, art, texts = fixture()
        once, images, _ = self.prepare(registry, art, texts)
        twice, images2, summary = self.prepare(once, images, texts, updated_at='later')
        self.assertEqual((once, images), (twice, images2))
        self.assertEqual(twice['updatedAt'], 'fixed')
        self.assertEqual((summary['addedSourceIds'], summary['citationUrlsChanged'], summary['remappedLines'],
                          summary['movedToReleaseNote'], summary['priorAgenticVaultCitationsRepinned']),
                         ([], 0, 0, [], 4))
        later, images3, summary = self.prepare(once, images, texts, commit=LATER, updated_at='later')
        self.assertEqual((summary['citationUrlsChanged'], summary['remappedLines']), (4, 0))
        self.assertTrue(all(row['url'].startswith(PREFIX + LATER + '/') for row in av_rows(later)))
        self.assertEqual((later['updatedAt'], later['snapshots']['agentic-vault']['commit']), ('later', LATER))
        self.assertEqual(images3['assets'][0]['currentEvidenceUrls'][0], PREFIX + LATER + '/README.md#L2')

    def test_a_later_catalog_base_whose_other_plugin_moved_is_repinned_the_same_way(self):
        registry, art = moved_base(*fixture()[:2])
        texts = fixture()[2]
        before = copy.deepcopy((registry, art))
        revised, images, summary = self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        self.assertEqual((summary['semanticCrosscheckVersion'], summary['coverageTuple']), ('v0.28.0', [1, 1, 1, 4, 6]))
        self.assertEqual(revised['snapshots']['semantic-crosscheck'], registry['snapshots']['semantic-crosscheck'])
        self.assertEqual(revised['sources'][3], registry['sources'][3])
        self.assertEqual([(row['file'], row['line']) for row in av_rows(revised)],
                         [('README.md', 2), (RELEASE, 9), (RELEASE, 10), (INTEGRITY, 3)])
        # The coverage line and the history test name the semantic-crosscheck version and the totals of that catalog.
        texts = {DELIVERY_FILE: delivery('v0.28.0', (1, 1, 1, 4, 6))}
        edited, files = updater.edit_tests(texts, summary['semanticCrosscheckVersion'], summary['coverageTuple'])
        self.assertEqual(files, 1)
        self.assertIn("    ('v0.52.0','v0.28.0'):(1,1,1,4,6),\n    ('v0.52.1','v0.28.0'):(1,1,1,4,6),\n",
                      edited[DELIVERY_FILE])
        self.assertIn("        prior=EXPECTED_COVERAGE[('v0.52.0','v0.28.0')]\n", edited[DELIVERY_FILE])
        # The tuple of the v0.52.0 line must be the catalog's own; otherwise there is no anchor.
        with self.assertRaisesRegex(ValueError, 'anchor'):
            updater.edit_tests({DELIVERY_FILE: delivery('v0.28.0', SMALL)}, 'v0.28.0', (1, 1, 1, 4, 6))

    def test_unexpected_baseline_is_refused(self):
        registry, art, texts = fixture()
        registry['snapshots']['agentic-vault']['version'] = 'v0.51.0'
        with self.assertRaisesRegex(ValueError, 'Unexpected agentic-vault reference snapshot'):
            self.prepare(registry, art, texts)
        # v0.52.0 pinned to a commit other than the one its public tag names.
        registry, art, texts = fixture()
        registry = json.loads(json.dumps(registry).replace(OLD, 'd' * 40))
        with self.assertRaisesRegex(ValueError, 'public v0.52.0 tag'):
            self.prepare(registry, art, texts)
        # Another agentic-vault card or one row fewer: not the v0.52.0 references this update repins.
        registry, art, texts = fixture()
        extra = copy.deepcopy(registry['sources'][1])
        extra.update(id='arxiv:2510.09023', keys=['arxiv:2510.09023'], url='https://arxiv.org/abs/2510.09023',
                     title='Another paper')
        registry['sources'].append(extra)
        with self.assertRaisesRegex(ValueError, 'v0.52.0 references'):
            self.prepare(registry, art, texts)
        registry, art, texts = fixture()
        registry['sources'][2]['uses'][0]['evidence'].pop()
        with self.assertRaisesRegex(ValueError, 'v0.52.0 references'):
            self.prepare(registry, art, texts)
        for version in ('0.28.0', 'v0.28', None):
            registry, art, texts = fixture()
            registry['snapshots']['semantic-crosscheck']['version'] = version
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'semantic-crosscheck'):
                self.prepare(registry, art, texts)

    def test_sha_tag_and_the_candidate_commit_are_refused(self):
        for commit, tag in [('B' * 40, 'v0.52.1'), ('b' * 39, 'v0.52.1'), (NEW, 'v0.52.0'), (NEW, '../v0.52.1'),
                            (OLD, 'v0.52.1')]:
            with self.subTest(commit=commit, tag=tag), self.assertRaises(ValueError):
                self.prepare(*fixture(), commit=commit, tag=tag)

    def test_artwork_evidence_must_follow_the_rows(self):
        registry, art, texts = fixture()
        art['assets'][0]['currentEvidenceUrls'].append(PREFIX + OLD + '/docs/unknown.md#L1')
        before = copy.deepcopy((registry, art))
        with self.assertRaisesRegex(ValueError, 'prior citation map'):
            self.prepare(registry, art, texts)
        self.assertEqual((registry, art), before)
        registry, art, texts = fixture()
        del art['assets'][0]['evidenceUrls']
        with self.assertRaisesRegex(ValueError, 'evidence field missing'):
            self.prepare(registry, art, texts)

    def test_artwork_that_differs_beyond_the_two_evidence_lists_after_the_remap_is_refused(self):
        real = copy.deepcopy
        changes = (('prompt', lambda art: art['assets'][0].update(prompt='Another prompt.')),
                   ('sha256', lambda art: art['assets'][0].update(sha256='0' * 64)),
                   ('generationEvidenceUrls', lambda art: art['assets'][0]['generationEvidenceUrls'].pop()),
                   ('count', lambda art: art.update(count=2)),
                   ('asset added', lambda art: art['assets'].append(dict(art['assets'][0], index=2))))
        for name, change in changes:
            def altered(document, *rest, change=change):
                # The updater's own copy of the manifest, changed as a faulty remap could change it.
                result = real(document, *rest)
                if isinstance(document, dict) and 'assets' in document:
                    change(result)
                return result
            registry, art, texts = fixture()
            before = copy.deepcopy((registry, art))
            with self.subTest(change=name), mock.patch.object(updater, 'deepcopy', altered), \
                    self.assertRaisesRegex(ValueError, 'Immutable artwork provenance or assignments changed'):
                self.prepare(registry, art, texts)
            self.assertEqual((registry, art), before)

    def test_release_constants_are_consistent(self):
        av_rows_total, av_coverage, prior_commit, reviewed = REAL
        self.assertEqual((updater.TAG, updater.PRIOR_TAG), ('v0.52.1', 'v0.52.0'))
        self.assertEqual((updater.CANDIDATE_NOTE, updater.RELEASE_NOTE), (CANDIDATE, RELEASE))
        self.assertEqual((av_rows_total, av_coverage), (267, (60, 57, 29)))
        self.assertEqual(prior_commit, '3dbee6a159dd5f21417fa52c222805d5081c9db0')
        self.assertEqual(updater.TEST_FILES, (DELIVERY_FILE, ARTWORK_FILE))
        self.assertEqual(len({entry[:3] for entry in reviewed}), len(reviewed))
        for entry in reviewed:
            self.assertEqual(len(entry), 4)
            for value in entry:
                self.assertTrue(isinstance(value, str) and value and value == value.strip()[:220])
        source = (ROOT / 'scripts/update_av0521_references.py').read_text(encoding='utf-8')
        self.assertIsNone(re.search(PRIVATE, source), 'A credential or local path was found in the helper')


class DeliveryEditTests(unittest.TestCase):
    """The two insertions into tests/test_delivery.py and where the history test goes."""

    def test_insertions_apply_once_and_add_lines_only(self):
        base = {DELIVERY_FILE: delivery()}
        once, files = updater.edit_tests(base, 'v0.27.0', SMALL)
        twice, again = updater.edit_tests(once, 'v0.27.0', SMALL)
        self.assertEqual((files, twice, again), (1, once, 0))
        text = once[DELIVERY_FILE]
        self.assertIn("    ('v0.52.0','v0.27.0'):(1,1,1,3,5),\n    ('v0.52.1','v0.27.0'):(1,1,1,3,5),\n", text)
        self.assertIn(V052_END + "\n    def test_v0521_repin_keeps_every_card_and_citation_without_rewriting_history"
                      "(self):\n", text)
        self.assertTrue(text.endswith("(0,0,0,0,0))\n" + MAIN))
        self.assertEqual(set(base[DELIVERY_FILE].split('\n')) - set(text.split('\n')), set())
        scope = {'__name__': 'edited_delivery'}
        exec(compile(text, 'test_delivery.py', 'exec'), scope)
        scope['DeliveryTests']('test_v0521_repin_keeps_every_card_and_citation_without_rewriting_history').debug()
        for broken in ('no anchor', delivery().replace('(1,1,1,3,5)', '(1,1,1,3,6)')):
            with self.subTest(broken=broken[:9]), self.assertRaisesRegex(ValueError, 'anchor'):
                updater.edit_tests({DELIVERY_FILE: broken}, 'v0.27.0', SMALL)
        # A v0.52.1 line or history test that is not this helper's own stops the edit instead of adding a second one.
        for extra in ("    ('v0.52.1','v0.27.0'):(9,9,9,9,9),\n", "    def test_v0521_other(self):pass\n"):
            text = delivery().replace("}\n", extra + "}\n", 1) if extra.startswith("    ('") else \
                delivery().replace(MAIN, '\n' + extra + MAIN)
            with self.subTest(extra=extra[:20]), self.assertRaisesRegex(ValueError, 'already holds'):
                updater.edit_tests({DELIVERY_FILE: text}, 'v0.27.0', SMALL)

    def test_the_history_test_never_splits_an_intact_insertion_of_a_later_helper(self):
        later = "\n    def test_later_helper(self):\n        self.assertTrue(True)\n"
        # Inserted after the v0.52.0 history test, as this catalog's helpers do: the v0.52.1 test goes to the end.
        after_v052 = delivery().replace(V052_END, V052_END + later)
        keep = [V052_END + later]
        once, _ = updater.edit_tests({DELIVERY_FILE: after_v052}, 'v0.27.0', SMALL, keep)
        text = once[DELIVERY_FILE]
        self.assertEqual(text.count(keep[0]), 1)
        self.assertTrue(text.endswith("(0,0,0,0,0))\n" + MAIN))
        # Inserted before the main line, as the semantic-crosscheck v0.27.0 helper did: the v0.52.1 test follows v0.52.0.
        before_main = delivery().replace(MAIN, later + MAIN)
        keep = [later + MAIN]
        once, _ = updater.edit_tests({DELIVERY_FILE: before_main}, 'v0.27.0', SMALL, keep)
        text = once[DELIVERY_FILE]
        self.assertEqual(text.count(keep[0]), 1)
        self.assertIn(V052_END + "\n    def test_v0521_", text)
        # Both at once: no anchor keeps both, so nothing is guessed.
        both = delivery().replace(V052_END, V052_END + later).replace(MAIN, later.replace('later', 'last') + MAIN)
        keep = [V052_END + later, later.replace('later', 'last') + MAIN]
        with self.assertRaisesRegex(ValueError, 'split'):
            updater.edit_tests({DELIVERY_FILE: both}, 'v0.27.0', SMALL, keep)
        with self.assertRaisesRegex(ValueError, 'exactly once before'):
            updater.edit_tests({DELIVERY_FILE: delivery()}, 'v0.27.0', SMALL, ['not in the text'])

    def check_delivery(self, text, registry, scripts, earlier):
        """The contract of a tests/test_delivery.py text before the update, after it and in later catalogs.

        Before (no v0.52.1 line, catalog at v0.52.0) the semantic-crosscheck version and the tuple come from the
        registry; afterwards from the one pair of lines this update inserts, and both insertions already stand in the
        text. Returns the version and the tuple.
        """
        recorded = bool(V0521_LINE.search(text))
        if recorded:
            pairs = recorded_pairs(text)
            self.assertEqual(len(pairs), 1, 'expected exactly one v0.52.1 coverage line with a v0.52.0 twin')
            other, coverage = pairs[0]
        else:
            self.assertEqual(registry['snapshots']['agentic-vault']['version'], 'v0.52.0')
            other = updater.other_version(registry)
            coverage = tuple(updater._coverage(build_catalog.merge_sources(registry['sources']))[2])
        self.assertEqual(tuple(coverage[:3]), updater.AV_COVERAGE)
        keep = updater.earlier_insertions(scripts, DELIVERY_FILE, text)
        self.assertGreaterEqual(len(keep), earlier)
        once, inserted = updater.edit_tests({DELIVERY_FILE: text}, other, coverage, keep)
        self.assertEqual(inserted, 0 if recorded else 1, 'after the update the history test must stand once as well')
        twice, applied = updater.edit_tests(once, other, coverage, keep)
        self.assertEqual((twice, applied), (once, 0))
        edited = once[DELIVERY_FILE]
        self.assertEqual(updater.earlier_insertions(scripts, DELIVERY_FILE, edited), keep)
        self.assertEqual(edited.count('def test_v0521_repin'), 1)
        self.assertEqual(recorded_pairs(edited), [(other, coverage)])
        tup = '(' + ','.join(map(str, coverage)) + ')'
        self.assertEqual(edited.count(f"    ('v0.52.1','{other}'):{tup},\n"), 1)
        self.assertIn(f"    ('v0.52.0','{other}'):{tup},\n", edited)
        self.assertEqual(set(text.split('\n')) - set(edited.split('\n')), set())
        scope = {'__name__': 'edited_delivery', '__file__': str(ROOT / DELIVERY_FILE)}
        exec(compile(edited, 'test_delivery.py', 'exec'), scope)
        self.assertEqual(scope['EXPECTED_COVERAGE'][('v0.52.1', other)], scope['EXPECTED_COVERAGE'][('v0.52.0', other)])
        scope['DeliveryTests']('test_v0521_repin_keeps_every_card_and_citation_without_rewriting_history').debug()
        return other, coverage

    def test_tracked_delivery_test_gains_the_lines_once_and_keeps_every_intact_earlier_insertion(self):
        """On the tracked files, before the update (catalog at v0.52.0), after it and in later catalogs."""
        text = (ROOT / DELIVERY_FILE).read_text(encoding='utf-8')
        registry = json.loads((ROOT / 'data/registry.source.json').read_text(encoding='utf-8'))
        self.check_delivery(text, registry, ROOT / 'scripts', 2)  # at least the v0.52.0 helper's two insertions

    def test_the_line_of_this_update_is_found_by_its_v0520_twin_before_after_and_in_later_catalogs(self):
        registry = moved_base(*fixture()[:2])[0]  # semantic-crosscheck v0.28.0, coverage (1,1,1,4,6)
        base, found = delivery('v0.28.0', (1, 1, 1, 4, 6)), ('v0.28.0', (1, 1, 1, 4, 6))
        anchor, ours = "    ('v0.52.0','v0.28.0'):(1,1,1,4,6),\n", "    ('v0.52.1','v0.28.0'):(1,1,1,4,6),\n"
        later, next_release = "    ('v0.52.1','v0.29.0'):(1,1,1,5,8),\n", "    ('v0.53.0','v0.29.0'):(2,1,1,6,9),\n"
        with tempfile.TemporaryDirectory() as scripts, mock.patch.object(updater, 'AV_COVERAGE', (1, 1, 1)):
            self.assertEqual(self.check_delivery(base, registry, scripts, 0), found)
            after = updater.edit_tests({DELIVERY_FILE: base}, *found)[0][DELIVERY_FILE]
            released = copy.deepcopy(registry)
            released['snapshots']['agentic-vault']['version'] = 'v0.52.1'
            # Later catalogs: the next semantic-crosscheck update adds its own v0.52.1 key (another tuple or, by chance,
            # the same) and the next agentic-vault release its own key; this update's line is still the one pair.
            for state, text in (('after', after), ('later', after.replace(ours, ours + later)),
                                ('same tuple', after.replace(ours, ours + later.replace('5,8', '4,6'))),
                                ('next release', after.replace(ours, ours + later + next_release))):
                with self.subTest(state=state):
                    self.assertEqual(self.check_delivery(text, released, scripts, 0), found)
            # Lost, without its twin, repeated, beside a second twin pair or without the history test: not this
            # update's lines as it inserted them.
            second = later.replace('v0.52.1', 'v0.52.0') + later
            history = updater.delivery_insertions(*found)[2]
            for state, text in (('lost', base), ('no twin', after.replace(anchor, '')),
                                ('repeated', after.replace(ours, ours * 2)),
                                ('second pair', after.replace(ours, ours + second)),
                                ('history test lost', after.replace(history, ''))):
                with self.subTest(state=state), self.assertRaises(self.failureException):
                    self.check_delivery(text, released, scripts, 0)


class ArtworkEditTests(unittest.TestCase):
    """The two edits of tests/artwork-uniqueness.test.mjs: releasedFile and the generation evidence assertion."""

    NEW_ASSERT = ("    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
                  "    if(avCatalogVersion==='v0.52.0') assert.deepEqual(record.generationEvidenceUrls,citations);\n"
                  "    else assert.deepEqual(record.generationEvidenceUrls.map(releasedFile),"
                  "citations.map(releasedFile));\n"
                  "    assert.deepEqual(record.delivery.sourceDimensions,[1536,1024]);\n")
    RELEASED_LINE = ("const releasedFile=url=>pinnedFile(url).replace('/blob/<commit>/docs/releases/v0.52.0.md',"
                     "'/blob/<commit>/docs/releases/v0.52.1.md');\n")

    def test_the_two_edits_apply_once_and_change_only_the_generation_assertion(self):
        base = artwork()
        once = updater.edit_artwork_test(base)
        self.assertEqual(updater.edit_artwork_test(once), once)
        self.assertEqual(once.count('const releasedFile='), 1)
        self.assertIn(PINNED_LINE + self.RELEASED_LINE, once)
        self.assertEqual(once.count(self.NEW_ASSERT), 1)
        self.assertNotIn(GENERATION_ASSERT, once)
        removed = set(base.split('\n')) - set(once.split('\n'))
        self.assertEqual(removed, {'    assert.deepEqual(record.generationEvidenceUrls,citations);'})
        # The assertion an earlier helper already made version-dependent is left as it is.
        self.assertIn("    if(avCatalogVersion==='v0.47.0') assert.deepEqual(record.generationEvidenceUrls,citations);\n", once)

    def test_a_missing_or_repeated_anchor_or_another_released_file_stops_the_edit(self):
        base = artwork()
        broken = {'no pinnedFile': base.replace(PINNED_LINE, ''), 'no assertion': base.replace(GENERATION_ASSERT, ''),
                  'two assertions': base + GENERATION_ASSERT,
                  'other releasedFile': base.replace(PINNED_LINE, PINNED_LINE + 'const releasedFile=url=>url;\n')}
        for name, text in broken.items():
            with self.subTest(name), self.assertRaisesRegex(ValueError, 'anchor'):
                updater.edit_artwork_test(text)

    def test_an_earlier_helpers_insertion_stays_whole(self):
        base = artwork()
        keep = ["const avCatalogVersion=catalog.snapshots['agentic-vault'].version;\n" + PINNED_LINE]
        self.assertEqual(updater.edit_artwork_test(base, keep).count(keep[0]), 1)
        with self.assertRaisesRegex(ValueError, 'exactly once before'):
            updater.edit_artwork_test(base, ['not in the text'])

    def test_edit_tests_edits_the_artwork_test_when_it_is_given(self):
        out, files = updater.edit_tests({DELIVERY_FILE: delivery(), ARTWORK_FILE: artwork()}, 'v0.27.0', SMALL)
        self.assertEqual((files, out[ARTWORK_FILE]), (2, updater.edit_artwork_test(artwork())))
        out, files = updater.edit_tests({DELIVERY_FILE: delivery()}, 'v0.27.0', SMALL)
        self.assertEqual((files, sorted(out)), (1, [DELIVERY_FILE]))

    def test_released_file_compares_a_moved_row_by_its_released_note_and_others_by_file(self):
        # The JavaScript mapping in Python terms: the first commit becomes <commit>, a final #L<n> goes, and the
        # candidate's note counts as the released note it moves to.
        def released(url):
            pinned = re.sub('#L[0-9]+$', '', re.sub('/blob/[0-9a-f]{40}/', '/blob/<commit>/', url, count=1))
            return pinned.replace('/blob/<commit>/' + CANDIDATE, '/blob/<commit>/' + RELEASE, 1)
        self.assertEqual(released(PREFIX + OLD + '/' + CANDIDATE + '#L50'), released(PREFIX + NEW + '/' + RELEASE + '#L81'))
        self.assertEqual(released(PREFIX + OLD + '/' + INTEGRITY + '#L507'),
                         released(PREFIX + NEW + '/' + INTEGRITY + '#L509'))
        self.assertNotEqual(released(PREFIX + OLD + '/' + INTEGRITY + '#L1'), released(PREFIX + NEW + '/' + RELEASE + '#L1'))
        self.assertEqual(self.RELEASED_LINE, updater.ARTWORK_RELEASED)
        self.assertEqual(self.NEW_ASSERT, updater.ARTWORK_ASSERT_NEW)


class CommandLineTests(SmallCatalogCase):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    identity = ('-c', 'user.name=Fixture', '-c', 'user.email=')

    def git(self, root, *parts):
        return subprocess.check_output(['git', '-C', str(root), *parts], env=self.env,
                                       stderr=subprocess.DEVNULL).decode().strip()

    def plugin(self, root, texts, tag=True):
        root.mkdir()
        self.git(root, 'init', '--quiet')
        for file, lines in texts.items():
            (root / file).parent.mkdir(parents=True, exist_ok=True)
            (root / file).write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
        self.git(root, 'add', '--all')
        self.git(root, *self.identity, 'commit', '--quiet', '-m', 'fixture')
        if tag:
            self.git(root, *self.identity, 'tag', '-a', 'v0.52.1', '-m', 'fixture release')
        return self.git(root, 'rev-parse', 'HEAD')

    def atlas(self, root, registry, art, delivery_text=None):
        for folder in ('data', 'docs', 'media/cards', 'tests'):
            (root / folder).mkdir(parents=True)
        (root / 'data/registry.source.json').write_bytes(updater.encode(registry))
        (root / 'docs/card-artwork-unique-prompts.json').write_bytes(updater.encode(art))
        (root / 'media/cards/card-001.webp').write_bytes(IMAGE)
        (root / DELIVERY_FILE).write_bytes((delivery_text or delivery()).encode('utf-8'))
        (root / ARTWORK_FILE).write_bytes(artwork().encode('utf-8'))
        build_catalog.build(root)

    @staticmethod
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob('*'))
                if path.is_file()}

    def cli(self, plugin, commit, atlas, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = updater.main(['--plugin-root', str(plugin), '--commit', commit, '--atlas-root', str(atlas), *extra])
        return code, json.loads(out.getvalue()) if out.getvalue().strip() else None, err.getvalue()

    def test_dry_run_apply_and_rerun_write_the_registry_the_generated_files_and_the_test_edit(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art, texts = fixture()
            self.atlas(atlas, registry, art)
            commit = self.plugin(plugin, texts)
            before = self.files(atlas)
            changed = sorted([*DATA_FILES, DELIVERY_FILE, ARTWORK_FILE])
            code, out, _ = self.cli(plugin, commit, atlas)
            self.assertEqual((code, out['status'], out['mode'], out['publishable'], out['standIn']),
                             (0, 'PASS', 'dry-run', False, False))
            self.assertEqual((out['filesChanged'], out['testEditsApplied']), (changed, 2))
            self.assertEqual(self.files(atlas), before)
            code, out, _ = self.cli(plugin, commit, atlas, '--apply', '--public-verified')
            self.assertEqual((code, out['status'], out['mode'], out['publishable']), (0, 'PASS', 'applied', True))
            self.assertEqual((out['addedSourceIds'], out['newCitationRows'], out['priorAgenticVaultCitationsRepinned'],
                              out['remappedLines'], out['coverageTuple'], out['testEditsApplied'], out['artworkCount']),
                             ([], 0, 4, 4, list(SMALL), 2, 1))
            after = self.files(atlas)
            self.assertEqual(set(after), set(before))
            self.assertEqual(sorted(name for name in after if after[name] != before[name]), changed)
            for name in DATA_FILES:
                self.assertNotIn(OLD.encode(), after[name])
            written = json.loads(after['data/registry.source.json'])
            catalog = json.loads(after['data/catalog.json'])
            self.assertEqual(written['snapshots']['agentic-vault'],
                             {'name': 'Agentic Vault', 'version': 'v0.52.1', 'commit': commit, 'url': TREE + commit})
            self.assertEqual(catalog['snapshots'], written['snapshots'])
            self.assertTrue(all(row['url'].startswith(PREFIX + commit + '/') for row in av_rows(catalog)))
            self.assertEqual((catalog['counts']['total'], catalog['counts']['citations']), (3, 5))
            # The generated files are exactly what the catalog's builder makes of the written registry.
            with tempfile.TemporaryDirectory() as other:
                (Path(other) / 'data').mkdir()
                (Path(other) / 'data/registry.source.json').write_bytes(after['data/registry.source.json'])
                build_catalog.build(Path(other))
                for name in ('data/catalog.json', 'data/catalog.csv'):
                    self.assertEqual((Path(other) / name).read_bytes(), after[name])
            compile(after[DELIVERY_FILE].decode('utf-8'), 'test_delivery.py', 'exec')
            self.assertEqual(after[DELIVERY_FILE].count(b"('v0.52.1','v0.27.0'):(1,1,1,3,5),"), 1)
            code, out, _ = self.cli(plugin, commit, atlas, '--apply', '--public-verified')
            self.assertEqual((code, out['status'], out['filesChanged'], out['testEditsApplied'], out['remappedLines'],
                              out['citationUrlsChanged'], out['addedSourceIds']), (0, 'PASS', [], 0, 0, 0, []))
            self.assertEqual(self.files(atlas), after)

    def test_apply_on_a_later_catalog_base_keeps_the_other_plugin_and_names_its_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art = moved_base(*fixture()[:2])
            self.atlas(atlas, registry, art, delivery('v0.28.0', (1, 1, 1, 4, 6)))
            commit = self.plugin(plugin, fixture()[2])
            base_catalog = json.loads((atlas / 'data/catalog.json').read_bytes())
            code, out, _ = self.cli(plugin, commit, atlas, '--apply', '--public-verified')
            self.assertEqual((code, out['status'], out['coverageTuple'], out['semanticCrosscheckVersion']),
                             (0, 'PASS', [1, 1, 1, 4, 6], 'v0.28.0'))
            catalog = json.loads((atlas / 'data/catalog.json').read_bytes())
            self.assertEqual((catalog['counts'], catalog['countsByPlugin']),
                             (base_catalog['counts'], base_catalog['countsByPlugin']))
            self.assertEqual(catalog['snapshots']['semantic-crosscheck'], base_catalog['snapshots']['semantic-crosscheck'])
            self.assertEqual([use for source in catalog['sources'] for use in source['uses']
                              if use['plugin'] == 'semantic-crosscheck'],
                             [use for source in base_catalog['sources'] for use in source['uses']
                              if use['plugin'] == 'semantic-crosscheck'])
            self.assertIn(b"    ('v0.52.1','v0.28.0'):(1,1,1,4,6),\n", (atlas / DELIVERY_FILE).read_bytes())

    def test_apply_keeps_the_intact_insertion_of_a_helper_found_in_the_catalog_scripts(self):
        later = "\n    def test_later_helper(self):\n        self.assertTrue(True)\n"
        helper = ("TEST_EDITS = (('tests/test_delivery.py',\n"
                  f"               {V052_END!r},\n"
                  f"               {V052_END + later!r}),)\n")
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art, texts = fixture()
            self.atlas(atlas, registry, art, delivery().replace(V052_END, V052_END + later))
            (atlas / 'scripts').mkdir()
            (atlas / 'scripts/update_later_references.py').write_text(helper, encoding='utf-8')
            commit = self.plugin(plugin, texts)
            code, out, _ = self.cli(plugin, commit, atlas, '--apply', '--public-verified')
            self.assertEqual((code, out['status'], out['earlierInsertionsKept'], out['testEditsApplied']),
                             (0, 'PASS', 1, 2))
            text = (atlas / DELIVERY_FILE).read_text(encoding='utf-8')
            self.assertEqual(text.count(V052_END + later), 1)
            self.assertTrue(text.endswith("(0,0,0,0,0))\n" + MAIN))
            # A helper whose test edits cannot be read stops the update before anything is written.
            (atlas / 'scripts/update_broken_references.py').write_text('raise RuntimeError("broken")\n',
                                                                       encoding='utf-8')
            before = self.files(atlas)
            code, out, err = self.cli(plugin, commit, atlas)
            self.assertEqual((code, out), (1, None))
            self.assertIn('update_broken_references.py', json.loads(err)['message'])
            self.assertEqual(self.files(atlas), before)

    def test_stand_in_is_a_dry_run_without_a_tag_and_a_real_run_needs_the_annotated_tag(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art, texts = fixture()
            self.atlas(atlas, registry, art)
            commit = self.plugin(plugin, texts, tag=False)
            before = self.files(atlas)
            code, out, err = self.cli(plugin, commit, atlas)
            self.assertEqual((code, out), (1, None))
            self.assertEqual(json.loads(err)['status'], 'error')
            code, out, _ = self.cli(plugin, commit, atlas, '--stand-in')
            self.assertEqual((code, out['status'], out['mode'], out['publishable'], out['standIn']),
                             (0, 'PASS', 'dry-run', False, True))
            # A stand-in commit that the plugin clone does not hold is an error, not a list of undecided rows.
            code, out, err = self.cli(plugin, 'f' * 40, atlas, '--stand-in')
            self.assertEqual((code, out, json.loads(err)['status']), (1, None, 'error'))
            self.git(plugin, 'tag', 'v0.52.1')
            self.assertEqual(self.cli(plugin, commit, atlas)[0], 1)
            self.assertEqual(self.files(atlas), before)

    def test_a_row_that_needs_a_decision_stops_with_exit_code_3_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art, texts = fixture()
            texts['README.md'] = ['Inserted line.', REWORDED]
            self.atlas(atlas, registry, art)
            commit = self.plugin(plugin, texts)
            before = self.files(atlas)
            for extra, mode in (((), 'dry-run'), (('--apply', '--public-verified'), 'apply refused'),
                                (('--stand-in',), 'dry-run')):
                code, out, err = self.cli(plugin, commit, atlas, *extra)
                with self.subTest(mode=mode, extra=extra):
                    self.assertEqual((code, out['status'], out['mode']), (3, 'BLOCKED', mode))
                    self.assertEqual(len(out['unresolvedRows']), 1)
                    row = out['unresolvedRows'][0]
                    self.assertEqual((row['sourceId'], row['file'], row['line'], row['excerpt']),
                                     ('github:example/prior', 'README.md', 1, README_ROW))
                    self.assertEqual((row['candidates'][0]['line'], row['candidates'][0]['excerpt']), (2, REWORDED))
                    self.assertIn('need a decision', json.loads(err)['message'])
                    self.assertEqual(self.files(atlas), before)

    def test_generated_files_that_are_not_a_build_of_the_registry_stop_the_helper(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas, plugin = Path(temporary) / 'atlas', Path(temporary) / 'plugin'
            registry, art, texts = fixture()
            self.atlas(atlas, registry, art)
            commit = self.plugin(plugin, texts)
            with (atlas / 'data/catalog.csv').open('ab') as stream:
                stream.write(b'unreviewed,row\n')
            before = self.files(atlas)
            code, out, err = self.cli(plugin, commit, atlas, '--apply', '--public-verified')
            self.assertEqual((code, out), (1, None))
            self.assertIn('not a build of data/registry.source.json', json.loads(err)['message'])
            self.assertEqual(self.files(atlas), before)

    def test_a_failed_replacement_restores_every_file_and_leaves_no_staging_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / 'first.json', Path(temporary) / 'second.json'
            first.write_bytes(b'one')
            second.write_bytes(b'two')
            replace = os.replace

            def failing(source, target):
                if Path(target) == second:
                    raise OSError('fixture failure')
                return replace(source, target)
            with mock.patch.object(updater.os, 'replace', failing), self.assertRaisesRegex(OSError, 'fixture failure'):
                updater.write_files({first: b'ONE', second: b'TWO'})
            self.assertEqual((first.read_bytes(), second.read_bytes()), (b'one', b'two'))
            self.assertEqual(sorted(path.name for path in Path(temporary).iterdir()), ['first.json', 'second.json'])
            updater.write_files({first: b'ONE', second: b'TWO'})
            self.assertEqual((first.read_bytes(), second.read_bytes()), (b'ONE', b'TWO'))

    def test_cli_rejects_apply_without_public_verification_and_stand_in_apply(self):
        for extra in (['--apply'], ['--stand-in', '--apply', '--public-verified'],
                      ['--stand-in', '--apply'], ['--stand-in', '--public-verified'], ['--tag', 'v0.52.0']):
            argv = ['--plugin-root', '.', '--commit', NEW, *extra]
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                updater.main(argv)
            self.assertEqual(raised.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            updater.main(['--plugin-root', '.', '--commit', OLD])
        self.assertEqual(raised.exception.code, 2)

    def test_actual_local_tag_must_be_annotated_and_match_exact_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plugin'
            commit = self.plugin(root, {'file.txt': ['fixture']}, tag=False)
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                updater.verify_tag(root, commit)
            self.git(root, 'tag', 'v0.52.1')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, commit)
            self.git(root, 'tag', '-d', 'v0.52.1')
            self.git(root, *self.identity, 'tag', '-a', 'v0.52.1', '-m', 'fixture release')
            updater.verify_tag(root, commit)
            (root / 'file.txt').write_text('changed fixture', encoding='utf-8')
            self.git(root, 'add', 'file.txt')
            self.git(root, *self.identity, 'commit', '--quiet', '-m', 'second fixture')
            with self.assertRaises(ValueError):
                updater.verify_tag(root, self.git(root, 'rev-parse', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
