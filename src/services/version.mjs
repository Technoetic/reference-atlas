export class VersionService {
  constructor({ baseURL = document.baseURI, loadedBuild = document.querySelector('meta[name="build-id"]')?.content || '', hasDraft = () => false, onChange = () => {}, fetcher = fetch, navigate = (url, replace) => replace ? location.replace(url) : location.assign(url), clock = () => Date.now(), timeoutMs = 4500 } = {}) {
    this.baseURL = baseURL; this.loadedBuild = loadedBuild; this.hasDraft = hasDraft; this.onChange = onChange; this.fetcher = fetcher.bind(globalThis); this.navigate = navigate; this.clock = clock; this.timeoutMs = timeoutMs; this.pending = null; this.inflight = null; this.error = null; this.listeners = null;
  }
  async check() {
    if (!this.loadedBuild || this.loadedBuild.includes('__BUILD_ID__') || this.loadedBuild === 'dev') return null;
    if (this.inflight) return this.inflight;
    this.inflight = (async () => {
      const controller = new AbortController(); let timeout;
      try {
        const url = new URL('version.json', this.baseURL); url.searchParams.set('_at', String(this.clock()));
        const request = (async () => { const response = await this.fetcher(url, { cache: 'no-store', signal: controller.signal }); if (!response.ok) throw new Error('version unavailable'); return response.json(); })();
        const expired = new Promise((_, reject) => { timeout = setTimeout(() => { controller.abort(); reject(new Error('version timeout')); }, this.timeoutMs); });
        const value = await Promise.race([request, expired]);
        if (typeof value.buildId !== 'string' || !/^[a-zA-Z0-9._-]{1,120}$/.test(value.buildId)) throw new Error('invalid version');
        this.pending = value.buildId !== this.loadedBuild ? value.buildId : null; this.error = null;
      } catch { this.error = 'unavailable'; } finally { clearTimeout(timeout); }
      this.onChange({ pending: this.pending, error: this.error, blocked: Boolean(this.pending && this.hasDraft()) });
      return this.pending;
    })().finally(() => { this.inflight = null; });
    return this.inflight;
  }
  async transition(target, { replace = false, isCurrent = () => true } = {}) {
    await this.check();
    if (!isCurrent()) return { mode: 'stale' };
    if (this.error || !this.pending) return { mode: 'internal' };
    if (this.hasDraft()) { this.onChange({ pending: this.pending, error: this.error, blocked: true }); return { mode: 'blocked' }; }
    const url = new URL(target, this.baseURL); url.searchParams.set('_build', this.pending);
    // Recheck immediately before document navigation: input may have changed while awaiting I/O.
    if (this.hasDraft()) return { mode: 'blocked' };
    if (!isCurrent()) return { mode: 'stale' };
    this.navigate(url.href, replace); return { mode: 'document', url: url.href };
  }
  attach(win = window, doc = document) { this.listeners = new AbortController(); const options = { signal: this.listeners.signal }; win.addEventListener('focus', () => this.check(), options); win.addEventListener('pageshow', () => this.check(), options); doc.addEventListener('visibilitychange', () => { if (doc.visibilityState === 'visible') this.check(); }, options); }
  destroy() { this.listeners?.abort(); }
}
