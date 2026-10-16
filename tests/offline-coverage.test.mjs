import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const run = promisify(execFile);
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
test('published offline and rank tricks agree with direct chronological operations and all subset XORs', { timeout: 180000 }, async () => {
  const result = await run('python3', ['tests/fixtures/offline-coverage-property.py'], { cwd: site, timeout: 170000, maxBuffer: 1024 * 1024 });
  assert.match(result.stdout, /offline coverage properties verified: 12 published implementations/);
});
