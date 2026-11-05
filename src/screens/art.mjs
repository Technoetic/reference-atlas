import {artworkIndex} from './artwork-index.mjs';

const escapeText=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const missingArtwork=Object.freeze({key:'unassigned',src:null,label:'REFERENCE RECORD',word:'REFERENCE'});

export function sourceArtwork(source) {
  return Object.hasOwn(artworkIndex,source.id)?artworkIndex[source.id]:missingArtwork;
}

export function artworkCover(source,{detail=false}={}) {
  const art=sourceArtwork(source);
  const image=art.src?`<img data-source-artwork src="${escapeText(art.src)}" alt="" width="960" height="640" loading="lazy" decoding="async">`:'';
  return `<span class="${detail?'detail-art':'source-art'} artwork-${art.key}${art.src?'':' is-art-fallback'}" aria-hidden="true">${image}<span class="art-fallback"><b>${escapeText(art.word)}</b><i>↗</i></span><span class="art-topic">${escapeText(art.label)}</span><span class="art-cover-mark">↗</span></span>`;
}

if(typeof document!=='undefined')document.addEventListener('error',event=>{
  const image=event.target;
  if(!image?.matches?.('img[data-source-artwork]'))return;
  image.hidden=true;
  image.closest('.source-art, .detail-art')?.classList.add('is-art-fallback');
},true);
