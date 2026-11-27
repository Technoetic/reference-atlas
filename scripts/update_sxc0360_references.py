"""Add the semantic-crosscheck v0.36.0 shared reference to openai/math and repin earlier uses."""
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
TAG = 'v0.36.0'
PRIOR_VERSION = 'v0.35.0'
PRIOR_COMMIT = '9e91c7a38973863c9e5ce2d137f422d13a5af7f5'
AV_VERSION = 'v0.59.0'

RELEASE = 'docs/releases/v0.36.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
PAIRED = 'docs/paired-release.md'

SHARED_UPDATES = [
    dict(
        id='github:openai/math',
        note=(
            'OpenAI (2026, Apache-2.0, commit 3344da59). Public repository of mathematical research artifacts, '
            'proof-verification workflows, and structured withdrawal/supersession records. Agentic Vault v0.59.0 '
            'selectively adapts three Python stdlib-only patterns: (1) opt-in read-only note withdrawal & supersession '
            'lifecycle auditing (skills/agentic-vault/scripts/vault_lifecycle.py, docs/note-lifecycle.md) with '
            'withdrawal_scope=proof_or_evidence_only, pinned 40/64-hex withdrawn_revision, O(N) supersession chains, '
            'and bounded cascade dependents; (2) check_exact_tree_membership() and required zero-count negative-evidence '
            'verification plus --require-independent-review in scripts/verify_release_claims.py; and (3) opt-in '
            'review_status, automation_methods, pinned immutable spec_files vs disjoint solution_files separation, and '
            'permitted_gaps allowlists in skills/agentic-vault/scripts/vault_coverage.py. Semantic Crosscheck v0.36.0 '
            'reuses this source for three distinct pure-stdlib verification patterns with zero new runtime dependencies '
            'and byte-identical default report outputs: (1) exact fixture-directory tree membership auditing '
            '(tree_membership_passed, extra_files, extra_directories, unexpected_entries, symlink/reparse rejection) in '
            'tools/paired_release.py and tools/run_paired_example.py (adapted from MUB-6 check_records.py); (2) closed-enum '
            'trust-assumption derivation (ASSUMPTION_CODES, 17 codes) and opt-in sxc.py report --permitted-assumptions '
            '<csv|none> allowlist checking (assumptions:permitted) in report.py and sxc.py (informed by Lean '
            'ComparatorChallenges permitted_axioms); and (3) removal of remaining production/CI raw assert statements '
            '(guarded by AST unit test) paired with relocated-CWD, read-only SHA-256, python -O -B tamper-rejection '
            'verification in tools/portability_check.py (informed by Einstein four-manifolds portability_check.py and '
            'Mahler reproduce.py). No Lean proofs, datasets, heavy numeric packages, or upstream code were copied.'
        ),
        cites=[
            (RELEASE, 'reused Reference Atlas source'),
            (THIRD_PARTY, 'https://github.com/openai/math'),
            (PAIRED, 'https://github.com/openai/math'),
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
    artwork_by_id = {a['sourceId']: a for a in artwork['assets']}
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
        if sid in artwork_by_id:
            all_urls = [row['url'] for use in source['uses'] for row in use['evidence']]
            artwork_by_id[sid]['evidenceUrls'] = list(all_urls)
            artwork_by_id[sid]['currentEvidenceUrls'] = list(all_urls)
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
