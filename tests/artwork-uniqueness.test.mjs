import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {sourceArtwork,artworkCover} from '../src/screens/art.mjs';

const catalog=JSON.parse(await readFile(new URL('../data/catalog.json',import.meta.url),'utf8'));
const manifest=JSON.parse(await readFile(new URL('../docs/card-artwork-unique-prompts.json',import.meta.url),'utf8'));
const newlyCommissioned=new Set([
  'url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai',
  'github:madthanu/alice','github:treeverse/dvc','arxiv:2407.12784','github:ai-secure/agentpoison'
]);
const uncommissioned=new Set([
  'url:https://papers.voltropy.com/LCM','github:martian-engineering/lossless-claw',
  'url:https://factory.com/news/evaluating-compression','github:sourcegraph/sourcegraph-public-snapshot',
  'github:sourcegraph/zoekt','github:prometheus/prometheus','github:phenomnomnominal/betterer','github:logpai/drain3',
  'arxiv:2607.19865','url:https://manpages.debian.org/unstable/reprotest/reprotest.1.en.html','arxiv:2610.30571',
  'github:wenjing95/stale-docs-data','arxiv:2610.31778','github:manuelschipper/nah',
  'url:https://code.claude.com/docs/en/worktrees','github:python-trio/trio','github:gastownhall/beads',
  'url:https://code.claude.com/docs/en/hooks','url:https://code.claude.com/docs/en/plugins/cli-reference',
  'arxiv:2606.22528','arxiv:2607.20972','github:joeblackwaslike/lessons-learned'
]);

test('artwork provenance assigns each generated file and exact prompt to its source',async()=>{
  assert.equal(manifest.count,manifest.assets.length);
  assert.equal(new Set(manifest.assets.map(asset=>asset.sourceId)).size,manifest.assets.length);
  const hashes=[];
  for(const asset of manifest.assets){
    const expected=new URL(`../${asset.output}`,import.meta.url);
    assert.equal(sourceArtwork({id:asset.sourceId}).src,expected.href);
    const bytes=await readFile(expected),digest=createHash('sha256').update(bytes).digest('hex');
    assert.equal(digest,asset.sha256);
    assert.equal(bytes.length,asset.bytes);
    assert.ok(asset.prompt.trim());
    hashes.push(digest);
    if(['v0.41.0','v0.42.0','v0.43.0'].includes(catalog.snapshots['agentic-vault'].version)){
      assert.ok(asset.generationEvidenceUrls.length);
      assert.deepEqual(asset.currentEvidenceUrls,asset.evidenceUrls);
    }
  }
  assert.equal(new Set(hashes).size,manifest.assets.length);
});

test('commissioned sources have dedicated images; explicit uncommissioned sources render text fallback',()=>{
  const images=[];
  for(const source of catalog.sources){
    const art=sourceArtwork(source);
    if(art.src)images.push(art.src);
    else{
      assert.ok(uncommissioned.has(source.id),`Missing commissioned artwork: ${source.id}`);
      for(const detail of [false,true]){
        const html=artworkCover(source,{detail});
        assert.ok(html.includes('is-art-fallback'));
        assert.ok(html.includes('REFERENCE'));
        assert.ok(!html.includes('<img'));
      }
    }
  }
  assert.equal(new Set(images).size,images.length,'Different cards must not share topic artwork');
  assert.equal(images.length,manifest.assets.length);
  assert.equal(images.length+uncommissioned.size,catalog.sources.length);
});

test('dedicated card images have different actual file contents',async()=>{
  const illustrated=catalog.sources.filter(source=>sourceArtwork(source).src);
  const hashes=await Promise.all(illustrated.map(async source=>{
    const bytes=await readFile(new URL(sourceArtwork(source).src));
    assert.equal(bytes.subarray(0,4).toString(),'RIFF');
    assert.equal(bytes.subarray(8,12).toString(),'WEBP');
    return createHash('sha256').update(bytes).digest('hex');
  }));
  assert.equal(new Set(hashes).size,illustrated.length,'A renamed copy of another image is still shared artwork');
});

test('the five newly commissioned references render their own card and detail images',()=>{
  const urls=new Set();
  for(const id of newlyCommissioned){
    const art=sourceArtwork({id});
    assert.ok(art.src);
    urls.add(art.src);
    for(const detail of [false,true]){
      const html=artworkCover({id,title:'Commissioned <reference>'},{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(art.src));
    }
  }
  assert.equal(urls.size,newlyCommissioned.size);
});

test('each uncommissioned v0.43.0 reference renders its card and detail text fallback',()=>{
  for(const id of uncommissioned){
    assert.ok(catalog.sources.some(source=>source.id===id),`Unknown listed source: ${id}`);
    assert.equal(sourceArtwork({id}).src,null);
    for(const detail of [false,true]){
      const html=artworkCover({id,title:'Uncommissioned <reference>'},{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(html.includes('is-art-fallback'));
      assert.ok(!html.includes('<img'));
    }
  }
});

test('an unillustrated future source never silently borrows another source image',()=>{
  const source={id:'unknown:future-source',title:'Future <source>',tags:['메모리·검색']};
  assert.equal(sourceArtwork(source).src,null);
  const cover=artworkCover(source);
  assert.ok(!cover.includes('<img'));
  assert.ok(!cover.includes('Future <source>'));
});
