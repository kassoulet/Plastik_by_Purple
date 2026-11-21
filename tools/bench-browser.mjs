// Browser speed (headless Chrome): ms/frame of each JS scene stepped straight from its entry state. node tools/bench-browser.mjs [ids]; WARM=1 lets the player's idle pre-warm (main.js) finish first (default: index.html?nowarm, cold JIT). Budget 42.9 ms (23.3 fps).
import {spawn} from 'child_process';import fs from 'fs';import http from 'http';import path from 'path';import {fileURLToPath} from 'url';
const root=path.join(path.dirname(fileURLToPath(import.meta.url)),'../web');
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.mp4':'video/mp4','.wasm':'application/wasm'};
const srv=http.createServer((q,r)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));if(p.endsWith('/'))p+='index.html';fs.stat(p,(e,s)=>{if(e){r.writeHead(404);r.end();return;}
  const h={'content-type':mime[path.extname(p)]||'application/octet-stream','accept-ranges':'bytes'},m=/bytes=(\d*)-(\d*)/.exec(q.headers.range||'');
  if(m){const a=m[1]?+m[1]:0,b=m[2]?+m[2]:s.size-1;r.writeHead(206,{...h,'content-range':`bytes ${a}-${b}/${s.size}`,'content-length':b-a+1});fs.createReadStream(p,{start:a,end:b}).pipe(r);}
  else{r.writeHead(200,{...h,'content-length':s.size});fs.createReadStream(p).pipe(r);}});}).listen(0);
const PORT=9300+Math.floor(Math.random()*500);
const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--autoplay-policy=no-user-gesture-required','--remote-debugging-port='+PORT,'about:blank'],{stdio:'ignore'});
const wait=ms=>new Promise(r=>setTimeout(r,ms));await wait(2000);
const tabs=await (await fetch('http://localhost:'+PORT+'/json')).json();const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pend={};ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id])pend[d.id](d);if(d.method==='Runtime.exceptionThrown')console.log('EXC',JSON.stringify(d.params.exceptionDetails).slice(0,300));};
const send=(method,params={})=>new Promise(r=>{pend[++id]=r;ws.send(JSON.stringify({id,method,params}))});
const ev=async e=>(await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result.result.value;
await send('Runtime.enable');await send('Page.navigate',{url:`http://localhost:${srv.address().port}/index.html${process.env.WARM?'':'?nowarm'}`});if(process.env.WARM){const t=Date.now();while(!(await ev('window.pl&&window.pl.warm.done'))&&Date.now()-t<180000)await wait(500);console.log('warm',JSON.stringify(await ev('window.pl.warm')));}
const ids=(process.argv[2]||'a,b,c,d,e,f,h').split(',');
for(const id of ids){const r=await ev(`(async()=>{const m=await import('./js/plastik-${id}-scene.mjs');const xm=await (await fetch('assets/system-times.json')).json();const b=new Uint8Array(await (await fetch('assets/plastik-${id}-init.bin')).arrayBuffer());
const f0={a:0,b:955,c:1912,d:2629,e:3346,f:3824,h:5006}['${id}'];const s=new m['${id.toUpperCase()}Scene'](m.unpackInit(b),xm,f0);const N=300,t=[];for(let i=0;i<N;i++){const a=performance.now();if(!s.step())break;t.push(performance.now()-a);}
t.sort((x,y)=>x-y);const sum=t.reduce((x,y)=>x+y,0);return {n:t.length,avg:sum/t.length,p50:t[t.length>>1],p95:t[Math.floor(t.length*.95)],max:t[t.length-1],over:t.filter(x=>x>42.9).length};})()`);
console.log(id,JSON.stringify(r,(k,v)=>typeof v==='number'?Math.round(v*10)/10:v));}
ch.kill();srv.close();process.exit(0);
