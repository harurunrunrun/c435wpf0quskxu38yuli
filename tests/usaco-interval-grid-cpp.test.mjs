import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
test('published interval XOR triples implementation agrees with enumeration and independent digit DP', { timeout: 250000 }, async () => {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/check_xor_bounded_triples_cpp.py', import.meta.url))],
    { timeout: 240000, maxBuffer: 1024 * 1024 });
  assert.match(stdout, /126072 checks passed/);
});

test('published grid rectangle implementation agrees with rectangle-local BFS', { timeout: 330000 }, async () => {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/check_grid_rectangle_components_cpp.py', import.meta.url))],
    { timeout: 320000, maxBuffer: 1024 * 1024 });
  const report = JSON.parse(stdout);
  assert.equal(report.checkedQueries, 8488341);
  assert.equal(report.binaryGrids, 74954);
  assert.equal(report.ternaryGrids, 21297);
  assert.equal(report.fourColorGrids, 8612);
  assert.equal(report.randomGrids, 2500);
  assert.equal(report.stressGrids, 8);
  assert.equal(report.invalidCases, 30);
});
