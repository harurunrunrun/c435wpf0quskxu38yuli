import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='ec94273cd1ffaf3f0b71d23c9a58eadb00f964a42a62e86d2a9c7d375d08c29c';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('forced row colors equal every compatible full binary row, including original bounds, contradictions and allocation faults',{timeout:310000},async()=>{
 const r=await check('../scripts/check_fixed_run_forced_colors_cpp.py');
 for(const [key,value]of Object.entries({checks:18676424,apiCalls:1008660,partialRows:88573,literalFullAssignmentPairs:52092093,exhaustiveCompletionRevealPairs:1398101,primarySamples:4,consistentObservationClueGroups:921587,originalDomainGroups:919540,zeroRunExtensionGroups:2047,contradictoryObservationClueCases:77096,adapterCalls:2830,randomInputs:1800,metamorphicChecks:5273,invalidCalls:21,allocationFaults:6}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'16381575956586682632');assert.equal(r.maximumCases.length,10);
 assert(r.maximumCases.some(c=>c.n===200000&&c.k===100&&c.exists));
});
test('directly enumerated black-block starts agree with color pinning, known singleton frames and allocation exception unwinding',{timeout:310000},async()=>{
 const r=await check('../research/probes/fixed-run-forced-colors-independent.py');
 for(const [key,value]of Object.entries({checks:117367,apiCalls:45193,baseObservationCases:19796,clueSlackProfiles:2387,directBlockPlacements:1658887,compatiblePlacements:512906,knownSingletonFrameCases:19796,colorPinnedBranchCases:4256,sourceAdapterCalls:1314,contradictoryCases:2771,allocationFailureExceptions:14}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'6445428823580750785');
});
