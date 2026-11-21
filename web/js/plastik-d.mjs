// Scene D ("stained-glass tunnel") table builders, ported from the original: 0x1d76c (log/exp tables) and the prologue of 0x1ddb4.
// Checked against the original's RAM (tools/test-d-tables.mjs, re/golden/d-inputs.bin).  The x87 code stores truncated (frndint, RC=chop) bytes.
const t=Math.trunc;
// log[x] = chop(46.1662*ln x) (x=0: -inf -> fistp "indefinite" 0x80000000 -> byte 0); exp[x] = chop(x*0.004*0.00390625*e^(0.021660868774124792*x)), clipped to 255.
export function logExp(){
  const log=new Uint8Array(512),exp=new Uint8Array(512);
  for(let x=1;x<512;x++)log[x]=t(46.1662*Math.log(x));
  for(let x=0;x<512;x++)exp[x]=Math.min(255,t(x*0.004*0.00390625*Math.exp(0.021660868774124792*x)));
  return {log,exp};
}
// palette used by the tunnel: product in the log domain, pal[i] = exp[log[4*pal0[i]] + log[0xd2]]  (0xd2 = 210: the byte at 0xc517d2)
export function palette(pal0,{log,exp}){return Uint8Array.from(pal0,v=>exp[log[4*v]+log[0xd2]]);}
// 32 darker copies of the palette: scale[k*768+i] = chop(pal[i]*k/32); the original then appends 32 copies fading to white (not ported yet).
export function darkTable(pal){const s=new Uint8Array(32*768);for(let k=0;k<32;k++)for(let i=0;i<768;i++)s[k*768+i]=t(pal[i]*k*0.03125);return s;}
// the full 0xc000-byte table at 0xc1afc0: 32 dark copies, then 32 copies fading to white: chop(pal*(31-j)/32 + 8j)   (second half: from the build notes, checked by the frame diff)
export function scaleTable(pal){const s=new Uint8Array(64*768);s.set(darkTable(pal));for(let j=0;j<32;j++)for(let i=0;i<768;i++)s[(32+j)*768+i]=t(pal[i]*(31-j)/32+8*j);return s;}
