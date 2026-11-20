"""Add the agentic-vault v0.54.0 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.54.0'
PRIOR_VERSION = 'v0.53.0'
PRIOR_COMMIT = 'c0f4a3cb4547897ad3e38a8a663e3aaa390db31a'
RELEASE = 'docs/releases/v0.54.0.md'
HOOK_WIRING = 'skills/agentic-vault/scripts/vault_hook_wiring.py'
INSTALL_STATE = 'skills/agentic-vault/scripts/vault_install_state.py'
CLAIM_VERIFIER = 'scripts/verify_release_claims.py'

ECC_ID = 'github:affaan-m/ecc'
ECC_URL = 'https://github.com/affaan-m/ECC'
ECC_ALIAS_URL = 'https://github.com/affaan-m/everything-claude-code'
CONNECTOME_ID = 'doi:10.5281/zenodo.24361690'


def _find_single_line(read_lines, file, commit, predicate, label):
    lines = read_lines(file)
    matches = [(i, line) for i, line in enumerate(lines, 1) if predicate(line)]
    if len(matches) != 1:
        raise ValueError(f'Expected one citation of {label} in {file}, found {len(matches)}')
    number, line = matches[0]
    excerpt = excerpt_of(line)
    if sum(excerpt_of(other) == excerpt for other in lines) != 1:
        raise ValueError(f'Ambiguous evidence excerpt for {label} in {file}')
    return dict(file=file, line=number, url=f'{PREFIX}{commit}/{file}#L{number}', excerpt=excerpt)


def prepare(registry, artwork, commit, read_lines):
    snapshot = registry['snapshots']['agentic-vault']
    if (snapshot['version'], snapshot['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'This update requires the published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]

    ecc_keys = [canonical_key(u)['key'] for u in (ECC_URL, ECC_ALIAS_URL)]
    ecc_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: 'https://github.com/affaan-m/ECC' in s, 'affaan-m/ECC'),
        _find_single_line(read_lines, HOOK_WIRING, commit, lambda s: 'affaan-m/ECC' in s, 'affaan-m/ECC'),
        _find_single_line(read_lines, INSTALL_STATE, commit, lambda s: 'affaan-m/ECC' in s, 'affaan-m/ECC'),
    ]
    registry['sources'].append(dict(
        id=ecc_keys[0],
        kind='project',
        title='affaan-m/ECC',
        url=ECC_URL,
        year=2026,
        keys=ecc_keys,
        aliases=['ECC', 'affaan-m/everything-claude-code', 'everything-claude-code'],
        tags=['보안·안전', '에이전트'],
        note=(
            "Affaan Mustafa's ECC v2.2.3 (commit ccd8da1a72, MIT, formerly affaan-m/everything-claude-code) "
            "provides hook/config diagnostics, install-state tracking, and static security checks. "
            "Agentic Vault v0.54.0 adapts invisible Unicode smuggling defense, read-only hook-wiring inspection, "
            "manifest-backed install-state safe uninstall, and CI static hygiene guards in Python standard library only. "
            "No Node/Rust runtime, hook engine, or general skill pack is copied."
        ),
        uses=[dict(plugin='agentic-vault', role='reference', evidence=ecc_rows)],
    ))

    connectome_matches = [s for s in registry['sources'] if s['id'] == CONNECTOME_ID]
    if len(connectome_matches) != 1:
        raise ValueError(f'Expected existing {CONNECTOME_ID} entry in registry, found {len(connectome_matches)}')
    connectome = connectome_matches[0]
    if any(use['plugin'] == 'agentic-vault' for use in connectome['uses']):
        raise ValueError(f'{CONNECTOME_ID} already has an agentic-vault use')
    connectome_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: 'doi.org/10.5281/zenodo.24361690' in s, 'connectome-cognition-benchmark'),
        _find_single_line(read_lines, CLAIM_VERIFIER, commit, lambda s: 'doi:10.5281/zenodo.24361690' in s, 'connectome-cognition-benchmark'),
    ]
    connectome['uses'].append(dict(plugin='agentic-vault', role='reference', evidence=connectome_rows))
    connectome['note'] = (
        "Chulmin Pyo’s v1.1.0 software release preserves code, per-fold results and pre-registrations. "
        "The archive identifies ai3inc/connectome-cognition-benchmark v1.1.0 at commit 9c5d863256fdc20c341b94b874e62921e92f22c1. "
        "Semantic Crosscheck v0.30.0 adapts the upstream preregistration and numerical claim checks for offline SQL evaluation runs. "
        "Agentic Vault v0.54.0 independently adapts the provenance-bound numbers index and declarative claim verifier pattern "
        "in scripts/verify_release_claims.py to check release verification receipts, release notes, and SHA256SUMS offline "
        "using Python standard library only. No neuroscience pipeline or upstream code is copied."
    )

    snapshot.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(
        rebound=prior_rows,
        moved=moved,
        added={ECC_ID: len(ecc_rows), CONNECTOME_ID: len(connectome_rows)},
    )


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
    print(json.dumps(dict(**report, applied=args.apply)))


if __name__ == '__main__':
    main()
