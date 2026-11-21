// node tools/test-scene.mjs a|b INIT.bin RAW_DIR [nframes]   RAW_DIR = harness RAW=dir RAWSTEP=1 (f%05d.npy, raw RGB565 640x400)
// JS frame n is golden flip n+1 (the display lags the render by one flip; flip 0 is blank).  Prints the first differing frame.
import fs from 'fs'; const [id,init,dir,nf='100']=process.argv.slice(2),F0={a:0,b:955,c:1912,e:3346,f:3824,g:4302,h:5006}[id],{unpackInit,...M}=await import(`../web/js/plastik-${id}-scene.mjs`), xm=JSON.parse(fs.readFileSync(new URL('../re/xm_times/system.json',import.meta.url)));
const npy=p=>{const b=fs.readFileSync(p),h=b.readUInt16LE(8);return new Uint16Array(b.buffer.slice(b.byteOffset+10+h,b.byteOffset+b.length));};
const a=new M[id.toUpperCase()+'Scene'](unpackInit(fs.readFileSync(init)),xm,F0); let bad=0;
for(let n=0;n<+nf;n++){const s=a.step(); if(!s) break; const g=npy(`${dir}/f${String(F0+n+1).padStart(5,'0')}.npy`),u=new Uint16Array(s.buffer,s.byteOffset,640*400);
  let d=0;for(let i=0;i<u.length;i++)if(u[i]!==g[i])d++; if(d){bad++; if(bad<=5||process.env.ALL)console.log('flip',n+1,'diff px',d);}}
console.log(nf,'frames',bad,'bad'); process.exit(bad?1:0);
