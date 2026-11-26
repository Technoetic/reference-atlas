"""Add the agentic-vault v0.59.0 openai/math reference, repin earlier uses, and register card-246 artwork."""
import argparse
from datetime import datetime, timezone
from functools import cache
import hashlib
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources
from reference_identity import canonical_key, validate_catalog
from update_av048_references import PREFIX, excerpt_of, repin
from update_av0521_references import ARTWORK, CATALOG_CSV, CATALOG_JSON, REGISTRY, built_catalog, encode, write_files


ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.59.0'
PRIOR_VERSION = 'v0.58.0'
PRIOR_COMMIT = '34db74b437ddca715280f7d934d90204405f87c3'
SXC_VERSION = 'v0.35.0'

CARD_SPEC = dict(
    index=246,
    sourceId='github:openai/math',
    title='openai/math — Proof Artifacts and Verification Workflows',
    kind='project',
    label='PROOF ARTIFACT LIFECYCLE',
    factualConcept=(
        'OpenAI math (Apache-2.0, commit 3344da59) documents structured proof withdrawal separating proof retraction '
        'from claim falsity, preserved superseded editions, exact verification-bundle tree membership with zero-count '
        'negative evidence, and immutable spec vs solution separation; Agentic Vault v0.59.0 selectively adapts these '
        'patterns into vault_lifecycle.py, verify_release_claims.py, and vault_coverage.py.'
    ),
    prompt=(
        'Macro isometric three-quarter studio product photograph on a near-black olive surface (#10130f) showing a '
        'precision brushed-graphite archival verification ledger tray divided by a slim machined silver divider rail: '
        'on the left side sits an immutable frosted-glass theorem specification block sealed under a fine luminous-lime '
        'optical verification frame beside a recessed empty silver zero-defect check trough, while on the right side '
        'three stepped translucent archival proof plates stand in sequence—the rearmost smoked-glass plate marked '
        'withdrawn with a delicate restrained amber ring, the middle frosted-lavender plate linked forward by a thin '
        'brushed-silver supersession bridge pin to the crisp luminous-lime replacement plate in front; dramatic soft '
        'studio rim lighting, crisp shallow depth of field, zero text, zero letters, zero digits, zero mathematical '
        'symbols, zero logos, zero borders.'
    ),
    output='media/cards/card-246-openai-math.webp',
    sourceSha256='2be29e7f311bc53a62ee683a9655d96c9e60f9575d83c7b1bdd0fd912c73bdf9',
    sourceDimensions=[1264, 848],
)

NEW_SOURCES = [
    dict(
        url='https://github.com/openai/math',
        other_urls=[],
        kind='project',
        title='openai/math — Proof Artifacts and Verification Workflows',
        year=2026,
        aliases=['openai/math', 'OpenAI Math Archive'],
        tags=['검증', '신뢰성', '지식관리'],
        note=(
            'OpenAI (2026, Apache-2.0, commit 3344da59). Public repository of mathematical research artifacts, '
            'proof-verification workflows, and structured withdrawal/supersession records. Agentic Vault v0.59.0 '
            'selectively adapts three Python stdlib-only patterns: (1) opt-in read-only note withdrawal & supersession '
            'lifecycle auditing (skills/agentic-vault/scripts/vault_lifecycle.py, docs/note-lifecycle.md) with '
            'withdrawal_scope=proof_or_evidence_only, pinned 40/64-hex withdrawn_revision, O(N) supersession chains, '
            'and bounded cascade dependents; (2) check_exact_tree_membership() and required zero-count negative-evidence '
            'verification plus --require-independent-review in scripts/verify_release_claims.py; and (3) opt-in '
            'review_status, automation_methods, pinned immutable spec_files vs disjoint solution_files separation, and '
            'permitted_gaps allowlists in skills/agentic-vault/scripts/vault_coverage.py.'
        ),
        cites=[
            ('docs/releases/v0.59.0.md', 'https://github.com/openai/math'),
            ('README.md', 'https://github.com/openai/math'),
            ('docs/note-lifecycle.md', 'https://github.com/openai/math'),
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


def prepare(registry, artwork, commit, read_lines, card_path):
    av_snap = registry['snapshots']['agentic-vault']
    sxc_snap = registry['snapshots']['semantic-crosscheck']
    if sxc_snap['version'] != SXC_VERSION:
        raise ValueError(f'Expected semantic-crosscheck {SXC_VERSION}, got {sxc_snap["version"]}')
    if (av_snap['version'], av_snap['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'This update requires the published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]

    existing_ids = {s['id'] for s in registry['sources']}
    existing_keys = {k for s in registry['sources'] for k in s.get('keys', [s['id']])}
    added = {}
    new_evidence_urls = []
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
        new_evidence_urls = [row['url'] for row in evidence]
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

    card_bytes = card_path.read_bytes()
    card_sha = hashlib.sha256(card_bytes).hexdigest()
    artwork['assets'].append(dict(
        index=CARD_SPEC['index'],
        sourceId=CARD_SPEC['sourceId'],
        title=CARD_SPEC['title'],
        kind=CARD_SPEC['kind'],
        label=CARD_SPEC['label'],
        factualConcept=CARD_SPEC['factualConcept'],
        prompt=CARD_SPEC['prompt'],
        output=CARD_SPEC['output'],
        sha256=card_sha,
        bytes=len(card_bytes),
        dimensions=[960, 640],
        evidenceUrls=list(new_evidence_urls),
        generationEvidenceUrls=list(new_evidence_urls),
        currentEvidenceUrls=list(new_evidence_urls),
        delivery=dict(
            sourceSha256=CARD_SPEC['sourceSha256'],
            sourceDimensions=list(CARD_SPEC['sourceDimensions']),
            operation='Full-frame Lanczos resize and WebP encoding only; no crop, compositing or semantic edit',
            tool='Pillow 12.3.0 (Python WebP encoder)',
            quality=90,
            compressionLevel=6,
            commandTemplate=(
                "python -c \"from PIL import Image; Image.open('INPUT').convert('RGB')"
                ".resize((960, 640), Image.Resampling.LANCZOS)"
                ".save('OUTPUT.webp', format='WEBP', quality=90, method=6)\""
            ),
        ),
        generationReferenceUrls=['https://github.com/openai/math'],
    ))
    artwork['count'] = len(artwork['assets'])

    av_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(rebound=prior_rows, moved=moved, added=added, card_sha256=card_sha, card_bytes=len(card_bytes))


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

    card_path = ROOT / CARD_SPEC['output']
    if not card_path.is_file():
        parser.error(f'Missing rendered card image: {card_path}')

    registry = json.loads((ROOT / REGISTRY).read_text(encoding='utf-8'))
    artwork = json.loads((ROOT / ARTWORK).read_text(encoding='utf-8'))
    report = prepare(registry, artwork, args.commit, read_lines, card_path)
    encoded = encode(registry)
    catalog_json, catalog_csv = built_catalog(encoded)
    if args.apply:
        write_files({ROOT / REGISTRY: encoded, ROOT / ARTWORK: encode(artwork),
                     ROOT / CATALOG_JSON: catalog_json, ROOT / CATALOG_CSV: catalog_csv})
    print(json.dumps(dict(**report, applied=args.apply), ensure_ascii=False))


if __name__ == '__main__':
    main()
