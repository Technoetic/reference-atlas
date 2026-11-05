import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {sourceArtwork,artworkCover} from '../src/screens/art.mjs';

const catalog=JSON.parse(await readFile(new URL('../data/catalog.json',import.meta.url),'utf8'));

test('every recorded source has its own dedicated artwork URL',()=>{
  const images=catalog.sources.map(source=>sourceArtwork(source).src);
  assert.ok(images.every(Boolean),'Every card needs an explicitly assigned image');
  assert.equal(new Set(images).size,catalog.sources.length,'Different cards must not share topic artwork');
});

test('dedicated card images have different actual file contents',async()=>{
  const hashes=await Promise.all(catalog.sources.map(async source=>{
    const bytes=await readFile(new URL(sourceArtwork(source).src));
    assert.equal(bytes.subarray(0,4).toString(),'RIFF');
    assert.equal(bytes.subarray(8,12).toString(),'WEBP');
    return createHash('sha256').update(bytes).digest('hex');
  }));
  assert.equal(new Set(hashes).size,catalog.sources.length,'A renamed copy of another image is still shared artwork');
});

test('an unillustrated future source never silently borrows another source image',()=>{
  const source={id:'unknown:future-source',title:'Future <source>',tags:['메모리·검색']};
  assert.equal(sourceArtwork(source).src,null);
  const cover=artworkCover(source);
  assert.ok(!cover.includes('<img'));
  assert.ok(!cover.includes('Future <source>'));
});
