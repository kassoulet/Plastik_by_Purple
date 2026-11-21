"""harness.py - boot the ORIGINAL PLASTIK.EXE (via emucore) with a virtual clock and grab the real 640x400x16 frames.
 usage: python3 harness.py NFRAMES OUTDIR [step]      (no -I, needs unicorn; env PL_MEM = image from unpack_clean.py)
Time model (see NOTES.md): the demo is a fixed-step loop on the tick counter [0xec0030] (MIDAS timer callback 0x3d190, once per display refresh, 70 Hz at 640x400)
and polls the XM position (order<<8|row, fn 0x3d220 -> 0x3d1d4).  No ISR runs here, so: every VBE 4F07 flip (= one finished frame) we add K ticks
([0xec0030] += K, virtual time += K/HZ) and 0x3d1d4 is replaced by a lookup in xm_times/system.json at the tick the logic step belongs to.
env: K (ticks per frame, default 3 = 23.3 fps), HZ (70), RAW=dir (crc.json + RAWSTEP-th frame as npy), VIDEO=file.mp4 (ffmpeg pipe)."""
import sys,os,struct,json,bisect,zlib,subprocess
import emucore as E
import numpy as np
from PIL import Image
from unicorn import *; from unicorn.x86_const import *
NF=int(sys.argv[1]); OUT=sys.argv[2]; STEP=int(sys.argv[3]) if len(sys.argv)>3 else 100
K=int(os.environ.get('K',3)); HZ=float(os.environ.get('HZ',70)); RAW=os.environ.get('RAW'); VIDEO=os.environ.get('VIDEO'); RAWSTEP=int(os.environ.get('RAWSTEP',100))
os.makedirs(OUT,exist_ok=True)
XM=json.load(open(E.HERE+'/xm_times/system.json')); ROWS=XM['rows']; TIMES=[r[2] for r in ROWS]
frames=[0]; total=[0]; crcs=[]
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x400','-r',str(HZ/K),'-i','-','-c:v','libx264','-crf','16','-pix_fmt','yuv420p',VIDEO],stdin=subprocess.PIPE) if VIDEO else None
def rgb(a):
    r=((a>>11)&31)<<3; g=((a>>5)&63)<<2; b=(a&31)<<3
    return np.stack([r|(r>>5),g|(g>>6),b|(b>>5)],-1).astype(np.uint8)
def status():   # replaces 0x3d1d4: fills [ec0024]=order, [ec0014]=pattern, [ec002c]=row, [ec0020]=0
    pending=E.u32(0xec0030); t=(total[0]-max(pending-1,0))/HZ
    i=max(0,bisect.bisect_right(TIMES,t)-1); r=ROWS[i]
    E.wr32(0xec0024,r[0]); E.wr32(0xec0014,XM['orders'][r[0]]); E.wr32(0xec002c,r[1]); E.wr32(0xec0020,0)
    sp=E.ireg('ESP'); E.w('ESP',sp+4); E.mu.reg_write(UC_X86_REG_EIP,E.u32(sp))
E.mu.hook_add(UC_HOOK_CODE,lambda *a:status(),begin=0x3d1d4,end=0x3d1d4)
def on_ds():
    k=frames[0]; frames[0]+=1
    raw=bytes(E.mu.mem_read(E.LFB+E.dispstart[1]*1280,640*400*2)); crcs.append(zlib.crc32(raw))
    if ff or k%STEP==0:
        im=rgb(np.frombuffer(raw,'<u2').reshape(400,640))
        if ff: ff.stdin.write(im.tobytes())
        if k%STEP==0:
            Image.fromarray(im).save('%s/f%05d.png'%(OUT,k)); print('frame',k,'t=%.2f'%(total[0]/HZ),'pos',[E.u32(0xec0024),E.u32(0xec002c)],flush=True)
    if RAW and k%RAWSTEP==0 and k>=int(os.environ.get('RAWFROM',0)): os.makedirs(RAW,exist_ok=True); np.save('%s/f%05d.npy'%(RAW,k),np.frombuffer(raw,'<u2'))
    if os.environ.get('DBGFLIP') and k>=int(os.environ['DBGFLIP']):
        pg=[np.count_nonzero(np.frombuffer(bytes(E.mu.mem_read(E.LFB+y*1280,640*400*2)),'<u2')) for y in (0,400,800)]
        print('flip',k,'start',E.dispstart,'nonzero px/page',pg,'cnt',dict(E.cnt),flush=True)
    if os.environ.get('DUMP') and k==int(os.environ.get('DUMPAT',1)): open(os.environ['DUMP'],'wb').write(bytes(E.mu.mem_read(0,0x1400000))); print('dumped RAM (20 MB) at frame',k,flush=True)
    if os.environ.get('DUMPD') and k==int(os.environ.get('DUMPAT',1)):   # scene D inputs: tables + palette/texture behind the heap pointers
        g=lambda a,n: bytes(E.mu.mem_read(a,n)); np.savez(os.environ['DUMPD'],log=np.frombuffer(g(0xc51700,0x200),'u1'),exp=np.frombuffer(g(0xb80120,0x200),'u1'),scale=np.frombuffer(g(0xc1afc0,0x6000),'u1'),
            pal=np.frombuffer(g(E.u32(0x103190),768),'u1'),pal0=np.frombuffer(g(E.u32(0xebea80),768),'u1'),tex=np.frombuffer(g(E.u32(0xebea5c),65536),'u1'),tex2=np.frombuffer(g(0xcee080,65536),'u1')); print('dumped D inputs',flush=True)
    if os.environ.get('DUMPK') and k==int(os.environ['DUMPK'].split(',')[0]):   # full RAM at flip k (compare with the JS memory at the same present)
        g=lambda p,n: bytes(E.mu.mem_read(p,n)); np.savez_compressed(os.environ['DUMPK'].split(',')[1],mem=np.frombuffer(g(0x100000,0x124f000-0x100000),'u1'),heap=np.frombuffer(g(0x124f000,0x4a00000-0x124f000),'u1'))
    if k>=NF: E.mu.emu_stop(); return
    total[0]+=K; E.wr32(0xec0030,E.u32(0xec0030)+K)
def tr9(uc,a,sz,ud):
    esp=E.ireg('ESP'); import struct
    print('T9',' '.join('%08x'%E.u32(esp+4*i) for i in range(1,24)),flush=True)
    tr9.n=getattr(tr9,'n',0)+1
    if tr9.n>=int(os.environ['TRACE9']): E.mu.emu_stop()
if os.environ.get('TRACE9'): E.mu.hook_add(UC_HOOK_CODE,tr9,begin=0x1d9bc,end=0x1d9bc)
SCENES={0x28264:'A',0x26278:'B',0x22af4:'C',0x1ddb4:'D',0x24168:'E',0x21e40:'F',0x2747c:'G',0x29634:'H'}   # main (0x2aa..) calls these in order
def fpst():   # x87 registers as st(0..7) doubles + top: stale registers are read by some scenes (QEMU keeps the old contents of 'empty' registers)
    top=(E.mu.reg_read(UC_X86_REG_FPSW)>>11)&7; r=[]
    for i in range(8):
        v=E.mu.reg_read(UC_X86_REG_ST0+((top+i)&7)); m,e=(v&0xffffffffffffffff,v>>64) if isinstance(v,int) else v; sg=-1.0 if e&0x8000 else 1.0; x=e&0x7fff
        r.append(float('nan') if x==0x7fff and m<<1&0xffffffffffffffff else sg*float('inf') if x==0x7fff else 0.0 if x==0 else sg*m*2.0**(x-16383-63))
    print('fp top',top,r,flush=True); return np.array(r)
def scene(uc,a,sz,ud):
    if os.environ.get('DUMPENT') and a==int(os.environ['DUMPENT'].split(',')[0],16):   # any scene's entry state: DUMPENT=28264,x.npz [STOPDE=1]
        g=lambda p,n: bytes(E.mu.mem_read(p,n)); np.savez_compressed(os.environ['DUMPENT'].split(',')[1],mem=np.frombuffer(g(0x100000,0x124f000-0x100000),'u1'),frames=np.array([frames[0],total[0]]),stk=np.frombuffer(g(E.ireg('ESP')-0x2000,0x2100),'u1'),esp=np.array([E.ireg('ESP')]),heap=np.frombuffer(g(0x124f000,0x4a00000-0x124f000),'u1'),fp=fpst())
        print('dumped entry',flush=True)
        if os.environ.get('STOPDE'): E.mu.emu_stop()
    if a==0x1ddb4 and os.environ.get('DUMPDE'):   # scene D entry state: .data/bss + the heap blocks D reads
        g=lambda p,n: bytes(E.mu.mem_read(p,n)); np.savez(os.environ['DUMPDE'],mem=np.frombuffer(g(0x100000,0x124f000-0x100000),'u1'),tex=np.frombuffer(g(E.u32(0xebea5c),65536),'u1'),pal0=np.frombuffer(g(E.u32(0xebea80),768),'u1'),pal=np.frombuffer(g(E.u32(0x103190),768),'u1'),frames=np.array([frames[0],total[0]]),stk=np.frombuffer(g(E.ireg('ESP')-0x2000,0x2100),'u1'),esp=np.array([E.ireg('ESP')]))
        print('dumped D entry',flush=True)
        if os.environ.get('STOPDE'): E.mu.emu_stop()
    print('SCENE %s entry %x frame %d t=%.2f pos %d:%d'%(SCENES[a],a,frames[0],total[0]/HZ,E.u32(0xec0024),E.u32(0xec002c)),flush=True)
for a in SCENES: E.mu.hook_add(UC_HOOK_CODE,scene,begin=a,end=a)
if os.environ.get('INDCALL'):   # log targets of indirect calls (and callers of present 0x51e3c) once, for the recompiler's extra entries
    seen=set()
    def ind(uc,a,sz,ud):
        i=bytes(E.mu.mem_read(a,6)); p=E.u32(int.from_bytes(i[2:6],'little')) if i[:2]==b'\xff\x15' else E.u32(E.ireg('EAX')) if i[:2]==b'\xff\x10' else None
        if (a,p) not in seen: seen.add((a,p)); print('IND %x -> %s'%(a,hex(p) if p is not None else '?'),flush=True)
    for a in [0x41dd7,0x41e84,0x41e90,0x41e96,0x421ee,0x421f9,0x42200,0x51c23,0x51c45,0x51c4b,0x5573b,0x5f342]: E.mu.hook_add(UC_HOOK_CODE,ind,begin=a,end=a)
    def pres(uc,a,sz,ud):
        r=E.u32(E.ireg('ESP'))
        if r not in seen: seen.add(r); print('PRESENT caller %x frame %d'%(r,frames[0]),flush=True)
    E.mu.hook_add(UC_HOOK_CODE,pres,begin=0x51e3c,end=0x51e3c)
# Unicorn bug: FYL2X with ST0==0 (divide-by-zero, masked) does not pop the x87 stack; the log-table builder 0x1d76c starts at x=0
# and the leak turns the table into ln(x)*ln2 instead of 46.1662*ln(x) (scene D then has an all-black palette).  ln(1)=ln(0)->0 in the byte table, so feed x=1.
def fixlog(uc,a,sz,ud):
    if E.ireg('EDX')==0: E.wr32(E.ireg('ESP')+0xc,1)
E.mu.hook_add(UC_HOOK_CODE,fixlog,begin=0x1d783,end=0x1d783)
E.on_ds=on_ds
PROF=os.environ.get('PROFILE')
if PROF:   # statistical profile: sample EIP every 20000 guest instructions; prints the hottest 256-byte blocks and 16-byte buckets
    import collections; C=collections.Counter(); pc=0x5386c
    while True:
        try: E.mu.emu_start(pc,0,count=20000)
        except UcError as e: print('ERR',e); break
        pc=E.ireg('EIP'); C[pc>>4]+=1
        if frames[0]>NF: break
    B=collections.Counter()
    for k,v in C.items(): B[k>>4]+=v
    n=sum(C.values()); print('samples',n)
    for k,v in B.most_common(25): print('%06x-%06x %5.1f%%'%(k<<8,(k<<8)+255,100*v/n))
else: E.run(0x5386c)
if ff: ff.stdin.close(); ff.wait()
if RAW: json.dump(crcs,open(RAW+'/crc.json','w'))
print('stopped',hex(E.ireg('EIP')),'frames',frames[0])
