import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, writeFile, rm } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);
async function codeFromArticle(id) {
  const content = await readFile(path.join(site, 'src/content/docs/techniques', `${id}.mdx`), 'utf8');
  const snippet = content.match(/^```cpp\s*\n([\s\S]*?)^```/m)?.[1];
  assert(snippet, `${id}: missing standalone C++ snippet`);
  return snippet;
}
async function verifyCppArticles(ids, fixtureName, expectedOutput) {
  const snippets = await Promise.all(ids.map(codeFromArticle));
  const includes = new Set(['#include <random>', '#include <string>', '#include <climits>', '#include <algorithm>', '#include <numeric>', '#include <iostream>', '#include <tuple>']);
  for (const snippet of snippets) for (const match of snippet.matchAll(/^#include[^\n]+/gm)) includes.add(match[0]);
  const namespaces = snippets.map((snippet, index) => `namespace t${index} {\n${snippet.replace(/^#include[^\n]+\n?/gm, '')}\n}`).join('\n');
  const fixture = await readFile(path.join(site, 'tests/fixtures', fixtureName), 'utf8');
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-core-properties-'));
  try {
    const source = path.join(directory, 'test.cpp');
    const binary = path.join(directory, 'test');
    await writeFile(source, [...includes].join('\n') + '\n' + namespaces + '\n' + fixture);
    await execute(process.env.CXX || 'g++', ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', source, '-o', binary], { timeout: 60000 });
    const result = await execute(binary, [], { timeout: 30000 });
    assert(result.stdout.includes(expectedOutput), `Missing success marker: ${expectedOutput}`);
  } finally { await rm(directory, { recursive: true, force: true }); }
}
test('published core implementations match exhaustive interval and shortest-path models', { timeout: 90000 }, async () => {
  await verifyCppArticles(['prefix-sum', 'difference-array', 'binary-search', 'zero-one-bfs', 'dijkstra', 'fenwick-tree', 'segment-tree'], 'core-property.cpp', 'core properties verified');
});
test('published advanced implementations match naive minima, subset enumeration, row scans, and exhaustive flows', { timeout: 90000 }, async () => {
  await verifyCppArticles(['convex-hull-trick', 'xor-basis', 'monge-smawk', 'max-flow', 'min-cost-flow', 'ntt', 'formal-power-series', 'linear-recurrence'], 'advanced-property.cpp', 'advanced properties verified');
});
