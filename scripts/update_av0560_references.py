"""Add the agentic-vault v0.55.0 and v0.56.0 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.56.0'
PRIOR_VERSION = 'v0.54.1'
PRIOR_COMMIT = '74a2776cec936cd2cce7274cc9f3cb29bacf0159'
SXC_VERSION = 'v0.32.0'

NEW_SOURCES = [
    dict(
        url='https://github.com/seulee26/stock-team-harness',
        other_urls=[],
        kind='project',
        title='seulee26/stock-team-harness',
        year=2026,
        aliases=['stock-team-harness'],
        tags=['보안·안전', '신뢰성', '검증'],
        note=(
            'seulee26/stock-team-harness (v2.4.0, commit d3b716d1, MIT). Agentic Vault v0.55.0 '
            'selectively adapts six non-redundant Python standard-library-only patterns: verification-date '
            'staleness and annual rollover warnings (checked-at-stale, review-by-passed) plus deterministic '
            'alias-collision lint in vault_lint_extensions.py, URL query credential/signature inspection '
            '(egress-url-secret) in vault_egress.py, read-only cloud-sync destination awareness and '
            'first-run capability summaries (vault_cloud_sync.py, vault_doctor --cloud-sync/--summary), '
            'optional ADR invalidation triggers, and unexplained conclusion-reversal review guidance. '
            'No finance/trading/tax domain modules, external code, or runtime dependencies were adopted.'
        ),
        cites=[
            ('docs/releases/v0.55.0.md', 'https://github.com/seulee26/stock-team-harness'),
            ('README.md', 'https://github.com/seulee26/stock-team-harness'),
        ],
    ),
    dict(
        url='https://github.com/ai3inc/foldboost',
        other_urls=[],
        kind='project',
        title='ai3inc/foldboost',
        year=2026,
        aliases=['foldboost', 'FoldBoost'],
        tags=['평가·테스트', '신뢰성', '검증'],
        note=(
            'ai3inc/foldboost (v0.3.0, commit ff7ad2208cf52d7692d5d016ba5b788d782256c7, Apache-2.0). '
            'Agentic Vault v0.56.0 selectively adapts three non-redundant Python standard-library-only '
            'patterns: pre-registered evaluation plan sealing with immutable frozen_core_sha256 and '
            'dual-verdict post-hoc amendment disclosure (scripts/verify_eval_plan.py), self-verifying '
            'manifest_sha256 seals and structured near_misses drift diagnostics in vault_install_state.py '
            'plus a read-only host/OS/adapter coverage matrix (vault_coverage_matrix.py, vault_doctor --coverage), '
            'and opt-in treatment activation / control zero-leakage silent no-op audits (scripts/eval_activation.py, '
            'exit 70, wired into evaluate_retrieval_backends.py and evaluate_tool_matrix.py via --check-activation). '
            'No biomolecular/GPU/Triton adapters, .pth interpreter hooks, Unix-socket servers, or NumPy dependencies were adopted.'
        ),
        cites=[
            ('docs/releases/v0.56.0.md', 'https://github.com/ai3inc/foldboost'),
            ('README.md', 'https://github.com/ai3inc/foldboost'),
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
