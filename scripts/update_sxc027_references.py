"""Offline, dry-run-first semantic-crosscheck v0.27.0 reference update from exact Git blobs.

Adds the six sources of the v0.27.0 release note's References table that have a
catalog identity: the pgsql-hackers thread behind the new timestamp/timestamptz
pitfall (cited through its list-archive page), the four pages the README
requirements table cites for the upstream end of support of the minimum
runtimes (PEP 664, the PostgreSQL versioning policy, the Adoptium Temurin
support page and the nodejs/Release repository) and Diátaxis. The GitHub
Advisory Database address that the table also cites has no canonical identity
(canonical_key() returns None), so it is reported and not catalogued.

Every prior semantic-crosscheck citation moves to the supplied commit, because
the catalog schema binds each citation of a plugin to that plugin's declared
snapshot. Each prior row keeps its file and excerpt; its line follows the
excerpt, which must occur exactly once in that file at the new revision, or the
helper stops and lists every row that does not. agentic-vault (snapshot and
rows), existing metadata and immutable artwork provenance stay unchanged. Every
non-test line of the plugin that names a new source must be covered by one of
that source's rows (test lines that pin the README's addresses are reported,
not cited), so a citation added later stops the helper instead of being left
out. The new sources use the text fallback; no image, prompt or interface is
created, and the two tracked tests that count catalog coverage and
commissioned artwork receive exact, guarded, idempotent edits.

No fetch, commit, push, publication or plugin change. Apply requires a locally
verified annotated release tag that names the commit and the caller's separate
assertion that those exact bytes are public. --stand-in skips the tag check
for a nonpublishable dry run; it cannot apply.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update
from update_av048_references import excerpt_of, grep_key, immutable_artwork, naming_lines, verify_images

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'semantic-crosscheck'
PREFIX = f'https://github.com/Technoetic/{PLUGIN}/blob/'
TAG, PRIOR_TAG, AV_TAG = 'v0.27.0', 'v0.24.0', 'v0.50.0'
RELEASE = 'docs/releases/v0.27.0.md'
README = 'README.md'

THREAD = 'https://www.postgresql.org/list/pgsql-hackers/since/202607270000/'
PEP = 'https://peps.python.org/pep-0664/'
POSTGRES = 'https://www.postgresql.org/support/versioning/'
ADOPTIUM = 'https://adoptium.net/support/'
NODE = 'https://github.com/nodejs/Release'
DIATAXIS = 'https://diataxis.fr/'

FIRST = ('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog, and a git grep '
         'of the semantic-crosscheck v0.26.0 tree (the previous release) found no citation of it. ')
TABLE_ROW = ('The release note lists it in its References table on one line with the other three end-of-support pages, '
             'for "The end-of-support dates in the README requirements table." The README says the dates were checked '
             'on 2026-11-16; this entry read the page the same day, and the schedule may change. ')
READ = 'Read 2026-11-16; the page may have changed since. '
NO_CLAIM = 'This records a citation, not copied code, a runtime dependency or reproduced results.'
THREAD_NOTE = (
    'A pgsql-hackers mailing-list thread, 2026-07-27 to 2026-07-31; the catalog has no mailing-list kind, so it is '
    'recorded as an article titled with the thread subject. The plugin cites it through the list-archive page for '
    'messages since 2026-07-27 00:00, which lists the opening message and the replies of that day (a reply of '
    '2026-07-31 is on the archive page for that day), because the address of a single message embeds an address-shaped '
    "Message-ID that the plugin's leak scanner refuses; this catalog records no Message-ID or e-mail address either. "
    'v0.27.0 cites it for the report that an index scan and a sequential scan disagree on these comparisons near a '
    'daylight-saving change, behind the new pitfall "Do not compare a timestamp column with a timestamptz value" in '
    'skills/semantic-crosscheck/references/pitfalls.md and its integration test. ')
PEP_NOTE = (
    'Python Enhancement Proposal 664, the Python 3.11 release schedule (Informational, created 2021-07-12), which gives '
    'source-only security fixes for 3.11 "until approximately October 2027". v0.27.0 cites it in the README '
    'requirements table for the upstream end of support of the minimum Python 3.11, about 2027-10 (end of security '
    'fixes). ')
POSTGRES_NOTE = (
    'The PostgreSQL versioning policy page, whose release table gives PostgreSQL 17 a final release on November 8, 2029. '
    'v0.27.0 cites it in the README requirements table for the upstream end of support of the minimum PostgreSQL 17 '
    '(2029-11-08, the final release). ')
ADOPTIUM_NOTE = (
    'The Eclipse Temurin support page of Adoptium (page title "Temurin™ Support | Adoptium"), whose table gives Java 11 '
    '(LTS) an end of availability of "At least Oct 2027". v0.27.0 cites it in the README requirements table for the '
    'upstream end of support of the minimum Java 11, which the reason stage needs for HermiT (at least until 2027-10, '
    'Eclipse Temurin 11). ')
NODE_NOTE = (
    'The repository of the Node.js Release Working Group, whose README release schedule gives Node.js 22.x (Jod) an '
    'end-of-life of 2027-04-30. v0.27.0 cites it in the README requirements table for the upstream end of support of '
    'the minimum Node.js 22, which cube-install, cube and verify need; the README notes that it is the first minimum to '
    'end and that raising it goes with moving the Cube 1.8.3 pin. ')
DIATAXIS_NOTE = (
    'Diátaxis, a framework for technical documentation that separates tutorials, how-to guides, reference and '
    'explanation; the site gives no publication date, so no year is recorded. v0.27.0 cites it, in the release note '
    "only, for separating the README's reference sections from its tutorial and explanation: the stages and options, "
    'the reading of results and the check ids moved to docs/reference/cli.md, docs/reference/results.md and '
    'docs/reference/check-ids.md, and the README went from 1,054 to 770 lines. ')


def _source(url, kind, title, year, aliases, note, files):
    # The release citation comes first; each text must appear on exactly one line that names the source.
    return (canonical_key(url)['key'], kind, title, url, year, aliases, 'reference', FIRST + note + NO_CLAIM,
            tuple((file, '(' + url + ')') for file in files))


# id, kind, title, url, year, aliases, role, note, ((file, text on exactly one line naming the source), ...)
REFERENCES = (
    _source(THREAD, 'article', 'timestamp vs. timestamptz comparisons inconsistently ordered under DST', 2026,
            ['pgsql-hackers list archive from 2026-07-27'], THREAD_NOTE + READ, (RELEASE,)),
    _source(PEP, 'article', 'PEP 664 – Python 3.11 Release Schedule', 2021, ['PEP 664'],
            PEP_NOTE + TABLE_ROW, (RELEASE, README)),
    _source(POSTGRES, 'article', 'PostgreSQL: Versioning Policy', None,
            ['PostgreSQL versioning policy', 'PostgreSQL 버전 정책'], POSTGRES_NOTE + TABLE_ROW, (RELEASE, README)),
    _source(ADOPTIUM, 'article', 'Temurin™ Support', None,
            ['Temurin Support', 'Adoptium support page', 'Adoptium 지원 일정'], ADOPTIUM_NOTE + TABLE_ROW,
            (RELEASE, README)),
    _source(NODE, 'project', 'nodejs/Release', None,
            ['Node.js release schedule', 'Node.js Release Working Group', 'Node.js 릴리스 일정'], NODE_NOTE + TABLE_ROW,
            (RELEASE, README)),
    _source(DIATAXIS, 'article', 'Diátaxis', None, ['Diataxis'], DIATAXIS_NOTE + READ, (RELEASE,)),
)
NEW_IDS = [row[0] for row in REFERENCES]
NEW_CITATIONS = sum(len(row[8]) for row in REFERENCES)
# Cited by the release note but not catalogued: a catalog entry needs a canonical identity.
UNCATALOGUED = ({'url': 'https://github.com/advisories', 'name': 'GitHub Advisory Database',
                 'reason': 'canonical_key() returns None: a github.com address needs an owner and a repository '
                           'segment, so this path has no catalog identity'},)
# The published catalog this update starts from: agentic-vault v0.50.0 with semantic-crosscheck v0.24.0 and all
# 172 sources illustrated (public main a3fb1d0).
BASE = {'total': 172, 'citations': 316, 'sxc': 66, 'av': 250}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE = (56, 57, 22, 172, 316)
EXPECTED_TUPLE = (56, 57, 22, 178, 326)
# semantic-crosscheck tuple of the same test: paper, sources, citations, sources shared by both plugins.
PRIOR_SXC = (15, 38, 66, 5)
EXPECTED_SXC = (15, 44, 76, 5)
# Public catalog data must hold no e-mail address, Message-ID, local path or credential (tests/test_delivery.py).
LEAK = re.compile(r'(?i)(?<![A-Za-z])[a-z]:[\\/]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|op_u_[A-Za-z0-9]+'
                  r'|sk-[A-Za-z0-9]{16,}|@')


def _validate_revision(commit, tag):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected an exact lowercase 40-character commit and release tag ' + TAG)


def _locations(pairs):
    return [f'{file}#L{line}' for file, line in sorted(pairs)]


def _shape(sources):
    return [(s['id'], s['kind'], s['title'], s['url'], s.get('year'), s.get('note'), s['keys'], s['aliases'],
             s['tags'], [(u['plugin'], u['role'], [(r['file'], r['excerpt']) for r in u['evidence']])
                         for u in s['uses']]) for s in sources]


def _plugin_uses(registry, plugin):
    return [(s['id'], deepcopy(u)) for s in registry['sources'] for u in s['uses'] if u['plugin'] == plugin]


def sxc_rows(registry):
    return sum(len(use['evidence']) for _, use in _plugin_uses(registry, PLUGIN))


def sxc_tuple(merged):
    counts = metrics([s for s in merged if any(u['plugin'] == PLUGIN for u in s['uses'])])
    rows = sum(len(u['evidence']) for s in merged for u in s['uses'] if u['plugin'] == PLUGIN)
    return (counts['paper'], counts['total'], rows, metrics(merged)['shared'])


def cited_rows(cites, read_lines, commit, identity):
    rows, covered = [], set()
    for file, needle in cites:
        lines = read_lines(file)
        matches = [i + 1 for i, text in enumerate(lines) if needle in text]
        if len(matches) != 1:
            raise ValueError(f'New citation needs one exact line: {file}: {needle} ({len(matches)} lines)')
        line = matches[0]
        excerpt = excerpt_of(lines[line - 1])
        if sum(excerpt_of(text) == excerpt for text in lines) != 1:
            raise ValueError(f'New citation excerpt is not unique in its file: {file}#L{line}')
        if line not in naming_lines(identity, lines):
            raise ValueError(f'The cited line does not name {identity}: {file}#L{line}')
        covered.add((file, line))
        rows.append({'file': file, 'line': line, 'url': f'{PREFIX}{commit}/{file}#L{line}', 'excerpt': excerpt})
    return rows, covered


def repin(revised, read_lines, commit):
    """Move every semantic-crosscheck row to the commit; the line follows the excerpt, which must occur once."""
    remapped, failures, moves = {}, [], []
    count = 0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin'] != PLUGIN:
                continue
            for row in use['evidence']:
                count += 1
                old_line, old_url = row['line'], row['url']
                name = f"{source['id']} / {row['file']}#L{old_line} (excerpt {row['excerpt'][:80]!r})"
                try:
                    lines = read_lines(row['file'])
                except (LookupError, ValueError, OSError):
                    failures.append(name + ': the file is absent at the new revision')
                    continue
                matches = [i + 1 for i, text in enumerate(lines) if excerpt_of(text) == row['excerpt']]
                if len(matches) != 1:
                    near = [i + 1 for i, text in enumerate(lines) if row['excerpt'][:40] in text][:5]
                    failures.append(f'{name}: the excerpt is on {len(matches)} lines at the new revision '
                                    f'(lines holding its first 40 characters: {near})')
                    continue
                line = matches[0]
                row.update(line=line, url=f"{PREFIX}{commit}/{row['file']}#L{line}")
                if old_url in remapped and remapped[old_url] != row['url']:
                    failures.append(name + ': ambiguous old citation map')
                remapped[old_url] = row['url']
                if line != old_line:
                    moves.append({'sourceId': source['id'], 'file': row['file'], 'from': old_line, 'to': line})
    if failures:
        raise ValueError(f'{len(failures)} semantic-crosscheck row(s) cannot be repinned: ' + '; '.join(failures))
    return remapped, count, moves


def prepare_update(registry, artwork, read_lines, commit, tag=TAG, *, url_index, updated_at=None):
    """url_index(url) -> {file: [line, ...]} of every line in the plugin revision that names the source."""
    _validate_revision(commit, tag)
    before = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': before})
    snapshots = registry['snapshots']
    version = snapshots[PLUGIN]['version']
    present = set(NEW_IDS) & {source['id'] for source in registry['sources']}
    if snapshots['agentic-vault']['version'] != AV_TAG:
        raise ValueError('Expected the published agentic-vault ' + AV_TAG + ' snapshot; rebase this helper')
    if version == PRIOR_TAG:
        counts = metrics(before)
        if present or (counts['total'], counts['citations'], sxc_rows(registry), registry_av_rows(registry)) != (
                BASE['total'], BASE['citations'], BASE['sxc'], BASE['av']):
            raise ValueError(f"Expected the published {PRIOR_TAG} baseline of {BASE['total']} sources and "
                             f"{BASE['citations']} citations ({BASE['sxc']} semantic-crosscheck, {BASE['av']} "
                             'agentic-vault)')
    elif version != TAG or present != set(NEW_IDS):
        raise ValueError('Unexpected or partial semantic-crosscheck reference snapshot ' + str(version))
    for entry in UNCATALOGUED:
        if canonical_key(entry['url']) is not None:
            raise ValueError('An uncatalogued address now has a catalog identity; review: ' + entry['url'])
    # Each key names one work. A hit under another id needs a reviewed merge, not a second card.
    for row in REFERENCES:
        if canonical_key(row[3])['key'] != row[0]:
            raise ValueError('Canonical source identity mismatch: ' + row[0])
        for source in registry['sources']:
            keys = {source['id'], *source['keys']}
            if source.get('url') and canonical_key(source['url']):
                keys.add(canonical_key(source['url'])['key'])
            if source['id'] != row[0] and row[0] in keys:
                raise ValueError('Existing source identity requires a reviewed merge: ' + row[0])

    revised, images = deepcopy(registry), deepcopy(artwork)
    old_ids = [source['id'] for source in registry['sources']]
    old_shape = _shape(registry['sources'])
    old_av = _plugin_uses(registry, 'agentic-vault')
    remapped, count, moves = repin(revised, read_lines, commit)
    added, occurrences, unlisted = [], {}, {}
    for identity, kind, title, url, year, aliases, role, note, cites in REFERENCES:
        rows, covered = cited_rows(cites, read_lines, commit, identity)
        if rows[0]['file'] != RELEASE:
            raise ValueError('New reference lacks an exact release citation: ' + identity)
        named = {(file, line) for file, lines in url_index(url).items() for line in lines}
        tests = {(file, line) for file, line in named if file.startswith('tests/')}
        uncovered = named - covered - tests
        if uncovered or covered - named:
            raise ValueError(f'Every non-test line that names {url} needs its own row; uncovered: '
                             + ', '.join(_locations(uncovered)) + '; expected but absent: '
                             + ', '.join(_locations(covered - named)))
        occurrences[url], unlisted[url] = _locations(covered), _locations(tests)
        record = {'id': identity, 'kind': kind, 'title': title, 'url': url, 'year': year, 'keys': [identity],
                  'aliases': list(aliases), 'tags': [], 'note': note,
                  'uses': [{'plugin': PLUGIN, 'role': role, 'evidence': rows}]}
        if LEAK.search(json.dumps(record, ensure_ascii=False)):
            raise ValueError('A new record would publish an address, Message-ID, local path or credential: '
                             + identity)
        prior = next((source for source in revised['sources'] if source['id'] == identity), None)
        if prior is None:
            revised['sources'].append(record)
            added.append(identity)
        elif prior != record:
            raise ValueError('Previously applied record differs; manual review required: ' + identity)
    revised['snapshots'][PLUGIN] = {
        'name': 'Semantic Crosscheck', 'version': TAG, 'commit': commit,
        'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}'}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    # Existing records keep kind, title, url, year, note, keys, aliases, tags, roles, files and excerpts.
    kept = [source for source in revised['sources'] if source['id'] in old_ids]
    if [source['id'] for source in revised['sources']][:len(old_ids)] != old_ids or _shape(kept) != old_shape:
        raise ValueError('An existing record changed beyond its commit and line')
    if (revised['snapshots']['agentic-vault'] != snapshots['agentic-vault']
            or _plugin_uses(revised, 'agentic-vault') != old_av):
        raise ValueError('The agentic-vault snapshot or one of its uses changed')
    counts = metrics(merged)
    av = metrics([s for s in merged if any(u['plugin'] == 'agentic-vault' for u in s['uses'])])
    coverage = (av['paper'], av['project'] + av['format'], av['article'], counts['total'], counts['citations'])
    sxc = sxc_tuple(merged)
    if (coverage != EXPECTED_TUPLE or sxc != EXPECTED_SXC
            or sxc_rows(revised) != BASE['sxc'] + NEW_CITATIONS or registry_av_rows(revised) != BASE['av']):
        raise ValueError(f'Unexpected coverage {coverage} / {sxc}; expected {EXPECTED_TUPLE} / {EXPECTED_SXC}')
    for asset in images['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            if field not in asset:
                raise ValueError('Artwork current evidence field missing')
            if any(url.startswith(PREFIX) and url not in remapped for url in asset[field]):
                raise ValueError('Artwork URL is absent from the prior citation map')
            asset[field] = [remapped.get(url, url) for url in asset[field]]
    if (images['count'] != artwork['count'] or len(images['assets']) != artwork['count']
            or immutable_artwork(images) != immutable_artwork(artwork)):
        raise ValueError('Immutable artwork provenance or assignments changed')
    if set(NEW_IDS) & {asset['sourceId'] for asset in images['assets']}:
        raise ValueError('Uncommissioned v0.27.0 sources must use text fallback')
    return revised, images, {
        'addedSourceIds': added, 'newCitationRows': NEW_CITATIONS, 'repinnedRowsTotal': count,
        'priorSemanticCrosscheckCitationsRepinned': count - (NEW_CITATIONS if version == TAG else 0),
        'remappedLines': len(moves), 'movedRows': moves, 'counts': counts,
        'semanticCrosscheckTuple': list(sxc), 'coverageTuple': list(coverage),
        'semanticCrosscheckRows': sxc_rows(revised), 'agenticVaultRows': registry_av_rows(revised),
        'citedAddressLines': occurrences, 'testLinesNotCited': unlisted,
        'notCatalogued': [dict(entry) for entry in UNCATALOGUED],
        'uncommissionedSourceIds': list(NEW_IDS), 'artworkCount': images['count'],
        'snapshot': revised['snapshots'][PLUGIN],
        'unchangedAgenticVaultSnapshot': snapshots['agentic-vault'],
    }


def registry_av_rows(registry):
    return sum(len(use['evidence']) for _, use in _plugin_uses(registry, 'agentic-vault'))


# Exact, guarded, idempotent edits of the two tracked tests that the update would otherwise break, written against
# the files at a3fb1d0 (all 172 sources illustrated, including the four v0.50.0 covers). Earlier helpers' edits stay
# in place. The new coverage line follows the agentic-vault v0.50.0 line; the declarations follow pinnedFile.
def _tuple(values):
    return '(' + ','.join(str(value) for value in values) + ')'


_FALLBACKS = ''.join(f"  ['{row[0]}','{row[1]}']{',' if index < len(REFERENCES) - 1 else ''}\n"
                     for index, row in enumerate(REFERENCES))
_DELTA = _tuple(b - a for a, b in zip(PRIOR_TUPLE, EXPECTED_TUPLE))
TEST_EDITS = (
    ('tests/test_delivery.py',
     f"    ('{AV_TAG}','{PRIOR_TAG}'):{_tuple(PRIOR_TUPLE)},\n",
     f"    ('{AV_TAG}','{PRIOR_TAG}'):{_tuple(PRIOR_TUPLE)},\n    ('{AV_TAG}','{TAG}'):{_tuple(EXPECTED_TUPLE)},\n"),
    ('tests/test_delivery.py',
     f"                      '{PRIOR_TAG}':{_tuple(PRIOR_SXC)}}}\n",
     f"                      '{PRIOR_TAG}':{_tuple(PRIOR_SXC)},\n"
     f"                      '{TAG}':{_tuple(EXPECTED_SXC)}}}\n"),
    ('tests/test_delivery.py',
     "\nif __name__=='__main__':unittest.main()\n",
     "\n    def test_sxc027_coverage_adds_six_cards_and_ten_citations_without_rewriting_history(self):\n"
     f"        prior=EXPECTED_COVERAGE[('{AV_TAG}','{PRIOR_TAG}')]\n"
     f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
     f"        revised=EXPECTED_COVERAGE[('{AV_TAG}','{TAG}')]\n"
     f"        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),{_DELTA})\n"
     "\nif __name__=='__main__':unittest.main()\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/')"
     ".replace(new RegExp('#L[0-9]+$'),'');\n",
     "const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/')"
     ".replace(new RegExp('#L[0-9]+$'),'');\n"
     "const sxcCatalogVersion=catalog.snapshots['semantic-crosscheck'].version;\n"
     "// Sources first cited by semantic-crosscheck v0.27.0, with their kinds; they use the text fallback until\n"
     "// artwork is commissioned.\n"
     "const sxc027TextFallbacks=new Map([\n" + _FALLBACKS + "]);\n"
     "const declaredSxc027TextFallback=source=>sxc027TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('all 172 catalog sources have their own commissioned image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,172);\n"
     "  assert.equal(catalog.sources.length,172);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    const art=sourceArtwork(source);\n",
     "test('all 172 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,172);\n"
     "  assert.equal(catalog.sources.filter(source=>!declaredSxc027TextFallback(source)).length,172);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    if(declaredSxc027TextFallback(source)) continue;\n"
     "    const art=sourceArtwork(source);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length,catalog.sources.length);\n});\n",
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length+catalog.sources.filter(declaredSxc027TextFallback).length,"
     "catalog.sources.length);\n});\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('the four formerly uncommissioned v0.50.0 sources render their exact separate images',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks,[]);\n",
     "test('the four formerly uncommissioned v0.50.0 sources render their exact separate images',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)),[]);\n"),
    # The v0.24 sources stay published at every later semantic-crosscheck snapshot.
    ('tests/artwork-uniqueness.test.mjs',
     f"  const published=catalog.snapshots['semantic-crosscheck'].version==='{PRIOR_TAG}';\n",
     f"  const published=['{PRIOR_TAG}','{TAG}'].includes(catalog.snapshots['semantic-crosscheck'].version);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "    assert.ok(!cover.includes('Future <source>'));\n  }\n});\n",
     "    assert.ok(!cover.includes('Future <source>'));\n  }\n});\n\n"
     f"test('only the declared semantic-crosscheck {TAG} sources render the uncommissioned text fallback',()=>{{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)),[]);\n"
     f"  if(sxcCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(fallbacks,[]);\n"
     f"  if(sxcCatalogVersion==='{TAG}') for(const id of sxc027TextFallbacks.keys())\n"
     "    assert.ok(catalog.sources.some(source=>source.id===id),`Missing catalog source: ${id}`);\n"
     "  for(const id of fallbacks){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,sxc027TextFallbacks.get(id));\n"
     "    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);\n"
     "    for(const detail of [false,true]){\n"
     "      const html=artworkCover(source,{detail});\n"
     "      assert.ok(html.includes('is-art-fallback'));\n"
     "      assert.ok(!html.includes('<img data-source-artwork'));\n"
     "    }\n"
     "  }\n"
     "});\n"),
)
TEST_FILES = tuple(dict.fromkeys(edit[0] for edit in TEST_EDITS))


def edit_tests(texts):
    """Apply each edit once; an edit whose result is already present is skipped. Returns (texts, edits applied)."""
    out, applied = dict(texts), 0
    for file, old, new in TEST_EDITS:
        text = out[file]
        if text.count(new) == 1:
            continue
        if text.count(old) != 1:
            raise ValueError('Test edit anchor needs exactly one match: ' + file)
        out[file] = text.replace(old, new)
        applied += 1
    return out, applied


def _git(plugin_root, *parts):
    return subprocess.check_output(['git', '-C', str(plugin_root), *parts],
                                   stderr=subprocess.DEVNULL).decode('utf-8')


def verify_tag(plugin_root, commit, tag=TAG):
    _validate_revision(commit, tag)
    if _git(plugin_root, 'cat-file', '-t', commit).strip() != 'commit':
        raise ValueError('Exact commit is not present locally')
    if _git(plugin_root, 'cat-file', '-t', 'refs/tags/' + tag).strip() != 'tag':
        raise ValueError('An annotated release tag is required')
    if _git(plugin_root, 'rev-parse', 'refs/tags/' + tag + '^{commit}').strip() != commit:
        raise ValueError('Release tag differs from the supplied exact commit')


def run(args):
    if not args.stand_in:
        verify_tag(args.plugin_root, args.commit, args.tag)
    elif _git(args.plugin_root, 'cat-file', '-t', args.commit).strip() != 'commit':
        raise ValueError('Stand-in commit is not present locally')
    cache = {}

    def read_lines(file):
        # Split on newlines only so line numbers match the GitHub blob view.
        if file not in cache:
            try:
                cache[file] = _git(args.plugin_root, 'show', args.commit + ':' + file).split('\n')
            except subprocess.CalledProcessError:
                raise LookupError('File absent from the supplied commit: ' + file) from None
        return cache[file]

    def grep_files(text):
        found = subprocess.run(['git', '-C', str(args.plugin_root), 'grep', '-z', '-l', '-I', '-i',
                                '-F', '-e', text, args.commit, '--'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if found.returncode not in (0, 1):
            raise ValueError('Git reference lookup failed')
        return [name[len(args.commit) + 1:] for name in found.stdout.decode('utf-8').split('\0')
                if name.startswith(args.commit + ':')]

    def url_index(url):
        identity = canonical_key(url)['key']
        index = {file: naming_lines(identity, read_lines(file)) for file in grep_files(grep_key(url))}
        return {file: lines for file, lines in index.items() if lines}

    root = args.atlas_root.resolve()
    source, art = root / 'data/registry.source.json', root / 'docs/card-artwork-unique-prompts.json'
    before = {path: path.read_bytes() for path in (source, art)}
    registry, artwork = (json.loads(before[path].decode('utf-8')) for path in (source, art))
    binding = verify_images(root, artwork)
    revised, images, summary = prepare_update(registry, artwork, read_lines, args.commit, args.tag,
                                               url_index=url_index)
    if verify_images(root, images) != binding:
        raise ValueError('Artwork image binding changed')
    # Where the plugin names each uncatalogued address (fixed text, case-insensitive), for the report only.
    for entry in summary['notCatalogued']:
        needle = entry['url'].split('://', 1)[1].lower()
        entry['lines'] = [f'{file}#L{number}' for file in sorted(grep_files(needle))
                          for number, text in enumerate(read_lines(file), 1) if needle in text.lower()]
    test_paths = {file: root / file for file in TEST_FILES}
    texts = {file: path.read_bytes().decode('utf-8') for file, path in test_paths.items()}
    edited, test_edits = edit_tests(texts)
    if any(path.read_bytes() != raw for path, raw in before.items()):
        raise ValueError('Atlas inputs changed during preparation')
    if args.apply:
        if revised != registry or images != artwork:
            write_update([(source, revised), (art, images)])
        for file, path in test_paths.items():
            if edited[file] != texts[file]:
                path.write_bytes(edited[file].encode('utf-8'))
    print(json.dumps({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
                      'publishable': not args.stand_in and args.public_verified,
                      'publicAvailability': 'caller asserted' if args.public_verified else 'not verified by this helper',
                      'standIn': args.stand_in, 'existingArtworkBindingSha256': binding,
                      'testEditsApplied': test_edits, 'testFilesEdited': sorted(f for f in texts if edited[f] != texts[f]),
                      **summary}, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True, help='Exact public commit that the annotated v0.27.0 tag names')
    parser.add_argument('--tag', default=TAG)
    parser.add_argument('--atlas-root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--public-verified', action='store_true',
                        help='Caller verified that the commit, tag and cited files are public')
    parser.add_argument('--stand-in', action='store_true', help='Dry run without the tag check; never publishable')
    args = parser.parse_args(argv)
    try:
        _validate_revision(args.commit, args.tag)
    except ValueError as error:
        parser.error(str(error))
    if args.apply and (not args.public_verified or args.stand_in):
        parser.error('--apply requires --public-verified and cannot use --stand-in')
    if args.stand_in and args.public_verified:
        parser.error('--stand-in is never publishable or public-verified')
    try:
        return run(args)
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError, UnicodeError, LookupError) as error:
        message = 'Local Git verification failed' if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
