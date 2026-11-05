const artworks = Object.freeze({
  amem: { key: 'amem', src: new URL('../../media/amem.webp', import.meta.url).href, label: 'CONNECTED MEMORY', word: 'A-MEM' },
  memory: { key: 'memory', src: new URL('../../media/memory.webp', import.meta.url).href, label: 'MEMORY & RETRIEVAL', word: 'MEMORY' },
  evaluation: { key: 'evaluation', src: new URL('../../media/evaluation.webp', import.meta.url).href, label: 'EVALUATION & TESTING', word: 'EVALUATE' },
  reliability: { key: 'reliability', src: new URL('../../media/reliability.webp', import.meta.url).href, label: 'RELIABLE SYSTEMS', word: 'RELIABILITY' },
  agents: { key: 'agents', src: new URL('../../media/agents.webp', import.meta.url).href, label: 'AGENTIC SYSTEMS', word: 'AGENTS' },
  knowledge: { key: 'knowledge', src: new URL('../../media/knowledge.webp', import.meta.url).href, label: 'CONNECTED KNOWLEDGE', word: 'KNOWLEDGE' },
  sql: { key: 'sql', src: new URL('../../media/sql.webp', import.meta.url).href, label: 'QUERIES & DATA', word: 'DATA' },
  security: { key: 'security', src: new URL('../../media/security.webp', import.meta.url).href, label: 'SECURITY & SAFETY', word: 'SECURITY' }
});

// Specific topics win over broad ones. The same tags always select the same artwork.
const topicPriority = [
  ['보안·안전', 'security'],
  ['SQL', 'sql'],
  ['지식 그래프', 'knowledge'],
  ['평가·테스트', 'evaluation'],
  ['에이전트', 'agents'],
  ['메모리·검색', 'memory'],
  ['신뢰성', 'reliability']
];

export function sourceArtwork(source) {
  const keys = new Set([source.id, ...(source.keys || [])]);
  if (keys.has('arxiv:2502.12110') || keys.has('github:wujiangxu/a-mem-sys')) return artworks.amem;
  const tags = new Set(source.tags || []);
  const matched = topicPriority.find(([tag]) => tags.has(tag));
  return artworks[matched?.[1] || 'agents'];
}

export function artworkCover(source, { detail = false } = {}) {
  const art = sourceArtwork(source);
  return `<span class="${detail ? 'detail-art' : 'source-art'} artwork-${art.key}" aria-hidden="true"><img data-source-artwork src="${art.src}" alt="" width="960" height="640" loading="lazy" decoding="async"><span class="art-fallback"><b>${art.word}</b><i>↗</i></span><span class="art-topic">${art.label}</span><span class="art-cover-mark">↗</span></span>`;
}

// Image failures do not remove the title, tags, plugin names or source evidence.
if (typeof document !== 'undefined') document.addEventListener('error', event => {
  const image = event.target;
  if (!image?.matches?.('img[data-source-artwork]')) return;
  image.hidden = true;
  image.closest('.source-art, .detail-art')?.classList.add('is-art-fallback');
}, true);
