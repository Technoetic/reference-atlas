#!/usr/bin/env python3
"""Check candidates locally; optionally fetch only the current public registry."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.request import Request,urlopen
from urllib.error import URLError
from reference_identity import find_matches,validate_catalog

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,default=Path(__file__).resolve().parents[1]/'data/catalog.json')
    parser.add_argument('--published',action='store_true',help='Fetch the current public registry only; candidate URLs are never requested')
    parser.add_argument('--url',action='append',default=[],help='URL, DOI, arXiv ID or title; repeatable')
    parser.add_argument('--input',type=Path,help='UTF-8 candidate list, one per line')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--fail-on-known',action='store_true',help='Exit 3 when an existing identifier is found')
    args=parser.parse_args(argv)
    try:
        if args.published:
            request=Request('https://technoetic.github.io/reference-atlas/data/catalog.json?_at='+str(time.time_ns()),headers={'Cache-Control':'no-cache','User-Agent':'ReferenceAtlas/1'})
            with urlopen(request,timeout=15) as response:raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024:raise ValueError('Published catalog exceeds size limit')
            catalog=validate_catalog(json.loads(raw.decode('utf-8-sig')))
        else:
            if args.catalog.stat().st_size>8*1024*1024:raise ValueError('Catalog exceeds size limit')
            catalog=validate_catalog(json.loads(args.catalog.read_text(encoding='utf-8-sig')))
        candidates=list(args.url)
        if args.input:
            if args.input.stat().st_size>2*1024*1024:raise ValueError('Candidate file exceeds size limit')
            candidates.extend(x.strip() for x in args.input.read_text(encoding='utf-8-sig').splitlines() if x.strip())
        if not candidates or len(candidates)>1000:raise ValueError('Provide between 1 and 1000 candidates')
        results=[{'input':value,**find_matches(catalog,value)} for value in candidates]
        output={'schemaVersion':1,'catalogUpdatedAt':catalog.get('updatedAt'),'results':results,
                'notice':'not_found means absent from this snapshot; it does not prove novelty. Name matches require identity review.'}
        if args.json:print(json.dumps(output,ensure_ascii=False))
        else:
            labels={'known':'이미 참조','possible':'이름 유사·확인 필요','not_found':'목록에서 찾지 못함','invalid':'유효한 식별자가 아님'}
            for result in results:
                print(f"{labels[result['status']]}\t{result['input']}")
                for match in result['matches']:
                    plugins=', '.join(sorted({x['plugin'] for x in match['uses']}))
                    print(f"  {match['title']} [{plugins}] {match.get('url') or ''}")
        return 3 if args.fail_on_known and any(x['status']=='known' for x in results) else 0
    except (OSError,URLError,UnicodeError,ValueError,TypeError,KeyError) as error:
        print(json.dumps({'status':'error','message':str(error)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
