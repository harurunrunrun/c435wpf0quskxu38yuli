import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
test('maximal threshold matchings agree with independent full matching enumeration', { timeout: 190000 }, async () => {
  const { stdout } = await promisify(execFile)('python3', [path.join(site, 'scripts/check_threshold_matching_cpp.py')], {
    cwd: site, timeout: 180000, maxBuffer: 1024 * 1024,
  });
  assert.match(stdout, /PASS: maximal threshold matching/);
});
