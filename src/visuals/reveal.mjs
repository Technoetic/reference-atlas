const DEFAULT_CLEANUP_MS = 1000;

export class ScrollReveal {
  constructor(root, { selector = '[data-reveal]' } = {}) {
    this.root = root;
    this.selector = selector;
    this.abort = new AbortController();
    this.destroyed = false;
    this.observer = null;
    this.pending = new Set();
    this.timers = new Set();
    this.reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)') || null;

    this.attachListeners();
    this.refresh();
  }

  attachListeners() {
    const options = { signal: this.abort.signal };
    this.reduced?.addEventListener?.('change', event => {
      if (event.matches) this.revealAll();
    }, options);
    this.root?.addEventListener?.('focusin', event => {
      const target = event.target?.closest?.('.reveal-pending');
      if (target) this.reveal(target);
    }, options);
    globalThis.addEventListener?.('beforeprint', () => this.revealAll(), options);
    globalThis.addEventListener?.('scrollend', () => this.sync(), { passive: true, signal: this.abort.signal });
    globalThis.addEventListener?.('pagehide', () => this.pauseForPageHide(), options);
    globalThis.addEventListener?.('pageshow', event => {
      if (event?.persisted) this.resumeFromBFCache();
    }, options);
  }

  viewportHeight() {
    return Number(globalThis.innerHeight) || 900;
  }

  refresh() {
    if (this.destroyed) return;
    this.observer?.disconnect();
    this.observer = null;
    this.pending.clear();

    const nodes = [...(this.root?.querySelectorAll?.(this.selector) || [])];
    if (!nodes.length) return;

    const reduced = Boolean(this.reduced?.matches);
    const hasIO = typeof globalThis.IntersectionObserver === 'function';
    if (reduced || !hasIO) {
      for (const el of nodes) this.markRevealed(el);
      return;
    }

    const vh = this.viewportHeight();
    const belowFold = [];

    for (const el of nodes) {
      if (el.classList?.contains('is-revealed')) continue;
      const rect = el.getBoundingClientRect?.();
      if (!rect || rect.top < vh * 0.98) {
        this.markRevealed(el);
      } else {
        el.classList?.add('reveal-pending');
        this.pending.add(el);
        belowFold.push(el);
      }
    }

    if (belowFold.length) {
      this.ensureObserver();
      for (const el of belowFold) this.observer.observe(el);
    }
  }

  ensureObserver() {
    if (this.observer || typeof globalThis.IntersectionObserver !== 'function') return;
    this.observer = new globalThis.IntersectionObserver(records => {
      if (this.destroyed) return;
      const vh = this.viewportHeight();
      for (const record of records) {
        if (!this.pending.has(record.target)) continue;
        const rect = record.boundingClientRect;
        if (record.isIntersecting || (rect && rect.top < vh)) {
          this.reveal(record.target, { immediate: Boolean(rect && rect.bottom <= 0) });
        }
      }
    }, { threshold: 0, rootMargin: '100000px 0px 40px 0px' });
  }

  sync({ immediate = false } = {}) {
    if (this.destroyed) return;
    if (this.reduced?.matches) {
      this.revealAll();
      return;
    }
    const vh = this.viewportHeight();
    for (const el of [...this.pending]) {
      const rect = el.getBoundingClientRect?.();
      if (!rect || rect.top < vh * 0.98) {
        this.reveal(el, { immediate: immediate || Boolean(rect && rect.bottom <= 0) });
      }
    }
  }

  reveal(el, { immediate = false } = {}) {
    if (!el) return;
    this.observer?.unobserve(el);
    this.pending.delete(el);
    if (immediate || this.reduced?.matches) {
      this.markRevealed(el);
      return;
    }
    el.classList?.add('reveal-entering');
    el.classList?.remove('reveal-pending');

    let finished = false;
    const onEnd = event => {
      if (event && event.target !== el) return;
      finish();
    };
    const finish = () => {
      if (finished) return;
      finished = true;
      el.removeEventListener?.('transitionend', onEnd);
      el.classList?.remove('reveal-entering');
      el.classList?.add('is-revealed');
      if (timer != null) {
        globalThis.clearTimeout?.(timer);
        this.timers.delete(timer);
      }
    };

    el.addEventListener?.('transitionend', onEnd, { signal: this.abort.signal });
    const timer = globalThis.setTimeout?.(() => finish(), DEFAULT_CLEANUP_MS);
    if (timer != null) this.timers.add(timer);
  }

  markRevealed(el) {
    this.observer?.unobserve(el);
    this.pending.delete(el);
    el.classList?.remove('reveal-pending', 'reveal-entering');
    el.classList?.add('is-revealed');
  }

  revealAll() {
    this.observer?.disconnect();
    this.observer = null;
    for (const el of [...this.pending]) this.markRevealed(el);
    const nodes = this.root?.querySelectorAll?.('.reveal-pending, .reveal-entering') || [];
    for (const el of nodes) this.markRevealed(el);
  }

  pauseForPageHide() {
    this.observer?.disconnect();
    this.observer = null;
  }

  resumeFromBFCache() {
    if (this.destroyed) return;
    if (this.reduced?.matches) {
      this.revealAll();
      return;
    }
    const vh = this.viewportHeight();
    const stillBelow = [];
    for (const el of [...this.pending]) {
      const rect = el.getBoundingClientRect?.();
      if (!rect || rect.top < vh * 0.98) {
        this.reveal(el, { immediate: Boolean(rect && rect.bottom <= 0) });
      } else {
        stillBelow.push(el);
      }
    }
    if (stillBelow.length && typeof globalThis.IntersectionObserver === 'function') {
      this.ensureObserver();
      for (const el of stillBelow) this.observer.observe(el);
    }
  }

  destroy() {
    this.destroyed = true;
    this.observer?.disconnect();
    this.observer = null;
    for (const timer of this.timers) globalThis.clearTimeout?.(timer);
    this.timers.clear();
    this.pending.clear();
    this.abort.abort();
  }
}
