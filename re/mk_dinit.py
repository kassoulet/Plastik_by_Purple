"""Pack the scene D entry state (harness.py DUMPDE=x.npz STOPDE=1) into web/assets/plastik-d-init.bin.
Layout: [RAM 0x100000..0x11c000 (.data)] [RAM 0xb35000..0xb46000 (shade table at 0xb35680, not built by D)] [texture 64K] [pal0 768] [stack esp-0x2000..esp+0x100]
Everything else D reads it builds itself (found by zeroing each non-empty 4K page: only these two RAM ranges matter)."""
import numpy as np,sys
d=np.load(sys.argv[1]); m=d['mem']; o=0x100000
out=[m[0:0x1c000],m[0xb35000-o:0xb46000-o],d['tex'],d['pal0'],d['stk']]
assert [len(x) for x in out]==[0x1c000,0x11000,0x10000,0x300,0x2100]
open(sys.argv[2],'wb').write(b''.join(x.tobytes() for x in out))
