"""Add the semantic-crosscheck v0.31.1 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.31.1'
PRIOR_VERSION = 'v0.31.0'
PRIOR_COMMIT = 'e9280f5e3011f8d1f4ba4bfe133235ace78ad39f'
AV_VERSION = 'v0.54.1'

RELEASE = 'docs/releases/v0.31.1.md'
THIRD_PARTY = 'THIRD_PARTY.md'
DATA_RULES = 'docs/data-rules.md'

NEW_SOURCES = [
    dict(
        url='https://reproducible-builds.org/specs/source-date-epoch/',
        kind='format',
        title='SOURCE_DATE_EPOCH specification (Reproducible Builds)',
        year=2026,
        aliases=['SOURCE_DATE_EPOCH', 'Reproducible Builds SOURCE_DATE_EPOCH'],
        tags=['신뢰성', '보안·안전'],
        note=(
            'Reproducible Builds specification defining SOURCE_DATE_EPOCH for timezone-independent build '
            'timestamps. Semantic Crosscheck v0.31.1 adds stdlib-only tools/build_release_zip.py using '
            'git archive --format=tar, UTC gmtime timestamps, sorted POSIX paths, fixed Unix metadata '
            '(create_system = 3), and deflate -9 so release ZIP SHA-256 digests match across TZ=KST-9, '
            'TZ=UTC0 and TZ=EST5. This records a citation, not copied code or a runtime dependency.'
        ),
        cites=[
            (RELEASE, 'reproducible-builds.org/specs/source-date-epoch/'),
            (THIRD_PARTY, 'reproducible-builds.org/specs/source-date-epoch/'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/collation.html',
        kind='article',
        title='PostgreSQL 17 Documentation — 23.2. Collation Support',
        year=2026,
        aliases=['PostgreSQL 17 Collation Support', 'PostgreSQL builtin C.UTF-8 collation'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 official documentation describing the built-in collation provider '
            '(provider = builtin, locale = C.UTF-8), deterministic code-point sorting immune to OS '
            'glibc/ICU drift. Semantic Crosscheck v0.31.1 documents it in docs/data-rules.md, '
            'pitfalls.md and docs/setup-roles.sql and verifies Python sorted() parity and Unicode '
            'upper() mapping in tests/test_collation_builtin_pg.py without altering existing databases.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/collation.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/collation.html'),
            (DATA_RULES, 'postgresql.org/docs/17/collation.html'),
        ],
    ),
    dict(
        url='https://ecma-international.org/publications-and-standards/standards/ecma-424/',
        kind='format',
        title='ECMA-424: OWASP CycloneDX Software Bill of Materials Standard',
        year=2026,
        aliases=['ECMA-424', 'CycloneDX SBOM Standard', 'OWASP CycloneDX'],
        tags=['보안·안전', '신뢰성'],
        note=(
            'ECMA-424 standardizing the OWASP CycloneDX machine-readable SBOM format. Semantic Crosscheck '
            'v0.31.1 verifies reproducible CycloneDX JSON SBOM generation in CI for Python requirements '
            '(cyclonedx-bom) and the Cube adapter lockfile (npm sbom) with zero runtime dependencies.'
        ),
        cites=[
            (RELEASE, 'ecma-international.org/publications-and-standards/standards/ecma-424/'),
            (THIRD_PARTY, 'ecma-international.org/publications-and-standards/standards/ecma-424/'),
        ],
    ),
    dict(
        url='https://docs.npmjs.com/cli/v11/commands/npm-sbom',
        kind='article',
        title='npm CLI Documentation — npm sbom',
        year=2026,
        aliases=['npm sbom'],
        tags=['보안·안전'],
        note=(
            'Official npm CLI documentation for built-in SBOM generation. Semantic Crosscheck v0.31.1 runs '
            'npm sbom --sbom-format cyclonedx --package-lock-only on skills/semantic-crosscheck/adapters/cube '
            'in the CI static job without adding any npm or Python runtime packages.'
        ),
        cites=[
            (RELEASE, 'docs.npmjs.com/cli/v11/commands/npm-sbom'),
            (THIRD_PARTY, 'docs.npmjs.com/cli/v11/commands/npm-sbom'),
        ],
    ),
    dict(
        url='https://github.com/CycloneDX/cyclonedx-python',
        kind='project',
        title='CycloneDX/cyclonedx-python',
        year=2026,
        aliases=['cyclonedx-bom', 'cyclonedx-py', 'cyclonedx-bom 9.0.0'],
        tags=['보안·안전', '신뢰성'],
        note=(
            'OWASP CycloneDX Python SBOM generator (Apache-2.0, pinned to cyclonedx-bom==9.0.0 in CI only). '
            'Semantic Crosscheck v0.31.1 checks reproducible CycloneDX JSON generation across all four '
            'requirements/*.txt files in the CI static job without adding any runtime dependency.'
        ),
        cites=[
            (RELEASE, 'https://github.com/CycloneDX/cyclonedx-python'),
            (THIRD_PARTY, 'https://github.com/CycloneDX/cyclonedx-python'),
        ],
    ),
    dict(
        url='https://github.com/zizmorcore/zizmor',
        kind='project',
        title='zizmorcore/zizmor',
        year=2026,
        aliases=['zizmor', 'zizmor 1.32.0'],
        tags=['보안·안전', '평가·테스트'],
        note=(
            'Static security analyzer for GitHub Actions workflows (MIT, pinned to 1.32.0 in CI only). '
            'Semantic Crosscheck v0.31.1 runs zizmor --offline .github/workflows/tests.yml in the CI '
            'static quality job without adding any runtime dependency or copying third-party code.'
        ),
        cites=[
            (RELEASE, 'https://github.com/zizmorcore/zizmor'),
            (THIRD_PARTY, 'https://github.com/zizmorcore/zizmor'),
        ],
    ),
    dict(
        url='https://github.com/pypa/pip-audit',
        kind='project',
        title='pypa/pip-audit',
        year=2026,
        aliases=['pip-audit', 'pip-audit 2.10.1'],
        tags=['보안·안전'],
        note=(
            'PyPA vulnerability scanner for Python environments and requirements files (Apache-2.0, pinned '
            'to 2.10.1 in CI only). Semantic Crosscheck v0.31.1 runs python -m pip_audit --no-deps '
            '--disable-pip across all four requirements/*.txt files in CI without adding runtime dependencies.'
        ),
        cites=[
            (RELEASE, 'https://github.com/pypa/pip-audit'),
            (THIRD_PARTY, 'https://github.com/pypa/pip-audit'),
        ],
    ),
    dict(
        url='https://doi.org/10.1145/3194164.3194186',
        kind='paper',
        title='Cognitive complexity: an overview and evaluation',
        year=2018,
        aliases=['Campbell (2018)', 'Campbell (TechDebt 2018)', 'Cognitive Complexity'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'G. Ann Campbell (IEEE/ACM TechDebt 2018), introducing cognitive complexity to measure control-flow '
            'understandability better than cyclomatic complexity. Semantic Crosscheck v0.31.1 cites it as '
            'rationale for CI cognitive complexity ceilings on tools/ and hotspot visibility on package scripts. '
            'This records a citation, not copied code or a runtime dependency.'
        ),
        cites=[
            (RELEASE, '10.1145/3194164.3194186'),
            (THIRD_PARTY, '10.1145/3194164.3194186'),
        ],
    ),
    dict(
        url='https://github.com/rohaquinlop/complexipy',
        kind='project',
        title='rohaquinlop/complexipy',
        year=2026,
        aliases=['complexipy', 'complexipy 9.0.0'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Rust-backed Python cognitive complexity analyzer (MIT, pinned to 9.0.0 in CI only). '
            'Semantic Crosscheck v0.31.1 enforces --max-complexity-allowed 50 on tools/ and prints top-10 '
            'hotspots on package scripts in CI without adding any runtime dependency.'
        ),
        cites=[
            (RELEASE, 'https://github.com/rohaquinlop/complexipy'),
            (THIRD_PARTY, 'https://github.com/rohaquinlop/complexipy'),
        ],
    ),
    dict(
        url='https://github.com/jendrikseipp/vulture',
        kind='project',
        title='jendrikseipp/vulture',
        year=2026,
        aliases=['vulture', 'vulture 2.16'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Static dead-code finder for Python (MIT, pinned to 2.16 in CI only). Semantic Crosscheck '
            'v0.31.1 runs vulture tools skills/semantic-crosscheck/scripts --min-confidence 80 in the CI '
            'static quality job without adding any runtime dependency.'
        ),
        cites=[
            (RELEASE, 'https://github.com/jendrikseipp/vulture'),
            (THIRD_PARTY, 'https://github.com/jendrikseipp/vulture'),
        ],
    ),
    dict(
        url='https://github.com/osprey-oss/deptry',
        kind='project',
        title='osprey-oss/deptry',
        year=2026,
        aliases=['deptry', 'deptry 0.25.1'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Python dependency hygiene checker detecting missing, unused and transitive imports (MIT, '
            'pinned to 0.25.1 in CI only). Semantic Crosscheck v0.31.1 checks skills/semantic-crosscheck/scripts '
            'against requirements/*.txt in CI without adding any runtime dependency.'
        ),
        cites=[
            (RELEASE, 'https://github.com/osprey-oss/deptry'),
            (THIRD_PARTY, 'https://github.com/osprey-oss/deptry'),
        ],
    ),
]

SHARED_SOURCES = [
    dict(
        id='url:https://www.usenix.org/conference/usenixsecurity23/presentation/boucher',
        needle='usenix.org/conference/usenixsecurity23/presentation/boucher',
        note_append=(
            ' Semantic Crosscheck v0.31.1 adopts the same bidirectional control character defense in '
            'stdlib-only tools/check_unicode.py, enforced by unit tests and CI hygiene without echoing line text.'
        ),
    ),
    dict(
        id='url:https://www.unicode.org/reports/tr39',
        needle='unicode.org/reports/tr39/',
        note_append=(
            ' Semantic Crosscheck v0.31.1 rejects dangerous Default_Ignorable and invisible smuggling code points '
            'in tools/check_unicode.py across tracked repository files and explicit TOML/SQL inputs while allowing '
            'normal UTF-8 text.'
        ),
    ),
    dict(
        id='github:rhysd/actionlint',
        needle='https://github.com/rhysd/actionlint',
        note_append=(
            ' Semantic Crosscheck v0.31.1 runs the same SHA-256 checksum-verified rhysd/actionlint v1.7.12 '
            'linux_amd64 binary in its CI hygiene job.'
        ),
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
    added = {}
    for spec in NEW_SOURCES:
        ident = canonical_key(spec['url'])
        if ident is None:
            raise ValueError(f'No canonical key for {spec["url"]}')
        sid = ident['key']
        if sid in existing_ids:
            raise ValueError(f'Source already exists: {sid}')
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
            keys=[sid],
            aliases=spec['aliases'],
            tags=spec['tags'],
            note=spec['note'],
            uses=[dict(plugin=PLUGIN, role='reference', evidence=evidence)],
        ))
        existing_ids.add(sid)
        added[sid] = len(evidence)

    for shared in SHARED_SOURCES:
        sid = shared['id']
        matches = [s for s in registry['sources'] if s['id'] == sid]
        if len(matches) != 1:
            raise ValueError(f'Expected existing {sid}, found {len(matches)}')
        src = matches[0]
        if any(u['plugin'] == PLUGIN for u in src['uses']):
            raise ValueError(f'{sid} already has a {PLUGIN} use')
        rows = [
            _find_single_line(read_lines, RELEASE, commit, shared['needle'], sid),
            _find_single_line(read_lines, THIRD_PARTY, commit, shared['needle'], sid),
        ]
        src['uses'].append(dict(plugin=PLUGIN, role='reference', evidence=rows))
        src['note'] = src['note'] + shared['note_append']
        new_urls = [row['url'] for row in rows]
        for asset in artwork['assets']:
            if asset['sourceId'] == sid:
                asset['evidenceUrls'] = list(asset['evidenceUrls']) + new_urls
                asset['currentEvidenceUrls'] = list(asset['currentEvidenceUrls']) + new_urls
        added[sid] = len(rows)

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
