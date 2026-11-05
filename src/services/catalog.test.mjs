import test from 'node:test';
import assert from 'node:assert/strict';
import { CatalogService } from './catalog.mjs';

test('catalog fetch uses the global receiver required by browser-native fetch', async () => {
  const catalog = { schemaVersion: 1, sources: [] };
  let receivedURL;
  function receiverSensitiveFetch(url) {
    if (this !== globalThis) throw new TypeError('Failed to execute fetch on Window: Illegal invocation');
    receivedURL = String(url);
    return Promise.resolve({ ok: true, json: async () => catalog });
  }
  const service = new CatalogService({ baseURL: 'https://technoetic.github.io/reference-atlas/?view=sources', fetcher: receiverSensitiveFetch });
  assert.deepEqual(await service.load(), catalog);
  assert.equal(new URL(receivedURL).pathname, '/reference-atlas/data/catalog.json');
});
