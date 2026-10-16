import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='97748db7491b31d9799fc9cdd1e672e4de97aef0221cc6c36a9bded5a874d42c';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('diagonal square union matches arbitrary literal photo sets, independent partition DP, penalty ties and original-range API boundaries',{timeout:310000},async()=>{
 const r=await check('../scripts/check_diagonal_square_union_cpp.py');
 for(const [key,value]of Object.entries({checks:5427033,apiCalls:696640,originalAdapterCalls:589343,allInterestSubsetsM1to5:33861,literalAllPhotoSubsets:33940,literalRequestedPhotoLimits:251085,penaltyCostAndFewerCountComparisons:884000,convexityAndMonotonicityChecks:86212,allOrderedCellArraysM1to3N1to5:67798,randomAllKCases:3500,literalUnionPartitionCases:444,literalUnionPartitionAssignments:65176,metamorphicChecks:40637,maximumOriginalCases:30,reentrantBatchCalls:20000,invalidCases:36,allocationFailuresInjected:14}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'8361293455850997735');
});
test('constructive balanced path exchanges preserve literal union costs on every small interval chain, with coordinate dilation checks',{timeout:310000},async()=>{
 const r=await check('../research/probes/diagonal-square-union-independent.py');
 for(const [key,value]of Object.entries({checks:14271756,strictIntervalChainsGrid1to9:23703,literalCellUnionPartitions:324065,constructiveTwoPathExchanges:969547,commonCutExchanges:301541,nestedEdgeExchanges:668006,apiCalls:110763,cellDilationCases:3000}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'17963117431430617432');
});
