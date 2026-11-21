// Hand port of 0x2accc: one 16x16 block of the stained-glass tunnel (8 rows x 8 texels, every texel is drawn 2x2).  Replaces the recompiled function (same
// result, ~15x faster); tools/test-d-scene.mjs diffs the frames against the original.  All variables are the original's globals (0xebe9xx / 0xebeaxx), written back
// so the RAM stays identical to the recompiled version.
// Per texel: bilinear 2x2 fetch from the 256x256 texture (0xcee080), weights = 4 floats at 0xc5b740 selected by the sub-texel position, each fetched texel indexes a
// table of doubles (0xc30f00, entry = shade<<8 | texel) whose mantissa bytes 0/2/4 hold the packed r/g/b; the weighted sum is stored as a double and bytes 0/2/4 are packed to RGB565.
import * as R from './x86rt.mjs';
const i32=new Int32Array(R.buf), f32=new Float32Array(R.buf), D=new Float64Array(R.buf,0xc30f00,0x4000), m8=R.m8, dv=R.dv;
const sc=new Float64Array(1), sb=new Uint8Array(sc.buffer);
const g=a=>i32[a>>2], s=(a,v)=>{i32[a>>2]=v;};
export function block(edi){
  s(0xebe9bc,8); s(0xebe9a0,edi);
  for(let row=0;row<8;row++){
    const c0=g(0xebe9c0),c4=g(0xebe9c4),a10=g(0xebea10),c8=g(0xebe9c8);
    s(0xebe9d8,c0); s(0xebe9e0,c4); s(0xebea18,a10); s(0xebe9cc,c8);
    const ac=((((g(0xebe9b8)-c0)|0)<<8>>19)+((((g(0xebea28)-a10)|0)<<8>>19)<<16))|0;
    const bc=((((g(0xebe9b4)-c4)|0)<<8>>19)+((((g(0xebe9e4)-c8)|0)<<8>>19)<<16))|0;
    s(0xebe9ac,ac); s(0xebe9b0,bc);
    let esi=((c4>>>8)+((c8>>>8)<<16))|0, ebp=((c0>>>8)+((a10>>>8)<<16))|0;
    for(let x=0;x<8;x++){
      const bl=(ebp>>>8)&0xff, bh=(esi>>>8)&0xff, al=((esi&0xf0)+((ebp&0xff)>>>4))&0xff, w=(0xc5b740>>2)+(al<<2), base=m8[0xb35680+(esi>>>24)]<<8;
      const bl1=(bl+1)&0xff, bh1=(bh+1)&0xff;
      let sum=f32[w]*D[base+m8[0xcee080+(bh<<8|bl)]];
      sum+=f32[w+1]*D[base+m8[0xcee080+(bh<<8|bl1)]];
      sum+=f32[w+2]*D[base+m8[0xcee080+(bh1<<8|bl)]];
      sum+=f32[w+3]*D[base+m8[0xcee080+(bh1<<8|bl1)]];
      ebp=(ebp+ac)|0; esi=(esi+bc)|0;
      sc[0]=sum; const c=((sb[4]>>3)<<11)|((sb[2]>>2)<<5)|(sb[0]>>3), px=(c<<16)|c;
      dv.setInt32(edi,px,true); dv.setInt32(edi+0x500,px,true); edi=(edi+4)|0;
      if(x===7) dv.setFloat64(0x112dd0,sum,true);
    }
    edi=(g(0xebe9a0)+0xa00)|0; s(0xebe9a0,edi);
    s(0xebe9c0,(c0+g(0xebe9d0))|0); s(0xebe9c4,(c4+g(0xebe9d4))|0); s(0xebea10,(a10+g(0xebea2c))|0); s(0xebe9c8,(c8+g(0xebe9ec))|0);
    s(0xebe9b8,(g(0xebe9b8)+g(0xebe9f4))|0); s(0xebe9b4,(g(0xebe9b4)+g(0xebe9fc))|0); s(0xebea28,(g(0xebea28)+g(0xebea00))|0); s(0xebe9e4,(g(0xebe9e4)+g(0xebe9a4))|0);
    s(0xebe9bc,7-row);
  }
}
