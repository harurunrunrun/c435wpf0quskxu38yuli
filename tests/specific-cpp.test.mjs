import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('18 published specific implementations match exhaustive array, tree, and graph models', { timeout: 150000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_specific_cpp.py')], {
    cwd: site,
    timeout: 145000,
  });
  assert.match(result.stdout, /All 18 specific scenarios passed randomized brute-force comparisons\./);
});
