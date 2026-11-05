import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {canonicalKey} from '../src/core/identity.mjs';
import {findMatches,filterSources} from '../src/core/catalog.mjs';

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
