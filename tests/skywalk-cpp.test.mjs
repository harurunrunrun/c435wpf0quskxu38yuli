import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const codeHash = '8623c4854f945e096e2b74d1f3fdcf0aa88da3543e9fe658b6ccec9d99595bd6';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, codeHash);
  return result;
}

test('published sparse skywalk graph matches every small intersection graph and seven original maximum constructions', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_skywalk_sparse_shortest_path_cpp.py');
  assert.equal(r.checks, 9280397);
  assert.equal(r.instances, 112287);
  assert.equal(r.exhaustiveInstances, 108279);
  assert.equal(r.exhaustiveTerminalPairs, 1716019);
  assert.equal(r.randomInstances, 4000);
  assert.equal(r.metamorphicChecks, 15440);
  assert.equal(r.invalidCalls, 24);
  assert.equal(r.maximumCases.length, 7);
  const detours = r.maximumCases.find(c => c.name === 'both short terminal detours');
  assert.equal(detours.vertices, 599994);
  assert.equal(detours.undirectedEdges, 1099978);
  assert.equal(r.maximumCases.find(c => c.name === 'alternating serial chain').distance, 99998999890004);
  assert.equal(r.maximumCases.find(c => c.name === 'disconnected halves').distance, -1);
  assert.equal(r.checksum, '9377741248886004889');
});

test('unit lattice edge BFS and geometric equivalences independently preserve every terminal distance', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/skywalk-shortest-path-independent.py');
  assert.equal(r.checks, 1750018);
  assert.equal(r.instances, 10624);
  assert(r.bfsQueries > 0);
  assert(r.heightInvarianceChecks > 0);
  assert(r.buildingInsertionChecks > 0);
  assert.equal(r.checksum, '17658587268103824764');
});
