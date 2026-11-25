"""Add the six semantic-crosscheck v0.35.0 primary references and repin earlier uses."""
import argparse
from datetime import datetime, timezone
from functools import cache
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources
from reference_identity import canonical_key, validate_catalog
from update_av048_references import excerpt_of
from update_av0521_references import ARTWORK, CATALOG_CSV, CATALOG_JSON, REGISTRY, built_catalog, encode, write_files
from update_sxc027_references import PLUGIN, PREFIX, repin


ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.35.0'
PRIOR_VERSION = 'v0.34.0'
PRIOR_COMMIT = '381212b8d3f63eebaa3bef48540ec4be1b22bb98'
AV_VERSION = 'v0.58.0'

RELEASE = 'docs/releases/v0.35.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
MUTATION_MATRIX_DOC = 'docs/mutation-matrix.md'

NEW_SOURCES = [
    dict(
        url='https://www.postgresql.org/docs/17/sql-createview.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — CREATE VIEW',
        year=2026,
        aliases=['PostgreSQL 17 CREATE VIEW', 'security_invoker', 'security_barrier'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 SQL reference for CREATE VIEW options security_invoker and security_barrier. '
            'Semantic Crosscheck v0.35.0 parses both boolean options inside SQL from pg_class.reloptions '
            'in doctor._privileges_sql() with zero extra per-entity round trips (never echoing raw reloptions '
            'strings) and discloses default view-owner execution (relkind=\'v\', view_security_invoker=false) '
            'in not_proven. Verified against live PostgreSQL 17 in tests/test_rls_catalog_pg.py.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/sql-createview.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/sql-createview.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/rules-privileges.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 39.5. Rules and Privileges',
        year=2026,
        aliases=['PostgreSQL 17 Rules and Privileges', 'view owner privileges'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 documentation explaining view-owner vs view-invoker privilege checks and '
            'row-level security policy evaluation across views. Semantic Crosscheck v0.35.0 cites it '
            'alongside CREATE VIEW for disclosing when a source view executes with view-owner privileges '
            '(view_security_invoker=false) rather than the read-only check role.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/rules-privileges.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/rules-privileges.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-database.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.15. pg_database',
        year=2026,
        aliases=['PostgreSQL 17 pg_database', 'datcollversion', 'pg_database_collation_actual_version'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_database (datcollversion and '
            'pg_database_collation_actual_version). Semantic Crosscheck v0.35.0 checks for database '
            'collation version drift in doctor._database() and runtime_provenance._postgres(), '
            'flagging collation_version_mismatch and appending a fixed not_proven disclosure so '
            'pre-existing glibc/ICU drift is not masked by matching start/end runtime digests.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-database.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-database.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-collation.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.12. pg_collation',
        year=2026,
        aliases=['PostgreSQL 17 pg_collation', 'collversion', 'pg_collation_actual_version'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_collation (collversion and '
            'pg_collation_actual_version). Semantic Crosscheck v0.35.0 checks column-referenced '
            'non-default collations inside doctor._privileges_sql() (zero extra per-entity round trips, '
            'filtering collversion IS NOT NULL) and discloses mismatched_column_collations in not_proven.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-collation.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-collation.html'),
        ],
    ),
    dict(
        url='https://doi.org/10.1609/aaai.v39i11.33217',
        other_urls=['https://arxiv.org/abs/2502.10155'],
        kind='paper',
        title='Complete Symmetry Breaking for Finite Models',
        year=2025,
        aliases=['Dančo et al. (AAAI 2025)', 'Complete Symmetry Breaking for Finite Models'],
        tags=['SQL', '검증'],
        note=(
            'Marek Dančo, Mikoláš Janota, Michael Codish & João Jorge Araújo (AAAI 2025, '
            'doi:10.1609/aaai.v39i11.33217, arXiv:2502.10155). Formulates complete lexicographic symmetry '
            'breaking for finite model finding. Semantic Crosscheck v0.35.0 applies lexicographic '
            'row-order symmetry breaking (row_symmetry_breaking=True default) in witness.py over Z3 '
            'active rows, eliminating k! SQL bag-isomorphic row permutations while preserving complete '
            'SQL multiset coverage and v2 replay compatibility.'
        ),
        cites=[
            (RELEASE, 'arxiv.org/abs/2502.10155'),
            (THIRD_PARTY, 'arxiv.org/abs/2502.10155'),
        ],
    ),
    dict(
        url='https://doi.org/10.1145/2950290.2950322',
        other_urls=[],
        kind='paper',
        title='Analyzing the Validity of Selective Mutation with Dominator Mutants',
        year=2016,
        aliases=['Kurtz et al. (ESEC/FSE 2016)', 'Dominator Mutants', 'DMSG'],
        tags=['평가·테스트', '검증'],
        note=(
            'Bob Kurtz, Paul Ammann, Jeff Offutt, Márcio Eduardo Delamaro, Mariet Kurtz & Nida Gökçe '
            '(ESEC/FSE 2016, doi:10.1145/2950290.2950322). Defines the Dynamic Mutant Subsumption Graph '
            '(DMSG) and minimal dominator mutants to expose mutation score inflation from redundant '
            'subsumed mutants. Semantic Crosscheck v0.35.0 implements pure-stdlib compute_subsumption() '
            'under subsumption in verify/mutation-matrix.json (diagnostic_only, zero extra Cube runs, '
            'zero impact on authoritative V4 verdicts).'
        ),
        cites=[
            (RELEASE, '10.1145/2950290.2950322'),
            (THIRD_PARTY, '10.1145/2950290.2950322'),
            (MUTATION_MATRIX_DOC, '10.1145/2950290.2950322'),
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
            uses=[dict(plugin=PLUGIN, role='reference', evidence=evidence)],
        ))
        existing_ids.add(sid)
        existing_keys.update(keys)
        added[sid] = len(evidence)

    sxc_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}')
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
