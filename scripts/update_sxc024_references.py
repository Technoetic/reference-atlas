"""Prepare v0.24.0 catalog citations from exact annotated-tag Git blobs.

Offline and dry-run by default. Public tag/release availability requires separate
verification by the caller. No plugin source, generated artwork or deployment is
created by this helper.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'semantic-crosscheck'
TAG = 'v0.24.0'
PREFIX = f'https://github.com/Technoetic/{PLUGIN}/blob/'
MATRIX = 'docs/mutation-matrix.md'
CORPUS = 'docs/join-aggregate-fixtures.md'
SPECS = (
    {'id': 'github:stryker-mutator/stryker-js', 'kind': 'project', 'title': 'StrykerJS',
     'url': 'https://github.com/stryker-mutator/stryker-js',
     'pin': 'https://github.com/stryker-mutator/stryker-js/blob/959127763e5bbe2eb65f5341a8161780d6d8a476/packages/api/schema/stryker-core.json#L499-L503',
     'aliases': ['StrykerJS', 'StrykerJS disableBail'], 'doc': MATRIX, 'role': 'reference',
     'note': 'Previously researched conceptual reference for optional bounded continued mutation observations in '
             'v0.24.0. Pins the v10.1.1 disableBail option at upstream commit '
             '959127763e5bbe2eb65f5341a8161780d6d8a476. Later observations do not change the authoritative '
             'first-detector verdict. No upstream code, JavaScript engine or runtime dependency is bundled.'},
    {'id': 'github:stryker-mutator/mutation-testing-elements', 'kind': 'format',
     'title': 'Mutation Testing Elements report schema',
     'url': 'https://github.com/stryker-mutator/mutation-testing-elements',
     'pin': 'https://github.com/stryker-mutator/mutation-testing-elements/blob/4b5b62cc6bf81f23dd9521447131abeb51f895db/packages/report-schema/src/mutation-testing-report-schema.json#L43-L100',
     'aliases': ['Mutation Testing Elements', 'Mutation Testing Report Schema'], 'doc': MATRIX,
     'role': 'reference',
     'note': 'Previously researched format reference for keeping execution coverage, observed detections and '
             'completed-test counts distinct in the v0.24.0 diagnostic matrix. Pins upstream '
             '4b5b62cc6bf81f23dd9521447131abeb51f895db. No schema is copied or format compatibility claimed; '
             'execution, errors and missing cells never imply detection.'},
    {'id': 'arxiv:2004.00481', 'kind': 'paper',
     'title': 'SPES: A Symbolic Approach to Proving Query Equivalence Under Bag Semantics',
     'url': 'https://arxiv.org/abs/2004.00481', 'pin': 'https://arxiv.org/abs/2004.00481v2',
     'aliases': ['SPES', 'SPES paper'], 'year': 2020, 'doc': CORPUS, 'role': 'reference',
     'note': 'Previously consulted paper, newly applied as conceptual bag-semantics background for the '
             'v0.24.0 independently authored bounded integer/text/NULL join and aggregate fixtures. '
             'Pins arXiv 2004.00481v2; 2020 is the registration-year hint, distinct from ICDE 2022 '
             'publication. No SPES proof, benchmark, or PostgreSQL/Cube equivalence claim is reproduced.'},
    {'id': 'github:georgia-tech-db/spes', 'kind': 'project', 'title': 'SPES repository',
     'url': 'https://github.com/georgia-tech-db/spes',
     'pin': 'https://github.com/georgia-tech-db/spes/tree/8049f98d8e64a5c2c43d1ed581e7d5b6e0a006e2',
     'aliases': ['SPES public repository'], 'doc': CORPUS, 'role': 'background',
     'note': 'Accompanying Apache-2.0 repository background, distinct from the SPES paper identity. '
             'Pins upstream 8049f98d8e64a5c2c43d1ed581e7d5b6e0a006e2. The independently authored '
             'v0.24.0 corpus uses no upstream code, examples or Java/Calcite/Z3 runtime stack.'},
)
NEW_IDS = {spec['id'] for spec in SPECS}


def _reviews(document, commit):
    if document is None:
        return {}
    if document.get('sxc_commit') != commit or not isinstance(document.get('reviews'), list):
        raise ValueError('Excerpt reviews must bind the exact sxc_commit')
    reviews = {}
    for row in document['reviews']:
        fields = ('source_id', 'file', 'old_excerpt', 'new_excerpt', 'reason')
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in fields):
            raise ValueError('Each excerpt review needs source, file, old/new excerpt and reason')
        key = (row['source_id'], row['file'], row['old_excerpt'])
        if key in reviews or row['old_excerpt'] == row['new_excerpt'] or len(row['new_excerpt']) > 220:
            raise ValueError('Duplicate or ineffective excerpt review')
        reviews[key] = row
    return reviews


def _cites(text, identity):
    for url in re.findall(r'https?://[^\s<>()`]+', text):
        key = canonical_key(url)
        if key and key['key'] == identity:
            return True
    return False


def _attach_pending(images, pending):
    if pending is None:
        return
    assets = pending.get('assets', [])
    if (pending.get('count') != 4 or len(assets) != 4
            or {a.get('sourceId') for a in assets} != NEW_IDS):
        raise ValueError('Pending commission must contain the four exact v0.24 source identities')
    by_spec = {s['id']: s for s in SPECS}
    for asset in assets:
        if (not re.fullmatch(r'media/cards/[A-Za-z0-9_-]+\.webp', asset.get('output', ''))
                or not re.fullmatch('[0-9a-f]{64}', asset.get('sha256', ''))
                or asset.get('dimensions') != [960, 640]
                or type(asset.get('bytes')) is not int or asset['bytes'] <= 0
                or type(asset.get('index')) is not int or asset['index'] <= 0
                or not isinstance(asset.get('prompt'), str) or not asset['prompt'].strip()
                or by_spec[asset['sourceId']]['pin'] not in asset.get('generationEvidenceUrls', [])):
            raise ValueError('Pending artwork needs safe paths, image metadata, prompt and exact public generation pin')
        existing = next((a for a in images['assets'] if a['sourceId'] == asset['sourceId']), None)
        if existing:
            if any(existing.get(k) != value for k, value in asset.items()):
                raise ValueError('Previously attached artwork differs from the pending commission')
        else:
            images['assets'].append(deepcopy(asset))
    for key in ('sourceId', 'output', 'sha256', 'index'):
        values = [a[key] for a in images['assets']]
        if len(values) != len(set(values)):
            raise ValueError('Artwork identity, path, actual hash and index must each be unique')
    images['count'] = len(images['assets'])


def prepare_update(registry, artwork, read_lines, commit, *, reviewed_excerpts=None, pending_artwork=None, updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact lowercase 40-character SXC commit required')
    merged = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': merged})
    old_by_id = {source['id']: source for source in merged}
    present = NEW_IDS & set(old_by_id)
    if present and present != NEW_IDS:
        raise ValueError('Partial v0.24 source update needs explicit review')
    if registry['snapshots'][PLUGIN]['version'] not in ('v0.21.1', TAG):
        raise ValueError('Unexpected SXC baseline; rebase this helper on the current catalog')
    for spec in SPECS:
        if canonical_key(spec['url'])['key'] != spec['id']:
            raise ValueError('New canonical identity mismatch')
        for source in merged:
            keys = {source['id'], *source['keys']}
            if source.get('url'):
                keys.add(canonical_key(source['url'])['key'])
            if spec['id'] in keys and source['id'] != spec['id']:
                raise ValueError('Existing identity/alias needs a reviewed merge: ' + spec['id'])
    ids = [asset['sourceId'] for asset in artwork['assets']]
    if (artwork['count'] != len(ids) or len(ids) != len(set(ids))
            or not set(ids) <= set(old_by_id) or not set(old_by_id) - NEW_IDS <= set(ids)):
        raise ValueError('Artwork must preserve unique assignments to every prior source')
    for asset in artwork['assets']:
        urls = [r['url'] for u in old_by_id[asset['sourceId']]['uses'] for r in u['evidence']]
        if (asset.get('evidenceUrls') != urls or asset.get('currentEvidenceUrls') != urls
                or not asset.get('generationEvidenceUrls')):
            raise ValueError('Artwork current citations and generation history must be intact')
    reviews = _reviews(reviewed_excerpts, commit)
    used_reviews = set()
    revised, images = deepcopy(registry), deepcopy(artwork)
    cache = {}
    def lines_for(file):
        if file not in cache:
            cache[file] = read_lines(file)
        return cache[file]
    count = repinned = moved = 0
    reviewed_changes = []
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin'] != PLUGIN:
                continue
            for row in use['evidence']:
                key = (source['id'], row['file'], row['excerpt'])
                review = reviews.get(key)
                review_key = key
                if review is None and registry['snapshots'][PLUGIN]['commit'] == commit:
                    completed = [(k, item) for k, item in reviews.items()
                                 if k[:2] == key[:2] and item['new_excerpt'] == row['excerpt']
                                 and row['url'] == f'{PREFIX}{commit}/{row["file"]}#L{row["line"]}']
                    if len(completed) > 1:
                        raise ValueError('Ambiguous previously applied excerpt reviews')
                    if completed:
                        review_key, review = completed[0]
                excerpt = review['new_excerpt'] if review else row['excerpt']
                matches = [i + 1 for i, text in enumerate(lines_for(row['file'])) if text.strip()[:220] == excerpt]
                if len(matches) != 1:
                    raise ValueError(f'Prior excerpt needs a unique exact match or explicit review: {source["id"]} / {row["file"]}')
                line = matches[0]
                url = f'{PREFIX}{commit}/{row["file"]}#L{line}'
                count += 1
                repinned += row['url'] != url
                moved += row['line'] != line
                if review:
                    used_reviews.add(review_key)
                    reviewed_changes.append({**review, 'url': url})
                row.update(line=line, url=url, excerpt=excerpt)
    if set(reviews) != used_reviews:
        raise ValueError('Unused excerpt review; refuse unrelated or stale approvals')
    added = 0
    for spec in SPECS:
        rows = []
        pin_found = False
        for file in ('THIRD_PARTY.md', spec['doc']):
            lines = lines_for(file)
            matches = [i + 1 for i, text in enumerate(lines) if _cites(text, spec['id'])]
            if len(matches) != 1:
                raise ValueError(f'Expected one exact canonical citation: {spec["id"]} / {file}')
            line = matches[0]
            # Exact pinned URL must be a whole URL, not an unrelated suffix/version.
            urls = re.findall(r'https?://[^\s<>()`]+', lines[line - 1])
            pin_found |= spec['pin'] in urls
            rows.append({'file': file, 'line': line, 'url': f'{PREFIX}{commit}/{file}#L{line}',
                         'excerpt': lines[line - 1].strip()[:220]})
        if not pin_found:
            raise ValueError('Missing exact upstream pin: ' + spec['id'])
        use = {'plugin': PLUGIN, 'role': spec['role'], 'evidence': rows}
        if spec['id'] in present:
            existing = [s for s in revised['sources'] if s['id'] == spec['id']]
            if (len(existing) != 1 or existing[0]['kind'] != spec['kind']
                    or canonical_key(existing[0]['url'])['key'] != spec['id']
                    or [u for u in existing[0]['uses'] if u['plugin'] == PLUGIN] != [use]):
                raise ValueError('Existing v0.24 identity or cited use differs: ' + spec['id'])
        else:
            source = {k: deepcopy(spec[k]) for k in ('id', 'kind', 'title', 'url', 'aliases', 'note')}
            source.update(year=spec.get('year'), keys=[spec['id']], tags=[], uses=[use])
            revised['sources'].append(source)
            added += len(rows)
    revised['snapshots'][PLUGIN] = {'name': 'Semantic Crosscheck', 'version': TAG, 'commit': commit,
                                  'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}'}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    final = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': final})
    by_id = {s['id']: s for s in final}
    _attach_pending(images, pending_artwork)
    for asset in images['assets']:
        urls = [r['url'] for u in by_id[asset['sourceId']]['uses'] for r in u['evidence']]
        asset.update(evidenceUrls=urls, currentEvidenceUrls=deepcopy(urls))
    return revised, images, {
        'priorSxcCitations': count, 'repinnedCitations': repinned, 'remappedLines': moved,
        'addedCitations': added, 'addedSourceIds': sorted(NEW_IDS - present),
        'counts': metrics(final), 'snapshot': revised['snapshots'][PLUGIN],
        'reviewedExcerptChanges': reviewed_changes,
        'artworkCount': images['count'],
        'pendingArtworkSourceIds': sorted(set(by_id) - {a['sourceId'] for a in images['assets']}),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', required=True, type=Path)
    parser.add_argument('--sxc-commit', required=True)
    parser.add_argument('--reviewed-excerpts', type=Path, help='Exact SHA-bound public excerpt replacements, with review reasons')
    parser.add_argument('--pending-artwork', type=Path, help='Attach the separately commissioned four-image manifest after public citation binding')
    parser.add_argument('--apply', action='store_true', help='Write source registry and current artwork citations; no publishing')
    args = parser.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}', args.sxc_commit):
        parser.error('--sxc-commit requires a full lowercase SHA')
    def git(*arguments):
        return subprocess.run(['git', '-C', str(args.plugin_root), *arguments],
                              capture_output=True, check=True).stdout.decode('utf8')
    if (git('cat-file', '-t', 'refs/tags/' + TAG).strip() != 'tag'
            or git('rev-parse', '--verify', 'refs/tags/' + TAG + '^{commit}').strip() != args.sxc_commit):
        raise ValueError('Exact annotated v0.24.0 tag must resolve to --sxc-commit')
    source_path = ROOT / 'data/registry.source.json'
    artwork_path = ROOT / 'docs/card-artwork-unique-prompts.json'
    reviews = json.loads(args.reviewed_excerpts.read_text(encoding='utf8')) if args.reviewed_excerpts else None
    pending = json.loads(args.pending_artwork.read_text(encoding='utf8')) if args.pending_artwork else None
    revised, images, summary = prepare_update(
        json.loads(source_path.read_text(encoding='utf8')),
        json.loads(artwork_path.read_text(encoding='utf8')),
        lambda file: git('show', args.sxc_commit + ':' + file).splitlines(),
        args.sxc_commit, reviewed_excerpts=reviews, pending_artwork=pending)
    if pending:
        for asset in pending['assets']:
            path = (ROOT / asset['output']).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError('Pending artwork resolves outside the Atlas checkout')
            data = path.read_bytes()
            if (len(data) != asset['bytes'] or hashlib.sha256(data).hexdigest() != asset['sha256']
                    or data[:4] != b'RIFF' or data[8:12] != b'WEBP'):
                raise ValueError('Actual pending WebP bytes do not match the commissioned manifest')
    if args.apply:
        write_update([(source_path, revised), (artwork_path, images)])
    print(json.dumps({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
                      'publicAvailability': 'caller must independently verify', **summary}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
