"""Offline, dry-run-first agentic-vault v0.52.0 reference update from exact Git blobs.

Adds the nine sources of the v0.52.0 release note's research table (the
Spotlighting, The Attacker Moves Second, LLMs as a Jury and Agreement-Based
Cascading papers, the Jujutsu divergent-changes guide, the SLSA v1.2 Source
requirements page and three GitHub documentation pages on private
vulnerability reporting and rulesets) and repins every prior agentic-vault
citation to the supplied commit, because the catalog schema binds each
citation of a plugin to that plugin's declared snapshot. Each prior row keeps
its file and excerpt; its line follows the excerpt, which must occur exactly
once in that file at the new revision. Existing metadata, semantic-crosscheck
uses and immutable artwork provenance stay unchanged. Every non-test line of
the plugin that names a new source must be covered by one of that source's
rows (test lines that pin the release note's addresses are reported, not
cited, and a line of the generated antigravity/<path> package equal to a cited
line of <path> at the same number is reported as a copy), so a citation added
later stops the helper instead of being left out. None of the nine addresses
was known to the catalog this update starts from (local and published lookup
on 2026-11-16, catalog updatedAt 2026-11-16T04:46:33Z), so each becomes a new
source; a source that another record already holds stops the helper for a
reviewed merge instead of receiving a second card. The new sources use the
text fallback; no image, prompt or interface is created, and the two tracked
tests that count catalog coverage and check commissioned artwork receive
exact, idempotent edits.

No fetch, commit, push, publication or plugin change. Apply requires a locally
verified annotated release tag that names the commit and the caller's separate
assertion that those exact bytes are public. --stand-in skips the tag check
for a nonpublishable dry run; it cannot apply.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update
from update_av048_references import (PREFIX, av_rows, cited_rows, generated_copies, grep_key,
    immutable_artwork, naming_lines, repin, verify_images)

ROOT = Path(__file__).resolve().parents[1]
TAG, PRIOR_TAG, SXC_TAG = 'v0.52.0', 'v0.51.0', 'v0.27.0'
RELEASE = 'docs/releases/v0.52.0.md'
SECURITY = 'SECURITY.md'
INTEGRITY = 'docs/release-integrity.md'

SPOTLIGHTING = 'https://arxiv.org/abs/2403.14720'
ATTACKER = 'https://arxiv.org/abs/2510.09023'
DIVERGENCE = 'https://docs.jj-vcs.dev/latest/guides/divergence/'
JURY = 'https://arxiv.org/abs/2607.10139'
CASCADING = 'https://arxiv.org/abs/2407.02348'
SLSA = 'https://slsa.dev/spec/v1.2/source-requirements'
REPORTING = ('https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/'
             'configure-vulnerability-reporting/configure-for-a-repository')
RULESETS = 'https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/'
ABOUT_RULESETS = RULESETS + 'about-rulesets'
AVAILABLE_RULES = RULESETS + 'available-rules-for-rulesets'

FIRST = ('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog; the '
         'v0.52.0 release note says earlier repository documents did not cite it (a git grep of the v0.51.0 tree '
         'found none). ')
UNDATED = 'The release note gives no read date; the page may have changed since. '
NO_CLAIM = ('This records a citation, not copied code, a runtime dependency or reproduced results; the effects '
            'and numbers the source reports are not claimed for the plugin.')
SPOTLIGHTING_NOTE = (
    'Paper on defending against indirect prompt injection (arXiv, 2024). The release note cites it for the point '
    'that its authors do not recommend delimiting alone (wrapping untrusted input in delimiters), because an '
    'attacker who knows the delimiters can insert the same delimiters to override instructions; they recommend '
    'datamarking or encoding instead. Release item 2 applies that point to SessionStart: a note line that starts '
    "with one of the hook's own section headers (=== SESSION HANDOFF, === HOT CONTEXT, === FIXED CONSTRAINTS) "
    'gets the prefix [note line, not a hook header], deterministically and right after credential redaction. The '
    'release did not adopt datamarking or encoding of the whole note text, so that the output of ordinary notes '
    'stays byte-identical. ')
ATTACKER_NOTE = (
    'Paper on adaptive attacks against LLM jailbreak and prompt injection defences (arXiv, 2025). The release note '
    'cites it for the finding that adaptive attacks, which change their method to fit a defence, bypassed most of '
    'the recent defences tested, most of which had originally reported attack success rates near zero. It is the '
    'basis for the limit stated for release item 2 and for the SECURITY.md sentence that the boundary sentence, '
    'credential redaction and header-line defusing are hygiene, not a guarantee against adaptive prompt '
    'injection; the defence stays with deterministic controls (note text grants no authority, and deny zones and '
    'the path checks do not depend on what a note says). ')
DIVERGENCE_NOTE = (
    'Jujutsu (jj) documentation page. The release note cites it for showing two visible commits with the same '
    'change ID as divergent (with /0 and /1 after the ID) instead of treating them as an error, where keeping both '
    'is one valid resolution (possibly the only one when both are immutable history) and the ID alone can then no '
    'longer name either. Release item 1 follows it: health check section 14d only reports level-2 ADR-<n> and '
    'M-<n> headings with the same number in one note and never renumbers them; when both headings are committed it '
    'says to keep both and add the title to references, and it tells only an uncommitted heading to change its '
    'number. ')
JURY_NOTE = (
    'Paper on cross-model consensus for LLM reasoning (arXiv, 2026). The release note cites its Appendix I for an '
    'agreement-gated cascade, in which an answer that two independently solving models agree on is accepted and '
    'only a disagreement is escalated to a larger panel, and for the shared-error floor it reports: models that '
    'share a misconception are wrong together. Release item 3 records for each escalated question whether the '
    'original Jev answer and the BizRouter answer agree (agreement) and turns a disagreement into the review reason '
    'provider_disagreement; because of the same limit, agreement is information and not a pass. ')
CASCADING_NOTE = (
    'Paper on agreement-based cascading for efficient inference (arXiv, 2024): the agreement of an ensemble of '
    'models at each stage decides whether to defer to the next stage, to reduce inference cost. The release note '
    'read it as earlier work on the same idea as release item 3 and states the difference: the plugin does not '
    'escalate to save cost, it escalates only low-confidence questions as in v0.51.0, and it uses agreement only '
    'to decide whether human review is needed, not whether to go to a next stage. ')
SLSA_NOTE = (
    'Page of the SLSA v1.2 specification (Source track). The release note cites it for the requirement that a '
    'source control system that supports tags must be configured to prevent tags from being moved or deleted '
    '(from level 2), for Source levels being shown by a Source VSA that the source control system issues (a '
    'revision without one is at Source level 0), and for level 4 requiring review by two trusted persons for every '
    'change to a protected branch. Release item 4 adds a v* tag ruleset that blocks updates and deletions; the '
    'release note and docs/release-integrity.md claim no Source level, because no Source VSA is issued and a single '
    'maintainer cannot meet the level 4 two-person review. The release note adds that docs/release-integrity.md '
    'mentioned SLSA earlier only for build provenance (actions/attest) and cited neither the Source track nor this '
    'page. ' + UNDATED)
REPORTING_NOTE = (
    'GitHub documentation page. The release note cites it for the repository setting that, when an owner or '
    'administrator of a public repository enables it, lets security researchers send a private report with the '
    'Report a vulnerability button or the REST API. Release item 4 enabled it (a repository setting applied by '
    'the maintainer, not a code change) and updated the reporting step of SECURITY.md, keeping the public-issue '
    'route that asks only for contact, without details, when the form is unavailable. ' + UNDATED)
RULESETS_ROW = (
    'cites it with the other rulesets page in one row for rulesets that target tags, bypass permissions and the '
    'active or disabled state, and for the Restrict updates and Restrict deletions rules, with which only users '
    'with bypass permission can push or delete tags whose names match. Release item 4 adds a ruleset on '
    'refs/tags/v* that blocks updates and deletions, with no bypass actors and no creation rule; because an '
    'administrator can disable the ruleset, docs/release-integrity.md states what it proves and what it does '
    'not. ' + UNDATED)
ABOUT_RULESETS_NOTE = 'GitHub documentation page (About rulesets). The release note ' + RULESETS_ROW
AVAILABLE_RULES_NOTE = 'GitHub documentation page (Available rules for rulesets). The release note ' + RULESETS_ROW


def _source(url, kind, title, year, aliases, role, note, *more):
    """The release citation comes first; each text must appear on exactly one line that names the source."""
    return (canonical_key(url)['key'], kind, title, url, year, aliases, role, FIRST + note + NO_CLAIM,
            ((RELEASE, '(' + url + ')'), *more))


# id, kind, title, url, year, aliases, role, note, ((file, text on exactly one line naming the source), ...), in the
# order of the release note's table. A role is reference when the release note says the source gave a point the
# release applies, background when it was read as earlier work and not applied.
REFERENCES = (
    _source(SPOTLIGHTING, 'paper', 'Defending Against Indirect Prompt Injection Attacks With Spotlighting', 2024,
            ['Spotlighting'], 'reference', SPOTLIGHTING_NOTE),
    _source(ATTACKER, 'paper', 'The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against Llm '
            'Jailbreaks and Prompt Injections', 2025, ['The Attacker Moves Second'], 'reference', ATTACKER_NOTE,
            (SECURITY, '(' + ATTACKER + ')')),
    _source(DIVERGENCE, 'article', 'Jujutsu: Divergent changes', None, ['Handling divergent changes'],
            'reference', DIVERGENCE_NOTE + UNDATED),
    _source(JURY, 'paper', 'LLMs as a Jury: Cross-Model Consensus Can Outperform Process Reward Models for LLM '
            'Reasoning', 2026, ['LLMs as a Jury'], 'reference', JURY_NOTE),
    _source(CASCADING, 'paper', 'Agreement-Based Cascading for Efficient Inference', 2024, [], 'background',
            CASCADING_NOTE),
    _source(SLSA, 'article', 'SLSA v1.2 Source requirements', None, ['SLSA v1.2 Source 요구사항'], 'reference',
            SLSA_NOTE, (INTEGRITY, '[SLSA v1.2 Source 요구사항](' + SLSA + ')'),
            (INTEGRITY, '[SLSA v1.2 Source requirements](' + SLSA + ')')),
    _source(REPORTING, 'article', 'GitHub Docs: Configuring private vulnerability reporting for a repository', None,
            ['Configuring private vulnerability reporting for a repository'], 'reference', REPORTING_NOTE,
            (INTEGRITY, '[Configuring private vulnerability reporting for a repository](' + REPORTING + ')')),
    _source(ABOUT_RULESETS, 'article', 'GitHub Docs: About rulesets', None, ['About rulesets'], 'reference',
            ABOUT_RULESETS_NOTE, (INTEGRITY, '[About rulesets](' + ABOUT_RULESETS + ')')),
    _source(AVAILABLE_RULES, 'article', 'GitHub Docs: Available rules for rulesets', None,
            ['Available rules for rulesets'], 'reference', AVAILABLE_RULES_NOTE,
            (INTEGRITY, '[Available rules for rulesets](' + AVAILABLE_RULES + ')')),
)
NEW_IDS = [row[0] for row in REFERENCES]
NEW_CITATIONS = sum(len(row[8]) for row in REFERENCES)
# The published catalog this update starts from: agentic-vault v0.51.0 with semantic-crosscheck v0.27.0, all 180
# sources illustrated (public main 9589bef: 180 sources, 328 citations, 252 of them agentic-vault rows).
BASE = {'total': 180, 'citations': 328, 'av': 252}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE = (56, 57, 24, 180, 328)
EXPECTED_TUPLE = (60, 57, 29, 189, 343)


def _validate_revision(commit, tag):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit) or tag != TAG:
        raise ValueError('Expected an exact lowercase 40-character commit and release tag ' + TAG)


def _locations(pairs):
    return [f'{file}#L{line}' for file, line in sorted(pairs)]


def _shape(sources):
    return [(s['id'], s['kind'], s['title'], s['url'], s.get('year'), s.get('note'), s['keys'], s['aliases'],
             s['tags'], [(u['plugin'], u['role'], [(r['file'], r['excerpt']) for r in u['evidence']])
                         for u in s['uses']]) for s in sources]


def prepare_update(registry, artwork, read_lines, commit, tag=TAG, *, url_index, updated_at=None):
    """url_index(url) -> {file: [line, ...]} of every line in the plugin revision that names the source."""
    _validate_revision(commit, tag)
    before = merge_sources(registry['sources'])
    validate_catalog({**registry, 'sources': before})
    version = registry['snapshots']['agentic-vault']['version']
    present = set(NEW_IDS) & {source['id'] for source in registry['sources']}
    if version == PRIOR_TAG:
        counts = metrics(before)
        if present or (counts['total'], counts['citations'], av_rows(registry)) != (
                BASE['total'], BASE['citations'], BASE['av']):
            raise ValueError(f"Expected the published v0.51.0 baseline of {BASE['total']} sources and "
                             f"{BASE['citations']} citations ({BASE['av']} agentic-vault)")
    elif version != TAG or present != set(NEW_IDS):
        raise ValueError('Unexpected or partial agentic-vault reference snapshot ' + str(version))
    if registry['snapshots']['semantic-crosscheck']['version'] != SXC_TAG:
        raise ValueError('Expected the semantic-crosscheck ' + SXC_TAG + ' snapshot')
    # Each key names one work. A hit under another id needs a reviewed merge (or a use row on that record), not a
    # second card.
    for row in REFERENCES:
        if canonical_key(row[3])['key'] != row[0]:
            raise ValueError('Canonical source identity mismatch: ' + row[0])
        if any(source['id'] != row[0] and row[0] in {source['id'], *source['keys']}
               for source in registry['sources']):
            raise ValueError('Existing source identity requires a reviewed merge: ' + row[0])

    revised, images = deepcopy(registry), deepcopy(artwork)
    old_ids = [source['id'] for source in registry['sources']]
    old_shape = _shape(registry['sources'])
    old_sxc = [(s['id'], deepcopy(u)) for s in registry['sources'] for u in s['uses'] if u['plugin'] == 'semantic-crosscheck']
    remapped, count, moved = repin(revised, read_lines, commit)
    added, occurrences, copied, unlisted, rows_per_source = [], {}, {}, {}, {}
    for identity, kind, title, url, year, aliases, role, note, cites in REFERENCES:
        rows, covered = cited_rows(cites, read_lines, commit, identity)
        if rows[0]['file'] != RELEASE:
            raise ValueError('New reference lacks an exact release citation: ' + identity)
        named = {(file, line) for file, lines in url_index(url).items() for line in lines}
        tests = {(file, line) for file, line in named if file.startswith('tests/')}
        copies = generated_copies(named, covered, read_lines)
        uncovered = named - covered - tests - copies
        if uncovered or covered - named:
            raise ValueError(f'Every non-test line that names {url} needs its own row; uncovered: '
                             + ', '.join(_locations(uncovered)) + '; expected but absent: '
                             + ', '.join(_locations(covered - named)))
        occurrences[url], copied[url], unlisted[url] = _locations(covered), _locations(copies), _locations(tests)
        rows_per_source[identity] = len(rows)
        record = {'id': identity, 'kind': kind, 'title': title, 'url': url, 'year': year, 'keys': [identity],
                  'aliases': list(aliases), 'tags': [], 'note': note,
                  'uses': [{'plugin': 'agentic-vault', 'role': role, 'evidence': rows}]}
        prior = next((source for source in revised['sources'] if source['id'] == identity), None)
        if prior is None:
            revised['sources'].append(record)
            added.append(identity)
        elif prior != record:
            raise ValueError('Previously applied record differs; manual review required: ' + identity)
    revised['snapshots']['agentic-vault'] = {
        'name': 'Agentic Vault', 'version': TAG, 'commit': commit,
        'url': 'https://github.com/Technoetic/agentic-vault/tree/' + commit}
    if revised != registry:
        revised['updatedAt'] = updated_at or datetime.now(timezone.utc).isoformat()
    merged = merge_sources(revised['sources'])
    validate_catalog({**revised, 'sources': merged})
    # Existing records keep kind, title, url, year, note, keys, aliases, tags, roles, files and excerpts.
    kept = [source for source in revised['sources'] if source['id'] in old_ids]
    if [source['id'] for source in revised['sources']][:len(old_ids)] != old_ids or _shape(kept) != old_shape:
        raise ValueError('An existing record changed beyond its commit and line')
    if revised['snapshots']['semantic-crosscheck'] != registry['snapshots']['semantic-crosscheck'] or [
            (s['id'], u) for s in revised['sources'] for u in s['uses'] if u['plugin'] == 'semantic-crosscheck'] != old_sxc:
        raise ValueError('Unrelated semantic-crosscheck snapshot or use changed')
    counts = metrics(merged)
    av = metrics([s for s in merged if any(u['plugin'] == 'agentic-vault' for u in s['uses'])])
    coverage = (av['paper'], av['project'] + av['format'], av['article'], counts['total'], counts['citations'])
    if coverage != EXPECTED_TUPLE or av_rows(revised) != BASE['av'] + NEW_CITATIONS:
        raise ValueError(f'Unexpected coverage {coverage}; expected {EXPECTED_TUPLE}')
    for asset in images['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            if field not in asset:
                raise ValueError('Artwork current evidence field missing')
            if any(url.startswith(PREFIX) and url not in remapped for url in asset[field]):
                raise ValueError('Artwork URL is absent from the prior citation map')
            asset[field] = [remapped.get(url, url) for url in asset[field]]
    if (images['count'] != artwork['count'] or len(images['assets']) != artwork['count']
            or immutable_artwork(images) != immutable_artwork(artwork)):
        raise ValueError('Immutable artwork provenance or assignments changed')
    if set(NEW_IDS) & {asset['sourceId'] for asset in images['assets']}:
        raise ValueError('Uncommissioned v0.52.0 sources must use text fallback')
    return revised, images, {
        'addedSourceIds': added, 'newCitationRows': NEW_CITATIONS, 'rowsPerNewSource': rows_per_source,
        'repinnedRowsTotal': count,
        'priorAgenticVaultCitationsRepinned': count - (NEW_CITATIONS if version == TAG else 0),
        'remappedLines': moved, 'counts': counts, 'agenticVaultCounts': av, 'coverageTuple': list(coverage),
        'agenticVaultRows': av_rows(revised), 'citedAddressLines': occurrences, 'testLinesNotCited': unlisted,
        'generatedCopyLines': copied, 'uncommissionedSourceIds': list(NEW_IDS), 'artworkCount': images['count'],
        'snapshot': revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot': registry['snapshots']['semantic-crosscheck'],
    }


# Exact, guarded, idempotent edits of the two tracked tests that the update would otherwise break. Earlier lines stay
# in place: the new coverage line follows the v0.51.0 line, and the artwork checks that compare records with the
# v0.51.0 citations keep doing so while the catalog is at v0.51.0 and compare file paths (and the immutable fields)
# once the agentic-vault rows are repinned.
def _tuple(values):
    return '(' + ','.join(str(value) for value in values) + ')'


_FALLBACK_ENTRIES = ''.join(f"  ['{row[0]}','{row[1]}']{',' if index < len(REFERENCES) - 1 else ''}\n"
                            for index, row in enumerate(REFERENCES))
_FULL_172 = 'cd4937c7f636bd80c50a2a4ebe7f553884fc0aabff586fee82ac51bd0465df1b'
# sha256 of JSON.stringify of the first 172 artwork records without evidenceUrls and currentEvidenceUrls (9589bef).
_IMMUTABLE_172 = '8cfd6cc21d1b8233cec30417cd5a43fe92646d793ec0ba19ddf4dcdd389285d4'
TEST_EDITS = (
    ('tests/test_delivery.py',
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n",
     f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n    ('{TAG}','{SXC_TAG}'):{_tuple(EXPECTED_TUPLE)},\n"),
    ('tests/test_delivery.py',
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,2,2,2))\n",
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,0,2,2,2))\n\n"
     "    def test_v052_coverage_adds_four_paper_and_five_article_cards_and_fifteen_citations_without_rewriting_history(self):\n"
     f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','{SXC_TAG}')]\n"
     f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
     f"        revised=EXPECTED_COVERAGE[('{TAG}','{SXC_TAG}')]\n"
     "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),"
     f"{_tuple(b - a for a, b in zip(PRIOR_TUPLE, EXPECTED_TUPLE))})\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  ['github:nodejs/release',180,'node-release']\n];\n",
     "  ['github:nodejs/release',180,'node-release']\n];\n"
     "// Sources first cited by agentic-vault v0.52.0, with their kinds; they use the text fallback until artwork is commissioned.\n"
     "const av052TextFallbacks=new Map([\n" + _FALLBACK_ENTRIES + "]);\n"
     "const declaredAv052TextFallback=source=>av052TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "test('all 180 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,180);\n"
     "  assert.equal(catalog.sources.length,180);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    const art=sourceArtwork(source);\n",
     "test('all 180 commissioned catalog sources have their own image in card and detail views',()=>{\n"
     "  assert.equal(manifest.count,180);\n"
     "  assert.equal(catalog.sources.filter(source=>!declaredAv052TextFallback(source)).length,180);\n"
     "  const images=[];\n"
     "  for(const source of catalog.sources){\n"
     "    if(declaredAv052TextFallback(source)) continue;\n"
     "    const art=sourceArtwork(source);\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length,catalog.sources.length);\n});\n",
     "  assert.equal(images.length,manifest.assets.length);\n"
     "  assert.equal(images.length+catalog.sources.filter(declaredAv052TextFallback).length,catalog.sources.length);\n});\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "  const originalRecords=manifest.assets.slice(0,172);\n"
     "  assert.equal(originalRecords.length,172);\n"
     f"  assert.equal(createHash('sha256').update(JSON.stringify(originalRecords)).digest('hex'),'{_FULL_172}');\n"
     "});\n",
     "  const originalRecords=manifest.assets.slice(0,172);\n"
     "  assert.equal(originalRecords.length,172);\n"
     "  // The full records hold the current evidence URLs, which follow the agentic-vault rows when a release repins them.\n"
     f"  if(avCatalogVersion==='{PRIOR_TAG}') assert.equal(createHash('sha256').update(JSON.stringify(originalRecords)).digest('hex'),'{_FULL_172}');\n"
     "  const immutableRecords=originalRecords.map(asset=>Object.fromEntries(\n"
     "    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))\n"
     "  ));\n"
     f"  assert.equal(createHash('sha256').update(JSON.stringify(immutableRecords)).digest('hex'),'{_IMMUTABLE_172}');\n"
     "});\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
     "    assert.deepEqual(record.generationEvidenceUrls,citations);\n",
     "    assert.deepEqual(record.currentEvidenceUrls,citations);\n"
     "    // Generation records keep the citations the image was made from; agentic-vault rows move with each release.\n"
     f"    if(avCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(record.generationEvidenceUrls,citations);\n"
     "    else assert.deepEqual(record.generationEvidenceUrls.map(pinnedFile),citations.map(pinnedFile));\n"),
    ('tests/artwork-uniqueness.test.mjs',
     "    assert.ok(!cover.includes('Future <source>'));\n  }\n});\n",
     "    assert.ok(!cover.includes('Future <source>'));\n  }\n});\n\n"
     "test('only the declared agentic-vault v0.52.0 sources render the uncommissioned text fallback',()=>{\n"
     "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
     "  assert.deepEqual(fallbacks.filter(id=>!av052TextFallbacks.has(id)),[]);\n"
     f"  if(avCatalogVersion==='{PRIOR_TAG}') assert.deepEqual(fallbacks,[]);\n"
     f"  if(avCatalogVersion==='{TAG}') for(const id of av052TextFallbacks.keys())\n"
     "    assert.ok(catalog.sources.some(source=>source.id===id),`Missing catalog source: ${id}`);\n"
     "  for(const id of fallbacks){\n"
     "    const source=catalog.sources.find(source=>source.id===id);\n"
     "    assert.equal(source.kind,av052TextFallbacks.get(id));\n"
     "    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);\n"
     "    for(const detail of [false,true]){\n"
     "      const html=artworkCover(source,{detail});\n"
     "      assert.ok(html.includes(detail?'detail-art':'source-art'));\n"
     "      assert.ok(html.includes('is-art-fallback'));\n"
     "      assert.ok(!html.includes('<img data-source-artwork'));\n"
     "    }\n"
     "  }\n"
     "});\n"),
)
TEST_FILES = tuple(dict.fromkeys(edit[0] for edit in TEST_EDITS))


def edit_tests(texts):
    """Apply each edit once; an edit whose result is already present is skipped. Returns the files changed."""
    out = dict(texts)
    for file, old, new in TEST_EDITS:
        text = out[file]
        if text.count(new) == 1:
            continue
        if text.count(old) != 1:
            raise ValueError('Test edit anchor needs exactly one match: ' + file)
        out[file] = text.replace(old, new)
    return out, sum(out[file] != texts[file] for file in texts)


def _git(plugin_root, *parts):
    return subprocess.check_output(['git', '-C', str(plugin_root), *parts],
                                   stderr=subprocess.DEVNULL).decode('utf-8')


def verify_tag(plugin_root, commit, tag=TAG):
    _validate_revision(commit, tag)
    if _git(plugin_root, 'cat-file', '-t', commit).strip() != 'commit':
        raise ValueError('Exact commit is not present locally')
    if _git(plugin_root, 'cat-file', '-t', 'refs/tags/' + tag).strip() != 'tag':
        raise ValueError('An annotated release tag is required')
    if _git(plugin_root, 'rev-parse', 'refs/tags/' + tag + '^{commit}').strip() != commit:
        raise ValueError('Release tag differs from the supplied exact commit')


def run(args):
    if not args.stand_in:
        verify_tag(args.plugin_root, args.commit, args.tag)
    elif _git(args.plugin_root, 'cat-file', '-t', args.commit).strip() != 'commit':
        raise ValueError('Stand-in commit is not present locally')
    cache = {}

    def read_lines(file):
        # Split on newlines only so line numbers match the GitHub blob view.
        if file not in cache:
            try:
                cache[file] = _git(args.plugin_root, 'show', args.commit + ':' + file).split('\n')
            except subprocess.CalledProcessError:
                raise LookupError('File absent from the supplied commit: ' + file) from None
        return cache[file]

    def url_index(url):
        identity = canonical_key(url)['key']
        found = subprocess.run(['git', '-C', str(args.plugin_root), 'grep', '-z', '-l', '-I', '-i',
                                '-F', '-e', grep_key(url), args.commit, '--'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if found.returncode not in (0, 1):
            raise ValueError('Git reference lookup failed')
        files = [name[len(args.commit) + 1:] for name in found.stdout.decode('utf-8').split('\0')
                 if name.startswith(args.commit + ':')]
        index = {file: naming_lines(identity, read_lines(file)) for file in files}
        return {file: lines for file, lines in index.items() if lines}

    root = args.atlas_root.resolve()
    source, art = root / 'data/registry.source.json', root / 'docs/card-artwork-unique-prompts.json'
    before = {path: path.read_bytes() for path in (source, art)}
    registry, artwork = (json.loads(before[path].decode('utf-8')) for path in (source, art))
    binding = verify_images(root, artwork)
    revised, images, summary = prepare_update(registry, artwork, read_lines, args.commit, args.tag,
                                               url_index=url_index)
    if verify_images(root, images) != binding:
        raise ValueError('Artwork image binding changed')
    test_paths = {file: root / file for file in TEST_FILES}
    texts = {file: path.read_bytes().decode('utf-8') for file, path in test_paths.items()}
    edited, test_edits = edit_tests(texts)
    if any(path.read_bytes() != raw for path, raw in before.items()):
        raise ValueError('Atlas inputs changed during preparation')
    if args.apply:
        if revised != registry or images != artwork:
            write_update([(source, revised), (art, images)])
        for file, path in test_paths.items():
            if edited[file] != texts[file]:
                path.write_bytes(edited[file].encode('utf-8'))
    print(json.dumps({'status': 'PASS', 'mode': 'applied' if args.apply else 'dry-run',
                      'publishable': not args.stand_in and args.public_verified,
                      'publicAvailability': 'caller asserted' if args.public_verified else 'not verified by this helper',
                      'standIn': args.stand_in, 'existingArtworkBindingSha256': binding,
                      'testEditsApplied': test_edits, 'testFilesEdited': sorted(f for f in texts if edited[f] != texts[f]),
                      **summary}, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True, help='Exact public commit that the annotated v0.52.0 tag names')
    parser.add_argument('--tag', default=TAG)
    parser.add_argument('--atlas-root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--public-verified', action='store_true',
                        help='Caller verified that the commit, tag and cited files are public')
    parser.add_argument('--stand-in', action='store_true', help='Dry run without the tag check; never publishable')
    args = parser.parse_args(argv)
    try:
        _validate_revision(args.commit, args.tag)
    except ValueError as error:
        parser.error(str(error))
    if args.apply and (not args.public_verified or args.stand_in):
        parser.error('--apply requires --public-verified and cannot use --stand-in')
    if args.stand_in and args.public_verified:
        parser.error('--stand-in is never publishable or public-verified')
    try:
        return run(args)
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError, UnicodeError, LookupError) as error:
        message = 'Local Git verification failed' if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
