"""Prepare the semantic-crosscheck v0.20.0 citation snapshot from exact Git blobs.

Offline and dry-run by default. Public tag/source availability and formal release
status must be checked independently by the caller before publication. This
helper does not fetch, publish, modify either plugin or regenerate artwork.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources, metrics
from reference_identity import validate_catalog
from update_ontology_references import write_update

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_URL = 'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/'
ARTICLE_ID = 'url:' + ARTICLE_URL.rstrip('/')
PROJECT_ID = 'github:nvidia/auto-ontology'
UPSTREAM_COMMIT = 'c4495670947eb7b4616f0dd9900e5ced2a48ca1e'
PROJECT_PIN = 'https://github.com/NVIDIA/auto-ontology/tree/' + UPSTREAM_COMMIT
PLUGIN = 'semantic-crosscheck'
PLUGIN_PREFIX = f'https://github.com/Technoetic/{PLUGIN}/blob/'
FILES = ('docs/semantic-preflight.md', 'THIRD_PARTY.md')
NOTES = {
    ARTICLE_ID: ('Also used as enterprise-platform context for semantic-crosscheck v0.20.0 authored '
                 'metric-definition contracts and structured-plan preflight. This is a new application '
                 'of an existing reference, with no NVIDIA code/runtime or reproduced performance claim.'),
    PROJECT_ID: (f'The semantic-crosscheck v0.20.0 application at upstream {UPSTREAM_COMMIT} checks authored '
                 'metric definitions and structured selections against measure/Gold/Cube declarations. '
                 'The prior agentic-vault application at 2a24f5d34ef6b6e168a7f22d308504d3ab36a198 remains '
                 'recorded. The newer pin tracks packaging/version changes, not a newly established '
                 'semantic capability; no NVIDIA code/runtime or reproduced benchmark is claimed.'),
}


def evidence_url(commit, file, line):
    return f'{PLUGIN_PREFIX}{commit}/{file}#L{line}'


def prepare_update(registry, artwork, read_lines, commit, tag, *, updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}', commit) or tag != 'v0.20.0':
        raise ValueError('Expected a full lowercase commit SHA and exact tag v0.20.0')
    old_sources = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': old_sources})
    revised, images = deepcopy(registry), deepcopy(artwork)
    targets = {}
    for identifier in (ARTICLE_ID, PROJECT_ID):
        found = [source for source in revised['sources'] if source['id'] == identifier]
        if len(found) != 1:
            raise ValueError('Both existing NVIDIA source records are required')
        targets[identifier] = found[0]
    old_by_id = {source['id']: source for source in old_sources}
    image_ids = [asset['sourceId'] for asset in images['assets']]
    if (images['count'] != len(image_ids) or len(set(image_ids)) != len(image_ids)
            or set(image_ids) != set(old_by_id)):
        raise ValueError('The exact existing artwork/source assignment is required')
    for asset in images['assets']:
        prior_urls = [row['url'] for use in old_by_id[asset['sourceId']]['uses'] for row in use['evidence']]
        active = asset.get('evidenceUrls', [])
        if (asset.get('currentEvidenceUrls') != active or len(active) != len(prior_urls)
                or set(active) != set(prior_urls) or not asset.get('generationEvidenceUrls')):
            raise ValueError('Artwork must retain generation history and every current citation')

    remapped = {}
    prior_count = repinned_count = moved_count = 0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin'] != PLUGIN:
                continue
            for row in use['evidence']:
                lines = read_lines(row['file'])
                old_line, old_url = row['line'], row['url']
                if old_line <= len(lines) and lines[old_line - 1].strip()[:220] == row['excerpt']:
                    line = old_line
                else:
                    matches = [i + 1 for i, text in enumerate(lines) if text.strip()[:220] == row['excerpt']]
                    if len(matches) != 1:
                        raise ValueError(f'Prior excerpt needs a unique exact match: {source["id"]} / {row["file"]}:{old_line}')
                    line = matches[0]
                url = evidence_url(commit, row['file'], line)
                if old_url in remapped and remapped[old_url] != url:
                    raise ValueError('A prior citation has conflicting line mappings')
                remapped[old_url] = url
                row.update(line=line, url=url)
                prior_count += 1
                repinned_count += old_url != url
                moved_count += old_line != line

    def cited_lines(needle):
        rows = []
        for file in FILES:
            lines = read_lines(file)
            matches = [i + 1 for i, text in enumerate(lines) if needle in text]
            if len(matches) != 1:
                raise ValueError(f'New citation needs a unique exact URL: {file}')
            line = matches[0]
            rows.append({'file': file, 'line': line, 'url': evidence_url(commit, file, line),
                         'excerpt': lines[line - 1].strip()[:220]})
        return rows

    added_count = 0
    for identifier, needle, role in ((ARTICLE_ID, ARTICLE_URL, 'background'),
                                     (PROJECT_ID, PROJECT_PIN, 'reference')):
        source = targets[identifier]
        uses = [use for use in source['uses'] if use['plugin'] == PLUGIN]
        if len(uses) > 1:
            raise ValueError('A source must have one SXC cited use')
        expected = cited_lines(needle)
        if uses:
            if uses[0] != {'plugin': PLUGIN, 'role': role, 'evidence': expected}:
                raise ValueError('An existing SXC NVIDIA use differs from the prepared citations')
        else:
            source['uses'].append({'plugin': PLUGIN, 'role': role, 'evidence': expected})
            added_count += len(expected)
        addition = NOTES[identifier]
        if addition not in source.get('note', ''):
            source['note'] = (source.get('note', '') + ' ' + addition).strip()

    revised['snapshots'][PLUGIN] = {'name': 'Semantic Crosscheck', 'version': tag, 'commit': commit,
                                  'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}'}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    by_id = {source['id']: source for source in merged}
    for asset in images['assets']:
        urls = [remapped.get(url, url) for url in asset['evidenceUrls']]
        if asset['sourceId'] in targets:
            urls = [row['url'] for use in by_id[asset['sourceId']]['uses'] for row in use['evidence']]
        asset['evidenceUrls'] = urls
        asset['currentEvidenceUrls'] = deepcopy(urls)
    summary = {'priorSxcCitations': prior_count, 'repinnedCitations': repinned_count,
               'remappedLines': moved_count, 'addedCitations': added_count, 'addedSourceIds': [],
               'counts': metrics(merged), 'artworkCount': images['count'],
               'snapshot': revised['snapshots'][PLUGIN]}
    return revised, images, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tag', required=True, choices=['v0.20.0'])
    parser.add_argument('--apply', action='store_true', help='Write the prepared registry and active artwork provenance; no publishing')
    args = parser.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}', args.commit):
        parser.error('--commit requires a full lowercase SHA')
    def git(*arguments):
        return subprocess.run(['git', '-C', str(args.plugin_root), *arguments],
                              capture_output=True, check=True).stdout.decode('utf8')
    if git('rev-parse', '--verify', 'refs/tags/' + args.tag + '^{commit}').strip() != args.commit:
        raise ValueError('The exact local tag does not resolve to --commit')
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
