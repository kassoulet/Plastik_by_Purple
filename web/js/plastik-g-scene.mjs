// Scene G: the recompiled original (plastik-g.gen.mjs), entry state = page list from re/mk_init.py.
import * as R from './x86rt.mjs';
import {Scene} from './scene.mjs';
import {f_2747c,f_41dd0,f_4ce08,setRegs,getRegs} from './plastik-g.gen.mjs';
export function unpackInit(b){const dv=new DataView(b.buffer||b,b.byteOffset||0),n=dv.getUint32(0,true),pages=[];for(let i=0,o=8;i<n;i++,o+=4100)pages.push([dv.getUint32(o,true),new Uint8Array(dv.buffer,dv.byteOffset+o+4,4096)]);return {esp:dv.getUint32(4,true),pages};}
export const RESUME=0x4ce82;   // instruction after "call present" in f_2747c (natives are esp-neutral)
export class GScene extends Scene{
  constructor(init,xm,f0=0){
    super({gen:{entry:f_2747c,resume:RESUME,chain:[[f_4ce08,0x4ce82],[f_41dd0,0x41ddd],[f_2747c,0x274ce]],setRegs,getRegs},xm,f0,esp:init.esp,lim:0x4a00000,load:m8=>{for(const [a,d] of init.pages)m8.set(d,a);},bufPtr:()=>0xf65220});
  }
}
