import {readFile,writeFile,mkdir,mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../../',import.meta.url)),base=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2016-runtime-'));
const hash=x=>createHash('sha256').update(x).digest('hex');
try{
 const manifest=JSON.parse(await readFile(path.join(root,'research/snapshots/ioi-2016-manifest.json'),'utf8'));
 const original=Buffer.from(manifest.originalManifestRawBase64,'base64');assert.equal(hash(original),'cc27a3e4b8fc71957827f96c970bd67c62ca859c300930e54fa7636574dffdf7');
 for(const[key,count]of [['initialBundle',1431],['vendorBundle',105]]){
  const entry=manifest[key],raw=await readFile(path.join(root,entry.path));assert.equal(hash(raw),entry.sha256);const bundle=JSON.parse(gunzipSync(raw));assert.equal(bundle.files.length,count);
  for(const item of bundle.files){assert(!path.isAbsolute(item.path)&&!item.path.split('/').some(p=>p==='..'||p.startsWith('.env')));const bytes=Buffer.from(item.rawBase64,'base64');assert.equal(hash(bytes),item.sha256);const target=path.join(base,item.path);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,bytes,{flag:'wx'});}
 }
 const {compileLocalModules}=await import(pathToFileURL(path.join(base,'scripts/local-modules.mjs')));const out=path.join(base,'compiled');await compileLocalModules(base,out);const flow=await import(pathToFileURL(path.join(out,'flow.js')));
 const artifact=manifest.originalArtifacts.find(a=>a.artifact==='routes.json');const routesRaw=gunzipSync(await readFile(path.join(root,artifact.path)));assert.equal(hash(routesRaw),artifact.uncompressedSha256);const routes=JSON.parse(routesRaw);
 for(const row of Object.values(routes)){
  const actual=flow.walkFromRoot(row.choices,row.entryGraphId);assert.equal(actual.consumed,row.choices.length);assert.deepEqual(actual.steps,row.steps.map(s=>({graph:s.graphId,node:s.nodeId,answer:s.answer,target:s.target})));
  assert.deepEqual({graphId:actual.graph.id,nodeId:actual.current.id,type:actual.current.type,title:actual.current.title,options:flow.getNodeOptions(actual.current),techniques:actual.current.techniques??[],conditions:actual.current.conditions??[]},row.reached);
  for(const step of row.steps){const node=flow.getNode(flow.getGraph(step.graphId),step.nodeId);assert.equal(node.title,step.question);assert.equal(flow.getAnswerLabel(node,step.answer),step.answerLabel);}
 }
 console.log(JSON.stringify({frozenRuntimeReplayEqual:true,sixCanonicalRoutes:6,entryDomainIds:flow.entryGraphs.map(g=>g.id),flowGraphs:flow.graphs.length,allQuestionsAndFullAnswerLabelsEqual:true,productionApiCoverageClaimed:false},null,2));
}finally{await rm(base,{recursive:true,force:true});}
