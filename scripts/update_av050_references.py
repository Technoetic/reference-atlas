"""Offline, dry-run-first agentic-vault v0.50.0 reference update from exact Git blobs.

Adds the four sources of the v0.50.0 release note's research table (a video on
Git at scale and the Anthropic, OpenAI and GitHub posts it introduces) and
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
TAG, PRIOR_TAG, SXC_TAG = 'v0.50.0', 'v0.49.0', 'v0.24.0'
RELEASE = 'docs/releases/v0.50.0.md'
RECORD = 'docs/verification/v0.50.0.md'

VIDEO = 'https://www.youtube.com/watch?v=iysCcCRKZA4'
ANTHROPIC = 'https://www.anthropic.com/research/redesigning-source-control'
OPENAI = 'https://openai.com/index/scaling-git-at-openai/'
GITHUB = 'https://github.blog/engineering/infrastructure/inside-githubs-new-git-storage-architecture/'

FIRST = ('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog; the '
         'v0.50.0 release note says earlier repository documents did not cite any of its four sources (a git grep '
         'of the v0.49.0 tree found none). ')
RECORD_ROW = ('The release verification record attributes the research to the video and the three posts and states '
              'that their server-side designs were not adopted and their measured benefits are not claimed. ')
NO_CLAIM = ('This records a citation, not copied code, a runtime dependency or reproduced results; the effects '
            'the sources report are not claimed for the plugin.')
VIDEO_NOTE = (
    'A video by the YouTube channel 개발동생, published 2026-11-14 (the date the release note gives); the catalog '
    'has no video kind, so it is recorded as an article. The release note says it introduced how Anthropic, OpenAI '
    'and GitHub responded to Git at scale and that the presenter gave small teams three pieces of advice: a separate '
    'git worktree for each agent, cancelling the tests still running when a new commit reaches the same pull '
    'request, and intent-centred instead of line-by-line review. Release item 1 carries the second piece of advice '
    "into the repository's own CI: a workflow-level concurrency block cancels only earlier runs of the same pull "
    'request, and master, tag, candidate-branch and manual runs are not cancelled. The first piece of advice was '
    'already recommended by the existing concurrent-commits guide; release items 2 and 3 (an opt-in, read-only '
    'healthcheck of linked worktrees whose detached HEAD no local branch or tag contains, and guidance for landing '
    'linked-worktree work on master) were added to use that practice safely, and the release note states that they '
    "are not the presenter's proposals. The third piece of advice is left to the existing task contracts, unchanged. ")
ANTHROPIC_NOTE = (
    'Anthropic research post, published 2026-10-13 and updated 2026-10-15 (post header, read 2026-11-15). The release note says it describes Scion, an in-house source control system in '
    'which the server takes over commits and computation on the premise that clients are always online, and quotes '
    'the authors: "Scion is by no means a suitable replacement for git for general use." Not adopted: the release '
    'read it as grounds for keeping local git, hooks and mirrors, and names vault_commit.py --own-lines (a commit of '
    "a session's own changes built on HEAD without the shared index, moving the branch only if HEAD has not changed "
    'in the meantime) as the closest existing feature. The release note says the server-side designs do not fit the '
    "plugin's scale, a vault shared by several sessions on one computer. ")
OPENAI_NOTE = (
    'OpenAI engineering article, published 2026-11-02 (header of the Korean edition, read 2026-11-15). The release note describes it as a case that built a new server behind the repository '
    'without changing how Git is used (Pando), and says it was read only as context and not adopted. ')
GITHUB_NOTE = (
    'GitHub engineering blog post, published 2026-11-05 (post header, read 2026-11-15). The release note describes a storage layer that orders updates per reference '
    'so that pushes to different branches do not wait for each other, quoting "When two pushes do update the same '
    'reference, only one will append to the log.", and says it was read only as context and not adopted. ')


def _source(url, title, year, aliases, role, note):
    # The release citation comes first; each text must appear on exactly one line that names the source.
    return (canonical_key(url)['key'], 'article', title, url, year, aliases, role,
            FIRST + note + RECORD_ROW + NO_CLAIM, ((RELEASE, '(' + url + ')'), (RECORD, url)))


# id, kind, title, url, year, aliases, role, note, ((file, text on exactly one line naming the source), ...)
REFERENCES = (
    _source(VIDEO, 'Git은 이러라고 만든 게 아님 | Scion & Pando', 2026, ['개발동생 영상'], 'reference', VIDEO_NOTE),
    _source(ANTHROPIC, 'Redesigning source control at Anthropic', 2026, ['Anthropic, Redesigning source control'],
            'background', ANTHROPIC_NOTE),
    _source(OPENAI, 'Scaling Git at OpenAI', 2026, ['OpenAI, Scaling Git at OpenAI'], 'background', OPENAI_NOTE),
    _source(GITHUB, "Inside GitHub's new Git storage architecture", 2026,
            ["GitHub, Inside GitHub's new Git storage architecture"], 'background', GITHUB_NOTE),
)
NEW_IDS = [row[0] for row in REFERENCES]
NEW_CITATIONS = sum(len(row[8]) for row in REFERENCES)
# The published catalog this update starts from: agentic-vault v0.49.0 with semantic-crosscheck v0.24.0 and all
# 168 sources illustrated (public main 3d4b505).
BASE = {'total': 168, 'citations': 308, 'av': 242}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE = (56, 57, 18, 168, 308)
EXPECTED_TUPLE = (56, 57, 22, 172, 316)


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
            raise ValueError(f"Expected the published v0.49.0 baseline of {BASE['total']} sources and "
                             f"{BASE['citations']} citations ({BASE['av']} agentic-vault)")
    elif version != TAG or present != set(NEW_IDS):
        raise ValueError('Unexpected or partial agentic-vault reference snapshot ' + str(version))
    if registry['snapshots']['semantic-crosscheck']['version'] != SXC_TAG:
        raise ValueError('Expected the semantic-crosscheck ' + SXC_TAG + ' snapshot')
    # Each key names one work. A hit under another id needs a reviewed merge, not a second card.
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
    # Existing records keep kind, title, url, year, note, keys, aliases, tags, roles, files and excerpts.
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
        raise ValueError('Uncommissioned v0.50.0 sources must use text fallback')
    return revised, images, {
        'addedSourceIds': added, 'newCitationRows': NEW_CITATIONS, 'repinnedRowsTotal': count,
        'priorAgenticVaultCitationsRepinned': count - (NEW_CITATIONS if version == TAG else 0),
        'remappedLines': moved, 'counts': counts, 'agenticVaultCounts': av, 'coverageTuple': list(coverage),
        'agenticVaultRows': av_rows(revised), 'citedAddressLines': occurrences, 'testLinesNotCited': unlisted,
        'generatedCopyLines': copied, 'uncommissionedSourceIds': list(NEW_IDS), 'artworkCount': images['count'],
        'snapshot': revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot': registry['snapshots']['semantic-crosscheck'],
    }


# Exact, guarded, idempotent edits of the two tracked tests that the update would otherwise break. Earlier edits
# (the v0.48.0 helper's and the v0.49.0 lines) stay in place; the new coverage line follows the v0.49.0 line.
def _tuple(values):
    return '(' + ','.join(str(value) for value in values) + ')'


_FALLBACK_IDS = ''.join(f"  '{identity}'{',' if index < len(NEW_IDS) - 1 else ''}\n"
                        for index, identity in enumerate(NEW_IDS))
TEST_EDITS = (
    ('tests/test_delivery.py',
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n",
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n    ('{TAG}','{SXC_TAG}'):{_tuple(EXPECTED_TUPLE)},\n"),
    ('tests/test_delivery.py',
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,1,0,1,5))\n",
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,1,0,1,5))\n\n"
     "    def test_v050_coverage_adds_four_article_cards_and_eight_citations_without_rewriting_history(self):\n"
     f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','{SXC_TAG}')]\n"
     f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
     f"        revised=EXPECTED_COVERAGE[('{TAG}','{SXC_TAG}')]\n"
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),"
     f"{_tuple(b - a for a, b in zip(PRIOR_TUPLE, EXPECTED_TUPLE))})\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "const avCatalogVersion=catalog.snapshots['agentic-vault'].version;\n",
     "const avCatalogVersion=catalog.snapshots['agentic-vault'].version;\n"
     "// Sources first cited by agentic-vault v0.50.0; they use the text fallback until artwork is commissioned.\n"
     "const av050TextFallbacks=new Set([\n" + _FALLBACK_IDS + "]);\n"
     "const declaredTextFallback=source=>av050TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('all 168 current catalog sources have their own commissioned image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,168);\n"
     "  assert.equal(catalog.sources.length,168);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    const art=sourceArtwork(source);\n",
     "test('all 168 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,168);\n"
     "  assert.equal(catalog.sources.filter(source=>!declaredTextFallback(source)).length,168);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    if(declaredTextFallback(source)) continue;\n"
     "    const art=sourceArtwork(source);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length,catalog.sources.length);\n});\n",
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length+catalog.sources.filter(declaredTextFallback).length,catalog.sources.length);\n});\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('no current catalog source remains on the uncommissioned text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks,[]);\n});\n",
     "test('only the declared v0.50.0 sources render the uncommissioned text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!av050TextFallbacks.has(id)),[]);\n"
     f"  if(avCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(fallbacks,[]);\n"
     "  for(const id of fallbacks){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,'article');\n"
     "    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);\n"
     "    for(const detail of [false,true]){\n"
     "      const html=artworkCover(source,{detail});\n"
     "      assert.ok(html.includes('is-art-fallback'));\n"
     "      assert.ok(!html.includes('<img data-source-artwork'));\n"
     "    }\n"
     "  }\n});\n"),
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
        # Split on newlines only so line numbers match the GitHub blob view.
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
    parser.add_argument('--commit', required=True, help='Exact public commit that the annotated v0.50.0 tag names')
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
