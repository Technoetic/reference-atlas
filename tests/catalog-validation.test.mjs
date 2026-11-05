import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCatalog} from '../src/core/validation.mjs';
const fixture=()=>({schemaVersion:1,sources:[{id:'arxiv:2502.12110',kind:'paper',title:'A-MEM',url:'https://arxiv.org/abs/2502.12110',year:2025,tags:[],aliases:[],keys:['arxiv:2502.12110'],uses:[{plugin:'agentic-vault',role:'reference',evidence:[{file:'docs/x.md',line:1,url:`https://github.com/Technoetic/agentic-vault/blob/${'a'.repeat(40)}/docs/x.md#L1`,excerpt:'A-MEM'}]}]}]});
test('complete public source structure is accepted',()=>assert.equal(validateCatalog(fixture()).sources.length,1));
for(const [label,change] of [['empty ID',s=>s.id=''],['unbound evidence',s=>s.uses[0].evidence=[{}]],['unsafe evidence path',s=>s.uses[0].evidence[0].file='../outside'],['wrong line type',s=>s.uses[0].evidence[0].line=true]])
  test(`catalog rejects ${label}`,()=>{const c=fixture();change(c.sources[0]);assert.throws(()=>validateCatalog(c));});
