import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);

test('six published tree and construction implementations match independent path, labelling, permutation and graph enumerations', { timeout: 330000 }, async () => {
  const result = await execute('python3', [path.join(site, 'scripts/check_tree_construction_cpp.py')], {
    cwd: site,
    timeout: 320000,
    maxBuffer: 1024 * 1024,
  });
  assert.equal((result.stdout.match(/ PASS:/g) || []).length, 6, result.stdout);
  assert.match(result.stdout, /All 6 tree and construction implementations passed independent comparisons and boundary cases\./);
});
