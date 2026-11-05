"""Offline source identities and registry lookup. Does not fetch candidate URLs."""
import re
import unicodedata
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,unquote

ARXIV=re.compile(r'^(\d{4}\.\d{4,5})(?:v[1-9]\d*)?(?:\.pdf)?$',re.I)
DOI=re.compile(r'^10\.\d{4,9}/\S+$',re.I)
PLUGINS={'agentic-vault','semantic-crosscheck'}

def name_key(value):
    value=unicodedata.normalize('NFKC',value).lower()
    return re.sub(r'[\W_]+',' ',value,flags=re.UNICODE).strip()

def _identity(key,kind,url=None):
    return {'key':key,'kind':kind,'canonicalUrl':url}

def _arxiv(value):
    match=ARXIV.fullmatch(value)
    if not match:return None
    identifier=match.group(1)
    if not 1<=int(identifier[2:4])<=12:return None
    return _identity('arxiv:'+identifier,'paper','https://arxiv.org/abs/'+identifier)

def canonical_key(value):
    if not isinstance(value,str) or not value.strip() or len(value)>8192:return None
    value=value.strip().strip('<>')
    if any(ord(c)<32 for c in value):return None
    markdown=re.fullmatch(r'\[[^\]]*\]\((https?://[^)]+)\)',value)
    if markdown:value=markdown.group(1)
    if value.lower().startswith(('javascript:','data:','file:','vbscript:')):return None
    if value.lower().startswith('git@github.com:'):
        value='https://github.com/'+value.split(':',1)[1]
    if value.lower().startswith('arxiv:'):return _arxiv(value.split(':',1)[1].strip())
    if re.fullmatch(r'\d{4}\.\d{4,5}(?:v\d+)?(?:\.pdf)?',value,re.I):return _arxiv(value)
    if value.lower().startswith('doi:'):value=value.split(':',1)[1].strip()
    if DOI.fullmatch(value):
        identifier=value.lower().rstrip('.,')
        return _identity('doi:'+identifier,'paper','https://doi.org/'+identifier)
    if re.match(r'^https?://',value,re.I):
        try:
            parsed=urlsplit(value)
            parsed.port  # Validate an explicitly supplied port as well as the host.
        except ValueError:return None
        if not parsed.hostname or parsed.username or parsed.password or re.search(r'\s',value):return None
        host=parsed.hostname.lower()
        if host in {'arxiv.org','www.arxiv.org','export.arxiv.org'}:
            match=re.fullmatch(r'/(?:abs|pdf|html)/([^/]+)/?',parsed.path)
            return _arxiv(match.group(1)) if match else None
        if host in {'doi.org','dx.doi.org','www.doi.org'}:
            identifier=unquote(parsed.path.lstrip('/')).lower()
            if not DOI.fullmatch(identifier):return None
            return _identity('doi:'+identifier,'paper','https://doi.org/'+identifier)
        if host in {'github.com','www.github.com'}:
            parts=parsed.path.strip('/').split('/')
            if len(parts)<2:return None
            owner,repo=parts[:2];repo=re.sub(r'\.git$','',repo,flags=re.I)
            if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',part) for part in [owner,repo]):return None
            if owner.lower() in {'login','settings','features','marketplace','topics','collections','orgs','users'}:return None
            slug=(owner+'/'+repo).lower()
            return _identity('github:'+slug,'project','https://github.com/'+slug)
        # Preserve meaningful query parameters; remove only common tracking keys.
        query=urlencode(sorted((k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True)
                               if not k.lower().startswith('utm_') and k.lower() not in {'gclid','fbclid'}))
        path=parsed.path.rstrip('/') or '/'
        url=urlunsplit((parsed.scheme.lower(),parsed.netloc.lower(),path,query,''))
        return _identity('url:'+url,'reference',url)
    if '://' in value:return None
    key=name_key(value)
    return _identity('name:'+key,'research-name') if key else None

def validate_catalog(catalog):
    if not isinstance(catalog,dict) or type(catalog.get('schemaVersion')) is not int or catalog['schemaVersion']!=1 or not isinstance(catalog.get('sources'),list):
        raise ValueError('Invalid catalog schema')
    ids=set();strong_keys=set()
    if not isinstance(catalog.get('snapshots',{}),dict):raise ValueError('Invalid snapshot metadata')
    for source in catalog['sources']:
        if not isinstance(source,dict) or not isinstance(source.get('id'),str) or not source['id'].strip() or source['id'] in ids:
            raise ValueError('Missing or duplicate source identity')
        ids.add(source['id'])
        if source.get('kind') not in {'paper','project','article','format','research-name'} or not isinstance(source.get('title'),str) or not source['title'].strip():
            raise ValueError('Invalid source kind or title')
        if source.get('year') is not None and (type(source['year']) is not int or not 1000<=source['year']<=3000):raise ValueError('Invalid source year')
        for field in ['tags','aliases']:
            if not isinstance(source.get(field),list) or not all(isinstance(value,str) for value in source[field]):raise ValueError('Invalid source labels')
        if source.get('url') is not None:
            parsed=canonical_key(source['url'])
            if not parsed or not parsed['canonicalUrl'] or not source['url'].lower().startswith(('http://','https://')):raise ValueError('Invalid source URL')
        if not isinstance(source.get('keys'),list) or not source['keys'] or not all(isinstance(x,str) and x for x in source['keys']):
            raise ValueError('Missing source keys')
        for key in source['keys']:
            if not key.startswith('name:'):
                if key in strong_keys:raise ValueError('A strong identifier belongs to multiple sources')
                strong_keys.add(key)
        if not isinstance(source.get('uses'),list) or not source['uses']:raise ValueError('Missing cited use')
        for use in source['uses']:
            if not isinstance(use,dict) or use.get('plugin') not in PLUGINS or use.get('role') not in {'reference','background','unresolved'}:
                raise ValueError('Invalid cited use')
            if not isinstance(use.get('evidence'),list) or not use['evidence']:raise ValueError('Missing citation evidence')
            for row in use['evidence']:
                if not isinstance(row,dict) or not isinstance(row.get('file'),str) or not row['file'] or '\\' in row['file'] or ':' in row['file'] or row['file'].startswith('/') or any(part in {'.','..'} for part in row['file'].split('/')):
                    raise ValueError('Invalid citation file')
                if type(row.get('line')) is not int or row['line']<1 or not isinstance(row.get('excerpt'),str) or not row['excerpt'].strip():raise ValueError('Invalid citation line or excerpt')
                prefix=f"https://github.com/Technoetic/{use['plugin']}/blob/"
                suffix=f"/{row['file']}#L{row['line']}"
                url=row.get('url','')
                if not isinstance(url,str) or not url.startswith(prefix) or not url.endswith(suffix):raise ValueError('Invalid citation URL')
                commit=url[len(prefix):-len(suffix)]
                if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Citation must pin a commit')
                snapshot=catalog.get('snapshots',{}).get(use['plugin'])
                if snapshot and snapshot.get('commit')!=commit:raise ValueError('Citation differs from the declared snapshot')
    return catalog

def find_matches(catalog,value):
    identity=canonical_key(value)
    if identity is None:return {'status':'invalid','key':None,'matches':[]}
    key=identity['key'];sources=catalog.get('sources',[])
    if not key.startswith('name:'):
        matches=[source for source in sources if key in source.get('keys',[]) or key==source.get('id')]
        return {'status':'known' if matches else 'not_found','key':key,'matches':matches}
    needle=key[5:]
    matches=[]
    for source in sources:
        names=[source.get('title',''),*source.get('aliases',[])]
        normalized=[name_key(x) for x in names if isinstance(x,str)]
        if needle in normalized or (len(needle)>=5 and any(needle in name for name in normalized)):
            matches.append(source)
    return {'status':'possible' if matches else 'not_found','key':key,'matches':matches}
