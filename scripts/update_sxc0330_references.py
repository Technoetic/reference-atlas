"""Add the semantic-crosscheck v0.33.0 shared reference to ai3inc/foldboost and repin earlier uses."""
import argparse
from datetime import datetime, timezone
from functools import cache
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources
from reference_identity import validate_catalog
from update_av048_references import excerpt_of
from update_av0521_references import ARTWORK, CATALOG_CSV, CATALOG_JSON, REGISTRY, built_catalog, encode, write_files
from update_sxc027_references import PLUGIN, PREFIX, repin


ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.33.0'
PRIOR_VERSION = 'v0.32.0'
PRIOR_COMMIT = '61abfc707a1930fd8c929a9c719bc964f5eca67d'
AV_VERSION = 'v0.56.0'

RELEASE = 'docs/releases/v0.33.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
PAIRED = 'docs/paired-release.md'

SHARED_UPDATES = [
    dict(
        id='github:ai3inc/foldboost',
        note=(
            'ai3inc/foldboost (v0.3.0, commit ff7ad2208cf52d7692d5d016ba5b788d782256c7, Apache-2.0). '
            'Agentic Vault v0.56.0 selectively adapts three Python standard-library-only patterns: '
            'pre-registered evaluation plan sealing with frozen_core_sha256 and dual-verdict post-hoc '
            'amendment disclosure (scripts/verify_eval_plan.py), manifest_sha256 seals and near_misses '
            'drift diagnostics in vault_install_state.py plus vault_doctor --coverage '
            '(vault_coverage_matrix.py), and opt-in activation / control zero-leakage audits '
            '(scripts/eval_activation.py, exit 70). Semantic Crosscheck v0.33.0 selectively adapts the '
            'same three non-redundant patterns across tools/paired_release.py (--seal-plan, '
            'frozen_core_sha256, dual-verdict amendment_audit, --strict-original, --check-activation '
            'exit 70), tools/run_paired_example.py (--with-activation), cube_run.py / cube_install.py '
            '(strict installed.json parsing, manifest_sha256, zero-path near_misses diagnostics), and '
            'coverage_matrix.py / doctor --coverage. No biomolecular/GPU/Triton adapters, .pth '
            'interpreter hooks, Unix-socket servers, NumPy dependencies, or upstream code were copied.'
        ),
        cites=[
            (RELEASE, 'https://github.com/ai3inc/foldboost'),
            (THIRD_PARTY, 'https://github.com/ai3inc/foldboost'),
            (PAIRED, 'https://github.com/ai3inc/foldboost'),
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
    sxc_snap = registry['snapshots'][PLUGIN]
    av_snap = registry['snapshots']['agentic-vault']
    if av_snap['version'] != AV_VERSION:
        raise ValueError(f'Expected agentic-vault {AV_VERSION}, got {av_snap["version"]}')
    if (sxc_snap['version'], sxc_snap['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'Expected published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]

    by_id = {s['id']: s for s in registry['sources']}
    shared_added = {}
    for spec in SHARED_UPDATES:
        sid = spec['id']
        if sid not in by_id:
            raise ValueError(f'Expected existing source {sid} for shared cross-plugin update')
        source = by_id[sid]
        if any(use['plugin'] == PLUGIN for use in source['uses']):
            raise ValueError(f'{sid} already has a {PLUGIN} use')
        evidence = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        source['uses'].append(dict(plugin=PLUGIN, role='reference', evidence=evidence))
        source['note'] = spec['note']
        shared_added[sid] = len(evidence)

    sxc_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(rebound=prior_rows, moved=moved, shared_added=shared_added)


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
