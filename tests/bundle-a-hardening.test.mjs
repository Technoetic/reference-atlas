import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, readFile, writeFile, copyFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SourcesScreen } from '../src/screens/sources.mjs';
import { ReferenceAtlasApp } from '../src/app.mjs';

const exec = promisify(execFile);
const project = fileURLToPath(new URL('../', import.meta.url));
const raster = Buffer.from([0x52, 0x49, 0x46, 0x46, 0xff, 0, 0x0d, 0x0a, 0x57, 0x45, 0x42, 0x50, 0x80, 0xfe]);

test('index.html ships inline SVG favicon, safe meta CSP without frame-ancestors, and Open Graph tags', async () => {
  const html = await readFile(path.join(project, 'index.html'), 'utf8');
  assert.match(html, /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="data:image\/svg\+xml,/i);
  const cspMatch = html.match(/<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i);
  assert.ok(cspMatch, 'index.html must include meta Content-Security-Policy');
  const csp = cspMatch[1];
  assert.match(csp, /default-src 'self'/);
  assert.match(csp, /script-src 'self'/);
  assert.match(csp, /img-src 'self' data:/);
  assert.match(csp, /object-src 'none'/);
  assert.doesNotMatch(csp, /frame-ancestors/i, 'frame-ancestors is ignored in meta CSP');
  assert.match(html, /property="og:title"/);
  assert.match(html, /property="og:description"/);
  assert.match(html, /property="og:url"\s+content="https:\/\/technoetic\.github\.io\/reference-atlas\/"/);
  assert.match(html, /name="twitter:card"\s+content="summary"/);
});

test('pages.yml validates pull_request on main without deploying PRs and sets persist-credentials false', async () => {
  const yml = await readFile(path.join(project, '.github/workflows/pages.yml'), 'utf8');
  assert.match(yml, /pull_request:\s*\n\s*branches:\s*\[main\]/);
  assert.match(yml, /persist-credentials:\s*false/);
  assert.match(yml, /if:\s*github\.event_name\s*!=\s*'pull_request'\s*\n\s*uses:\s*actions\/upload-pages-artifact@/m);
  assert.match(yml, /deploy:\s*\n\s*if:\s*github\.event_name\s*!=\s*'pull_request'/m);
});

test('build.mjs retains >256 assets cleanly and outputs dark-styled 404.html with absolute /reference-atlas/ link', async t => {
  const root = await mkdtemp(path.join(tmpdir(), 'reference-atlas-cap-'));
  t.after(async () => { await rm(root, { recursive: true, force: true }); });
  for (const dir of ['scripts', 'src/screens', 'styles', 'data', 'media/cards']) {
    await mkdir(path.join(root, dir), { recursive: true });
  }
  for (const file of ['build.mjs', 'build-identity.mjs']) {
    await copyFile(path.join(project, 'scripts', file), path.join(root, 'scripts', file));
  }
  await writeFile(path.join(root, 'index.html'), '<meta name="build-id" content="__BUILD_ID__"><script type="module" src="./src/app.mjs"></script><link rel="stylesheet" href="./styles/main.css">');
  await writeFile(path.join(root, 'src/app.mjs'), "export const ok = true;\n");
  await writeFile(path.join(root, 'styles/main.css'), 'body { margin: 0; }\n');
  await writeFile(path.join(root, 'data/catalog.json'), '{}\n');
  await writeFile(path.join(root, 'data/catalog.csv'), 'id,title\n');
  for (let i = 1; i <= 270; i++) {
    await writeFile(path.join(root, 'media/cards', `card-${i}.webp`), Buffer.concat([raster, Buffer.from(String(i))]));
  }
  const env = { ...process.env };
  delete env.RETAIN_BASE_URL;
  await exec(process.execPath, [path.join(root, 'scripts/build.mjs')], { cwd: root, env });
  const first = JSON.parse(await readFile(path.join(root, 'dist/deployment-manifest.json'), 'utf8'));
  assert.ok(first.currentAssets.length > 256, `Expected >256 assets, got ${first.currentAssets.length}`);

  // Next build must retain all >256 previous assets without throwing Invalid retention manifest.
  await writeFile(path.join(root, 'src/app.mjs'), "export const ok = 'v2';\n");
  await exec(process.execPath, [path.join(root, 'scripts/build.mjs')], { cwd: root, env });
  const second = JSON.parse(await readFile(path.join(root, 'dist/deployment-manifest.json'), 'utf8'));
  assert.equal(second.retainedAssets.length, first.currentAssets.length);

  // Verify 404.html uses absolute /reference-atlas/ path and dark theme + inline favicon.
  const notFound = await readFile(path.join(root, 'dist/404.html'), 'utf8');
  assert.match(notFound, /href="\/reference-atlas\/"/);
  assert.doesNotMatch(notFound, /href="\.\/"/);
  assert.match(notFound, /rel="icon"/);
  assert.match(notFound, /#10130f/);
});

test('SourcesScreen scrolls detail panel into view, focuses detail title, and restores trigger focus on close', () => {
  const calls = [];
  const heading = {
    focus(opts) { calls.push({ action: 'focus-heading', opts }); },
  };
  const panel = {
    getBoundingClientRect() { return { top: -22048 }; },
    scrollIntoView(opts) { calls.push({ action: 'scroll-detail', opts }); },
    querySelector(sel) { return sel === '#detail-title' ? heading : null; },
  };
  const detailContainer = {
    _html: '',
    get innerHTML() { return this._html; },
    set innerHTML(val) { this._html = val; },
    querySelector(sel) { return this._html && sel === '.detail-panel' ? panel : null; },
  };
  const triggerCard = {
    dataset: { source: 'arxiv:2502.12110' },
    focus(opts) { calls.push({ action: 'focus-trigger', opts }); },
  };
  const element = {
    querySelector(sel) { return sel === '#source-detail' ? detailContainer : null; },
    querySelectorAll(sel) { return sel === '[data-source]' ? [triggerCard] : []; },
  };
  const catalog = {
    sources: [{
      id: 'arxiv:2502.12110',
      kind: 'paper',
      title: 'A-MEM',
      url: 'https://arxiv.org/abs/2502.12110',
      year: 2025,
      tags: ['메모리·검색'],
      keys: ['arxiv:2502.12110'],
      aliases: [],
      uses: [{ plugin: 'agentic-vault', role: 'reference', evidence: [{ file: 'docs/x.md', line: 1, url: 'https://github.com/Technoetic/agentic-vault/blob/74a2776cec936cd2cce7274cc9f3cb29bacf0159/docs/x.md#L1', excerpt: 'demo' }] }],
    }],
  };

  const screen = new SourcesScreen({ element, catalog, state: {}, onState() {}, onSource() {} });
  screen.lastTriggerId = 'arxiv:2502.12110';
  screen.renderDetail('arxiv:2502.12110');
  assert.match(detailContainer.innerHTML, /id="detail-title" tabindex="-1"/);
  assert.deepEqual(calls, [
    { action: 'scroll-detail', opts: { behavior: 'instant', block: 'start' } },
    { action: 'focus-heading', opts: { preventScroll: true } },
  ]);

  // Re-rendering the same source id must not hijack scroll/focus again.
  screen.renderDetail('arxiv:2502.12110');
  assert.equal(calls.length, 2);

  // Closing restores focus to the trigger card.
  screen.pendingRestoreFocusId = 'arxiv:2502.12110';
  screen.renderDetail(null);
  assert.equal(detailContainer.innerHTML, '');
  assert.deepEqual(calls[2], { action: 'focus-trigger', opts: { preventScroll: true } });
});

test('SourcesScreen focusDetail uses smooth scroll when panel is near and instant under reduced motion', t => {
  const prevMatchMedia = Object.getOwnPropertyDescriptor(globalThis, 'matchMedia');
  t.after(() => {
    if (prevMatchMedia) Object.defineProperty(globalThis, 'matchMedia', prevMatchMedia);
    else delete globalThis.matchMedia;
  });
  const calls = [];
  const panel = {
    getBoundingClientRect() { return { top: 250 }; },
    scrollIntoView(opts) { calls.push(opts); },
    querySelector() { return { focus() {} }; },
  };
  const container = { querySelector(sel) { return sel === '.detail-panel' ? panel : null; } };
  const screen = new SourcesScreen({ element: { querySelector: () => container }, catalog: { sources: [] }, state: {}, onState() {}, onSource() {} });

  globalThis.matchMedia = () => ({ matches: false });
  screen.focusDetail(container);
  assert.deepEqual(calls[0], { behavior: 'smooth', block: 'start' });

  globalThis.matchMedia = () => ({ matches: true });
  screen.focusDetail(container);
  assert.deepEqual(calls[1], { behavior: 'instant', block: 'start' });
});

test('ReferenceAtlasApp cross-view atlas->sources source navigation preserves detail scroll/focus and re-click refocuses', async t => {
  const base = 'https://technoetic.github.io/reference-atlas/';
  const prev = new Map(['location', 'history', 'document', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  t.after(() => {
    for (const [k, d] of prev) {
      if (d) Object.defineProperty(globalThis, k, d);
      else delete globalThis[k];
    }
  });
  const events = [];
  globalThis.location = new URL(`${base}?view=atlas`);
  globalThis.history = {
    pushState(_s, _t, u) { globalThis.location = new URL(u, base); },
    replaceState(_s, _t, u) { globalThis.location = new URL(u, base); },
  };
  globalThis.document = { baseURI: base, querySelectorAll: () => [] };
  globalThis.window = { scrollTo(opts) { events.push(['window.scrollTo', opts]); } };

  const app = Object.assign(Object.create(ReferenceAtlasApp.prototype), {
    navigationSequence: 0,
    view: 'atlas',
    main: { focus(opts) { events.push(['main.focus', opts]); } },
    screen: { focusDetail() { events.push(['screen.focusDetail']); } },
    version: { async transition() { return { mode: 'internal' }; } },
    render() {
      this.renderedURL = location.href;
      this.view = this.state().view;
      events.push(['render', this.view, this.state().source]);
    },
  });

  // 1. Cross-view atlas -> sources&source=arxiv:2502.12110 must NOT clobber scroll/focus with window.scrollTo(0) or main.focus().
  await app.navigate(new URL(`${base}?view=sources&source=arxiv%3A2502.12110`));
  assert.deepEqual(events, [['render', 'sources', 'arxiv:2502.12110']]);

  // 2. Re-clicking the already-open source on sources calls screen.focusDetail().
  app.openSource('arxiv:2502.12110');
  await new Promise(r => setTimeout(r, 10));
  assert.deepEqual(events.at(-1), ['screen.focusDetail']);

  // 3. Navigating from sources -> atlas (no open source) resets scroll to top and focuses #main.
  await app.navigate(new URL(`${base}?view=atlas`));
  assert.deepEqual(events.slice(-3), [
    ['render', 'atlas', null],
    ['window.scrollTo', { top: 0, behavior: 'instant' }],
    ['main.focus', { preventScroll: true }],
  ]);
});
