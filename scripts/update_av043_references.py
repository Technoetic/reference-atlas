"""Offline, dry-run-first v0.43.0 citation preparation from exact tagged Git blobs.

No fetch/publication/plugin mutation. Caller independently verifies public tag
and source availability before --apply. Uncommissioned sources use text fallback.
Sources the release calls prior use but this registry never recorded still need
a card; their notes keep the prior-use statement instead of claiming a discovery.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from build_catalog import merge_sources, metrics
from reference_identity import canonical_key, validate_catalog
from update_ontology_references import write_update

ROOT=Path(__file__).resolve().parents[1]
PREFIX='https://github.com/Technoetic/agentic-vault/blob/'
TAG='v0.43.0'
RELEASE='docs/releases/v0.43.0.md'
HANDOFF='docs/handoff-fold.md'
RECALL='docs/recall-scope.md'
CAPACITY='docs/capacity.md'
RECURRENCE='docs/lesson-recurrence.md'
FIDELITY='docs/verifier-fidelity.md'
HARDENING='docs/hardening.md'
COMMITS='docs/concurrent-commits.md'
RELIABILITY='docs/reliability.md'
CUES='assets/adapters/lesson-cues/guide.md'
GUARD='assets/adapters/deny-guard/guide.md'

LCM='https://papers.voltropy.com/LCM'
FACTORY='https://factory.com/news/evaluating-compression'
REPROTEST='https://manpages.debian.org/unstable/reprotest/reprotest.1.en.html'
WORKTREES='https://code.claude.com/docs/en/worktrees'
HOOKS='code.claude.com/docs/en/hooks'
PLUGIN_CLI='https://code.claude.com/docs/en/plugins/cli-reference'
GIT_DOCS='https://git-scm.com/docs/'
NO_COPY='Concepts only; no code or data copied.'
PRIOR='The v0.43.0 release lists this under prior use, so it is not a new discovery; this is its first card here.'

# id, kind, title, canonical url, year, extra strong keys, aliases, role, prior use, note,
# ((file, exact text that must appear on one line), ...). The release citation comes first.
REFERENCES=(
 ('url:'+LCM,'paper','LCM: Lossless Context Management',LCM,2026,[],['LCM'],'reference',False,
  'PDF generated 2026-02-14. Summaries as a derived cache, a threshold below which nothing runs and a deterministic fallback inform the handoff fold. LCM leaves its source untouched; this tool moves bytes. '+NO_COPY,
  ((RELEASE,LCM),(HANDOFF,LCM))),
 ('github:martian-engineering/lossless-claw','project','lossless-claw','https://github.com/Martian-Engineering/lossless-claw',None,[],
  ['Martian-Engineering/lossless-claw'],'reference',False,
  'Pinned at v1.2.0 (MIT) beside the LCM paper for the same handoff-fold concepts. '+NO_COPY,
  ((RELEASE,'https://github.com/Martian-Engineering/lossless-claw/tree/v1.2.0'),(HANDOFF,'https://github.com/Martian-Engineering/lossless-claw'))),
 ('url:'+FACTORY,'article','Evaluating Context Compression for AI Agents',FACTORY,2025,[],[],'reference',False,
  'Published 2025-12-16. Probe kinds for the offline handoff-fold evaluator. This is a vendor post on its own product and it scores model answers, which the offline evaluator does not. '+NO_COPY,
  ((RELEASE,FACTORY),(HANDOFF,FACTORY))),
 ('github:sourcegraph/sourcegraph-public-snapshot','project','Sourcegraph public snapshot','https://github.com/sourcegraph/sourcegraph-public-snapshot',None,[],
  ['Sourcegraph Skipped','sourcegraph/sourcegraph-public-snapshot'],'reference',False,
  'Archived snapshot with no clear license, pinned at c864f15af264f0f456a6d8a83290b5c940715349. Structure only: the Skipped type separates "not searched" from "searched and absent" for recall scope reports. '+NO_COPY,
  ((RELEASE,'https://github.com/sourcegraph/sourcegraph-public-snapshot/blob/c864f15af264f0f456a6d8a83290b5c940715349/'),(RECALL,'https://github.com/sourcegraph/sourcegraph-public-snapshot/blob/c864f15af264'))),
 ('github:sourcegraph/zoekt','project','Zoekt','https://github.com/sourcegraph/zoekt',None,[],['sourcegraph/zoekt'],'reference',False,
  'Stats pinned at a5a933bc043e (Apache-2.0): separating "not searched" from "searched and absent". '+NO_COPY,
  ((RELEASE,'https://github.com/sourcegraph/zoekt/blob/a5a933bc043e/api.go'),(RECALL,'https://github.com/sourcegraph/zoekt/blob/a5a933bc043e/api.go'))),
 ('github:prometheus/prometheus','project','Prometheus','https://github.com/prometheus/prometheus',None,[],['predict_linear','prometheus/prometheus'],'reference',False,
  'predict_linear pinned at dd7aa6b0f19f (Apache-2.0): the shape of a linear estimate. '+NO_COPY,
  ((RELEASE,'https://github.com/prometheus/prometheus/blob/dd7aa6b0f19f'),(CAPACITY,'https://github.com/prometheus/prometheus/blob/dd7aa6b0f19f'))),
 ('github:phenomnomnominal/betterer','project','Betterer','https://github.com/phenomnomnominal/betterer',None,[],['phenomnomnominal/betterer'],'reference',False,
  'Pinned at 69a83c14975b (MIT): a check that fails only on getting worse. Here HEAD is the baseline and there is no result file. '+NO_COPY,
  ((RELEASE,'https://github.com/phenomnomnominal/betterer/tree/69a83c14975b'),(CAPACITY,'https://github.com/phenomnomnominal/betterer'))),
 ('github:logpai/drain3','project','Drain3','https://github.com/logpai/Drain3',None,[],['logpai/Drain3'],'background',False,
  'Pinned at v0.9.11, commit 78d3cae4bcac329c4e4f275d416562e10c5c446e. Weighed and rejected: masking would remove the entry numbers that carry the best signal. Nothing was taken.',
  ((RELEASE,'https://github.com/logpai/Drain3/tree/78d3cae4bcac'),(RECURRENCE,'https://github.com/logpai/Drain3'),(CUES,'https://github.com/logpai/Drain3'))),
 ('arxiv:2607.19865','paper','DocOps: A Verifiable Benchmark for Autonomous Agents in Complex Document Operations','https://arxiv.org/abs/2607.19865',2026,[],['DocOps'],'reference',False,
  'v1: the mutation evaluation design. Its figures belong to task-specific checkers and are not comparable, and its human audit has no counterpart here. '+NO_COPY,
  ((RELEASE,'https://arxiv.org/abs/2607.19865'),(FIDELITY,'https://arxiv.org/abs/2607.19865'))),
 ('url:'+REPROTEST,'project','reprotest',REPROTEST,None,[],['reprotest 0.7.33 manual'],'reference',False,
  'Manual for 0.7.33: the control, variation and blame order. Its code is GPL and none of it is used. New here is the order of runs, with shuffled cumulative blame; the encoding CI leg itself is not new.',
  ((RELEASE,REPROTEST),(FIDELITY,REPROTEST))),
 ('arxiv:2610.30571','paper','Stale Instruction Files Override the Code in Coding Agents: A One-Sentence Fix','https://arxiv.org/abs/2610.30571',2026,[],['Stale Instruction Files Override the Code'],'reference',False,
  'v1: follow what was observed and report each inconsistency. Applying this to factual statements in a project rule file is the plugin\'s extension, which the study does not measure. '+NO_COPY,
  ((RELEASE,'https://arxiv.org/abs/2610.30571'),(HARDENING,'https://arxiv.org/abs/2610.30571'))),
 ('github:wenjing95/stale-docs-data','project','stale-docs-data','https://github.com/WenJing95/stale-docs-data',None,[],['WenJing95/stale-docs-data'],'reference',False,
  'Data repository of the stale instruction file study, pinned at fa3c8b8. '+NO_COPY,
  ((RELEASE,'https://github.com/WenJing95/stale-docs-data/tree/fa3c8b8'),(HARDENING,'https://github.com/WenJing95/stale-docs-data/blob/fa3c8b8/'))),
 ('arxiv:2610.31778','paper','Benchmarks Are Surprisingly Compaction-Friendly','https://arxiv.org/abs/2610.31778',2026,[],[],'reference',False,
  'v1, abstract only: constraints that exist nowhere else are the ones lost. The same abstract finds no method better than default self-summarization, so it is not evidence that re-injecting text improves results.',
  ((RELEASE,'https://arxiv.org/abs/2610.31778'),(HARDENING,'https://arxiv.org/abs/2610.31778'))),
 ('github:manuelschipper/nah','project','nah','https://github.com/manuelschipper/nah',None,[],['manuelschipper/nah'],'background',False,
  'Pinned at v1.7.0 (MIT): another hook at the same layer, mentioned in the deny-guard guide. Nothing was taken from it.',
  ((RELEASE,'https://github.com/manuelschipper/nah/tree/v1.7.0'),(GUARD,'https://github.com/manuelschipper/nah/tree/v1.7.0'))),
 ('url:'+WORKTREES,'article','Claude Code worktrees documentation',WORKTREES,None,[],[],'reference',False,
  'Fetched 2026-11-07: the default location and the facts the worktree guard relies on. The page has no version and may have changed since.',
  ((RELEASE,WORKTREES),(HARDENING,WORKTREES))),
 ('github:python-trio/trio','project','Trio','https://github.com/python-trio/trio',None,[],['MockClock','python-trio/trio'],'reference',False,
  'MockClock at v0.35.0 informs replacing one wall-clock bound in a test with an assertion on event order. Trio is not a dependency and no code was taken.',
  ((RELEASE,'https://github.com/python-trio/trio/blob/v0.35.0/'),)),
 ('github:gastownhall/beads','project','Beads','https://github.com/gastownhall/beads',None,['github:steveyegge/beads'],['gastownhall/beads','steveyegge/beads'],'reference',True,
  PRIOR+' Earlier work consulted hash IDs and ready or claim states. New here at v1.3.4 (MIT) is the bd admin compact sequence of analyze, host summary and apply. Beads discards the original; this tool keeps every byte and folds sections with unresolved lines by lifting those lines. Former steveyegge/beads is the same repository (GitHub ID 1074561042). '+NO_COPY,
  ((RELEASE,'https://github.com/gastownhall/beads/tree/v1.3.4'),(HANDOFF,'https://github.com/gastownhall/beads/blob/v1.3.4/'))),
 ('url:https://'+HOOKS,'article','Claude Code hooks reference','https://'+HOOKS,None,[],[],'reference',True,
  PRIOR+' Read 2026-11-07. Earlier used for the output cap and for deny-guard input and decision fields. New here is where additionalContext lands: the model has already issued the call, so a hint reaches the next decision, not that call. The page has no version and may have changed since.',
  ((RELEASE,HOOKS),(CUES,HOOKS),(GUARD,HOOKS))),
 ('url:'+PLUGIN_CLI,'article','Claude Code plugin CLI reference',PLUGIN_CLI,None,[],[],'reference',True,
  PRIOR+' Referenced before in another context. New here is a report of each value with its scope, and the merged enabled state from the host as a comparison value. The page has no version and may have changed since.',
  ((RELEASE,PLUGIN_CLI),(RELIABILITY,PLUGIN_CLI))),
 ('arxiv:2606.22528','paper','Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents','https://arxiv.org/abs/2606.22528',2026,[],['Governance Decay'],'reference',True,
  PRIOR+' Already read in earlier work. New here is that it motivates the constraint probe kind. '+NO_COPY,
  ((RELEASE,'https://arxiv.org/abs/2606.22528'),)),
 ('arxiv:2607.20972','paper','Delivery, Not Storage: Cue-Anchored Working Memory as a Harness Property for Coding Agents','https://arxiv.org/abs/2607.20972',2026,[],['Delivery, Not Storage'],'reference',True,
  PRIOR+' Earlier work proposed from this paper a cues field of path globs and command prefixes, injected by an opt-in PreToolUse hook within about 1,500 characters, so the cue bundle is not new. New here are the split into hint and guard, the per-call budget and the handling of quoted text. '+NO_COPY,
  ((RELEASE,'https://arxiv.org/abs/2607.20972'),(CUES,'https://arxiv.org/abs/2607.20972'))),
 ('github:joeblackwaslike/lessons-learned','project','lessons-learned','https://github.com/joeblackwaslike/lessons-learned',None,[],['joeblackwaslike/lessons-learned'],'reference',False,
  'Pinned at 3b39f38152fe (MIT), beside a prior-use paper but a new source. It informs the split into hint and guard, the per-call budget and the handling of quoted text. Its budget is larger and its patterns are regular expressions; both differ. '+NO_COPY,
  ((RELEASE,'https://github.com/joeblackwaslike/lessons-learned/tree/3b39f38152fe'),(CUES,'https://github.com/joeblackwaslike/lessons-learned'))),
)
# Existing cards gain uses only. Git manual pages stay on the Git project card so a
# later lookup of those URLs reports the existing record, not an unknown source.
EXISTING=(
 ('github:git/git',['url:'+GIT_DOCS+page for page in ('git-commit','git-update-ref','git-worktree')],
  ['git-commit','git-config','git-update-ref','git-worktree'],
  'The agentic-vault v0.43.0 application adds the git-commit --only, git-worktree and git-update-ref manual pages, as shipped with Git for Windows 2.55.0.windows.3, and git-config.adoc at fb25501. Commands are called; nothing is copied. The git-update-ref old-value check, earlier a design analogy, now guards the actual HEAD update in --own-lines, and git-config informs a report of each value with its scope.',
  ((RELEASE,GIT_DOCS+'git-commit'),(RELEASE,GIT_DOCS+'git-worktree'),(RELEASE,GIT_DOCS+'git-update-ref'),
   (RELEASE,'https://github.com/git/git/blob/fb25501/Documentation/git-config.adoc'),
   (COMMITS,GIT_DOCS+'git-commit'),(COMMITS,GIT_DOCS+'git-update-ref'),
   (RELIABILITY,'https://github.com/git/git/blob/fb25501/Documentation/git-config.adoc'))),
 ('github:python/cpython',[],[],
  'The agentic-vault v0.43.0 application pins Doc/using/windows.rst at cbaba022cf2778c5f02445ae231a8af1f1db53a1 for the cleanup of PYTHON* values that -I ignores in evaluation workers. CPython was already cited for other issues; no code is copied.',
  ((RELEASE,'https://github.com/python/cpython/blob/cbaba022cf2778c5f02445ae231a8af1f1db53a1/Doc/using/windows.rst'),)),
)
NEW_IDS={row[0] for row in REFERENCES}
PRIOR_USE_IDS={row[0] for row in REFERENCES if row[8]}
EXISTING_IDS={row[0] for row in EXISTING}

def cited_rows(cites,read_lines,commit):
    rows=[]
    for file,needle in cites:
        lines=read_lines(file);matches=[i+1 for i,text in enumerate(lines) if needle in text]
        if len(matches)!=1:raise ValueError(f'New citation needs one exact line: {file}: {needle}')
        line=matches[0]
        rows.append({'file':file,'line':line,'url':f'{PREFIX}{commit}/{file}#L{line}','excerpt':lines[line-1].strip()[:220]})
    return rows

def prepare_update(registry,artwork,read_lines,commit,tag,*,updated_at=None):
    if not re.fullmatch('[0-9a-f]{40}',commit) or tag!=TAG:
        raise ValueError('Expected exact lowercase commit and v0.43.0 tag')
    validate_catalog({**registry,'sources':merge_sources(registry['sources'])})
    revised,images=deepcopy(registry),deepcopy(artwork)
    # Each key names one work. A hit under another id needs a reviewed merge, not a second card.
    for row in REFERENCES:
        identity,wanted=row[0],{row[0],*row[5]}
        for source in revised['sources']:
            if source['id']!=identity and wanted&(set(source['keys'])|{source['id']}):
                raise ValueError('Existing source identity needs explicit reviewed merge: '+identity)
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
    added=[];uses_added=0
    for identity,keys,aliases,note,cites in EXISTING:
        found=[s for s in revised['sources'] if s['id']==identity]
        if len(found)!=1:raise ValueError('Existing source record required: '+identity)
        source=found[0]
        use=next((u for u in source['uses'] if u['plugin']=='agentic-vault'),None)
        if not use:raise ValueError('Existing source lacks an agentic-vault use: '+identity)
        for row in cited_rows(cites,read_lines,commit):
            if row['url'] not in {x['url'] for x in use['evidence']}:
                use['evidence'].append(row);uses_added+=1
        source['keys']=[*source['keys'],*(k for k in keys if k not in source['keys'])]
        source['aliases']=[*source['aliases'],*(a for a in aliases if a not in source['aliases'])]
        if note not in source.get('note',''):source['note']=(source.get('note','')+' '+note).strip()
    for identity,kind,title,url,year,extra,aliases,role,_,note,cites in REFERENCES:
        evidence=cited_rows(cites,read_lines,commit)
        if evidence[0]['file']!=RELEASE:raise ValueError('New reference lacks exact release citation: '+identity)
        prior=next((s for s in revised['sources'] if s['id']==identity),None)
        if prior:
            if not any(u['plugin']=='agentic-vault' and u['role']==role and u['evidence']==evidence for u in prior['uses']):
                raise ValueError('Existing new-reference use differs; manual review required: '+identity)
            continue
        if canonical_key(url)['key']!=identity:raise ValueError('Canonical identity mismatch: '+identity)
        revised['sources'].append({'id':identity,'kind':kind,'title':title,'url':url,'year':year,
            'keys':[identity,*extra],'aliases':list(aliases),'tags':[],'note':note,
            'uses':[{'plugin':'agentic-vault','role':role,'evidence':evidence}]})
        added.append(identity)
    revised['snapshots']['agentic-vault']={'name':'Agentic Vault','version':tag,'commit':commit,
        'url':f'https://github.com/Technoetic/agentic-vault/tree/{commit}'}
    if revised!=registry:revised['updatedAt']=updated_at or datetime.now(timezone.utc).isoformat()
    merged=merge_sources(revised['sources']);validate_catalog({**revised,'sources':merged})
    by_id={source['id']:source for source in merged}
    # Never add or mutate image/prompt/generation records for uncommissioned art.
    for asset in images['assets']:
        for field in ('evidenceUrls','currentEvidenceUrls'):
            if field not in asset:raise ValueError('Existing artwork current evidence field missing')
            urls=[]
            for url in asset[field]:
                if url.startswith(PREFIX) and url not in remapped:raise ValueError('Artwork URL not in prior citation map')
                urls.append(remapped.get(url,url))
            if asset['sourceId'] in EXISTING_IDS:
                urls=[row['url'] for use in by_id[asset['sourceId']]['uses'] for row in use['evidence']]
            asset[field]=urls
    if len(images['assets'])!=artwork['count']:raise ValueError('Artwork count mismatch')
    return revised,images,{'priorAgenticVaultCitations':count,'remappedLines':moved,
        'addedSourceIds':added,'addedUsesOnExistingSources':uses_added,'counts':metrics(merged),
        'artworkCount':len(images['assets']),
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
        # Split on newlines only so line numbers match the GitHub blob view.
        if file not in cache:cache[file]=git('show',args.commit+':'+file).split('\n')
        return cache[file]
    source=ROOT/'data/registry.source.json';art=ROOT/'docs/card-artwork-unique-prompts.json'
    revised,images,summary=prepare_update(json.loads(source.read_text(encoding='utf-8')),
        json.loads(art.read_text(encoding='utf-8')),read_lines,args.commit,args.tag)
    if args.apply:write_update([(source,revised),(art,images)])
    print(json.dumps({'status':'PASS','mode':'applied' if args.apply else 'dry-run',
        'publicAvailability':'caller must independently verify before apply',**summary}))
    return 0
if __name__=='__main__':raise SystemExit(main())
