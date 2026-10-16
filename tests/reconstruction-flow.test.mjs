import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,readdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {compileLocalModules} from '../scripts/local-modules.mjs';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
let temporary;
const implementation=(async()=>{temporary=await mkdtemp(path.join(tmpdir(),'flowchartcp-reconstruction-flow-'));await compileLocalModules(site,temporary);return {flow:await import(pathToFileURL(path.join(temporary,'flow.js'))),viewer:await import(pathToFileURL(path.join(temporary,'diagram-viewer.js')))};})();
after(async()=>{await implementation;await rm(temporary,{recursive:true,force:true});});
const stringPrefix=['extraction','subsequence','common-reconstruction'];
const memoryPrefix=['generation-history','history','sequential-conditions','lcs-reconstruction'];
const polynomialPrefix=['counting-totals','poly','yes','coefficient-values','values-shift','known-samples'];
const ids=['lcs-hirschberg-reconstruction','polynomial-interpolation-product-tree','lagrange-consecutive-values'];
function walk(flow,domain,choices){const value=flow.walkFromRoot(choices,domain);assert.equal(value.consumed,choices.length);return value;}
function candidates(value){return value.current.techniques??[];}
function replayState(flow,domain,choices){let state=flow.initialState(domain);for(const answer of choices){while(flow.evaluateState(state).current.type==='route')state=flow.enterFlowRoute(state);state=flow.answerState(state,answer);}while(flow.evaluateState(state).current.type==='route')state=flow.enterFlowRoute(state);return state;}

test('LCS reconstruction is reachable from sequence features and memory constraints, retaining the originating field',async()=>{
 const {flow,viewer}=await implementation;
 for(const [domain,prefix] of [['strings',stringPrefix],['dp',memoryPrefix]]){
  const choices=[...prefix,'sequence','yes'];const value=walk(flow,domain,choices);
  assert(candidates(value).includes(ids[0]));
  assert.match(value.current.conditions.join(' '),/O\(NM\)/);
  assert.match(value.current.conditions.join(' '),/辞書順/);
  let state=replayState(flow,domain,choices);
  assert.deepEqual(flow.evaluateState(state).current,value.current);
  assert.equal(flow.getFlowDomainId(state),domain);
  assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)),state);
  assert.deepEqual(viewer.diagramState(state.graph,flow.serializeFlowHash(state)),state);
  const weight=s=>s.answers.length+(s.trail??[]).reduce((sum,c)=>sum+c.answers.length+1,0);
  for(let left=weight(state)+1;weight(state);left--){assert(left>0);const previous=flow.backFlowState(state);assert(weight(previous)<weight(state));assert.equal(flow.getFlowDomainId(previous),domain);state=previous;}
  assert.deepEqual(state,flow.initialState(domain));
 }
 assert(candidates(walk(flow,'strings',[...stringPrefix,'length','yes'])).includes('dp-dimension-rolling'));
 for(const answer of ['no','unknown']){
  assert(!candidates(walk(flow,'strings',[...stringPrefix,'sequence',answer])).includes(ids[0]));
  assert(!candidates(walk(flow,'strings',[...stringPrefix,'length',answer])).includes(ids[0]));
 }
 const unknown=walk(flow,'strings',[...stringPrefix,'unknown']);assert.equal(unknown.current.type,'question');assert.equal(unknown.current.id,'check');
});

test('polynomial reconstruction requires field/distinctness or a proved degree and usable factorials',async()=>{
 const {flow}=await implementation;
 const coefficient=walk(flow,'math',[...polynomialPrefix,'coefficients','yes','yes']);
 assert(candidates(coefficient).includes(ids[1]));assert.match(coefficient.current.conditions.join(' '),/互いに異な/);assert.match(coefficient.current.conditions.join(' '),/998244353/);
 const single=walk(flow,'math',[...polynomialPrefix,'one-value','yes','yes']);
 assert(candidates(single).includes(ids[2]));assert.match(single.current.conditions.join(' '),/D<p/);assert.match(single.current.conditions.join(' '),/次数/);assert.match(single.current.conditions.join(' '),/一致/);
 for(const choice of ['coefficients','one-value'])for(const answer of ['no','unknown'])for(const suffix of [[answer],['yes',answer]]){
  const value=walk(flow,'math',[...polynomialPrefix,choice,...suffix]);
  assert(ids.every(id=>!candidates(value).includes(id)),`${choice}/${suffix}: missing properties do not select reconstruction`);
 }
 const unknown=walk(flow,'math',[...polynomialPrefix,'unknown']);assert.equal(unknown.current.type,'question');assert.equal(unknown.current.id,'check');
});

test('new techniques have verified original examples, root walks and rendered article links',async()=>{
 const {flow}=await implementation;
 const files=await readdir(path.join(site,'data'));
 const metadata=(await Promise.all(files.filter(n=>/^techniques-.*\.json$/.test(n)).map(async n=>JSON.parse(await readFile(path.join(site,'data',n),'utf8'))))).flat();
 const references=(await Promise.all(files.filter(n=>/^references-.*\.json$/.test(n)).map(async n=>JSON.parse(await readFile(path.join(site,'data',n),'utf8'))))).flat();
 const walks=JSON.parse(await readFile(path.join(site,'data/problem-walks.json'),'utf8'));
 for(const id of ids){
  const item=metadata.find(t=>t.id===id);assert(item);assert.equal(item.status,'reviewed');assert(item.aliases.some(a=>/[A-Za-z]/.test(a)));
  const examples=references.filter(row=>row.techniqueId===id);assert(examples.length>=1);
  if(id!==ids[1])assert(examples.length>=2,`${id}: string/integer or two different polynomial sources`);
  for(const row of examples){
   const record=walks.find(w=>w.statementUrl===row.url&&w.expectedTechniqueIds.includes(id));assert(record);assert.equal(record.reviewStatus,'verified');assert.equal(record.verificationKind,row.verification);assert(record.features.length>=2);
   const value=walk(flow,record.entryGraphId,record.choices);assert(candidates(value).includes(id));
   assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${id}/`));
  }
 }
});
