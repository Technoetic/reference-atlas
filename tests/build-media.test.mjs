import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,mkdir,readFile,writeFile,copyFile,rm,symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const exec=promisify(execFile);
const project=fileURLToPath(new URL('../',import.meta.url));
const raster=Buffer.from([0x52,0x49,0x46,0x46,0xff,0,0x0d,0x0a,0x57,0x45,0x42,0x50,0x80,0xfe]);
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');

async function fixture(t){
  const root=await mkdtemp(path.join(tmpdir(),'reference-atlas-media-'));
  t.after(async()=>{
    assert.equal(path.dirname(root),path.resolve(tmpdir()));
    assert.ok(path.basename(root).startsWith('reference-atlas-media-'));
    await rm(root,{recursive:true,force:true});
  });
  for(const dir of ['scripts','src/screens','styles','data','media'])await mkdir(path.join(root,dir),{recursive:true});
  for(const file of ['build.mjs','build-identity.mjs'])await copyFile(path.join(project,'scripts',file),path.join(root,'scripts',file));
  await writeFile(path.join(root,'index.html'),'<meta name="build-id" content="__BUILD_ID__"><script type="module" src="./src/app.mjs"></script><link rel="stylesheet" href="./styles/main.css">');
  await writeFile(path.join(root,'src/app.mjs'),"export {art,pixel} from './screens/art.mjs';\n");
  await writeFile(path.join(root,'src/screens/art.mjs'),"export const art=new URL('../../media/amem.webp',import.meta.url).href;\nexport const pixel = new URL( '../../media/pixel.png', import.meta.url ).href;\n");
  await writeFile(path.join(root,'styles/main.css'),'body { margin: 0; }\n');
  await writeFile(path.join(root,'data/catalog.json'),'{}\n');
  await writeFile(path.join(root,'data/catalog.csv'),'id,title\n');
  await writeFile(path.join(root,'media/amem.webp'),raster);
  await writeFile(path.join(root,'media/pixel.png'),png);
  return root;
}
async function build(root){
  const env={...process.env};delete env.RETAIN_BASE_URL;
  await exec(process.execPath,[path.join(root,'scripts/build.mjs')],{cwd:root,env});
  return JSON.parse(await readFile(path.join(root,'dist/deployment-manifest.json'),'utf8'));
}

test('raster URLs resolve to hashed public files with original binary bytes and manifest integrity',async t=>{
  const root=await fixture(t),manifest=await build(root);
  const imagePath=`assets/media/amem.${manifest.buildId}.webp`;
  const pngPath=`assets/media/pixel.${manifest.buildId}.png`;
  assert.ok(manifest.currentAssets.includes(imagePath),'WebP must be part of the deployed current asset graph');
  assert.ok(manifest.currentAssets.includes(pngPath),'PNG must be part of the deployed current asset graph');
  const built=await import(pathToFileURL(path.join(root,`dist/assets/src/screens/art.${manifest.buildId}.mjs`)).href);
  assert.equal(fileURLToPath(built.art),path.join(root,'dist',imagePath));
  assert.equal(fileURLToPath(built.pixel),path.join(root,'dist',pngPath));
  assert.deepEqual(await readFile(fileURLToPath(built.art)),raster);
  assert.deepEqual(await readFile(fileURLToPath(built.pixel)),png);
  assert.deepEqual(manifest.files[imagePath],{sha256:hash(raster),bytes:raster.length});
  assert.deepEqual(manifest.files[pngPath],{sha256:hash(png),bytes:png.length});
});

test('an image-only update changes the build and preserves exactly the preceding image graph',async t=>{
  const root=await fixture(t),first=await build(root);
  const secondRaster=Buffer.concat([raster,Buffer.from([0x01])]);
  await writeFile(path.join(root,'media/amem.webp'),secondRaster);
  const second=await build(root);
  assert.notEqual(first.buildId,second.buildId,'Image-only changes must reach already open tabs through version identity');
  const firstPath=`assets/media/amem.${first.buildId}.webp`,secondPath=`assets/media/amem.${second.buildId}.webp`;
  assert.ok(second.retainedAssets.includes(firstPath));
  assert.deepEqual(await readFile(path.join(root,'dist',firstPath)),raster);
  assert.deepEqual(await readFile(path.join(root,'dist',secondPath)),secondRaster);
  await writeFile(path.join(root,'media/amem.webp'),Buffer.concat([secondRaster,Buffer.from([0x02])]));
  const third=await build(root);
  assert.ok(third.retainedAssets.includes(secondPath));
  assert.ok(!third.retainedAssets.includes(firstPath),'Only one previous complete graph is retained');
  await assert.rejects(readFile(path.join(root,'dist',firstPath)),{code:'ENOENT'});
  assert.deepEqual(await readFile(path.join(root,'dist',secondPath)),secondRaster);
});

test('a raster above the retention size bound is rejected before replacing the existing deployment',async t=>{
  const root=await fixture(t),before=await build(root);
  await writeFile(path.join(root,'media/amem.webp'),Buffer.alloc(2*1024*1024+1));
  await assert.rejects(build(root),/Raster asset exceeds 2 MiB/);
  assert.equal(JSON.parse(await readFile(path.join(root,'dist/version.json'),'utf8')).buildId,before.buildId);
});

test('media directory symlinks cannot bring outside files into the public asset graph',async t=>{
  const root=await fixture(t);
  await mkdir(path.join(root,'outside'));
  await writeFile(path.join(root,'outside/secret.webp'),raster);
  await symlink(path.join(root,'outside'),path.join(root,'media/external'),process.platform==='win32'?'junction':'dir');
  await assert.rejects(build(root),/Symbolic links are not allowed in media/);
});

test('one full catalog of dedicated images survives the next deployment',async t=>{
  const root=await fixture(t);
  await mkdir(path.join(root,'media/cards'));
  for(let index=1;index<=104;index++)await writeFile(path.join(root,'media/cards',`card-${index}.webp`),Buffer.concat([raster,Buffer.from(String(index))]));
  const first=await build(root);
  assert.ok(first.currentAssets.length>100);
  await writeFile(path.join(root,'src/app.mjs'),"export {art,pixel} from './screens/art.mjs';\n// next application release\n");
  const second=await build(root);
  assert.equal(second.retainedAssets.length,first.currentAssets.length);
  const retained=`assets/media/cards/card-104.${first.buildId}.webp`;
  assert.ok(second.retainedAssets.includes(retained));
  assert.deepEqual(await readFile(path.join(root,'dist',retained)),Buffer.concat([raster,Buffer.from('104')]));
});
