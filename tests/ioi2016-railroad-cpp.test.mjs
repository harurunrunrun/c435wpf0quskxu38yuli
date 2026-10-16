import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='0f96903e638b431fec50f4261e87e6b30738a0a5ccb741757fbd2a90baae9529';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('line-section connection equals literal physical permutations and independent Held-Karp, with all original boundaries and allocation faults',{timeout:310000},async()=>{
 const r=await check('../scripts/check_line_section_connection_cpp.py');
 for(const [key,value]of Object.entries({checks:67533397,apiCalls:93460,originalAdapterCalls:76252,allArraysN2to5Speeds1to3:66420,allArraysN2to6Speeds1to2:5456,literalPhysicalPermutations:11911144,heldKarpCases:5816,heldKarpRelaxations:167264334,randomHeldKarpCases:360,metamorphicCases:1208,maximumN200000Cases:21,invalidCases:30,allocationFailuresInjected:22,reentrantBatchCalls:20000,maximumCoreVectorPayloadBytes:8000012,maximumAdapterAdditionalPayloadBytes:11200012}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'10479858278086570783');
});
test('independently enumerated degree-feasible connected flows produce Euler circuits and real accepted-speed orderings at the same optimum',{timeout:310000},async()=>{
 const r=await check('../research/probes/line-section-connection-independent.py');
 for(const [key,value]of Object.entries({checks:2752841,apiCalls:67084,allThreeSpeedMultisetsN2to7:11430,allFourSpeedMultisetsN2to4:4828,randomFourSpeedMultisetsN5to10:512,connectorCountSearchStates:14475224,balancedConnectorConfigurations:1250748,connectedBalancedConfigurations:1249599,constructedEulerWitnesses:67084,constructedEulerEdges:697962,restoredPhysicalSections:376580}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'16174261861575450891');
});
