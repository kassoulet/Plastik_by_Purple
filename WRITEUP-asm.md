# PLASTIK - the assembly worth reading (work in progress)

Addresses are linear addresses of the unpacked flat image (`re/unpack_clean.py`), listing from `objdump -M intel`. Only things actually read so far are here; the engine's rasterisers are not yet analysed.

## 1. A game-style fixed timestep, driven by the display refresh
Every scene is the same skeleton (scene A, `0x28900`..`0x28c98`):

```asm
28900: cmp  dword [0xec0030], 1      ; ticks accumulated by the timer callback
28907: jbe  render                   ; nothing (or only the leftover 1) -> just draw
2890d: call 0x3d220                  ; music position = order<<8 | row  (MIDAS play status)
...                                  ; one logic step (state += f(tick), scene switches on position)
28c48: mov  eax, [0xec0030]
28c4d: dec  dword [0xec0030]         ; consume one tick
28c8b: cmp  dword [0xec0030], 1
28c92: ja   0x2890d                  ; catch up: as many steps as ticks passed
```
The counter is bumped by a three-instruction callback at `0x3d190` (`inc dword [0xec0030]`) that MIDAS calls once per vertical retrace (`0x32f70` programs it after *measuring* the refresh with the `0x3da` retrace bit: `in al,dx / test al,8` loops at `0x32fe9`, then PIT channel 0 mode 0 `out 0x43,0x30`). Consequence for the port: the picture is a pure function of the number of logic steps and of the XM position, never of wall time; a slow PC drops frames but not speed. Our harness exploits exactly this (add K ticks per flip).

## 2. Three colour channels in one double
The 3D shading/filter code at `0x2accc` (called from `0x1d977`, about 3 KB unrolled four pixels at a time) builds RGB565 like this:

```asm
fld   dword [eax*4+0xc5b740]        ; weight A of this sample
...
mov   ch, [edx+0xb35680]            ; u >> 2 (table of 256 bytes)
mov   cl, [ebx+0xcee080]            ; v index
fmul  qword [ecx*8+0xc30f00]        ; 64K-entry table of doubles
...  (4 products, faddp)
fstp  qword [0x112dd0]              ; store the double ...
mov   dl, [0x112dd0]  ; shr edx,3   ; ... and read its BYTES 0, 2, 4 back:
mov   cl, [0x112dd2]  ; shr ecx,2 ; shl ecx,5  ; or ecx,edx
mov   dl, [0x112dd4]  ; shr edx,3 ; shl edx,11 ; or edx,ecx   -> RGB565
mov   [edi], edx  ; mov [edi+0x500], edx                      ; write the pixel pair, and the line below
```
Reading the channels out of the byte lanes of a double's mantissa lets *one* `fmul`/`faddp` scale and accumulate three colour channels at once (hypothesis, to be checked against the tables: the entries are doubles with R, G, B in separate 16-bit lanes; the operand roles in the comments above are guesses from the index arithmetic). It also doubles each result vertically (`[edi+0x500]` = next 640x400 line, 4 bytes = 2 pixels per store): a 320x200 work image shown at 640x400. The exact encoding of the tables (built when the scene starts; they are zero in the entry dump) is still to be decoded from a RAM dump (`DUMP=` in `re/harness.py`).

## 3. Getting at the code at all: PMODE/W in an emulator
The MZ file is a small LZ-style stub that unpacks PMODE/W, which reads its own `PMW1` overlay with DOS int 21h, decompresses and relocates the objects, enters protected mode and jumps to Watcom's `_cstart` (`0x5386c`, `jmp short` over the "WATCOM C/C++32 Run-Time system" banner). Running the stub's own code under Unicorn with a 20-line DOS stub (file I/O on the EXE itself) unpacks the program in 1.5 s, no unpacker to write. Pitfall met: DPMI `0300` calls to VBE 4F00 must keep the mode list within the first 256 bytes of the info block, because the program allocates a 512-byte DOS block per call and the next block overlaps the tail.

## 4. Triple buffering with the linear framebuffer
Frames are flipped with VBE function 4F07 (set display start) using y = 0 / 400 / 800 of a 1200-line virtual screen in the LFB; each call is one finished frame, which is what the harness hooks to grab frames and to advance its clock.

## A transcendental trap in the emulator, not in the demo
The palette of the stained-glass tunnel is built by multiplying in the log domain: `exp[log[4*v] + log[210]]`, with a byte log table made by `chop(46.1662*ln x)`. The builder (0x1d76c) runs `fld c; fild x; fldln2; fxch; fyl2x; fmul st,st(1); frndint; fistp` for x = 0..511. For x = 0 the real FPU gives -infinity (masked divide-by-zero), pops once, and `fistp` stores the "integer indefinite" whose low byte is 0. Unicorn 2.1.4 forgot the pop for that case, the stack grew by one `ln 2` and the whole table became `ln x * ln 2`: black palette, black scene. The cure in the harness is to feed x = 1 (same byte, 0). Watcom emits `frndint` with the control word forced to chop (0x1f7f) before every float-to-int, so the stored values are truncations; the JS port reproduces them with `Math.trunc`.

## From listing to JavaScript: a static recompiler
Scene D runs in the browser as the original code, not as a re-implementation. `re/x86js.py` reads an `objdump -M intel` listing and emits one JS function per x86 function (`for(;;)switch(pc)`, one `case` per instruction), with registers as locals, flags computed lazily (dead flag writes are stripped), a flat `ArrayBuffer` for memory and a Float64 array for the x87 stack. The x87 control word is 0x127f (double precision), so JS doubles agree with the FPU; `frndint` with round-to-chop is `Math.trunc`. Three bugs only showed up by diffing RAM with the emulator: `push [esp+x]` reads its operand before esp moves, a memory operand without a size takes it from the register, and `0x13` is hexadecimal. The display lags one flip behind the render, and the first frame reads uninitialised stack. Only the 16x16 block routine (the channel-in-a-double trick of section 2) is hand-ported, as `plastik-d-block.mjs`, 13.9 ms per frame for the whole scene.

## Scenes A and B as recompiled JS
Scenes A and B are not rewritten: `re/x86js.py` turns their x86 into JS (flat memory, lazy flags, x87 stack) and the output is diffed bit-exact against the emulator, 955 and 957 frames. V8 refuses to optimise a function above ~60 KB of bytecode, so the recompiler splits big functions into chunks that share the module-level registers (B went from 600 to 27 ms/frame).

## Scenes C, E and H: the same recipe, three more lessons
C (the satellite photo with a digit column), E (a shiny 3D object over a striped background) and H (the "purple" logo made of discs) are recompiled the same way and are bit-exact against the emulator (717, 478 and 250 frames). What they taught:
- `0x536f1` is the real `sprintf`: the digit column of C is printed with `"%13d"`, so the recompiler needs a native that formats like it (`R.n_sprintf`), not a stub.
- A pruned entry snapshot is only as good as its page trace: natives that read memory on their own (memcpy, memset, sprintf) must mark the pages they read, and a range read marks every page in the range, otherwise the scene reads a zero page and diverges one or two frames later.
- The x87 registers are state too. QEMU/Unicorn keep stale values in "empty" registers and a scene that reads a register it never wrote sees them; the entry dump therefore carries st(0..7) (used by F, which is not wired yet, see `re/NOTES.md`).
- F taught the x87 lesson: the original pops four values from an already empty FPU stack every frame (`faddp st(0),st` x4 at 0x3d56c). Hardware masks the underflow and the ring wraps, nothing observable happens; a linear JS stack drifts off its array. The recompiler now keeps an empty stack empty on pop.

## Scene G: code that is only reachable through pointers
G's loop calls its renderer and its present function through a table of function pointers (`call [0xec106c]` and friends) that the init code fills at run time, so the static call graph from the scene's entry never reaches them. The harness logs the targets (`INDCALL=1`), the recompiler takes them as extra entries and turns `call [mem]` into a lookup in a table of every generated function. Because the present is then three calls deep, a scene resumes by finishing the open functions from their call sites, innermost first. Two small things were wrong in the first guess: the picture is not at the usual buffer pointer (the present function receives it in `eax`), and the DPMI/selector code that the call graph also drags in is never executed in the 704 frames, so it stays a throwing stub.
