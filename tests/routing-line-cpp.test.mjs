import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const routingHash = 'e7413df680357afece2e8915990aca0c38862693e84a290906460dc69a8ee561';
const lineHash = '4d35c149f77752aef1909e46250606366916a243951891ac2fa2c4244a16445b';
async function check(relative, hash) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('edge routing counts match literal local bijections and complete source trails for all small legal roles', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_almost_dag_routing_cpp.py', routingHash);
  assert.equal(r.checks, 8888553);
  assert.equal(r.apiCalls, 2955941);
  assert.equal(r.allSmallGraphs, 58812);
  assert.equal(r.balancedSmallCases, 9288);
  assert.equal(r.literalLocalPairings, 86720);
  assert.equal(r.validLiteralPairings, 46563);
  assert.equal(r.literalTrailRecursions, 296988);
  assert.equal(r.literalTrailSchemes, 46563);
  assert.equal(r.unbalancedRoleCalls, 2883600);
  assert.equal(r.randomCases, 1000);
  assert.equal(r.maximumCalls, 84);
  assert.equal(r.originalBatchCalls, 22);
  assert.equal(r.invalidCalls, 18);
  assert.equal(r.checksum, '12131375425186710056');
});

test('independent graph and trail bijections preserve routing counts up to one hundred vertices', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/almost-dag-routing-independent.py', routingHash);
  assert.equal(r.checks, 5880);
  assert.equal(r.baseInstances, 120);
  assert.equal(r.apiCalls, 2784);
  assert.equal(r.subdivisionChecks, 864);
  assert.equal(r.trailReversalChecks, 480);
  assert.equal(r.withinLayerRelabelChecks, 480);
  assert.equal(r.maximumN100PaddingChecks, 480);
  assert.equal(r.independentDagClosedFormChecks, 96);
  assert.equal(r.checksum, '10593336235733119677');
});

test('orthogonal cover passes every rank permutation through nine points and generated maximum geometries', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_orthogonal_point_cover_cpp.py', lineHash);
  assert.equal(r.checks, 28709275);
  assert.equal(r.rankPermutations, 409113);
  assert.equal(r.literalPointSegmentTests, 72632802);
  assert.equal(r.randomCases, 6000);
  assert.equal(r.metamorphicChecks, 6000);
  assert.equal(r.invalidCalls, 14);
  assert.equal(r.maximumCases.length, 15);
  for (const item of r.maximumCases) {
    assert(item.segments <= item.n + 3);
    assert(item.outputBytes <= 2200073);
  }
  assert.equal(r.originalContestInputFilesTested, 0);
  assert.equal(r.checksum, '16725969703083196');
});

test('support-coordinate dictionaries and independent monotone warps verify point coverage and segment signatures', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/orthogonal-point-cover-independent.py', lineHash);
  assert.equal(r.checks, 13310052);
  assert.equal(r.baseRankPatterns, 402);
  assert.equal(r.directCoverCalls, 1608);
  assert.equal(r.writerCalls, 6);
  assert.equal(r.totalCoverConstructions, 1614);
  assert.equal(r.strictCoordinateWarpSignatures, 1206);
  assert.equal(r.maximumN100000DirectCoverCalls, 24);
  assert.equal(r.maximumN100000WriterCalls, 6);
  assert.equal(r.originalContestInputFilesTested, 0);
  assert.equal(r.checksum, '2898367367102235497');
});
