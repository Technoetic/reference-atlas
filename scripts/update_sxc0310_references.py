"""Add the semantic-crosscheck v0.31.0 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.31.0'
PRIOR_VERSION = 'v0.30.0'
PRIOR_COMMIT = 'b51688e57e2a208e17f8408eae0d2076a7e87dd5'
AV_VERSION = 'v0.54.0'

RELEASE = 'docs/releases/v0.31.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
PAIRED_DOC = 'docs/paired-release.md'

RULESETS_ID = 'url:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets'
RULESETS_URL = 'https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets'

NEW_SOURCES = [
    dict(
        url='https://doi.org/10.1186/1471-2288-13-91',
        kind='paper',
        title='The McNemar test for binary matched-pairs data: mid-p and asymptotic are better than exact conditional',
        year=2013,
        aliases=['Fagerland et al. (2013)', 'Fagerland, Lydersen & Laake 2013', 'Mid-P McNemar test'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Fagerland, Lydersen & Laake (2013), BMC Medical Research Methodology 13:91. '
            'Semantic Crosscheck v0.31.0 implements exact conditional and Mid-P McNemar two-sided p-values '
            'in tools/paired_release.py using Python standard library math.comb only and discloses minimum '
            'discordant-pair thresholds (5 for Mid-P p < 0.05, 6 for exact p < 0.05). '
            'This records a citation, not copied code, a runtime dependency or reproduced results.'
        ),
        cites=[
            (RELEASE, '10.1186/1471-2288-13-91'),
            (THIRD_PARTY, '10.1186/1471-2288-13-91'),
            (PAIRED_DOC, '10.1186/1471-2288-13-91'),
        ],
    ),
    dict(
        url='https://doi.org/10.1002/%28SICI%291097-0258%2819981130%2917:22%3C2635::AID-SIM954%3E3.0.CO;2-C',
        kind='paper',
        title='Improved confidence intervals for the difference between binomial proportions based on paired data',
        year=1998,
        aliases=['Newcombe (1998)', 'Newcombe Method 10', 'Paired Wilson confidence interval'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Robert G. Newcombe (1998), Statistics in Medicine 17(22):2635-2650. '
            'Semantic Crosscheck v0.31.0 implements Method 10 paired Wilson-score 95% confidence intervals '
            '(with zero-denominator phi=0 handling) in tools/paired_release.py using Python standard library only '
            'to expose small-sample uncertainty width beside paired detection counts. '
            'This records a citation, not copied code, a runtime dependency or reproduced results.'
        ),
        cites=[
            (RELEASE, 'AID-SIM954'),
            (THIRD_PARTY, 'AID-SIM954'),
            (PAIRED_DOC, 'AID-SIM954'),
        ],
    ),
    dict(
        url='https://doi.org/10.1162/089976698300017197',
        kind='paper',
        title='Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms',
        year=1998,
        aliases=['Dietterich (1998)'],
        tags=['평가·테스트'],
        note=(
            'Thomas G. Dietterich (1998), Neural Computation 10(7):1895-1923. '
            'Semantic Crosscheck v0.31.0 cites it in docs/paired-release.md and THIRD_PARTY.md as methodology '
            'rationale for using paired McNemar-family tests when comparing two detectors on the same test set. '
            'This records a citation, not copied code, a runtime dependency or reproduced results.'
        ),
        cites=[
            (RELEASE, '10.1162/089976698300017197'),
            (THIRD_PARTY, '10.1162/089976698300017197'),
            (PAIRED_DOC, '10.1162/089976698300017197'),
        ],
    ),
    dict(
        url='https://doi.org/10.1002/stvr.1486',
        kind='paper',
        title="A Hitchhiker's guide to statistical tests for assessing randomized algorithms in software engineering",
        year=2014,
        aliases=['Arcuri & Briand (2014)', 'Arcuri & Briand (2012/2014)'],
        tags=['평가·테스트'],
        note=(
            'Andrea Arcuri & Lionel Briand (2014), Software Testing, Verification and Reliability 24(3):219-250. '
            'Semantic Crosscheck v0.31.0 cites it in docs/paired-release.md and THIRD_PARTY.md for reporting '
            'non-parametric tests and effect sizes when comparing randomized or mutation-based checks. '
            'This records a citation, not copied code, a runtime dependency or reproduced results.'
        ),
        cites=[
            (RELEASE, '10.1002/stvr.1486'),
            (THIRD_PARTY, '10.1002/stvr.1486'),
            (PAIRED_DOC, '10.1002/stvr.1486'),
        ],
    ),
    dict(
        url='https://doi.org/10.1145/3243734.3243804',
        kind='paper',
        title='Evaluating Fuzz Testing',
        year=2018,
        aliases=['Klees et al. (CCS 2018)', 'Evaluating Fuzz Testing (CCS 2018)'],
        tags=['평가·테스트', '보안·안전'],
        note=(
            'George Klees, Andrew Ruef, Benji Cooper, Shiyi Wei & Michael Hicks (CCS 2018). '
            'Semantic Crosscheck v0.31.0 cites it in docs/paired-release.md and THIRD_PARTY.md for experimental '
            'hygiene rules: deduplicating synthetic faults, fixing seeds and separating development from held-out cases. '
            'This records a citation, not copied code, a runtime dependency or reproduced results.'
        ),
        cites=[
            (RELEASE, '10.1145/3243734.3243804'),
            (THIRD_PARTY, '10.1145/3243734.3243804'),
            (PAIRED_DOC, '10.1145/3243734.3243804'),
        ],
    ),
    dict(
        url='https://github.com/astral-sh/ruff',
        kind='project',
        title='astral-sh/ruff',
        year=2026,
        aliases=['Ruff', 'Ruff 0.17.6'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Astral Ruff Python linter (MIT, pinned to 0.17.6 in CI only). '
            'Semantic Crosscheck v0.31.0 runs ruff check --isolated on scripts, tools and tests in the CI '
            'static quality job without adding any runtime dependency or copying third-party code.'
        ),
        cites=[
            (RELEASE, 'https://github.com/astral-sh/ruff'),
            (THIRD_PARTY, 'https://github.com/astral-sh/ruff'),
        ],
    ),
    dict(
        url='https://github.com/astral-sh/ty',
        kind='project',
        title='astral-sh/ty',
        year=2026,
        aliases=['ty', 'ty 0.0.107'],
        tags=['평가·테스트', '신뢰성'],
        note=(
            'Astral ty Python static type checker (MIT, pre-1.0, pinned to 0.0.107 in CI only). '
            'Semantic Crosscheck v0.31.0 checks a curated list of clean core and tool modules in the CI '
            'static quality job without adding any runtime dependency or copying third-party code.'
        ),
        cites=[
            (RELEASE, 'https://github.com/astral-sh/ty'),
            (THIRD_PARTY, 'https://github.com/astral-sh/ty'),
        ],
    ),
    dict(
        url='https://github.com/quarylabs/sqruff',
        kind='project',
        title='quarylabs/sqruff',
        year=2026,
        aliases=['sqruff', 'sqruff 0.44.0'],
        tags=['SQL', '평가·테스트'],
        note=(
            'Quary Labs sqruff PostgreSQL-capable SQL linter (Apache-2.0, pinned to 0.44.0 in CI only). '
            'Semantic Crosscheck v0.31.0 runs sqruff lint with .sqruff (dialect = postgres, non-layout rules) '
            'on demo/gold/*.sql in CI for advisory syntax/lint hygiene only, without SQL equivalence or verdict authority.'
        ),
        cites=[
            (RELEASE, 'https://github.com/quarylabs/sqruff'),
            (THIRD_PARTY, 'https://github.com/quarylabs/sqruff'),
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

    # Shared source: GitHub Docs: About rulesets (already cited by agentic-vault)
    matches = [s for s in registry['sources'] if s['id'] == RULESETS_ID]
    if len(matches) != 1:
        raise ValueError(f'Expected existing {RULESETS_ID}, found {len(matches)}')
    rulesets = matches[0]
    if any(u['plugin'] == PLUGIN for u in rulesets['uses']):
        raise ValueError(f'{RULESETS_ID} already has a {PLUGIN} use')
    rulesets_rows = [
        _find_single_line(read_lines, RELEASE, commit, RULESETS_URL, RULESETS_ID),
        _find_single_line(read_lines, THIRD_PARTY, commit, RULESETS_URL, RULESETS_ID),
    ]
    rulesets['uses'].append(dict(plugin=PLUGIN, role='reference', evidence=rulesets_rows))
    rulesets['note'] = rulesets['note'] + (
        ' Semantic Crosscheck v0.31.0 applies the same refs/tags/v* immutable release-tag ruleset pattern '
        'alongside main branch protection and Dependabot security updates.'
    )
    # Keep artwork manifest's evidenceUrls / currentEvidenceUrls aligned with the updated shared source.
    new_urls = [row['url'] for row in rulesets_rows]
    for asset in artwork['assets']:
        if asset['sourceId'] == RULESETS_ID:
            asset['evidenceUrls'] = list(asset['evidenceUrls']) + new_urls
            asset['currentEvidenceUrls'] = list(asset['currentEvidenceUrls']) + new_urls
    added[RULESETS_ID] = len(rulesets_rows)

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
