import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('published blossom and bit-parallel LCS implementations match independent subset and full-table DP', { timeout: 390000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_blossom_lcs_cpp.py')], {
    cwd: site,
    timeout: 380000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 2, result.stdout);
  assert.match(result.stdout, /All 2 blossom and LCS implementations passed independent comparisons and boundary cases\./);
});
