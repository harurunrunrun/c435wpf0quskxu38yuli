import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

const run = promisify(execFile);
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  return JSON.parse(stdout);
}

test('published grid updates match every small arrangement and swap and all source maximum shapes', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_prefix_rectangle_grid_cpp.py');
  assert.equal(result.checks, 16930653);
  assert.equal(result.exhaustivePermutations, 174569);
  assert.equal(result.exhaustiveSwapPairs, 4773592);
  assert.equal(result.bitmaps, 74938);
  assert.equal(result.randomInstances, 400);
  assert.equal(result.randomSwaps, 240000);
  assert.equal(result.maximumSwaps, 250000);
  assert.equal(result.maximumCells, 1000000);
  assert.equal(result.maximumHeight, 1000000);
  assert.equal(result.maximumWidth, 1000000);
  assert.equal(result.checksum, '3501807229918974063');
  assert.equal(result.cppSha256, '53bfff9aa968b7b8876aa153a0b5315984a269063f065511168ced62d0ce0b89');
});

test('published threshold intersections agree with direct two-form BFS on every small graph and query', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_threshold_component_intersection_cpp.py');
  assert.equal(result.checks, 33949663);
  assert.equal(result.sourceGraphs, 27475);
  assert.equal(result.sourceQueries, 8527158);
  assert.equal(result.allSmallQueries, 10048867);
  assert.equal(result.randomGraphs, 300);
  assert.equal(result.maximumCases, 5);
  assert.equal(result.maximumQueries, 1000000);
  assert.equal(result.invalidCases, 62);
  assert.equal(result.checksum, '16549868984224916885');
  assert.equal(result.cppSha256, 'dd1013768b7f8549b0afb09680850b0c46bc92993533156a2c05d520955b3974');
});

test('grid updates preserve source and target through allocation failures and allocate nothing during valid swaps', { timeout: 310000 }, async () => {
  const result = await check('../research/probes/grid-prefix-rectangle-api.py');
  assert.equal(result.copyAllocationFailures, 5);
  assert.equal(result.assignmentAllocationFailures, 5);
  assert.equal(result.noAllocationValidSwaps, 30000);
  assert.equal(result.noAllocationGetters, 10000);
  assert.equal(result.cppSha256, '53bfff9aa968b7b8876aa153a0b5315984a269063f065511168ced62d0ce0b89');
});

test('the independent corner criterion matches every nonempty 5 by 5 bitmap and all local interval identities', { timeout: 310000 }, async () => {
  const temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-grid-corner-proof-'));
  try {
    const binary = path.join(temporary, 'corners');
    await run('g++', ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
      fileURLToPath(new URL('../research/probes/grid-prefix-rectangle-corners.cpp', import.meta.url)),
      '-o', binary], { timeout: 120000 });
    const { stdout } = await run(binary, [], { timeout: 120000 });
    const result = JSON.parse(stdout);
    assert.equal(result.allNonempty5x5Subsets, 33554431);
    assert.equal(result.literalRectangles, 225);
    assert.equal(result.prefixIntervalChecks, 912730);
    assert.equal(result.counterexamples, 0);
    // The raw C++ JSON number exceeds JS's exact integer range; compare bytes.
    assert.match(stdout, /"checksum":7828622978098135040/);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
