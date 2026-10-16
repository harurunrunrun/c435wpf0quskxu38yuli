import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='b4497f26102e1d3ba262a63f98943aebe81c72b5b7ef6b18b283c2c11edbc609';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('precompiled membership restores every small permutation and checks all original budgets and grader callback forms',{timeout:310000},async()=>{
 const r=await check('../scripts/check_precompiled_permutation_cpp.py');
 assert.equal(r.checks,95249053);assert.equal(r.apiCalls,42080);
 const g=r.genericWithoutGraderStub;
 for(const [key,value]of Object.entries({checks:77823670,apiCalls:41705,allSmallPermutations:40347,allSmallReplyBitstrings:261,compatibleCompleteTranscripts:27,sourceBudgetCases:830,extensionCases:205,randomCases:1000,invalidApiCalls:39,oracleGuardTests:5,callbackFailures:7,nestedCalls:1}))assert.equal(g[key],value,key);
 assert.equal(g.checksum,'4045640110253301528');assert.equal(g.sourceStructuredCases.length,30);
 assert.equal(r.syntheticHeaderAdapters.length,3);
 for(const a of r.syntheticHeaderAdapters){assert.equal(a.actualOriginalHeaderRetrieved,false);assert.equal(a.checks,5808461);assert.equal(a.apiCalls,125);assert.equal(a.invalidPreflight,5);assert.equal(a.checksum,'16364191081451181720');}
});
test('independent integer zero-support oracle covers group action, every large transposition and all callback/allocation faults',{timeout:310000},async()=>{
 const r=await check('../research/probes/precompiled-permutation-independent.py');
 for(const [key,value]of Object.entries({checks:1803910389,apiCalls:55634,allSmallPermutations:40347,affinePermutations:2859,allTranspositions:10760,randomFull128:256,allocationFailures:510,callbackExceptionsBeforeAfter:194,callbackTypeCases:3,oracleSelfchecks:168726}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'5007159836349817482');
});
