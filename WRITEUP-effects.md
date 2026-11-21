# PLASTIK - effects (work in progress)

Nothing here is ported yet: the frames in the web player are captured from the original code running under Unicorn (see README, "Exact vs approximated").

## Structure
`main` (0x2aa..) calls eight scene functions in order, each guarded by a quit flag. Every scene is a fixed-step loop on the 70 Hz tick counter, switching on the XM (order:row) position.

| scene | function | starts | what it shows (from captured frames) |
|---|---|---|---|
| A | 0x28264 | 0.0 s (0:0) | credit names as lit sphere sprites, "plastik" logo, star field |
| B | 0x26278 | 41.0 s (7:63) | flat-shaded shards flying over a 640x400 picture |
| C | 0x22af4 | 81.9 s (16:0) | not yet described |
| D | 0x1ddb4 | 112.8 s (22:1) | rotating stained-glass tunnel: a 40x19 grid of 16-pixel blocks warps a 256x256 texture, lit through a 32-level palette table (fade to black and to white) |
| E-H | 0x24168, 0x21e40, 0x2747c, 0x29634 | later | not yet described |

## Assets
`PLASTIK.DLL` is a flat archive: 33 PCX (credit names, environment map, aerial photo maps, clouds, 2200x100 greetings strip), one 3DS scene (`lugter2.3ds`), and `kola.bit`/`kola.idx` (3890 offsets into a bit-packed stream, unparsed, scene unknown).

## 3D engine
Pure x87 + integer. The 3DS loader builds a node hierarchy, normals and light tables at start-up (the "Doing hierarchy" and "Calculating lighttables" messages). Output is RGB565 at 640x400, triple buffered. A pixel pack routine at 0x2accc reads the colour channels from the bytes of a double (hypothesis, tables not yet decoded).

## Not done
Every effect renderer except scene D (A, B, C, E-H are still the captured video), the exact per-scene timings of C-H, and kola.bit.

## Scene D in the player
Rotating stained-glass tunnel (112.7 s to 143.4 s): a 40x19 grid of 16x16 blocks warps a 256x256 texture into a 640x300 picture centred in the 640x400 mode; each block is 8x8 bilinear texels drawn 2x2, shaded through a 64x768-byte palette-scale table. It is rendered live by the recompiled original and matches the emulator's frames pixel for pixel (see README for the caveats).

## Scenes A and B (ported by recompilation)
A is an 8-bit software renderer (640x300 index buffer, palette row per fade level, anti-aliased lines, alpha-blended fade); B is a flat-shaded 3D polygon engine writing RGB565 directly. Both run as the original code recompiled to JS and match the emulator frame for frame; see `re/NOTES.md` for the hand-ported loops and natives.

## Scenes C, E, F and H (ported by recompilation)
C shows a photo with a scrolling column of digits, E a rotating shiny 3D object in front of a striped background, H the "purple" logo built from discs (it runs 250 flips until the demo exits). All three are the original code recompiled to JS, bit-exact against the emulator's frames; see `re/NOTES.md` for sizes and browser speed. F (3824..4302) and G (4302..5006) are ported the same way: every scene is now live JavaScript and the player ships no video.
