import {createHash} from 'node:crypto';
export function calculateBuildIdentity(html,entries){
  const normalize=value=>value.replace(/\r\n?/g,'\n');
  const sorted=entries.map(([name,text])=>[name.replaceAll('\\','/'),normalize(text)]).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
  return createHash('sha256').update(normalize(html)+sorted.map(([name,text])=>name+'\n'+text).join('\n')).digest('hex').slice(0,16);
}
