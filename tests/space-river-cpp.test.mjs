import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const hash = '533fe3f5288d25bf6bb4676d6b2a7d90b01fa1cef7cdb70d08d08f57e2977e72';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('sparse word-space DP and event widths agree with literal grids, all small widths and independent full-width maximum scans', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_word_wrap_space_river_cpp.py');
  assert.equal(r.checks, 4382429);
  assert.equal(r.apiCalls, 545801);
  assert.equal(r.exhaustiveLengthInputs, 21844);
  assert.equal(r.literalIntegerWidths, 521155);
  assert.equal(r.literalGridCells, 94307189);
  assert.equal(r.nextChangeChecks, 521106);
  assert.equal(r.literalPathCalls, 44895);
  assert.equal(r.randomInputs, 450);
  assert.equal(r.metamorphicChecks, 1212);
  assert.equal(r.invalidCases, 23);
  assert.equal(r.fullWidthOracleIntegerWidths, 262088);
  assert.equal(r.fullWidthOracleSpaceUpdates, 641826740);
  assert.equal(r.maximumCases.length, 7);
  assert.equal(r.checksum, '14932699637744859611');
});

test('all line partitions and boolean reachability independently verify greedy rows, next layout, minimum-width ties and extreme widths', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/word-wrap-space-river-independent.py');
  assert.equal(r.inputCases, 3660);
  assert.equal(r.allLegalOrderedLinePartitionsExamined, 302345);
  assert.equal(r.fixedWidthsComparedIncludingTwoPastOneLine, 205199);
  assert.equal(r.minimumRowCountAcrossAllFeasiblePartitionsChecks, 205199);
  assert.equal(r.additionalIntExtremeWidthComparisons, 7320);
  assert.equal(r.casesWithTiedOptimalWidths, 3632);
  assert.equal(r.emptyRowEvaluations, 93200);
  assert.equal(r.apiMemoryAndWriter.memoryWriterAssertions, 13);
  assert.equal(r.apiMemoryAndWriter.maxNIntMaxWidthPeakRequestedAllocationBytes, 40000);
  assert.equal(r.apiMemoryAndWriter.liveRequestedBytesAfterCall, 0);
  assert.equal(r.checksum, '3236069206071420278');
});
