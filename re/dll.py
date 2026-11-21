#!/usr/bin/env python3
"""dll.py - PLASTIK.DLL is not a PE: a flat archive. Entry = [name 64 B, NUL padded][u32 size][data], entries separated by a u32 (= offset of the next name field), the first has no prefix.
usage: python3 -I re/dll.py list|extract OUTDIR"""
import struct,sys,os
def entries(p=os.path.dirname(os.path.abspath(__file__))+'/../PLASTIK.DLL'):
    d=open(p,'rb').read(); o=0
    while o+68<=len(d):
        n=d[o:o+64].split(b'\0')[0].decode(); sz=struct.unpack_from('<I',d,o+64)[0]
        yield n,d[o+68:o+68+sz]; o+=68+sz+4
def pcx(b):   # 8-bit RLE PCX with 256-colour palette at the end -> (w,h,indices bytes,palette 768 bytes)
    xmin,ymin,xmax,ymax=struct.unpack_from('<4H',b,4); w=xmax-xmin+1; h=ymax-ymin+1; bpl=struct.unpack_from('<H',b,66)[0]; planes=b[65]
    assert b[3]==8 and planes==1 and b[-769]==12,(b[3],planes)
    out=bytearray(); i=128
    while len(out)<bpl*h:
        c=b[i]; i+=1
        if c>=0xc0: out+=bytes([b[i]])*(c&0x3f); i+=1
        else: out.append(c)
    rows=[out[y*bpl:y*bpl+w] for y in range(h)]
    return w,h,b''.join(rows),b[-768:]
if __name__=='__main__':
    for n,b in entries():
        if sys.argv[1]=='list':
            if n.endswith('.pcx'):
                try: w,h,_,_=pcx(b); print('%-12s %7d  pcx %dx%d'%(n,len(b),w,h))
                except AssertionError as e: print('%-12s %7d  pcx NOT 8bit-pal'%(n,len(b)),e, 'bpp',b[3],'planes',b[65],'dim',struct.unpack_from('<4H',b,4))
            else: print('%-12s %7d  %s'%(n,len(b),b[:16].hex()))
        else: os.makedirs(sys.argv[2],exist_ok=True); open(sys.argv[2]+'/'+n,'wb').write(b)
