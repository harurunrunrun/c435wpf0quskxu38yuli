import { mkdir, writeFile, readFile, readdir, unlink } from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import { compileLocalModules } from './local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output = path.join(site,'.cache/modules');
await compileLocalModules(site,output);
const { graphs, renderFlowSvg } = await import(pathToFileURL(path.join(output,'flow.js')).href+'?build='+Date.now());
const metadata = (await Promise.all((await readdir(path.join(site,'data'))).filter(name => name.startsWith('techniques-')).map(async name => JSON.parse(await readFile(path.join(site,'data',name),'utf8'))))).flat();
const titles = Object.fromEntries(metadata.map(item=>[item.id,item.title]));
const diagramDirectory=path.join(site,'public/diagrams');
await mkdir(diagramDirectory,{recursive:true});
const currentFiles=new Set(graphs.map(graph=>graph.id+'.svg'));
for(const name of await readdir(diagramDirectory)) {
  if(!name.endsWith('.svg') || currentFiles.has(name)) continue;
  const file=path.join(diagramDirectory,name);
  const old=await readFile(file,'utf8');
  if(old.includes(`data-flow-svg="${name.slice(0,-4)}"`)) await unlink(file);
}
for (const graph of graphs) await writeFile(path.join(site,'public/diagrams',graph.id+'.svg'),renderFlowSvg(graph,'/flowchartcp/',titles));
console.log(`Generated ${graphs.length} SVG diagrams from the shared decision graphs.`);
