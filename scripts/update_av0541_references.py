"""Add the agentic-vault v0.54.1 references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.54.1'
PRIOR_VERSION = 'v0.54.0'
PRIOR_COMMIT = '2b35dc0635edb453077aecebac5717e05afe25c8'
RELEASE = 'docs/releases/v0.54.1.md'
SECURITY = 'SECURITY.md'
RELEASE_INTEGRITY = 'docs/release-integrity.md'

TROJAN_URL = 'https://www.usenix.org/conference/usenixsecurity23/presentation/boucher'
UTS39_URL = 'https://www.unicode.org/reports/tr39/'
BAD_CHARS_URL = 'https://arxiv.org/abs/2106.09898'
ACTIONLINT_URL = 'https://github.com/rhysd/actionlint'
PILLAI_ID = 'url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai'


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

    trojan_key = canonical_key(TROJAN_URL)['key']
    trojan_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: TROJAN_URL in s, 'Trojan Source'),
        _find_single_line(read_lines, SECURITY, commit, lambda s: TROJAN_URL in s, 'Trojan Source'),
    ]
    registry['sources'].append(dict(
        id=trojan_key,
        kind='paper',
        title='Trojan Source: Invisible Vulnerabilities',
        url=TROJAN_URL,
        year=2023,
        keys=[trojan_key],
        aliases=['Trojan Source', 'Boucher & Anderson (USENIX Security 2023)'],
        tags=['보안·안전'],
        note=(
            'Nicholas Boucher and Ross Anderson (USENIX Security 2023) demonstrate how Unicode '
            'bidirectional control characters alter visual rendering relative to logical token order. '
            'Agentic Vault v0.54.1 expands SessionStart, vault_doctor, and static repo hygiene checks '
            'to strip directional marks (U+061C, U+200E, U+200F) alongside bidi overrides and isolates.'
        ),
        uses=[dict(plugin='agentic-vault', role='reference', evidence=trojan_rows)],
    ))

    uts39_key = canonical_key(UTS39_URL)['key']
    uts39_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: UTS39_URL in s, 'Unicode UTS #39'),
        _find_single_line(read_lines, SECURITY, commit, lambda s: UTS39_URL in s, 'Unicode UTS #39'),
    ]
    registry['sources'].append(dict(
        id=uts39_key,
        kind='format',
        title='Unicode Technical Standard #39: Unicode Security Mechanisms',
        url=UTS39_URL,
        year=2026,
        keys=[uts39_key],
        aliases=['UTS #39', 'Unicode Security Mechanisms'],
        tags=['보안·안전'],
        note=(
            'Unicode Technical Standard #39 (Unicode 18.0.0) catalogs Default_Ignorable and confusable '
            'security hazards. Agentic Vault v0.54.1 adds seven Default_Ignorable code points '
            '(U+00AD, U+034F, U+061C, U+200E, U+200F, U+3164, U+FFA0) to SessionStart and CI hygiene stripping '
            'while documenting visual homoglyphs as a residual boundary.'
        ),
        uses=[dict(plugin='agentic-vault', role='reference', evidence=uts39_rows)],
    ))

    bad_chars_key = canonical_key(BAD_CHARS_URL)['key']
    bad_chars_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: BAD_CHARS_URL in s, 'Bad Characters'),
        _find_single_line(read_lines, SECURITY, commit, lambda s: BAD_CHARS_URL in s, 'Bad Characters'),
    ]
    registry['sources'].append(dict(
        id=bad_chars_key,
        kind='paper',
        title='Bad Characters: Imperceptible NLP Attacks',
        url=BAD_CHARS_URL,
        year=2022,
        keys=[bad_chars_key],
        aliases=['Bad Characters', 'Boucher et al. (IEEE S&P 2022)'],
        tags=['보안·안전'],
        note=(
            'Boucher et al. (IEEE S&P 2022, arXiv:2106.09898) analyze invisible character and control '
            'perturbations against language models. Agentic Vault v0.54.1 strips seven additional '
            'invisible Default_Ignorable code points (including U+034F CGJ) before secret redaction and '
            'fake-header neutralization in SessionStart and vault_doctor.'
        ),
        uses=[dict(plugin='agentic-vault', role='reference', evidence=bad_chars_rows)],
    ))

    actionlint_key = canonical_key(ACTIONLINT_URL)['key']
    actionlint_rows = [
        _find_single_line(read_lines, RELEASE, commit, lambda s: ACTIONLINT_URL in s, 'rhysd/actionlint'),
        _find_single_line(read_lines, RELEASE_INTEGRITY, commit, lambda s: ACTIONLINT_URL in s, 'rhysd/actionlint'),
    ]
    registry['sources'].append(dict(
        id=actionlint_key,
        kind='project',
        title='rhysd/actionlint',
        url=ACTIONLINT_URL,
        year=2026,
        keys=[actionlint_key],
        aliases=['actionlint'],
        tags=['보안·안전', '검증'],
        note=(
            'rhysd/actionlint v1.7.12 (MIT) statically checks GitHub Actions workflow syntax, expressions, '
            'and shell scripts. Agentic Vault v0.54.1 adds a SHA-256 checksum-verified advisory actionlint '
            'step to its read-only supply-chain-audit CI job alongside zizmor and hash-checked pip-audit.'
        ),
        uses=[dict(plugin='agentic-vault', role='reference', evidence=actionlint_rows)],
    ))

    pillai_matches = [s for s in registry['sources'] if s['id'] == PILLAI_ID]
    if len(pillai_matches) != 1:
        raise ValueError(f'Expected existing {PILLAI_ID} entry in registry, found {len(pillai_matches)}')
    pillai = pillai_matches[0]
    pillai_row = _find_single_line(
        read_lines,
        RELEASE,
        commit,
        lambda s: 'usenix.org/conference/osdi14/technical-sessions/presentation/pillai' in s,
        'Pillai et al. (OSDI 2014)',
    )
    av_use = next(u for u in pillai['uses'] if u['plugin'] == 'agentic-vault')
    av_use['evidence'].append(pillai_row)
    pillai['note'] = (
        'Application-level interrupted-operation reasoning informs cooperating Markdown journal recovery '
        '(v0.42.0) and POSIX parent-directory fsync durability in backup_vault.py snapshot publish and restore '
        '(v0.54.1); not filesystem-wide atomicity or reproduced crash-consistency results.'
    )
    for asset in artwork['assets']:
        if asset['sourceId'] == PILLAI_ID:
            for field in ('evidenceUrls', 'currentEvidenceUrls'):
                asset[field].append(pillai_row['url'])
            break

    snapshot.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(
        rebound=prior_rows,
        moved=moved,
        added={
            trojan_key: len(trojan_rows),
            uts39_key: len(uts39_rows),
            bad_chars_key: len(bad_chars_rows),
            actionlint_key: len(actionlint_rows),
            PILLAI_ID: 1,
        },
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
