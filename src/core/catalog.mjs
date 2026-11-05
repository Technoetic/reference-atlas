import {canonicalKey,nameKey} from './identity.mjs';
export function findMatches(catalog,input){
  const identity=canonicalKey(input);if(!identity)return{status:'invalid',key:null,matches:[]};
  const {key}=identity,sources=catalog.sources??[];
  if(!key.startsWith('name:')){const matches=sources.filter(source=>source.id===key||source.keys?.includes(key));return{status:matches.length?'known':'not_found',key,matches};}
  const needle=key.slice(5),matches=sources.filter(source=>[source.title,...(source.aliases??[])].filter(x=>typeof x==='string').map(nameKey).some(name=>name===needle||(needle.length>=5&&name.includes(needle))));
  return{status:matches.length?'possible':'not_found',key,matches};
}
export function filterSources(catalog,{plugin='all',kind='all',query='',sort='title',tag='all'}={}){
  const q=query.trim().toLocaleLowerCase(),identity=q?canonicalKey(query):null;
  const result=(catalog.sources??[]).filter(source=>{
    const plugins=new Set(source.uses.map(use=>use.plugin));
    if(plugin==='shared'&&plugins.size<2)return false;
    if(!['all','shared'].includes(plugin)&&!plugins.has(plugin))return false;
    if(kind!=='all'&&source.kind!==kind)return false;
    if(tag!=='all'&&!source.tags.includes(tag))return false;
    if(q){const text=[source.title,...(source.aliases??[]),...(source.tags??[]),...(source.keys??[])].join(' ').toLocaleLowerCase();if(!text.includes(q)&&!source.keys?.includes(identity?.key))return false;}
    return true;
  });
  const title=(a,b)=>a.title.localeCompare(b.title,'ko',{sensitivity:'base'});
  result.sort((a,b)=>{
    if(sort==='year-desc'||sort==='year-asc'){
      if(a.year===null||a.year===undefined)return b.year===null||b.year===undefined?title(a,b):1;
      if(b.year===null||b.year===undefined)return-1;
      return(sort==='year-desc'?b.year-a.year:a.year-b.year)||title(a,b);
    }
    if(sort==='connections')return b.uses.length-a.uses.length||title(a,b);
    return title(a,b);
  });return result;
}
