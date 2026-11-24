"""Add the semantic-crosscheck v0.34.0 PostgreSQL 17 catalog references and repin earlier uses."""
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
TAG = 'v0.34.0'
PRIOR_VERSION = 'v0.33.0'
PRIOR_COMMIT = 'ad335c06b27abf8608a209a4f3b967805b7a8888'
AV_VERSION = 'v0.57.0'

RELEASE = 'docs/releases/v0.34.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'

EXISTING_UPDATES = [
    dict(
        id='url:https://www.postgresql.org/docs/17/catalog-pg-index.html',
        note=(
            'PostgreSQL 17 system catalog documentation for pg_index (indisunique, indisvalid, indisready, '
            'indpred, indexprs and indnullsnotdistinct). Semantic Crosscheck v0.32.0 first recorded '
            'unique_nulls_not_distinct catalog facts in doctor and grain, and v0.34.0 tightened the predicate '
            'in doctor._privileges_sql() and grain.evaluate() to require indisunique AND indisvalid AND '
            'indisready AND indpred IS NULL AND indexprs IS NULL AND indnullsnotdistinct, eliminating false '
            'positives from invalid, partial and expression unique indexes (verified against live PostgreSQL 17 '
            'in tests/test_rls_catalog_pg.py).'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-index.html'),
            (THIRD_PARTY, 'indisvalid AND indisready'),
        ],
    ),
]

NEW_SOURCES = [
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-class.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 52.11. pg_class',
        year=2026,
        aliases=['PostgreSQL 17 pg_class', 'relispopulated', 'relhasrules', 'pg_class.relkind'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_class (relkind, relispopulated, relhasrules). '
            'Semantic Crosscheck v0.34.0 inspects these columns inside doctor._privileges_sql() with zero extra '
            'SQL round trips to fail closed on unpopulated materialized views (relkind=\'m\', '
            'relispopulated=false) with an actionable REFRESH MATERIALIZED VIEW hint, disclose foreign-table '
            'REPEATABLE READ snapshot limits (relkind=\'f\'), and disclose ordinary/partitioned table rewrite '
            'rules (relhasrules=true, excluding views and materialized views). This records a citation, not '
            'copied code or a runtime dependency.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-class.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-class.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-constraint.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 52.13. pg_constraint',
        year=2026,
        aliases=['PostgreSQL 17 pg_constraint', 'convalidated', 'NOT VALID constraint'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_constraint (contype, convalidated). '
            'Semantic Crosscheck v0.34.0 counts unvalidated CHECK and FOREIGN KEY constraints '
            '(contype IN (\'c\', \'f\') AND NOT convalidated) inside doctor._privileges_sql() with zero extra '
            'SQL round trips and discloses them in not_proven so NOT VALID constraints are never mistaken for '
            'validated row invariants. Verified against live PostgreSQL 17 in tests/test_rls_catalog_pg.py.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-constraint.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-constraint.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/ddl-partitioning.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 5.12. Table Partitioning',
        year=2026,
        aliases=['PostgreSQL 17 Table Partitioning', 'pg_inherits', 'child_partition_row_security'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 official documentation covering declarative table partitioning and pg_inherits '
            'partition hierarchies. Semantic Crosscheck v0.34.0 adds a recursive pg_inherits check inside '
            'doctor._privileges_sql() and grain.evaluate() (zero extra SQL round trips, preserving grain\'s '
            'five-statement budget) to record child_partition_row_security and disclose asymmetric child '
            'partition RLS policies when the parent relation has relrowsecurity=false.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/ddl-partitioning.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/ddl-partitioning.html'),
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
    asset_by_id = {a['sourceId']: a for a in artwork['assets']}
    updated_existing = {}
    for spec in EXISTING_UPDATES:
        sid = spec['id']
        if sid not in by_id:
            raise ValueError(f'Expected existing source {sid}')
        source = by_id[sid]
        sxc_use = next((u for u in source['uses'] if u['plugin'] == PLUGIN), None)
        if sxc_use is None:
            raise ValueError(f'Expected existing {PLUGIN} use on {sid}')
        extra = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        existing_urls = {row['url'] for row in sxc_use['evidence']}
        for row in extra:
            if row['url'] in existing_urls:
                raise ValueError(f'Duplicate citation URL for {sid}: {row["url"]}')
        sxc_use['evidence'].extend(extra)
        source['note'] = spec['note']
        if sid in asset_by_id:
            all_urls = [row['url'] for u in source['uses'] for row in u['evidence']]
            asset_by_id[sid]['evidenceUrls'] = list(all_urls)
            asset_by_id[sid]['currentEvidenceUrls'] = list(all_urls)
        updated_existing[sid] = len(extra)

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
    return dict(rebound=prior_rows, moved=moved, updated_existing=updated_existing, added=added)


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
