import {canonicalKey} from './identity.mjs';
export function validateCatalog(catalog){
  const fail=()=>{throw new Error('출처 목록의 형식 또는 인용 근거가 올바르지 않습니다.');};
  if(!catalog||catalog.schemaVersion!==1||!Array.isArray(catalog.sources))fail();
  const ids=new Set(),strong=new Set(),snapshots=catalog.snapshots??{};
  if(typeof snapshots!=='object'||Array.isArray(snapshots))fail();
  for(const source of catalog.sources){
    if(!source||typeof source.id!=='string'||!source.id.trim()||ids.has(source.id))fail();ids.add(source.id);
    if(!['paper','project','format','research-name'].includes(source.kind)||typeof source.title!=='string'||!source.title.trim())fail();
    if(source.year!==null&&source.year!==undefined&&(!Number.isInteger(source.year)||source.year<1000||source.year>3000))fail();
    for(const field of ['tags','aliases'])if(!Array.isArray(source[field])||source[field].some(x=>typeof x!=='string'))fail();
    if(source.url!==null&&source.url!==undefined&&(!/^https?:\/\//i.test(source.url)||!canonicalKey(source.url)?.canonicalUrl))fail();
    if(!Array.isArray(source.keys)||!source.keys.length||source.keys.some(x=>typeof x!=='string'||!x))fail();
    for(const key of source.keys)if(!key.startsWith('name:')){if(strong.has(key))fail();strong.add(key);}
    if(!Array.isArray(source.uses)||!source.uses.length)fail();
    for(const use of source.uses){
      if(!use||!['agentic-vault','semantic-crosscheck'].includes(use.plugin)||!['reference','background','unresolved'].includes(use.role)||!Array.isArray(use.evidence)||!use.evidence.length)fail();
      for(const row of use.evidence){
        if(!row||typeof row.file!=='string'||!row.file||row.file.startsWith('/')||row.file.includes('\\')||row.file.includes(':')||row.file.split('/').some(x=>x==='..'||x==='.')||!Number.isInteger(row.line)||row.line<1||typeof row.excerpt!=='string'||!row.excerpt.trim()||typeof row.url!=='string')fail();
        const prefix=`https://github.com/Technoetic/${use.plugin}/blob/`,suffix=`/${row.file}#L${row.line}`;
        if(!row.url.startsWith(prefix)||!row.url.endsWith(suffix))fail();
        const commit=row.url.slice(prefix.length,-suffix.length);
        if(!/^[a-f0-9]{40}$/.test(commit)||(snapshots[use.plugin]&&snapshots[use.plugin].commit!==commit))fail();
      }
    }
  }return catalog;
}
