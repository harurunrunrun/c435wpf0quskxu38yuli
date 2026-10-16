import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('published silhouettes and independent letter rewrites match direct legal height tables and whole-word state searches', { timeout: 320000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_silhouette_translation_cpp.py')], {
    cwd: site,
    timeout: 310000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 2, result.stdout);
  assert.match(result.stdout, /All 2 silhouette and translation implementations passed independent comparisons and contract checks\./);
});
