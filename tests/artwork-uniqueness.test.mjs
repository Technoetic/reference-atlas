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
const avCatalogVersion=catalog.snapshots['agentic-vault'].version;
// The four v0.50.0 references now have separately commissioned artwork as well.
const completedAv050Artwork=[
  ['url:https://www.youtube.com/watch?v=iysCcCRKZA4',169,'agent-scale-git-video'],
  ['url:https://github.blog/engineering/infrastructure/inside-githubs-new-git-storage-architecture',170,'github-rubicon'],
  ['url:https://www.anthropic.com/research/redesigning-source-control',171,'anthropic-scion'],
  ['url:https://openai.com/index/scaling-git-at-openai',172,'openai-pando']
];
const completedReleaseArtwork=[
  ['url:https://antigravity.google/docs/cli/commands/permissions',154],
  ['url:https://antigravity.google/docs/build-plugins',155],
  ['url:https://antigravity.google/docs/cli/reference',156],
  ['url:https://antigravity.google/docs/customization-discovery',157],
  ['url:https://antigravity.google/docs/faq',158],
  ['url:https://antigravity.google/docs/hooks',159],
  ['url:https://antigravity.google/docs/permissions',160],
  ['url:https://antigravity.google/docs/plugins',161],
  ['url:https://antigravity.google/docs/rules',162],
  ['url:https://antigravity.google/docs/settings',163],
  ['url:https://antigravity.google/docs/skills',164],
  ['github:google-antigravity/antigravity-cli',165],
  ['github:obra/superpowers',166],
  ['github:q00/ouroboros',167],
  ['github:tw93/waza',168]
];
const pinnedFile=url=>url.replace(new RegExp('/blob/[0-9a-f]{40}/'),'/blob/<commit>/').replace(new RegExp('#L[0-9]+$'),'');
const sxcCatalogVersion=catalog.snapshots['semantic-crosscheck'].version;
// Sources first cited by semantic-crosscheck v0.27.0, with their kinds; they use the text fallback until
// artwork is commissioned.
const sxc027TextFallbacks=new Map([
  ['url:https://www.postgresql.org/list/pgsql-hackers/since/202607270000','article'],
  ['url:https://peps.python.org/pep-0664','article'],
  ['url:https://www.postgresql.org/support/versioning','article'],
  ['url:https://adoptium.net/support','article'],
  ['github:nodejs/release','project'],
  ['url:https://diataxis.fr/','article']
]);
const declaredSxc027TextFallback=source=>sxc027TextFallbacks.has(source.id)&&!sourceArtwork(source).src;
// Sources first cited by agentic-vault v0.51.0; they use the text fallback until artwork is commissioned.
const av051TextFallbacks=new Set([
  'url:https://bizrouter.ai/docs/decisions',
  'url:https://artificialanalysis.ai/evaluations/decision-index'
]);
const declaredAv051TextFallback=source=>av051TextFallbacks.has(source.id)&&!sourceArtwork(source).src;
const declaredAnyTextFallback=source=>declaredSxc027TextFallback(source)||declaredAv051TextFallback(source);

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
    if(avCatalogVersion==='v0.47.0') assert.deepEqual(record.generationEvidenceUrls,citations);
    else assert.deepEqual(record.generationEvidenceUrls.map(pinnedFile),citations.map(pinnedFile));
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
  assert.equal(new Set(manifest.assets.map(asset=>asset.output)).size,manifest.assets.length);
  assert.equal(new Set(manifest.assets.map(asset=>asset.prompt)).size,manifest.assets.length);
  assert.equal(new Set(manifest.assets.map(asset=>asset.factualConcept)).size,manifest.assets.length);
  const hashes=[];
  for(const asset of manifest.assets){
    const source=catalog.sources.find(source=>source.id===asset.sourceId);
    assert.ok(source,`Unknown artwork source: ${asset.sourceId}`);
    const expected=new URL(`../${asset.output}`,import.meta.url);
    assert.equal(sourceArtwork({id:asset.sourceId}).src,expected.href);
    const bytes=await readFile(expected),digest=createHash('sha256').update(bytes).digest('hex');
    assert.equal(digest,asset.sha256);
    assert.equal(bytes.length,asset.bytes);
    assert.ok(asset.prompt.trim());
    hashes.push(digest);
    assert.ok(asset.generationEvidenceUrls.length);
    assert.deepEqual(asset.currentEvidenceUrls,asset.evidenceUrls);
    assert.deepEqual(asset.currentEvidenceUrls,source.uses.flatMap(use=>use.evidence.map(row=>row.url)));
  }
  assert.equal(new Set(hashes).size,manifest.assets.length);
});

test('all 172 commissioned catalog sources have their own image in card and detail views',()=>{
  assert.equal(manifest.count,172);
  assert.equal(catalog.sources.filter(source=>!declaredAnyTextFallback(source)).length,172);
  const images=[];
  for(const source of catalog.sources){
    if(declaredAnyTextFallback(source)) continue;
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
  assert.equal(images.length+catalog.sources.filter(declaredAnyTextFallback).length,catalog.sources.length);
});

test('the four formerly uncommissioned v0.50.0 sources render their exact separate images and only declared sxc027/av051 sources use text fallback',()=>{
  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);
  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)&&!av051TextFallbacks.has(id)),[]);
  if(avCatalogVersion==='v0.50.0') assert.deepEqual(fallbacks.filter(id=>av051TextFallbacks.has(id)),[]);
  for(const id of fallbacks.filter(id=>av051TextFallbacks.has(id))){
    const source=catalog.sources.find(source=>source.id===id);
    assert.equal(source.kind,'article');
    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(html.includes('is-art-fallback'));
      assert.ok(!html.includes('<img data-source-artwork'));
    }
  }
  for(const [id,index,slug] of completedAv050Artwork){
    const source=catalog.sources.find(source=>source.id===id);
    assert.equal(source.kind,'article');
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.equal(record.index,index);
    assert.equal(record.output,`media/cards/card-${index}-${slug}.webp`);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(sourceArtwork(source).src));
    }
  }
});

test('the fifteen formerly unillustrated v0.48 and v0.49 sources render their exact separately commissioned images',()=>{
  const records=manifest.assets.slice(153,168);
  assert.deepEqual(records.map(asset=>[asset.sourceId,asset.index]),completedReleaseArtwork);
  assert.equal(new Set(records.map(asset=>asset.prompt)).size,15);
  assert.equal(new Set(records.map(asset=>asset.factualConcept)).size,15);
  for(const [id,index] of completedReleaseArtwork){
    const source=catalog.sources.find(source=>source.id===id);
    assert.ok(source,`Missing catalog source: ${id}`);
    assert.equal(source.kind,id.startsWith('url:')?'article':'project');
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.ok(record,`Missing commissioned artwork: ${id}`);
    assert.equal(record.index,index);
    assert.match(record.output,new RegExp(`^media/cards/card-${index}-[a-z0-9-]+\\.webp$`));
    assert.deepEqual(record.dimensions,[960,640]);
    assert.ok(record.prompt.trim());
    assert.ok(record.factualConcept.trim());
    assert.ok(record.generationEvidenceUrls.length);
    const citations=source.uses.flatMap(use=>use.evidence.map(row=>row.url));
    assert.deepEqual(record.evidenceUrls,citations);
    assert.deepEqual(record.currentEvidenceUrls,citations);
    const expected=new URL(`../${record.output}`,import.meta.url).href;
    assert.equal(sourceArtwork(source).src,expected);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(`src="${expected}"`));
    }
  }
});

test('the v0.24 catalog publishes four distinct source-specific raster assignments together',()=>{
  const ids=[
    'github:stryker-mutator/stryker-js',
    'github:stryker-mutator/mutation-testing-elements',
    'arxiv:2004.00481',
    'github:georgia-tech-db/spes'
  ];
  const published=['v0.24.0','v0.27.0'].includes(catalog.snapshots['semantic-crosscheck'].version);
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

test('the twelve images commissioned at agentic-vault v0.47.0 keep their generation records when citations move',()=>{
  const generationRecords=manifest.assets.slice(137,149).map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  assert.deepEqual(generationRecords.map(record=>[record.sourceId,record.index]),completedArtwork);
  const digest=createHash('sha256').update(JSON.stringify(generationRecords)).digest('hex');
  assert.equal(digest,'28d76e85647acd97c35566b48bb66d664b3a38175314f73aa60cfb7537cc5da8');
});

test('all original 153 images retain their immutable generation records when the next fifteen are commissioned',()=>{
  const generationRecords=manifest.assets.slice(0,153).map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  assert.equal(generationRecords.length,153);
  const digest=createHash('sha256').update(JSON.stringify(generationRecords)).digest('hex');
  assert.equal(digest,'290310e9b78b760862ac224e5a3b01b26eb505dcb75f35a93b32119db335f71c');
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
  for(const detail of [false,true]){
    const cover=artworkCover(source,{detail});
    assert.ok(cover.includes(detail?'detail-art':'source-art'));
    assert.ok(cover.includes('is-art-fallback'));
    assert.ok(!cover.includes('<img'));
    assert.ok(!cover.includes('Future <source>'));
  }
});

test('only the declared semantic-crosscheck v0.27.0 and agentic-vault v0.51.0 sources render the uncommissioned text fallback',()=>{
  const fallbacks=catalog.sources.filter(source=>!sourceArtwork(source).src).map(source=>source.id);
  assert.deepEqual(fallbacks.filter(id=>!sxc027TextFallbacks.has(id)&&!av051TextFallbacks.has(id)),[]);
  if(sxcCatalogVersion==='v0.24.0'&&avCatalogVersion==='v0.50.0') assert.deepEqual(fallbacks,[]);
  if(sxcCatalogVersion==='v0.27.0') for(const id of sxc027TextFallbacks.keys())
    assert.ok(catalog.sources.some(source=>source.id===id),`Missing catalog source: ${id}`);
  for(const id of fallbacks){
    const source=catalog.sources.find(source=>source.id===id);
    assert.equal(source.kind,sxc027TextFallbacks.get(id)||'article');
    assert.equal(manifest.assets.find(asset=>asset.sourceId===id),undefined);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(html.includes('is-art-fallback'));
      assert.ok(!html.includes('<img data-source-artwork'));
    }
  }
});
