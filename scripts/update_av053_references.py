"""Add the v0.53.0 design references and repin earlier uses from the exact plugin tree."""
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
TAG = 'v0.53.0'
PRIOR = 'b581c5836c6c8b86c3aff200d4b0b1c4663b1083'
RELEASE = 'docs/releases/v0.53.0.md'
KO = 'docs/ko-order-recall.md'
HANDOFF = 'docs/handoff-resume.md'
REFERENCES = (
    ('paper', 'PAWS-X: A Cross-lingual Adversarial Dataset for Paraphrase Identification',
     'https://doi.org/10.18653/v1/D19-1382', 2019, ['PAWS-X', 'ACL D19-1382'],
     ['https://aclanthology.org/D19-1382/', 'https://arxiv.org/abs/1908.11828'],
     'The paper motivates paired examples with overlapping words and different meanings. '
     'The plugin authors wrote Korean procedure notes and tested retrieval order using those pairs.',
     (RELEASE, KO)),
    ('project', 'google-research-datasets/paws', 'https://github.com/google-research-datasets/paws',
     2019, ['PAWS-X dataset repository'], [],
     "The authors' PAWS-X dataset documentation illustrates paraphrase and non-paraphrase pairs. "
     'The release adapts the pair construction to locally authored retrieval fixtures.',
     (RELEASE, KO)),
    ('paper', 'Switch-SWE: Do Coding Agents Hold Focus When Switching Between Unfinished Tasks?',
     'https://arxiv.org/abs/2611.02017', 2026, ['Switch-SWE paper'], [],
     'The comparison of interrupted and uninterrupted tasks under a common verifier informed the '
     'release’s synthetic scenario with a fresh receiver and matching artifact criteria.',
     (RELEASE, HANDOFF)),
    ('project', 'Miraclecsc/Switch-SWE', 'https://github.com/Miraclecsc/Switch-SWE', 2026,
     ['Switch-SWE benchmark repository'], [],
     'The upstream task documentation describes keeping a native agent session across switches and '
     'grading the final focus checkout. The plugin checks independently authored artifacts and damaged handoffs.',
     (RELEASE, HANDOFF)),
    ('project', 'simplistix/sybil', 'https://github.com/simplistix/sybil', 2017, ['Sybil'], [],
     'The Markdown parser guide illustrates running a documented command and checking the example’s '
     'output. The plugin uses Python unittest to replay the commands in its bilingual first-handoff tutorial.',
     (RELEASE,)),
)
LINK = re.compile(r'\]\((https?://[^)\s]+)\)')


def prepare(registry, artwork, commit, read_lines):
    snapshot = registry['snapshots']['agentic-vault']
    if (snapshot['version'], snapshot['commit']) != ('v0.52.1', PRIOR):
        raise ValueError('This update requires the published v0.52.1 baseline')
    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]
    counts = {}
    for kind, title, url, year, aliases, other_urls, note, files in REFERENCES:
        keys = [canonical_key(address)['key'] for address in [url, *other_urls]]
        rows = []
        for file in files:
            lines = read_lines(file)
            matches = [(i, line) for i, line in enumerate(lines, 1)
                       if any(canonical_key(link)['key'] in keys for link in LINK.findall(line))]
            if len(matches) != 1:
                raise ValueError(f'Expected one citation of {title} in {file}, found {len(matches)}')
            number, line = matches[0]
            excerpt = excerpt_of(line)
            if sum(excerpt_of(other) == excerpt for other in lines) != 1:
                raise ValueError(f'Ambiguous evidence excerpt for {title} in {file}')
            rows.append(dict(file=file, line=number, url=f'{PREFIX}{commit}/{file}#L{number}', excerpt=excerpt))
        registry['sources'].append(dict(id=keys[0], kind=kind, title=title, url=url, year=year,
                                        keys=keys, aliases=aliases, tags=['평가·테스트'], note=note,
                                        uses=[dict(plugin='agentic-vault', role='reference', evidence=rows)]))
        counts[keys[0]] = len(rows)
    snapshot.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/agentic-vault/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(rebound=prior_rows, moved=moved, added=counts)


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
