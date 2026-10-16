import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile),hash='3a6f404db20af159ce47c67688ee05f93586a6833da3d6fce24a38bb3f41cad4';
async function check(relative){
 const {stdout}=await run('python3',[fileURLToPath(new URL(relative,import.meta.url))],{timeout:300000,maxBuffer:1024*1024});
 const r=JSON.parse(stdout);assert.equal(r.cppSha256,hash);return r;
}
test('path shortcut minimum matches every endpoint Floyd graph and exact four-bound/discrete-box checks at source maximum',{timeout:310000},async()=>{
 const r=await check('../scripts/check_path_shortcut_diameter_cpp.py');
 for(const [key,value]of Object.entries({checks:8752494,preparedInputs:10836,preparedMinimumCalls:10843,genericFunctionCalls:16022,originalAdapterCalls:10826,explicitPredicateCalls:100861,allSmallN2to5:9324,allBinaryBranchPathsN2to6:372,randomAllEndpointFloydCases:1120,literalAugmentedGraphs:152165,floydRelaxations:556286427,fourBoundaryEquivalences:7009273,decisionThresholds:100819,arbitraryDiscreteBoxes:233415,literalStationPairsForBoxes:982800,invalidCases:30,allocationFailuresInjected:28,stateChecks:10023,maximumPreparedPayloadBytes:56000000}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'11498457106931259831');assert.equal(r.maximumCases.length,14);assert(r.maximumCases.every(c=>c.n===1000000));
});
test('literal unit-edge BFS on original stations agrees with every threshold, branch translation, extreme two-station and irregular-box cases',{timeout:310000},async()=>{
 const r=await check('../research/probes/path-shortcut-diameter-independent.py');
 for(const [key,value]of Object.entries({checks:8644858,apiCalls:136388,allSmallN2to4:9344,randomPhysicalCases:480,unitExpandedShortcutGraphs:82277,originalStationBfsRuns:828659,bfsVertexVisits:25506853,bfsArcScans:50843762,allThresholdComparisons:99922,literalBranchTranslations:886,literalTripleScales:706,extremeTwoStationCases:900,extremeDiscreteBoxes:20000,literalBoxStationPairs:1399803,millionStationBranchTranslations:1}))assert.equal(r[key],value,key);
 assert.equal(r.checksum,'17492186508820992233');
});
