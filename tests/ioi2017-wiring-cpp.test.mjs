import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const hash = '4ecea22560306bd2c60860ed143e3d374702d7fd255a03ba7972ac93f6f1ea76';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('linear bichromatic edge cover agrees with all small literal edge subsets, cover-mask DP, every prefix and maximum source inputs', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_line_bichromatic_edge_cover_cpp.py');
  assert.equal(r.checks, 579529);
  assert.equal(r.apiCalls, 147985);
  assert.equal(r.originalAdapterCalls, 37985);
  assert.equal(r.allTwoColorOrdersN2to12FourCoordinateProfiles, 32664);
  assert.equal(r.literalAllEdgeSubsetsN2to8, 35358064);
  assert.equal(r.independentExponentialOracleCalls, 59139);
  assert.equal(r.independentQuadraticCells, 106517092);
  assert.equal(r.everySmallCompletedPrefix, 24672);
  assert.equal(r.randomExactCoverCases, 1800);
  assert.equal(r.randomQuadraticCases, 3500);
  assert.equal(r.maximumCases, 10);
  assert.equal(r.reentrantBatchCalls, 20000);
  assert.equal(r.invalidCases, 17);
  assert.equal(r.checksum, '14068181790685886015');
});

test('weighted matching independently checks edge-cover optima and allocation failures in the const API and value-vector adapter', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/line-bichromatic-cover-independent.py');
  assert.equal(r.checks, 21885);
  assert.equal(r.weightedMatchingEdgeCoverInputs, 5672);
  assert.equal(r.hungarianVersusLiteralSubsetAssignmentSelfChecks, 4834);
  assert.equal(r.allocationFailureExceptions, 14);
  assert.equal(r.maxApiRequestedVectorBytes, 5000036);
  assert.equal(r.maxApiLiveVectorBytesAfterCall, 0);
  assert.equal(r.checksum, '9075146730217315746');
});
