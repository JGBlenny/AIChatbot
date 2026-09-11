import { chromium } from 'playwright';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const root=process.argv[2], out=process.argv[3], port=Number(process.argv[4]), route=process.argv[5];
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.json':'application/json'};
const srv=http.createServer((q,s)=>{let p=decodeURIComponent(q.url.split('?')[0]);let f=path.join(root,p);
  if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(root,'index.html');
  s.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream'});s.end(fs.readFileSync(f));});
await new Promise(r=>srv.listen(port,r));
const b=await chromium.launch(); const pg=await b.newPage({viewport:{width:1440,height:1000}});
await pg.addInitScript(()=>{localStorage.setItem('auth_token','vis-test')});
try{await pg.goto(`http://127.0.0.1:${port}${route}`,{waitUntil:'networkidle',timeout:15000});}catch{}
await pg.waitForTimeout(700);
const data=await pg.evaluate(()=>{
  const props=['margin','padding','font-size','color','background-color','border','border-radius','display','width','height','line-height','flex','gap'];
  const out=[];
  document.querySelectorAll('*').forEach((el,i)=>{
    if(i>1200)return;
    const cs=getComputedStyle(el); const r=el.getBoundingClientRect();
    const key=el.tagName+'.'+(el.className&&el.className.baseVal===undefined?String(el.className):'')+'#'+i;
    const o={k:key,rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]};
    props.forEach(p=>o[p]=cs.getPropertyValue(p));
    out.push(o);
  });
  return out;
});
fs.writeFileSync(out,JSON.stringify(data));
await b.close(); srv.close(); console.log('elements',data.length);
