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

test('oriented equal pairs match exact adjacent-swap BFS for every small balanced word', { timeout: 310000 }, async () => {
  const result = JSON.parse(await check('check_oriented_pair_swaps_cpp.py'));
  assert.equal(result.checks, 475661);
  assert.equal(result.bfsStates, 155850);
  assert.equal(result.bfsFamilies, 55);
  assert.equal(result.bfsDirectedEdges, 1059098);
  assert.equal(result.maximumElements, 200002);
  assert.equal(result.checksum, '1456229913660587723');
});

test('generated gates decide exact distance on actual two-pixel images within both source budgets', { timeout: 310000 }, async () => {
  const stdout = await check('check_two_mark_manhattan_circuit_cpp.py');
  assert.match(stdout, /checks=55810190 circuits=1858 scalar_images=297360 batch_images=8485484/);
  assert.match(stdout, /callback_gates=17078 max_gates=3190 max_terminals=86368 checksum=15915287276903946258/);
});

test('three requested sizes agree with literal partitions and induced connectivity on all small graphs', { timeout: 310000 }, async () => {
  const result = JSON.parse(await check('check_three_size_two_connected_cpp.py'));
  assert.equal(result.checks, 4278886);
  assert.equal(result.connectedGraphs, 27474);
  assert.equal(result.sortedSizeCases, 81610);
  assert.equal(result.orderedSizeCases, 271526);
  assert.equal(result.literalPartitions, 16208532);
  assert.equal(result.stackLimitBytes, 1048576);
  assert.equal(result.checksum, '17105848895082083793');
});
