import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

test('published locally filtered hand partition agrees with direct ownership enumeration', { timeout: 310000 }, async () => {
  const { stdout } = await promisify(execFile)('python3', [fileURLToPath(new URL('../scripts/check_disjoint_candidate_sets_cpp.py', import.meta.url))],
    { timeout: 300000, maxBuffer: 1024 * 1024 });
  assert.match(stdout, /checks=17150 complete_assignments=13521480/);
  assert.match(stdout, /max_pair_product=511225 pair_upper_bound=76683750/);
});
