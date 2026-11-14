"""Offline, dry-run-first agentic-vault v0.49.0 reference update.

Read only exact local Git blobs. Repin every prior agentic-vault citation and
add the release's Ouroboros reference lines. Existing metadata, independent
plugin uses and immutable artwork provenance stay unchanged. Uncommissioned
artwork uses the existing text fallback. No fetch, push, plugin change or
publication is performed. Apply requires a locally verified annotated release
tag and the caller's separate assertion that those exact bytes are public.
--stand-in skips the tag check for a nonpublishable dry run; it cannot apply.
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
from update_av048_references import (PREFIX, excerpt_of, generated_copies, grep_key,
    immutable_artwork, naming_lines, repin, verify_images, av_rows)

ROOT = Path(__file__).resolve().parents[1]
TAG, PRIOR_TAG = 'v0.49.0', 'v0.48.0'
RELEASE = 'docs/releases/v0.49.0.md'
IDENTITY, URL = 'github:q00/ouroboros', 'https://github.com/Q00/ouroboros'
UPSTREAM = '54dad8e1dd93aee31858bde72493cd7a0f938739'
BASE = {'total': 167, 'citations': 303, 'av': 237}
NOTE = (
    'The agentic-vault v0.49.0 release cites Ouroboros v0.60.0 at upstream commit ' + UPSTREAM +
    ' as a conceptual design reference: task provenance and explicit requirements, staged evaluation boundaries, '
    'and distinct success/stop conditions informed original Python standard-library task contracts, staged '
    'review data and bounded read-only improvement observations. This records an original implementation '
    'reference, not copied code, a runtime dependency, a reproduced benchmark or measured performance. '
    'The release also cites the upstream MIT license. Caller-declared observations, costs and confirmation '
    'labels do not establish execution truth, authenticated identity or permission.'
)


def _validate_revision(commit, tag):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected an exact lowercase 40-character commit and release tag ' + TAG)


def _shape(sources):
    shape = deepcopy(sources)
    for source in shape:
        for use in source['uses']:
            if use['plugin'] == 'agentic-vault':
                for row in use['evidence']:
                    row.pop('line', None)
                    row.pop('url', None)
    return shape


def prepare_update(registry, artwork, read_lines, commit, tag, *, url_index, updated_at=None):
    _validate_revision(commit, tag)
    before = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': before})
    version = registry['snapshots']['agentic-vault']['version']
    prior = next((source for source in registry['sources'] if source['id'] == IDENTITY), None)
    if version == PRIOR_TAG:
        counts = metrics(before)
        if prior is not None or (counts['total'], counts['citations'], av_rows(registry)) != (
                BASE['total'], BASE['citations'], BASE['av']):
            raise ValueError('Expected the complete published v0.48.0 baseline')
    elif version != TAG or prior is None:
        raise ValueError('Unexpected or partial agentic-vault reference snapshot')
    if canonical_key(URL)['key'] != IDENTITY:
        raise ValueError('Canonical source identity mismatch')
    if any(source['id'] != IDENTITY and IDENTITY in {source['id'], *source['keys']}
           for source in registry['sources']):
        raise ValueError('Existing source identity requires a reviewed merge')

    revised, images = deepcopy(registry), deepcopy(artwork)
    remapped, count, moved = repin(revised, read_lines, commit)
    lines = read_lines(RELEASE)
    locations = naming_lines(IDENTITY, lines)
    if not locations:
        raise ValueError('Release lacks an Ouroboros reference line')
    rows, covered = [], set()
    for line in locations:
        excerpt = excerpt_of(lines[line - 1])
        if sum(excerpt_of(text) == excerpt for text in lines) != 1:
            raise ValueError('New reference excerpt must identify one exact release line')
        rows.append({'file': RELEASE, 'line': line,
                     'url': f'{PREFIX}{commit}/{RELEASE}#L{line}', 'excerpt': excerpt})
        covered.add((RELEASE, line))
    named = {(file, line) for file, numbers in url_index(URL).items() for line in numbers}
    tests = {(file, line) for file, line in named if file.startswith('tests/')}
    copies = generated_copies(named, covered, read_lines)
    if named - covered - tests - copies or covered - named:
        raise ValueError('Every non-test source reference needs an exact release citation; uncovered: ' +
                         ', '.join(f'{file}#L{line}' for file, line in sorted(named - covered - tests - copies)))
    record = {'id': IDENTITY, 'kind': 'project', 'title': 'Ouroboros', 'url': URL, 'year': None,
              'keys': [IDENTITY], 'aliases': ['Q00/ouroboros', 'Ouroboros'], 'tags': [], 'note': NOTE,
              'uses': [{'plugin': 'agentic-vault', 'role': 'reference', 'evidence': rows}]}
    existing = next((source for source in revised['sources'] if source['id'] == IDENTITY), None)
    added = []
    if existing is None:
        revised['sources'].append(record)
        added.append(IDENTITY)
    elif existing != record:
        raise ValueError('Previously applied Ouroboros record differs; manual review required')
    revised['snapshots']['agentic-vault'] = {
        'name': 'Agentic Vault', 'version': TAG, 'commit': commit,
        'url': 'https://github.com/Technoetic/agentic-vault/tree/' + commit}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    if _shape(revised['sources'][:len(registry['sources'])]) != _shape(registry['sources']):
        raise ValueError('Existing source metadata changed beyond commit and line bindings')
    if revised['snapshots']['semantic-crosscheck'] != registry['snapshots']['semantic-crosscheck']:
        raise ValueError('Independent plugin snapshot changed')
    validate_catalog({**revised, 'sources': merge_sources(revised['sources'])})
    counts = metrics(merge_sources(revised['sources']))
    if (counts['total'], counts['citations'], av_rows(revised)) != (
            BASE['total'] + 1, BASE['citations'] + len(rows), BASE['av'] + len(rows)):
        raise ValueError('Unexpected reference coverage after update')
    for asset in images['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            if field not in asset:
                raise ValueError('Artwork current evidence field missing')
            if any(url.startswith(PREFIX) and url not in remapped for url in asset[field]):
                raise ValueError('Artwork URL is absent from prior citation map')
            asset[field] = [remapped.get(url, url) for url in asset[field]]
    if images['count'] != artwork['count'] or immutable_artwork(images) != immutable_artwork(artwork):
        raise ValueError('Immutable artwork provenance or assignments changed')
    if any(asset['sourceId'] == IDENTITY for asset in images['assets']):
        raise ValueError('Uncommissioned Ouroboros reference must use text fallback')
    return revised, images, {
        'addedSourceIds': added, 'newCitationRows': len(rows), 'repinnedRowsTotal': count,
        'priorAgenticVaultCitationsRepinned': count - (len(rows) if version == TAG else 0),
        'remappedLines': moved, 'counts': counts,
        'citedAddressLines': [f'{file}#L{line}' for file, line in sorted(covered)],
        'testLinesNotCited': [f'{file}#L{line}' for file, line in sorted(tests)],
        'generatedCopyLines': [f'{file}#L{line}' for file, line in sorted(copies)],
        'uncommissionedSourceIds': [IDENTITY], 'artworkCount': images['count'],
        'snapshot': revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot': registry['snapshots']['semantic-crosscheck'],
    }


def _git(plugin_root, *parts):
    return subprocess.check_output(['git', '-C', str(plugin_root), *parts],
                                   stderr=subprocess.DEVNULL).decode('utf-8')


def verify_tag(plugin_root, commit, tag):
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
        found = subprocess.run(['git', '-C', str(args.plugin_root), 'grep', '-z', '-l', '-I', '-i',
                                '-F', '-e', grep_key(url), args.commit, '--'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if found.returncode not in (0, 1):
            raise ValueError('Git reference lookup failed')
        files = [name[len(args.commit) + 1:] for name in found.stdout.decode('utf-8').split('\0')
                 if name.startswith(args.commit + ':')]
        return {file: naming_lines(IDENTITY, read_lines(file)) for file in files}
    root = args.atlas_root.resolve()
    source, art = root / 'data/registry.source.json', root / 'docs/card-artwork-unique-prompts.json'
    before = {path: path.read_bytes() for path in (source, art)}
    registry, artwork = (json.loads(before[path].decode('utf-8')) for path in (source, art))
    binding = verify_images(root, artwork)
    revised, images, summary = prepare_update(registry, artwork, read_lines, args.commit,
                                               args.tag, url_index=url_index)
    if verify_images(root, images) != binding:
        raise ValueError('Artwork image binding changed')
    if any(path.read_bytes() != raw for path, raw in before.items()):
        raise ValueError('Atlas inputs changed during preparation')
    if args.apply and (revised != registry or images != artwork):
        write_update([(source, revised), (art, images)])
    print(json.dumps({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
                      'publishable': not args.stand_in and args.public_verified,
                      'publicAvailability': 'caller asserted' if args.public_verified else 'not verified by this helper',
                      'standIn': args.stand_in, 'existingArtworkBindingSha256': binding, **summary},
                     ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--atlas-root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--public-verified', action='store_true')
    parser.add_argument('--stand-in', action='store_true')
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
