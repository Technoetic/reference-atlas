import { findMatches } from '../core/catalog.mjs';
import { escapeHTML, sourceBadges } from './util.mjs';

const labels = { known: ['이미 참조한 자료', 'known'], possible: ['유사한 이름 기록', 'possible'], not_found: ['목록에서 찾지 못함', 'not-found'], invalid: ['식별 정보를 확인해 주세요', 'invalid'] };
export class CheckScreen {
  constructor({ element, catalog, draft = '', onDraft, onSource }) { this.element = element; this.catalog = catalog; this.draft = draft; this.onDraft = onDraft; this.onSource = onSource; this.abort = new AbortController(); }
  mount() {
    this.element.innerHTML = `<section class="checker-page"><div class="page-heading"><p class="eyebrow">BEFORE THE NEXT DEEP DIVE / 중복 확인</p><h1>SEEN IT<br><span>BEFORE?</span></h1><p>새로운 참고 자료라고 말하기 전에.<br>논문과 프로젝트의 기존 참조 기록을 확인하세요.</p></div><div class="checker-layout"><form class="checker-form"><label for="candidate-input"><span>확인할 자료</span><span>한 줄에 하나씩 입력</span></label><textarea id="candidate-input" rows="7" spellcheck="false" placeholder="https://arxiv.org/abs/2502.12110v2&#10;https://github.com/google-research/harness2&#10;논문 제목 또는 DOI"></textarea><div class="input-meta"><p><span class="private-dot" aria-hidden="true"></span>입력은 이 브라우저 안에서만 대조합니다.</p><button type="button" class="clear-input">입력 지우기</button></div><button class="button button-lime check-submit" type="submit">기존 참조 확인 <span aria-hidden="true">↗</span></button><div class="checker-examples"><span>이런 주소도 같은 자료로 확인합니다.</span><code>arXiv의 abs / pdf / 버전 주소</code><code>GitHub의 하위 파일 / 커밋 주소</code></div></form><aside class="checker-guide"><span class="guide-mark" aria-hidden="true">≠</span><h2>이미 참고했다면,<br>다음 질문으로.</h2><ol><li><b>기존 기록을 확인한다.</b><span>어느 플러그인이 무엇을 참고했는지 근거를 따라갑니다.</span></li><li><b>달라진 점을 적는다.</b><span>새 버전, 새로운 질문, 아직 반영하지 않은 부분을 구분합니다.</span></li><li><b>차이가 있을 때 다시 검토한다.</b><span>단순 재추천 대신, 이번에 새로 검토하는 이유를 남깁니다.</span></li></ol><p>목록에 없다고 새로운 연구로 확인된 것은 아닙니다. 이 대장은 공개 저장소의 특정 시점 기록입니다.</p></aside></div><section id="check-results" class="check-results" aria-live="polite"></section></section>`;
    const input = this.element.querySelector('#candidate-input'); input.value = this.draft;
    const options = { signal: this.abort.signal };
    input.addEventListener('input', () => { this.draft = input.value; this.onDraft(this.draft); }, options);
    this.element.querySelector('.clear-input').addEventListener('click', () => { input.value = ''; this.draft = ''; this.onDraft(''); this.element.querySelector('#check-results').innerHTML = ''; input.focus(); }, options);
    this.element.querySelector('form').addEventListener('submit', event => { event.preventDefault(); this.run(input.value); }, options);
    this.element.addEventListener('click', event => { const source = event.target.closest('[data-source]'); if (source) this.onSource(source.dataset.source); }, options);
  }
  run(value) {
    const candidates = value.split(/\r?\n/).map(input => input.trim()).filter(Boolean).slice(0, 100);
    const container = this.element.querySelector('#check-results');
    if (!candidates.length) { container.innerHTML = '<div class="check-empty"><p>논문 주소, DOI, 저장소 주소 또는 제목을 먼저 입력해 주세요.</p></div>'; return; }
    const rows = candidates.map(input => ({ input, result: findMatches(this.catalog, input) }));
    const known = rows.filter(row => row.result.status === 'known').length;
    container.innerHTML = `<div class="check-result-heading"><p class="eyebrow">CHECKED AGAINST THIS SNAPSHOT</p><h2>${candidates.length}개 확인. <span>기존 참조 ${known}개.</span></h2>${value.split(/\r?\n/).filter(row => row.trim()).length > 100 ? '<p>한 번에 100개까지 표시합니다. 나머지는 나누어 확인해 주세요.</p>' : ''}</div><div class="check-result-list">${rows.map(({ input, result }, index) => { const [label, style] = labels[result.status] || labels.invalid; return `<article class="check-result ${style}"><div class="check-result-number">${String(index + 1).padStart(2, '0')}</div><div class="check-result-body"><p class="check-input">${escapeHTML(input)}</p><span class="match-status"><i aria-hidden="true"></i>${label}</span>${result.key ? `<code class="matched-key">${escapeHTML(typeof result.key === 'string' ? result.key : result.key.key || '')}</code>` : ''}${(result.matches || []).map(source => `<button type="button" data-source="${escapeHTML(source.id)}" class="matched-source"><span>${escapeHTML(source.title)}</span><span class="plugin-badges">${sourceBadges(source)} <b aria-hidden="true">↗</b></span></button>`).join('')}${result.status === 'not_found' ? '<p class="result-limit">이 스냅샷에서 발견되지 않았습니다. 다른 이름·공식 원문·최신 버전도 확인하세요.</p>' : ''}${result.status === 'possible' ? '<p class="result-limit">이름이 비슷한 후보입니다. 같은 자료인지 원문으로 확인해야 합니다.</p>' : ''}${result.status === 'invalid' ? '<p class="result-limit">주소나 식별자를 확인하고, 제목은 충분한 단어로 입력해 주세요.</p>' : ''}</div></article>`; }).join('')}</div>`;
  }
  update() {}
  destroy() { this.abort.abort(); }
}
