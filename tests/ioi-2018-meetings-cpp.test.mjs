import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const codeHash = '7241cb7bc2c5a4f6786a342a8a78592f0ba37097f2b01894afc4790c5263f1b1';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, codeHash);
  return result;
}

test('published meeting costs match literal all-venue oracles, each orientation, and the full original input limits', { timeout: 310000 }, async () => {
  const result = await check('../scripts/check_cartesian_meeting_cost_cpp.py');
  assert.equal(result.checks, 10223222);
  assert.equal(result.smallArrays, 51367);
  assert.equal(result.smallQueries, 1766247);
  assert.equal(result.orientedQueries, 1288632);
  assert.equal(result.randomArrays, 500);
  assert.equal(result.randomQueries, 100000);
  assert.equal(result.maximumCases, 7);
  assert.equal(result.maximumQueries, 5250000);
  assert.equal(result.maximumCost, 750000000000000);
  assert.equal(result.invalidCalls, 15);
  assert.equal(result.checksum, '14312679095217143898');
});

test('affine heights, reflection, outside padding and subarray isolation preserve the expected meeting costs', { timeout: 310000 }, async () => {
  const result = await check('../research/probes/cartesian-meeting-cost-metamorphic.py');
  assert.equal(result.status, 'passed');
  assert.equal(result.checks, 1255051);
  assert.equal(result.cases, 6513);
  assert.equal(result.literalQueries, 167685);
  assert.equal(result.affineQueries, 339523);
  assert.equal(result.reflectionQueries, 339523);
  assert.equal(result.outsidePaddingQueries, 339523);
  assert.equal(result.subarrayIsolationQueries, 55770);
  assert.equal(result.checksum, '14795718582425382993');
});

test('full-length intervals with arbitrary heights agree with an independent all-sites monotone-stack oracle', { timeout: 310000 }, async () => {
  const result = await check('../research/probes/cartesian-meeting-cost-large.py');
  assert.equal(result.status, 'passed');
  assert.equal(result.checks, 15038);
  assert.equal(result.smallLiteralCrosschecks, 14846);
  assert.equal(result.maximumN, 750000);
  assert.equal(result.largeCases, 3);
  assert.equal(result.largeQueries, 192);
  assert.equal(result.checksum, '8452447248660873667');
});
