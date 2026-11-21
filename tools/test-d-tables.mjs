// Compares the JS table builders of web/js/plastik-d.mjs with the RAM of the original (re/golden/d-inputs.bin, written by re/harness.py DUMPD, see re/NOTES.md)
import fs from 'fs';import {logExp,palette,darkTable} from '../web/js/plastik-d.mjs';
const b=fs.readFileSync(new URL('../re/golden/d-inputs.bin',import.meta.url));
const L={log:0x200,exp:0x200,scale:0x6000,pal:768,pal0:768};let o=0;const g={};for(const k in L){g[k]=b.subarray(o,o+L[k]);o+=L[k];}
const diff=(a,c)=>{let n=0;for(let i=0;i<Math.min(a.length,c.length);i++)if(a[i]!==c[i])n++;return n;};
const T=logExp(),P=palette(g.pal0,T),S=darkTable(P);let bad=0;
for(const [n,a,c] of [['log',T.log,g.log],['exp',T.exp,g.exp],['palette',P,g.pal],['dark scale table',S,g.scale]]){const d=diff(a,c);console.log(n,d?'FAIL '+d+' bytes differ':'exact',c.length+' bytes');bad+=d;}
process.exit(bad?1:0);
