import test from 'node:test';
import assert from 'node:assert/strict';
import { VersionService } from './version.mjs';

const response = buildId => ({ ok: true, json: async () => ({ buildId }) });
const baseURL = 'https://technoetic.github.io/reference-atlas/?view=atlas';

test('loaded identity stays A until a clean target navigation receives B', async () => {
  const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', fetcher: async () => response('B'), navigate: url => navigations.push(url), clock: () => 42 });
  await service.check();
  assert.equal(service.loadedBuild, 'A'); assert.equal(service.pending, 'B'); assert.deepEqual(navigations, []);
  const result = await service.transition('https://technoetic.github.io/reference-atlas/?view=sources&q=memory');
  assert.equal(result.mode, 'document'); assert.equal(navigations.length, 1);
  const target = new URL(navigations[0]); assert.equal(target.searchParams.get('view'), 'sources'); assert.equal(target.searchParams.get('q'), 'memory'); assert.equal(target.searchParams.get('_build'), 'B');
});

test('rollback is a changed identity and not a chronological comparison', async () => {
  let destination;
  const service = new VersionService({ baseURL, loadedBuild: 'B', fetcher: async () => response('A'), navigate: url => { destination = url; } });
  assert.equal((await service.transition('?view=check')).mode, 'document'); assert.equal(new URL(destination).searchParams.get('_build'), 'A');
});

test('pending update protects a draft until explicitly cleared', async () => {
  let dirty = true; const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', hasDraft: () => dirty, fetcher: async () => response('B'), navigate: url => navigations.push(url) });
  assert.equal((await service.transition('?view=sources')).mode, 'blocked'); assert.deepEqual(navigations, []);
  dirty = false; assert.equal((await service.transition('?view=sources')).mode, 'document'); assert.equal(navigations.length, 1);
});

test('input begun while a version request is in flight prevents navigation', async () => {
  let resolveResponse, dirty = false; const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', hasDraft: () => dirty, fetcher: () => new Promise(resolve => { resolveResponse = resolve; }), navigate: url => navigations.push(url) });
  const pending = service.transition('?view=sources'); dirty = true; resolveResponse(response('B'));
  assert.equal((await pending).mode, 'blocked'); assert.deepEqual(navigations, []);
});

test('a failed fresh version check keeps the current application usable', async () => {
  let fail = false; const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', fetcher: async () => { if (fail) throw new Error('offline'); return response('B'); }, navigate: url => navigations.push(url) });
  await service.check(); fail = true;
  assert.equal((await service.transition('?view=sources')).mode, 'internal'); assert.deepEqual(navigations, []);
});

test('a superseded target cannot trigger a full-document transition', async () => {
  let resolveResponse, current = true; const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', fetcher: () => new Promise(resolve => { resolveResponse = resolve; }), navigate: url => navigations.push(url) });
  const pending = service.transition('?view=sources', { isCurrent: () => current }); current = false; resolveResponse(response('B'));
  assert.equal((await pending).mode, 'stale'); assert.deepEqual(navigations, []);
});

test('an unchanged identity performs internal navigation without a reload', async () => {
  const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', fetcher: async () => response('A'), navigate: url => navigations.push(url) });
  assert.equal((await service.transition('?view=check')).mode, 'internal'); assert.deepEqual(navigations, []);
});

test('a hanging version request is bounded and does not trap navigation', async () => {
  const navigations = [];
  const service = new VersionService({ baseURL, loadedBuild: 'A', timeoutMs: 5, fetcher: () => new Promise(() => {}), navigate: url => navigations.push(url) });
  assert.equal((await service.transition('?view=sources')).mode, 'internal'); assert.equal(service.error, 'unavailable'); assert.deepEqual(navigations, []);
});

test('version fetch uses the global receiver required by browser-native fetch', async () => {
  function receiverSensitiveFetch() {
    if (this !== globalThis) throw new TypeError('Failed to execute fetch on Window: Illegal invocation');
    return Promise.resolve(response('B'));
  }
  const service = new VersionService({ baseURL, loadedBuild: 'A', fetcher: receiverSensitiveFetch });
  assert.equal(await service.check(), 'B');
  assert.equal(service.error, null);
});
