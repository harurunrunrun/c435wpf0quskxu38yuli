import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
const run = promisify(execFile);
const hash = '320921a0131689953b2ebd74a0bc81a6abe9073fd506576a4c18cb1909af7bd6';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))], { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}
test('single-held-book linear walk agrees with full physical states, every small permutation and independent exponential oracles', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_permutation_single_book_walk_cpp.py');
  for (const [key, value] of Object.entries({checks:5166352,apiCalls:430576,originalAdapterCalls:371400,allPermutationsAndStartsN1to8:362879,physicalInputsN1to7:40319,physicalShelfHeldPositionStates:2177282,cycleSubsetOracleCalls:368879,exhaustiveIntervalOracleCalls:8500,maximumN1millionCases:14,invalidCases:16,reentrantBatchCalls:20000})) assert.equal(r[key], value, key);
  assert.equal(r.checksum, '11819723664200185900');
});
test('directed arborescence independently verifies walk costs, stretched million-position cases, scan bounds and allocation failures', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/single-book-sort-walk-independent.py');
  for (const [key, value] of Object.entries({checks:1761612,smallPermutationStarts:40319,bruteIncomingTreeCases:719,bruteIncomingAssignments:65769,randomArborescenceCases:1500,metamorphicChecks:4500,millionScaleCases:19,allocationFailuresInjected:24,instrumentedCalls:46338,maxScannedPlusPaid:1999997})) assert.equal(r[key], value, key);
  assert.equal(r.checksum, '10441972892649583544');
});
