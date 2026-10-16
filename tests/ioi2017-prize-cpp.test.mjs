import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='af538cebe18119d7f93b645d56ee74ff3432d7225dcffe630f4d5bcff6a1947b';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:2*1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('rank-count search finds the best in every surviving completion and keeps the4779 worst-case bound throughout the original source domain',{timeout:310000},async()=>{
 const r=await check('../scripts/check_rank_count_prize_cpp.py');assert.equal(r.officialHeaderBytesRetrieved,false);
 const c=r.genericStandaloneFull;
 for(const [key,value]of Object.entries({checks:9804568,apiCalls:26286,allLegalArraysN3to16:23807,adaptiveCompletionRuns:36,allAdaptiveTreeNodesN3to12:1976,allAdaptiveTreeLeavesN3to12:939,allFeasibleAdaptiveResponseBranchesN3to12:1966,largeAdaptiveCompletionRuns:3,allMarkedPatternsN1to18:524286,legalCountChains:13098,maximumNonCheapest:472,maximumNonCheapestReplySum:26,maximumQueriesObserved:4112,invalidCases:16}))assert.equal(c[key],value,key);
 assert.equal(c.checksum,'12118485734290438769');assert.equal(c.maximumCases.length,106);
 assert.equal(r.syntheticHeaderOriginalAdapterSmoke.checks,285071);assert.equal(r.syntheticHeaderOriginalAdapterSmoke.apiCalls,370);assert.equal(r.syntheticHeaderOriginalAdapterSmoke.checksum,'12874631007238081852');
});
test('independent legal-completion adversaries, every capacity-feasible small recurrence split and allocation/callback faults preserve rank-count search',{timeout:310000},async()=>{
 const r=await check('../research/probes/rank-count-prize-independent.py'),c=r.result;
 for(const [key,value]of Object.entries({checks:44386,apiCalls:3984,adaptiveRuns:12,initialLegalCompletionOccurrences:75825,candidateReplyComparisons:6216314,maximumAdaptiveQueries:555,allocationFaults:2,callbackFaults:3967,exactRecurrenceLengths:255,exactRecurrenceStates:32640}))assert.equal(c[key],value,key);
 assert.equal(c.checksum,'10991112477329892348');
});
