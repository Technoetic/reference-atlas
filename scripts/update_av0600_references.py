"""Add the five agentic-vault v0.60.0 references, repin earlier uses, and register card-247..251 artwork."""
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
TAG = 'v0.60.0'
PRIOR_VERSION = 'v0.59.0'
PRIOR_COMMIT = '0ce51c04924170a0ef5341e4225ee9fe9798a621'
SXC_VERSION = 'v0.36.0'

CARD_SPECS = [
    dict(
        index=247,
        sourceId='arxiv:2602.10498',
        title='When Skills Lie: Hidden-Comment Injection in LLM Agents',
        kind='paper',
        label='HIDDEN COMMENT FILTERING',
        factualConcept=(
            'Wang et al. (2026) document hidden-comment prompt injection in rendered Markdown and agent skills; '
            'Agentic Vault v0.60.0 extends linear-time _strip_hidden_markup() in hooks/session_start.py and '
            'vault_doctor.py to strip Obsidian %% ... %% comments, zero-dimension <svg> elements, and <svg>-scoped '
            'non-rendered metadata (<desc>/<title>/<metadata>) from the injected buffer while preserving code fences, '
            'inline code, single %, and vault files on disk.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite optical inspection track: a sleek translucent frosted-glass document '
            'slab glides smoothly under a slim machined-silver dual-beam inspection bridge; tiny dark-amber concealed '
            'glass shards wedged along its underside are cleanly deflected sideways into a recessed graphite rejection '
            'channel, while intact luminous-lime (#d3fc70) crystalline text blocks and two protective frosted-lavender '
            '(#c3b0f6) enclosed code capsules pass completely untouched through the illuminated optical aperture; '
            'refined tactile brushed metal and optical glass materials, dramatic soft studio rim lighting, shallow '
            'depth of field, centered crop-safe composition with generous dark olive margins, zero text, zero letters, '
            'zero digits, zero mathematical symbols, zero icons, zero logos, zero borders.'
        ),
        output='media/cards/card-247-when-skills-lie.webp',
        sourceSha256='c2020e7f38c6367f227b8ad2315c59029f409681892f063330a3e1bbd5acd3ed',
        sourceDimensions=[1264, 848],
        refUrl='https://arxiv.org/abs/2602.10498',
    ),
    dict(
        index=248,
        sourceId='arxiv:2611.32195',
        title='When Answering Is Administering: Permission Replies That Rewrite Coding-Agent Policy',
        kind='paper',
        label='DENY RULE MONOTONICITY',
        factualConcept=(
            'Fei et al. (2026) demonstrate how permission replies in coding-agent clients can silently delete or '
            'weaken operator deny rules in settings.json; Agentic Vault v0.60.0 adds read-only content-free '
            'permissions.deny monotonicity and hooks-config auditing in skills/agentic-vault/scripts/vault_policy_drift.py '
            'and opt-in fail-soft vault_doctor.py --policy-drift.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite monotonic policy-ratchet rail: five tall crystalline luminous-lime '
            '(#d3fc70) barrier pins stand seated in calibrated silver slots guarded by a delicate one-way brushed-silver '
            'mechanical pawl allowing additional lime pins to slide into an open right-hand slot while blocking backward '
            'removal; beside the rail rests a separate frosted-lavender (#c3b0f6) permission tray where a small restrained '
            'amber glass wedge attempts to lift one barrier pin from its socket, causing a single subtle amber optical '
            'prism along the sealed baseline plinth to catch soft studio light; tactile machined graphite, brushed silver, '
            'optical glass, dramatic controlled studio rim lighting, shallow depth of field, centered crop-safe '
            'composition with generous dark margins, zero text, zero letters, zero digits, zero padlocks, zero shields, '
            'zero icons, zero logos, zero borders.'
        ),
        output='media/cards/card-248-when-answering-is-administering.webp',
        sourceSha256='89f3cce03e2dc2d668146e61bbe23879a493f7bcd25db5cd0a6cc0b5f2b540f5',
        sourceDimensions=[1264, 848],
        refUrl='https://arxiv.org/abs/2611.32195',
    ),
    dict(
        index=249,
        sourceId='arxiv:2611.01976',
        title='Beyond Prompt Injection: The Tool Update Gap in LLM Agent Security',
        kind='paper',
        label='POST-TRUST HOOK HASH DRIFT',
        factualConcept=(
            'Kan et al. (2026) analyze post-trust mutations to external tool and hook scripts outside the LLM context '
            'window (ETUDE); Agentic Vault v0.60.0 seals content-free SHA-256 digests of settings hooks, managed vault '
            'git hooks, and bundled plugin hooks in 00-meta/.vault-policy-baseline.json via vault_policy_drift.py and '
            'flags script modification, removal, unsafe links/UNC paths, and untracked hook targets read-only.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite optical fingerprint comparator: two parallel machined trays sit beneath '
            'a suspended clear glass reference lens bar; the rear sealed baseline tray holds three matching faceted '
            'translucent crystal cylinders glowing with calm luminous-lime (#d3fc70) internal edges, while the front '
            'live tray holds two identical luminous-lime crystal cylinders and a third cylinder whose exterior '
            'frosted-lavender (#c3b0f6) silhouette matches the others yet reveals a subtly misaligned warm-amber '
            'internal core refracting off a thin brushed-silver reference beam; ultra-clean scientific laboratory exhibit '
            'aesthetic, tactile metal and glass refraction, soft studio key and rim lighting, shallow depth of field, '
            'centered crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, '
            'zero warnings, zero icons, zero logos, zero borders.'
        ),
        output='media/cards/card-249-tool-update-gap.webp',
        sourceSha256='a622d4d747564d4088a9740f906bacb50ccb175c2d8cdd40b4106c6421d6574e',
        sourceDimensions=[1264, 848],
        refUrl='https://arxiv.org/abs/2611.01976',
    ),
    dict(
        index=250,
        sourceId='arxiv:2605.14478',
        title='When Retrieval Hurts Code Completion: A Diagnostic Study of Stale Repository Context',
        kind='paper',
        label='STALE RETRIEVAL EXCLUSION',
        factualConcept=(
            'Weng et al. (2026) diagnose how retrieving stale repository artifacts sharply raises compatibility errors; '
            'Agentic Vault v0.60.0 propagates v0.59.0 frontmatter status: withdrawn | superseded non-breakingly into '
            'vault_retrieval.py (--as-of exclusion, lifecycle_status annotations, opt-in --exclude-withdrawn and '
            '--exclude-superseded) and vault_healthcheck.py (opt-in --exclude-retired and '
            'exclude_retired_from_active_checks).'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision stepped temporal retrieval sieve crafted from brushed graphite and clear optical glass: '
            'a graceful curved brushed-silver temporal divider rail cleanly separates a front active gallery holding '
            'three crisp luminous-lime (#d3fc70) optical glass specimen blocks from a rear recessed compartment holding '
            'two dimmed smoked-glass and frosted-lavender (#c3b0f6) retired slabs edged with a fine restrained amber '
            'glass stop-bar so outdated blocks cannot slide forward into the illuminated front retrieval channel; '
            'refined architectural miniature still-life, crisp glass refraction, dramatic soft studio rim lighting, '
            'shallow depth of field, centered crop-safe composition with generous dark margins, zero text, zero letters, '
            'zero digits, zero clocks, zero calendars, zero icons, zero logos, zero borders.'
        ),
        output='media/cards/card-250-stale-repository-context.webp',
        sourceSha256='7d8ff3fe045c50ac21569a9c86dfc8cf26813a063e7649452809adafabe129a9',
        sourceDimensions=[1264, 848],
        refUrl='https://arxiv.org/abs/2605.14478',
    ),
    dict(
        index=251,
        sourceId='github:ccf/agentcairn',
        title='ccf/agentcairn — Vault-Backed Agent Memory with Superseded-Note Deprioritization',
        kind='project',
        label='VAULT CAIRN RETIREMENT',
        factualConcept=(
            'ccf/agentcairn (Apache-2.0) demonstrates Obsidian-vault agent memory that distinguishes superseded notes '
            'in graph and retrieval workflows; Agentic Vault v0.60.0 connects v0.59.0 withdrawn/superseded frontmatter '
            'non-breakingly into vault_retrieval.py, vault_recall.py, and vault_healthcheck.py while keeping legacy '
            'default outputs unchanged.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing an architectural miniature glass-and-metal cairn specimen: four precision-milled brushed-graphite '
            'and clear optical glass slabs interleaved with thin luminous-lime (#d3fc70) luminous layers stand stacked '
            'in a balanced stepped beacon upon a slim brushed-silver baseplate, while two quieter frosted-lavender '
            '(#c3b0f6) superseded tiles rest neatly separated on a lower stepped side terrace connected back to the '
            'main cairn by a single delicate brushed-silver lineage pin and a muted amber collar so historical lineage '
            'remains visible without entering the active stack; museum-grade studio product photography, tactile matte '
            'graphite and translucent glass, soft cinematic rim lighting, shallow depth of field, centered crop-safe '
            'composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero borders.'
        ),
        output='media/cards/card-251-ccf-agentcairn.webp',
        sourceSha256='cdb0aa4d7f0551e329a083213b597fdd55dc5d2a4381e8df7905f473ca333da4',
        sourceDimensions=[1264, 848],
        refUrl='https://github.com/ccf/agentcairn',
    ),
]

NEW_SOURCES = [
    dict(
        url='https://arxiv.org/abs/2602.10498',
        other_urls=[],
        kind='paper',
        title='When Skills Lie: Hidden-Comment Injection in LLM Agents',
        year=2026,
        aliases=['When Skills Lie', 'arXiv:2602.10498', 'Hidden-Comment Injection in LLM Agents'],
        tags=['보안·안전', '에이전트', '지식관리'],
        note=(
            'Qianli Wang, Boyang Ma et al. (2026, arXiv:2602.10498v1). Demonstrates hidden-comment prompt injection in '
            'Markdown documents and agent skills invisible to human readers. Agentic Vault v0.60.0 extends linear-time '
            '_strip_hidden_markup() in hooks/session_start.py (shared by vault_doctor.py) to strip Obsidian %% ... %% '
            'inline/multiline/unclosed comments, zero-dimension <svg> elements (attribute and CSS width:0/height:0 with '
            'exact HTML5 §13.2.5.32-40 self-closing state machine), and <svg>-scoped <desc>/<title>/<metadata> from the '
            'injected SessionStart buffer only while preserving fenced code, inline code spans, single %, and vault files.'
        ),
        cites=[
            ('docs/releases/v0.60.0.md', 'https://arxiv.org/abs/2602.10498'),
            ('README.md', 'https://arxiv.org/abs/2602.10498'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2611.32195',
        other_urls=[],
        kind='paper',
        title='When Answering Is Administering: Permission Replies That Rewrite Coding-Agent Policy',
        year=2026,
        aliases=['When Answering Is Administering', 'arXiv:2611.32195'],
        tags=['보안·안전', '신뢰성', '에이전트'],
        note=(
            'Zeming Fei, Hongming Fei et al. (2026, arXiv:2611.32195v1). Shows across 10 coding-agent clients that '
            'permission-prompt replies can silently delete or weaken operator permissions.deny rules in settings.json. '
            'Agentic Vault v0.60.0 adds opt-in offline read-only skills/agentic-vault/scripts/vault_policy_drift.py '
            '(docs/policy-drift.md) and fail-soft vault_doctor.py --policy-drift to seal content-free permissions.deny '
            'SHA-256 sets and canonical hooks_config_sha256 in 00-meta/.vault-policy-baseline.json, allowing monotonic '
            'deny additions while flagging deny deletions, missing/invalid settings, and hooks-config tampering.'
        ),
        cites=[
            ('docs/releases/v0.60.0.md', 'https://arxiv.org/abs/2611.32195'),
            ('README.md', 'https://arxiv.org/abs/2611.32195'),
            ('docs/policy-drift.md', 'https://arxiv.org/abs/2611.32195'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2611.01976',
        other_urls=[],
        kind='paper',
        title='Beyond Prompt Injection: The Tool Update Gap in LLM Agent Security',
        year=2026,
        aliases=['ETUDE', 'Tool Update Gap', 'arXiv:2611.01976'],
        tags=['보안·안전', '신뢰성', '에이전트'],
        note=(
            'Shiyu Kan, Yue Qi et al. (2026, arXiv:2611.01976v1). Evaluates post-trust mutations to external tool and '
            'hook code outside the LLM context window (ETUDE). Agentic Vault v0.60.0 tracks SHA-256 digests of '
            'settings-referenced hooks, managed vault git hooks (00-meta/scripts/git-hooks/pre-commit, pre-push, and '
            'vault_healthcheck.py), and bundled plugin hooks in vault_policy_drift.py, flagging modified, missing, '
            'untracked, or symlinked/junctioned/hardlinked/UNC hook targets fail-closed without executing hooks.'
        ),
        cites=[
            ('docs/releases/v0.60.0.md', 'https://arxiv.org/abs/2611.01976'),
            ('README.md', 'https://arxiv.org/abs/2611.01976'),
            ('docs/policy-drift.md', 'https://arxiv.org/abs/2611.01976'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2605.14478',
        other_urls=[],
        kind='paper',
        title='When Retrieval Hurts Code Completion: A Diagnostic Study of Stale Repository Context',
        year=2026,
        aliases=['Stale Repository Context', 'arXiv:2605.14478'],
        tags=['메모리·검색', '신뢰성', '지식관리'],
        note=(
            'Haojun Weng et al. (2026, arXiv:2605.14478v1). Diagnoses how stale repository context returned by retrieval '
            'causes sharp compatibility error increases. Agentic Vault v0.60.0 connects v0.59.0 frontmatter status: '
            'withdrawn | superseded non-breakingly into vault_retrieval.py (--as-of exclusion of withdrawn and unbounded '
            'superseded notes, lifecycle_status annotation, opt-in --exclude-withdrawn / --exclude-superseded) and '
            'vault_healthcheck.py (opt-in --exclude-retired and exclude_retired_from_active_checks for §7/§8).'
        ),
        cites=[
            ('docs/releases/v0.60.0.md', 'https://arxiv.org/abs/2605.14478'),
            ('README.md', 'https://arxiv.org/abs/2605.14478'),
        ],
    ),
    dict(
        url='https://github.com/ccf/agentcairn',
        other_urls=[],
        kind='project',
        title='ccf/agentcairn — Vault-Backed Agent Memory with Superseded-Note Deprioritization',
        year=2026,
        aliases=['ccf/agentcairn', 'agentcairn'],
        tags=['메모리·검색', '에이전트', '지식관리'],
        note=(
            'Open-source Apache-2.0 Obsidian-vault agent memory workflow that explicitly separates and deprioritizes '
            'superseded notes in retrieval and graph traversal. Referenced in Agentic Vault v0.60.0 for non-breaking '
            'propagation of frontmatter status: withdrawn | superseded into vault_retrieval.py, vault_recall.py, and '
            'vault_healthcheck.py while preserving default legacy outputs.'
        ),
        cites=[
            ('docs/releases/v0.60.0.md', 'https://github.com/ccf/agentcairn'),
            ('README.md', 'https://github.com/ccf/agentcairn'),
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


def prepare(registry, artwork, commit, read_lines, root=ROOT):
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
    evidence_by_id = {}
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
        evidence_by_id[sid] = [row['url'] for row in evidence]
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

    card_digests = {}
    for spec in CARD_SPECS:
        card_path = root / spec['output']
        if not card_path.is_file():
            raise ValueError(f'Missing rendered card image: {card_path}')
        card_bytes = card_path.read_bytes()
        card_sha = hashlib.sha256(card_bytes).hexdigest()
        ev_urls = list(evidence_by_id[spec['sourceId']])
        artwork['assets'].append(dict(
            index=spec['index'],
            sourceId=spec['sourceId'],
            title=spec['title'],
            kind=spec['kind'],
            label=spec['label'],
            factualConcept=spec['factualConcept'],
            prompt=spec['prompt'],
            output=spec['output'],
            sha256=card_sha,
            bytes=len(card_bytes),
            dimensions=[960, 640],
            evidenceUrls=list(ev_urls),
            generationEvidenceUrls=list(ev_urls),
            currentEvidenceUrls=list(ev_urls),
            delivery=dict(
                sourceSha256=spec['sourceSha256'],
                sourceDimensions=list(spec['sourceDimensions']),
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
            generationReferenceUrls=[spec['refUrl']],
        ))
        card_digests[spec['sourceId']] = dict(sha256=card_sha, bytes=len(card_bytes))
    artwork['count'] = len(artwork['assets'])

    av_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(rebound=prior_rows, moved=moved, added=added, cards=card_digests)


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
    report = prepare(registry, artwork, args.commit, read_lines, ROOT)
    encoded = encode(registry)
    catalog_json, catalog_csv = built_catalog(encoded)
    if args.apply:
        write_files({ROOT / REGISTRY: encoded, ROOT / ARTWORK: encode(artwork),
                     ROOT / CATALOG_JSON: catalog_json, ROOT / CATALOG_CSV: catalog_csv})
    print(json.dumps(dict(**report, applied=args.apply), ensure_ascii=False))


if __name__ == '__main__':
    main()
