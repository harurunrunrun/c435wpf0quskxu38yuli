import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

for (const [name, file, success] of [
  ['two-choice exact-count reconstruction', 'check_two_choice_count_cpp.py', /PASS: two-choice nondecreasing/],
  ['hidden original-color pairs', 'check_hidden_color_pairs_cpp.py', null],
  ['whole-color tree closure', 'check_tree_color_closure_cpp.py', /PASS: tree-color-closure-sink-scc/],
  ['grid triplet packing and rollback', 'check_grid_triplet_conflict_packing_cpp.py', /PASS: grid triplet packing/],
]) {
  test(`published JOI technique: ${name}`, { timeout: 270000 }, async () => {
    const { stdout } = await promisify(execFile)('python3', [fileURLToPath(new URL('../scripts/' + file, import.meta.url))],
      { timeout: 260000, maxBuffer: 2 * 1024 * 1024 });
    if (success) assert.match(stdout, success);
    else {
      const report = JSON.parse(stdout);
      assert.equal(report.status, 'passed');
      assert(report.exhaustiveCases > 0 && report.randomCases > 0 && report.officialAdapterCases > 0);
      assert.equal(report.provedMaximumQueries, 19000);
      assert(report.maximumObservedQueries <= report.provedMaximumQueries);
    }
  });
}
