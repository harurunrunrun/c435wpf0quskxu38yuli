import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const countHash = 'd454db3070931a3ffad8c7f78373c4f1a000d3ab5a77e1c3b368f48fb5b77b9d';
const convexHash = '21132d1dd677f87110e24ea1563245b380b3ec18de594b636067b9d888e660c6';
async function check(relative, hash) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('walk-preserving graph counts match every complete language class and literal edge-selection primitives', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_parity_walk_graph_count_cpp.py', countHash);
  assert.equal(r.checks, 457134);
  assert.equal(r.apiCalls, 151370);
  assert.equal(r.allConnectedLoopGraphsN2to5, 23940);
  assert.equal(r.languageGroupsN2to5, 932);
  assert.equal(r.allConnectedLoopGraphsN6, 1709056);
  assert.equal(r.languageGroupsN6, 10263);
  assert.equal(r.literalBipartiteMatrices, 74963);
  assert.equal(r.literalTerminalLoopGraphs, 2131019);
  assert.equal(r.maximumN100Calls, 119);
  assert.equal(r.maximumBatchCalls, 25000);
  assert.equal(r.invalidCalls, 20);
  assert.equal(r.checksum, '14785516314595030999');
});

test('exact edge-clause Shannon counting independently verifies complete walk languages beyond six vertices', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/parity-walk-count-independent.py', countHash);
  assert.equal(r.checks, 527754);
  assert.equal(r.instances, 35182);
  assert.equal(r.apiCalls, 492548);
  assert.equal(r.oracleCrosschecks, 12);
  assert.equal(r.oracleGraphAssignments, 266240);
  assert.equal(r.maximumExactRealizations, '35184372088832');
  assert.equal(r.checksum, '14715201252465104520');
});

test('convex connected subsets match every small grass board, literal cell subsets and original maximum grids', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_row_column_convex_subsets_cpp.py', convexHash);
  assert.equal(r.checks, 83403);
  assert.equal(r.allSmallGrassBoards, 74954);
  assert.equal(r.literalNonemptyShapes, 74938);
  assert.equal(r.literalEnumeratedSubsetCandidates, 909914);
  assert.equal(r.directTransitionBoards, 240);
  assert.equal(r.metamorphicChecks, 5400);
  assert.equal(r.invalidCalls, 10);
  assert.equal(r.maximumCases.length, 10);
  assert.equal(r.maximumCases.find(c => c.name === 'all grass').count, 498249215);
  assert.equal(r.checksum, '5989455240367906907');
});

test('direct column lifetimes and blocked separators independently verify convex subsets without endpoint phases', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/row-column-convex-subsets-independent.py', convexHash);
  assert.equal(r.checks, 99248);
  assert.equal(r.boards, 33230);
  assert.equal(r.all5x3Boards, 32768);
  assert.equal(r.literal5x3Shapes, 32767);
  assert.equal(r.maximumTallPatterns, 42);
  assert.equal(r.randomNarrowBoards, 420);
  assert.equal(r.maximumSeparatorChecks, 20);
  assert.equal(r.checksum, '16617549809945668858');
});
