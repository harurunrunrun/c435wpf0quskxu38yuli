import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const opening = new Set([...'([{（［｛〔〈《「『【〖〘〚‘“«‹']);
const closing = new Set([...')]}）］｝〕〉》」』】〗〙〛’”»›、。，．・：；？！!?%,.:;ー々〃ゝゞヽヾぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ…‥']);
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-text-wrapping-'));
  await compileLocalModules(site, temporary);
  return import(pathToFileURL(path.join(temporary, 'flow.js')).href);
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });
const titles = {};
for (const name of (await readdir(path.join(site, 'data'))).filter(name => /^techniques.*\.json$/.test(name))) {
  for (const item of JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))) titles[item.id] = item.title;
}

function decode(value) {
  return value.replace(/&(amp|lt|gt|quot|apos|#39);/g, (_, entity) => ({ amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", '#39': "'" })[entity]);
}
function parseSvg(source) {
  const root = { tag: 'root', attrs: {}, children: [], text: '' };
  const stack = [root];
  for (const token of source.match(/<[^>]+>|[^<]+/g) ?? []) {
    if (token.startsWith('</')) { stack.pop(); continue; }
    if (!token.startsWith('<')) { stack.at(-1).text += decode(token); continue; }
    const tag = token.match(/^<([\w:-]+)/)?.[1];
    assert(tag, 'valid SVG opening tag');
    const attrs = Object.fromEntries([...token.matchAll(/([\w:-]+)="([^"]*)"/g)].map(match => [match[1], decode(match[2])]));
    const node = { tag, attrs, children: [], text: '' };
    stack.at(-1).children.push(node);
    if (!token.endsWith('/>')) stack.push(node);
  }
  assert.equal(stack.length, 1, 'balanced SVG');
  return root;
}
function descendants(node, predicate) {
  return node.children.flatMap(child => [...(predicate(child) ? [child] : []), ...descendants(child, predicate)]);
}
function checkLines(lines, expected, width, description, strict = true) {
  assert.equal(lines.map(line => line.text).join(''), expected, `${description}: no characters are added, removed or reordered`);
  for (let index = 0; index < lines.length; index++) {
    const characters = [...lines[index].text];
    assert(characters.length > 0 && characters.length <= width, `${description}: each line fits ${width} full-em cells`);
    if (!strict) continue;
    if (index > 0) assert(!closing.has(characters[0]), `${description}: punctuation and closing brackets do not start a line: ${lines[index].text}`);
    if (index < lines.length - 1) assert(!opening.has(characters.at(-1)), `${description}: opening brackets do not end a line: ${lines[index].text}`);
  }
}
function checkBounds(group, lines, font, centered, description) {
  const rect = group.children.find(child => child.tag === 'rect');
  assert(rect, `${description}: text has a reserved rectangle`);
  const x = Number(rect.attrs.x), y = Number(rect.attrs.y), width = Number(rect.attrs.width), height = Number(rect.attrs.height);
  for (const line of lines) {
    const textWidth = [...line.text].length * font;
    const left = Number(line.attrs.x) - (centered ? textWidth / 2 : 0);
    const baseline = Number(line.attrs.y);
    assert(left >= x && left + textWidth <= x + width, `${description}: text fits horizontally without hanging punctuation`);
    assert(baseline - font >= y && baseline + font * .25 <= y + height, `${description}: text fits vertically`);
  }
}
function inspect(flow, graph, techniqueTitles, { strict = true, explanations = false } = {}) {
  const svg = parseSvg(flow.renderFlowSvg(graph, '/flowchartcp/', techniqueTitles));
  const nodes = descendants(svg, node => node.tag === 'g' && Object.hasOwn(node.attrs, 'data-node'));
  for (const node of graph.nodes) {
    const group = nodes.find(group => group.attrs['data-node'] === node.id);
    assert(group, `${graph.id}/${node.id}: node is rendered`);
    const title = descendants(group, text => text.tag === 'text' && text.attrs.class === 'node-title');
    checkLines(title, node.title, 17, `${graph.id}/${node.id} title`, strict);
    checkBounds(group, title, 16, false, `${graph.id}/${node.id} title`);
    const explanation = descendants(group, text => text.tag === 'text' && text.attrs.class === 'node-explanation');
    if (explanations) checkLines(explanation, node.explanation ?? '', 24, `${graph.id}/${node.id} explanation`, strict);
    checkBounds(group, explanation, 12, false, `${graph.id}/${node.id} explanation`);
    const links = descendants(group, item => item.tag === 'a' && (item.attrs.href ?? '').includes('/techniques/'));
    assert.equal(links.length, node.techniques?.length ?? 0, `${graph.id}/${node.id}: each technique has a link`);
    for (const [index, link] of links.entries()) {
      const id = node.techniques[index];
      const lines = descendants(link, text => text.tag === 'text');
      checkLines(lines, techniqueTitles[id] ?? id, 23, `${graph.id}/${node.id} link ${id}`, strict);
      checkBounds(group, lines, 12, false, `${graph.id}/${node.id} link ${id}`);
    }
    if (node.type !== 'question') continue;
    for (const option of flow.getNodeOptions(node)) {
      const id = `${node.id}:${option.id}:${node.answers[option.id]}`;
      const label = descendants(svg, group => group.tag === 'g' && group.attrs['data-edge-label'] === id)[0];
      assert(label, `${graph.id}/${id}: answer label is rendered`);
      const lines = descendants(label, text => text.tag === 'text');
      checkLines(lines, option.label, 17, `${graph.id}/${id} answer`, strict);
      checkBounds(label, lines, 13, true, `${graph.id}/${id} answer`);
    }
  }
  return svg;
}
function fixture(title, answer = title) {
  return {
    id: 'wrapping-fixture', title: '改行の検証', description: '元の文字列を保持する。', root: 'question',
    nodes: [
      { id: 'question', type: 'question', title, explanation: '値を「まとめて扱う」とき、同じ結果を再利用できますか？', options: [{ id: 'yes', label: answer }, { id: 'unknown', label: 'わからない' }], answers: { yes: 'result', unknown: 'result' } },
      { id: 'result', type: 'result', title: '候補の記事へ進む', techniques: ['example'], conditions: ['必要な性質を確認する'] },
    ],
  };
}

test('Japanese punctuation stays with the preceding character in actual node, answer and technique text', async () => {
  const flow = await implementation;
  for (const punctuation of ['？', '。', '、', '！', '?', ')', '）', '」', '』', '】', '…']) {
    const graph = fixture(`${'文'.repeat(17)}${punctuation}`);
    const svg = inspect(flow, graph, { example: `${'技'.repeat(23)}${punctuation}` }, { explanations: true });
    const question = descendants(svg, node => node.attrs['data-node'] === 'question')[0];
    const lines = descendants(question, node => node.attrs.class === 'node-title');
    assert.deepEqual(lines.map(line => line.text), ['文'.repeat(16), `文${punctuation}`], 'the preceding line gives up one cell instead of leaving punctuation alone');
  }
});

test('opening brackets move to the next line without changing their contents', async () => {
  const flow = await implementation;
  for (const bracket of ['(', '（', '[', '［', '{', '｛', '「', '『', '【', '〈']) {
    inspect(flow, fixture(`${'文'.repeat(16)}${bracket}補足の内容`), { example: `${'技'.repeat(22)}${bracket}補足の内容` }, { explanations: true });
  }
  inspect(flow, fixture(`${'文'.repeat(16)}「括弧」${'文'.repeat(16)}？`), { example: `${'技'.repeat(22)}（詳細）` }, { explanations: true });
});

test('ASCII, escaped text, supplementary characters and unbreakable symbol runs retain bounded text', async () => {
  const flow = await implementation;
  for (const value of ['ASCII<&"\' text and punctuation?', `${'🧭'.repeat(17)}？`, '('.repeat(2048), '？'.repeat(2048), '[]{}()!?,.;:'.repeat(128), '']) {
    inspect(flow, fixture(value), { example: value }, { strict: false, explanations: true });
  }
});

function linesAtWidth(svg, width) {
  const question = descendants(svg, node => node.attrs['data-node'] === 'question')[0];
  if (width === 17) {
    const title = descendants(question, node => node.attrs.class === 'node-title').map(node => node.text);
    const label = descendants(svg, node => node.attrs['data-edge-label'] === 'question:yes:result')[0];
    assert.deepEqual(descendants(label, node => node.tag === 'text').map(node => node.text), title, 'node and answer use the same word boundaries');
    return title;
  }
  if (width === 24) return descendants(question, node => node.attrs.class === 'node-explanation').map(node => node.text);
  const result = descendants(svg, node => node.attrs['data-node'] === 'result')[0];
  const link = descendants(result, node => node.tag === 'a' && node.attrs.href.includes('/techniques/'))[0];
  return descendants(link, node => node.tag === 'text').map(node => node.text);
}

test('English technique names move whole words to the next line at every rendered text width', async () => {
  const flow = await implementation;
  for (const width of [17, 23, 24]) {
    const cases = [
      [`${'文'.repeat(width - 1)}GCD`, ['文'.repeat(width - 1), 'GCD']],
      [`${'文'.repeat(width - 2)}XOR`, ['文'.repeat(width - 2), 'XOR']],
      [`${'文'.repeat(width - 1)}GCDとXOR`, ['文'.repeat(width - 1), 'GCDとXOR']],
      [`${'文'.repeat(width - 16)}Segment Tree Beats`, [`${'文'.repeat(width - 16)}Segment Tree `, 'Beats']],
      [`${'文'.repeat(width - 2)}range_add/GCD-v2`, ['文'.repeat(width - 2), 'range_add/GCD-v2']],
      [`${'文'.repeat(width - 2)}（GCD）`, ['文'.repeat(width - 2), '（GCD）']],
      [`${'文'.repeat(width - 2)}(XOR)`, ['文'.repeat(width - 2), '(XOR)']],
      [`${'文'.repeat(width - 3)}GCD？`, ['文'.repeat(width - 3), 'GCD？']],
    ];
    for (const [value, expected] of cases) {
      const graph = fixture(value);
      graph.nodes[0].explanation = value;
      const svg = inspect(flow, graph, { example: value }, { explanations: true });
      assert.deepEqual(linesAtWidth(svg, width), expected, `${width} cells: ${value}`);
    }
  }
});

test('exact-width words and overlong words preserve every character and fall back to punctuation-safe splits', async () => {
  const flow = await implementation;
  for (const width of [17, 23, 24]) {
    const cases = [
      [`${'文'.repeat(width - 3)}GCD`, [`${'文'.repeat(width - 3)}GCD`]],
      [`${'文'.repeat(width - 3)}XOR後`, [`${'文'.repeat(width - 3)}XOR`, '後']],
      ['A'.repeat(width), ['A'.repeat(width)]],
      [`文文文${'A'.repeat(width + 5)}後`, [`文文文${'A'.repeat(width - 3)}`, `${'A'.repeat(8)}後`]],
      [`（${'A'.repeat(width)}）`, [`（${'A'.repeat(width - 1)}`, 'A）']],
    ];
    for (const [value, expected] of cases) {
      const graph = fixture(value);
      graph.nodes[0].explanation = value;
      const svg = inspect(flow, graph, { example: value }, { explanations: true });
      assert.deepEqual(linesAtWidth(svg, width), expected, `${width} cells: ${value}`);
    }
  }
});

test('every checked-in diagram preserves full titles, answer labels and Japanese technique names within their text boxes', async () => {
  const flow = await implementation;
  for (const graph of flow.graphs) inspect(flow, graph, titles);
});
