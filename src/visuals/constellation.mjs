export class Constellation {
  constructor(element, sources, onSelect) {
    this.element = element; this.sources = sources; this.onSelect = onSelect; this.canvas = element.querySelector('canvas'); this.context = this.canvas.getContext('2d'); this.label = element.querySelector('.map-tooltip'); this.reduced = matchMedia('(prefers-reduced-motion: reduce)'); this.hovered = null; this.pointer = { x: -9999, y: -9999 }; this.frame = null; this.started = performance.now(); this.abort = new AbortController();
    if (!this.context) return;
    this.resize = new ResizeObserver(() => { this.measure(); if (this.reduced.matches) this.draw(performance.now()); }); this.resize.observe(element);
    const options = { signal: this.abort.signal };
    this.canvas.addEventListener('pointermove', event => { const rect = this.canvas.getBoundingClientRect(); this.pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top }; if (this.reduced.matches) this.draw(performance.now()); }, options);
    this.canvas.addEventListener('pointerleave', () => { this.pointer = { x: -9999, y: -9999 }; this.hovered = null; this.label.hidden = true; }, options);
    this.canvas.addEventListener('click', () => { if (this.hovered) this.onSelect(this.hovered); }, options);
    this.measure(); this.tick = time => { this.draw(time); if (!this.reduced.matches) this.frame = requestAnimationFrame(this.tick); }; this.frame = requestAnimationFrame(this.tick);
    this.reduced.addEventListener('change', () => { cancelAnimationFrame(this.frame); this.frame = requestAnimationFrame(this.tick); }, options);
  }
  hash(text) { let value = 2166136261; for (const char of text) value = Math.imul(value ^ char.charCodeAt(0), 16777619); return (value >>> 0) / 4294967295; }
  measure() { this.width = this.element.clientWidth; this.height = this.element.clientHeight; const ratio = Math.min(devicePixelRatio || 1, 1.5); this.canvas.width = Math.round(this.width * ratio); this.canvas.height = Math.round(this.height * ratio); this.context.setTransform(ratio, 0, 0, ratio, 0, 0); const avY=matchMedia('(min-width:721px)').matches?.68:.5; this.hubs = [{ x: this.width * .36, y: this.height * avY, plugin: 'agentic-vault', color: '#d3fc70' }, { x: this.width * .68, y: this.height * .5, plugin: 'semantic-crosscheck', color: '#c3b0f6' }]; }
  draw(time) {
    const ctx = this.context, w = this.width, h = this.height; if (!w || !h) return; ctx.clearRect(0, 0, w, h); const elapsed = this.reduced.matches ? 0 : (time - this.started) / 1000;
    const center = { x: w * .52, y: h * .5 };
    ctx.save(); ctx.translate(center.x, center.y); ctx.strokeStyle = 'rgba(212,225,205,.065)'; ctx.lineWidth = 1;
    for (const scale of [.57, .82, 1.08]) { ctx.beginPath(); ctx.ellipse(0, 0, w * .41 * scale, h * .42 * scale, -.22, 0, Math.PI * 2); ctx.stroke(); }
    for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 6) { ctx.beginPath(); ctx.moveTo(Math.cos(angle) * w * .08, Math.sin(angle) * h * .08); ctx.lineTo(Math.cos(angle) * w * .49, Math.sin(angle) * h * .47); ctx.stroke(); }
    ctx.restore();
    const nodes = this.sources.slice(0, 180).map((source, index) => {
      const seed = this.hash(source.id), ring = .64 + (index % 3) * .16; const angle = (index / Math.max(1, Math.min(this.sources.length, 180))) * Math.PI * 2 + seed * .2 + elapsed * .008;
      return { source, x: center.x + Math.cos(angle) * w * .47 * ring + Math.sin(elapsed * .18 + seed * 8) * 4, y: center.y + Math.sin(angle) * h * .43 * ring + Math.cos(elapsed * .15 + seed * 9) * 4, seed };
    });
    let hit = null, closest = 20;
    for (const node of nodes) { const distance = Math.hypot(node.x - this.pointer.x, node.y - this.pointer.y); if (distance < closest) { closest = distance; hit = node; } }
    this.hovered = hit?.source || null;
    for (const node of nodes) {
      const plugins = new Set(node.source.uses.map(use => use.plugin)); const active = hit === node;
      for (const hub of this.hubs) {
        if (!plugins.has(hub.plugin)) continue;
        ctx.beginPath(); ctx.moveTo(hub.x, hub.y); ctx.quadraticCurveTo((hub.x + node.x) / 2, (hub.y + node.y) / 2 - (node.seed - .5) * 75, node.x, node.y); ctx.strokeStyle = active ? hub.color : hub.plugin === 'agentic-vault' ? 'rgba(211,252,112,.12)' : 'rgba(195,176,246,.13)'; ctx.lineWidth = active ? 1.5 : .65; ctx.stroke();
        if (!this.reduced.matches && (Math.floor(node.seed * 100) % 7 === 0 || active)) { const t = (elapsed * .14 + node.seed) % 1; const x = hub.x + (node.x - hub.x) * t, y = hub.y + (node.y - hub.y) * t; ctx.beginPath(); ctx.arc(x, y, active ? 2.2 : 1.4, 0, Math.PI * 2); ctx.fillStyle = hub.color; ctx.fill(); }
      }
      const shared = plugins.size > 1; ctx.beginPath(); ctx.arc(node.x, node.y, active ? 7 : shared ? 4.2 : 2.7, 0, Math.PI * 2); ctx.fillStyle = shared ? '#f5f6ee' : plugins.has('agentic-vault') ? '#d3fc70' : '#c3b0f6'; ctx.shadowBlur = active ? 24 : shared ? 12 : 3; ctx.shadowColor = ctx.fillStyle; ctx.fill(); ctx.shadowBlur = 0;
      if (active) { ctx.beginPath(); ctx.arc(node.x, node.y, 13, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(245,246,238,.45)'; ctx.stroke(); }
    }
    for (const hub of this.hubs) {
      const glow = ctx.createRadialGradient(hub.x, hub.y, 4, hub.x, hub.y, 100); glow.addColorStop(0, hub.plugin === 'agentic-vault' ? 'rgba(211,252,112,.17)' : 'rgba(195,176,246,.17)'); glow.addColorStop(1, 'transparent'); ctx.fillStyle = glow; ctx.fillRect(hub.x - 100, hub.y - 100, 200, 200);
      ctx.beginPath(); ctx.arc(hub.x, hub.y, 53, 0, Math.PI * 2); ctx.fillStyle = '#141911'; ctx.fill(); ctx.strokeStyle = hub.color; ctx.lineWidth = 1.2; ctx.stroke(); ctx.beginPath(); ctx.arc(hub.x, hub.y, 62 + Math.sin(elapsed * .6) * 2, 0, Math.PI * 2); ctx.strokeStyle = hub.plugin === 'agentic-vault' ? 'rgba(211,252,112,.17)' : 'rgba(195,176,246,.17)'; ctx.stroke();
    }
    if (hit) { this.label.hidden = false; this.label.textContent = hit.source.title; this.label.style.left = `${Math.min(Math.max(hit.x, 120), w - 120)}px`; this.label.style.top = `${Math.max(12, hit.y - 34)}px`; this.canvas.style.cursor = 'pointer'; } else { this.label.hidden = true; this.canvas.style.cursor = 'default'; }
  }
  destroy() { cancelAnimationFrame(this.frame); this.resize?.disconnect(); this.abort.abort(); }
}
