import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('published speed bisection and weighted quantization match independent models', { timeout: 200000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_speed_quantization_cpp.py')], {
    cwd: site,
    timeout: 190000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 2, result.stdout);
  assert.match(result.stdout, /All 2 speed and quantization implementations passed independent comparisons and contract checks\./);
});
