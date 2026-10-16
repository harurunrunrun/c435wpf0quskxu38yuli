import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
async function check(script) {
  return (await run('python3', [fileURLToPath(new URL('../scripts/' + script, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 })).stdout;
}

test('equal-bag values match every physical allocation and support the original 1000-call bounds', { timeout: 310000 }, async () => {
  const result = JSON.parse(await check('check_equal_bag_values_cpp.py'));
  assert.equal(result.checks, 139189);
  assert.equal(result.exhaustiveCases, 1456);
  assert.equal(result.physicalAllocations, 37626900);
  assert.equal(result.provedStateBound, 2016);
  assert.equal(result.checksum, '247190460644545666');
});

test('two-source mixture matches direct finite flow assignments, all cuts and maximum-size reconstruction', { timeout: 310000 }, async () => {
  const stdout = await check('check_two_source_mixture_cpp.py');
  assert.match(stdout, /checks=830234 all_small_graphs=756 finite_edge_assignments=91138194 valid_assignments=79242/);
  assert.match(stdout, /constructions=3523 checksum=5985807862651685642/);
});
