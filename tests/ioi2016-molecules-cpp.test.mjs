import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='af88cbae982b487fc8b3055c91139f50b558f5f4a28a11076c993fa3b2fbf106';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('bounded-spread subset witnesses match every small ordered array and valid range, with original indices, both API editions and maximum integer cases',{timeout:310000},async()=>{
 const r=await check('../scripts/check_bounded_spread_subset_cpp.py');
 for(const [key,value]of Object.entries({checks:34096437,apiCalls:3129167,orderedWeightArrays:21844,literalSubsetAssignments:13228154,allValidSmallRangeCases:3088644,adapterCalls:36074,randomInputs:1200,metamorphicChecks:3200,invalidCalls:25}))assert.equal(r[key],value,key);
 assert.equal(r.maximumCases.length,8);assert.equal(r.checksum,'2569540640142451667');
});
test('independent cardinality-polynomial coefficients justify the window reduction, including large offsets, missing-width counterexamples and allocation faults',{timeout:310000},async()=>{
 const r=await check('../research/probes/bounded-spread-subset-independent.py');
 for(const [key,value]of Object.entries({checks:19763636,apiCalls:925746,sortedMultisetsWeights1to8Length1to9:24309,cardinalityMinimalWidthRangeComparisons:7565272,minimumWidthApiCases:923778,largeOffsetFixedCardinalityCases:1683,reverseIndexCases:250,allocationFailureExceptions:16,widthViolationCounterexamples:4}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'15452486297988215716');
});
