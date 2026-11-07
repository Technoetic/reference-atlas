import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { ReferenceAtlasApp } from '../src/app.mjs';
import { AtlasScreen } from '../src/screens/atlas.mjs';
import { routeURL } from '../src/screens/util.mjs';

const base = 'https://technoetic.github.io/reference-atlas/';
const legacy = `${base}?view=check&q=memory&plugin=agentic-vault&kind=paper&source=arxiv%3A2502.12110&_build=A#source-detail`;
const canonical = legacy.replace('view=check', 'view=sources');

function environment(t, href = legacy) {
  const previous = new Map(['location', 'history', 'document', 'window', 'matchMedia'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const changes = [];
  globalThis.location = new URL(href);
  globalThis.history = Object.fromEntries(['pushState', 'replaceState'].map(method => [method, (_state, _title, target) => { changes.push({ method, url: String(target) }); globalThis.location = new URL(target, base); }]));
  globalThis.document = { baseURI: base, querySelectorAll: () => [] };
  globalThis.window = { scrollTo() {} };
  globalThis.matchMedia = () => ({ matches: true });
  t.after(() => { for (const [key, descriptor] of previous) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; } });
  return changes;
}

test('legacy check URLs resolve to the source library without losing filters or source links', () => {
  assert.equal(routeURL({}, legacy).href, canonical);
  assert.equal(routeURL({ view: 'check' }, `${base}?q=memory`).href, `${base}?q=memory&view=sources`);
  assert.equal(routeURL({}, `${base}?view=unknown`).searchParams.get('view'), 'unknown');
});

test('rendering a legacy check deep link replaces its history entry and restores source state', t => {
  const changes = environment(t);
  let state;
  const app = Object.assign(Object.create(ReferenceAtlasApp.prototype), { catalog: { sources: [] }, view: 'sources', screen: { update(value) { state = value; } } });
  assert.equal(app.state().view, 'sources');
  app.render();
  assert.deepEqual(changes, [{ method: 'replaceState', url: canonical }]);
  assert.equal(state.view, 'sources');
  assert.equal(state.q, 'memory');
  assert.equal(state.plugin, 'agentic-vault');
  assert.equal(state.source, 'arxiv:2502.12110');
  assert.equal(app.renderedURL, canonical);
});

for (const pop of [false, true]) {
  test(`legacy check ${pop ? 'history restoration' : 'navigation'} uses the canonical source URL without adding an entry`, async t => {
    const changes = environment(t, pop ? legacy : `${base}?view=atlas`);
    let transition;
    const app = Object.assign(Object.create(ReferenceAtlasApp.prototype), {
      navigationSequence: 0, view: 'sources', main: { focus() {} },
      version: { async transition(target, options) { transition = { url: target.href, replace: options.replace }; return { mode: 'internal' }; } },
      render() { this.renderedURL = location.href; this.view = this.state().view; }
    });
    await app.navigate(new URL(legacy), { pop });
    assert.deepEqual(transition, { url: canonical, replace: true });
    assert.deepEqual(changes, [{ method: 'replaceState', url: canonical }]);
    assert.equal(app.view, 'sources');
  });
}

test('an available build update receives the canonical source destination for a legacy link', async t => {
  const changes = environment(t, `${base}?view=atlas`);
  let transition;
  const app = Object.assign(Object.create(ReferenceAtlasApp.prototype), {
    navigationSequence: 0,
    version: { async transition(target, options) { transition = { url: target.href, replace: options.replace }; return { mode: 'document' }; } }
  });
  await app.navigate(new URL(legacy));
  assert.deepEqual(transition, { url: canonical, replace: true });
  assert.deepEqual(changes, []);
});

test('public header and home expose research exploration without the removed check feature', async t => {
  environment(t, base);
  const header = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  const graph = { querySelector(selector) { return selector === 'canvas' ? { getContext: () => null } : {}; } };
  const element = { innerHTML: '', querySelector: () => graph, addEventListener() {}, removeEventListener() {} };
  new AtlasScreen({ element, catalog: { sources: [] }, onSource() {} }).mount();
  for (const html of [header, element.innerHTML]) assert.doesNotMatch(html, /view=check|기존 참조 확인|이미 참고한 자료일까|check-callout|로컬 중복 확인|다음 참고 자료의 중복/);
  assert.match(header, /view=sources/);
  assert.match(header, /data\/catalog\.json/);
  assert.match(header, /data\/catalog\.csv/);
  assert.match(element.innerHTML, /hero-map/);
  assert.match(element.innerHTML, /연구 탐색하기/);
  assert.match(element.innerHTML, /featured-section/);
});
