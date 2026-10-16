import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('published synchronized product-distance sum matches literal product-graph BFS and boundary cases', { timeout: 250000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_product_distance_cpp.py')], {
    cwd: site,
    timeout: 240000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 3, result.stdout);
  assert.match(result.stdout, /Published synchronized product-distance implementation passed independent product-graph BFS and boundary comparisons\./);
});
