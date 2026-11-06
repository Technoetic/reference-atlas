"""Offline, dry-run-first v0.42.0 citation preparation from exact tagged Git blobs.

No fetch/publication/plugin mutation. Caller independently verifies public tag
and source availability before --apply. Uncommissioned sources use text fallback.
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

ROOT=Path(__file__).resolve().parents[1]
PREFIX='https://github.com/Technoetic/agentic-vault/blob/'
TAG='v0.42.0'
FILES=('docs/releases/v0.42.0.md','docs/recoverable-bundles.md',
       'docs/review-planning.md','docs/generated-memory-lifecycle.md')
REFERENCES=(
 ('url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai','paper',
  'All File Systems Are Not Created Equal: On the Complexity of Crafting Crash-Consistent Applications',
  'https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai',2014,[],
  'Application-level interrupted-operation reasoning informs cooperating Markdown journal recovery; not filesystem-wide atomicity or reproduced crash-consistency results.'),
 ('github:madthanu/alice','project','ALICE',
  'https://github.com/madthanu/alice/tree/6afda210b96baa2b0b277505d72742420ba89b68',None,['madthanu/alice'],
  'Pinned legacy Linux/Python 2 conceptual reference for interrupted-operation recovery; no implementation or dependency copied.'),
 ('github:treeverse/dvc','project','DVC',
  'https://github.com/treeverse/dvc/tree/1c06f9860af61d3947adafac99d8206f713dbfdd',None,['iterative/dvc','treeverse/dvc'],
  'Already researched generally in VCS notes; new Agentic Vault application is an explicit data-only transitive review worklist over declared dependencies, not a newly discovered project or computational/cache execution. Former iterative/dvc is the same repository (GitHub ID 83878269). No code copied.'),
 ('arxiv:2407.12784','paper','AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases',
  'https://arxiv.org/abs/2407.12784',2024,['AgentPoison paper'],
  'Conceptual poisoned-persistent-memory reference for disposable synthetic checksum experiments. No copied dataset, embedding optimization, published attack rates or robustness reproduction.'),
 ('github:ai-secure/agentpoison','project','AgentPoison',
  'https://github.com/AI-secure/AgentPoison/tree/7b02e28f5e477052bd16c778fef7c1f78f7c9d7c',None,['AI-secure/AgentPoison'],
  'Pinned conceptual implementation reference only; no upstream code/dataset, embedding optimizer or published rate adoption. Scripted control is not a real model result.'),
)
NEW_IDS={row[0] for row in REFERENCES}

def prepare_update(registry,artwork,read_lines,commit,tag,*,updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}',commit) or tag!=TAG:
        raise ValueError('Expected exact lowercase commit and v0.42.0 tag')
    validate_catalog({**registry,'sources':merge_sources(registry['sources'])})
    revised,images=deepcopy(registry),deepcopy(artwork)
    # A renamed repo is one identity; do not silently create a second card.
    for source in revised['sources']:
        if 'github:iterative/dvc' in source.get('keys',[]) and source['id']!='github:treeverse/dvc':
            raise ValueError('Existing former DVC identity needs explicit reviewed merge')
    remapped={};count=moved=0
    for source in revised['sources']:
        for use in source['uses']:
            if use['plugin']!='agentic-vault':continue
            for row in use['evidence']:
                lines=read_lines(row['file']);old_line=row['line'];old_url=row['url']
                if old_line<=len(lines) and lines[old_line-1].strip()[:220]==row['excerpt']:line=old_line
                else:
                    matches=[i+1 for i,text in enumerate(lines) if text.strip()[:220]==row['excerpt']]
                    if len(matches)!=1:raise ValueError('Prior excerpt needs a unique exact match: '+row['file'])
                    line=matches[0]
                row.update(line=line,url=f'{PREFIX}{commit}/{row["file"]}#L{line}')
                if old_url in remapped and remapped[old_url]!=row['url']:raise ValueError('Ambiguous old citation map')
                remapped[old_url]=row['url'];count+=1;moved+=line!=old_line
    added=[]
    for identity,kind,title,url,year,aliases,note in REFERENCES:
        evidence=[]
        for file in FILES:
            lines=read_lines(file);matches=[i+1 for i,line in enumerate(lines) if url in line]
            if len(matches)>1:raise ValueError('New citation URL is ambiguous: '+file)
            if matches:
                line=matches[0];evidence.append({'file':file,'line':line,
                    'url':f'{PREFIX}{commit}/{file}#L{line}','excerpt':lines[line-1].strip()[:220]})
        if not evidence or not any(r['file']==FILES[0] for r in evidence):
            raise ValueError('New reference lacks exact release citation: '+identity)
        prior=next((s for s in revised['sources'] if s['id']==identity),None)
        if prior:
            existing=next((u for u in prior['uses'] if u['plugin']=='agentic-vault'),None)
            if not existing:prior['uses'].append({'plugin':'agentic-vault','role':'reference','evidence':evidence})
            elif existing['evidence']!=evidence:raise ValueError('Existing new-reference use differs; manual review required')
        else:
            keys=[identity]+(['github:iterative/dvc'] if identity=='github:treeverse/dvc' else [])
            canonical=url.split('/tree/')[0]
            revised['sources'].append({'id':identity,'kind':kind,'title':title,'url':canonical,'year':year,
                'keys':keys,'aliases':aliases,'tags':[], 'note':note,
                'uses':[{'plugin':'agentic-vault','role':'reference','evidence':evidence}]})
            added.append(identity)
    revised['snapshots']['agentic-vault']={'name':'Agentic Vault','version':tag,'commit':commit,
        'url':f'https://github.com/Technoetic/agentic-vault/tree/{commit}'}
    revised['updatedAt']=updated_at or datetime.now(timezone.utc).isoformat()
    merged=merge_sources(revised['sources']);validate_catalog({**revised,'sources':merged})
    # Never add or mutate image/prompt/generation records for uncommissioned art.
    for asset in images['assets']:
        for field in ('evidenceUrls','currentEvidenceUrls'):
            if field not in asset:raise ValueError('Existing artwork current evidence field missing')
            urls=[]
            for url in asset[field]:
                if url.startswith(PREFIX) and url not in remapped:raise ValueError('Artwork URL not in prior citation map')
                urls.append(remapped.get(url,url))
            asset[field]=urls
    if len(images['assets'])!=artwork['count']:raise ValueError('Artwork count mismatch')
    return revised,images,{'priorAgenticVaultCitations':count,'remappedLines':moved,
        'addedSourceIds':added,'counts':metrics(merged),'artworkCount':len(images['assets']),
        'uncommissionedSourceIds':sorted(NEW_IDS-{a['sourceId'] for a in images['assets']}),
        'snapshot':revised['snapshots']['agentic-vault']}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plugin-root',type=Path,required=True)
    p.add_argument('--commit',required=True);p.add_argument('--tag',choices=[TAG],required=True)
    p.add_argument('--apply',action='store_true');args=p.parse_args(argv)
    if not re.fullmatch('[0-9a-f]{40}',args.commit):p.error('exact full commit required')
    def git(*parts):return subprocess.check_output(['git','-C',str(args.plugin_root),*parts]).decode('utf-8')
    if git('cat-file','-t','refs/tags/'+TAG).strip()!='tag':raise ValueError('Annotated release tag required')
    if git('rev-parse','refs/tags/'+TAG+'^{commit}').strip()!=args.commit:raise ValueError('Tag source differs')
    cache={}
    def read_lines(file):
        if file not in cache:cache[file]=git('show',args.commit+':'+file).splitlines()
        return cache[file]
    source=ROOT/'data/registry.source.json';art=ROOT/'docs/card-artwork-unique-prompts.json'
    revised,images,summary=prepare_update(json.loads(source.read_text(encoding='utf-8')),
        json.loads(art.read_text(encoding='utf-8')),read_lines,args.commit,args.tag)
    if args.apply:write_update([(source,revised),(art,images)])
    print(json.dumps({'status':'PASS','mode':'applied' if args.apply else 'dry-run',
        'publicAvailability':'caller must independently verify before apply',**summary}))
    return 0
if __name__=='__main__':raise SystemExit(main())
