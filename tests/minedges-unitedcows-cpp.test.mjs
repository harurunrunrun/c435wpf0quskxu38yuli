import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const minimumHash = '1a04200fd167167a77a09ff5d98ca3a5354e6538025e2e36e41158636317693e';
const triplesHash = '407284b9682e4d15c74625be2294fe2234c79b8e7f6e4671366a8af92c4b6fcf';
async function check(relative, hash) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('minimum walk-preserving edges match the exact infinite languages and original maximum limits', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_parity_walk_minimum_cpp.py', minimumHash);
  assert.equal(r.checks, 292700);
  assert.equal(r.allConnectedLoopGraphsN2to5, 23940);
  assert.equal(r.completeInfiniteLanguageGroups, 932);
  assert.equal(r.rootRelabelingCases, 23940);
  assert.equal(r.independentDpComparisons, 25540);
  assert.equal(r.maximumN100000Cases, 7);
  assert.equal(r.maximumBatchCalls, 50000);
  assert.equal(r.invalidCalls, 14);
  assert.equal(r.checksum, '18056148866444260320');
});

test('all connected six-vertex graphs supply an independent true minimum for every complete walk language', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/parity-walk-minimum-independent.py', minimumHash);
  assert.equal(r.checks, 1717587);
  assert.equal(r.allConnectedLoopGraphsN6, 1709056);
  assert.equal(r.completeInfiniteLanguageGroups, 10263);
  assert.equal(r.extraNonzeroRootCases, 4265);
  assert.equal(r.reachableSetStatesProcessed, 14415046);
  assert.equal(r.checksum, '13145737057088314510');
});

test('unique endpoint and middle triples match literal interval frequencies, event invariants and maximum arrays', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_interval_unique_leaders_cpp.py', triplesHash);
  assert.equal(r.checks, 8876842);
  assert.equal(r.allFourLabelArrays, 349525);
  assert.equal(r.literalLeaderTriples, 35091758);
  assert.equal(r.invariantArrays, 87380);
  assert.equal(r.invariantSnapshots, 757304);
  assert.equal(r.invariantPoints, 2922420);
  assert.equal(r.primitiveSteps, 48000);
  assert.equal(r.maximumCases, 8);
  assert.equal(r.maximumN, 200000);
  assert.equal(r.checksum, '11233411103425697573');
});

test('all equality partitions through ten positions and disjoint-alphabet concatenations independently verify the triple count', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/interval-unique-leader-independent.py', triplesHash);
  assert.equal(r.checks, 144583);
  assert.equal(r.allEqualityPartitionsN0to10, 142418);
  assert.equal(r.allTriplesByNearestOccurrence, 15960528);
  assert.equal(r.disjointAlphabetConcatenations, 1008);
  assert.equal(r.maximumN200000Concatenations, 8);
  assert.equal(r.checksum, '5277007377993953808');
});
