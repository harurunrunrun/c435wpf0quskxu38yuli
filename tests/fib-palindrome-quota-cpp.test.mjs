import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('six published mask, quota, automaton, Fibonacci and palindrome implementations match independent subset, path, replacement, array and adjacent-swap enumerations', { timeout: 390000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_fib_palindrome_quota_cpp.py')], {
    cwd: site,
    timeout: 380000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 6, result.stdout);
  assert.match(result.stdout, /All 6 mask, quota, automaton, Fibonacci and palindrome implementations passed independent comparisons and boundary cases\./);
});
