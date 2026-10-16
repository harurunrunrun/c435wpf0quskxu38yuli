import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
const run=promisify(execFile),hash='890af3ba0d61b726576a464272e51ac2816e3ca2bf59facee194b58a5f0972bd';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('hidden tree reconstruction uses legal spanning-tree queries for every small graph/secret and dense source maxima with explicit synthetic header variants',{timeout:310000},async()=>{
 const r=await check('../scripts/check_spanning_tree_overlap_cpp.py');assert.equal(r.genericWithoutHeaderCompiled,true);
 const c=r.constReferenceHeaderFull;
 for(const [key,value]of Object.entries({checks:711667,recoverCalls:11275,literalValidTreeQuestions:371287,literalQuestionEntries:37828515,exhaustiveConnectedGraphs:771,everyHiddenTreeForEverySmallGraph:8135,completeN6PruferHiddenTrees:1296,randomGraphs:400,metamorphicChecks:1200,invalidCases:36,originalAdapterCalls:140}))assert.equal(c[key],value,key);
 assert.equal(c.maximumCases.length,8);assert.equal(c.checksum,'14758130767299308416');
 assert.equal(r.mutableReferenceHeaderApiSmoke.checks,1559);assert.equal(r.mutableReferenceHeaderApiSmoke.checksum,'141949014370290246');
});
test('coherent transcripts, independent leaf stripping and allocation/callback/budget faults preserve a fixed-secret reconstruction',{timeout:310000},async()=>{
 const r=await check('../research/probes/spanning-tree-overlap-independent.py');
 for(const [key,value]of Object.entries({checks:30227,consistentAdversarialTranscripts:396,independentLeafStrippingTreeChecks:11917,allPerCallBudgetsChecked:32,everyCallbackExceptionPosition:29,allocationFailureExceptions:276,maximumDenseN500ApiRequestedPayloadBytes:2713370,maximumDenseN500Queries:5229}))assert.equal(r[key],value,key);
 assert.equal(r.additionalProbeSanitized,false);assert.equal(r.checksum,'2819309625694043276');
});
