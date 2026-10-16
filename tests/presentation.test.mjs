import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderHome, renderTechniqueList, renderProblemReferences, sections } from '../src/lib/presentation.mjs';
import { renderMarkdown } from '../vendor/markdown.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const names = await readdir(path.join(site, 'data'));
const techniques = (await Promise.all(names.filter(name => /^techniques-.*\.json$/.test(name)).map(async name =>
  JSON.parse(await readFile(path.join(site, 'data', name), 'utf8')).map(row => ({ ...row, kind: name.includes('-specific-') ? 'technique' : 'foundation' }))
))).flat();
const references = (await Promise.all(names.filter(name => /^references-.*\.json$/.test(name)).map(async name =>
  JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))
))).flat();

test('primary collections show concrete cases and keep foundation articles in their own index', () => {
  const primary = renderTechniqueList(techniques);
  const foundations = renderTechniqueList(techniques, { kind: 'foundation' });
  for (const technique of techniques) {
    const href = `/flowchartcp/techniques/${technique.id}/`;
    assert.equal(primary.includes(`href="${href}"`), technique.kind === 'technique', technique.id);
    assert.equal(foundations.includes(`href="${href}"`), technique.kind === 'foundation', technique.id);
  }
  for (const id of ['dp-range-sum', 'bounded-knapsack-deque', 'reroot-prefix-suffix', 'subarray-extremum-contribution']) {
    assert.ok(primary.includes(`/techniques/${id}/`), id);
  }
  const home = renderHome(techniques);
  assert.equal((home.match(/data-section-link/g) ?? []).length, sections.length);
  assert.doesNotMatch(home, /entrance-card|hero|問題の条件から|知識の地図|QUESTION|CANDIDATES/);
});

test('source tables distinguish an official explanation from a proved independent classification', () => {
  const official = renderProblemReferences(references, 'quotient-blocks');
  const independent = renderProblemReferences(references, 'expectation-indicators', ['indicator variables']);
  assert.match(official, />解説<\/a>/);
  assert.match(independent, />問題文<\/a>/);
  assert.doesNotMatch(independent, />参照解答<\/a>/);
  assert.match(independent, /この手法を使う問題/);
  assert.match(independent, /indicator variables/);
  const unsafe = renderProblemReferences([{ techniqueId: 'test', title: '<script>', url: 'https://example.com/?a=1&b=2', source: '<img>', evidence: '<svg>' }], 'test');
  assert.doesNotMatch(unsafe, /<script>|<img>|<svg>/);
  assert.match(unsafe, /&lt;script&gt;/);
});

test('all article formulas render and prose contains no corrupted escapes or template headings', async () => {
  for (const technique of techniques) {
    let content = await readFile(path.join(site, 'src/content/docs/techniques', `${technique.id}.mdx`), 'utf8');
    assert.doesNotMatch(content, /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/, technique.id);
    const prose = content.replace(/```[\s\S]*?```/g, '');
    assert.doesNotMatch(prose, /\t[a-z]+/g, `${technique.id}: broken LaTeX escape`);
    assert.doesNotMatch(prose, /## (気づく手掛かり|モデル・使い方|関連技巧|根拠資料)\n|根拠資料[0-9]+|TODO|TBD/, technique.id);
    content = content.replace(/^---\n[\s\S]*?\n---\n/, '').replace(/^import .+;\s*$/gm, '').replace(/<TechniqueReferences[^>]+\/>/g, '');
    const html = renderMarkdown(content);
    assert.doesNotMatch(html, /class="katex-error"/, `${technique.id}: invalid math`);
    if (technique.kind === 'technique') {
      assert.match(content, /## 適用条件\n[\s\S]+?## なぜ正しいか\n[\s\S]+?## 計算量\n[\s\S]+?## 実装/);
    }
  }
});
