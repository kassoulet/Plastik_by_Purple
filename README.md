# PLASTIK - Purple, The Party 1998 (DOS, 640x400 high colour)

Reverse engineering and web player for **plastik** by Purple (code vipa, rbecue; gfx thorsten, mads; music mystical). The original files (`PLASTIK.EXE`, `PLASTIKW.EXE`, `PLASTIK.DLL`, `SYSTEM.XM`) stay untouched next to the port.

**Status: every scene is ported.** All eight scenes (A to H, 5257 flips, 0 - 225 s) are the original x86 statically recompiled to JavaScript and drawn live in the browser, bit-exact against the frames of an emulator running the original (the golden frames). No video is shipped. The module is played by libopenmpt, not the original MIDAS mixer. The honest tables below say what is what.

## The original
- `PLASTIK.EXE` (DOS): MZ stub + **PMODE/W 1.30** + Watcom C 32-bit flat program, **MIDAS Sound System 0.6.1**, VESA 2.0 linear framebuffer **640x400x16 (RGB565), triple buffered** (`-F`: 640x480). Software 3D engine, x87 floating point, no MMX. Needs a P200.
- `PLASTIKW.EXE`: the Win32 build (DirectDraw, MIDAS 1.1.2 DLL).
- `PLASTIK.DLL` is not a library but a data archive (33 PCX pictures, one 3DS scene, `kola.bit/.idx`): `re/dll.py`.
- `SYSTEM.XM`: the 3.8 minute module. The demo is a fixed-step function of the display tick counter and of the module position (order/row), see `re/NOTES.md`.
- Aspect ratio: 640x400 pixels are shown square (16:10), not stretched to 4:3. The frames are letterboxed 640x300 pictures, and the sphere and logo disc are round only at square pixels (stretching to 4:3 turned them into ovals). The original VGA mode is 70 Hz; whether the authors tuned for a 4:3 CRT is unknown, the picture content says square.

## What is in this repository
| path | content |
|---|---|
| `re/NOTES.md` | running log: formats, memory map, time model, scene table, todo |
| `re/unpack_clean.py`, `unpack_pmodew.py` | run the EXE's own PMODE/W loader under Unicorn, dump RAM at the program entry |
| `re/emucore.py`, `re/harness.py` | DOS/DPMI/VESA emulation, virtual clock, frame capture (`python3 harness.py NFRAMES OUTDIR [step]`, env `K`, `VIDEO`, `RAW`, `PROFILE`, `DUMP`) |
| `re/x86js.py`, `re/mk_init.py`, `re/mk_dinit.py` | static recompiler (objdump -> JS) and the entry-state packers (page list; D's older format) |
| `re/dll.py`, `re/xmtime.py` | archive parser + PCX decoder; XM order/row -> time table |
| `web/` | player (`index.html`, `js/main.js`, libopenmpt in `vendor/`, `assets/system.xm`, `assets/plastik-{a,b,c,d,e,f,g,h}-init.bin`, `assets/system-times.json`) |
| `WRITEUP-asm.md`, `WRITEUP-effects.md` | write-ups (work in progress) |

The player no longer ships any video (the 25 MB `plastik.mp4` of the emulator capture is gone from `web/assets`, the web payload is about 14 MB). Every range is drawn live by the JS ports (A 0 - 40.9 s, B - 81.9, C - 112.7, D - 143.4, E - 163.9, F - 184.4, G - 214.6, H - 225.4). The capture is only a by-product of the golden-frame harness: regenerate it with the command below if you want it (`VIDEO=` is the video, `RAW=` the raw frames the tests diff against).

Checks: `node tools/uitest.mjs` (headless Chrome: play, pause, seek, +5 s, canvas shown at one time per scene A..H; passes), `node tools/test-d-scene.mjs GOLDEN_PNG_DIR 1000` (D frames vs golden, 7 checked 0 bad), `node tools/test-scene.mjs a|b|c|e|f|h INIT RAW_DIR n` (frames vs harness RAW frames, bit-exact), `node tools/bench-browser.mjs [ids]` (ms/frame in headless Chrome), `node tools/test-seek.mjs a|b|c|d|e|f|h` (checkpoint seek == straight run), `node tools/test-d-tables.mjs`.

Run the player: `cd web && python3 -m http.server 8000`. Pause, seek (slider, arrows, +-5 s), volume and fullscreen work; the module is the master clock and the picture follows it.

Regenerate the golden capture / the emulator video (needs `unicorn`, `numpy`, `Pillow`, `ffmpeg`; no `-I`):
```
python3 re/unpack_clean.py $PL_MEM            # 64 MB RAM image at the entry, ~2 s
cd re && PL_MEM=... VIDEO=/tmp/plastik.mp4 RAW=/tmp/raw python3 harness.py 5500 /tmp/g 100   # ~30 min
```

## Exact vs approximated (kept honest)
| item | state |
|---|---|
| EXE unpack, entry, DLL archive layout, PCX decoding | exact (checked: all 33 PCX decode, entries tile the file with no gap) |
| Golden frames (tests only) | captured from the original code running in Unicorn, 640x400 RGB565 (`RAW=`); not shipped. |
| Time model of the capture | approximated: 70 Hz tick, frames every 3 ticks (23.3 fps), XM position from a theoretical timeline (`xmtime.py`) instead of MIDAS's player. The real demo ran at whatever frame rate the machine gave; the logic is tick-locked, so the *content* at a given tick is the same, the sampling is not. |
| Audio | libopenmpt playing `SYSTEM.XM`, not the MIDAS mixer of the original (interpolation, ramping differ). |
| Scene D in JS (`web/js/plastik-d-scene.mjs`) | **bit-exact against the emulator's frames** (golden PNGs 2700..3300, every 100th, 0 differing pixels; RAM identical to the emulator at the first frames). It is *not* a rewrite: `re/x86js.py` statically recompiles the original x86 (scene D's call graph, ~1200 lines of JS, `plastik-d.gen.mjs`) onto flat memory plus an x87 stack; only the 16x16 block routine 0x2accc is a hand port (`plastik-d-block.mjs`), checked by the same frame diff. 13.9 ms/frame in Node (budget 43 ms). Known gaps: (1) the first D frame of the capture shows stale memory left by scene C and is not reproduced (the player starts D one flip later); (2) the initial state (tables not built by D, texture, 8 KB of stack the code reads uninitialised) is a snapshot of the emulator at D's entry, `web/assets/plastik-d-init.bin`, not built by earlier scenes in JS; (3) sin/cos/atan2 use JS `Math` rather than the x87, no difference seen so far, but 1-ulp divergence is possible; (4) only 7 frames are compared against PNGs, the rest rely on the RAM match. |
| Scenes A and B in JS (`web/js/plastik-{a,b}-scene.mjs`) | **bit-exact against the emulator's frames**, all 955 (A) and 957 (B) frames, 0 differing pixels. Same method as D (static recompilation of the original x86, `plastik-{a,b}.gen.mjs`); two hand-ported inner loops in A (palette conversion, line drawing) and a native alpha blend are checked only by the frame diff. Entry state is a snapshot of the emulator's RAM at the scene start (~0.5 MB each), not rebuilt from the data files. Golden flip 0 is blank and not reproduced. JS ~30 ms/frame in Node (43 ms budget); browser speed below. |
| Scenes C, E, F, H in JS (`web/js/plastik-{c,e,f,h}-scene.mjs`) | **bit-exact against the emulator's frames**: C 717, E 478, F 478, H 250 frames, 0 differing pixels (the demo exits at flip 5257, so H has no golden frame after its 250th). Same method; entry snapshots pruned to the pages the scene reads (C 2.6 MB because of the photo, E 1.2 MB, F and H 0.9 MB). Speed in headless Chrome (budget 42.9 ms/frame, first 300 frames of each scene, `tools/bench-browser.mjs`): A avg 20.2 ms, B 10.9, C 11.9, D 9.4, E 15.4 (4 of 300 frames over budget), F 11.1 (4 over), G 17.4 (2 over), H 16.0 (2 over of 251); the first frame of a scene can take several hundred ms (JIT warm-up). Hand-ported inner loops (palette conversion, the RGB565 anti-aliased wireframe line loop at 0x535dd used by B/E/F/G, E/F/G/H scanline fill, F's clamp and palette passes) are checked only by the frame diffs. |
| Scene G in JS (`web/js/plastik-g-scene.mjs`) | **bit-exact**, 704 frames. Needed indirect calls through function pointers filled at run time (the recompiler now emits a lookup table and takes extra entries) and a resume chain, because its present is three calls deep. DPMI, `lsl`, `int3` code reachable from G is stubbed (throws) and never executed in the 704 frames. Init 1.3 MB. Browser speed: see the C/E/F/H row. |

## Scene D
It was black in the first capture: a **Unicorn bug** (FYL2X with a zero operand does not pop the x87 stack) corrupted the log table that builds D's palette. Worked around in `re/harness.py`, details in `re/NOTES.md`.

## Next
See `re/NOTES.md`. Open: the scene boundaries are verified frame by frame but the entry snapshots are RAM dumps from the emulator, not rebuilt from the data files; the original's timing (the module position, 70 Hz tick) is the harness's approximation; frames over the 42.9 ms budget remain in E, F, H on slow machines (JIT warm-up, `switch(pc)` dispatch of recompiled loops).
