import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const run = promisify(execFile);
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
test('published matching models agree with exhaustive circulations, matrices, paths, assignments, and covers', { timeout: 240000 }, async () => {
  const result = await run('python3', ['tests/fixtures/flow-matching-property.py'], { cwd: site, timeout: 230000, maxBuffer: 1024 * 1024 });
  assert.match(result.stdout, /flow matching properties verified: 10 published implementations/);
});
