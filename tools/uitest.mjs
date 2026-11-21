// UI smoke test (headless Chrome, CDP): play advances, pause holds, seek jumps, Right key = +5 s. Exit code 1 on failure.
import {spawn} from 'child_process';import fs from 'fs';import http from 'http';import path from 'path';import {fileURLToPath} from 'url';
const root=path.join(path.dirname(fileURLToPath(import.meta.url)),'../web');
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.wasm':'application/wasm'};
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
await send('Runtime.enable');await send('Page.navigate',{url:`http://localhost:${srv.address().port}/index.html`});
for(let i=0;i<100&&!(await ev('!!window.pl&&!document.getElementById("gob").hidden'));i++)await wait(200);
let bad=0;const ok=(c,m)=>{console.log(c?'ok  ':'FAIL',m);if(!c)bad++;};
const cur=()=>ev('window.pl.cur()');
try{
await ev('document.getElementById("gob").click()');await wait(3500);const a=await cur();ok(a>1.5&&a<5,'play advances: '+a);
await ev('document.getElementById("pp").click()');const p0=await cur();await wait(1200);ok(await cur()===p0,'pause holds: '+p0);
await ev('window.pl.seek(100)');await wait(500);ok(Math.abs(await cur()-100)<0.5,'seek to 100 s: '+await cur());
await ev('document.getElementById("seek").focus()');
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight',windowsVirtualKeyCode:39});
await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowRight',code:'ArrowRight',windowsVirtualKeyCode:39});await wait(400);
ok(Math.abs(await cur()-105)<1,'Right = +5 s: '+await cur());
await ev('document.getElementById("pp").click()');const q=await cur();await wait(2000);ok(await cur()>q+1,'play from seek: '+await cur());
await ev('window.pl.seek(30)');await wait(2500);
const shown='(()=>{const c=document.getElementById("cv");if(c.hidden)return false;const d=c.getContext("2d").getImageData(0,100,640,200).data;let s=0;for(let i=0;i<d.length;i+=4)s+=d[i]+d[i+1]+d[i+2];return s>1e6;})()';
for(const [t,id] of [[30,'A'],[60,'B'],[100,'C'],[125,'D'],[150,'E'],[170,'F'],[200,'G'],[218,'H']]){await ev('window.pl.seek('+t+')');await wait(2500);ok(await ev(shown),'scene '+id+' canvas shown and not blank at '+t+' s');}
}catch(e){console.log('FAIL',e);bad++;}
ch.kill();srv.close();process.exit(bad?1:0);
