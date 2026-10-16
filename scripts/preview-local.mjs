import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const directory = path.join(site,'dist-local');
const args = process.argv.slice(2);
let port = 4321, host = '127.0.0.1';
for(let i=0;i<args.length;i++) {
  if(args[i]==='--port') port=Number(args[++i]);
  else if(args[i]==='--host') host=args[++i] || '127.0.0.1';
  else throw new Error(`Unknown option: ${args[i]}`);
}
if(!Number.isInteger(port)||port<1||port>65535)throw new Error('Port must be 1–65535');
try { await stat(path.join(directory,'index.html')); }
catch { console.error('先に npm run build:local を実行してください。'); process.exit(1); }
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf'};
const server=http.createServer(async(req,res)=>{
  try {
    const url=new URL(req.url,'http://localhost');
    if(url.pathname==='/'){res.writeHead(302,{Location:'/flowchartcp/'});res.end();return;}
    if(url.pathname==='/flowchartcp'){res.writeHead(302,{Location:'/flowchartcp/'});res.end();return;}
    if(!url.pathname.startsWith('/flowchartcp/')){res.writeHead(404);res.end('Not found');return;}
    const file=path.resolve(directory,decodeURIComponent(url.pathname.slice('/flowchartcp/'.length)));
    if(file!==directory&&!file.startsWith(directory+path.sep)){res.writeHead(403);res.end();return;}
    const info=await stat(file);
    if(info.isDirectory()&&!url.pathname.endsWith('/')){res.writeHead(302,{Location:url.pathname+'/'+url.search});res.end();return;}
    const target=info.isDirectory()?path.join(file,'index.html'):file;
    const data=await readFile(target);
    res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});
    res.end(req.method==='HEAD'?undefined:data);
  }catch(error){res.writeHead(error instanceof URIError?400:404);res.end('Not found');}
});
server.on('error',error=>{console.error(error.message);process.exitCode=1;});
server.listen(port,host,()=>console.log(`Local preview: http://${host}:${port}/flowchartcp/\nCtrl+C で停止します。`));
