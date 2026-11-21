// Runtime for the statically recompiled original code (plastik-d.gen.mjs): flat memory + x87 stack.  x87 runs in double precision (the original sets PC=53 bit: CW 0x127f).
const MEM=0x4a00000; export const buf=new ArrayBuffer(MEM), m8=new Uint8Array(buf), dv=new DataView(buf);
export const rd8=a=>m8[a],rd16=a=>dv.getUint16(a,true),rd32=a=>dv.getInt32(a,true),wr8=(a,v)=>{m8[a]=v;},wr16=(a,v)=>dv.setUint16(a,v,true),wr32=(a,v)=>dv.setInt32(a,v,true);
export const rdf32=a=>dv.getFloat32(a,true),rdf64=a=>dv.getFloat64(a,true),wrf32=(a,v)=>dv.setFloat32(a,v,true),wrf64=(a,v)=>dv.setFloat64(a,v,true);
export const f=new Float64Array(16), S={sp:8,fsw:0,pos:()=>0,present:()=>{},blk:()=>{}};
export const fpush=v=>{f[--S.sp]=v;}, fxch=i=>{const t=f[S.sp];f[S.sp]=f[S.sp+i];f[S.sp+i]=t;}, sx16=v=>v<<16>>16;
export const fist=v=>{if(!(Math.abs(v)<2147483648))return -2147483648;const r=Math.round(v);return (Math.abs(v-Math.trunc(v))===0.5&&(r&1))?r-1:r|0;};   // round to nearest even
export const fp_add=v=>{f[S.sp]+=v;},fp_mul=v=>{f[S.sp]*=v;},fp_sub=v=>{f[S.sp]-=v;},fp_subr=v=>{f[S.sp]=v-f[S.sp];},fp_div=v=>{f[S.sp]/=v;},fp_divr=v=>{f[S.sp]=v/f[S.sp];};
export const fp_add_st=i=>{f[S.sp]+=f[S.sp+i];},fp_mul_st=i=>{f[S.sp]*=f[S.sp+i];},fp_sub_st=i=>{f[S.sp]-=f[S.sp+i];},fp_subr_st=i=>{f[S.sp]=f[S.sp+i]-f[S.sp];},fp_div_st=i=>{f[S.sp]/=f[S.sp+i];},fp_divr_st=i=>{f[S.sp]=f[S.sp+i]/f[S.sp];};
export const fp_add_to=i=>{f[S.sp+i]+=f[S.sp];},fp_mul_to=i=>{f[S.sp+i]*=f[S.sp];},fp_sub_to=i=>{f[S.sp+i]-=f[S.sp];},fp_subr_to=i=>{f[S.sp+i]=f[S.sp]-f[S.sp+i];},fp_div_to=i=>{f[S.sp+i]/=f[S.sp];},fp_divr_to=i=>{f[S.sp+i]=f[S.sp]/f[S.sp+i];};
const cmp=(a,b)=>{S.fsw=a!==a||b!==b?0x4500:a>b?0:a<b?0x100:0x4000;};
export const fp_com=v=>cmp(f[S.sp],v), fp_com_st=i=>cmp(f[S.sp],f[S.sp+i]);
export const n_fpatan=()=>{fxch(1);const x=f[S.sp],y=f[S.sp+1];f[S.sp+1]=Math.atan2(y,x);S.sp++;};
export const n_pos=()=>S.pos(), n_present=()=>S.present();

export const wrf64i=(a,v)=>{let r=Math.round(v);if(Math.abs(v-Math.trunc(v))===0.5&&(r&1))r-=1;const lo=((r%4294967296)+4294967296)%4294967296;dv.setUint32(a,lo,true);dv.setInt32(a+4,Math.floor(r/4294967296),true);};   // fistp qword, round to nearest even
// 0x28028 (scene A): per-pixel alpha blend of RGB565 src into dst; alpha[] indexes a table at 0xea3de0 (+sh<<5), blend step table at 0xea47dd
export const n_blend=(dst,alpha,cnt,src,sh)=>{const b=sh<<5;for(let i=0;i<cnt;i++,dst+=2,src+=2){const bx=dv.getUint16(0xea3de0+((m8[alpha+i]+b)<<1),true);if(bx<=0x40)continue;const s=dv.getUint16(src,true);
  if(bx>=0x2000){dv.setUint16(dst,s,true);continue;}
  const d=dv.getUint16(dst,true),s5=s&31,d5=d&31,s6=(s&0x7e0)>>5,d6=(d&0x7e0)>>5,s0=s>>11,d0=d>>11;
  dv.setUint16(dst,((d5+(dv.getInt32(0xea47dd+s5-d5+bx,true)>>24))|((d6+(dv.getInt32(0xea47dd+s6-d6+bx,true)>>24))<<5)|((d0+(dv.getInt32(0xea47dd+s0-d0+bx,true)>>24))<<11))&0xffff,true);}};

export function imulhi(a,b){const ah=a>>16,al=a&0xffff,bh=b>>16,bl=b&0xffff;return (ah*bh+Math.floor((((ah*bl+al*bh)*65536)+al*bl)/4294967296))|0;}   // high word of the signed 64-bit product
// sprintf(dest,fmt,...) native (0x536f1): only %[-0]width d/i/u/x/s/c, the formats the scenes use ("FPS: %3d", "%13d")
export function n_sprintf(dst,fmt,ap){let o='',i=fmt;const s0=()=>{let r='';for(;m8[i]&&m8[i]!==37;i++)r+=String.fromCharCode(m8[i]);return r;};
  o+=s0();while(m8[i]===37){i++;let left=0,zero=0,w=0;for(;;i++){if(m8[i]===45)left=1;else if(m8[i]===48)zero=1;else break;}
    while(m8[i]>=48&&m8[i]<=57){w=w*10+m8[i]-48;i++;}const c=String.fromCharCode(m8[i++]);let v='';
    if(c==='d'||c==='i'){v=String(dv.getInt32(ap,true));ap+=4;}else if(c==='u'){v=String(dv.getUint32(ap,true));ap+=4;}else if(c==='x'){v=dv.getUint32(ap,true).toString(16);ap+=4;}
    else if(c==='c'){v=String.fromCharCode(dv.getUint32(ap,true)&255);ap+=4;}else if(c==='s'){let p=dv.getUint32(ap,true);ap+=4;for(;m8[p];p++)v+=String.fromCharCode(m8[p]);}else if(c==='%')v='%';else throw new Error('sprintf %'+c);
    o+=left?v.padEnd(w):(zero&&c!=='s'?v.padStart(w,'0'):v.padStart(w));o+=s0();}
  for(let k=0;k<o.length;k++)m8[dst+k]=o.charCodeAt(k);m8[dst+o.length]=0;return o.length;}
export const rdf80=a=>{const m=dv.getBigUint64(a,true),e=dv.getUint16(a+8,true),s=e&0x8000?-1:1,x=e&0x7fff;if(x===0)return s*0;if(x===0x7fff)return (m<<1n)&0xffffffffffffffffn?NaN:s*Infinity;return s*Number(m)*Math.pow(2,x-16383-63);};
export const n_copy=(d,s,n)=>{m8.copyWithin(d,s,s+n);}, n_fill=(v,d,n)=>{m8.fill(v,d,d+n);};
export const bad=a=>{throw new Error('indirect call to non-generated function '+(a>>>0).toString(16));};
