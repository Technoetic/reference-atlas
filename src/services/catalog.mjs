import {validateCatalog} from '../core/validation.mjs';
export class CatalogService {
  constructor({ baseURL = document.baseURI, fetcher = fetch } = {}) { this.baseURL = baseURL; this.fetcher = fetcher.bind(globalThis); this.controller = null; this.sequence = 0; }
  async load() {
    const sequence = ++this.sequence;
    this.controller?.abort(); this.controller = new AbortController(); const controller = this.controller;
    const timeout = setTimeout(() => controller.abort('timeout'), 12000);
    const url = new URL('data/catalog.json', this.baseURL); url.searchParams.set('_at', String(Date.now()));
    try {
      const response = await this.fetcher(url, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`출처 목록을 가져오지 못했습니다. (HTTP ${response.status})`);
      const catalog = await response.json();
    validateCatalog(catalog);
      if (sequence !== this.sequence) throw new DOMException('A newer request replaced this result.', 'AbortError');
      return catalog;
    } catch (error) { if (controller.signal.reason === 'timeout') throw new Error('출처 목록의 응답이 늦어지고 있습니다. 연결을 확인하고 다시 시도해 주세요.'); throw error; }
    finally { clearTimeout(timeout); }
  }
  destroy() { this.controller?.abort(); }
}
