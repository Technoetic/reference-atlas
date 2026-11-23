import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  CountUp,
  countUpMarkup,
  digitWidthClass,
  easeOutCubic,
  formatCount,
  parseDurationToken,
} from '../src/visuals/countup.mjs';
import { ScrollReveal } from '../src/visuals/reveal.mjs';
import { ReferenceAtlasApp } from '../src/app.mjs';

const project = fileURLToPath(new URL('../', import.meta.url));

function makeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add(...names) { for (const n of names) set.add(n); },
    remove(...names) { for (const n of names) set.delete(n); },
    contains(name) { return set.has(name); },
    toArray() { return [...set]; },
  };
}

function makeElement({ dataset = {}, textContent = '', rect = { top: 100, bottom: 140 }, classes = [] } = {}) {
  const listeners = new Map();
  const el = {
    dataset: { ...dataset },
    textContent,
    classList: makeClassList(classes),
    _rect: rect,
    getBoundingClientRect() { return this._rect; },
    closest(selector) {
      if (selector === '.reveal-pending' && this.classList.contains('reveal-pending')) return this;
      return null;
    },
    addEventListener(type, fn, opts) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(fn);
      opts?.signal?.addEventListener?.('abort', () => listeners.get(type)?.delete(fn));
    },
    dispatch(type, event = {}) {
      for (const fn of [...(listeners.get(type) || [])]) fn({ target: this, ...event });
    },
  };
  return el;
}

function installBrowserEnv(t, { reduced = false, innerHeight = 900 } = {}) {
  const keys = [
    'matchMedia', 'requestAnimationFrame', 'cancelAnimationFrame',
    'IntersectionObserver', 'addEventListener', 'removeEventListener',
    'innerHeight', 'performance', 'getComputedStyle', 'document',
  ];
  const saved = new Map(keys.map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  t.after(() => {
    for (const [k, d] of saved) {
      if (d) Object.defineProperty(globalThis, k, d);
      else delete globalThis[k];
    }
  });

  let now = 0;
  let nextFrameId = 1;
  const frames = new Map();
  const cancelledFrames = [];
  const globalListeners = new Map();
  const registeredEventTypes = [];
  const observers = [];
  const mediaListeners = new Set();
  const mediaState = {
    matches: reduced,
    addEventListener(type, fn, opts) {
      if (type !== 'change') return;
      mediaListeners.add(fn);
      opts?.signal?.addEventListener?.('abort', () => mediaListeners.delete(fn));
    },
  };

  globalThis.innerHeight = innerHeight;
  globalThis.performance = { now: () => now };
  globalThis.matchMedia = () => mediaState;
  globalThis.getComputedStyle = () => ({ getPropertyValue: () => '1400ms' });
  globalThis.document = { documentElement: {} };

  globalThis.requestAnimationFrame = cb => {
    const id = nextFrameId++;
    frames.set(id, cb);
    return id;
  };
  globalThis.cancelAnimationFrame = id => {
    cancelledFrames.push(id);
    frames.delete(id);
  };

  globalThis.addEventListener = (type, fn, opts) => {
    registeredEventTypes.push(type);
    if (!globalListeners.has(type)) globalListeners.set(type, new Set());
    globalListeners.get(type).add(fn);
    opts?.signal?.addEventListener?.('abort', () => globalListeners.get(type)?.delete(fn));
  };
  globalThis.removeEventListener = (type, fn) => {
    globalListeners.get(type)?.delete(fn);
  };

  class MockIntersectionObserver {
    constructor(callback, options) {
      this.callback = callback;
      this.options = options;
      this.observed = new Set();
      this.unobserved = [];
      this.disconnected = false;
      observers.push(this);
    }
    observe(target) { this.observed.add(target); }
    unobserve(target) { this.observed.delete(target); this.unobserved.push(target); }
    disconnect() { this.disconnected = true; this.observed.clear(); }
    trigger(entries) { this.callback(entries, this); }
  }
  globalThis.IntersectionObserver = MockIntersectionObserver;

  return {
    get frames() { return frames; },
    get cancelledFrames() { return cancelledFrames; },
    get observers() { return observers; },
    get registeredEventTypes() { return registeredEventTypes; },
    setNow(ms) { now = ms; },
    stepFrame(ms) {
      now = ms;
      const batch = [...frames.entries()];
      frames.clear();
      for (const [, cb] of batch) cb(ms);
    },
    emit(type, event = {}) {
      for (const fn of [...(globalListeners.get(type) || [])]) fn(event);
    },
    setReduced(value) {
      mediaState.matches = value;
      for (const fn of [...mediaListeners]) fn({ matches: value });
    },
  };
}

test('easeOutCubic, formatCount, parseDurationToken, and countUpMarkup produce accessible, CSP-safe values', () => {
  assert.equal(easeOutCubic(0), 0);
  assert.equal(easeOutCubic(1), 1);
  assert.ok(easeOutCubic(0.5) > 0.8 && easeOutCubic(0.5) < 0.95);
  assert.equal(easeOutCubic(-1), 0);
  assert.equal(easeOutCubic(2), 1);

  assert.equal(formatCount(1234), '1,234');
  assert.equal(formatCount(91), '91');
  assert.equal(formatCount(12.5, { decimals: 1 }), '12.5');
  assert.equal(formatCount(0.42, { format: 'percent' }), '42%');
  assert.equal(formatCount(Number.NaN), '0');

  assert.equal(parseDurationToken('1400ms'), 1400);
  assert.equal(parseDurationToken('1.5s'), 1500);
  assert.equal(parseDurationToken('invalid', 1200), 1200);

  assert.equal(digitWidthClass('6'), 'cu-d1');
  assert.equal(digitWidthClass('91'), 'cu-d2');
  assert.equal(digitWidthClass('1,234'), 'cu-d5');

  const markup = countUpMarkup(1234);
  assert.match(markup, /class="countup-value cu-d5"/);
  assert.match(markup, /data-countup-target="1234"/);
  assert.match(markup, /aria-hidden="true">1,234<\/span>/);
  assert.match(markup, /<span class="sr-only countup-sr">1,234<\/span>/);
  assert.doesNotMatch(markup, /aria-live|style=|hidden(?!=)/i);
});

test('CountUp animates visible and intersection-triggered counters to exact targets and cancels cleanly on destroy', t => {
  const env = installBrowserEnv(t);
  const heroNum = makeElement({ dataset: { countupTarget: '1234' }, textContent: '1,234', rect: { top: 200, bottom: 250 } });
  const belowNum = makeElement({ dataset: { countupTarget: '91' }, textContent: '91', rect: { top: 1400, bottom: 1440 } });
  const zeroNum = makeElement({ dataset: { countupTarget: '0' }, textContent: '0', rect: { top: 220, bottom: 260 } });
  const root = { querySelectorAll: () => [heroNum, belowNum, zeroNum] };

  const cu = new CountUp(root, { animate: true, duration: 1000 });
  assert.ok(!env.registeredEventTypes.includes('unload'), 'must never register unload listener');
  assert.equal(heroNum.textContent, '0');
  assert.equal(belowNum.textContent, '0');
  assert.equal(zeroNum.textContent, '0');
  assert.equal(env.observers.length, 1);
  assert.equal(env.observers[0].options.threshold, 0);
  assert.equal(env.observers[0].options.rootMargin, '100000px 0px 40px 0px');
  assert.ok(env.observers[0].observed.has(belowNum));

  // Mid-animation at 500ms: heroNum climbs with cubic ease-out, belowNum still waiting.
  env.stepFrame(500);
  assert.equal(heroNum.textContent, '1,080');
  assert.equal(belowNum.textContent, '0');

  // Complete heroNum at 1000ms -> exact final target and rAF loop stops.
  env.stepFrame(1000);
  assert.equal(heroNum.textContent, '1,234');
  assert.equal(env.frames.size, 0);

  // Scroll belowNum into view -> unobserve immediately and animate once.
  belowNum._rect = { top: 600, bottom: 640 };
  env.observers[0].trigger([{ target: belowNum, isIntersecting: true, boundingClientRect: belowNum._rect }]);
  assert.ok(env.observers[0].unobserved.includes(belowNum));
  assert.equal(env.frames.size, 1);

  env.stepFrame(1500);
  assert.equal(belowNum.textContent, '80');

  // Destroy mid-animation cancels rAF and disconnects IO.
  cu.destroy();
  assert.ok(env.cancelledFrames.length >= 1);
  assert.equal(env.observers[0].disconnected, true);
});

test('CountUp respects prefers-reduced-motion, animate:false refresh, beforeprint, and BFCache pageshow recovery', t => {
  const env = installBrowserEnv(t, { reduced: true });
  const elReduced = makeElement({ dataset: { countupTarget: '94' }, textContent: '94', rect: { top: 100, bottom: 140 } });
  const cuReduced = new CountUp({ querySelectorAll: () => [elReduced] });
  assert.equal(elReduced.textContent, '94');
  assert.equal(env.frames.size, 0);
  cuReduced.destroy();

  // Normal motion, animate: false (same-screen API refresh -> no recount from 0).
  const env2 = installBrowserEnv(t, { reduced: false });
  const elRefresh = makeElement({ dataset: { countupTarget: '99' }, textContent: '99', rect: { top: 100, bottom: 140 } });
  const cuRefresh = new CountUp({ querySelectorAll: () => [elRefresh] }, { animate: false });
  assert.equal(elRefresh.textContent, '99');
  assert.equal(env2.frames.size, 0);
  cuRefresh.destroy();

  // beforeprint settles both active and below-fold counters immediately.
  const active = makeElement({ dataset: { countupTarget: '91' }, textContent: '91', rect: { top: 100, bottom: 140 } });
  const below = makeElement({ dataset: { countupTarget: '38' }, textContent: '38', rect: { top: 1400, bottom: 1440 } });
  const cuPrint = new CountUp({ querySelectorAll: () => [active, below] }, { duration: 1000 });
  assert.equal(active.textContent, '0');
  assert.equal(below.textContent, '0');
  env2.emit('beforeprint');
  assert.equal(active.textContent, '91');
  assert.equal(below.textContent, '38');
  assert.equal(env2.frames.size, 0);
  cuPrint.destroy();

  // pagehide + pageshow(persisted: true): interrupted settles to final, pending re-observes.
  const running = makeElement({ dataset: { countupTarget: '91' }, textContent: '91', rect: { top: 100, bottom: 140 } });
  const pending = makeElement({ dataset: { countupTarget: '11' }, textContent: '11', rect: { top: 1500, bottom: 1540 } });
  const cuBf = new CountUp({ querySelectorAll: () => [running, pending] }, { duration: 1000 });
  const observerCountBefore = env2.observers.length;
  env2.emit('pagehide');
  assert.equal(env2.frames.size, 0);
  env2.emit('pageshow', { persisted: true });
  assert.equal(running.textContent, '91');
  assert.equal(pending.textContent, '0');
  assert.equal(env2.observers.length, observerCountBefore + 1);
  assert.ok(env2.observers.at(-1).observed.has(pending));
  cuBf.destroy();
});

test('ScrollReveal keeps visible/above-fold items visible, reveals below-fold once, and handles reduced-motion, focusin, print, and BFCache', t => {
  const env = installBrowserEnv(t, { reduced: false, innerHeight: 900 });
  const above = makeElement({ rect: { top: -200, bottom: -50 } });
  const inView = makeElement({ rect: { top: 300, bottom: 500 } });
  const below1 = makeElement({ rect: { top: 1200, bottom: 1500 } });
  const below2 = makeElement({ rect: { top: 2000, bottom: 2400 } });
  const rootListeners = new Map();
  const root = {
    querySelectorAll: sel => sel === '[data-reveal]' ? [above, inView, below1, below2] : [above, inView, below1, below2].filter(e => e.classList.contains('reveal-pending') || e.classList.contains('reveal-entering')),
    addEventListener(type, fn, opts) {
      if (!rootListeners.has(type)) rootListeners.set(type, new Set());
      rootListeners.get(type).add(fn);
      opts?.signal?.addEventListener?.('abort', () => rootListeners.get(type)?.delete(fn));
    },
  };

  const reveal = new ScrollReveal(root);
  assert.ok(!env.registeredEventTypes.includes('unload'), 'must never register unload listener');
  assert.ok(above.classList.contains('is-revealed') && !above.classList.contains('reveal-pending'));
  assert.ok(inView.classList.contains('is-revealed') && !inView.classList.contains('reveal-pending'));
  assert.ok(below1.classList.contains('reveal-pending'));
  assert.ok(below2.classList.contains('reveal-pending'));
  assert.equal(env.observers[0].options.threshold, 0);
  assert.equal(env.observers[0].options.rootMargin, '100000px 0px 40px 0px');

  // Reveal below1 on intersection, unobserve immediately, transitionend completes cleanup.
  below1._rect = { top: 700, bottom: 1000 };
  env.observers[0].trigger([{ target: below1, isIntersecting: true, boundingClientRect: below1._rect }]);
  assert.ok(!below1.classList.contains('reveal-pending'));
  assert.ok(below1.classList.contains('reveal-entering'));
  assert.ok(env.observers[0].unobserved.includes(below1));
  below1.dispatch('transitionend');
  assert.ok(!below1.classList.contains('reveal-entering'));
  assert.ok(below1.classList.contains('is-revealed'));

  // BFCache restore: below2 scrolled into view while away -> immediately revealed on pageshow(persisted).
  env.emit('pagehide');
  assert.equal(env.observers[0].disconnected, true);
  below2._rect = { top: 400, bottom: 700 };
  env.emit('pageshow', { persisted: true });
  assert.ok(!below2.classList.contains('reveal-pending'));
  reveal.destroy();

  // Focusin on pending item reveals it immediately; beforeprint reveals remaining items.
  const env2 = installBrowserEnv(t, { reduced: false, innerHeight: 900 });
  const focusTarget = makeElement({ rect: { top: 1400, bottom: 1600 } });
  const printTarget = makeElement({ rect: { top: 2200, bottom: 2500 } });
  const rListeners = new Map();
  const root2 = {
    querySelectorAll: () => [focusTarget, printTarget],
    addEventListener(type, fn, opts) {
      if (!rListeners.has(type)) rListeners.set(type, new Set());
      rListeners.get(type).add(fn);
      opts?.signal?.addEventListener?.('abort', () => rListeners.get(type)?.delete(fn));
    },
  };
  const reveal2 = new ScrollReveal(root2);
  assert.ok(focusTarget.classList.contains('reveal-pending'));
  for (const fn of rListeners.get('focusin') || []) fn({ target: focusTarget });
  assert.ok(!focusTarget.classList.contains('reveal-pending'));
  env2.emit('beforeprint');
  assert.ok(!printTarget.classList.contains('reveal-pending'));
  assert.ok(printTarget.classList.contains('is-revealed'));
  reveal2.destroy();

  // Instant scrollbar/End jump past elements (skipped by IO) recovers on scrollend without per-scroll polling.
  const env3 = installBrowserEnv(t, { reduced: false, innerHeight: 900 });
  const jumpedPast = makeElement({ rect: { top: 2000, bottom: 2300 } });
  const atBottom = makeElement({ rect: { top: 4000, bottom: 4200 } });
  const root3 = { querySelectorAll: () => [jumpedPast, atBottom], addEventListener() {} };
  const reveal3 = new ScrollReveal(root3);
  assert.ok(!env3.registeredEventTypes.includes('scroll'), 'must never register per-frame scroll listener');
  assert.ok(env3.registeredEventTypes.includes('scrollend'));
  jumpedPast._rect = { top: -1800, bottom: -1500 };
  atBottom._rect = { top: 600, bottom: 800 };
  env3.emit('scrollend');
  assert.ok(!jumpedPast.classList.contains('reveal-pending') && jumpedPast.classList.contains('is-revealed'));
  assert.ok(!atBottom.classList.contains('reveal-pending'));
  reveal3.destroy();
});

test('ReferenceAtlasApp refreshCatalog never recounts atlas KPIs from zero', async t => {
  const prev = new Map(['location', 'history', 'document'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  t.after(() => {
    for (const [k, d] of prev) {
      if (d) Object.defineProperty(globalThis, k, d);
      else delete globalThis[k];
    }
  });
  globalThis.location = new URL('https://technoetic.github.io/reference-atlas/?view=atlas');
  globalThis.history = { replaceState() {} };
  globalThis.document = { querySelector: () => null, querySelectorAll: () => [] };

  const renderCalls = [];
  const app = Object.assign(Object.create(ReferenceAtlasApp.prototype), {
    loadSequence: 0,
    abort: new AbortController(),
    catalogService: { async load() { return { sources: [] }; } },
    screen: { destroy() {} },
    view: 'atlas',
    render(opts) { renderCalls.push(opts); },
    renderSnapshot() {},
  });

  const ok = await app.refreshCatalog();
  assert.equal(ok, true);
  assert.deepEqual(renderCalls, [{ animateMetrics: false }]);
});

test('CSS tokens, motion.css, index.html, and screens uphold motion and CSP contracts', async () => {
  const [tokens, motionCss, mainCss, indexHtml, atlasJs, sourcesJs, countupJs, revealJs] = await Promise.all([
    readFile(path.join(project, 'styles/tokens.css'), 'utf8'),
    readFile(path.join(project, 'styles/motion.css'), 'utf8'),
    readFile(path.join(project, 'styles/main.css'), 'utf8'),
    readFile(path.join(project, 'index.html'), 'utf8'),
    readFile(path.join(project, 'src/screens/atlas.mjs'), 'utf8'),
    readFile(path.join(project, 'src/screens/sources.mjs'), 'utf8'),
    readFile(path.join(project, 'src/visuals/countup.mjs'), 'utf8'),
    readFile(path.join(project, 'src/visuals/reveal.mjs'), 'utf8'),
  ]);

  for (const token of [
    '--motion-countup-duration',
    '--motion-reveal-duration',
    '--motion-reveal-stagger',
    '--motion-reveal-distance',
    '--motion-ease-out',
  ]) {
    assert.ok(tokens.includes(token), `tokens.css must define ${token}`);
  }

  assert.match(mainCss.trim(), /@import\s+'\.\/motion\.css';\s*$/);
  assert.match(motionCss, /\.scroll-progress\s*\{\s*display:\s*none;/);
  assert.match(motionCss, /@supports\s*\(animation-timeline:\s*scroll\(\)\)/);
  assert.match(motionCss, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(motionCss, /@media\s+print/);
  assert.match(motionCss, /font-variant-numeric:\s*tabular-nums/);
  assert.doesNotMatch(motionCss, /visibility\s*:\s*hidden/i);

  assert.match(indexHtml, /<div class="scroll-progress" aria-hidden="true"><\/div>/);
  assert.match(indexHtml, /style-src 'self'/);
  for (const [name, content] of [['index.html', indexHtml], ['atlas.mjs', atlasJs], ['sources.mjs', sourcesJs], ['countup.mjs', countupJs], ['reveal.mjs', revealJs]]) {
    assert.doesNotMatch(content, /\sstyle="/i, `${name} must not emit inline style attributes under CSP style-src 'self'`);
    assert.doesNotMatch(content, /addEventListener\(\s*['"]unload['"]/i, `${name} must never attach unload listeners`);
  }
  assert.doesNotMatch(countupJs, /style\s*:\s*['"]unit['"]/, 'must never pass Korean units to Intl.NumberFormat style: unit');
});
