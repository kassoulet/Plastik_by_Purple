// Scene D driver: runs the recompiled original code (plastik-d.gen.mjs) on the flat memory of x86rt.mjs.
// Time model = re/harness.py: each presented frame adds K ticks to [0xec0030]; 0x3d220 answers from the XM row table.
import * as R from './x86rt.mjs';
import {Scene,K,HZ} from './scene.mjs';
import {logExp,palette,scaleTable} from './plastik-d.mjs';
import {block} from './plastik-d-block.mjs';
import {f_1ddb4,setRegs,getRegs} from './plastik-d.gen.mjs';
export const BUF=0x1300000, TEX=0x1380000, PAL0=0x1390000, PAL=0x1391000;
// init = plastik-d-init.bin (see re/mk_dinit.py), xm = system.json, f0 = flip index at D entry (2629 in the K=3 capture)
export function unpackInit(b){const u=new Uint8Array(b),L=[0x1c000,0x11000,0x10000,0x300,0x2100],n=['mem','mem2','tex','pal0','stk'],o={};let p=0;L.forEach((l,i)=>{o[n[i]]=u.subarray(p,p+=l);});return o;}
const RESUME=0x1e3c8;  // instruction after "call present" inside f_1ddb4: natives are esp-neutral, so a Stop thrown from present can be resumed here
export class DScene extends Scene{
  constructor(init,xm,f0){
    super({gen:{entry:f_1ddb4,resume:RESUME,setRegs,getRegs},xm,f0,esp:0x1400804,lim:0x1500000,bufPtr:()=>BUF,   // esp&7=4 like the original: 1d9bc does and esp,-8
      load:m8=>{ m8.set(init.mem,0x100000); m8.set(init.mem2,0xb35000); m8.set(init.tex,TEX); m8.set(init.pal0,PAL0);
        const T=logExp(),P=palette(init.pal0,T); m8.set(T.log,0xc51700); m8.set(T.exp,0xb80120); m8.set(P,PAL); m8.set(scaleTable(P),0xc1afc0);
        const w=(a,v)=>R.wr32(a,v); w(0xebea78,BUF); w(0xebea5c,TEX); w(0xebea80,PAL0); w(0x103190,PAL);
        m8.set(init.stk,0x1400804-0x2000);},   // the original reads uninitialised stack slots in its first frame: replay the stack as the emulator had it
      setup:()=>{R.S.blk=block;}});
  }
}
export function runD(init,xm,f0,nFrames,onFrame){ const d=new DScene(init,xm,f0); for(let i=0;i<nFrames;i++){ const s=d.step(); if(!s) break; onFrame(s,i); } }
