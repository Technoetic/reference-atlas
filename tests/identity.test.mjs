import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {canonicalKey} from '../src/core/identity.mjs';
import {findMatches,filterSources} from '../src/core/catalog.mjs';
import {catalogStats,kindLabel,kindKorean,sourceCard} from '../src/screens/util.mjs';

const cases=JSON.parse(await readFile(new URL('./fixtures/identity-cases.json',import.meta.url),'utf8'));
for(const item of cases)test(`identity: ${item.input}`,()=>assert.equal(canonicalKey(item.input)?.key??null,item.key));
const record=(id,title,year,plugins)=>({id,kind:'paper',title,year,tags:['memory'],keys:[id],aliases:[title],url:`https://arxiv.org/abs/${id.slice(6)}`,uses:plugins.map(plugin=>({plugin,role:'reference',evidence:[]}))});
const catalog={schemaVersion:1,sources:[record('arxiv:2502.12110','A-MEM',2025,['agentic-vault','semantic-crosscheck']),record('arxiv:2401.12345','Older',2024,['semantic-crosscheck']),record('arxiv:2301.12345','Unknown year',null,['agentic-vault'])]};
test('paper versions find the existing record',()=>assert.equal(findMatches(catalog,'https://arxiv.org/pdf/2502.12110v7.pdf').status,'known'));
test('matching alias is possible, not certain identifier match',()=>assert.equal(findMatches(catalog,'a-mem').status,'possible'));
test('unknown result never claims novelty',()=>assert.equal(findMatches(catalog,'https://arxiv.org/abs/2502.12111').status,'not_found'));
test('shared plugin filter uses distinct actual plugin references',()=>assert.deepEqual(filterSources(catalog,{plugin:'shared'}).map(x=>x.title),['A-MEM']));
test('case-insensitive text search and plugin filters compose',()=>assert.deepEqual(filterSources(catalog,{plugin:'agentic-vault',query:'a-mEM'}).map(x=>x.title),['A-MEM']));
test('year descending keeps unknown dates last',()=>assert.deepEqual(filterSources(catalog,{sort:'year-desc'}).map(x=>x.year),[2025,2024,null]));
test('year ascending also keeps unknown dates last',()=>assert.deepEqual(filterSources(catalog,{sort:'year-asc'}).map(x=>x.year),[2024,2025,null]));
test('filtering does not mutate the source array',()=>{const old=JSON.stringify(catalog);filterSources(catalog,{sort:'title'});assert.equal(JSON.stringify(catalog),old)});

const article={...record('url:https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit','NVIDIA Agent Toolkit article',2026,['agentic-vault']),kind:'article',url:'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/'};
const project={...record('github:nvidia/auto-ontology','Auto Ontology',null,['agentic-vault']),kind:'project',url:'https://github.com/NVIDIA/auto-ontology'};
test('article and repository URLs resolve to their own records without an alias merge',()=>{
  const sources={sources:[article,project]};
  assert.deepEqual(findMatches(sources,article.url).matches.map(source=>source.id),[article.id]);
  assert.deepEqual(findMatches(sources,project.url+'/tree/2a24f5d34ef6b6e168a7f22d308504d3ab36a198').matches.map(source=>source.id),[project.id]);
  assert.equal(canonicalKey(article.url).kind,'reference');
  assert.deepEqual(filterSources(sources,{kind:'article',plugin:'agentic-vault'}).map(source=>source.id),[article.id]);
});
test('article counts never inflate papers or projects and remain visible by plugin',()=>{
  const sources={sources:[...catalog.sources,article,project]};
  assert.deepEqual(catalogStats(sources),{total:5,papers:3,projects:1,articles:1,names:0,shared:1});
  assert.deepEqual(catalogStats(sources,'semantic-crosscheck'),{total:2,papers:2,projects:0,articles:0,names:0,shared:1});
  assert.equal(kindLabel('article'),'ARTICLE');
  assert.equal(kindKorean('article'),'기사');
  assert.match(sourceCard(article),/>ARTICLE</);
});
