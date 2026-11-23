import { escapeHTML } from '../screens/util.mjs';

const DEFAULT_DURATION_MS = 1400;
const formatters = new Map();

export function easeOutCubic(progress) {
  const clamped = Math.min(1, Math.max(0, Number(progress) || 0));
  return 1 - (1 - clamped) ** 3;
}

export function formatCount(value, { locale = 'ko-KR', decimals = 0, format = 'decimal', currency } = {}) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '0';
  const safeDecimals = Math.max(0, Math.min(6, Number(decimals) || 0));
  const style = format === 'percent' ? 'percent' : (format === 'currency' && currency ? 'currency' : 'decimal');
  const key = `${locale}|${style}|${safeDecimals}|${currency || ''}`;
  let formatter = formatters.get(key);
  if (!formatter) {
    const options = {
      style,
      minimumFractionDigits: safeDecimals,
      maximumFractionDigits: safeDecimals,
    };
    if (style === 'currency' && currency) options.currency = currency;
    formatter = new Intl.NumberFormat(locale, options);
    formatters.set(key, formatter);
  }
  return formatter.format(numeric);
}

export function digitWidthClass(formatted) {
  const len = Math.max(1, Math.min(6, String(formatted ?? '').length));
  return `cu-d${len}`;
}

export function countUpMarkup(value, options = {}) {
  const numeric = Number.isFinite(Number(value)) ? Number(value) : 0;
  const formatted = formatCount(numeric, options);
  const widthClass = digitWidthClass(formatted);
  const attrs = [`data-countup-target="${escapeHTML(numeric)}"`];
  if (options.decimals) attrs.push(`data-countup-decimals="${escapeHTML(options.decimals)}"`);
  if (options.format && options.format !== 'decimal') attrs.push(`data-countup-format="${escapeHTML(options.format)}"`);
  if (options.currency) attrs.push(`data-countup-currency="${escapeHTML(options.currency)}"`);
  return `<span class="countup-value ${widthClass}" ${attrs.join(' ')} aria-hidden="true">${escapeHTML(formatted)}</span><span class="sr-only countup-sr">${escapeHTML(formatted)}</span>`;
}

export function parseDurationToken(raw, fallback = DEFAULT_DURATION_MS) {
  if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) return raw;
  const text = String(raw ?? '').trim();
  const match = text.match(/^(\d+(?:\.\d+)?)(ms|s)$/i);
  if (!match) return fallback;
  const amount = Number(match[1]);
  if (!Number.isFinite(amount) || amount <= 0) return fallback;
  return match[2].toLowerCase() === 's' ? amount * 1000 : amount;
}

function readDurationToken(fallback = DEFAULT_DURATION_MS) {
  try {
    const root = globalThis.document?.documentElement;
    if (!root || typeof globalThis.getComputedStyle !== 'function') return fallback;
    return parseDurationToken(globalThis.getComputedStyle(root).getPropertyValue('--motion-countup-duration'), fallback);
  } catch {
    return fallback;
  }
}

export class CountUp {
  constructor(root, { animate = true, locale = 'ko-KR', duration } = {}) {
    this.root = root;
    this.animate = Boolean(animate);
    this.locale = locale;
    this.duration = duration != null ? parseDurationToken(duration) : readDurationToken();
    this.abort = new AbortController();
    this.destroyed = false;
    this.frame = null;
    this.observer = null;
    this.entries = new Map();
    this.active = new Set();
    this.reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)') || null;
    this.tick = now => this.onFrame(now);

    const nodes = this.root?.querySelectorAll?.('[data-countup-target]') || [];
    for (const el of nodes) {
      const target = Number(el.dataset?.countupTarget);
      if (!Number.isFinite(target)) continue;
      const decimals = Number(el.dataset?.countupDecimals) || 0;
      const format = el.dataset?.countupFormat || 'decimal';
      const currency = el.dataset?.countupCurrency || undefined;
      const formatOptions = { locale: this.locale, decimals, format, currency };
      const finalText = formatCount(target, formatOptions);
      const zeroText = formatCount(0, formatOptions);
      this.entries.set(el, {
        el,
        target,
        decimals,
        formatOptions,
        finalText,
        zeroText,
        lastText: el.textContent,
        startTime: 0,
        state: 'pending',
      });
    }

    if (!this.entries.size) return;

    this.attachListeners();
    if (!this.shouldAnimate()) {
      this.finishAll();
      return;
    }

    this.prepareAndObserve();
  }

  shouldAnimate() {
    return (
      this.animate &&
      !this.reduced?.matches &&
      typeof globalThis.requestAnimationFrame === 'function'
    );
  }

  attachListeners() {
    const options = { signal: this.abort.signal };
    this.reduced?.addEventListener?.('change', event => {
      if (event.matches) this.finishAll();
    }, options);
    globalThis.addEventListener?.('beforeprint', () => this.finishAll(), options);
    globalThis.addEventListener?.('scrollend', () => this.sync(), { passive: true, signal: this.abort.signal });
    globalThis.addEventListener?.('pagehide', () => this.pauseForPageHide(), options);
    globalThis.addEventListener?.('pageshow', event => {
      if (event?.persisted) this.resumeFromBFCache();
    }, options);
  }

  viewportHeight() {
    return Number(globalThis.innerHeight) || 900;
  }

  prepareAndObserve() {
    const vh = this.viewportHeight();
    const toObserve = [];
    const hasIO = typeof globalThis.IntersectionObserver === 'function';

    for (const entry of this.entries.values()) {
      if (entry.state === 'done') continue;
      if (entry.target === 0) {
        this.settle(entry);
        continue;
      }
      const rect = entry.el.getBoundingClientRect?.();
      if (rect && rect.bottom <= 0) {
        this.settle(entry);
        continue;
      }
      if (!rect || rect.top < vh * 0.98 || !hasIO) {
        this.writeText(entry, entry.zeroText);
        this.startEntry(entry);
      } else {
        this.writeText(entry, entry.zeroText);
        toObserve.push(entry);
      }
    }

    if (toObserve.length && hasIO) {
      this.ensureObserver();
      for (const entry of toObserve) this.observer.observe(entry.el);
    }
  }

  ensureObserver() {
    if (this.observer || typeof globalThis.IntersectionObserver !== 'function') return;
    this.observer = new globalThis.IntersectionObserver(records => {
      if (this.destroyed) return;
      const vh = this.viewportHeight();
      for (const record of records) {
        const entry = this.entries.get(record.target);
        if (!entry || entry.state !== 'pending') continue;
        const rect = record.boundingClientRect;
        if (record.isIntersecting || (rect && rect.top < vh)) {
          this.observer?.unobserve(record.target);
          if (rect && rect.bottom <= 0) this.settle(entry);
          else this.startEntry(entry);
        }
      }
    }, { threshold: 0, rootMargin: '100000px 0px 40px 0px' });
  }

  sync({ settleAbove = false } = {}) {
    if (this.destroyed) return;
    if (!this.shouldAnimate()) {
      this.finishAll();
      return;
    }
    const vh = this.viewportHeight();
    for (const entry of this.entries.values()) {
      if (entry.state === 'done') continue;
      const rect = entry.el.getBoundingClientRect?.();
      if (!rect) continue;
      if (rect.bottom <= 0 || (settleAbove && rect.top < 0)) {
        this.observer?.unobserve(entry.el);
        this.settle(entry);
      } else if (entry.state === 'pending' && rect.top < vh * 0.98) {
        this.observer?.unobserve(entry.el);
        this.startEntry(entry);
      }
    }
  }

  startEntry(entry) {
    if (this.destroyed || entry.state !== 'pending') return;
    if (!this.shouldAnimate() || entry.target === 0) {
      this.settle(entry);
      return;
    }
    entry.state = 'running';
    entry.startTime = globalThis.performance?.now?.() ?? Date.now();
    this.active.add(entry);
    if (this.frame === null) {
      this.frame = globalThis.requestAnimationFrame(this.tick);
    }
  }

  onFrame(now) {
    this.frame = null;
    if (this.destroyed) return;
    const currentNow = Number.isFinite(now) ? now : (globalThis.performance?.now?.() ?? Date.now());
    for (const entry of [...this.active]) {
      const elapsed = Math.max(0, currentNow - entry.startTime);
      const progress = this.duration > 0 ? Math.min(1, elapsed / this.duration) : 1;
      if (progress >= 1) {
        this.settle(entry);
        continue;
      }
      const eased = easeOutCubic(progress);
      const raw = entry.target * eased;
      const value = (entry.decimals > 0 || entry.formatOptions.format === 'percent') ? raw : Math.round(raw);
      const nextText = formatCount(value, entry.formatOptions);
      this.writeText(entry, nextText);
    }
    if (this.active.size > 0 && !this.destroyed) {
      this.frame = globalThis.requestAnimationFrame(this.tick);
    }
  }

  writeText(entry, text) {
    if (entry.lastText === text) return;
    entry.lastText = text;
    entry.el.textContent = text;
  }

  settle(entry) {
    this.active.delete(entry);
    entry.state = 'done';
    this.writeText(entry, entry.finalText);
  }

  finishAll() {
    this.cancelFrame();
    this.observer?.disconnect();
    this.observer = null;
    for (const entry of this.entries.values()) {
      this.settle(entry);
    }
  }

  pauseForPageHide() {
    this.cancelFrame();
    this.observer?.disconnect();
    this.observer = null;
    for (const entry of [...this.active]) {
      entry.state = 'interrupted';
      this.active.delete(entry);
    }
  }

  resumeFromBFCache() {
    if (this.destroyed) return;
    if (!this.shouldAnimate()) {
      this.finishAll();
      return;
    }
    const vh = this.viewportHeight();
    const toObserve = [];
    const hasIO = typeof globalThis.IntersectionObserver === 'function';
    for (const entry of this.entries.values()) {
      if (entry.state === 'interrupted') {
        this.settle(entry);
      } else if (entry.state === 'pending') {
        const rect = entry.el.getBoundingClientRect?.();
        if (rect && rect.bottom <= 0) {
          this.settle(entry);
        } else if (!rect || rect.top < vh * 0.98 || !hasIO) {
          this.startEntry(entry);
        } else {
          toObserve.push(entry);
        }
      }
    }
    if (toObserve.length && hasIO) {
      this.ensureObserver();
      for (const entry of toObserve) this.observer.observe(entry.el);
    }
  }

  cancelFrame() {
    if (this.frame !== null) {
      globalThis.cancelAnimationFrame?.(this.frame);
      this.frame = null;
    }
  }

  destroy() {
    this.destroyed = true;
    this.cancelFrame();
    this.observer?.disconnect();
    this.observer = null;
    this.active.clear();
    this.abort.abort();
  }
}
