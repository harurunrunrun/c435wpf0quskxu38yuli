import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const hash = '361a44b414edbe2654d5d86b3c997ca0dd355565d1daf3cd3548c626c1f87029';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('degree-preserving reconstruction reaches literal all-tree optima for all small desired vectors and connected multigraphs', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_tree_degree_preservation_cpp.py');
  assert.equal(r.checks, 4721765);
  assert.equal(r.apiCalls, 263049);
  assert.equal(r.completeGraphEdgeSubsets, 57501);
  assert.equal(r.labeledTrees, 18248);
  assert.equal(r.degreeVectors, 142073);
  assert.equal(r.literalTreeVectorComparisons, 24486515);
  assert.equal(r.connectedMultigraphs, 59139);
  assert.equal(r.randomCases, 2000);
  assert.equal(r.fullDegreeAssignmentDPStates, 22546158);
  assert.equal(r.metamorphicChecks, 400);
  assert.equal(r.invalidCalls, 31);
  assert.equal(r.maximumCases.length, 10);
  assert.equal(r.checksum, '9025324404316664252');
});

test('literal positive degree compositions and allocation faults independently verify optimum, returned trees and recovery', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/tree-degree-preservation-independent.py');
  assert.equal(r.checks, 21790);
  assert.equal(r.newDegreeInputs, 1800);
  assert.equal(r.literalPositiveDegreeCompositions, 6619600);
  assert.equal(r.allocationFailures, 17);
  assert.equal(r.checksum, '14600543257379776778');
});
