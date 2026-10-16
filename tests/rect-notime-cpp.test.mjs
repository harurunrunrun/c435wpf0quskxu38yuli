import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const paintHash = 'e04fe2fe44a59765e06690d592aab60cdcedeb817dca165bc62b1194d31b767c';
const rectangleHash = '69a053a27c5d26d392eda313d2cfded6fbaa150c4f4ad959850e05cb914dd5d2';
async function check(relative, hash) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('published paint strokes agree with every small brush-action BFS and the full original limits', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_monotone_paint_range_cpp.py', paintHash);
  assert.equal(r.checks, 2702609);
  assert.equal(r.literalPaintingBFSStates, 87380);
  assert.equal(r.literalPaintingBFSActions, 4817386);
  assert.equal(r.allThreeColorArrays, 9840);
  assert.equal(r.allSubintervalsIncludingEmpty, 401040);
  assert.equal(r.randomCases, 1800);
  assert.equal(r.randomQueries, 540000);
  assert.equal(r.maximumN, 200000);
  assert.equal(r.maximumQ, 200000);
  assert.equal(r.maximumQueries, 1200000);
  assert.equal(r.checksum, '1028313103656390273');
});

test('an independent four-color BFS leaves every outside cell explicitly unpainted, including empty queries', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/monotone-paint-range-four-color-bfs.py', paintHash);
  assert.equal(r.checks, 551710);
  assert.equal(r.fiveStateBfsConfigurations, 19531);
  assert.equal(r.legalBrushActions, 799398);
  assert.equal(r.fourColorArraysIncludingEmpty, 5461);
  assert.equal(r.fullBoardBlankOutsideQueries, 140781);
  assert.equal(r.emptyQueriesIncludingMaximumBatches, 436409);
  assert.equal(r.maximumN, 200000);
  assert.equal(r.maximumQ, 200000);
  assert.equal(r.checksum, '15760702932218361702');
});

test('published rectangle candidates match literal four-boundary inequalities and 2500-by-2500 cases', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_enclosed_rectangle_candidates_cpp.py', rectangleHash);
  assert.equal(r.checks, 2884927);
  assert.equal(r.binaryGrids, 74954);
  assert.equal(r.ternaryGrids, 1082565);
  assert.equal(r.literalRectangles, 5096743);
  assert.equal(r.randomGrids, 1000);
  assert.equal(r.maximumCases, 7);
  assert.equal(r.maximumRows, 2500);
  assert.equal(r.maximumColumns, 2500);
  assert.equal(r.maximumHeight, 7000000);
  assert.equal(r.invalidCalls, 11);
  assert.equal(r.checksum, '16899164946917607117');
});

test('an independent interval-maximum and violation-prefix oracle exercises all maximum witnesses and rejects spurious candidates', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/higher-boundary-rectangle-independent.py', rectangleHash);
  assert.equal(r.checks, 2444422);
  assert.equal(r.cases, 394563);
  assert.equal(r.distinct3x3Permutations, 362880);
  assert.equal(r.ternary5x5FramedInteriors, 19683);
  assert.equal(r.randomGrids, 12000);
  assert.equal(r.rectangles, 190182034);
  assert.equal(r.validRectangles, 438720);
  assert.equal(r.allMaximumWitnesses, 822011);
  assert.equal(r.duplicateCandidateEmissions, 508047);
  assert.equal(r.spuriousCandidates, 561845);
  assert.equal(r.checksum, '13428659320025481575');
});
