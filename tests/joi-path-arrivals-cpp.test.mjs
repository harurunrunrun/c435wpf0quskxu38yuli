import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
test('published skyline and ancestor path selection agrees with rectangle and vertex-set enumeration', { timeout: 310000 }, async () => {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/check_skyline_path_packing_cpp.py', import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  assert.match(stdout, /checks=57582 exhaustive_boards=288 all_star_subsets=50978/);
  assert.match(stdout, /all_weighted_small_images=2214 exhaustive_trees=10/);
});

test('published timed arrivals and circular harvest agree with independent physical events and individual walks', { timeout: 310000 }, async () => {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/check_timed_graph_arrivals_cpp.py', import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.checks, 26409576);
  assert.equal(result.graphCases, 21504);
  assert.equal(result.circleCases, 152225);
  assert.equal(result.randomCases, 2500);
  assert.equal(result.invalidCases, 60);
  assert.equal(result.checksum, '11764706113351154515');
});
