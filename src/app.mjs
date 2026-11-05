import { CatalogService } from './services/catalog.mjs';
import { VersionService } from './services/version.mjs';
import { AtlasScreen } from './screens/atlas.mjs';
import { SourcesScreen } from './screens/sources.mjs';
import { CheckScreen } from './screens/check.mjs';
import { escapeHTML, routeURL } from './screens/util.mjs';

export class ReferenceAtlasApp {
  constructor() { this.main = document.querySelector('#main'); this.catalog = null; this.screen = null; this.view = null; this.draft = ''; this.navigationSequence = 0; this.pendingTarget = null; this.intendedURL = null; this.renderedURL = location.href; this.catalogService = new CatalogService(); this.version = new VersionService({ hasDraft: () => Boolean(this.draft), onChange: status => this.showVersion(status) }); this.abort = new AbortController(); }
  async start() {
    const options = { signal: this.abort.signal };
    document.addEventListener('click', event => { const anchor = event.target.closest('a[data-nav]'); if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return; const url = new URL(anchor.href); if (url.origin !== location.origin) return; event.preventDefault(); this.navigate(url); }, options);
    window.addEventListener('popstate', () => this.navigate(new URL(location.href), { pop: true }), options);
    document.querySelector('#version-notice').addEventListener('click', event => { if (!event.target.closest('[data-discard-draft]')) return; this.draft = ''; const input = document.querySelector('#candidate-input'); if (input) input.value = ''; const target = this.pendingTarget || new URL(location.href); this.pendingTarget = null; this.navigate(target); }, options);
    this.version.attach(); await this.load(); this.version.check();
  }
  async load() {
    this.screen?.destroy(); this.screen = null; this.view = null;
    this.main.innerHTML = '<div class="loading-screen"><span class="loading-orbit" aria-hidden="true"></span><p>연구의 연결망을 펼치는 중입니다.</p></div>';
    try { this.catalog = await this.catalogService.load(); this.screen = null; this.view = null; this.render(); this.renderSnapshot(); }
    catch (error) { if (error.name === 'AbortError') return; this.main.innerHTML = `<section class="load-error"><p class="eyebrow">CATALOG UNAVAILABLE</p><h1>연결을 잠시<br><span>놓쳤습니다.</span></h1><p>${escapeHTML(error.message || '출처 목록을 불러오지 못했습니다.')}</p><button class="button button-lime" type="button" id="retry-catalog">다시 불러오기 ↻</button><a href="./data/catalog.json">출처 파일 직접 확인 ↗</a></section>`; this.main.querySelector('#retry-catalog').addEventListener('click', () => this.load(), { once: true }); }
  }
  async refreshCatalog() {
    try { const next = await this.catalogService.load(); this.catalog = next; this.screen?.destroy(); this.screen = null; this.view = null; this.render(); this.renderSnapshot(); document.querySelector('#refresh-catalog')?.focus({ preventScroll: true }); return true; }
    catch { return false; }
  }
  state(url = new URL(location.href)) { return { view: url.searchParams.get('view') || 'atlas', q: url.searchParams.get('q') || '', plugin: url.searchParams.get('plugin') || 'all', kind: url.searchParams.get('kind') || 'all', sort: url.searchParams.get('sort') || 'title', source: url.searchParams.get('source'), tag: url.searchParams.get('tag') || '' }; }
  async navigate(url, { replace = false, pop = false } = {}) {
    const sequence = ++this.navigationSequence; const target = new URL(url, document.baseURI); this.intendedURL = target;
    const outcome = await this.version.transition(target, { replace: replace || pop, isCurrent: () => sequence === this.navigationSequence });
    if (sequence !== this.navigationSequence || outcome.mode === 'document' || outcome.mode === 'stale') return;
    if (outcome.mode === 'blocked') { this.pendingTarget = target; if (pop) history.replaceState({}, '', this.renderedURL); return; }
    if (!pop) history[replace ? 'replaceState' : 'pushState']({}, '', target); this.intendedURL = null; this.pendingTarget = null;
    const previous = this.view; this.render();
    if (previous !== this.view) { window.scrollTo({ top: 0, behavior: 'instant' }); this.main.focus({ preventScroll: true }); }
  }
  setFilters(patch, { replace = false } = {}) { const target = routeURL(patch, this.intendedURL?.href || location.href); return this.navigate(target, { replace }); }
  openSource(id) { const target = routeURL({ view: 'sources', source: id }); this.navigate(target).then(() => { if (this.view === 'sources' && !this.pendingTarget) document.querySelector('#source-detail')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }); }); }
  render() {
    if (!this.catalog) return; const state = this.state(); this.renderedURL = location.href;
    for (const anchor of document.querySelectorAll('[data-view]')) { const active = state.view === anchor.dataset.view; anchor.classList.toggle('active', active); if (active) anchor.setAttribute('aria-current', 'page'); else anchor.removeAttribute('aria-current'); }
    if (this.view === state.view && this.screen) { this.screen.update(state); return; }
    this.screen?.destroy(); this.view = state.view;
    const common = { element: this.main, catalog: this.catalog, state, onSource: id => this.openSource(id) };
    if (state.view === 'atlas') this.screen = new AtlasScreen(common);
    else if (state.view === 'sources') this.screen = new SourcesScreen({ ...common, onState: (patch, options) => this.setFilters(patch, options), onRefresh: () => this.refreshCatalog() });
    else if (state.view === 'check') this.screen = new CheckScreen({ ...common, draft: this.draft, onDraft: value => { this.draft = value; if (this.version.pending) this.showVersion({ pending: this.version.pending, blocked: Boolean(value) }); } });
    else { this.screen = null; this.main.innerHTML = '<section class="load-error"><p class="eyebrow">VIEW NOT FOUND</p><h1>지도를 벗어난<br><span>주소입니다.</span></h1><p>요청한 화면을 찾을 수 없습니다.</p><a class="button button-lime" href="?view=atlas" data-nav>연구 지도로 돌아가기 ↗</a></section>'; return; }
    this.screen.mount();
  }
  showVersion({ pending, blocked = false }) { const notice = document.querySelector('#version-notice'); notice.hidden = !pending; if (!pending) { notice.innerHTML = ''; return; } notice.innerHTML = `<p>${blocked ? '새 버전이 준비됐습니다. 작성 중인 확인 목록을 유지하고 있습니다.' : '새 버전이 준비됐습니다. 다음 화면 이동에 자동 반영됩니다.'}</p>${blocked ? '<button type="button" data-discard-draft>입력 지우고 계속 →</button>' : ''}`; }
  renderSnapshot() { const snapshots = this.catalog.snapshots || {}; const values = Array.isArray(snapshots) ? snapshots : Object.values(snapshots); const parts = values.map(value => [value.name || value.plugin || '', value.version || '', value.commit ? value.commit.slice(0, 7) : ''].filter(Boolean).join(' ')); document.querySelector('#snapshot-label').textContent = parts.length ? parts.join(' · ') : `공개 출처 스냅샷 · ${this.catalog.updatedAt?.slice(0, 10) || ''}`; }
  destroy() { this.screen?.destroy(); this.catalogService.destroy(); this.version.destroy(); this.abort.abort(); }
}

if (typeof document !== 'undefined') { const application = new ReferenceAtlasApp(); window.referenceAtlas = application; application.start(); }
