#!/usr/bin/env python3
"""unpack_clean.py - run PLASTIK.EXE's own PMODE/W 1.33 loader under Unicorn until the program entry (0x5386c, Watcom _cstart) and dump RAM.
usage: python3 unpack_clean.py OUT.bin   (64 MB raw dump; run WITHOUT -I, needs unicorn; ~1 s)
The first INT 31h/0300 -> INT 10h/4F00 (VBE) the loader-made program issues comes only after entry, so the hook fires first."""
import sys
EXE=__file__.rsplit('/',2)[0]+'/PLASTIK.EXE'; OUT=sys.argv[1]
sys.argv=['x','0',EXE,'0x2cb0','0x3ce',OUT]
sys.path.insert(0,__file__.rsplit('/',1)[0])
import unpack_pmodew as U
from unicorn import *; from unicorn.x86_const import *
ENTRY=0x5386c
def at_entry(uc,a,sz,ud):
    print('ENTRY reached; regs',{r:hex(uc.reg_read(getattr(__import__('unicorn.x86_const',fromlist=['x']),'UC_X86_REG_'+r))) for r in ('CS','DS','ES','SS','ESP','EAX','EBX','ECX','EDX','ESI','EDI')})
    print('GDTR',[hex(x) for x in uc.reg_read(UC_X86_REG_GDTR)],'LDTR',uc.reg_read(UC_X86_REG_LDTR),'IDTR',[hex(x) for x in uc.reg_read(UC_X86_REG_IDTR)])
    open(OUT,'wb').write(bytes(uc.mem_read(0,0x4000000))); uc.emu_stop()
U.mu.hook_add(UC_HOOK_CODE,at_entry,begin=ENTRY,end=ENTRY)
try: U.mu.emu_start(U.SEG*16+0x5e,0,timeout=120*10**6)
except UcError as e: print('err',e)
