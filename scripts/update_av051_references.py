"""Offline, dry-run-first agentic-vault v0.51.0 reference update from exact Git blobs.

Adds the two sources of the v0.51.0 release note's research table (the BizRouter
Decisions API documentation and the Artificial Analysis Decision Index page) and
repins every prior agentic-vault citation to the supplied commit, because the
catalog schema binds each citation of a plugin to that plugin's declared
snapshot. Each prior row keeps its file and excerpt; its line follows the
excerpt, which must occur exactly once in that file at the new revision.
Existing metadata, semantic-crosscheck uses and immutable artwork provenance
stay unchanged. Every non-test line of the plugin that names a new source must
be covered by one of that source's rows (test lines that pin the release
note's addresses are reported, not cited), so a citation added later stops the
helper instead of being left out. The new sources use the text fallback; no
image, prompt or interface is created, and the two tracked tests that count
catalog coverage and commissioned artwork receive exact, idempotent edits.

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
from update_av048_references import (PREFIX, av_rows, cited_rows, generated_copies, grep_key,
    immutable_artwork, naming_lines, repin, verify_images)

ROOT = Path(__file__).resolve().parents[1]
TAG, PRIOR_TAG, SXC_TAG = 'v0.51.0', 'v0.50.0', 'v0.27.0'
RELEASE = 'docs/releases/v0.51.0.md'

BIZROUTER = 'https://bizrouter.ai/docs/decisions'
DECISION_INDEX = 'https://artificialanalysis.ai/evaluations/decision-index'

FIRST = ('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog '
         '(a git grep of the v0.50.0 tree found none). Read 2026-11-16; the page may have changed since. ')
NO_CLAIM = ('This records a citation, not copied code, a default runtime dependency or reproduced results; '
            'external provider or benchmark numbers are not claimed for the plugin.')
BIZROUTER_NOTE = (
    'Public API documentation for BizRouter Decisions (POST https://api.bizrouter.ai/v1/decisions), which '
    'describes structured noul, choice and score judgment requests for google/gemini-decision-1 and '
    'typesafe/jev-1.13.0. The v0.51.0 release keeps TypeSafe Jev (jev_client.py) unchanged as the default '
    'provider and adds an opt-in standard-library adapter (skills/agentic-vault/scripts/bizrouter_client.py, '
    '--provider bizrouter) and selective low-confidence escalation (jev_ask.py --escalate-bizrouter), reusing '
    'jev_client.SENSITIVE secret filtering and vault_judge.py source binding. ')
DECISION_INDEX_NOTE = (
    'Public benchmark index page (Decision Index v2.1) reporting structured-judgment metrics, calibration and '
    'invariance characteristics across models including google/gemini-decision-1. The v0.51.0 release note '
    'states that it was consulted only as background context and that external benchmark scores are not claimed '
    "as the plugin's own performance. ")


def _source(url, title, year, aliases, role, note):
    return (canonical_key(url)['key'], 'article', title, url, year, aliases, role,
            FIRST + note + NO_CLAIM, ((RELEASE, '(' + url + ')'),))


# id, kind, title, url, year, aliases, role, note, ((file, text on exactly one line naming the source), ...)
REFERENCES = (
    _source(BIZROUTER, 'BizRouter Decisions API documentation', None,
            ['BizRouter Decisions API 문서'], 'reference', BIZROUTER_NOTE),
    _source(DECISION_INDEX, 'Artificial Analysis Decision Index', None,
            ['Google Gemini Decision 1 공개 벤치마크 색인', 'Decision Index v2.1'], 'background', DECISION_INDEX_NOTE),
)
NEW_IDS = [row[0] for row in REFERENCES]
NEW_CITATIONS = sum(len(row[8]) for row in REFERENCES)
# The published catalog this update starts from: agentic-vault v0.50.0 with semantic-crosscheck v0.27.0
# (public main 7b572a4: 178 sources, 326 citations, 172 commissioned images + 6 sxc v0.27.0 text fallbacks).
BASE = {'total': 178, 'citations': 326, 'av': 250}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE = (56, 57, 22, 178, 326)
EXPECTED_TUPLE = (56, 57, 24, 180, 328)


def _validate_revision(commit, tag):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected an exact lowercase 40-character commit and release tag ' + TAG)


def _locations(pairs):
    return [f'{file}#L{line}' for file, line in sorted(pairs)]


def _shape(sources):
    return [(s['id'], s['kind'], s['title'], s['url'], s.get('year'), s.get('note'), s['keys'], s['aliases'],
             s['tags'], [(u['plugin'], u['role'], [(r['file'], r['excerpt']) for r in u['evidence']])
                         for u in s['uses']]) for s in sources]


def prepare_update(registry, artwork, read_lines, commit, tag=TAG, *, url_index, updated_at=None):
    """url_index(url) -> {file: [line, ...]} of every line in the plugin revision that names the source."""
    _validate_revision(commit, tag)
    before = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': before})
    version = registry['snapshots']['agentic-vault']['version']
    present = set(NEW_IDS) & {source['id'] for source in registry['sources']}
    if version == PRIOR_TAG:
        counts = metrics(before)
        if present or (counts['total'], counts['citations'], av_rows(registry)) != (
                BASE['total'], BASE['citations'], BASE['av']):
            raise ValueError(f"Expected the published v0.50.0 baseline of {BASE['total']} sources and "
                             f"{BASE['citations']} citations ({BASE['av']} agentic-vault)")
    elif version != TAG or present != set(NEW_IDS):
        raise ValueError('Unexpected or partial agentic-vault reference snapshot ' + str(version))
    if registry['snapshots']['semantic-crosscheck']['version'] != SXC_TAG:
        raise ValueError('Expected the semantic-crosscheck ' + SXC_TAG + ' snapshot')
    for row in REFERENCES:
        if canonical_key(row[3])['key'] != row[0]:
            raise ValueError('Canonical source identity mismatch: ' + row[0])
        if any(source['id'] != row[0] and row[0] in {source['id'], *source['keys']}
               for source in registry['sources']):
            raise ValueError('Existing source identity requires a reviewed merge: ' + row[0])

    revised, images = deepcopy(registry), deepcopy(artwork)
    old_ids = [source['id'] for source in registry['sources']]
    old_shape = _shape(registry['sources'])
    old_sxc = [(s['id'], deepcopy(u)) for s in registry['sources'] for u in s['uses'] if u['plugin'] == 'semantic-crosscheck']
    remapped, count, moved = repin(revised, read_lines, commit)
    added, occurrences, copied, unlisted = [], {}, {}, {}
    for identity, kind, title, url, year, aliases, role, note, cites in REFERENCES:
        rows, covered = cited_rows(cites, read_lines, commit, identity)
        if rows[0]['file'] != RELEASE:
            raise ValueError('New reference lacks an exact release citation: ' + identity)
        named = {(file, line) for file, lines in url_index(url).items() for line in lines}
        tests = {(file, line) for file, line in named if file.startswith('tests/')}
        copies = generated_copies(named, covered, read_lines)
        uncovered = named - covered - tests - copies
        if uncovered or covered - named:
            raise ValueError(f'Every non-test line that names {url} needs its own row; uncovered: '
                             + ', '.join(_locations(uncovered)) + '; expected but absent: '
                             + ', '.join(_locations(covered - named)))
        occurrences[url], copied[url], unlisted[url] = _locations(covered), _locations(copies), _locations(tests)
        record = {'id': identity, 'kind': kind, 'title': title, 'url': url, 'year': year, 'keys': [identity],
                  'aliases': list(aliases), 'tags': [], 'note': note,
                  'uses': [{'plugin': 'agentic-vault', 'role': role, 'evidence': rows}]}
        prior = next((source for source in revised['sources'] if source['id'] == identity), None)
        if prior is None:
            revised['sources'].append(record)
            added.append(identity)
        elif prior != record:
            raise ValueError('Previously applied record differs; manual review required: ' + identity)
    revised['snapshots']['agentic-vault'] = {
        'name': 'Agentic Vault', 'version': TAG, 'commit': commit,
        'url': 'https://github.com/Technoetic/agentic-vault/tree/' + commit}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    kept = [source for source in revised['sources'] if source['id'] in old_ids]
    if [source['id'] for source in revised['sources']][:len(old_ids)] != old_ids or _shape(kept) != old_shape:
        raise ValueError('An existing record changed beyond its commit and line')
    if revised['snapshots']['semantic-crosscheck'] != registry['snapshots']['semantic-crosscheck'] or [
            (s['id'], u) for s in revised['sources'] for u in s['uses'] if u['plugin'] == 'semantic-crosscheck'] != old_sxc:
        raise ValueError('Unrelated semantic-crosscheck snapshot or use changed')
    counts = metrics(merged)
    av = metrics([s for s in merged if any(u['plugin'] == 'agentic-vault' for u in s['uses'])])
    coverage = (av['paper'], av['project'] + av['format'], av['article'], counts['total'], counts['citations'])
    if coverage != EXPECTED_TUPLE or av_rows(revised) != BASE['av'] + NEW_CITATIONS:
        raise ValueError(f'Unexpected coverage {coverage}; expected {EXPECTED_TUPLE}')
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
        raise ValueError('Uncommissioned v0.51.0 sources must use text fallback')
    return revised, images, {
        'addedSourceIds': added, 'newCitationRows': NEW_CITATIONS, 'repinnedRowsTotal': count,
        'priorAgenticVaultCitationsRepinned': count - (NEW_CITATIONS if version == TAG else 0),
        'remappedLines': moved, 'counts': counts, 'agenticVaultCounts': av, 'coverageTuple': list(coverage),
        'agenticVaultRows': av_rows(revised), 'citedAddressLines': occurrences, 'testLinesNotCited': unlisted,
        'generatedCopyLines': copied, 'uncommissionedSourceIds': list(NEW_IDS), 'artworkCount': images['count'],
        'snapshot': revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot': registry['snapshots']['semantic-crosscheck'],
    }


def _tuple(values):
    return '(' + ','.join(str(value) for value in values) + ')'


_FALLBACK_IDS = ''.join(f"  '{identity}'{',' if index < len(NEW_IDS) - 1 else ''}\n"
                        for index, identity in enumerate(NEW_IDS))
TEST_EDITS = (
    ('tests/test_delivery.py',
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n",
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n    ('{TAG}','{SXC_TAG}'):{_tuple(EXPECTED_TUPLE)},\n"),
    ('tests/test_delivery.py',
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,0,6,10))\n",
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,0,6,10))\n\n"
     "    def test_v051_coverage_adds_two_article_cards_and_two_citations_without_rewriting_history(self):\n"
     f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','{SXC_TAG}')]\n"
     f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
     f"        revised=EXPECTED_COVERAGE[('{TAG}','{SXC_TAG}')]\n"
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),"
     f"{_tuple(b - a for a, b in zip(PRIOR_TUPLE, EXPECTED_TUPLE))})\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "const declaredSxc027TextFallback=source=>sxc027TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n",
     "const declaredSxc027TextFallback=source=>sxc027TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"
     "// Sources first cited by agentic-vault v0.51.0; they use the text fallback until artwork is commissioned.\n"
     "const av051TextFallbacks=new Set([\n" + _FALLBACK_IDS + "]);\n"
     "const declaredAv051TextFallback=source=>av051TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"
     "const declaredAnyTextFallback=source=>declaredSxc027TextFallback(source)||declaredAv051TextFallback(source);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('all 172 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,172);\n"
     "  assert.equal(catalog.sources.filter(source=>!declaredSxc027TextFallback(source)).length,172);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    if(declaredSxc027TextFallback(source)) continue;\n"
     "    const art=sourceArtwork(source);\n",
     "test('all 172 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,172);\n"
     "  assert.equal(catalog.sources.filter(source=>!declaredAnyTextFallback(source)).length,172);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    if(declaredAnyTextFallback(source)) continue;\n"
     "    const art=sourceArtwork(source);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length+catalog.sources.filter(declaredSxc027TextFallback).length,catalog.sources.length);\n});\n",
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length+catalog.sources.filter(declaredAnyTextFallback).length,catalog.sources.length);\n});\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('the four formerly uncommissioned v0.50.0 sources render their exact separate images',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)),[]);\n",
     "test('the four formerly uncommissioned v0.50.0 sources render their exact separate images and only declared sxc027/av051 sources use text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)&&!av051TextFallbacks.has(id)),[]);\n"
     f"  if(avCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(fallbacks.filter(id=>av051TextFallbacks.has(id)),[]);\n"
     "  for(const id of fallbacks.filter(id=>av051TextFallbacks.has(id))){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,'article');\n"
     "    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);\n"
     "    for(const detail of [false,true]){\n"
     "      const html=artworkCover(source,{detail});\n"
     "      assert.ok(html.includes('is-art-fallback'));\n"
     "      assert.ok(!html.includes('<img data-source-artwork'));\n"
     "    }\n"
     "  }\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('only the declared semantic-crosscheck v0.27.0 sources render the uncommissioned text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)),[]);\n"
     "  if(sxcCatalogVersion==='v0.24.0') assert.deepEqual(fallbacks,[]);\n"
     "  if(sxcCatalogVersion==='v0.27.0') for(const id of sxc027TextFallbacks.keys())\n"
     "    assert.ok(catalog.sources.some(source=>source.id===id),`Missing catalog source: ${id}`);\n"
     "  for(const id of fallbacks){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,sxc027TextFallbacks.get(id));\n",
     "test('only the declared semantic-crosscheck v0.27.0 and agentic-vault v0.51.0 sources render the uncommissioned text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)&&!av051TextFallbacks.has(id)),[]);\n"
     "  if(sxcCatalogVersion==='v0.24.0'&&avCatalogVersion==='v0.50.0') assert.deepEqual(fallbacks,[]);\n"
     "  if(sxcCatalogVersion==='v0.27.0') for(const id of sxc027TextFallbacks.keys())\n"
     "    assert.ok(catalog.sources.some(source=>source.id===id),`Missing catalog source: ${id}`);\n"
     "  for(const id of fallbacks){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,sxc027TextFallbacks.get(id)||'article');\n"),
)
TEST_FILES = tuple(dict.fromkeys(edit[0] for edit in TEST_EDITS))


def edit_tests(texts):
    """Apply each edit once; an edit whose result is already present is skipped. Returns the files changed."""
    out = dict(texts)
    for file, old, new in TEST_EDITS:
        text = out[file]
        if text.count(new) == 1:
            continue
        if text.count(old) != 1:
            raise ValueError('Test edit anchor needs exactly one match: ' + file)
        out[file] = text.replace(old, new)
    return out, sum(out[file] != texts[file] for file in texts)


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
        if file not in cache:
            try:
                cache[file] = _git(args.plugin_root, 'show', args.commit + ':' + file).split('\n')
            except subprocess.CalledProcessError:
                raise LookupError('File absent from the supplied commit: ' + file) from None
        return cache[file]

    def url_index(url):
        identity = canonical_key(url)['key']
        found = subprocess.run(['git', '-C', str(args.plugin_root), 'grep', '-z', '-l', '-I', '-i',
                                '-F', '-e', grep_key(url), args.commit, '--'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if found.returncode not in (0, 1):
            raise ValueError('Git reference lookup failed')
        files = [name[len(args.commit) + 1:] for name in found.stdout.decode('utf-8').split('\0')
                 if name.startswith(args.commit + ':')]
        index = {file: naming_lines(identity, read_lines(file)) for file in files}
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
    parser.add_argument('--commit', required=True, help='Exact public commit that the annotated v0.51.0 tag names')
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
