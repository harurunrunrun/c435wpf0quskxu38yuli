import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

test('published quadratic grid profile agrees with direct path DP and independent boundary formulas', { timeout: 330000 }, async () => {
  const { stdout } = await promisify(execFile)('python3', [fileURLToPath(new URL('../scripts/check_quadratic_grid_profile_cpp.py', import.meta.url))],
    { timeout: 320000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.checks, 21926323);
  assert.equal(result.exhaustiveGrids, 391902);
  assert.equal(result.randomGrids, 1800);
  assert.equal(result.invalidCases, 44);
  assert.equal(result.checksum, '2479293403635762744');
});
