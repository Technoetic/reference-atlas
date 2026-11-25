"""Add the six agentic-vault v0.58.0 primary references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.58.0'
PRIOR_VERSION = 'v0.57.0'
PRIOR_COMMIT = 'a478283b71b455e37fe7fef222101abd386c8c37'
SXC_VERSION = 'v0.34.0'

# PR #26 (Jarvis Telegram removal, included in v0.58.0) retired the README.md
# OpenClaw inspiration row while preserving the historical Jarvis design spec
# in the v0.58.0 tree. Map that single retired row explicitly before repin().
REVIEWED_MOVES = {
    ('github:openclaw/openclaw', 'README.md'): (
        'docs/superpowers/specs/2026-07-17-vault-jarvis-design.md',
        'OpenClaw의 채널 편재성·상시성과',
    ),
}

NEW_SOURCES = [
    dict(
        url='https://arxiv.org/abs/2611.28763',
        other_urls=[],
        kind='paper',
        title='Who Is Prompt-Injecting Coding Agents? An Empirical Study of Hidden AI-Directed Text on GitHub',
        year=2026,
        aliases=['Hidden AI-Directed Text on GitHub', 'GitHub IPI in the Wild'],
        tags=['보안·안전', '신뢰성'],
        note=(
            'Gabi Nakibly & Zvika Babo (2026, arXiv:2611.28763). Empirical study of non-rendered hidden Markdown and '
            'HTML prompt-injection channels on GitHub. Agentic Vault v0.58.0 cites it for linear-time '
            '_strip_hidden_markup() sanitization in hooks/session_start.py and skills/agentic-vault/scripts/vault_doctor.py, '
            'stripping HTML comments, hidden Markdown link-reference comments, and hidden HTML elements from the injected '
            'buffer only (never mutating vault files on disk; preserving fenced code, inline code spans, normal URLs, and '
            'trailing/standalone single-token anchors) before credential redaction and fake-header neutralization.'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://arxiv.org/abs/2611.28763'),
            ('README.md', 'https://arxiv.org/abs/2611.28763'),
        ],
    ),
    dict(
        url='https://doi.org/10.2307/4615733',
        other_urls=[],
        kind='paper',
        title='A Simple Sequentially Rejective Multiple Test Procedure',
        year=1979,
        aliases=['Holm (1979)', 'Holm-Bonferroni'],
        tags=['평가·테스트', '검증'],
        note=(
            'Sture Holm (Scandinavian Journal of Statistics, 1979, doi:10.2307/4615733). Distribution-free step-down '
            'family-wise error rate (FWER) adjustment for multiple hypothesis testing. Agentic Vault v0.58.0 cites it '
            'for holm_bonferroni_adjust() (schema agentic-vault/holm-bonferroni/v1) in scripts/eval_stats.py using only '
            'the Python standard library, keeping existing evaluation defaults and pass/fail gates unchanged.'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://doi.org/10.2307/4615733'),
            ('README.md', 'https://doi.org/10.2307/4615733'),
        ],
    ),
    dict(
        url='https://doi.org/10.1126/science.adi6000',
        other_urls=[],
        kind='paper',
        title='Prediction-Powered Inference',
        year=2023,
        aliases=['PPI (Science 2023)', 'Prediction-Powered Inference'],
        tags=['평가·테스트', '검증'],
        note=(
            'Anastasios N. Angelopoulos, Stephen Bates, Clara Fannjiang, Michael I. Jordan & Tijana Zrnic '
            '(Science, 2023, doi:10.1126/science.adi6000). Statistical framework combining a small gold-labeled sample '
            'with abundant model predictions to construct valid confidence intervals without relying on model unbiasedness. '
            'Agentic Vault v0.58.0 cites it alongside PPI++ and PRECISE for stdlib ppi_pp_mean_ci() '
            '(schema agentic-vault/ppi-pp-mean/v1) in scripts/eval_stats.py.'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://doi.org/10.1126/science.adi6000'),
            ('README.md', 'https://doi.org/10.1126/science.adi6000'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2311.01453',
        other_urls=[],
        kind='paper',
        title='PPI++: Efficient Prediction-Powered Inference',
        year=2023,
        aliases=['PPI++'],
        tags=['평가·테스트', '검증'],
        note=(
            'Anastasios N. Angelopoulos, John C. Duchi & Tijana Zrnic (2023, arXiv:2311.01453). Power-tuned '
            'prediction-powered inference that chooses an optimal scalar weight lambda_hat so variance never degrades '
            'asymptotically below classical estimation when predictions are noisy. Agentic Vault v0.58.0 implements '
            'power-tuned mean and 95% confidence interval estimation (ppi_pp_mean_ci, reporting lambda_hat and '
            'ci_width_ratio) in scripts/eval_stats.py with zero external dependencies.'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://arxiv.org/abs/2311.01453'),
            ('README.md', 'https://arxiv.org/abs/2311.01453'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2601.18777',
        other_urls=[],
        kind='paper',
        title='PRECISE: Reducing the Bias of LLM Evaluations Using Prediction-Powered Ranking Estimation',
        year=2026,
        aliases=['PRECISE'],
        tags=['평가·테스트', '검증'],
        note=(
            'Abhishek Divekar & Anirban Majumder (AAAI/IAAI 2026, arXiv:2601.18777). Applies prediction-powered '
            'inference to debias automated LLM evaluations using small human-audited calibration sets. Agentic Vault '
            'v0.58.0 cites it alongside PPI and PPI++ as the evaluation motivation for descriptive stdlib '
            'ppi_pp_mean_ci() in scripts/eval_stats.py (not used as an automatic pass/fail gate).'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://arxiv.org/abs/2601.18777'),
            ('README.md', 'https://arxiv.org/abs/2601.18777'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2611.24185',
        other_urls=[],
        kind='paper',
        title='Guarding the Kingdom of Skill-Based Agents in the AI Dynasty of Computation: Control-Flow Integrity for Agent Skills',
        year=2026,
        aliases=['SkillCFI'],
        tags=['보안·안전', '에이전트', '신뢰성'],
        note=(
            'Bonan Ruan, Yuhao Sun, Jiahao Liu et al. (2026, arXiv:2611.24185). Skill control-flow integrity study '
            'observing that enumerating legal next steps in policy refusals substantially improves agent recovery. '
            'Agentic Vault v0.58.0 selectively adapts only the deterministic recovery-guidance pattern: appending '
            'pure-ASCII single-line Next legal steps: hints to every deny/ask reason in assets/adapters/deny-guard/deny-guard.py '
            '(engine=0.58.0 with matching ps-parse.ps1, unchanged 3-key hookSpecificOutput schema) and adding content-free '
            'next_legal_steps lists to skills/agentic-vault/scripts/vault_task_contracts.py. It does not claim runtime CFI sandboxing.'
        ),
        cites=[
            ('docs/releases/v0.58.0.md', 'https://arxiv.org/abs/2611.24185'),
            ('README.md', 'https://arxiv.org/abs/2611.24185'),
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
    av_snap = registry['snapshots']['agentic-vault']
    sxc_snap = registry['snapshots']['semantic-crosscheck']
    if sxc_snap['version'] != SXC_VERSION:
        raise ValueError(f'Expected semantic-crosscheck {SXC_VERSION}, got {sxc_snap["version"]}')
    if (av_snap['version'], av_snap['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'This update requires the published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    pre_remapped = {}
    for source in registry['sources']:
        for use in source['uses']:
            if use['plugin'] != 'agentic-vault':
                continue
            for row in use['evidence']:
                move = REVIEWED_MOVES.get((source['id'], row['file']))
                if move is None:
                    continue
                target_file, needle = move
                old_url = row['url']
                replacement = _find_single_line(read_lines, target_file, commit, needle, source['id'])
                row.update(replacement)
                pre_remapped[old_url] = replacement['url']

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    remapped.update(pre_remapped)
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
            uses=[dict(plugin='agentic-vault', role='reference', evidence=evidence)],
        ))
        existing_ids.add(sid)
        existing_keys.update(keys)
        added[sid] = len(evidence)

    av_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
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
