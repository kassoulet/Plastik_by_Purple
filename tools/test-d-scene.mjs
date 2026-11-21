// node tools/test-d-scene.mjs GOLDEN_DIR [nframes]  (golden = harness PNGs f%05d.png)
import fs from 'fs'; import zlib from 'zlib'; import {runD,unpackInit} from '../web/js/plastik-d-scene.mjs';
const [gold,nf='80']=process.argv.slice(2);
const xm=JSON.parse(fs.readFileSync(new URL('../re/xm_times/system.json',import.meta.url))), F0=2629;
const png=p=>{const b=fs.readFileSync(p);let o=8,idat=[],w,h;while(o<b.length){const l=b.readUInt32BE(o),t=b.toString('latin1',o+4,o+8);if(t==='IHDR'){w=b.readUInt32BE(o+8);h=b.readUInt32BE(o+12);}if(t==='IDAT')idat.push(b.subarray(o+8,o+8+l));o+=12+l;}
  const raw=zlib.inflateSync(Buffer.concat(idat)),st=w*3,out=Buffer.alloc(w*h*3);for(let y=0;y<h;y++){const ft=raw[y*(st+1)];for(let x=0;x<st;x++){const v=raw[y*(st+1)+1+x],a=x>=3?out[y*st+x-3]:0,u=y?out[(y-1)*st+x]:0,c=x>=3&&y?out[(y-1)*st+x-3]:0;
    out[y*st+x]=(v+(ft===0?0:ft===1?a:ft===2?u:ft===3?(a+u)>>1:(()=>{const p=a+u-c,pa=Math.abs(p-a),pb=Math.abs(p-u),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?u:c;})()))&255;}}return out;};
const rgb=(a)=>{const r=((a>>11)&31)<<3,g=((a>>5)&63)<<2,b=(a&31)<<3;return [r|(r>>5),g|(g>>6),b|(b>>5)];};
let bad=0,chk=0;
runD(unpackInit(fs.readFileSync(new URL('../web/assets/plastik-d-init.bin',import.meta.url))),xm,F0,+nf,(fb,n)=>{
  const k=F0+n+1;  // the display lags one flip: the picture shown at flip k is the one rendered in flip k-1 (golden frame F0 is stale memory)
  if(k%100&&!process.env.ALL) return; const g=png(`${gold}/f${String(k).padStart(5,'0')}.png`),u=new Uint16Array(fb.buffer,fb.byteOffset,640*400);
  let d=0;for(let i=0;i<640*400;i++){const c=rgb(u[i]);if(c[0]!==g[3*i]||c[1]!==g[3*i+1]||c[2]!==g[3*i+2])d++;} chk++; if(d)bad++; console.log('frame',k,'diff px',d);});
console.log(chk,'checked',bad,'bad');
