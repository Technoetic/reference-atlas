"""Repin node-pg-defense to v0.3.0 and attach 25 cross-axis shared references from docs/references.md."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from build_catalog import build, merge_sources
from reference_identity import canonical_key, validate_catalog
from update_av048_references import excerpt_of

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'node-pg-defense'
PLUGIN_NAME = 'Node PG Defense'
VERSION = 'v0.3.0'
REF_FILE = 'docs/references.md'

# 25 existing Reference Atlas sources newly cross-linked to Node PG Defense v0.3.0.
# Every entry records only what v0.3.0 actually implemented without claiming copied code or reproduced benchmarks.
CROSS_LINK_NOTES = {
    'url:https://www.usenix.org/conference/usenixsecurity23/presentation/boucher': (
        'Node PG Defense v0.3.0 adds zero-dependency bidirectional Unicode control detection in lib/unicode.cjs '
        '(refusing automatic apply without echoing source, checking shadow-stripped lines in lib/controls.cjs, and '
        'enforcing repository Unicode hygiene in test/integrity.test.cjs).'
    ),
    'arxiv:2106.09898': (
        'Node PG Defense v0.3.0 detects and shadow-strips dangerous Default_Ignorable and Unicode Tag smuggling code '
        'points (U+E0000-U+E007F, U+200B-U+200D, U+2060-U+2064, U+00AD, U+034F) in lib/unicode.cjs and lib/controls.cjs.'
    ),
    'url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai': (
        'Node PG Defense v0.3.0 applies durability ordering in lib/workspace.cjs by fsyncing .bak backup files before '
        'committing journal.json and issuing POSIX O_DIRECTORY fsyncs around staging-to-transaction renames and atomic '
        'source replacements.'
    ),
    'doi:10.1145/3689031.3696064': (
        'Node PG Defense v0.3.0 expands scripts/verify-postgres.cjs live PostgreSQL 17 checks with empty string, '
        'backslash, whitespace, combining Unicode, and JS null/undefined string-coercion boundary probes.'
    ),
    'arxiv:1411.6704': (
        'Node PG Defense v0.3.0 adapts differential boundary and multi-predicate AND oracle fixtures in '
        'scripts/verify-postgres.cjs against an ephemeral PostgreSQL 17 instance.'
    ),
    'arxiv:2611.01976': (
        'Node PG Defense v0.3.0 adds test-time SHA-256 verification of bundled vendor/acorn.cjs against '
        'vendor/README.md in test/integrity.test.cjs.'
    ),
    'arxiv:2611.24185': (
        'Node PG Defense v0.3.0 adapts deterministic content-free nextLegalSteps recovery guidance alongside errorCode '
        'in scripts/pg-defense.cjs CLI error responses.'
    ),
    'arxiv:2611.28763': (
        'Node PG Defense v0.3.0 adds an explicit untrusted-repository boundary section to '
        'skills/node-pg-defense/SKILL.md so target comments, READMEs, and hidden markup are treated strictly as data.'
    ),
    'arxiv:2602.10498': (
        'Node PG Defense v0.3.0 cites hidden-comment injection risks in docs/references.md for '
        'skills/node-pg-defense/SKILL.md, which treats target comments as untrusted data and requires raw code-point '
        'inspection whenever unicodeFindings are reported.'
    ),
    'arxiv:2403.14720': (
        'Node PG Defense v0.3.0 cites Spotlighting conceptually in docs/references.md for the untrusted-data versus '
        'execution-instruction boundary guidance in skills/node-pg-defense/SKILL.md (without claiming datamarking or '
        'encoding).'
    ),
    'arxiv:2510.09023': (
        'Node PG Defense v0.3.0 cites adaptive prompt-injection limits in SECURITY.md and docs/references.md, and '
        'documents in skills/node-pg-defense/SKILL.md that write safety relies on deterministic engine checks rather '
        'than prompt wording alone.'
    ),
    'github:madthanu/alice': (
        'Node PG Defense v0.3.0 references ALICE conceptually alongside Pillai et al. (OSDI 2014) for backup-file and '
        'POSIX directory fsync ordering in lib/workspace.cjs; no ALICE code or dependency is copied.'
    ),
    'github:sqlancer/sqlancer': (
        'Node PG Defense v0.3.0 references SQLancer conceptually for differential result-set and injection-rejection '
        'oracle checks in scripts/verify-postgres.cjs; no SQLancer code or dependency is copied.'
    ),
    'github:openai/math': (
        'Node PG Defense v0.3.0 adapts exact root-tree membership auditing, vendored-parser SHA-256 checking, and '
        'relocated-CWD portability execution tests in test/integrity.test.cjs with zero runtime dependencies.'
    ),
    'github:sourcegraph/sourcegraph-public-snapshot': (
        'Node PG Defense v0.3.0 adopts typed skipped reasonCode entries and summary.skippedByReason counts in '
        'lib/workspace.cjs and scripts/pg-defense.cjs to distinguish skipped files from inspected clean files.'
    ),
    'github:sourcegraph/zoekt': (
        'Node PG Defense v0.3.0 cites Zoekt alongside Sourcegraph for separating searched-and-absent files from '
        'reason-coded skipped files (oversized, binary, invalid_utf8, symlink, unreadable).'
    ),
    'github:rhysd/actionlint': (
        'Node PG Defense v0.3.0 runs the SHA-256 verified rhysd/actionlint v1.7.12 linux_amd64 binary in its CI '
        'hygiene job (.github/workflows/verify.yml) with zero runtime dependencies.'
    ),
    'github:zizmorcore/zizmor': (
        'Node PG Defense v0.3.0 runs pinned zizmor 1.32.0 --offline on .github/workflows/verify.yml in its CI hygiene '
        'job with zero runtime dependencies.'
    ),
    'url:https://www.unicode.org/reports/tr39': (
        'Node PG Defense v0.3.0 enforces UTS #39 dangerous Default_Ignorable and Bidi controls detection in '
        'lib/unicode.cjs, lib/controls.cjs, scripts/pg-defense.cjs, and test/integrity.test.cjs.'
    ),
    'url:https://www.postgresql.org/docs/17/ddl-partitioning.html': (
        'Node PG Defense v0.3.0 extends Control 19 (lib/controls.cjs and docs/controls.md) to surface declarative '
        'partition definitions (PARTITION OF, ATTACH PARTITION, CREATE/ALTER TABLE ... PARTITION BY) for child RLS review.'
    ),
    'url:https://www.postgresql.org/docs/17/catalog-pg-class.html': (
        'Node PG Defense v0.3.0 extends Control 19 to surface CREATE [OR REPLACE] RULE declarations for table rewrite '
        'rule review alongside RLS policies.'
    ),
    'url:https://www.postgresql.org/docs/17/catalog-pg-constraint.html': (
        'Node PG Defense v0.3.0 extends Control 19 to surface constraint-scoped NOT VALID declarations so unvalidated '
        'CHECK and FOREIGN KEY constraints are reviewed explicitly.'
    ),
    'url:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets': (
        'Node PG Defense v0.3.0 protects release tags under refs/tags/v* with an active update/deletion-blocking '
        'ruleset documented in SECURITY.md.'
    ),
    'url:https://slsa.dev/spec/v1.2/source-requirements': (
        'Node PG Defense v0.3.0 cites SLSA v1.2 Source tag-immutability principles in docs/references.md alongside '
        'the refs/tags/v* ruleset and admin-override limit disclosure in SECURITY.md, without claiming formal SLSA '
        'certification.'
    ),
    'url:https://reproducible-builds.org/specs/source-date-epoch': (
        'Node PG Defense v0.3.0 builds its published release archive deterministically from git archive using '
        'SOURCE_DATE_EPOCH and accompanies it with SHA256SUMS.txt.'
    ),
}


def read_blob_lines(plugin_root: Path, commit: str, rel_file: str) -> list[str]:
    out = subprocess.check_output(
        ['git', '-C', str(plugin_root), 'show', f'{commit}:{rel_file}'],
        stderr=subprocess.PIPE,
    )
    return out.decode('utf8').splitlines()


def find_unique_line(lines: list[str], url_needles: list[str], label: str) -> tuple[int, str]:
    matches = []
    for idx, line in enumerate(lines, 1):
        if any(needle in line for needle in url_needles):
            matches.append((idx, line))
    if len(matches) != 1:
        raise ValueError(f'Expected 1 match for {label} ({url_needles}) in {REF_FILE}, found {len(matches)}')
    line_no, text = matches[0]
    return line_no, excerpt_of(text)


def make_evidence(commit: str, line_no: int, excerpt: str) -> dict:
    return {
        'file': REF_FILE,
        'line': line_no,
        'url': f'https://github.com/Technoetic/{PLUGIN}/blob/{commit}/{REF_FILE}#L{line_no}',
        'excerpt': excerpt,
    }


def apply_update(plugin_root: Path, commit: str, apply: bool, public_ref: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Expected 40-hex commit SHA')
    resolved = subprocess.check_output(
        ['git', '-C', str(plugin_root), 'rev-parse', '--verify', '--end-of-options', f'{public_ref}^{{commit}}'],
        stderr=subprocess.PIPE,
    ).decode('utf8').strip()
    if resolved != commit:
        raise ValueError(f'Public ref {public_ref} resolves to {resolved}, expected {commit}')

    lines = read_blob_lines(plugin_root, commit, REF_FILE)
    all_urls = re.findall(r'\((https?://[^)\s]+)\)', '\n'.join(lines))
    url_by_cid = {}
    for raw_url in all_urls:
        cid = canonical_key(raw_url)['key']
        if cid in url_by_cid:
            raise ValueError(f'Duplicate canonical URL in {REF_FILE}: {cid}')
        url_by_cid[cid] = raw_url

    reg_path = ROOT / 'data/registry.source.json'
    art_path = ROOT / 'docs/card-artwork-unique-prompts.json'
    registry = json.loads(reg_path.read_text(encoding='utf8'))
    manifest = json.loads(art_path.read_text(encoding='utf8'))

    by_id = {s['id']: s for s in registry['sources']}
    rebound = 0
    cross_added = 0

    # Verify every URL in docs/references.md maps to an existing Atlas source
    for cid in url_by_cid:
        if cid not in by_id:
            raise ValueError(f'URL in {REF_FILE} is missing from registry: {cid}')

    # 1. Repin all existing node-pg-defense uses to exact lines at commit
    for src in registry['sources']:
        has_npd = any(u['plugin'] == PLUGIN for u in src['uses'])
        if not has_npd:
            continue
        cid = src['id']
        if cid not in url_by_cid:
            raise ValueError(f'Existing node-pg-defense source dropped from {REF_FILE}: {cid}')
        line_no, excerpt = find_unique_line(lines, [url_by_cid[cid]], cid)
        ev = make_evidence(commit, line_no, excerpt)
        for u in src['uses']:
            if u['plugin'] == PLUGIN:
                u['evidence'] = [ev]
                rebound += 1

    # 2. Cross-attach the 25 newly adopted existing Atlas sources
    for cid, note_suffix in CROSS_LINK_NOTES.items():
        if cid not in url_by_cid:
            raise ValueError(f'Expected cross-link source missing from {REF_FILE}: {cid}')
        src = by_id[cid]
        if any(u['plugin'] == PLUGIN for u in src['uses']):
            raise ValueError(f'Source already has {PLUGIN} use: {cid}')
        line_no, excerpt = find_unique_line(lines, [url_by_cid[cid]], cid)
        ev = make_evidence(commit, line_no, excerpt)
        src['uses'].append({'plugin': PLUGIN, 'role': 'reference', 'evidence': [ev]})
        if note_suffix not in src['note']:
            sep = '' if not src['note'] or src['note'].endswith(' ') else ' '
            src['note'] = src['note'] + sep + note_suffix
        cross_added += 1

    # Confirm 100% of docs/references.md URLs are now linked to node-pg-defense
    linked_npd = {s['id'] for s in registry['sources'] if any(u['plugin'] == PLUGIN for u in s['uses'])}
    if linked_npd != set(url_by_cid):
        raise ValueError(f'Mismatch between {REF_FILE} and linked NPD sources: diff={linked_npd ^ set(url_by_cid)}')

    registry['snapshots'][PLUGIN] = {
        'name': PLUGIN_NAME,
        'version': VERSION,
        'commit': commit,
        'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}',
    }
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    audited = merge_sources(registry['sources'])
    validate_catalog({'schemaVersion': 1, 'snapshots': registry['snapshots'], 'sources': audited})
    audited_by_id = {s['id']: s for s in audited}

    # 3. Sync artwork manifest evidenceUrls & currentEvidenceUrls (strictly preserving generationEvidenceUrls)
    for asset in manifest['assets']:
        src = audited_by_id.get(asset['sourceId'])
        if src:
            urls = [row['url'] for use in src['uses'] for row in use['evidence']]
            asset['evidenceUrls'] = urls
            asset['currentEvidenceUrls'] = urls

    summary = {
        'apply': apply,
        'commit': commit,
        'version': VERSION,
        'rebound': rebound,
        'cross_added': cross_added,
        'total_npd_sources': len(linked_npd),
        'audited_sources': len(audited),
    }
    if apply:
        reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
        art_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
        catalog = build(ROOT)
        summary['counts'] = catalog['counts']
        summary['countsByPlugin'] = catalog['countsByPlugin']
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--public-ref', default=f'refs/tags/{VERSION}')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = apply_update(args.plugin_root, args.commit, args.apply, args.public_ref)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
