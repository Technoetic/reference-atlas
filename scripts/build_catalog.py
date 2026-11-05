"""Validate and merge curated, public, source-bound reference records."""
from copy import deepcopy
import csv
import json
from pathlib import Path
from reference_identity import validate_catalog

ROOT=Path(__file__).resolve().parents[1]

def metrics(sources):
    result={kind:sum(source['kind']==kind for source in sources) for kind in ['paper','project','format','research-name']}
    result['total']=len(sources)
    result['shared']=sum(len({use['plugin'] for use in source['uses']})>1 for source in sources)
    result['citations']=sum(len(use['evidence']) for source in sources for use in source['uses'])
    return result

def merge_sources(records):
    merged=[]
    for original in records:
        candidate=deepcopy(original)
        validate_catalog({'schemaVersion':1,'sources':[candidate]})
        # Explicit identities only: equal titles do not merge different papers.
        keys=set(candidate['keys'])
        matches=[source for source in merged if source['id']==candidate['id'] or
                 (set(source['keys'])&keys and any(not key.startswith('name:') for key in set(source['keys'])&keys))]
        if not matches:
            merged.append(candidate);continue
        target=matches[0]
        for incoming in [*matches[1:],candidate]:
            if incoming['kind']!=target['kind']:raise ValueError('Conflicting kinds for a shared source identity')
            target['keys']=sorted(set(target['keys'])|set(incoming['keys']))
            target['aliases']=sorted(set(target.get('aliases',[]))|set(incoming.get('aliases',[]))|{incoming['title']})
            target['tags']=sorted(set(target.get('tags',[]))|set(incoming.get('tags',[])))
            if target.get('year') is None:target['year']=incoming.get('year')
            for use in incoming['uses']:
                same=next((item for item in target['uses'] if item['plugin']==use['plugin']),None)
                if same:
                    if use['role']=='reference':same['role']='reference'
                    existing={(row['file'],row['line'],row['url']) for row in same['evidence']}
                    same['evidence'].extend(row for row in use['evidence'] if (row['file'],row['line'],row['url']) not in existing)
                else:target['uses'].append(deepcopy(use))
            if incoming is not candidate:merged.remove(incoming)
        target['aliases']=[alias for alias in target['aliases'] if alias!=target['title']]
    merged.sort(key=lambda source:(source['kind'],source['title'].lower(),source['id']))
    validate_catalog({'schemaVersion':1,'sources':merged})
    return merged

def build(root=ROOT):
    data=json.loads((root/'data/registry.source.json').read_text(encoding='utf8'))
    sources=merge_sources(data['sources'])
    catalog={key:value for key,value in data.items() if key!='sources'}
    catalog.update({'schemaVersion':1,'sources':sources,'counts':metrics(sources)})
    catalog['countsByPlugin']={plugin:metrics([source for source in sources if any(use['plugin']==plugin for use in source['uses'])])
                              for plugin in data['snapshots']}
    for plugin,counts in catalog['countsByPlugin'].items():
        counts['citations']=sum(len(use['evidence']) for source in sources for use in source['uses'] if use['plugin']==plugin)
    (root/'data/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    with (root/'data/catalog.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(['id','kind','title','year_hint','source_url','plugins','roles','evidence_urls'])
        for source in sources:
            writer.writerow([source['id'],source['kind'],source['title'],source.get('year') or '',source.get('url') or '',
                '; '.join(use['plugin'] for use in source['uses']),'; '.join(use['role'] for use in source['uses']),
                '; '.join(row['url'] for use in source['uses'] for row in use['evidence'])])
    return catalog

if __name__=='__main__':
    catalog=build();print(json.dumps({'status':'PASS','counts':catalog['counts'],'countsByPlugin':catalog['countsByPlugin']},ensure_ascii=False))
