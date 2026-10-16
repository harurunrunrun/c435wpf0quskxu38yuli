import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  return JSON.parse(stdout);
}

test('published alternating circuits reproduce every small sequence and restore every switch on the first origin return', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_alternating_trigger_circuit_cpp.py');
  assert.equal(result.checks, 117243125);
  assert.equal(result.smallCases, 97738);
  assert.equal(result.binaryExtra, 130560);
  assert.equal(result.singleLengths, 2048);
  assert.equal(result.allLengthBudgets, 200000);
  assert.equal(result.periods, 461464);
  assert.equal(result.maximumN, 200000);
  assert.equal(result.maximumM, 100000);
  assert.equal(result.maximumSwitches, 200012);
  assert.equal(result.maximumChanges, 3836286);
  assert.equal(result.invalidBuilderCalls, 12);
  assert.equal(result.checksum, '17302177393877592427');
  assert.equal(result.cppSha256, 'ec7888a3cf046dd5d72d48429c83b1113d401c82558d0e36899cb1591be7a973');
});

test('published hidden-pair questions match actual Dijkstra replies on every small graph and achieve the tight fifty-call boundary', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_binary_weight_hidden_pair_cpp.py');
  assert.equal(result.checks, 178526522);
  assert.equal(result.allConnectedSimpleGraphs, 27475);
  assert.equal(result.allPairsTimesFiveTolls, 2040405);
  assert.equal(result.oracleQueries, 12899409);
  assert.equal(result.randomCases, 3000);
  assert.equal(result.maximumCases, 6);
  assert.equal(result.maximumN, 90000);
  assert.equal(result.maximumM, 130000);
  assert.equal(result.largestQueryCount, 50);
  assert.equal(result.largestReply, 89998999955001);
  assert.equal(result.checksum, '13151808493442697981');
  assert.equal(result.cppSha256, 'b7e618bcd9befb83f25499a950bde4c6feed4c0be5340bbbaa81f031731d9715');
});

test('an independent spatial recurrence verifies every legal length and rejects pruning in time order', { timeout: 310000 }, async () => {
  const result = await check('../research/probes/alternating-switch-structure.py');
  assert.equal(result.allNSpatialStructureCases, 200000);
  assert.deepEqual(result.maxS, { value: 200012, firstN: 200000 });
  assert.deepEqual(result.maxT, { value: 3836286, firstN: 200000 });
  assert.deepEqual(result.negativeControls.wrongTimePrefixPruningN4,
    { switches: 7, fullScoreIntegerBound: 6, correctSpatialPruningSwitches: 6 });
  assert.equal(result.checksum, '9839057549024960597');
});
