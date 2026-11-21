import {createHash} from 'node:crypto';
import {readFile,writeFile,readdir,mkdir,rm,rename,lstat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {calculateBuildIdentity} from './build-identity.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dist=path.join(root,'dist'),stage=path.join(root,'.build-temp');
function owned(target){const rel=path.relative(root,path.resolve(target));if(!rel||rel.startsWith('..')||path.isAbsolute(rel))throw new Error('Unsafe build path');}
owned(dist);owned(stage);
const sha=data=>createHash('sha256').update(data).digest('hex');
async function files(dir,{media=false}={}){const result=[];for(const entry of await readdir(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(media&&entry.isSymbolicLink())throw new Error('Symbolic links are not allowed in media');if(entry.isDirectory())result.push(...await files(full,{media}));else result.push(full);}return result;}
async function rasterFiles(){const dir=path.join(root,'media');let info;try{info=await lstat(dir);}catch(error){if(error.code==='ENOENT')return [];throw error;}if(info.isSymbolicLink())throw new Error('Symbolic links are not allowed in media');if(!info.isDirectory())throw new Error('Media must be a directory');return(await files(dir,{media:true})).filter(file=>/\.(webp|png)$/i.test(file)).sort();}
const sources=[...(await files(path.join(root,'src'))).filter(file=>file.endsWith('.mjs')&&!file.endsWith('.test.mjs')), ...(await files(path.join(root,'styles'))).filter(file=>file.endsWith('.css'))].sort();
const html=(await readFile(path.join(root,'index.html'),'utf8')).replace(/\r\n?/g,'\n');
const contents=new Map(await Promise.all(sources.map(async file=>[file,(await readFile(file,'utf8')).replace(/\r\n?/g,'\n')])));
const images=new Map(await Promise.all((await rasterFiles()).map(async file=>{if((await lstat(file)).size>2*1024*1024)throw new Error('Raster asset exceeds 2 MiB');const bytes=await readFile(file);if(bytes.length>2*1024*1024)throw new Error('Raster asset exceeds 2 MiB');return[file,bytes];})));
const buildId=calculateBuildIdentity(html,[...[...contents].map(([file,text])=>[path.relative(root,file),text]),...[...images].map(([file,bytes])=>[path.relative(root,file),sha(bytes)])]);
const assetPath=file=>'assets/'+path.relative(root,file).replaceAll(path.sep,'/').replace(/\.(mjs|css|webp|png)$/i,`.${buildId}.$1`);
const paths=new Map([...sources,...images.keys()].map(file=>[file,assetPath(file)]));
function rewrite(file,text){
  const remap=specifier=>{
    if(!specifier.startsWith('.'))return specifier;
    const target=path.resolve(path.dirname(file),specifier);
    if(!paths.has(target))throw new Error(`Missing imported asset ${specifier}`);
    let relative=path.posix.relative(path.posix.dirname(paths.get(file)),paths.get(target));
    if(!relative.startsWith('.'))relative='./'+relative;return relative;
  };
  if(file.endsWith('.mjs'))return text.replace(/(from\s+['"]|import\s*['"]|import\(\s*['"])(\.{1,2}\/[^'"]+)(['"])/g,(_all,a,b,c)=>a+remap(b)+c).replace(/(new\s+URL\s*\(\s*['"])(\.{1,2}\/[^'"]+)(['"]\s*,\s*import\.meta\.url\s*\))/g,(_all,a,b,c)=>a+remap(b)+c);
  return text.replace(/(@import\s+['"])([^'"]+)(['"])/g,(_all,a,b,c)=>a+remap(b)+c);
}
await rm(stage,{recursive:true,force:true});await mkdir(stage,{recursive:true});
const currentAssets=[];
for(const[file,text]of contents){const rel=paths.get(file),target=path.join(stage,rel);owned(target);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,rewrite(file,text));currentAssets.push(rel);}
for(const[file,bytes]of images){const rel=paths.get(file),target=path.join(stage,rel);owned(target);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,bytes);currentAssets.push(rel);}
let output=html.replaceAll('__BUILD_ID__',buildId);
for(const[original,built]of paths)output=output.replaceAll('./'+path.relative(root,original).replaceAll(path.sep,'/'),'./'+built);
await writeFile(path.join(stage,'index.html'),output);
const faviconHref="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%2310130f'/%3E%3Ccircle cx='32' cy='32' r='22' fill='none' stroke='%23d3fc70' stroke-width='3'/%3E%3Ctext x='20' y='44' font-family='Arial,sans-serif' font-size='34' font-weight='800' fill='%23f4f5ed'%3Er%3C/text%3E%3Ctext x='36' y='26' font-family='Arial,sans-serif' font-size='18' font-weight='800' fill='%23d3fc70'%3E%E2%86%97%3C/text%3E%3C/svg%3E";
const notFoundHtml=`<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#10130f">
  <link rel="icon" type="image/svg+xml" href="${faviconHref}">
  <title>404 · Reference Atlas</title>
  <style>
    :root{color-scheme:dark}
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;display:grid;place-items:center;padding:32px 20px;background:#10130f;color:#f4f5ed;font-family:Arial,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
    main{max-width:560px;width:100%;padding:36px 28px;border:1px solid rgba(225,234,214,.18);border-radius:18px;background:#171c16}
    .eyebrow{margin:0 0 14px;font-family:"Courier New",monospace;font-size:12px;font-weight:700;letter-spacing:.14em;color:#9ba294}
    h1{margin:0;font-size:clamp(28px,6vw,42px);line-height:1.2;letter-spacing:-.04em}
    p{margin:16px 0 28px;font-size:14px;line-height:1.75;color:#9ba294}
    a{display:inline-flex;align-items:center;gap:14px;min-height:44px;padding:12px 22px;border-radius:99px;background:#d3fc70;color:#10130f;font-size:14px;font-weight:700;text-decoration:none}
    a:hover{background:#e1ff9d}
    a:focus-visible{outline:2px solid #d3fc70;outline-offset:4px}
  </style>
</head>
<body>
  <main>
    <p class="eyebrow">404 / NOT FOUND</p>
    <h1>이 주소에는 파일이 없습니다.</h1>
    <p>요청한 경로가 존재하지 않거나 이전 배포 경로입니다. 연구 지도에서 공개 출처를 다시 탐색하세요.</p>
    <a href="/reference-atlas/">연구 지도로 돌아가기 <span aria-hidden="true">↗</span></a>
  </main>
</body>
</html>
`;
await writeFile(path.join(stage,'404.html'),notFoundHtml);
await writeFile(path.join(stage,'.nojekyll'),'');
await mkdir(path.join(stage,'data'),{recursive:true});
for(const name of ['catalog.json','catalog.csv'])await writeFile(path.join(stage,'data',name),await readFile(path.join(root,'data',name)));
await writeFile(path.join(stage,'version.json'),JSON.stringify({buildId})+'\n');

// Keep one previous complete asset graph, so a cached entry HTML can still load.
const MAX_RETAINED_ASSETS=2048;
let previous=null,remote=false;
if(process.env.RETAIN_BASE_URL){
  const base=new URL(process.env.RETAIN_BASE_URL);
  if(base.protocol!=='https:'||base.hostname!=='technoetic.github.io'||base.pathname!=='/reference-atlas/')throw new Error('Untrusted retention origin');
  const response=await fetch(new URL('deployment-manifest.json?at='+Date.now(),base),{signal:AbortSignal.timeout(15000)});
  if(response.ok){const raw=await response.text();if(raw.length>4*1024*1024)throw new Error('Oversize retention manifest');previous=JSON.parse(raw);remote=true;}
  else if(response.status!==404)throw new Error('Could not verify previous deployment');
}else{try{previous=JSON.parse(await readFile(path.join(dist,'deployment-manifest.json'),'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}}
const retainedAssets=[];
if(previous){
  if(!Array.isArray(previous.currentAssets)||previous.currentAssets.length>MAX_RETAINED_ASSETS||!previous.files)throw new Error('Invalid retention manifest');
  for(const rel of previous.currentAssets){
    if(!/^assets\/[A-Za-z0-9_./-]+$/.test(rel)||rel.split('/').includes('..')||!previous.files[rel])throw new Error('Invalid retained path');
    if(currentAssets.includes(rel))continue;
    let bytes;
    if(remote){const response=await fetch(new URL(rel,process.env.RETAIN_BASE_URL),{signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Missing previous asset');bytes=Buffer.from(await response.arrayBuffer());}
    else bytes=await readFile(path.join(dist,rel));
    if(bytes.length>2*1024*1024||sha(bytes)!==previous.files[rel].sha256)throw new Error('Retained asset integrity mismatch');
    const target=path.join(stage,rel);owned(target);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,bytes);retainedAssets.push(rel);
  }
}
const manifest={schemaVersion:1,buildId,currentAssets,retainedAssets,files:{}};
for(const file of await files(stage)){const data=await readFile(file);manifest.files[path.relative(stage,file).replaceAll(path.sep,'/')]={sha256:sha(data),bytes:data.length};}
await writeFile(path.join(stage,'deployment-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
owned(dist);owned(stage);await rm(dist,{recursive:true,force:true});await rename(stage,dist);
console.log(JSON.stringify({status:'PASS',buildId,currentAssets:currentAssets.length,retainedAssets:retainedAssets.length,files:Object.keys(manifest.files).length}));
