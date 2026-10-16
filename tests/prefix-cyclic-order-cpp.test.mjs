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

test('concatenated prefix questions reconstruct all small secrets and respect maximum query budgets', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_unique_initial_prefix_cpp.py');
  assert.equal(result.checks, 10421309);
  assert.equal(result.smallCases, 118096);
  assert.equal(result.renamedCases, 104928);
  assert.equal(result.binaryCases, 1456);
  assert.equal(result.adaptiveNodes, 2684);
  assert.equal(result.adaptiveLeaves, 1456);
  assert.equal(result.adaptivePartitions, 2678);
  assert.equal(result.maximumCases, 33);
  assert.equal(result.queries, 2252418);
  assert.equal(result.queryCharacters, 297911871);
  assert.equal(result.checksum, '9247008998039105376');
  assert.equal(result.cppSha256, 'de1b771bf52638eec3e39270b39c84a0362e5485d89ffa19b86ac19e76496e28');
});

test('cyclic window comparisons agree with every consistent small permutation and reject impossible observations', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_cyclic_window_order_cpp.py');
  assert.equal(result.checks, 19024422);
  assert.equal(result.permutations, 362879);
  assert.equal(result.observationGroups, 215446);
  assert.equal(result.oracleQueries, 13368156);
  assert.equal(result.semanticVectors, 71992);
  assert.equal(result.impossibleVectors, 68872);
  assert.equal(result.randomInstances, 1500);
  assert.equal(result.maximumQueries, 1200000);
  assert.equal(result.maximumN, 200000);
  assert.equal(result.maximumJumpLevels, 18);
  assert.equal(result.checksum, '3615291826092893586');
  assert.equal(result.cppSha256, 'd8dfab3f30ed369b6ab511e5585c2ad80cec9c5f0a46518ebbfbbe49ab17b0c1');
});

test('cyclic window comparisons also match an independently constructed full near-neighbor closure and its reflection', { timeout: 310000 }, async () => {
  const result = await check('../research/probes/cyclic-window-order-independent.py');
  assert.equal(result.cases, 48);
  assert.equal(result.queries, 18555245);
  assert.equal(result.checksum, '13630968379293366250');
  assert.equal(result.cppSha256, 'd8dfab3f30ed369b6ab511e5585c2ad80cec9c5f0a46518ebbfbbe49ab17b0c1');
});
