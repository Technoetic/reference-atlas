"""Add the semantic-crosscheck v0.32.0 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.32.0'
PRIOR_VERSION = 'v0.31.1'
PRIOR_COMMIT = '0d741b3287d30d323268b607c06a22d6d68a74b3'
AV_VERSION = 'v0.54.1'

RELEASE = 'docs/releases/v0.32.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
PAIRED = 'docs/paired-release.md'
PREFLIGHT = 'docs/semantic-preflight.md'

NEW_SOURCES = [
    dict(
        url='https://www.postgresql.org/docs/17/ddl-rowsecurity.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 5.9. Row Security Policies',
        year=2026,
        aliases=['PostgreSQL 17 Row Security Policies', 'PostgreSQL RLS', 'relrowsecurity'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 official documentation covering row-level security policies, '
            'pg_class.relrowsecurity, relforcerowsecurity and pg_roles.rolbypassrls. '
            'Semantic Crosscheck v0.32.0 inspects these catalog flags in doctor (recording '
            'not_proven visibility-skew disclosures with zero extra round trips) and fails closed '
            '(not_run, reason=row_level_security) in grain when RLS filters the check role without '
            'BYPASSRLS. This records a citation, not copied code or a runtime dependency.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/ddl-rowsecurity.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/ddl-rowsecurity.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-index.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 52.26. pg_index (indnullsnotdistinct)',
        year=2026,
        aliases=['PostgreSQL 17 pg_index', 'UNIQUE NULLS NOT DISTINCT', 'indnullsnotdistinct'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_index.indnullsnotdistinct (introduced '
            'in PostgreSQL 15 for UNIQUE NULLS NOT DISTINCT constraints). Semantic Crosscheck '
            'v0.32.0 records unique_nulls_not_distinct catalog facts on doctor privileges checks and '
            'grain evidence within existing catalog queries, verified against live PostgreSQL 17 in '
            'tests/test_rls_catalog_pg.py.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-index.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-index.html'),
        ],
    ),
    dict(
        url='https://doi.org/10.1093/jrsssb/qkae011',
        other_urls=['https://arxiv.org/abs/1906.07801'],
        kind='paper',
        title='Safe Testing',
        year=2024,
        aliases=['Grünwald, de Heide & Koolen (2024)', 'Grünwald et al. (JRSS-B 2024)', 'Safe Testing'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Peter Grünwald, Rianne de Heide & Wouter M. Koolen (JRSS-B 2024, arXiv:1906.07801), '
            'introducing e-values and safe tests valid under optional stopping and optional '
            'continuation. Semantic Crosscheck v0.32.0 implements exact stdlib (math.lgamma) '
            'Jeffreys Beta(1/2, 1/2) mixture-martingale e-values (safe_e_value, safe_e_log, '
            'safe_anytime_p) in tools/paired_release.py with zero new runtime dependencies.'
        ),
        cites=[
            (RELEASE, '10.1093/jrsssb/qkae011'),
            (THIRD_PARTY, '10.1093/jrsssb/qkae011'),
            (PAIRED, '10.1093/jrsssb/qkae011'),
        ],
    ),
    dict(
        url='https://doi.org/10.1214/23-STS894',
        other_urls=['https://arxiv.org/abs/2210.01948'],
        kind='paper',
        title='Game-Theoretic Statistics and Safe Anytime-Valid Inference',
        year=2023,
        aliases=['Ramdas, Grünwald, Vovk & Shafer (2023)', 'SAVI', 'Safe Anytime-Valid Inference'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Aaditya Ramdas, Peter Grünwald, Vladimir Vovk & Glenn Shafer (Statistical Science 2023, '
            'arXiv:2210.01948), surveying game-theoretic testing by betting, test martingales and '
            'anytime-valid p-values p = min(1, 1/E). Semantic Crosscheck v0.32.0 cites it for '
            'anytime-valid sequential monitoring and additive log-e cohort pooling in '
            'tools/paired_release.py and docs/paired-release.md.'
        ),
        cites=[
            (RELEASE, '10.1214/23-STS894'),
            (THIRD_PARTY, '10.1214/23-STS894'),
            (PAIRED, '10.1214/23-STS894'),
        ],
    ),
    dict(
        url='https://doi.org/10.1214/20-AOS1991',
        other_urls=['https://arxiv.org/abs/1810.08240'],
        kind='paper',
        title='Time-uniform, nonparametric, nonasymptotic confidence sequences',
        year=2021,
        aliases=['Howard, Ramdas, McAuliffe & Sekhon (2021)', 'Confidence Sequences (AoS 2021)'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Steven R. Howard, Aaditya Ramdas, Jon McAuliffe & Jasjeet Sekhon (Annals of Statistics '
            '2021, arXiv:1810.08240), establishing nonasymptotic time-uniform martingale bounds. '
            'Semantic Crosscheck v0.32.0 cites it alongside Safe Testing for sequential held-out '
            'monitoring boundaries and minimum discordant sample disclosure (b >= 7 for E >= 20) in '
            'tools/paired_release.py and docs/paired-release.md.'
        ),
        cites=[
            (RELEASE, '10.1214/20-AOS1991'),
            (THIRD_PARTY, '10.1214/20-AOS1991'),
            (PAIRED, '10.1214/20-AOS1991'),
        ],
    ),
    dict(
        url='https://doi.org/10.1016/j.datak.2009.07.010',
        other_urls=[],
        kind='paper',
        title='A survey on summarizability issues in multidimensional modeling',
        year=2009,
        aliases=['Mazón, Lechtenbörger & Trujillo (2009)', 'Mazón et al. (DKE 2009)', 'OLAP Summarizability Survey'],
        tags=['데이터 계약', 'SQL', '신뢰성'],
        note=(
            'Jose-Norberto Mazón, Jens Lechtenbörger & Juan Trujillo (Data & Knowledge Engineering '
            '2009), taxonomizing multidimensional summarizability constraints (disjointness, '
            'completeness, strictness and additive/semi-additive/non-additive measures). Semantic '
            'Crosscheck v0.32.0 classifies semantic-preflight contracts into closed summarizability '
            'enums with opt-in --reject-semi-additive enforcement and maps grain violations to '
            'summarizability_failures dimensions.'
        ),
        cites=[
            (RELEASE, '10.1016/j.datak.2009.07.010'),
            (THIRD_PARTY, '10.1016/j.datak.2009.07.010'),
            (PREFLIGHT, '10.1016/j.datak.2009.07.010'),
        ],
    ),
    dict(
        url='https://doi.org/10.1145/3689031.3696064',
        other_urls=[],
        kind='paper',
        title='Understanding and Detecting SQL Function Bugs: Using Simple Boundary Arguments to Trigger Hundreds of DBMS Bugs',
        year=2025,
        aliases=['Fu et al. (EuroSys 2025)', 'Soft (EuroSys 2025)', 'SQL Function Boundary Bugs'],
        tags=['SQL', '평가·테스트'],
        note=(
            'Jingzhou Fu, Jie Liang, Zhiyong Wu, Jingzheng Zhao, Mingzhe Li & Yu Jiang (EuroSys '
            '2025), showing that targeted boundary arguments (empty/quoted/Unicode strings, signed '
            'zero, integer/decimal extremes, extreme dates and NULLs) trigger hundreds of SQL '
            'built-in function bugs across DBMS engines. Semantic Crosscheck v0.32.0 adds the '
            'deterministic function_boundary synthetic fixture scenario to counterexample and tlp '
            'without copying external code or changing existing scenarios.'
        ),
        cites=[
            (RELEASE, '10.1145/3689031.3696064'),
            (THIRD_PARTY, '10.1145/3689031.3696064'),
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
