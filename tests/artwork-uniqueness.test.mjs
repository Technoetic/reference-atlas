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
const releasedFile=url=>pinnedFile(url).replace('/blob/<commit>/docs/releases/v0.52.0.md','/blob/<commit>/docs/releases/v0.52.1.md');
const completedLatestArtwork=[
  ['url:https://artificialanalysis.ai/evaluations/decision-index',173,'decision-index'],
  ['url:https://bizrouter.ai/docs/decisions',174,'bizrouter-decisions'],
  ['url:https://diataxis.fr/',175,'diataxis'],
  ['url:https://peps.python.org/pep-0664',176,'python-lifecycle'],
  ['url:https://www.postgresql.org/support/versioning',177,'postgresql-support'],
  ['url:https://adoptium.net/support',178,'temurin-support'],
  ['url:https://www.postgresql.org/list/pgsql-hackers/since/202607270000',179,'dst-order'],
  ['github:nodejs/release',180,'node-release']
];
// The ten remaining sources now have independently generated, source-specific artwork.
const completedCurrentArtwork=[
  ['url:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets',181,'rulesets','article','SCOPED RULE ARCHITECTURE'],
  ['url:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets',182,'rule-options','article','CONFIGURABLE RULE MECHANISMS'],
  ['url:https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository',183,'private-reporting','article','PRIVATE DISCLOSURE CHANNEL'],
  ['url:https://docs.jj-vcs.dev/latest/guides/divergence',184,'divergent-changes','article','COEXISTING DIVERGENT CHANGES'],
  ['url:https://slsa.dev/spec/v1.2/source-requirements',185,'slsa-source','article','SOURCE PROVENANCE REQUIREMENTS'],
  ['arxiv:2407.02348',186,'agreement-cascade','paper','AGREEMENT-GATED CASCADE'],
  ['arxiv:2403.14720',187,'spotlighting','paper','MARKED UNTRUSTED INPUT'],
  ['doi:10.1145/3654991',188,'query-plans','paper','DIFFERENTIAL QUERY ROUTES'],
  ['arxiv:2607.10139',189,'model-jury','paper','CROSS-MODEL JURY'],
  ['arxiv:2510.09023',190,'adaptive-attacks','paper','ADAPTIVE BOUNDARY PROBE']
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
  assert.equal(new Set(manifest.assets.map(asset=>asset.label)).size,manifest.assets.length);
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

test('commissioned sources have dedicated images and uncommissioned records use text covers',()=>{
  const uncommissioned=new Set([
    'doi:10.1186/1471-2288-13-91',
    'doi:10.1002/(sici)1097-0258(19981130)17:22<2635::aid-sim954>3.0.co;2-c',
    'doi:10.1162/089976698300017197',
    'doi:10.1002/stvr.1486',
    'doi:10.1145/3243734.3243804',
    'github:astral-sh/ruff',
    'github:astral-sh/ty',
    'github:quarylabs/sqruff'
  ]);
  for(const id of uncommissioned){
    assert.ok(catalog.sources.some(source=>source.id===id),`Missing uncommissioned source: ${id}`);
  }
  assert.equal(manifest.count,catalog.sources.length-uncommissioned.size);
  const images=[];
  for(const source of catalog.sources){
    const art=sourceArtwork(source);
    if(uncommissioned.has(source.id)){
      assert.equal(art.src,null);
      for(const detail of [false,true]){
        const html=artworkCover(source,{detail});
        assert.ok(html.includes('is-art-fallback'),`Expected text cover for ${source.id}`);
        assert.ok(!html.includes('<img'));
      }
      continue;
    }
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
});

test('the four formerly uncommissioned v0.50.0 sources render their exact separate images',()=>{
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
  const published=['v0.24.0','v0.27.0','v0.28.0','v0.29.0','v0.30.0','v0.31.0'].includes(catalog.snapshots['semantic-crosscheck'].version);
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

test('all original 172 images retain their immutable records when the next eight are commissioned',()=>{
  const generationRecords=manifest.assets.slice(0,153).map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  assert.equal(generationRecords.length,153);
  const digest=createHash('sha256').update(JSON.stringify(generationRecords)).digest('hex');
  assert.equal(digest,'290310e9b78b760862ac224e5a3b01b26eb505dcb75f35a93b32119db335f71c');
  const originalRecords=manifest.assets.slice(0,172);
  assert.equal(originalRecords.length,172);
  // The full records hold the current evidence URLs, which follow the agentic-vault rows when a release repins them.
  if(avCatalogVersion==='v0.51.0') assert.equal(createHash('sha256').update(JSON.stringify(originalRecords)).digest('hex'),'cd4937c7f636bd80c50a2a4ebe7f553884fc0aabff586fee82ac51bd0465df1b');
  const immutableRecords=originalRecords.map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  assert.equal(createHash('sha256').update(JSON.stringify(immutableRecords)).digest('hex'),'8cfd6cc21d1b8233cec30417cd5a43fe92646d793ec0ba19ddf4dcdd389285d4');
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

test('the five v0.53.0 covers retain the source and delivery provenance of each independent commission',()=>{
  const expected=[
    ['doi:10.18653/v1/d19-1382','paws-x','https://aclanthology.org/D19-1382/'],
    ['arxiv:2611.02017','switch-swe-paper','https://arxiv.org/abs/2611.02017'],
    ['github:google-research-datasets/paws','paws-dataset','https://github.com/google-research-datasets/paws'],
    ['github:miraclecsc/switch-swe','switch-swe-project','https://github.com/Miraclecsc/Switch-SWE'],
    ['github:simplistix/sybil','sybil','https://github.com/simplistix/sybil']
  ];
  const records=manifest.assets.slice(190,195);
  assert.equal(records.length,expected.length);
  assert.equal(new Set(records.map(record=>record.delivery.sourceSha256)).size,expected.length);
  for(const [offset,record] of records.entries()){
    const [id,slug,referenceUrl]=expected[offset];
    assert.equal(record.sourceId,id);
    const source=catalog.sources.find(item=>item.id===record.sourceId);
    assert.equal(record.index,191+offset);
    assert.equal(record.kind,source.kind);
    assert.equal(record.title,source.title);
    assert.equal(sourceArtwork(source).label,record.label);
    assert.equal(record.output,`media/cards/card-${record.index}-${slug}.webp`);
    assert.deepEqual(record.dimensions,[960,640]);
    assert.match(record.delivery.sourceSha256,/^[0-9a-f]{64}$/);
    assert.ok(record.generationReferenceUrls.includes(referenceUrl));
    if(avCatalogVersion==='v0.53.0') assert.deepEqual(record.generationEvidenceUrls,record.currentEvidenceUrls);
  }
});

test('the ten formerly unillustrated v0.52.0 and v0.28.0 references render their exact commissioned card and detail images',()=>{
  const records=manifest.assets.slice(180,190);
  assert.deepEqual(records.map(asset=>[asset.sourceId,asset.index,asset.output,asset.kind,asset.label]),
    completedCurrentArtwork.map(([id,index,slug,kind,label])=>[id,index,`media/cards/card-${index}-${slug}.webp`,kind,label]));
  for(const [id,index,slug,kind,label] of completedCurrentArtwork){
    const source=catalog.sources.find(source=>source.id===id);
    assert.ok(source,`Missing catalog source: ${id}`);
    assert.equal(source.kind,kind);
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.ok(record,`Missing commissioned artwork: ${id}`);
    const expected=new URL(`../media/cards/card-${index}-${slug}.webp`,import.meta.url).href;
    assert.equal(sourceArtwork(source).src,expected);
    assert.equal(sourceArtwork(source).label,label);
    assert.deepEqual(record.dimensions,[960,640]);
    assert.ok(record.factualConcept.trim());
    assert.ok(record.prompt.trim());
    const citations=source.uses.flatMap(use=>use.evidence.map(row=>row.url));
    assert.deepEqual(record.evidenceUrls,citations);
    assert.deepEqual(record.currentEvidenceUrls,citations);
    const avCitations=source.uses.filter(use=>use.plugin==='agentic-vault').flatMap(use=>use.evidence.map(row=>row.url));
    const baseCitations=id.includes('about-rulesets')?avCitations:citations;
    if(avCatalogVersion==='v0.52.0') assert.deepEqual(record.generationEvidenceUrls,baseCitations);
    else assert.deepEqual(record.generationEvidenceUrls.map(releasedFile),baseCitations.map(releasedFile));
    assert.deepEqual(record.delivery.sourceDimensions,[1536,1024]);
    assert.match(record.delivery.sourceSha256,/^[0-9a-f]{64}$/);
    assert.equal(record.delivery.quality,90);
    assert.equal(record.delivery.compressionLevel,6);
    assert.match(record.delivery.commandTemplate,/scale=960:640:flags=lanczos/);
    for(const detail of [false,true]){
      const html=artworkCover(source,{detail});
      assert.ok(html.includes(detail?'detail-art':'source-art'));
      assert.ok(!html.includes('is-art-fallback'));
      assert.ok(html.includes('<img data-source-artwork'));
      assert.ok(html.includes(`src="${expected}"`));
    }
  }
});

test('ECC and the connectome benchmark have their assigned artwork and generation evidence',()=>{
  const projects = [
    [196, 'github:affaan-m/ecc', 'ecc', 'HOOK WIRING'],
    [197, 'doi:10.5281/zenodo.24361690', 'connectome-folds', 'PAIRED FOLD RESULTS']
  ];
  const originalHashes = new Set();
  for (const [index, id, slug, label] of projects) {
    const source = catalog.sources.find(item => item.id === id);
    const record = manifest.assets.find(asset => asset.sourceId === id);
    assert.ok(record, `Missing artwork for ${id}`);
    assert.equal(record.index, index);
    assert.equal(record.kind, 'project');
    assert.equal(record.title, source.title);
    assert.equal(record.label, label);
    assert.equal(sourceArtwork(source).label, label);
    assert.equal(record.output, `media/cards/card-${index}-${slug}.webp`);
    assert.deepEqual(record.dimensions, [960, 640]);
    assert.match(record.delivery.sourceSha256, /^[0-9a-f]{64}$/);
    originalHashes.add(record.delivery.sourceSha256);
    if (avCatalogVersion === 'v0.54.0' && catalog.snapshots['semantic-crosscheck'].version === 'v0.30.0') {
      assert.deepEqual(record.generationEvidenceUrls, record.currentEvidenceUrls);
    }
  }
  assert.equal(originalHashes.size, projects.length);
});

test('the first 195 commissioned covers retain their immutable generation records',()=>{
  const records=manifest.assets.slice(0,195).map(asset=>Object.fromEntries(
    Object.entries(asset).filter(([key])=>!['evidenceUrls','currentEvidenceUrls'].includes(key))
  ));
  assert.equal(createHash('sha256').update(JSON.stringify(records)).digest('hex'),
    '653e968e8acad6396d15d1bb2163a3d33da7a12c6c124ea19fca3a9ec45f5893');
});

test('the new artwork preserves all first 180 generation records at the current citation snapshot',()=>{
  if(avCatalogVersion!=='v0.52.0'||catalog.snapshots['semantic-crosscheck'].version!=='v0.28.0') return;
  assert.equal(createHash('sha256').update(JSON.stringify(manifest.assets.slice(0,180))).digest('hex'),
    '22138e438e0758335e8466deabb9bbb3508d51559c43d1e0f0e98d21fca22680');
});

test('the eight formerly unillustrated v0.27.0 and v0.51.0 references render their exact commissioned card and detail images',()=>{
  const records=manifest.assets.slice(172,180);
  assert.deepEqual(records.map(asset=>[asset.sourceId,asset.index,asset.output]),completedLatestArtwork.map(([id,index,slug])=>[id,index,`media/cards/card-${index}-${slug}.webp`]));
  for(const [id,index,slug] of completedLatestArtwork){
    const source=catalog.sources.find(source=>source.id===id);
    assert.ok(source,`Missing catalog source: ${id}`);
    assert.equal(source.kind,id.startsWith('url:')?'article':'project');
    const expected=new URL(`../media/cards/card-${index}-${slug}.webp`,import.meta.url).href;
    assert.equal(sourceArtwork(source).src,expected,`Missing dedicated artwork: ${id}`);
    const record=manifest.assets.find(asset=>asset.sourceId===id);
    assert.ok(record,`Missing commissioned artwork: ${id}`);
    assert.deepEqual(record.dimensions,[960,640]);
    assert.ok(record.factualConcept.trim());
    const citations=source.uses.flatMap(use=>use.evidence.map(row=>row.url));
    assert.deepEqual(record.evidenceUrls,citations);
    assert.deepEqual(record.currentEvidenceUrls,citations);
    // Generation records keep the citations the image was made from; agentic-vault rows move with each release.
    if(avCatalogVersion==='v0.51.0') assert.deepEqual(record.generationEvidenceUrls,citations);
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
