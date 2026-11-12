"""Offline, dry-run-first agentic-vault v0.47.0 citation update from exact Git blobs.

Adds two documentation cards that the v0.47.0 release note cites for the first
time (the prompting guide for Claude Fable 5.2 and the Claude Code skills page)
and repins every existing agentic-vault citation to the supplied commit,
because the catalog schema binds each citation of a plugin to that plugin's
declared snapshot. Each existing row keeps its file and excerpt; its line
follows the excerpt, which must occur exactly once in that file at the new
revision, or the helper stops and names every row that does not.
Existing notes, roles, semantic-crosscheck uses and artwork identities stay as
they are; only the commit, and a line number where the source moved, change.
Every line of the plugin that names a new source's address must be covered by
one of its rows, so a citation added later stops the helper instead of being
left out. New cards use the text fallback; no image, prompt or UI is created
or changed.

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
from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update

ROOT=Path(__file__).resolve().parents[1]
PREFIX='https://github.com/Technoetic/agentic-vault/blob/'
TAG='v0.47.0'
PRIOR_TAG='v0.46.0'
RELEASE='docs/releases/v0.47.0.md'
HARDENING='docs/hardening.md'
SECURITY='SECURITY.md'

FABLE='https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2'
SKILLS='https://code.claude.com/docs/en/skills'
NO_COPY='No code or text of the page is copied; the plugin wording is its own.'
FIRST=('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog; '
       'the v0.47.0 release note says earlier documents of the repository did not cite it. '
       'Read 2026-11-12, the date the release note gives; the page may have changed since.')

# Where the address sits relative to a cited line: 0 on the line itself, -1 on the line just
# before it (docs/hardening.md repeats the same link line, so its rows anchor on the line that
# closes each citing sentence with the read date), None when the file does not name the address
# and the release note's reference table names the file as where the source is used.
ON_LINE,LINE_BEFORE,NOT_IN_FILE=0,-1,None

# id, kind, title, url, year, extra strong keys, aliases, tags, note,
# ((file, text that must appear on exactly one line, address position), ...). The release citation comes first.
REFERENCES=(
 ('url:'+FABLE,'article','Prompting Claude Fable 5.2',FABLE,None,[],['prompting guide for Claude Fable 5.2'],[],
  FIRST+' A comparison review set the commands, rules, bridge and adapters of agentic-vault v0.47.0 against this '
  'guide, and the release cites it as the reason for its items on saying who owns what (the contributor guide; '
  'the engine-copy ownership line was tried and not shipped), an optional effort setting for the bridge, refusal '
  'handling (looked at, not implemented: the bridge reads no field that marks a refusal), the scope, reason and '
  'removal of accumulated cautions (the constraints_note advice), the condition for finishing work, and reports '
  "written for a reader who was not in the session. The guide's figures were measured on coding tasks and are not "
  'evidence or results for this plugin. '+NO_COPY,
  ((RELEASE,FABLE,ON_LINE),
   (HARDENING,'(read 2026-11-12). The engine does not check them',LINE_BEFORE),
   (HARDENING,'(read 2026-11-12). Before shipping, three wordings were tried',LINE_BEFORE))),
 ('url:'+SKILLS,'article','Extend Claude with skills',SKILLS,None,[],[],[],
  FIRST+' Used for what the page says about shell commands that a command or skill body injects (!`…` and ```! '
  'blocks), $ARGUMENTS substitution, allowed-tools, the permission-rule check of injected commands and '
  'disableSkillShellExecution: in the design of the optional /aside-repl procedure command, which injects no shell '
  'command, and in SECURITY.md, which keeps the documented behaviour apart from the plugin\'s own observation '
  '(Claude Code 2.1.252 in print mode, one run per case) that injected commands did not reach a PreToolUse hook. '
  'SECURITY.md records that the page does not mention hooks, so that observation is not a statement of the page; '
  'its row cites the sentence that reports what the documentation says, as that file does not repeat the address. '+NO_COPY,
  ((RELEASE,SKILLS,ON_LINE),
   (SECURITY,'`$ARGUMENTS` expands to the argument string as typed',NOT_IN_FILE))),
)
NEW_IDS={row[0] for row in REFERENCES}
NEW_CITATIONS=sum(len(row[9]) for row in REFERENCES)
BASE={'total':147,'citations':264,'av':206}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
PRIOR_TUPLE=(56,53,5,147,264)
EXPECTED_TUPLE=(56,53,7,149,269)

def url_lines(url,lines):
    """Line numbers (1-based) that name the address, with or without scheme, slash or fragment."""
    host_path=url.split('://',1)[1].rstrip('/')
    pattern=re.compile(re.escape(host_path)+r'/?(?![A-Za-z0-9_./-])')
    return [i+1 for i,text in enumerate(lines) if pattern.search(text)]

def excerpt_of(text):
    return text.strip()[:220]

def cited_rows(cites,read_lines,commit,url):
    rows=[];covered=set()
    for file,needle,position in cites:
        lines=read_lines(file);matches=[i+1 for i,text in enumerate(lines) if needle in text]
        if len(matches)!=1:raise ValueError(f'New citation needs one exact line: {file}: {needle} ({len(matches)} lines)')
        line=matches[0];excerpt=excerpt_of(lines[line-1])
        if sum(excerpt_of(text)==excerpt for text in lines)!=1:raise ValueError(f'New citation excerpt is not unique in its file: {file}#L{line}')
        named=set(url_lines(url,lines))
        if position is NOT_IN_FILE:
            if named:raise ValueError(f'{file} now names {url}; anchor its row on that line: {file}#L{min(named)}')
        elif line+position not in named:
            raise ValueError(f'The address is not where the row expects it: {file}#L{line} (offset {position})')
        else:covered.add((file,line+position))
        rows.append({'file':file,'line':line,'url':f'{PREFIX}{commit}/{file}#L{line}','excerpt':excerpt})
    return rows,covered

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

def prepare_update(registry,artwork,read_lines,commit,*,url_index,updated_at=None):
    """url_index(url) -> {file: [line, ...]} of every line in the plugin revision that names the address."""
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Exact lowercase 40-character commit required')
    before=merge_sources(registry['sources']);validate_catalog({**registry,'sources':before})
    version=registry['snapshots']['agentic-vault']['version']
    present=NEW_IDS&{s['id'] for s in registry['sources']}
    if version==PRIOR_TAG:
        if present or metrics(before)['total']!=BASE['total'] or metrics(before)['citations']!=BASE['citations'] or av_rows(registry)!=BASE['av']:
            raise ValueError('Expected the published v0.46.0 baseline of 147 sources and 264 citations (206 agentic-vault)')
    elif version==TAG:
        if present!=NEW_IDS:raise ValueError('A partial v0.47.0 update needs review')
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
    added=[];occurrences={}
    for identity,kind,title,url,year,extra,aliases,tags,note,cites in REFERENCES:
        evidence,covered=cited_rows(cites,read_lines,commit,url)
        if evidence[0]['file']!=RELEASE:raise ValueError('New reference lacks exact release citation: '+identity)
        named={(file,line) for file,lines in url_index(url).items() for line in lines}
        if named!=covered:
            raise ValueError(f'Every line that names {url} needs its own row; uncovered: '
                             +', '.join(f'{f}#L{n}' for f,n in sorted(named-covered))
                             +'; expected but absent: '+', '.join(f'{f}#L{n}' for f,n in sorted(covered-named)))
        occurrences[url]=[f'{f}#L{n}' for f,n in sorted(named)]
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
    if NEW_IDS&{a['sourceId'] for a in images['assets']}:raise ValueError('Uncommissioned v0.47.0 sources must use text fallback')
    return revised,images,{'priorAgenticVaultCitationsRepinned':count-(0 if version==PRIOR_TAG else NEW_CITATIONS),
        'repinnedRowsTotal':count,'remappedLines':moved,'addedSourceIds':added,'newCitationRows':NEW_CITATIONS,
        'citedAddressLines':occurrences,'counts':counts,'agenticVaultCounts':av,'coverageTuple':list(tuple_now),
        'artworkCount':images['count'],'uncommissionedSourceIds':sorted(NEW_IDS),'snapshot':revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot':registry['snapshots']['semantic-crosscheck']}

# Test expectations: exact, guarded, idempotent text edits. They leave every text that the v0.46.0
# helper's edits produced in place, so tests/test_av046_update.py keeps passing on the edited files.
def _tuple(values):return '('+','.join(str(v) for v in values)+')'
_FALLBACK_IDS=''.join(f"  '{identity}'{',' if index<len(REFERENCES)-1 else ''}\n" for index,identity in enumerate(row[0] for row in REFERENCES))
TEST_EDITS=(
 ('tests/test_delivery.py',
  f"    ('{PRIOR_TAG}','v0.21.1'):{_tuple(PRIOR_TUPLE)},\n",
  f"    ('{PRIOR_TAG}','v0.21.1'):{_tuple(PRIOR_TUPLE)},\n    ('{TAG}','v0.21.1'):{_tuple(EXPECTED_TUPLE)},\n"),
 ('tests/test_delivery.py',
  "    def test_public_data_has_no_local_paths_or_credentials(self):\n",
  "    def test_v047_coverage_adds_the_release_cited_cards_without_rewriting_history(self):\n"
  f"        prior=EXPECTED_COVERAGE[('{PRIOR_TAG}','v0.21.1')]\n"
  f"        self.assertEqual(prior,{_tuple(PRIOR_TUPLE)})\n"
  f"        revised=EXPECTED_COVERAGE[('{TAG}','v0.21.1')]\n"
  f"        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),{_tuple(b-a for a,b in zip(PRIOR_TUPLE,EXPECTED_TUPLE))})\n\n"
  "    def test_public_data_has_no_local_paths_or_credentials(self):\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  'url:https://www.unicode.org/reports/tr15/tr15-58.html','url:https://yaml.org/spec/1.2.2'\n]);\n",
  "  'url:https://www.unicode.org/reports/tr15/tr15-58.html','url:https://yaml.org/spec/1.2.2'\n]);\n"
  "const av047TextFallbacks=new Set([\n  ...av046TextFallbacks,\n"+_FALLBACK_IDS+"]);\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "'v0.45.1','v0.46.0'].includes(catalog.snapshots['agentic-vault'].version)){\n",
  "'v0.45.1','v0.46.0'].includes(catalog.snapshots['agentic-vault'].version)\n"
  "      ||catalog.snapshots['agentic-vault'].version==='v0.47.0'){\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "assert.ok(expectedFallbacks.has(source.id),",
  "assert.ok((avVersion==='v0.47.0' ? av047TextFallbacks : expectedFallbacks).has(source.id),"),
 ('tests/artwork-uniqueness.test.mjs',
  "  else assert.deepEqual(fallbacks,[]);\n",
  "  else if(avVersion==='v0.47.0') assert.deepEqual(new Set(fallbacks),av047TextFallbacks);\n"
  "  else assert.deepEqual(fallbacks,[]);\n"),
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
        if asset['sourceId'] in seen or not re.fullmatch(r'media/cards/card-[0-9]{3}\.webp',asset['output']):
            raise ValueError('Unsafe or duplicate artwork assignment')
        seen.add(asset['sourceId']);path=Path(atlas_root)/asset['output']
        if path.is_symlink() or not path.is_file():raise ValueError('Missing or indirect artwork file')
        raw=path.read_bytes()
        if len(raw)!=asset['bytes'] or hashlib.sha256(raw).hexdigest()!=asset['sha256']:raise ValueError('Artwork bytes differ from manifest')
    return hashlib.sha256(json.dumps(immutable_artwork(artwork),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plugin-root',type=Path,required=True,help='Local clone of the public agentic-vault repository')
    p.add_argument('--commit',required=True,help='Exact public commit that the v0.47.0 tag names')
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
        if git('cat-file','-t','refs/tags/'+TAG).strip()!='tag':raise ValueError('Annotated v0.47.0 tag required')
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
        host_path=url.split('://',1)[1].rstrip('/')
        found=subprocess.run(['git','-C',str(args.plugin_root),'grep','-l','-I','-F','-e',host_path,rev,'--'],
                             stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        if found.returncode not in (0,1):raise ValueError('git grep failed with exit '+str(found.returncode))
        files=[line[len(rev)+1:] for line in found.stdout.decode('utf-8').splitlines() if line.startswith(rev+':')]
        return {file:url_lines(url,read_lines(file)) for file in files if url_lines(url,read_lines(file))}
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
