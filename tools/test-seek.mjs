// Seek check: frames reached by checkpoint restore must equal those of a straight run.  usage: node tools/test-seek.mjs [a|b|c|d|e|f|g|h] [init.bin]
import fs from 'fs';
const id=process.argv[2]||'d',m=await import(`../web/js/plastik-${id}-scene.mjs`),Sc=m[id.toUpperCase()+'Scene'],f0={a:0,b:955,c:1912,d:2629,e:3346,f:3824,g:4302,h:5006}[id];
const init=m.unpackInit(fs.readFileSync(process.argv[3]||new URL(`../web/assets/plastik-${id}-init.bin`,import.meta.url))),xm=JSON.parse(fs.readFileSync(new URL('../re/xm_times/system.json',import.meta.url)));
const MAX=id==='h'?249:451,want=[10,99,100,120,149,150,300,449,451].filter(n=>n<=MAX),ref={};  // one scene at a time: the memory is a module singleton
const d0=new Sc(init,xm,f0);for(let n=0;n<=MAX;n++){const s=d0.step();if(want.includes(n))ref[n]=s.slice();}
const d=new Sc(init,xm,f0);
for(let n=0;n<=MAX;n++)d.step();
let bad=0; for(const n of [451,120,300,10,150,449,100].filter(n=>n<=MAX)){ const s=d.frame(n); if(want.includes(n)&&Buffer.compare(Buffer.from(s),Buffer.from(ref[n]))) {bad++;console.log('BAD',n);} }
console.log(bad?'FAIL':'seek ok ('+id+')');process.exit(bad?1:0);
