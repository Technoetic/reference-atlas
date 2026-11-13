import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {sourceArtwork,artworkCover} from '../src/screens/art.mjs';

const pending=JSON.parse(await readFile(new URL('../docs/sxc024-card-artwork.pending.json',import.meta.url),'utf8'));
const manifest=JSON.parse(await readFile(new URL('../docs/card-artwork-unique-prompts.json',import.meta.url),'utf8'));
const ids=new Set([
  'github:stryker-mutator/stryker-js','github:stryker-mutator/mutation-testing-elements',
  'arxiv:2004.00481','github:georgia-tech-db/spes'
]);

test('all four pending v0.24 images render their exact source-specific card and detail artwork',()=>{
  assert.equal(pending.count,4);
  assert.deepEqual(new Set(pending.assets.map(asset=>asset.sourceId)),ids);
  for(const asset of pending.assets){
    const expected=new URL(`../${asset.output}`,import.meta.url).href;
    assert.equal(sourceArtwork({id:asset.sourceId}).src,expected);
    assert.deepEqual(asset.dimensions,[960,640]);
    assert.ok(asset.prompt.trim());
    assert.ok(asset.factualConcept.trim());
    assert.ok(asset.generationEvidenceUrls.length);
    for(const detail of [false,true]){
      const html=artworkCover({id:asset.sourceId},{detail});
      assert.ok(html.includes(`src="${expected}"`));
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
    }
  }
});

test('149 preserved originals plus the four commissions have 153 unique actual WebP files and prompts',async()=>{
  const originals=manifest.assets.filter(asset=>!ids.has(asset.sourceId));
  assert.equal(originals.length,149);
  const all=[...originals,...pending.assets];
  assert.equal(new Set(all.map(asset=>asset.output)).size,153);
  assert.equal(new Set(all.map(asset=>asset.prompt)).size,153);
  const hashes=[];
  for(const asset of all){
    const bytes=await readFile(new URL(`../${asset.output}`,import.meta.url));
    assert.equal(bytes.subarray(0,4).toString(),'RIFF');
    assert.equal(bytes.subarray(8,12).toString(),'WEBP');
    const hash=createHash('sha256').update(bytes).digest('hex');
    assert.equal(hash,asset.sha256);
    assert.equal(bytes.length,asset.bytes);
    hashes.push(hash);
  }
  assert.equal(new Set(hashes).size,153);
});
