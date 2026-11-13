import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {sourceArtwork,artworkCover} from '../src/screens/art.mjs';

const catalog=JSON.parse(await readFile(new URL('../data/catalog.json',import.meta.url),'utf8'));
const manifest=JSON.parse(await readFile(new URL('../docs/card-artwork-unique-prompts.json',import.meta.url),'utf8'));
const completedArtwork=[
  ['url:https://code.claude.com/docs/en/skills',138],
  ['url:https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2',139],
  ['url:https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3',140],
  ['url:https://www.unicode.org/reports/tr15/tr15-58.html',141],
  ['url:https://yaml.org/spec/1.2.2',142],
  ['arxiv:2611.09807',143],
  ['arxiv:2611.09662',144],
  ['arxiv:2611.09721',145],
  ['arxiv:2502.05167',146],
  ['arxiv:2404.06654',147],
  ['arxiv:2411.06037',148],
  ['github:nvidia/ruler',149]
];

test('all twelve formerly unillustrated references render their own exact card and detail images',()=>{
  for(const [id,index] of completedArtwork){
    const source=catalog.sources.find(source=>source.id===id);
    assert.ok(source,`Missing catalog source: ${id}`);
    const output=`media/cards/card-${index}${index===149?'-v2':''}.webp`;
    const expected=new URL(`../${output}`,import.meta.url).href;
    assert.equal(sourceArtwork(source).src,expected,`Missing dedicated artwork: ${id}`);
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.equal(record.index,index);
    assert.equal(record.output,output);
    if(index===149) assert.ok(record.refinementPrompts?.length,'The refined RULER artwork retains its exact edit prompt');
    assert.deepEqual(record.dimensions,[960,640]);
    const citations=source.uses.flatMap(use=>use.evidence.map(row=>row.url));
    assert.deepEqual(record.evidenceUrls,citations);
    assert.deepEqual(record.currentEvidenceUrls,citations);
    assert.deepEqual(record.generationEvidenceUrls,citations);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(`src="${expected}"`));
    }
  }
});
const newlyCommissioned=new Set([
  'url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai',
  'github:madthanu/alice','github:treeverse/dvc','arxiv:2407.12784','github:ai-secure/agentpoison'
]);
const sxc021Commissioned=new Set([
  'github:datacontract/datacontract-cli',
  'github:bitol-io/open-data-contract-standard',
  'github:pganalyze/libpg_query',
  'github:lelit/pglast',
  'arxiv:2504.12058',
  'github:pierresenellart/provenance-lean'
]);
const newReleaseCommissioned=new Set([
  "url:https://code.claude.com/docs/en/hooks",
  "url:https://code.claude.com/docs/en/plugins/cli-reference",
  "url:https://code.claude.com/docs/en/worktrees",
  "url:https://factory.com/news/evaluating-compression",
  "arxiv:2610.31778",
  "arxiv:2607.20972",
  "arxiv:2607.19865",
  "arxiv:2606.22528",
  "url:https://papers.voltropy.com/LCM",
  "arxiv:2610.30571",
  "github:gastownhall/beads",
  "github:phenomnomnominal/betterer",
  "github:logpai/drain3",
  "github:joeblackwaslike/lessons-learned",
  "github:martian-engineering/lossless-claw",
  "github:manuelschipper/nah",
  "github:prometheus/prometheus",
  "url:https://manpages.debian.org/unstable/reprotest/reprotest.1.en.html",
  "github:sourcegraph/sourcegraph-public-snapshot",
  "github:wenjing95/stale-docs-data",
  "github:python-trio/trio",
  "github:sourcegraph/zoekt"
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
    assert.ok(asset.generationEvidenceUrls.length);
    assert.deepEqual(asset.currentEvidenceUrls,asset.evidenceUrls);
  }
  assert.equal(new Set(hashes).size,manifest.assets.length);
});

test('every current catalog source has its own commissioned image in card and detail views',()=>{
  const expectedCount=catalog.snapshots['semantic-crosscheck'].version==='v0.24.0'?153:149;
  assert.equal(manifest.count,expectedCount);
  const images=[];
  for(const source of catalog.sources){
    const art=sourceArtwork(source);
    assert.ok(art.src,`Missing commissioned artwork: ${source.id}`);
    images.push(art.src);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(!html.includes('is-art-fallback'),`Fallback rendered for ${source.id}`);
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(art.src));
    }
  }
  assert.equal(new Set(images).size,images.length,'Different cards must not share topic artwork');
  assert.equal(images.length,manifest.assets.length);
  assert.equal(images.length,catalog.sources.length);
});

test('the v0.24 catalog publishes four distinct source-specific raster assignments together',()=>{
  const ids=[
    'github:stryker-mutator/stryker-js',
    'github:stryker-mutator/mutation-testing-elements',
    'arxiv:2004.00481',
    'github:georgia-tech-db/spes'
  ];
  const published=catalog.snapshots['semantic-crosscheck'].version==='v0.24.0';
  for(const id of ids){
    const source=catalog.sources.find(source=>source.id===id);
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    if(!published){
      assert.equal(source,undefined,'An unreleased snapshot must not invent a public source use');
      assert.equal(record,undefined,'Artwork assignment is pending the actual public source citation');
      continue;
    }
    assert.ok(source,`Missing v0.24 source ${id}`);
    assert.ok(record,`Missing separately commissioned image ${id}`);
    assert.match(record.output,/\.webp$/);
    assert.equal(sourceArtwork(source).src,new URL(`../${record.output}`,import.meta.url).href);
    assert.deepEqual(record.currentEvidenceUrls,source.uses.flatMap(use=>use.evidence.map(row=>row.url)));
    assert.ok(record.generationEvidenceUrls.length);
  }
});

test('the original 137 commissioned images retain their generation records and binary identities',()=>{
  const generationRecords=manifest.assets.slice(0,137).map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  const digest=createHash('sha256').update(JSON.stringify(generationRecords)).digest('hex');
  assert.equal(digest,'97ffb3dbe6005aa2d0c45c3e8e2741ae1b49217fafadbf7ff50044293455539b');
});

test('each v0.21.1 reference renders its own exact commissioned card and detail image',()=>{
  const expectedCards=[
    ['github:datacontract/datacontract-cli','132'],
    ['github:bitol-io/open-data-contract-standard','133'],
    ['github:pganalyze/libpg_query','134'],
    ['github:lelit/pglast','135'],
    ['arxiv:2504.12058','136'],
    ['github:pierresenellart/provenance-lean','137']
  ];
  assert.equal(sxc021Commissioned.size,6);
  for(const [id,index] of expectedCards){
    assert.ok(sxc021Commissioned.has(id));
    const source=catalog.sources.find(source=>source.id===id);
    assert.ok(source);
    const expected=new URL(`../media/cards/card-${index}.webp`,import.meta.url).href;
    assert.equal(sourceArtwork({id}).src,expected);
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.equal(record.output,`media/cards/card-${index}.webp`);
    assert.deepEqual(record.dimensions,[960,640]);
    const citations=source.uses.flatMap(use=>use.evidence.map(row=>row.url));
    assert.deepEqual(record.evidenceUrls,citations);
    assert.deepEqual(record.currentEvidenceUrls,citations);
    // The original 137-record hash above protects these exact generation URLs.
    // Current evidence can be repinned without rewriting how an image was made.
    assert.ok(record.generationEvidenceUrls.length);
    for(const detail of [false,true]){
      const html=artworkCover({id,title:'Commissioned <reference>'},{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(`src="${expected}"`));
    }
  }
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

test('each commissioned v0.43.0 reference renders its dedicated card and detail image',()=>{
  assert.equal(newReleaseCommissioned.size,22);
  const urls=new Set();
  for(const id of newReleaseCommissioned){
    assert.ok(catalog.sources.some(source=>source.id===id),`Unknown listed source: ${id}`);
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
  assert.equal(urls.size,22);
});

test('an unillustrated future source never silently borrows another source image',()=>{
  const source={id:'unknown:future-source',title:'Future <source>',tags:['메모리·검색']};
  assert.equal(sourceArtwork(source).src,null);
  const cover=artworkCover(source);
  assert.ok(!cover.includes('<img'));
  assert.ok(!cover.includes('Future <source>'));
});
