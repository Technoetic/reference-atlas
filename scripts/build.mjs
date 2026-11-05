import {createHash} from 'node:crypto';
import {readFile,writeFile,readdir,mkdir,rm,rename,stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {calculateBuildIdentity} from './build-identity.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dist=path.join(root,'dist'),stage=path.join(root,'.build-temp');
function owned(target){const rel=path.relative(root,path.resolve(target));if(!rel||rel.startsWith('..')||path.isAbsolute(rel))throw new Error('Unsafe build path');}
owned(dist);owned(stage);
const sha=data=>createHash('sha256').update(data).digest('hex');
async function files(dir){const result=[];for(const entry of await readdir(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(entry.isDirectory())result.push(...await files(full));else result.push(full);}return result;}
const sources=[...(await files(path.join(root,'src'))).filter(file=>file.endsWith('.mjs')&&!file.endsWith('.test.mjs')), ...(await files(path.join(root,'styles'))).filter(file=>file.endsWith('.css'))].sort();
const html=(await readFile(path.join(root,'index.html'),'utf8')).replace(/\r\n?/g,'\n');
const contents=new Map(await Promise.all(sources.map(async file=>[file,(await readFile(file,'utf8')).replace(/\r\n?/g,'\n')])));
const buildId=calculateBuildIdentity(html,[...contents].map(([file,text])=>[path.relative(root,file),text]));
const assetPath=file=>'assets/'+path.relative(root,file).replaceAll(path.sep,'/').replace(/\.(mjs|css)$/,`.${buildId}.$1`);
const paths=new Map(sources.map(file=>[file,assetPath(file)]));
function rewrite(file,text){
  const remap=specifier=>{
    if(!specifier.startsWith('.'))return specifier;
    const target=path.resolve(path.dirname(file),specifier);
    if(!paths.has(target))throw new Error(`Missing imported asset ${specifier}`);
    let relative=path.posix.relative(path.posix.dirname(paths.get(file)),paths.get(target));
    if(!relative.startsWith('.'))relative='./'+relative;return relative;
  };
  if(file.endsWith('.mjs'))return text.replace(/(from\s+['"]|import\s*['"]|import\(\s*['"])(\.{1,2}\/[^'"]+)(['"])/g,(_all,a,b,c)=>a+remap(b)+c);
  return text.replace(/(@import\s+['"])([^'"]+)(['"])/g,(_all,a,b,c)=>a+remap(b)+c);
}
await rm(stage,{recursive:true,force:true});await mkdir(stage,{recursive:true});
const currentAssets=[];
for(const[file,text]of contents){const rel=paths.get(file),target=path.join(stage,rel);owned(target);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,rewrite(file,text));currentAssets.push(rel);}
let output=html.replaceAll('__BUILD_ID__',buildId);
for(const[original,built]of paths)output=output.replaceAll('./'+path.relative(root,original).replaceAll(path.sep,'/'),'./'+built);
await writeFile(path.join(stage,'index.html'),output);
await writeFile(path.join(stage,'404.html'),'<!doctype html><html lang="ko"><meta charset="utf-8"><title>404 · Reference Atlas</title><h1>이 주소에는 파일이 없습니다.</h1><a href="./">연구 지도로 돌아가기</a></html>');
await writeFile(path.join(stage,'.nojekyll'),'');
await mkdir(path.join(stage,'data'),{recursive:true});
for(const name of ['catalog.json','catalog.csv'])await writeFile(path.join(stage,'data',name),await readFile(path.join(root,'data',name)));
await writeFile(path.join(stage,'version.json'),JSON.stringify({buildId})+'\n');

// Keep one previous complete asset graph, so a cached entry HTML can still load.
let previous=null,remote=false;
if(process.env.RETAIN_BASE_URL){
  const base=new URL(process.env.RETAIN_BASE_URL);
  if(base.protocol!=='https:'||base.hostname!=='technoetic.github.io'||base.pathname!=='/reference-atlas/')throw new Error('Untrusted retention origin');
  const response=await fetch(new URL('deployment-manifest.json?at='+Date.now(),base),{signal:AbortSignal.timeout(15000)});
  if(response.ok){const raw=await response.text();if(raw.length>1024*1024)throw new Error('Oversize retention manifest');previous=JSON.parse(raw);remote=true;}
  else if(response.status!==404)throw new Error('Could not verify previous deployment');
}else{try{previous=JSON.parse(await readFile(path.join(dist,'deployment-manifest.json'),'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}}
const retainedAssets=[];
if(previous){
  if(!Array.isArray(previous.currentAssets)||previous.currentAssets.length>100||!previous.files)throw new Error('Invalid retention manifest');
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
