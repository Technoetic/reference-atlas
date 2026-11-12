"""Offline, dry-run-first agentic-vault v0.46.0 citation update from exact Git blobs.

Adds three format cards that the v0.46.0 release note cites (Unicode Standard
18.0.0 chapter 3 D145, UAX #15 revision 58, YAML 1.2.2) and repins every
existing agentic-vault citation to the supplied commit, because the catalog
schema binds each citation of a plugin to that plugin's declared snapshot.
Existing notes, roles, semantic-crosscheck uses and artwork identities stay as
they are; only the commit, and a line number where the source moved, change.
New cards use the text fallback; no image, prompt or UI is created or changed.

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
TAG='v0.46.0'
PRIOR_TAG='v0.45.1'
RELEASE='docs/releases/v0.46.0.md'
CONTRACT='docs/verification/v0.46.0.md'
ZONE_TEST='tests/test_zone_normalization.py'
PATHS='skills/agentic-vault/scripts/vault_paths.py'

CH3='https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/'
UAX15='https://www.unicode.org/reports/tr15/tr15-58.html'
UAX15_LATEST='https://www.unicode.org/reports/tr15/'
YAML122='https://yaml.org/spec/1.2.2/'
NO_COPY='Definitions only; no code, data or text is copied.'
FIRST=('No earlier agentic-vault or semantic-crosscheck use of this source is recorded in this catalog; '
       'the v0.46.0 release note says the catalog did not list it and that this release adds it.')

# id, kind, title, url, year, extra strong keys, aliases, tags, note,
# ((file, text that must appear on exactly one line), ...). The release citation comes first.
REFERENCES=(
 ('url:'+CH3.rstrip('/'),'format','The Unicode Standard, Version 18.0.0, Core Specification, Chapter 3: Conformance',CH3,2026,[],
  ['Unicode Standard chapter 3','Default Caseless Matching','canonical caseless match','Unicode D145'],['보안·안전'],
  FIRST+' Fix F1 of agentic-vault v0.46.0 defines the deny-zone fold (fold_path_part in '+PATHS+') by definition D145, '
  'canonical caseless matching: NFD(toCasefold(NFD(X))) = NFD(toCasefold(NFD(Y))). The code applies it with the running '
  "Python's own Unicode data, so version 18.0.0 names the text of the definition, not the character data. "
  'Difference from earlier plugin text comparisons: those compare note text with NFKC and casefold; path names here '
  'use canonical decomposition only, never compatibility (NFKC) decomposition. '+NO_COPY,
  ((RELEASE,CH3),(CONTRACT,'Standard 18.0.0 chapter 3 (D145)'),(ZONE_TEST,'Unicode D145'),
   (PATHS,'canonical caseless matches (NFD, casefold, NFD)'))),
 ('url:'+UAX15,'format','Unicode Standard Annex #15: Unicode Normalization Forms',UAX15,2026,['url:'+UAX15_LATEST.rstrip('/')],
  ['UAX #15','Unicode Normalization Forms','Unicode Standard Annex #15'],['보안·안전'],
  FIRST+' Pinned at revision 58 (Unicode 18.0.0, 2026-08-12); the unversioned annex address that revision names as its '
  'latest version is kept as a second key, as arXiv versions share one card. Fix F1 of agentic-vault v0.46.0 uses its '
  'NFD and NFC forms: the fold returns NFC, which is one-to-one on NFD strings, so equal folds mean canonical caseless '
  'matches. Difference from earlier NFKC (compatibility) uses in the plugin: only canonical normalization is used here. '+NO_COPY,
  ((RELEASE,UAX15),(CONTRACT,'UAX #15 revision 58'))),
 ('url:'+YAML122.rstrip('/'),'format',"YAML Ain't Markup Language (YAML) version 1.2, Revision 1.2.2",YAML122,2021,[],
  ['YAML 1.2.2','YAML specification 1.2.2'],['신뢰성'],
  FIRST+' Revision 1.2.2 of 2021-10-01. Fix F2 of agentic-vault v0.46.0 takes from it which front-matter shapes a YAML '
  'reader loads as a nested list (flow sequences, block scalars, quoted scalars) for the unquoted wiki-link check. '
  'The check is a small line scanner written for the plugin, not a YAML parser; the earlier check matched one regular '
  'expression per line without YAML context. PyYAML and ruamel.yaml served only as offline development comparisons '
  'and are not recorded here. '+NO_COPY,
  ((RELEASE,YAML122),(CONTRACT,'YAML 1.2.2'))),
)
NEW_IDS={row[0] for row in REFERENCES}
NEW_CITATIONS=sum(len(row[9]) for row in REFERENCES)
BASE={'total':144,'citations':256,'av':198}
# Coverage tuple of tests/test_delivery.py: AV paper, AV project+format, AV article, total sources, citations.
EXPECTED_TUPLE=(56,53,5,147,264)

def cited_rows(cites,read_lines,commit):
    rows=[]
    for file,needle in cites:
        lines=read_lines(file);matches=[i+1 for i,text in enumerate(lines) if needle in text]
        if len(matches)!=1:raise ValueError(f'New citation needs one exact line: {file}: {needle}')
        line=matches[0]
        rows.append({'file':file,'line':line,'url':f'{PREFIX}{commit}/{file}#L{line}','excerpt':lines[line-1].strip()[:220]})
    return rows

def immutable_artwork(artwork):
    return [{k:v for k,v in asset.items() if k not in {'evidenceUrls','currentEvidenceUrls'}} for asset in artwork['assets']]

def av_rows(registry):
    return sum(len(use['evidence']) for s in registry['sources'] for use in s['uses'] if use['plugin']=='agentic-vault')

def prepare_update(registry,artwork,read_lines,commit,*,updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Exact lowercase 40-character commit required')
    before=merge_sources(registry['sources']);validate_catalog({**registry,'sources':before})
    version=registry['snapshots']['agentic-vault']['version']
    present=NEW_IDS&{s['id'] for s in registry['sources']}
    if version==PRIOR_TAG:
        if present or metrics(before)['total']!=BASE['total'] or metrics(before)['citations']!=BASE['citations'] or av_rows(registry)!=BASE['av']:
            raise ValueError('Expected the published v0.45.1 baseline of 144 sources and 256 citations (198 agentic-vault)')
    elif version==TAG:
        if present!=NEW_IDS:raise ValueError('A partial v0.46.0 update needs review')
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
    old_shape=[(s['id'],s.get('note'),s['keys'],s['aliases'],[(u['plugin'],u['role'],[(r['file'],r['excerpt']) for r in u['evidence']]) for u in s['uses']])
               for s in registry['sources']]
    remapped={};count=moved=0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin']!='agentic-vault':continue
            for row in use['evidence']:
                lines=read_lines(row['file']);old_line,old_url=row['line'],row['url']
                if old_line<=len(lines) and lines[old_line-1].strip()[:220]==row['excerpt']:line=old_line
                else:
                    matches=[i+1 for i,text in enumerate(lines) if text.strip()[:220]==row['excerpt']]
                    if len(matches)!=1:raise ValueError('Prior excerpt needs a unique exact match: '+source['id']+' / '+row['file'])
                    line=matches[0]
                row.update(line=line,url=f'{PREFIX}{commit}/{row["file"]}#L{line}')
                if old_url in remapped and remapped[old_url]!=row['url']:raise ValueError('Ambiguous old citation map')
                remapped[old_url]=row['url'];count+=1;moved+=line!=old_line
    added=[]
    for identity,kind,title,url,year,extra,aliases,tags,note,cites in REFERENCES:
        evidence=cited_rows(cites,read_lines,commit)
        if evidence[0]['file']!=RELEASE:raise ValueError('New reference lacks exact release citation: '+identity)
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
    # Existing records keep notes, keys, aliases, roles, files and excerpts; only commit/line move.
    new_shape=[(s['id'],s.get('note'),s['keys'],s['aliases'],[(u['plugin'],u['role'],[(r['file'],r['excerpt']) for r in u['evidence']]) for u in s['uses']])
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
    if NEW_IDS&{a['sourceId'] for a in images['assets']}:raise ValueError('Uncommissioned v0.46.0 sources must use text fallback')
    return revised,images,{'priorAgenticVaultCitationsRepinned':count-(0 if version==PRIOR_TAG else NEW_CITATIONS),
        'repinnedRowsTotal':count,'remappedLines':moved,'addedSourceIds':added,'newCitationRows':NEW_CITATIONS,
        'counts':counts,'agenticVaultCounts':av,'coverageTuple':list(tuple_now),'artworkCount':images['count'],
        'uncommissionedSourceIds':sorted(NEW_IDS),'snapshot':revised['snapshots']['agentic-vault'],
        'unchangedSemanticCrosscheckSnapshot':registry['snapshots']['semantic-crosscheck']}

# Test expectations: exact, guarded, idempotent text edits (the previous releases made the same kind by hand).
TEST_EDITS=(
 ('tests/test_delivery.py',
  "    ('v0.45.1','v0.21.1'):(56,50,5,144,256),\n",
  "    ('v0.45.1','v0.21.1'):(56,50,5,144,256),\n    ('v0.46.0','v0.21.1'):(56,53,5,147,264),\n"),
 ('tests/test_delivery.py',
  "    def test_every_source_has_public_commit_bound_evidence(self):\n",
  "    def test_v046_coverage_adds_three_format_cards_and_eight_citations_without_rewriting_history(self):\n"
  "        prior=EXPECTED_COVERAGE[('v0.45.1','v0.21.1')]\n"
  "        self.assertEqual(prior,(56,50,5,144,256))\n"
  "        revised=EXPECTED_COVERAGE[('v0.46.0','v0.21.1')]\n"
  "        self.assertEqual(tuple(new-old for old,new in zip(prior,revised)),(0,3,0,3,8))\n\n"
  "    def test_every_source_has_public_commit_bound_evidence(self):\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  'arxiv:2502.05167','arxiv:2404.06654','arxiv:2411.06037','github:nvidia/ruler'\n]);\n",
  "  'arxiv:2502.05167','arxiv:2404.06654','arxiv:2411.06037','github:nvidia/ruler'\n]);\n"
  "const av046TextFallbacks=new Set([\n  ...av045TextFallbacks,\n"
  "  'url:https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3',\n"
  "  'url:https://www.unicode.org/reports/tr15/tr15-58.html','url:https://yaml.org/spec/1.2.2'\n]);\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "['v0.41.0','v0.42.0','v0.43.0','v0.44.0','v0.45.0','v0.45.1'].includes",
  "['v0.41.0','v0.42.0','v0.43.0','v0.44.0','v0.45.0','v0.45.1','v0.46.0'].includes"),
 ('tests/artwork-uniqueness.test.mjs',
  "  const expectedFallbacks=['v0.45.0','v0.45.1'].includes(catalog.snapshots['agentic-vault'].version)\n    ? av045TextFallbacks : av044TextFallbacks;\n",
  "  const avVersion=catalog.snapshots['agentic-vault'].version;\n"
  "  const expectedFallbacks=avVersion==='v0.46.0' ? av046TextFallbacks\n"
  "    : ['v0.45.0','v0.45.1'].includes(avVersion) ? av045TextFallbacks : av044TextFallbacks;\n"),
 ('tests/artwork-uniqueness.test.mjs',
  "  if(['v0.44.0','v0.45.0','v0.45.1'].includes(catalog.snapshots['agentic-vault'].version))\n",
  "  if(['v0.44.0','v0.45.0','v0.45.1','v0.46.0'].includes(catalog.snapshots['agentic-vault'].version))\n"),
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
    p.add_argument('--commit',required=True,help='Exact public commit that the v0.46.0 tag names')
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
        if git('cat-file','-t','refs/tags/'+TAG).strip()!='tag':raise ValueError('Annotated v0.46.0 tag required')
        if git('rev-parse','refs/tags/'+TAG+'^{commit}').strip()!=args.commit:raise ValueError('Tag source differs from --commit')
    rev=args.content_rev or args.commit
    cache={}
    def read_lines(file):
        # Split on newlines only so line numbers match the GitHub blob view.
        if file not in cache:cache[file]=git('show',rev+':'+file).split('\n')
        return cache[file]
    root=args.atlas_root.resolve()
    source=root/'data/registry.source.json';art=root/'docs/card-artwork-unique-prompts.json'
    before={path:path.read_bytes() for path in (source,art)}
    registry=json.loads(before[source].decode('utf-8'));artwork=json.loads(before[art].decode('utf-8'))
    bindings=verify_images(root,artwork)
    revised,images,summary=prepare_update(registry,artwork,read_lines,args.commit)
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
