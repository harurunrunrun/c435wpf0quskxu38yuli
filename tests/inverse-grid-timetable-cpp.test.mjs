import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
async function check(name) {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/' + name, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  return stdout;
}

test('one-error grid inversion matches direct predecessor enumeration and forward histories', { timeout: 310000 }, async () => {
  const stdout = await check('check_xor_grid_predecessor_cpp.py');
  assert.match(stdout, /checks=948236 arbitrary_patterns=74938 forward_cases=33505 candidate_assignments=13634516 histories=240/);
  assert.match(stdout, /max_dimensions=300x300 max_reverse_steps=149 checksum=11714764890392139543/);
});

test('timetable choices match every small policy and independent running world, including maximum-scale calls', { timeout: 310000 }, async () => {
  const result = JSON.parse(await check('check_stochastic_timetable_cpp.py'));
  assert.equal(result.checks, 62915);
  assert.equal(result.oracleCases, 19448);
  assert.equal(result.completePolicies, 112146);
  assert.equal(result.nonzeroWorldEvaluations, 512294);
  assert.equal(result.maximumTrips, 1000000);
  assert.equal(result.maximumStations, 1000000);
  assert(result.maximumAbsoluteError < 1e-10);
  assert.equal(result.checksum, '9809417411711479524');
});
