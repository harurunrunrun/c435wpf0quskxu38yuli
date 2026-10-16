import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

for (const [name, file, success] of [
  ['incremental reciprocal-neighbor closure', 'check_directed_reciprocal_closure_cpp.py', null],
  ['interval endpoint contractions', 'check_interval_contraction_cpp.py', /PASS descending groups/],
  ['paired-height survivor counting', 'check_paired_height_survivors_cpp.py', /paired-height survivor checks passed/],
  ['nested rectangle corner recovery', 'check_nested_corner_pairing_cpp.py', /PASS: nested rectangle corner matching/],
]) {
  test(`published technique: ${name}`, { timeout: 330000 }, async () => {
    const { stdout } = await promisify(execFile)('python3', [fileURLToPath(new URL('../scripts/' + file, import.meta.url))],
      { timeout: 320000, maxBuffer: 2 * 1024 * 1024 });
    if (success) assert.match(stdout, success);
    else {
      const report = JSON.parse(stdout.trim().split(/\r?\n/).at(-1));
      assert.equal(report.status, 'passed');
      assert.equal(report.results.length, 5, 'the oracle and all four large patterns run');
      for (const result of report.results) assert.equal(result.status, 'passed');
    }
  });
}
