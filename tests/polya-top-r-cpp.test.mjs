import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const hash = 'ba1d3404002c8dac230479a6cecc63bf559fd5135ca50c6ef95c945f0f8e5d51';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('unit-reinforcement top-r DP agrees with all small compositions, exact owner-history probabilities and full-range integer oracles', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_unit_polya_top_sum_cpp.py');
  assert.equal(r.checks, 2292379);
  assert.equal(r.apiCalls, 759821);
  assert.equal(r.compositionParameterPairs, 104);
  assert.equal(r.allWeakCompositions, 203489);
  assert.equal(r.historyParameterPairs, 50);
  assert.equal(r.ownerHistories, 2821488);
  assert.equal(r.historyTerminalStates, 3002);
  assert.equal(r.exactTailOracleCalls, 3653);
  assert.equal(r.exactTailIntegerTerms, 105439);
  assert.equal(r.randomRankQueries, 2834);
  assert.equal(r.metamorphicChecks, 5488);
  assert.equal(r.boundaryApiCalls, 753001);
  assert.equal(r.invalidCases, 16);
  assert.equal(r.maximumCases.length, 13);
  assert(r.maximumAbsoluteError < 1e-6);
  assert.equal(r.checksum, '7563957929397653268');
});

test('weighted integer partitions independently check top-r values, requested memory, stream behavior and the numerical bound', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/unit-polya-top-sum-independent.py');
  assert.equal(r.integerPartitions, 62497);
  assert.equal(r.parameterPairs, 200);
  assert.equal(r.expectedValueComparisons, 1085);
  assert.equal(r.additionalPositiveMinimumTailCases, 60);
  assert(r.maximumExactRationalError < 1e-6);
  assert.equal(r.apiMemoryAndWriter.memoryWriterChecks, 13);
  assert.equal(r.apiMemoryAndWriter.apiOnlyPeakRequestedAllocationBytes, 6016008);
  assert.equal(r.apiMemoryAndWriter.liveRequestedBytesAfterCall, 0);
  assert(Number(r.decimalErrorBoundRecalculation.absoluteWithSerializationUpper) < 1e-6);
  assert.equal(r.checksum, '9209358677489316410');
});
