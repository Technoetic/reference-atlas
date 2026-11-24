"""Add the agentic-vault v0.57.0 reference (ai3inc/opentoolsearch) and repin earlier uses from the exact plugin tree."""
import argparse
from datetime import datetime, timezone
from functools import cache
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources
from reference_identity import canonical_key, validate_catalog
from update_av048_references import PREFIX, excerpt_of, repin
from update_av0521_references import ARTWORK, CATALOG_CSV, CATALOG_JSON, REGISTRY, built_catalog, encode, write_files


ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.57.0'
PRIOR_VERSION = 'v0.56.0'
PRIOR_COMMIT = 'de80d0bf7cd80ab73238ec17539909b44d52c2b3'
SXC_VERSION = 'v0.33.0'

NEW_SOURCES = [
    dict(
        url='https://github.com/ai3inc/opentoolsearch',
        other_urls=[],
        kind='project',
        title='ai3inc/opentoolsearch',
        year=2026,
        aliases=['opentoolsearch', 'OpenToolSearch'],
        tags=['메모리·검색', '평가·테스트', '검증'],
        note=(
            'ai3inc/opentoolsearch (v0.2.1, commit 7da656db3e57de95fb2bf5a89052430fb3dfdd46, Apache-2.0). '
            'Agentic Vault v0.57.0 selectively adapts five non-redundant Python standard-library-only patterns: '
            'flat and (language, scenario) stratified-macro 95% paired percentile bootstrap CIs plus deterministic '
            'SHA-256 2-fold cross-fitting (scripts/eval_stats.py, evaluate_recall.py --bootstrap-ci), cross-split '
            'near-duplicate query leakage auditing and isolated Markdown layout-invariance probing '
            '(scripts/eval_recall_hygiene.py, --check-split-leakage, --layout-invariance), fail-closed JSON-to-Markdown '
            'result table synchronization (scripts/sync_result_tables.py), multi-turn follow-up query framing guidance '
            'in commands/vault-recall.md, and opt-in Stage-2 single-choice candidate reranking via TypeSafe Jev or '
            'BizRouter with explicit __none__ abstention, optional stdlib z-score fusion, and external_candidates '
            'sidecar output (scripts/rerank_candidates.py). No neural embeddings/cross-encoders, persistent vector '
            'caches, MCP/OpenAI-SDK proxies, or NumPy/SciPy/PyTorch dependencies were adopted.'
        ),
        cites=[
            ('docs/releases/v0.57.0.md', 'https://github.com/ai3inc/opentoolsearch'),
            ('README.md', 'https://github.com/ai3inc/opentoolsearch'),
        ],
    ),
]


def _find_single_line(read_lines, file, commit, needle, label):
    lines = read_lines(file)
    matches = [(i, line) for i, line in enumerate(lines, 1) if needle in line]
    if len(matches) != 1:
        raise ValueError(f'Expected one citation of {label} in {file}, found {len(matches)}')
    number, line = matches[0]
    excerpt = excerpt_of(line)
    if sum(excerpt_of(other) == excerpt for other in lines) != 1:
        raise ValueError(f'Ambiguous evidence excerpt for {label} in {file}')
    return dict(file=file, line=number, url=f'{PREFIX}{commit}/{file}#L{number}', excerpt=excerpt)


def prepare(registry, artwork, commit, read_lines):
    av_snap = registry['snapshots']['agentic-vault']
    sxc_snap = registry['snapshots']['semantic-crosscheck']
    if sxc_snap['version'] != SXC_VERSION:
        raise ValueError(f'Expected semantic-crosscheck {SXC_VERSION}, got {sxc_snap["version"]}')
    if (av_snap['version'], av_snap['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'This update requires the published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]

    existing_ids = {s['id'] for s in registry['sources']}
    existing_keys = {k for s in registry['sources'] for k in s.get('keys', [s['id']])}
    added = {}
    for spec in NEW_SOURCES:
        keys = []
        for address in [spec['url'], *spec['other_urls']]:
            ident = canonical_key(address)
            if ident is None:
                raise ValueError(f'No canonical key for {address}')
            if ident['key'] not in keys:
                keys.append(ident['key'])
        sid = keys[0]
        if sid in existing_ids or any(k in existing_keys for k in keys):
            raise ValueError(f'Source or key already exists: {keys}')
        evidence = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        registry['sources'].append(dict(
            id=sid,
            kind=spec['kind'],
            title=spec['title'],
            url=spec['url'],
            year=spec['year'],
            keys=keys,
            aliases=spec['aliases'],
            tags=spec['tags'],
            note=spec['note'],
            uses=[dict(plugin='agentic-vault', role='reference', evidence=evidence)],
        ))
        existing_ids.add(sid)
        existing_keys.update(keys)
        added[sid] = len(evidence)

    av_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(rebound=prior_rows, moved=moved, added=added)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plugin', type=Path, help='Checkout containing the cited public commit')
    parser.add_argument('commit', help='Full plugin commit ID')
    parser.add_argument('--public-ref', default=f'refs/tags/{TAG}',
                        help='Ref already confirmed on the public plugin repository (defaults to the release tag)')
    parser.add_argument('--apply', action='store_true', help='Write the catalog from the verified public ref')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.commit):
        parser.error('Expected a full Git commit ID')

    def git(*parts):
        return subprocess.check_output(['git', '-C', str(args.plugin), *parts]).decode('utf-8')

    if args.apply and git('rev-parse', '--verify', '--end-of-options', f'{args.public_ref}^{{commit}}').strip() != args.commit:
        parser.error('The verified public ref must resolve to the supplied commit')

    @cache
    def read_lines(file):
        return git('show', f'{args.commit}:{file}').split('\n')

    registry = json.loads((ROOT / REGISTRY).read_text(encoding='utf-8'))
    artwork = json.loads((ROOT / ARTWORK).read_text(encoding='utf-8'))
    report = prepare(registry, artwork, args.commit, read_lines)
    encoded = encode(registry)
    catalog_json, catalog_csv = built_catalog(encoded)
    if args.apply:
        write_files({ROOT / REGISTRY: encoded, ROOT / ARTWORK: encode(artwork),
                     ROOT / CATALOG_JSON: catalog_json, ROOT / CATALOG_CSV: catalog_csv})
    print(json.dumps(dict(**report, applied=args.apply), ensure_ascii=False))


if __name__ == '__main__':
    main()
