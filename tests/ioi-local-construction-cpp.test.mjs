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

test('published median ticket allocation agrees with original choices and actual round medians', { timeout: 310000 }, async () => {
  const stdout = await check('check_median_ticket_allocation_cpp.py');
  assert.match(stdout, /20445406 checks passed; 6244 exhaustive matrices\/K; 1195179 original allocations/);
  assert.match(stdout, /checksum 3972146740598713967/);
});

test('published tree labels route correctly even when the router is compiled without its labeler', { timeout: 310000 }, async () => {
  const result = JSON.parse(await check('check_tree_local_routing_cpp.py'));
  assert.equal(result.checks, 54792748);
  assert.equal(result.isolatedRouterChecks, 71696);
  assert.equal(result.routerCompiledWithoutLabeler, true);
  assert.equal(String(result.checksum), '10724171460026289549');
});

test('published path count construction agrees with direct enumeration of graphs and matrices', { timeout: 310000 }, async () => {
  const stdout = await check('check_simple_path_count_graph_cpp.py');
  assert.match(stdout, /checks=52708028 all_graphs=33867 all_symmetric_matrices=1052741/);
  assert.match(stdout, /returned_graph_rechecks=9393 three_path_graphs=6886/);
});
