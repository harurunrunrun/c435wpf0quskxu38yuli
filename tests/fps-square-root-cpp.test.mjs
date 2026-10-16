import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

test('published FPS square root matches direct coefficients and boundary cases', { timeout: 270000 }, async () => {
  const { stdout } = await promisify(execFile)('python3', [fileURLToPath(new URL('../scripts/check_fps_square_root_cpp.py', import.meta.url))], { timeout: 260000, maxBuffer: 1024 * 1024 });
  assert.match(stdout, /PASS: FPS square root/);
});
