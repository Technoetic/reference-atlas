"""Prepare semantic-crosscheck v0.21.0 references from exact tagged Git blobs.

Offline and dry-run by default. The caller must independently verify public
source/tag availability before publishing. This helper neither publishes nor
changes plugin source, artwork assignments, generated images or their history.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'semantic-crosscheck'
PREFIX = f'https://github.com/Technoetic/{PLUGIN}/blob/'
TAG = 'v0.21.0'
SCOPE = ('공개 저장소의 논문·설계/평가/구현 참고·배경 사례. 실제 구현의 파서 구조 참고는 포함하고, '
         '실행·CI 도구로만 쓰는 의존성은 제외합니다. 참고 기록은 코드 복사나 연구 결과 재현을 뜻하지 않습니다.')
SPECS = (
    {'id': 'github:datacontract/datacontract-cli', 'kind': 'project',
     'title': 'Data Contract CLI', 'url': 'https://github.com/datacontract/datacontract-cli',
     'aliases': ['datacontract-cli'], 'tags': ['데이터 계약', '평가·테스트'],
     'files': [('docs/contract-report.md', 1), ('THIRD_PARTY.md', 1)],
     'note': ('Previously observed watchlist source, newly catalogued for the v0.21.0 authored '
              'contract-to-report evidence boundary. Upstream pin 09e779dfeaec63ee60edc102e7a3d6970e34e16b. '
              'Original implementation; no external contract engine or source is installed or bundled.')},
    {'id': 'github:bitol-io/open-data-contract-standard', 'kind': 'format',
     'title': 'Open Data Contract Standard (ODCS)',
     'url': 'https://github.com/bitol-io/open-data-contract-standard',
     'aliases': ['ODCS', 'Open Data Contract Standard'], 'tags': ['데이터 계약', '지식·온톨로지'],
     'files': [('docs/contract-report.md', 1), ('THIRD_PARTY.md', 1)],
     'note': ('Previously observed watchlist source, newly catalogued for v0.21.0 explicit authored '
              'contract/report declarations. Upstream pin 448f7b93329ece7827897d7dd51e827a3e279460. '
              'No full ODCS import/export compatibility, copied code or external contract runtime is claimed.')},
    {'id': 'github:pganalyze/libpg_query', 'kind': 'project', 'title': 'libpg_query',
     'url': 'https://github.com/pganalyze/libpg_query', 'aliases': [],
     'tags': ['SQL·데이터 검증', '평가·테스트'],
     'files': [('docs/sql-structure.md', 1), ('THIRD_PARTY.md', 1)],
     'note': ('Implemented structural-parser reference for the opt-in v0.21.0 SQL diagnostic through '
              'the separately installed pglast binding and PostgreSQL 17 parser. This is a project, '
              'not a paper or a CI-only tool. No parser code is vendored and a structure match does '
              'not establish SQL semantic equivalence or business correctness.')},
    {'id': 'github:lelit/pglast', 'kind': 'project', 'title': 'pglast',
     'url': 'https://github.com/lelit/pglast', 'aliases': ['pglast Python binding'],
     'tags': ['SQL·데이터 검증', '평가·테스트'],
     'files': [('docs/sql-structure.md', 1), ('THIRD_PARTY.md', 1)],
     'note': ('Separately selected optional binding pinned to 7.22 for the v0.21.0 PostgreSQL 17 '
              'AST structure diagnostic. GPL-3.0-or-later binding, distinct from libpg_query licenses; '
              'no parser source is vendored. Included for its implemented structural role, not '
              'as a paper or a CI-only dependency. Operational reports gain no parser proof authority.')},
    {'id': 'arxiv:2504.12058', 'kind': 'paper',
     'title': 'ProvSQL: A General System for Keeping Track of the Provenance and Probability of Data',
     'url': 'https://arxiv.org/abs/2504.12058', 'needle': 'https://arxiv.org/abs/2504.12058v3',
     'aliases': ['ProvSQL provenance formalization paper'], 'tags': ['SQL·데이터 검증', '평가·테스트'],
     'year': 2025, 'files': [('docs/provenance-fixtures.md', 1), ('THIRD_PARTY.md', 1)],
     'note': ('The v0.21.0 new application pins arXiv v3 and its formal proof-scope caution for '
              'independently authored synthetic bag/provenance expectations. No benchmark, theorem, '
              'universal SQL correctness claim, Lean execution or ProvSQL runtime is reproduced. '
              'Existing ProvSQL project background remains a separate background reference.')},
    {'id': 'github:pierresenellart/provenance-lean', 'kind': 'project', 'title': 'provenance-lean',
     'url': 'https://github.com/PierreSenellart/provenance-lean', 'aliases': ['Provenance Lean formalization'],
     'tags': ['SQL·데이터 검증', '평가·테스트'],
     'files': [('docs/provenance-fixtures.md', 2), ('THIRD_PARTY.md', 1)],
     'note': ('Pinned at 92af5cf2a057dfb46aab0a364d4ade5fde9c5699 for the v0.21.0 scoped '
              'Dedup/Diff annotation counterexample and positive Diff-free adequacy boundary. '
              'Original small synthetic Python model and literal PostgreSQL bags do not execute '
              'or transfer upstream Lean proofs; no Lean/Mathlib or upstream source is installed or bundled.')},
)
NEW_IDS = {spec['id'] for spec in SPECS}


def evidence_url(commit, file, line):
    return f'{PREFIX}{commit}/{file}#L{line}'


def prepare_update(registry, artwork, read_lines, commit, tag, *, updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected a full lowercase commit SHA and exact tag v0.21.0')
    old_sources = merge_sources(registry['sources'])
    # Raw curation retains separate plugin rows/notes for some shared identities.
    # Validate the published merge, but edit and preserve every raw record below.
    validate_catalog({**registry, 'sources': old_sources})
    old_by_id = {source['id']: source for source in old_sources}
    present_new = NEW_IDS & set(old_by_id)
    for spec in SPECS:
        if canonical_key(spec['url'])['key'] != spec['id']:
            raise ValueError('New source does not match its canonical identity')
        for source in old_sources:
            identity_keys = {source['id'], *source['keys']}
            if source.get('url'):
                identity_keys.add(canonical_key(source['url'])['key'])
            if spec['id'] in identity_keys and source['id'] != spec['id']:
                raise ValueError(f'New canonical identity already belongs to {source["id"]}')
    image_ids = [asset['sourceId'] for asset in artwork['assets']]
    if (artwork['count'] != len(image_ids) or len(set(image_ids)) != len(image_ids)
            or set(image_ids) != set(old_by_id) - present_new):
        raise ValueError('Every prior source needs its exact artwork assignment; six new sources use text fallback')
    for asset in artwork['assets']:
        prior_urls = [row['url'] for use in old_by_id[asset['sourceId']]['uses'] for row in use['evidence']]
        if (asset.get('evidenceUrls') != prior_urls or asset.get('currentEvidenceUrls') != prior_urls
                or not asset.get('generationEvidenceUrls')):
            raise ValueError('Artwork must preserve generation history and every current citation')

    revised, images = deepcopy(registry), deepcopy(artwork)
    cache = {}
    def lines_for(file):
        if file not in cache:
            cache[file] = read_lines(file)
        return cache[file]

    prior_count = repinned_count = moved_count = 0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin'] != PLUGIN:
                continue
            for row in use['evidence']:
                lines = lines_for(row['file'])
                old_line, old_url = row['line'], row['url']
                if old_line <= len(lines) and lines[old_line - 1].strip()[:220] == row['excerpt']:
                    line = old_line
                else:
                    matches = [i + 1 for i, text in enumerate(lines) if text.strip()[:220] == row['excerpt']]
                    if len(matches) != 1:
                        raise ValueError(f'Prior excerpt needs a unique exact match: {source["id"]} / {row["file"]}:{old_line}')
                    line = matches[0]
                url = evidence_url(commit, row['file'], line)
                row.update(line=line, url=url)
                prior_count += 1
                repinned_count += old_url != url
                moved_count += old_line != line

    added_count = 0
    for spec in SPECS:
        rows = []
        needle = spec.get('needle', spec['url'])
        for file, expected_count in spec['files']:
            lines = lines_for(file)
            matches = [i + 1 for i, text in enumerate(lines) if needle in text]
            if len(matches) != expected_count:
                raise ValueError(f'Expected {expected_count} exact citation URL(s): {spec["id"]} / {file}')
            rows.extend({'file': file, 'line': line, 'url': evidence_url(commit, file, line),
                         'excerpt': lines[line - 1].strip()[:220]} for line in matches)
        source = {key: deepcopy(spec[key]) for key in ('id', 'kind', 'title', 'url', 'aliases', 'tags', 'note')}
        source.update(year=spec.get('year'), keys=[spec['id']],
                      uses=[{'plugin': PLUGIN, 'role': 'reference', 'evidence': rows}])
        if spec['id'] in present_new:
            existing = next(item for item in revised['sources'] if item['id'] == spec['id'])
            if existing != source:
                raise ValueError(f'Existing v0.21.0 source differs from the prepared record: {spec["id"]}')
        else:
            revised['sources'].append(source)
            added_count += len(rows)

    revised.setdefault('method', {})['scope'] = SCOPE
    revised['snapshots'][PLUGIN] = {'name': 'Semantic Crosscheck', 'version': tag, 'commit': commit,
                                  'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}'}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    by_id = {source['id']: source for source in merged}
    for asset in images['assets']:
        urls = [row['url'] for use in by_id[asset['sourceId']]['uses'] for row in use['evidence']]
        asset['evidenceUrls'] = urls
        asset['currentEvidenceUrls'] = deepcopy(urls)
    summary = {'priorSxcCitations': prior_count, 'repinnedCitations': repinned_count,
               'remappedLines': moved_count, 'addedCitations': added_count,
               'addedSourceIds': sorted(NEW_IDS - present_new),
               'counts': metrics(merged), 'artworkCount': images['count'],
               'textFallbackSourceIds': sorted(NEW_IDS), 'snapshot': revised['snapshots'][PLUGIN]}
    return revised, images, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tag', required=True, choices=[TAG])
    parser.add_argument('--apply', action='store_true', help='Write registry and current artwork citation mapping; no publishing')
    args = parser.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}', args.commit):
        parser.error('--commit requires a full lowercase SHA')
    def git(*arguments):
        return subprocess.run(['git', '-C', str(args.plugin_root), *arguments],
                              capture_output=True, check=True).stdout.decode('utf8')
    if git('rev-parse', '--verify', 'refs/tags/' + args.tag + '^{commit}').strip() != args.commit:
        raise ValueError('The exact local tag does not resolve to --commit')
    def read_lines(file):
        return git('show', args.commit + ':' + file).splitlines()
    source_path = ROOT / 'data/registry.source.json'
    artwork_path = ROOT / 'docs/card-artwork-unique-prompts.json'
    registry = json.loads(source_path.read_text(encoding='utf8'))
    artwork = json.loads(artwork_path.read_text(encoding='utf8'))
    revised, images, summary = prepare_update(registry, artwork, read_lines, args.commit, args.tag)
    if args.apply:
        write_update([(source_path, revised), (artwork_path, images)])
    print(json.dumps({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
                      'publicAvailability': 'caller must independently verify', **summary}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
