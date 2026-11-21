"""Pack a scene entry dump (harness.py DUMPENT=addr,x.npz STOPDE=1) into a page list: [u32 n][u32 esp] n x ([u32 addr][4096 bytes]).
Optional 3rd arg: JSON list of page numbers (addr>>12) to keep (pages the JS run reads before writing, see tools/trace-pages.mjs); default = all non-zero pages."""
import numpy as np,sys,json,struct
d=np.load(sys.argv[1]); mem=bytearray(0x4a00000)
mem[0x100000:0x124f000]=d['mem'].tobytes(); mem[0x124f000:0x4a00000]=d['heap'].tobytes()
e=int(d['esp'][0]); s=d['stk'].tobytes(); mem[e-0x2000:e-0x2000+len(s)]=s
keep=set(json.load(open(sys.argv[3]))) if len(sys.argv)>3 else None
pg=[p for p in range(0x100000>>12,0x4a00000>>12) if any(mem[p<<12:(p+1)<<12]) and (keep is None or p in keep)]
out=struct.pack('<II',len(pg),e)+b''.join(struct.pack('<I',p<<12)+bytes(mem[p<<12:(p+1)<<12]) for p in pg)
open(sys.argv[2],'wb').write(out); print(len(pg),'pages',len(out)//1024,'KB')
