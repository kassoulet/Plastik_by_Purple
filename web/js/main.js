// Player: every scene (A-H) is rendered live by its JS port (the recompiled original); libopenmpt (chiptune3) is the master clock.
const $=id=>document.getElementById(id),sk=$('seek');
let cp,ac,buf,dur=230.4,playing=false,started=false,t0=0,w0=0,vol=1,muted=false,drag=false;
const now=()=>performance.now()/1000,fmt=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');
const cur=()=>Math.min(dur,playing?t0+now()-w0:t0);
async function init(){
  const {ChiptuneJsPlayer}=await import('../vendor/chiptune3.js');
  ac=new AudioContext();cp=new ChiptuneJsPlayer({context:ac,repeatCount:0,interpolationFilter:8});cp.gain.connect(ac.destination);
  await new Promise(r=>cp.onInitialized(r));
  cp.onProgress(m=>{if(!playing||now()-w0<.2)return;const p=m.pos-((ac.outputLatency||0)+(ac.baseLatency||0));if(Math.abs(p-cur())>.05){t0=Math.max(0,p);w0=now();}});
  cp.onMetadata(m=>{if(m.dur){dur=m.dur;sk.max=Math.round(dur*10);}});
  cp.onEnded(()=>{playing=false;t0=dur;ui();});
  buf=await (await fetch('assets/system.xm')).arrayBuffer();
}
function ui(){$('pp').textContent=playing?'Pause':'Play';$('mute').textContent=muted||!vol?'Muted':'Vol';}
async function start(){if(started)return;started=true;$('go').hidden=true;await init();cp.play(buf);play(0);}
function play(t){t0=t===undefined?cur():t;w0=now();playing=true;if(t!==undefined)cp.setPos(t);else cp.unpause();ac.resume();ui();}
function pause(){t0=cur();playing=false;cp.pause();ui();}
function seek(t){t=Math.max(0,Math.min(dur-.05,t));t0=t;w0=now();cp&&cp.setPos(t);}
const toggle=()=>!started?start():playing?pause():(t0>=dur-.1?(cp.play(buf),play(0)):play());
function setVol(x){vol=Math.max(0,Math.min(1,x));$('vol').value=Math.round(vol*100);cp&&cp.setVol(muted?0:vol);ui();}
const cv=$('cv'),cx=cv.getContext('2d'),im=cx.createImageData(640,400),px=new Uint32Array(im.data.buffer);
// recompiled scenes: first = first flip of the 23.33 fps capture clock that shows one of its frames (the display lags the render by one flip), n = frame count, f0 = flip at the scene's entry
const SC=[['a',1,955,0],['b',956,957,955],['c',1913,717,1912],['d',2630,717,2629],['e',3347,478,3346],['f',3825,478,3824],['g',4303,704,4302],['h',5007,250,5006]].map(([id,first,n,f0])=>({id,first,n,f0,init:'assets/plastik-'+id+'-init.bin'}));
let lastN=-2,lastId='';
const xmP=fetch('assets/system-times.json').then(r=>r.json());
for(const sc of SC) sc.p=Promise.all([import('./plastik-'+sc.id+'-scene.mjs'),fetch(sc.init).then(r=>r.arrayBuffer()),xmP]).then(([m,b,xm])=>{sc.s=new m[sc.id.toUpperCase()+'Scene'](m.unpackInit(b),xm,sc.f0);}).catch(e=>console.warn('JS scene '+sc.id+' unavailable',e));
function drawScene(t){const k=Math.floor(t*70/3);
  for(const sc of SC){const n=k-sc.first;if(sc.s&&n>=0&&n<sc.n){if(n!==lastN||sc.id!==lastId){const s=sc.s.frame(n);if(s){const u=new Uint16Array(s.buffer,s.byteOffset,640*400);
      for(let i=0;i<u.length;i++){const a=u[i],r=(a>>11)<<3,g=((a>>5)&63)<<2,b=(a&31)<<3;px[i]=0xff000000|(b|b>>5)<<16|(g|g>>6)<<8|(r|r>>5);}cx.putImageData(im,0,0);lastN=n;lastId=sc.id;}}}}
}
function loop(){const t=cur();drawScene(t);if(!drag)sk.value=Math.round(t*10);$('tm').textContent=fmt(t)+' / '+fmt(dur);
  requestAnimationFrame(loop);}
$('pp').onclick=toggle;$('b5').onclick=()=>seek(cur()-5);$('f5').onclick=()=>seek(cur()+5);
$('fs').onclick=()=>document.fullscreenElement?document.exitFullscreen():$('stage').requestFullscreen();
$('mute').onclick=()=>{muted=!muted;cp&&cp.setVol(muted?0:vol);ui();};$('vol').oninput=e=>setVol(e.target.value/100);
sk.oninput=()=>seek(sk.value/10);sk.onpointerdown=()=>drag=true;addEventListener('pointerup',()=>drag=false);
$('gob').onclick=start;
addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'&&e.target.type!=='range')return;const k=e.key;
  if(k===' '||k==='p'){e.preventDefault();toggle();}else if(k==='ArrowLeft'){e.preventDefault();seek(cur()-(e.shiftKey?10:5));}
  else if(k==='ArrowRight'){e.preventDefault();seek(cur()+(e.shiftKey?10:5));}else if(k==='Home')seek(0);else if(k==='End')seek(dur-1);
  else if(k==='f'||k==='F')$('fs').click();else if(k==='m'||k==='M')$('mute').click();});
SC[0].p.finally(()=>{$('gomsg').hidden=true;$('gob').hidden=false;$('gob').focus();});   // Play is offered once scene A is loaded
// Pre-warm: V8 has no type feedback for recompiled code first reached later in a scene, so those frames run cold or deoptimise (first frames 50-1000 ms, E's wireframes at frame ~120, H at 25 and 215).
// While the Play button is showing, step each scene's frames in 25 ms slices; stops at once on Play. Output is unaffected: the run is deterministic and frame() restores a checkpoint on the first real request. ?nowarm disables it.
const WARM=[['a',30],['b',10],['c',4],['d',6],['e',8],['f',8],['g',10],['h',10],['e',135],['h',28],['f',133],['c',20]],warm={frames:0,done:false,ms:0};
(async()=>{const T=performance.now();
  if(!/nowarm/.test(location.search)){await SC[0].p;
    for(const [id,k] of WARM){const sc=SC.find(x=>x.id===id);await sc.p;sc.wn=sc.wn||0;
      while(sc.s&&sc.wn<k){if(started)return;const t=performance.now();
        while(sc.wn<k&&performance.now()-t<25){if(!sc.s.frame(sc.wn)){sc.wn=k;break;}sc.wn++;warm.frames++;}
        await new Promise(r=>setTimeout(r));}}}
  warm.done=true;warm.ms=performance.now()-T;})();
window.pl={seek,toggle,cur,warm,get playing(){return playing;}};
loop();
