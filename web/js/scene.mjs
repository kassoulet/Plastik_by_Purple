// Generic scene driver for the recompiled scenes: runs a generated entry function frame by frame on the flat memory of x86rt.mjs.
// Time model = re/harness.py: each presented frame adds K ticks to [0xec0030]; 0x3d220 answers from the XM row table.
// The memory and the R.S hooks are module singletons: only one Scene is live at a time (frame() re-activates by restoring a checkpoint).
import * as R from './x86rt.mjs';
export const K=3, HZ=70, PG=4096, CK=50;
export class Stop{}
export class Scene{
  // o = {gen:{entry,resume,pc0,setRegs,getRegs}, xm, f0, load(m8)->void, esp, bufPtr(): address of the 640x300 RGB565 picture at present time, lim: scan limit for checkpoints, setup()}
  constructor(o){
    Object.assign(this,o); this.times=o.xm.rows.map(r=>r[2]); this.screen=new Uint8Array(640*400*2); this.ck=new Map();
    R.m8.fill(0); o.load(R.m8); R.S.sp=8; this.hooks(); o.gen.setRegs({esp:o.esp}); this.total=K*o.f0; this.n=-1; this.done=false;
    this.base=new Map(); const m32=new Uint32Array(R.buf,0,o.lim>>2); for(let a=0;a<o.lim;a+=PG) if(m32.subarray(a>>2,(a+PG)>>2).some(x=>x)) this.base.set(a,R.m8.slice(a,a+PG)); this.save();
  }
  hooks(){ const xm=this.xm,w=R.wr32; R.S.active=this;
    R.S.pos=()=>{ // = harness status(): XM position at the tick the logic step belongs to
      const pend=R.rd32(0xec0030), t=(this.total-Math.max(pend-1,0))/HZ, T=this.times;
      let lo=0,hi=T.length; while(lo<hi){const m=(lo+hi)>>1; if(T[m]<=t)lo=m+1; else hi=m;}
      const r=xm.rows[Math.max(0,lo-1)];
      w(0xec0024,r[0]); w(0xec0014,xm.orders[r[0]]); w(0xec002c,r[1]); w(0xec0020,0); return (r[0]<<8|r[1])&0xffff;};
    R.S.present=()=>{ const b=this.bufPtr(); this.screen.set(R.m8.subarray(b,b+640*300*2),640*50*2); this.n++; this.total+=K; w(0xec0030,R.rd32(0xec0030)+K); throw new Stop(); };
    if(this.setup) this.setup(); }
  save(){ const m=R.m8,m32=new Uint32Array(R.buf,0,this.lim>>2),pg=[]; // pages that differ from the entry state (zero where the entry state has no page)
    for(let a=0;a<this.lim;a+=PG){ const b=this.base.get(a); let d=false; const e=(a+PG)>>2;
      if(b){const b32=new Uint32Array(b.buffer);for(let i=a>>2,k=0;i<e;i++,k++) if(m32[i]!==b32[k]){d=true;break;}} else for(let i=a>>2;i<e;i++) if(m32[i]){d=true;break;}
      if(d) pg.push([a,m.slice(a,a+PG)]); }
    this.ck.set(this.n,{pg,regs:this.gen.getRegs(),sp:R.S.sp,f:R.f.slice(),total:this.total,done:this.done}); }
  restore(n){ const c=this.ck.get(n); R.m8.fill(0); for(const [a,d] of this.base) R.m8.set(d,a); for(const [a,d] of c.pg) R.m8.set(d,a);
    this.gen.setRegs(c.regs); R.S.sp=c.sp; R.f.set(c.f); this.total=c.total; this.n=n; this.done=c.done;
    if(n>=0){ const b=this.bufPtr(); this.screen.set(R.m8.subarray(b,b+640*300*2),640*50*2); } }
  step(){ if(this.done) return null;
    try{ const g=this.gen; if(this.n<0||!g.chain) g.entry(this.n<0?0:g.resume); else for(const [fn,pc] of g.chain) fn(pc);   // chain: present is nested in calls, resume = finish each open function from its call site, innermost first
      this.done=true; return null; }catch(e){ if(!(e instanceof Stop)) throw e; }
    if(this.n%CK===CK-1 && !this.ck.has(this.n)) this.save();
    return this.screen; }
  // screen after n+1 presents (n = 0..), i.e. golden flip f0+n+1
  frame(n){ if(R.S.active!==this){ this.hooks(); this.n=1e9; }
    if(n<this.n||n>this.n+CK){ let b=-1; for(const k of this.ck.keys()) if(k<=n&&k>b) b=k; this.restore(b); }
    while(this.n<n){ if(!this.step()) return null; } return this.screen; }
}
