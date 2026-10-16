import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('published hierarchical reset walks match direct mask DP and maximum-size independent examples', { timeout: 310000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_spaceship_cpp.py')], {
    cwd: site,
    timeout: 300000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 4, result.stdout);
  assert.match(result.stdout, /Published hierarchical reset walk implementation passed independent mask-DP and maximum-boundary comparisons\./);
});
