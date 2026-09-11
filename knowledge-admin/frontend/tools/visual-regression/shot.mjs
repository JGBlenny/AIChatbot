import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2], out = process.argv[3], port = Number(process.argv[4]);
const mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.json':'application/json','.png':'image/png'};
const srv = http.createServer((req,res)=>{
  let p = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(root, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(root,'index.html');
  res.writeHead(200,{'Content-Type': mime[path.extname(f)]||'application/octet-stream'});
  res.end(fs.readFileSync(f));
});
await new Promise(r=>srv.listen(port,r));

const routes = JSON.parse(fs.readFileSync(process.argv[5],'utf8'));
const b = await chromium.launch();
const pg = await b.newPage({viewport:{width:1440,height:1000}});
// 讓受保護頁面過關：塞一個假 token
await pg.addInitScript(()=>{ localStorage.setItem('auth_token','vis-test'); });
fs.mkdirSync(out,{recursive:true});
for (const r of routes) {
  try {
    await pg.goto(`http://127.0.0.1:${port}${r.path}`, {waitUntil:'networkidle', timeout:15000});
  } catch { /* API 不在，networkidle 可能逾時，照樣截圖 */ }
  await pg.waitForTimeout(700);
  await pg.screenshot({path: path.join(out, r.name + '.png'), fullPage: false});
}
await b.close(); srv.close();
console.log('shots:', routes.length);
