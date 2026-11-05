export function nameKey(value){return String(value).normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();}
const identity=(key,kind,canonicalUrl=null)=>({key,kind,canonicalUrl});
function arxiv(value){
  const match=value.match(/^(\d{4}\.\d{4,5})(?:v[1-9]\d*)?(?:\.pdf)?$/i);
  if(!match||Number(match[1].slice(2,4))<1||Number(match[1].slice(2,4))>12)return null;
  return identity(`arxiv:${match[1]}`,'paper',`https://arxiv.org/abs/${match[1]}`);
}
export function canonicalKey(input){
  if(typeof input!=='string'||!input.trim()||input.length>8192)return null;
  let value=input.trim().replace(/^<|>$/g,'');
  if(/[\u0000-\u001f]/.test(value)||/^(javascript|data|file|vbscript):/i.test(value))return null;
  const markdown=value.match(/^\[[^\]]*\]\((https?:\/\/[^)]+)\)$/);if(markdown)value=markdown[1];
  if(/^git@github.com:/i.test(value))value=`https://github.com/${value.split(':').slice(1).join(':')}`;
  if(/^arxiv:/i.test(value))return arxiv(value.slice(value.indexOf(':')+1).trim());
  if(/^\d{4}\.\d{4,5}(?:v\d+)?(?:\.pdf)?$/i.test(value))return arxiv(value);
  if(/^doi:/i.test(value))value=value.slice(4).trim();
  if(/^10\.\d{4,9}\/\S+$/i.test(value)){const id=value.toLowerCase().replace(/[.,]+$/,'');return identity(`doi:${id}`,'paper',`https://doi.org/${id}`);}
  if(/^https?:\/\//i.test(value)){
    let url;try{url=new URL(value);}catch{return null;}
    if(!url.hostname||url.username||url.password||/\s/.test(value))return null;
    const host=url.hostname.toLowerCase();
    if(['arxiv.org','www.arxiv.org','export.arxiv.org'].includes(host)){const m=url.pathname.match(/^\/(?:abs|pdf|html)\/([^/]+)\/?$/);return m?arxiv(m[1]):null;}
    if(['doi.org','dx.doi.org','www.doi.org'].includes(host)){let id;try{id=decodeURIComponent(url.pathname.replace(/^\//,'')).toLowerCase();}catch{return null;}return /^10\.\d{4,9}\/\S+$/i.test(id)?identity(`doi:${id}`,'paper',`https://doi.org/${id}`):null;}
    if(['github.com','www.github.com'].includes(host)){
      const parts=url.pathname.replace(/^\/+|\/+$/g,'').split('/');if(parts.length<2)return null;
      const owner=parts[0],repo=parts[1].replace(/\.git$/i,'');
      if(![owner,repo].every(x=>/^[A-Za-z0-9_.-]+$/.test(x))||['login','settings','features','marketplace','topics','collections','orgs','users'].includes(owner.toLowerCase()))return null;
      const slug=`${owner}/${repo}`.toLowerCase();return identity(`github:${slug}`,'project',`https://github.com/${slug}`);
    }
    url.hash='';url.pathname=url.pathname.replace(/\/+$/,'')||'/';
    const params=[...url.searchParams].filter(([key])=>!key.toLowerCase().startsWith('utm_')&&!['gclid','fbclid'].includes(key.toLowerCase())).sort(([a,av],[b,bv])=>a.localeCompare(b)||av.localeCompare(bv));
    url.search=new URLSearchParams(params).toString();return identity(`url:${url.href}`,'reference',url.href);
  }
  if(value.includes('://'))return null;
  const key=nameKey(value);return key?identity(`name:${key}`,'research-name'):null;
}
