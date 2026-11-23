import test from 'node:test';
import assert from 'node:assert/strict';
import { CatalogService } from './catalog.mjs';

test('catalog fetch uses the global receiver required by browser-native fetch', async () => {
  const catalog = { schemaVersion: 1, sources: [], counts: { total: 0, 'research-name': 0 }, countsByPlugin: {} };
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

test('screens receive only identified sources when the server returns an older snapshot', async () => {
  const reference = { plugin: 'agentic-vault', role: 'reference', evidence: [{
    file: 'docs/source.md', line: 3, excerpt: 'Published source',
    url: `https://github.com/Technoetic/agentic-vault/blob/${'a'.repeat(40)}/docs/source.md#L3`,
  }] };
  const article = { id: 'url:https://example.org/article', keys: ['url:https://example.org/article'],
    kind: 'article', title: 'Published article', url: 'https://example.org/article',
    tags: [], aliases: [], uses: [reference] };
  const name = { ...article, id: 'name:old', keys: ['name:old'], kind: 'research-name',
    title: 'Old name only', url: null, uses: [{ ...reference, role: 'unresolved' }] };
  const legacy = { schemaVersion: 1, sources: [name, article], counts: { total: 2, 'research-name': 1 }, countsByPlugin: { 'agentic-vault': { total: 2 } } };
  const service = new CatalogService({ baseURL: 'https://example.org/', fetcher: async () => ({
    ok: true, json: async () => legacy,
  }) });
  const visible = await service.load();
  assert.deepEqual(visible.sources, [article]);
  assert.equal('counts' in visible, false);
  assert.equal('countsByPlugin' in visible, false);
});
