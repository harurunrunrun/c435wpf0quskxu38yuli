import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
async function check(name) {
  const { stdout } = await run('python3', [fileURLToPath(new URL('../scripts/' + name, import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  return JSON.parse(stdout);
}

test('transition counting handles every adaptive small branch and the maximum budget in both linking modes', { timeout: 310000 }, async () => {
  const result = await check('check_transition_species_cpp.py');
  assert.equal(result.checks, 23642187);
  assert.equal(result.localAssignments, 128);
  assert.equal(result.staticCases, 131304);
  assert.equal(result.adaptiveStates, 5586);
  assert.equal(result.adaptiveLeaves, 3814);
  assert.equal(result.maxQueries, 226);
  assert.equal(result.provedTotalLengthBound, 40306);
  assert.equal(result.checksum, '17036070644408443896');
  assert.deepEqual(result.standaloneCallback, { cases: 4099, checks: 314871,
    checksum: '7379661480237581096', graderMacro: false, machineStub: false });
});

test('word-side comma propagation agrees with literal rules, every closed extension and a separate grammar oracle', { timeout: 310000 }, async () => {
  const result = await check('check_word_boundary_comma_cpp.py');
  assert.equal(result.checks, 1051695);
  assert.equal(result.exhaustiveTexts, 134117);
  assert.equal(result.closedConfigurationsEnumerated, 667190);
  assert.equal(result.lexicalStrings, 87381);
  assert.equal(result.lexicalValid, 73);
  assert.equal(result.maximumInputBytes, 1000000);
  assert.equal(result.maximumOutputBytes, 1499997);
  assert.equal(result.checksum, '10870040000863900980');
});
