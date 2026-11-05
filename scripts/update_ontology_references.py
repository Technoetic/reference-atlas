"""Prepare the v0.41.0 reference update from exact release-tag Git blobs.

Offline and dry-run by default. The caller must independently verify that the
supplied commit/tag are public before using --apply. This helper does not fetch,
publish, change a plugin, or certify public availability.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from build_catalog import merge_sources, metrics
from reference_identity import validate_catalog

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_URL = 'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/'
ARTICLE_ID = 'url:' + ARTICLE_URL.rstrip('/')
PROJECT_ID = 'github:nvidia/auto-ontology'
UPSTREAM_COMMIT = '2a24f5d34ef6b6e168a7f22d308504d3ab36a198'
PROJECT_PIN = 'https://github.com/NVIDIA/auto-ontology/tree/' + UPSTREAM_COMMIT
NEW_IDS = {ARTICLE_ID, PROJECT_ID}
PLUGIN_PREFIX = 'https://github.com/Technoetic/agentic-vault/blob/'


def evidence_url(commit, file, line):
    return f'{PLUGIN_PREFIX}{commit}/{file}#L{line}'


def prepare_update(registry, artwork, read_lines, commit, tag, *, updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}', commit) or tag != 'v0.41.0':
        raise ValueError('Expected a full lowercase commit SHA and release tag v0.41.0')
    # Validate the declared old snapshot before preparing any changed objects.
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    revised, images = deepcopy(registry), deepcopy(artwork)
    present = {source['id'] for source in revised['sources']} & NEW_IDS
    if present and present != NEW_IDS:
        raise ValueError('Partial NVIDIA source update requires manual review')
    remapped = {}
    prior_count = moved_count = 0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin'] != 'agentic-vault':
                continue
            for row in use['evidence']:
                lines = read_lines(row['file'])
                old_line, old_url = row['line'], row['url']
                if old_line <= len(lines) and lines[old_line - 1].strip()[:220] == row['excerpt']:
                    line = old_line
                else:
                    matches = [i + 1 for i, text in enumerate(lines)
                               if text.strip()[:220] == row['excerpt']]
                    if len(matches) != 1:
                        raise ValueError(f'Prior excerpt needs a unique exact match: {source["id"]} / {row["file"]}:{old_line}')
                    line = matches[0]
                row.update(line=line, url=evidence_url(commit, row['file'], line))
                remapped[old_url] = row['url']
                if source['id'] not in NEW_IDS:
                    prior_count += 1
                    moved_count += line != old_line

    def cited_lines(needle):
        rows = []
        for file in ['docs/ontology-contracts.md', 'docs/releases/v0.41.0.md']:
            lines = read_lines(file)
            matches = [i + 1 for i, text in enumerate(lines) if needle in text]
            if len(matches) != 1:
                raise ValueError(f'New citation needs a unique exact URL: {file}')
            line = matches[0]
            rows.append({'file': file, 'line': line,
                         'url': evidence_url(commit, file, line),
                         'excerpt': lines[line - 1].strip()[:220]})
        return rows

    if not present:
        revised['sources'].extend([
            {'id': ARTICLE_ID, 'kind': 'article',
             'title': 'NVIDIA Agent Toolkit Expands, Grounding Enterprise Agents in Company Data',
             'url': ARTICLE_URL, 'year': 2026,
             'keys': [ARTICLE_ID], 'aliases': [],
             'tags': ['지식 그래프', '신뢰성'],
             'uses': [{'plugin': 'agentic-vault', 'role': 'background',
                       'evidence': cited_lines(ARTICLE_URL)}],
             'note': 'Official article used as enterprise-platform context for the optional v0.41.0 definitions contract. A prior research reference reused for a new application; this records neither NVIDIA code adoption nor reproduced performance.'},
            {'id': PROJECT_ID, 'kind': 'project', 'title': 'NVIDIA Auto Ontology',
             'url': 'https://github.com/NVIDIA/auto-ontology', 'year': None,
             'keys': [PROJECT_ID], 'aliases': ['Auto Ontology', 'NVIDIA/auto-ontology'],
             'tags': ['지식 그래프', '메모리·검색'],
             'uses': [{'plugin': 'agentic-vault', 'role': 'reference',
                       'evidence': cited_lines(PROJECT_PIN)}],
             'note': f'Conceptual design reference pinned upstream at {UPSTREAM_COMMIT}: explicit terms, curated lookup and coverage gaps informed a host-authored typed definitions contract and narrow structured-plan preflight. A prior reference reused for a new application; no NVIDIA code/dependency adoption or benchmark reproduction is claimed.'},
        ])
    revised['snapshots']['agentic-vault'] = {
        'name': 'Agentic Vault', 'version': tag, 'commit': commit,
        'url': f'https://github.com/Technoetic/agentic-vault/tree/{commit}',
    }
    revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})

    by_id = {source['id']: source for source in merged}
    image_ids = {asset['sourceId'] for asset in images['assets']}
    if not NEW_IDS <= image_ids:
        raise ValueError('Both separately generated artwork records must exist before applying this update')
    for asset in images['assets']:
        # Generation provenance is historical. Advancing a citation snapshot
        # does not retroactively regenerate the artwork or change its prompt.
        asset.setdefault('generationEvidenceUrls', deepcopy(asset.get('evidenceUrls', [])))
        urls = []
        for url in asset.get('evidenceUrls', []):
            if url.startswith(PLUGIN_PREFIX) and url not in remapped:
                raise ValueError('Active artwork evidence is absent from the prior citation map')
            urls.append(remapped.get(url, url))
        if asset['sourceId'] in NEW_IDS:
            urls = [row['url'] for use in by_id[asset['sourceId']]['uses']
                    if use['plugin'] == 'agentic-vault' for row in use['evidence']]
        asset['evidenceUrls'] = urls
        asset['currentEvidenceUrls'] = deepcopy(urls)
    images['evidencePolicy'] = ('generationEvidenceUrls preserve the public source URLs recorded when each image was generated. '
        'currentEvidenceUrls and the legacy evidenceUrls field follow the current citation snapshot. '
        'Repinning citations does not regenerate artwork or change original prompts.')
    images['count'] = len(images['assets'])
    if images['count'] != len(merged):
        raise ValueError('Artwork records and catalog sources must have the same count')
    summary = {'priorAgenticVaultCitations': prior_count, 'remappedLines': moved_count,
               'addedSourceIds': sorted(NEW_IDS - present),
               'counts': metrics(merged), 'artworkCount': images['count'],
               'snapshot': revised['snapshots']['agentic-vault']}
    return revised, images, summary


def write_update(documents):
    """Stage all changed bytes and restore prior files if replacement fails.

    This is failure recovery for an ordinary write error, not a filesystem-wide
    transaction or protection against power loss/concurrent editors.
    """
    originals = {path: path.read_bytes() for path, _ in documents}
    encoded = {path: (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf8')
               for path, data in documents}
    staged, replaced = {}, []
    def stage(path, content):
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.ontology-update-', suffix='.tmp', delete=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            return Path(stream.name)
    try:
        for path, content in encoded.items():
            staged[path] = stage(path, content)
        for path, _ in documents:
            if path.read_bytes() != originals[path]:
                raise OSError('Input file changed after preparation; apply aborted')
            os.replace(staged[path], path)
            replaced.append(path)
    except BaseException as failure:
        for path in reversed(replaced):
            if path.read_bytes() != encoded[path]:
                raise RuntimeError('Concurrent file change prevents automatic rollback; preserve the worktree for manual recovery') from failure
            rollback = stage(path, originals[path])
            try:
                os.replace(rollback, path)
            except BaseException:
                # Keep the original-byte backup if restoration itself fails.
                raise RuntimeError(f'Rollback failed; original bytes preserved at {rollback}') from failure
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tag', required=True, choices=['v0.41.0'])
    parser.add_argument('--apply', action='store_true', help='Write the prepared source registry and active artwork provenance; no publishing')
    args = parser.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}', args.commit):
        parser.error('--commit requires a full lowercase SHA')
    def git(*arguments):
        result = subprocess.run(['git', '-C', str(args.plugin_root), *arguments],
                                capture_output=True, check=True)
        return result.stdout.decode('utf8')
    tagged = git('rev-parse', '--verify', 'refs/tags/' + args.tag + '^{commit}').strip()
    if tagged != args.commit:
        raise ValueError('The exact local release tag does not resolve to --commit')
    cache = {}
    def read_lines(file):
        if file not in cache:
            cache[file] = git('show', args.commit + ':' + file).splitlines()
        return cache[file]
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
