"""Offline, dry-run-first agentic-vault v0.48.0 citation update from exact Git blobs.

Adds the fourteen cards that the v0.48.0 release note's reference table cites
for the first time (eleven Google Antigravity documentation pages, the
google-antigravity/antigravity-cli repository, tw93/Waza and obra/superpowers)
and repins every existing agentic-vault citation to the supplied commit,
because the catalog schema binds each citation of a plugin to that plugin's
declared snapshot. Each existing row keeps its file and excerpt; its line
follows the excerpt, which must occur exactly once in that file at the new
revision, or the helper stops and names every row that does not.
Existing notes, roles, semantic-crosscheck uses and artwork identities stay as
they are; only the commit, and a line number where the source moved, change.
A line names a new source when an address on it, written with or without its
scheme, has that source's canonical identity: a deeper path of a repository
names the repository, a longer path of a page is another page. Every such line
of the plugin must be covered by one of the source's rows, except two kinds
that are reported and not cited: a line of the generated Antigravity package
(antigravity/<path>) that equals a cited line of <path> at the same number, and
the listed test lines that pin the release note's link text. A citation added
later therefore stops the helper instead of being left out. New cards use the
text fallback; no image, prompt or UI is created or changed.

No fetch, commit, push, publication or plugin change. The caller verifies that
the commit and annotated tag are public before --apply --public-verified.
--stand-in exists only for rehearsals in a throwaway clone: it skips the tag
check and may read file text from another revision (--content-rev), so its
output is never valid catalog data.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update

ROOT=Path(__file__).resolve().parents[1]
PREFIX='https://github.com/Technoetic/agentic-vault/blob/'
TAG='v0.48.0'
PRIOR_TAG='v0.47.0'
RELEASE='docs/releases/v0.48.0.md'
GUIDE='docs/antigravity.md'
GENERATED='antigravity/'
METADATA_TEST='tests/test_release_metadata.py'

DOCS='https://antigravity.google/docs/'
BUILD_PLUGINS=DOCS+'build-plugins'
HOOKS=DOCS+'hooks'
DISCOVERY=DOCS+'customization-discovery'
PLUGINS=DOCS+'plugins'
RULES=DOCS+'rules'
PERMISSIONS=DOCS+'permissions'
PERMISSIONS_COMMAND=DOCS+'cli/commands/permissions'
SETTINGS=DOCS+'settings'
CLI_REFERENCE=DOCS+'cli/reference'
SKILLS=DOCS+'skills'
FAQ=DOCS+'faq'
AGY_CLI='https://github.com/google-antigravity/antigravity-cli'
WAZA='https://github.com/tw93/Waza'
SUPERPOWERS='https://github.com/obra/superpowers'
NO_COPY='No code or text of the source is copied; the plugin wording is its own.'
FIRST=('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog; '
       'the v0.48.0 release note says earlier documents of the repository did not cite it. ')
READ='Read 2026-11-13, the date the release note gives; the page may have changed since. '
DOCS_ROW=('One of the eleven Google Antigravity documentation pages (Build plugins, Hooks, Customization discovery, '
 'Plugins, Rules, Permissions, the /permissions command, Settings, CLI reference, Skills, FAQ) that the v0.48.0 release '
 'note lists in one reference row; the row names the page of some statements (given in parentheses) and does not say '
 'which page the others come from. Together they are the basis for the format of the generated Antigravity CLI '
 "package antigravity/ and its hook input and output, for the guide's permissions, data and hands-on checks, and for "
 "the release's known limits: where the plugin manifest sits and which keys it allows; the components at the plugin "
 'root (skills/ and hooks.json, no commands/) and the install location; the six hook events (no compaction or '
 'session-end event); plugin hooks running in the plugin folder and receiving the workspace as workspacePaths on '
 'standard input; JSON on standard output and injectSteps; a non-zero exit code logged and ignored; skill front '
 'matter; rule-file discovery (AGENTS.md is read, CLAUDE.md is not among the loaded locations) and the cut of rule '
 'files longer than 24,000 bytes once @ includes are expanded (Rules); the Global, Shared and Project scopes of '
 '/permissions, a read_file deny that also blocks write_file on the same path, and Windows paths matched without the '
 'drive letter and with / (Permissions, the /permissions command); the data collection setting, stored with the '
 'account and always off for business accounts (Settings); the workspace trust list and --log-file, which changes the '
 'CLI log file path (CLI reference); a /<skill name> slash command for each skill (Skills), and plugin skills, too, '
 'called with /<skill name> (Plugins, Build plugins); plugin skill names that start with the plugin name '
 '(Customization discovery); and the FAQ on wrapping agy inside third-party agents under consumer plans. The release '
 "ran no real agy conversation: agy's behaviour (check, install and list results and the automatic conversion) was "
 'obtained, not from public documents, by running the login-free agy plugin commands of agy 1.5.7 in an isolated '
 'home, and the hook tests use synthetic hook input. ')
FAQ_USE=('The release note names this page for the statement that wrapping agy inside third-party coding agents or apps '
 'is not supported under consumer plans and that accessing an Antigravity login with third-party software violates '
 'its terms; for that reason no agent-run agy check was made. The guide (docs/antigravity.md) adds that the '
 "plugin's skills, hooks and Jarvis bridge do not run agy. ")
CLI_USE=('The release note pins its README and CHANGELOG as read on 2026-11-13 at main 87bd973; the catalog update '
 'resolved that commit through the GitHub API on 2026-11-13 as 87bd97327a72d62d553c3aede8cf77752ae4c59a ("Update '
 'CHANGELOG.md for 1.5.7"). Used for the subpath install of 1.0.7, '
 'PLUGIN_ROOT and PLUGIN_DATA given to hooks from 1.5.3, cwd and hookEventName in hook input from 1.5.4, the 1.5.6 '
 'validator warning on ${PLUGIN_ROOT} in hook commands and the Auto mode default of 1.5.7: the basis for recommending '
 'agy 1.5.6 or later, for relative paths in hook commands and for the order of the inputs in which the hooks look for '
 'the vault. ')
WAZA_USE=('A public repository that keeps an Antigravity plugin in a subfolder (plugins/waza). Running agy 1.5.7 in an '
 'isolated home, the release installed it from the /tree/main/plugins/waza and /tree/v3.42.0/plugins/waza addresses: '
 'both exited 0 with source "antigravity", 8 skills and 6 rules, and the install folder held only the content of the '
 "subfolder (no .git); the same method installed agentic-vault's own /tree/v0.45.1 address at that tag. It is the basis "
 'for the install address that pins a tag and a subfolder, a syntax the official documentation does not show. The '
 'release note gives no read date for this row. ')
SUPERPOWERS_NOTE=('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog. The '
 "v0.48.0 release note says earlier documents did not cite this repository's layout, and that the internal plan "
 'documents under docs/superpowers/plans/ named its superpowers: skills (such as '
 'superpowers:subagent-driven-development) as the way of working; those plans name skills, not this address, and are '
 'not recorded here as a use. A repository that keeps the manifests of several hosts at one root: '
 '.antigravity-plugin/plugin.json at the root and no root hooks.json for Antigravity (skill-centred; GitHub code '
 'search). Hooks and commands are central to agentic-vault itself: adding an Antigravity manifest at the '
 "agentic-vault root made agy 1.5.7 turn off the automatic conversion of agentic-vault's Claude layout and not read "
 "its commands/ or hooks/hooks.json, and agentic-vault's root AGENTS.md left a validator warning that went away only "
 'when the plugin root moved to a subfolder, so the release uses a generated subfolder instead of the same-root '
 'layout. The release note gives no read date for this row. ')

def _page(url,title,aliases,extra=''):
    return ('url:'+url,'article','Google Antigravity documentation: '+title,url,None,[],aliases,[],
            FIRST+READ+DOCS_ROW+extra+NO_COPY,((RELEASE,'('+url+')'),(GUIDE,'('+url+')')))

# id, kind, title, url, year, extra strong keys, aliases, tags, note,
# ((file, text that must appear on exactly one line, and that line must name the source), ...).
# The release citation comes first.
REFERENCES=(
 _page(BUILD_PLUGINS,'Build plugins',[]),
 _page(HOOKS,'Hooks',[]),
 _page(DISCOVERY,'Customization discovery',[]),
 _page(PLUGINS,'Plugins',[]),
 _page(RULES,'Rules',[]),
 _page(PERMISSIONS,'Permissions',[]),
 _page(PERMISSIONS_COMMAND,'/permissions command',[]),
 _page(SETTINGS,'Settings',[]),
 _page(CLI_REFERENCE,'CLI reference',[]),
 _page(SKILLS,'Skills',[]),
 _page(FAQ,'FAQ',['Antigravity FAQ'],FAQ_USE),
 ('github:google-antigravity/antigravity-cli','project','google-antigravity/antigravity-cli',AGY_CLI,None,[],
  ['antigravity-cli'],[],FIRST+CLI_USE+NO_COPY,((RELEASE,'('+AGY_CLI+')'),(GUIDE,'('+AGY_CLI+')'))),
 ('github:tw93/waza','project','tw93/Waza',WAZA,None,[],['Waza'],[],FIRST+WAZA_USE+NO_COPY,((RELEASE,'('+WAZA+')'),)),
 ('github:obra/superpowers','project','obra/superpowers',SUPERPOWERS,None,[],['superpowers'],[],SUPERPOWERS_NOTE+NO_COPY,
  ((RELEASE,'('+SUPERPOWERS+')'),)),
)
# Test lines that may name a new source without a row: they pin the release note's link text, which is cited.
# A listed line may be absent; a listed text on two lines, or any other test line naming a source, stops the helper.
ALLOWED_TEST_LINES=(
 (METADATA_TEST,'"]('+AGY_CLI+')"'),
 (METADATA_TEST,'"]('+WAZA+')"'),
 (METADATA_TEST,'"]('+SUPERPOWERS+')"'),
)
NEW_IDS={row[0] for row in REFERENCES}
NEW_CITATIONS=sum(len(row[9]) for row in REFERENCES)
# The published catalog this update starts from: agentic-vault v0.47.0 with semantic-crosscheck v0.24.0 (public main
# 80b7884, which added four semantic-crosscheck cards to the v0.47.0 catalog of 149 sources and 269 citations).
SXC_TAG='v0.24.0'
BASE={'total':153,'citations':277,'av':211}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE=(56,53,7,153,277)
EXPECTED_TUPLE=(56,56,18,167,303)

ADDRESS=re.compile(r'(?i)(?:https?://)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s<>()\[\]{}"\'`|\\]*)?')
# Artwork files: card-NNN.webp, a revision card-NNN-vN.webp, or a named card such as card-150-stryker-js-v024.webp
# (semantic-crosscheck v0.24.0); nothing outside media/cards and no dots or upper case in the name.
ARTWORK_PATH=re.compile(r'media/cards/card-[0-9]{3}(?:-[a-z0-9]+)*\.webp')

def identities_on(text):
    """Canonical identities of the web addresses on a line, written with or without scheme."""
    found=set()
    for match in ADDRESS.finditer(text):
        token=re.sub(r'(?i)^https?://','',match.group(0)).rstrip('.,;:!?*_~')
        identity=canonical_key('https://'+token) if token else None
        if identity:found.add(identity['key'])
    return found

def naming_lines(identity,lines):
    """Line numbers (1-based) that hold an address whose canonical identity is this source."""
    return [i+1 for i,text in enumerate(lines) if identity in identities_on(text)]

def grep_key(url):
    """Case-insensitive fixed text that every line naming the source contains."""
    identity=canonical_key(url)['key']
    return 'github.com/'+identity[len('github:'):] if identity.startswith('github:') else urlsplit(url).hostname

def excerpt_of(text):
    return text.strip()[:220]

def cited_rows(cites,read_lines,commit,identity):
    rows=[];covered=set()
    for file,needle in cites:
        lines=read_lines(file);matches=[i+1 for i,text in enumerate(lines) if needle in text]
        if len(matches)!=1:raise ValueError(f'New citation needs one exact line: {file}: {needle} ({len(matches)} lines)')
        line=matches[0];excerpt=excerpt_of(lines[line-1])
        if sum(excerpt_of(text)==excerpt for text in lines)!=1:raise ValueError(f'New citation excerpt is not unique in its file: {file}#L{line}')
        if line not in naming_lines(identity,lines):raise ValueError(f'The cited line does not name {identity}: {file}#L{line}')
        covered.add((file,line))
        rows.append({'file':file,'line':line,'url':f'{PREFIX}{commit}/{file}#L{line}','excerpt':excerpt})
    return rows,covered

def allowed_test_lines(read_lines):
    allowed=set()
    for file,needle in ALLOWED_TEST_LINES:
        try:lines=read_lines(file)
        except LookupError:continue
        matches=[i+1 for i,text in enumerate(lines) if needle in text]
        if len(matches)>1:raise ValueError(f'A listed test line is not unique: {file}: {needle} ({len(matches)} lines)')
        allowed.update((file,line) for line in matches)
    return allowed

def generated_copies(named,covered,read_lines):
    """Lines of antigravity/<path> equal to a cited line of <path> at the same number."""
    copies=set()
    for file,line in named-covered:
        origin=file[len(GENERATED):]
        if file.startswith(GENERATED) and (origin,line) in covered and read_lines(file)[line-1]==read_lines(origin)[line-1]:
            copies.add((file,line))
    return copies

def immutable_artwork(artwork):
    return [{k:v for k,v in asset.items() if k not in {'evidenceUrls','currentEvidenceUrls'}} for asset in artwork['assets']]

def av_rows(registry):
    return sum(len(use['evidence']) for s in registry['sources'] for use in s['uses'] if use['plugin']=='agentic-vault')

def repin(revised,read_lines,commit):
    """Move every agentic-vault row to the commit; the line follows the excerpt, which must occur exactly once."""
    remapped={};failures=[];count=moved=0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin']!='agentic-vault':continue
            for row in use['evidence']:
                count+=1;old_line,old_url=row['line'],row['url'];name=f"{source['id']} / {row['file']}#L{old_line}"
                try:lines=read_lines(row['file'])
                except (LookupError,ValueError,OSError):
                    failures.append(name+': file missing at the new revision');continue
                matches=[i+1 for i,text in enumerate(lines) if excerpt_of(text)==row['excerpt']]
                if len(matches)!=1:
                    failures.append(f"{name}: excerpt found on {len(matches)} lines ({row['excerpt'][:60]!r})");continue
                line=matches[0]
                row.update(line=line,url=f'{PREFIX}{commit}/{row["file"]}#L{line}')
                if old_url in remapped and remapped[old_url]!=row['url']:failures.append(name+': ambiguous old citation map')
                remapped[old_url]=row['url'];moved+=line!=old_line
    if failures:raise ValueError(f'{len(failures)} agentic-vault row(s) cannot be repinned: '+'; '.join(failures))
    return remapped,count,moved

def _locations(pairs):
    return [f'{f}#L{n}' for f,n in sorted(pairs)]

def prepare_update(registry,artwork,read_lines,commit,*,url_index,updated_at=None):
    """url_index(url) -> {file: [line, ...]} of every line in the plugin revision that names the source."""
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Exact lowercase 40-character commit required')
    before=merge_sources(registry['sources']);validate_catalog({**registry,'sources':before})
    version=registry['snapshots']['agentic-vault']['version']
    present=NEW_IDS&{s['id'] for s in registry['sources']}
    if version==PRIOR_TAG:
        if present or metrics(before)['total']!=BASE['total'] or metrics(before)['citations']!=BASE['citations'] or av_rows(registry)!=BASE['av']:
            raise ValueError(f"Expected the published v0.47.0 baseline of {BASE['total']} sources and {BASE['citations']} "
                             f"citations ({BASE['av']} agentic-vault)")
    elif version==TAG:
        if present!=NEW_IDS:raise ValueError('A partial v0.48.0 update needs review')
    else:raise ValueError('Unexpected agentic-vault snapshot '+version+'; rebase this script on the current catalog')
    # Each key names one work. A hit under another id needs a reviewed merge, not a second card.
    for row in REFERENCES:
        if canonical_key(row[3])['key']!=row[0]:raise ValueError('Canonical identity mismatch: '+row[0])
        wanted={row[0],*row[5]}
        for extra in row[5]:
            if not canonical_key(extra[4:]) or canonical_key(extra[4:])['key']!=extra:raise ValueError('Extra key is not canonical: '+extra)
        for source in registry['sources']:
            if source['id']!=row[0] and wanted&(set(source['keys'])|{source['id']}):
                raise ValueError('Existing source identity needs explicit reviewed merge: '+row[0])
    revised,images=deepcopy(registry),deepcopy(artwork)
    old_ids=[s['id'] for s in registry['sources']]
    old_sxc=[(s['id'],deepcopy(u)) for s in registry['sources'] for u in s['uses'] if u['plugin']=='semantic-crosscheck']
    old_shape=[(s['id'],s['kind'],s['title'],s.get('note'),s['keys'],s['aliases'],s['tags'],
                [(u['plugin'],u['role'],[(r['file'],r['excerpt']) for r in u['evidence']]) for u in s['uses']]) for s in registry['sources']]
    remapped,count,moved=repin(revised,read_lines,commit)
    allowed=allowed_test_lines(read_lines)
    added=[];occurrences={};copied={};unlisted={}
    for identity,kind,title,url,year,extra,aliases,tags,note,cites in REFERENCES:
        evidence,covered=cited_rows(cites,read_lines,commit,identity)
        if evidence[0]['file']!=RELEASE:raise ValueError('New reference lacks exact release citation: '+identity)
        named={(file,line) for file,lines in url_index(url).items() for line in lines}
        copies=generated_copies(named,covered,read_lines);tests=(named-covered)&allowed
        uncovered=named-covered-copies-tests
        if uncovered or covered-named:
            raise ValueError(f'Every line that names {url} needs its own row; uncovered: '+', '.join(_locations(uncovered))
                             +'; expected but absent: '+', '.join(_locations(covered-named)))
        occurrences[url]=_locations(covered);copied[url]=_locations(copies);unlisted[url]=_locations(tests)
        record={'id':identity,'kind':kind,'title':title,'url':url,'year':year,'keys':[identity,*extra],
                'aliases':list(aliases),'tags':list(tags),'note':note,
                'uses':[{'plugin':'agentic-vault','role':'reference','evidence':evidence}]}
        prior=next((s for s in revised['sources'] if s['id']==identity),None)
        if prior is not None:
            if prior!=record:raise ValueError('Previously applied record differs; manual review required: '+identity)
            continue
        revised['sources'].append(record);added.append(identity)
    revised['snapshots']['agentic-vault']={'name':'Agentic Vault','version':TAG,'commit':commit,
        'url':f'https://github.com/Technoetic/agentic-vault/tree/{commit}'}
    if revised!=registry:revised['updatedAt']=updated_at or datetime.now(timezone.utc).isoformat()
    merged=merge_sources(revised['sources']);validate_catalog({**revised,'sources':merged})
    # Existing records keep kind, title, notes, keys, aliases, tags, roles, files and excerpts; only commit/line move.
    new_shape=[(s['id'],s['kind'],s['title'],s.get('note'),s['keys'],s['aliases'],s['tags'],
                [(u['plugin'],u['role'],[(r['file'],r['excerpt']) for r in u['evidence']]) for u in s['uses']])
               for s in revised['sources'] if s['id'] in old_ids]
    if new_shape!=old_shape or [s['id'] for s in revised['sources']][:len(old_ids)]!=old_ids:
        raise ValueError('An existing record changed beyond its commit and line')
    if revised['snapshots']['semantic-crosscheck']!=registry['snapshots']['semantic-crosscheck'] or [
        (s['id'],u) for s in revised['sources'] for u in s['uses'] if u['plugin']=='semantic-crosscheck']!=old_sxc:
        raise ValueError('Unrelated semantic-crosscheck snapshot or use changed')
    counts=metrics(merged)
    av=metrics([s for s in merged if any(u['plugin']=='agentic-vault' for u in s['uses'])])
    tuple_now=(av['paper'],av['project']+av['format'],av['article'],counts['total'],counts['citations'])
    if tuple_now!=EXPECTED_TUPLE:raise ValueError(f'Unexpected coverage {tuple_now}; expected {EXPECTED_TUPLE}')
    for asset in images['assets']:
        for field in ('evidenceUrls','currentEvidenceUrls'):
            if field not in asset:raise ValueError('Existing artwork current evidence field missing')
            if any(u.startswith(PREFIX) and u not in remapped for u in asset[field]):raise ValueError('Artwork URL not in prior citation map')
            asset[field]=[remapped.get(u,u) for u in asset[field]]
    if images['count']!=artwork['count'] or len(images['assets'])!=artwork['count'] or immutable_artwork(images)!=immutable_artwork(artwork):
        raise ValueError('Artwork identity, prompt or generation provenance changed')
    if NEW_IDS&{a['sourceId'] for a in images['assets']}:raise ValueError('Uncommissioned v0.48.0 sources must use text fallback')
    return revised,images,{'priorAgenticVaultCitationsRepinned':count-(0 if version==PRIOR_TAG else NEW_CITATIONS),
        'repinnedRowsTotal':count,'remappedLines':moved,'addedSourceIds':added,'newCitationRows':NEW_CITATIONS,
        'citedAddressLines':occurrences,'generatedCopyLines':copied,'testLinesNotCited':unlisted,
        'counts':counts,'agenticVaultCounts':av,'coverageTuple':list(tuple_now),
        'artworkCount':images['count'],'uncommissionedSourceIds':sorted(NEW_IDS),'snapshot':revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot':registry['snapshots']['semantic-crosscheck']}

# Test expectations: exact, guarded, idempotent text edits. tests/test_delivery.py keeps every text that the
# v0.46.0 and v0.47.0 helpers' edits and the semantic-crosscheck v0.24.0 update produced (the helpers' tests read it);
# the v0.48.0 coverage line is keyed by the current semantic-crosscheck version and follows the v0.24.0 line. Those
# helpers read the artwork test from tests/fixtures/artwork-v047-before-commissioning.mjs.txt, so the edits below
# apply to the current artwork test.
def _tuple(values):return '('+','.join(str(v) for v in values)+')'
_FALLBACK_IDS=''.join(f"  '{identity}'{',' if index<len(REFERENCES)-1 else ''}\n" for index,identity in enumerate(row[0] for row in REFERENCES))
_TWELVE_DIGEST='28d76e85647acd97c35566b48bb66d664b3a38175314f73aa60cfb7537cc5da8'
TEST_EDITS=(
 ('tests/test_delivery.py',
  f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n",
  f"    ('{PRIOR_TAG}','{SXC_TAG}'):{_tuple(PRIOR_TUPLE)},\n    ('{TAG}','{SXC_TAG}'):{_tuple(EXPECTED_TUPLE)},\n"),
 ('tests/test_delivery.py',
  "        self.assertIsNone(re.search(pattern,text),'A credential or local path was found in public data')\n",
  "        self.assertIsNone(re.search(pattern,text),'A credential or local path was found in public data')\n\n"
  "    def test_v048_coverage_adds_the_release_cited_cards_without_rewriting_history(self):\n"
  f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','{SXC_TAG}')]\n"
  f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
  f"        revised=EXPECTED_COVERAGE[('{TAG}','{SXC_TAG}')]\n"
  f"        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),{_tuple(b-a for a,b in zip(PRIOR_TUPLE,EXPECTED_TUPLE))})\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  ['github:nvidia/ruler',149]\n];\n",
  "  ['github:nvidia/ruler',149]\n];\n"
  "const avCatalogVersion=catalog.snapshots['agentic-vault'].version;\n"
  "const av048TextFallbacks=new Set([\n"+_FALLBACK_IDS+"]);\n"
  "const declaredTextFallback=source=>avCatalogVersion==='v0.48.0'&&av048TextFallbacks.has(source.id)&&!sourceArtwork(source).src;\n"
  "const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/').replace(new RegExp('#L[0-9]+$'),'');\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "    assert.deepEqual(record.generationEvidenceUrls,citations);\n"
  "    for(const detail of [false,true]){\n"
  "      const html=artworkCover(source,{detail});\n",
  "    if(avCatalogVersion==='v0.47.0') assert.deepEqual(record.generationEvidenceUrls,citations);\n"
  "    else assert.deepEqual(record.generationEvidenceUrls.map(pinnedFile),citations.map(pinnedFile));\n"
  "    for(const detail of [false,true]){\n"
  "      const html=artworkCover(source,{detail});\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  assert.equal(digest,'97ffb3dbe6005aa2d0c45c3e8e2741ae1b49217fafadbf7ff50044293455539b');\n});\n",
  "  assert.equal(digest,'97ffb3dbe6005aa2d0c45c3e8e2741ae1b49217fafadbf7ff50044293455539b');\n});\n\n"
  "test('the twelve images commissioned at agentic-vault v0.47.0 keep their generation records when citations move',()=>{\n"
  "  const generationRecords=manifest.assets.slice(137,149).map(asset=>Object.fromEntries(\n"
  "    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))\n"
  "  ));\n"
  "  assert.deepEqual(generationRecords.map(record=>[record.sourceId,record.index]),completedArtwork);\n"
  "  const digest=createHash('sha256').update(JSON.stringify(generationRecords)).digest('hex');\n"
  "  assert.equal(digest,'"+_TWELVE_DIGEST+"');\n"
  "});\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "test('every current catalog source has its own commissioned image in card and detail views',()=>{\n"
  "  const expectedCount=catalog.snapshots['semantic-crosscheck'].version==='v0.24.0'?153:149;\n"
  "  assert.equal(manifest.count,expectedCount);\n"
  "  const images=[];\n"
  "  for(const source of catalog.sources){\n"
  "    const art=sourceArtwork(source);\n"
  "    assert.ok(art.src,`Missing commissioned artwork: ${source.id}`);\n",
  "test('every current catalog source except the declared v0.48.0 text fallbacks has its own commissioned image in card and detail views',()=>{\n"
  "  const expectedCount=catalog.snapshots['semantic-crosscheck'].version==='v0.24.0'?153:149;\n"
  "  assert.equal(manifest.count,expectedCount);\n"
  "  const images=[];\n"
  "  for(const source of catalog.sources){\n"
  "    const art=sourceArtwork(source);\n"
  "    if(declaredTextFallback(source)) continue;\n"
  "    assert.ok(art.src,`Missing commissioned artwork: ${source.id}`);\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  assert.equal(images.length,catalog.sources.length);\n});\n",
  "  assert.equal(images.length+catalog.sources.filter(declaredTextFallback).length,catalog.sources.length);\n});\n\n"
  "test('the sources first cited by agentic-vault v0.48.0 render the text fallback until their artwork is commissioned',()=>{\n"
  "  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);\n"
  "  if(avCatalogVersion==='v0.48.0') assert.deepEqual(new Set(fallbacks),av048TextFallbacks);\n"
  "  else assert.deepEqual(fallbacks,[]);\n"
  "  for(const id of fallbacks){\n"
  "    const source=catalog.sources.find(source=>source.id===id);\n"
  "    for(const detail of [false,true]){\n"
  "      const html=artworkCover(source,{detail});\n"
  "      assert.ok(html.includes('is-art-fallback'));\n"
  "      assert.ok(!html.includes('<img data-source-artwork'));\n"
  "    }\n"
  "  }\n"
  "});\n"),
 # The semantic-crosscheck v0.24.0 test rebuilds the catalog it was published on by removing only its own four
 # sources from the live files, which holds while agentic-vault is at v0.47.0. After this update the live files hold
 # fourteen sources without artwork and agentic-vault rows pinned to v0.48.0, so that reconstruction cannot be made
 # from them; the test is skipped there instead of being changed. No semantic-crosscheck data changes.
 ('tests/test_sxc024_update.py',
  "    def test_published_identity_set_and_all_prior_raw_records_are_preserved(self):\n"
  "        registry = json.loads((ROOT / 'data/registry.source.json').read_text(encoding='utf8'))\n"
  "        artwork = json.loads((ROOT / 'docs/card-artwork-unique-prompts.json').read_text(encoding='utf8'))\n",
  "    def test_published_identity_set_and_all_prior_raw_records_are_preserved(self):\n"
  "        registry = json.loads((ROOT / 'data/registry.source.json').read_text(encoding='utf8'))\n"
  "        artwork = json.loads((ROOT / 'docs/card-artwork-unique-prompts.json').read_text(encoding='utf8'))\n"
  f"        if registry['snapshots']['agentic-vault']['version'] != '{PRIOR_TAG}':\n"
  "            # The reconstruction below removes only this update's sources, so it describes the catalog this update\n"
  f"            # was published on (agentic-vault {PRIOR_TAG}). agentic-vault {TAG} adds text-fallback sources without\n"
  "            # artwork and repins every agentic-vault row; tests/test_av048_update.py covers that update.\n"
  f"            self.skipTest('The live catalog is past the agentic-vault {PRIOR_TAG} snapshot this reconstruction assumes')\n"),
)

def edit_tests(texts):
    """Apply each edit once; an edit whose result is already present is skipped."""
    out=dict(texts);applied=0
    for file,old,new in TEST_EDITS:
        text=out[file]
        if text.count(new)==1:continue
        if text.count(old)!=1:raise ValueError('Test edit anchor needs exactly one match: '+file)
        out[file]=text.replace(old,new);applied+=1
    return out,applied

def verify_images(atlas_root,artwork):
    seen=set()
    for asset in artwork['assets']:
        if asset['sourceId'] in seen or not ARTWORK_PATH.fullmatch(asset['output']):
            raise ValueError('Unsafe or duplicate artwork assignment')
        seen.add(asset['sourceId']);path=Path(atlas_root)/asset['output']
        if path.is_symlink() or not path.is_file():raise ValueError('Missing or indirect artwork file')
        raw=path.read_bytes()
        if len(raw)!=asset['bytes'] or hashlib.sha256(raw).hexdigest()!=asset['sha256']:raise ValueError('Artwork bytes differ from manifest')
    return hashlib.sha256(json.dumps(immutable_artwork(artwork),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plugin-root',type=Path,required=True,help='Local clone of the public agentic-vault repository')
    p.add_argument('--commit',required=True,help='Exact public commit that the v0.48.0 tag names')
    p.add_argument('--atlas-root',type=Path,default=ROOT)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--public-verified',action='store_true',help='Caller verified the commit, tag and cited files are public')
    p.add_argument('--stand-in',action='store_true',help='Rehearsal only: no tag check; output is not catalog data')
    p.add_argument('--content-rev',help='Rehearsal only: read file text from this revision instead of --commit')
    args=p.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}',args.commit):p.error('--commit needs the exact 40-character lowercase commit')
    if args.content_rev and not args.stand_in:p.error('--content-rev is allowed only with --stand-in')
    if args.apply and not (args.public_verified or args.stand_in):p.error('--apply needs --public-verified')
    if args.stand_in and args.public_verified:p.error('--stand-in output can never be public-verified')
    try:return run(args)
    except subprocess.CalledProcessError as error:
        message='git '+' '.join(error.cmd[3:])+' failed with exit '+str(error.returncode)
    except (OSError,ValueError,KeyError,UnicodeError) as error:message=str(error)
    print(json.dumps({'status':'error','message':message},ensure_ascii=False),file=sys.stderr)
    return 1

def run(args):
    def git(*parts):return subprocess.check_output(['git','-C',str(args.plugin_root),*parts],stderr=subprocess.DEVNULL).decode('utf-8')
    if git('cat-file','-t',args.commit).strip()!='commit':raise ValueError('Commit not present in plugin root')
    if not args.stand_in:
        if git('cat-file','-t','refs/tags/'+TAG).strip()!='tag':raise ValueError('Annotated v0.48.0 tag required')
        if git('rev-parse','refs/tags/'+TAG+'^{commit}').strip()!=args.commit:raise ValueError('Tag source differs from --commit')
    rev=args.content_rev or args.commit
    if git('cat-file','-t',rev).strip()!='commit':raise ValueError('Content revision is not a commit')
    cache={}
    def read_lines(file):
        # Split on newlines only so line numbers match the GitHub blob view.
        if file not in cache:
            try:cache[file]=git('show',rev+':'+file).split('\n')
            except subprocess.CalledProcessError:raise LookupError('File missing at the content revision: '+file) from None
        return cache[file]
    def url_index(url):
        identity=canonical_key(url)['key']
        found=subprocess.run(['git','-C',str(args.plugin_root),'grep','-z','-l','-I','-i','-F','-e',grep_key(url),rev,'--'],
                             stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        if found.returncode not in (0,1):raise ValueError('git grep failed with exit '+str(found.returncode))
        files=[name[len(rev)+1:] for name in found.stdout.decode('utf-8').split('\0') if name.startswith(rev+':')]
        index={file:naming_lines(identity,read_lines(file)) for file in files}
        return {file:lines for file,lines in index.items() if lines}
    root=args.atlas_root.resolve()
    source=root/'data/registry.source.json';art=root/'docs/card-artwork-unique-prompts.json'
    before={path:path.read_bytes() for path in (source,art)}
    registry=json.loads(before[source].decode('utf-8'));artwork=json.loads(before[art].decode('utf-8'))
    bindings=verify_images(root,artwork)
    revised,images,summary=prepare_update(registry,artwork,read_lines,args.commit,url_index=url_index)
    if verify_images(root,images)!=bindings:raise ValueError('Image binding changed')
    test_paths={file:root/file for file in {e[0] for e in TEST_EDITS}}
    texts={file:path.read_bytes().decode('utf-8') for file,path in test_paths.items()}
    edited,test_edits=edit_tests(texts)
    if any(path.read_bytes()!=content for path,content in before.items()):raise ValueError('Atlas input changed while preparing')
    if args.apply:
        if revised!=registry or images!=artwork:write_update([(source,revised),(art,images)])
        for file,path in test_paths.items():
            if edited[file]!=texts[file]:path.write_bytes(edited[file].encode('utf-8'))
    print(json.dumps({'status':'PASS','mode':('applied' if args.apply else 'dry-run')+(' stand-in' if args.stand_in else ''),
        'contentRevision':rev,'publicAvailability':'caller asserted' if args.public_verified else 'not verified by this helper',
        'existingArtworkBindingSha256':bindings,'testEditsApplied':test_edits,**summary},ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
