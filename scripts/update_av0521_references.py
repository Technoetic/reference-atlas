"""Offline, dry-run-first agentic-vault v0.52.1 reference repin from exact Git blobs.

agentic-vault v0.52.1 supersedes v0.52.0, a candidate whose annotated tag stays
public but which was never released, and carries the candidate's whole change
set. This update therefore adds no source and no citation. It moves every
agentic-vault citation from the commit of the v0.52.0 tag to the supplied
commit, because the catalog schema binds each citation of a plugin to that
plugin's declared snapshot. Each row keeps its excerpt, which must occur
exactly once in the cited file at the new revision; its line follows the
excerpt. Two cases differ from a plain repin, and both are reported:

- A row that quotes the candidate's release note (docs/releases/v0.52.0.md)
  moves to the released note (docs/releases/v0.52.1.md) when its excerpt occurs
  exactly once there. Otherwise it stays on the candidate's note, provided the
  excerpt occurs exactly once there, and is listed.
- A row whose excerpt no longer occurs exactly once (the release edited,
  removed or repeated the quoted line) is never guessed. The helper stops with
  exit code 3, writes nothing and lists each such row with its excerpt and the
  closest lines of the files it searched. A replacement goes into
  REVIEWED_EXCERPTS only after review; a listed replacement for a row that
  still resolves stops the helper as well.

Only the v0.52.0 references are fixed here: 267 agentic-vault rows and the
agentic-vault part of the coverage tuple. The semantic-crosscheck snapshot and
the catalog's totals are read from the catalog the update starts from and kept,
so the helper also runs on a later catalog commit whose other plugin moved.

Record metadata, notes, roles, semantic-crosscheck uses and immutable artwork
provenance stay unchanged; the current evidence URLs of the artwork manifest
follow the rows. With --apply the helper also writes data/catalog.json and
data/catalog.csv exactly as scripts/build_catalog.py builds them from the
updated registry, and gives tests/test_delivery.py the v0.52.1 coverage line
and one history test (exact, idempotent insertions that keep every intact
insertion of an earlier catalog helper whole). All changed files are staged
first and replaced together.

No fetch, commit, push, publication or plugin change. Apply requires a locally
verified annotated release tag that names the commit and the caller's separate
assertion that those exact bytes are public. --stand-in skips the tag check
for a nonpublishable dry run; it cannot apply.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from build_catalog import build, merge_sources, metrics
from reference_identity import validate_catalog
from update_av048_references import PREFIX, av_rows, excerpt_of, immutable_artwork, verify_images

ROOT = Path(__file__).resolve().parents[1]
TAG, PRIOR_TAG = 'v0.52.1', 'v0.52.0'
# The commit that the public annotated tag v0.52.0 names. The catalog this update starts from pins every
# agentic-vault row to it; v0.52.1 is another commit.
PRIOR_COMMIT = '3dbee6a159dd5f21417fa52c222805d5081c9db0'
CANDIDATE_NOTE = 'docs/releases/v0.52.0.md'
RELEASE_NOTE = 'docs/releases/v0.52.1.md'
REGISTRY, ARTWORK = 'data/registry.source.json', 'docs/card-artwork-unique-prompts.json'
CATALOG_JSON, CATALOG_CSV = 'data/catalog.json', 'data/catalog.csv'
DELIVERY = 'tests/test_delivery.py'
ARTWORK_TEST = 'tests/artwork-uniqueness.test.mjs'
TEST_FILES = (DELIVERY, ARTWORK_TEST)
# The v0.52.0 references this update repins: the agentic-vault rows the public catalog recorded for v0.52.0 and the
# agentic-vault part (paper, project+format, article) of the coverage tuple of tests/test_delivery.py. The rest of the
# tuple (all sources, all citations) and the semantic-crosscheck snapshot come from the catalog the update starts from
# (public main 1aa4dee: 189 sources, 343 citations, semantic-crosscheck v0.27.0); a repin keeps them.
AV_ROWS = 267
AV_COVERAGE = (60, 57, 29)
SEMVER = re.compile(r'v\d+\.\d+\.\d+')
# Reviewed replacements for rows whose quoted line the release changed, each as
# (source id, file of the row before this update, excerpt before this update, excerpt at the tagged commit).
# Empty when every excerpt still occurs exactly once, which is the plain repin.
REVIEWED_EXCERPTS = ()


class UnresolvedRows(ValueError):
    """Rows whose excerpt does not occur exactly once at the new revision; .rows lists them for a decision."""

    def __init__(self, rows):
        self.rows = rows
        super().__init__(f'{len(rows)} agentic-vault row(s) cannot be repinned without a decision: '
                         + '; '.join(f"{row['sourceId']} / {row['file']}#L{row['line']}" for row in rows))


def _validate_revision(commit, tag):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected an exact lowercase 40-character commit and release tag ' + TAG)
    if commit == PRIOR_COMMIT:
        raise ValueError('The supplied commit is the commit of the v0.52.0 tag; v0.52.1 repins away from it')


def _closest(excerpt, files, lines_of, limit=3):
    """The lines of the searched files that are most similar to the excerpt, best first."""
    matcher = SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(excerpt)
    scored = []
    for file in files:
        for number, text in enumerate(lines_of(file) or [], 1):
            candidate = excerpt_of(text)
            if candidate:
                matcher.set_seq1(candidate)
                scored.append((matcher.quick_ratio(), file, number, candidate))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    exact = []
    for _, file, number, candidate in scored[:20]:
        matcher.set_seq1(candidate)
        exact.append((matcher.ratio(), file, number, candidate))
    exact.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [{'file': file, 'line': number, 'similarity': round(score, 3), 'excerpt': candidate}
            for score, file, number, candidate in exact[:limit]]


def repin_rows(revised, read_lines, commit):
    """Move every agentic-vault row to the commit, in place. Returns the URL map, the allowed changes and a report.

    The line follows the excerpt, which must occur exactly once in the row's file; a row on the candidate's release
    note looks in the released note first. Rows that cannot be placed raise UnresolvedRows together.
    """
    reviewed = {(identity, file, old): new for identity, file, old, new in REVIEWED_EXCERPTS}
    if len(reviewed) != len(REVIEWED_EXCERPTS) or not all(
            isinstance(value, str) and value and len(value) <= 220 and value == excerpt_of(value)
            for entry in REVIEWED_EXCERPTS for value in entry):
        raise ValueError('REVIEWED_EXCERPTS needs distinct rows and stripped excerpts of at most 220 characters')
    cache = {}

    def lines_of(file):
        if file not in cache:
            try:
                cache[file] = read_lines(file)
            except LookupError:
                cache[file] = None
        return cache[file]

    def found(files, excerpt):
        return {file: None if lines_of(file) is None else
                [number for number, text in enumerate(lines_of(file), 1) if excerpt_of(text) == excerpt]
                for file in files}

    def single(matches):
        return next((file for file, numbers in matches.items() if numbers is not None and len(numbers) == 1), None)

    remapped, changes, unresolved, used = {}, {}, [], set()
    report = {'rows': 0, 'urlsChanged': 0, 'locationsChanged': 0, 'moved': [], 'kept': [], 'excerptChanges': []}
    for i, source in enumerate(revised['sources']):
        for j, use in enumerate(source['uses']):
            if use['plugin'] != 'agentic-vault':
                continue
            for k, row in enumerate(use['evidence']):
                report['rows'] += 1
                old = dict(row)
                files = [RELEASE_NOTE, CANDIDATE_NOTE] if old['file'] == CANDIDATE_NOTE else [old['file']]
                excerpt, matches = old['excerpt'], found(files, old['excerpt'])
                where, key = single(matches), (source['id'], old['file'], old['excerpt'])
                if key in reviewed:
                    if where is not None:
                        raise ValueError('A reviewed excerpt is listed for a row that still resolves; remove it: '
                                         f"{source['id']} / {old['file']}#L{old['line']}")
                    used.add(key)
                    excerpt = reviewed[key]
                    where = single(found(files, excerpt))
                if where is None:
                    unresolved.append({
                        'sourceId': source['id'], 'file': old['file'], 'line': old['line'], 'excerpt': old['excerpt'],
                        'searched': [{'file': file, 'occurrences': None if numbers is None else len(numbers)}
                                     for file, numbers in matches.items()],
                        'reviewedExcerpt': reviewed.get(key),
                        'candidates': _closest(old['excerpt'], files, lines_of)})
                    continue
                line = found([where], excerpt)[where][0]
                row.update(file=where, line=line, url=f'{PREFIX}{commit}/{where}#L{line}', excerpt=excerpt)
                if remapped.get(old['url'], row['url']) != row['url']:
                    raise ValueError('Ambiguous prior citation map: ' + old['url'])
                remapped[old['url']] = row['url']
                report['urlsChanged'] += row['url'] != old['url']
                report['locationsChanged'] += (row['file'], row['line']) != (old['file'], old['line'])
                place = {'sourceId': source['id'], 'from': f"{old['file']}#L{old['line']}", 'to': f'{where}#L{line}'}
                if where != old['file']:
                    changes.setdefault((i, j, k), {})['file'] = where
                    # The candidate's note keeps the same line unless the release reworded it there.
                    again = matches[CANDIDATE_NOTE]
                    report['moved'].append({**place, 'candidateNoteLine': again[0] if again and len(again) == 1 else None})
                elif where == CANDIDATE_NOTE:
                    numbers = matches[RELEASE_NOTE]
                    report['kept'].append({**place, 'releaseNoteOccurrences': None if numbers is None else len(numbers)})
                if excerpt != old['excerpt']:
                    changes.setdefault((i, j, k), {})['excerpt'] = excerpt
                    report['excerptChanges'].append({**place, 'before': old['excerpt'], 'after': excerpt})
    if unresolved:
        raise UnresolvedRows(unresolved)
    report['reviewedExcerptsUnused'] = [
        {'sourceId': identity, 'file': file, 'excerpt': old} for identity, file, old, _ in REVIEWED_EXCERPTS
        if (identity, file, old) not in used]
    return remapped, changes, report


def _shape(sources, changes=None):
    """Everything a repin must keep: each record as it is, each agentic-vault row without its line and URL."""
    shape = deepcopy(sources)
    for i, source in enumerate(shape):
        for j, use in enumerate(source['uses']):
            if use['plugin'] != 'agentic-vault':
                continue
            for k, row in enumerate(use['evidence']):
                del row['line'], row['url']
                row.update((changes or {}).get((i, j, k), {}))
    return shape


def _coverage(merged):
    counts = metrics(merged)
    av = metrics([source for source in merged if any(use['plugin'] == 'agentic-vault' for use in source['uses'])])
    return counts, av, (av['paper'], av['project'] + av['format'], av['article'], counts['total'], counts['citations'])


def other_version(registry):
    """The semantic-crosscheck version of the catalog, the second half of the coverage key of tests/test_delivery.py."""
    version = registry['snapshots']['semantic-crosscheck']['version']
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError('Unexpected semantic-crosscheck snapshot version ' + repr(version))
    return version


def prepare_update(registry, artwork, read_lines, commit, tag=TAG, *, updated_at=None):
    """read_lines(file) -> the lines of the file at the commit, split on newlines only; LookupError when absent."""
    _validate_revision(commit, tag)
    before = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': before})
    snapshot = registry['snapshots']['agentic-vault']
    if snapshot['version'] == PRIOR_TAG:
        if snapshot['commit'] != PRIOR_COMMIT:
            raise ValueError('Expected the v0.52.0 snapshot at the commit of the public v0.52.0 tag')
    elif snapshot['version'] != TAG:
        raise ValueError('Unexpected agentic-vault reference snapshot ' + str(snapshot['version']))
    sxc_version = other_version(registry)
    counts, av, coverage = _coverage(before)
    if av_rows(registry) != AV_ROWS or coverage[:3] != AV_COVERAGE:
        raise ValueError(f'Expected the published v0.52.0 references: {AV_ROWS} agentic-vault rows and agentic-vault '
                         f'coverage {AV_COVERAGE}; found {av_rows(registry)} rows and {coverage[:3]}')

    revised, images = deepcopy(registry), deepcopy(artwork)
    remapped, changes, report = repin_rows(revised, read_lines, commit)
    revised['snapshots']['agentic-vault'] = {
        **snapshot, 'version': TAG, 'commit': commit,
        'url': 'https://github.com/Technoetic/agentic-vault/tree/' + commit}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    # A repin adds and removes nothing: the same records in the same order, every field as it was, each
    # agentic-vault row with its file and excerpt (but for the reported moves and reviewed excerpts).
    if list(revised) != list(registry) or any(
            revised[key] != registry[key] for key in registry if key not in ('updatedAt', 'snapshots', 'sources')):
        raise ValueError('Registry metadata changed')
    if _shape(revised['sources']) != _shape(registry['sources'], changes):
        raise ValueError('An existing record changed beyond the commit, line and reported file of its rows')
    if {plugin: value for plugin, value in revised['snapshots'].items() if plugin != 'agentic-vault'} != {
            plugin: value for plugin, value in registry['snapshots'].items() if plugin != 'agentic-vault'}:
        raise ValueError('Unrelated plugin snapshot changed')
    if [source['id'] for source in merged] != [source['id'] for source in before]:
        raise ValueError('The built catalog would list other sources or another order')
    if _coverage(merged) != (counts, av, coverage) or av_rows(revised) != AV_ROWS or report['rows'] != AV_ROWS:
        raise ValueError(f'Unexpected coverage {_coverage(merged)[2]}; a repin keeps {coverage}')
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
    return revised, images, {
        'addedSourceIds': [], 'newCitationRows': 0,
        'priorAgenticVaultCitationsRepinned': report['rows'], 'repinnedRowsTotal': report['rows'],
        'citationUrlsChanged': report['urlsChanged'], 'remappedLines': report['locationsChanged'],
        'movedToReleaseNote': report['moved'], 'keptOnCandidateNote': report['kept'],
        'excerptChanges': report['excerptChanges'], 'reviewedExcerptsUnused': report['reviewedExcerptsUnused'],
        'counts': counts, 'agenticVaultCounts': av, 'coverageTuple': list(coverage),
        'agenticVaultRows': av_rows(revised), 'artworkCount': images['count'],
        'previousSnapshot': snapshot, 'snapshot': revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot': registry['snapshots']['semantic-crosscheck'],
        'semanticCrosscheckVersion': sxc_version,
    }


# Exact, guarded, idempotent insertions into the tracked test that pins catalog coverage by snapshot versions. Earlier
# lines stay in place (the earlier helpers' tests read them): the v0.52.1 line follows the v0.52.0 line of the same
# semantic-crosscheck version with the same tuple, and one history test states that the repin changed no count.
def _tuple(values):
    return '(' + ','.join(str(value) for value in values) + ')'


MAIN_LINE = "\nif __name__=='__main__':unittest.main()\n"
# The last line of the v0.52.0 history test; the v0.52.1 test follows it unless that would split the intact insertion
# of a later helper, in which case it goes to the end of the test class (before the main line).
V052_HISTORY_END = "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(4,0,5,9,15))\n"


def delivery_insertions(sxc_version, coverage):
    """The coverage line (after its anchor line) and the history test block for this catalog."""
    if not SEMVER.fullmatch(str(sxc_version)) or len(coverage) != 5 or not all(
            isinstance(value, int) and value >= 0 for value in coverage):
        raise ValueError('Coverage insertions need a semantic-crosscheck version and five counts')
    anchor = f"    ('{PRIOR_TAG}','{sxc_version}'):{_tuple(coverage)},\n"
    line = f"    ('{TAG}','{sxc_version}'):{_tuple(coverage)},\n"
    history = ("\n    def test_v0521_repin_keeps_every_card_and_citation_without_rewriting_history(self):\n"
               f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','{sxc_version}')]\n"
               f"        self.assertEqual(prior,{_tuple(coverage)})\n"
               f"        revised=EXPECTED_COVERAGE[('{TAG}','{sxc_version}')]\n"
               "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,0,0,0))\n")
    return anchor, line, history


# The artwork test of the catalog pins the generation evidence of the ten images commissioned for the v0.52.0 and
# semantic-crosscheck v0.28.0 references to the current citations. A repin moves the citations but keeps the generation
# records (immutable provenance), so, as the v0.48.0 helper did for the v0.47.0 commissions, the assertion compares the
# generation URLs with the citations by file once the catalog has moved past v0.52.0; a row of the candidate's release
# note counts as the released note it moves to (the rule of repin_rows).
ARTWORK_PINNED = ("const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/')"
                  ".replace(new RegExp('#L[0-9]+$'),'');\n")
ARTWORK_RELEASED = ("const releasedFile=url=>pinnedFile(url).replace('/blob/<commit>/" + CANDIDATE_NOTE + "',"
                    "'/blob/<commit>/" + RELEASE_NOTE + "');\n")
ARTWORK_ASSERT = ("    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
                  "    assert.deepEqual(record.generationEvidenceUrls,citations);\n"
                  "    assert.deepEqual(record.delivery.sourceDimensions,[1536,1024]);\n")
ARTWORK_ASSERT_NEW = ("    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
                      f"    if(avCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(record.generationEvidenceUrls,citations);\n"
                      "    else assert.deepEqual(record.generationEvidenceUrls.map(releasedFile),"
                      "citations.map(releasedFile));\n"
                      "    assert.deepEqual(record.delivery.sourceDimensions,[1536,1024]);\n")


def edit_artwork_test(text, keep=()):
    """The two edits of the artwork test, each made once; an edit already present is skipped.

    keep: the intact insertions of earlier catalog helpers in this file; each must stay present exactly once.
    """
    if any(text.count(kept) != 1 for kept in keep):
        raise ValueError('A text to keep is not present exactly once before the artwork test edit')
    if text.count(ARTWORK_PINNED + ARTWORK_RELEASED) != 1:
        if text.count('const releasedFile=') or text.count(ARTWORK_PINNED) != 1:
            raise ValueError('Artwork test edit anchor needs exactly one match: the pinnedFile line and no other '
                             'releasedFile')
        text = text.replace(ARTWORK_PINNED, ARTWORK_PINNED + ARTWORK_RELEASED)
    if text.count(ARTWORK_ASSERT_NEW) != 1:
        if text.count(ARTWORK_ASSERT) != 1:
            raise ValueError('Artwork test edit anchor needs exactly one match: the generation evidence assertion of '
                             'the ten images commissioned for the v0.52.0 and v0.28.0 references')
        text = text.replace(ARTWORK_ASSERT, ARTWORK_ASSERT_NEW)
    if any(text.count(kept) != 1 for kept in keep):
        raise ValueError('The artwork test edit would split an earlier helper\'s insertion')
    return text


def edit_tests(texts, sxc_version, coverage, keep=(), keep_artwork=()):
    """Insert the v0.52.1 coverage line and history test once; an insertion already present is skipped.

    keep: texts (each present exactly once before the edit) that must stay present exactly once afterwards, i.e. the
    intact insertions of earlier catalog helpers. When texts holds the artwork test, its two edits are made as well
    (keep_artwork for its earlier insertions). Returns the texts and the number of files changed.
    """
    out = dict(texts)
    text = out[DELIVERY]
    if any(text.count(kept) != 1 for kept in keep):
        raise ValueError('A text to keep is not present exactly once before the edit')
    anchor, line, history = delivery_insertions(sxc_version, coverage)

    def kept(candidate):
        return all(candidate.count(item) == 1 for item in keep)
    # An insertion counts as made when its exact text stands once (and, for the line, its anchor too).
    if not (text.count(line) == 1 and text.count(anchor) == 1):
        if text.count(f"    ('{TAG}','"):
            raise ValueError('tests/test_delivery.py already holds another v0.52.1 coverage line')
        if text.count(anchor) != 1:
            raise ValueError('Test edit anchor needs exactly one match: the v0.52.0 coverage line of '
                             + sxc_version + ' with the tuple ' + _tuple(coverage))
        text = text.replace(anchor, anchor + line)
        if not kept(text):
            raise ValueError('The v0.52.1 coverage line would split an earlier helper\'s insertion')
    if text.count(history) != 1:
        if text.count('def test_v0521_'):
            raise ValueError('tests/test_delivery.py already holds another v0.52.1 history test')
        candidates = []
        if text.count(V052_HISTORY_END) == 1:
            candidates.append(text.replace(V052_HISTORY_END, V052_HISTORY_END + history))
        if text.count(MAIN_LINE) == 1 and text.endswith(MAIN_LINE):
            candidates.append(text.replace(MAIN_LINE, history + MAIN_LINE))
        if not candidates:
            raise ValueError('Test edit anchor needs exactly one match: the end of the v0.52.0 history test or the '
                             'main line')
        text = next((candidate for candidate in candidates if kept(candidate)), None)
        if text is None:
            raise ValueError('The v0.52.1 history test would split an earlier helper\'s insertion at every anchor')
    out[DELIVERY] = text
    if ARTWORK_TEST in out:
        out[ARTWORK_TEST] = edit_artwork_test(out[ARTWORK_TEST], keep_artwork)
    return out, sum(out[file] != texts[file] for file in texts)


def earlier_insertions(scripts, file, text):
    """The insertions of the other catalog helpers in scripts/ (TEST_EDITS entries of `file`) that are intact in text.

    Each helper is loaded by path under its own module name; no bytecode is written next to it.
    """
    found, saved = [], sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        for path in sorted(Path(scripts).glob('update_*_references.py')):
            if path.name == Path(__file__).name:
                continue
            spec = importlib.util.spec_from_file_location('earlier_' + path.stem, path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as error:
                raise ValueError('Cannot read the test edits of ' + path.name + ': ' + type(error).__name__) from None
            edits = getattr(module, 'TEST_EDITS', ())
            if not isinstance(edits, tuple):
                continue
            found += [entry[2] for entry in edits if isinstance(entry, tuple) and len(entry) == 3
                      and entry[0] == file and isinstance(entry[2], str) and text.count(entry[2]) == 1]
    finally:
        sys.dont_write_bytecode = saved
    return list(dict.fromkeys(found))


def encode(document):
    return (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode('utf8')


def built_catalog(registry_bytes):
    """data/catalog.json and data/catalog.csv as scripts/build_catalog.py builds them from this registry."""
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        (stage / 'data').mkdir()
        (stage / REGISTRY).write_bytes(registry_bytes)
        build(stage)
        return (stage / CATALOG_JSON).read_bytes(), (stage / CATALOG_CSV).read_bytes()


def write_files(files):
    """Stage every changed file beside its target, then replace them; restore the originals if a step fails.

    Failure recovery for an ordinary write error, not protection against power loss or concurrent editors.
    """
    originals = {path: path.read_bytes() for path in files}
    staged, replaced = {}, []

    def stage(path, content):
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.av0521-update-', suffix='.tmp',
                                         delete=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            return Path(stream.name)
    try:
        for path, content in files.items():
            staged[path] = stage(path, content)
        for path in files:
            if path.read_bytes() != originals[path]:
                raise OSError('Input file changed after preparation; apply aborted')
            os.replace(staged[path], path)
            replaced.append(path)
    except BaseException as failure:
        for path in reversed(replaced):
            if path.read_bytes() != files[path]:
                raise RuntimeError('Concurrent file change prevents automatic rollback; keep the worktree for '
                                   'manual recovery') from failure
            rollback = stage(path, originals[path])
            try:
                os.replace(rollback, path)
            except BaseException:
                raise RuntimeError(f'Rollback failed; original bytes preserved at {rollback.name}') from failure
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def _print(document, stream=None):
    """One JSON line; excerpts are escaped only when the console encoding cannot show them."""
    try:
        print(json.dumps(document, ensure_ascii=False), file=stream or sys.stdout)
    except UnicodeEncodeError:
        print(json.dumps(document), file=stream or sys.stdout)


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

    root = args.atlas_root.resolve()
    names = (REGISTRY, ARTWORK, CATALOG_JSON, CATALOG_CSV, *TEST_FILES)
    before = {name: (root / name).read_bytes() for name in names}
    # The generated files must be a build of the registry as it stands, so that their change is this update's alone.
    if built_catalog(before[REGISTRY]) != (before[CATALOG_JSON], before[CATALOG_CSV]):
        raise ValueError('data/catalog.json or data/catalog.csv is not a build of data/registry.source.json; '
                         'run scripts/build_catalog.py and review the difference first')
    registry, artwork = (json.loads(before[name].decode('utf-8')) for name in (REGISTRY, ARTWORK))
    binding = verify_images(root, artwork)
    revised, images, summary = prepare_update(registry, artwork, read_lines, args.commit, args.tag)
    if verify_images(root, images) != binding:
        raise ValueError('Artwork image binding changed')
    after = dict(before)
    if revised != registry:
        after[REGISTRY] = encode(revised)
    if images != artwork:
        after[ARTWORK] = encode(images)
    after[CATALOG_JSON], after[CATALOG_CSV] = built_catalog(after[REGISTRY])
    texts = {file: before[file].decode('utf-8') for file in TEST_FILES}
    keep = earlier_insertions(root / 'scripts', DELIVERY, texts[DELIVERY])
    keep_artwork = earlier_insertions(root / 'scripts', ARTWORK_TEST, texts[ARTWORK_TEST])
    edited, test_edits = edit_tests(texts, summary['semanticCrosscheckVersion'], summary['coverageTuple'], keep,
                                    keep_artwork)
    after.update((file, edited[file].encode('utf-8')) for file in TEST_FILES)
    changed = sorted(name for name in names if after[name] != before[name])
    if any((root / name).read_bytes() != raw for name, raw in before.items()):
        raise ValueError('Atlas inputs changed during preparation')
    if args.apply and changed:
        write_files({root / name: after[name] for name in changed})
    _print({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
            'publishable': not args.stand_in and args.public_verified,
            'publicAvailability': 'caller asserted' if args.public_verified else 'not verified by this helper',
            'standIn': args.stand_in, 'existingArtworkBindingSha256': binding,
            'filesChanged': changed, 'testEditsApplied': test_edits,
            'testFilesEdited': sorted(file for file in texts if edited[file] != texts[file]),
            'earlierInsertionsKept': len(keep), **summary})
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True, help='Exact public commit that the annotated v0.52.1 tag names')
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
    except UnresolvedRows as blocked:
        # Nothing was written. The rows go to standard output so that the caller's saved result holds them.
        _print({'status': 'BLOCKED', 'mode': 'apply refused' if args.apply else 'dry-run', 'standIn': args.stand_in,
                'message': str(blocked), 'unresolvedRows': blocked.rows})
        _print({'status': 'error', 'message': f'{len(blocked.rows)} agentic-vault row(s) need a decision; '
                'see unresolvedRows on standard output'}, sys.stderr)
        return 3
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError, UnicodeError, LookupError) as error:
        message = 'Local Git verification failed' if isinstance(error, subprocess.CalledProcessError) else str(error)
        _print({'status': 'error', 'message': message}, sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
