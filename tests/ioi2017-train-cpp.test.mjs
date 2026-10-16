import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const hash = 'e8f17727cc378089486222a8168e5fa42abb26e79e4b56faee4410a70f0627c1';
async function check(relative) {
  const { stdout } = await run('python3', [fileURLToPath(new URL(relative, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  const result = JSON.parse(stdout);
  assert.equal(result.cppSha256, hash);
  return result;
}

test('repeated-target winning regions and positional policies agree with literal first-visit games, fixed policies and maximum elimination cases', { timeout: 310000 }, async () => {
  const r = await check('../scripts/check_buchi_owned_graph_cpp.py');
  assert.equal(r.checks, 12032358);
  assert.equal(r.apiCalls, 454155);
  assert.equal(r.exhaustiveGraphs, 2145);
  assert.equal(r.exhaustiveAssignments, 449398);
  assert.equal(r.firstVisitInitialPositions, 1781207);
  assert.equal(r.firstVisitSearchNodes, 7419964);
  assert.equal(r.fixedPolicyPairs, 954684);
  assert.equal(r.fixedPolicyInitialPositions, 3916282);
  assert.equal(r.randomSmallGraphs, 500);
  assert.equal(r.randomLargeGraphs, 1000);
  assert.equal(r.strategyCertificates, 3008);
  assert.equal(r.metamorphicChecks, 3000);
  assert.equal(r.invalidCases, 30);
  assert.equal(r.maximumCases.length, 8);
  assert.equal(r.maximumCases.at(-1).deletionRounds, 2500);
  assert.equal(r.checksum, '5543748192885197194');
});

test('finite battery safety games independently verify both returned policies against adaptive opponents, charge boundaries and allocation failures', { timeout: 310000 }, async () => {
  const r = await check('../research/probes/owned-repeated-target-independent.py');
  assert.equal(r.checks, 6023018);
  assert.equal(r.inputs, 23600);
  assert.equal(r.exhaustiveTotalGraphs, 353);
  assert.equal(r.exhaustiveOwnerAndTargetAssignmentsIncludingEmpty, 22100);
  assert.equal(r.randomInputs, 1500);
  assert.equal(r.finiteBatterySafetyGames, 70926);
  assert.equal(r.returnedPolicyAdaptiveOpponentInitialPositions, 232866);
  assert.equal(r.exactCapacityBoundaryControls, 63);
  assert.equal(r.allocationFailureExceptions, 163);
  assert.equal(r.bodyAllocationFailures, 79);
  assert.equal(r.adapterAllocationFailures, 84);
  assert.equal(r.maximum2500RoundBodyRequestedPayloadBytes, 754600);
  assert.equal(r.maximum2500RoundAdapterRequestedPayloadBytes, 1114600);
  assert.equal(r.checksum, '617204148435879420');
});
