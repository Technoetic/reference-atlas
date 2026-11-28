import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCatalog} from '../src/core/validation.mjs';
import {filterSources} from '../src/core/catalog.mjs';
import {pluginLabel,pluginClass} from '../src/screens/util.mjs';
const fixture=()=>({schemaVersion:1,sources:[{id:'arxiv:2502.12110',kind:'paper',title:'A-MEM',url:'https://arxiv.org/abs/2502.12110',year:2025,tags:[],aliases:[],keys:['arxiv:2502.12110'],uses:[{plugin:'agentic-vault',role:'reference',evidence:[{file:'docs/x.md',line:1,url:`https://github.com/Technoetic/agentic-vault/blob/${'a'.repeat(40)}/docs/x.md#L1`,excerpt:'A-MEM'}]}]}]});
test('complete public source structure is accepted',()=>assert.equal(validateCatalog(fixture()).sources.length,1));
test('node-pg-defense is accepted as the third catalog plugin and filterable alongside shared sources',()=>{
  const commit='b'.repeat(40);
  const catalog=fixture();
  catalog.sources.push({
    id:'github:brianc/node-postgres',kind:'project',title:'node-postgres (pg)',url:'https://github.com/brianc/node-postgres',
    year:null,tags:['SQL'],aliases:['pg'],keys:['github:brianc/node-postgres'],
    uses:[{plugin:'node-pg-defense',role:'reference',evidence:[{file:'docs/references.md',line:17,url:`https://github.com/Technoetic/node-pg-defense/blob/${commit}/docs/references.md#L17`,excerpt:'node-postgres'}]}]
  });
  catalog.sources[0].uses.push({
    plugin:'node-pg-defense',role:'reference',evidence:[{file:'docs/references.md',line:9,url:`https://github.com/Technoetic/node-pg-defense/blob/${commit}/docs/references.md#L9`,excerpt:'shared'}]
  });
  assert.equal(validateCatalog(catalog).sources.length,2);
  assert.equal(filterSources(catalog,{plugin:'node-pg-defense'}).length,2);
  assert.equal(filterSources(catalog,{plugin:'shared'}).length,1);
  assert.equal(pluginLabel('node-pg-defense'),'Node PG Defense');
  assert.equal(pluginClass('node-pg-defense'),'npd');
});
test('an official article can remain a separately identified background source',()=>{
  const catalog=fixture(),article=catalog.sources[0];
  Object.assign(article,{id:'url:https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit',kind:'article',title:'NVIDIA Agent Toolkit article',url:'https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit/',keys:['url:https://blogs.nvidia.com/blog/enterprise-platforms-agent-toolkit']});
  article.uses[0].role='background';
  assert.equal(validateCatalog(catalog).sources[0].kind,'article');
});
for(const [label,change] of [['empty ID',s=>s.id=''],['unbound evidence',s=>s.uses[0].evidence=[{}]],['unsafe evidence path',s=>s.uses[0].evidence[0].file='../outside'],['wrong line type',s=>s.uses[0].evidence[0].line=true]])
  test(`catalog rejects ${label}`,()=>{const c=fixture();change(c.sources[0]);assert.throws(()=>validateCatalog(c));});
