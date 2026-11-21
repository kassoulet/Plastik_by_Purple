// Scene A (credits, logo, star field): the recompiled original (plastik-a.gen.mjs), entry state = page list from re/mk_init.py.
import * as R from './x86rt.mjs';
import {Scene} from './scene.mjs';
import {f_28264,setRegs,getRegs} from './plastik-a.gen.mjs';
export function unpackInit(b){const dv=new DataView(b.buffer||b,b.byteOffset||0),n=dv.getUint32(0,true),pages=[];for(let i=0,o=8;i<n;i++,o+=4100)pages.push([dv.getUint32(o,true),new Uint8Array(dv.buffer,dv.byteOffset+o+4,4096)]);return {esp:dv.getUint32(4,true),pages};}
export const RESUME=0x288d6;   // instruction after "call present" in f_28264 (natives are esp-neutral)
export class AScene extends Scene{
  constructor(init,xm,f0=0){
    super({gen:{entry:f_28264,resume:RESUME,setRegs,getRegs},xm,f0,esp:init.esp,lim:0x4a00000,load:m8=>{for(const [a,d] of init.pages)m8.set(d,a);},bufPtr:()=>R.rd32(0xebea78)});
  }
}
