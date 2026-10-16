import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('six published DP implementations match independent subsequence, partition, removal and permutation enumerations', { timeout: 270000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_dp_expansion_cpp.py')], {
    cwd: site,
    timeout: 260000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 6, result.stdout);
  assert.match(result.stdout, /All 6 DP expansion implementations passed independent comparisons and boundary cases\./);
});
