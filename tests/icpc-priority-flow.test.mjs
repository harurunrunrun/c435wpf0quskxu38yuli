import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-icpc-priority-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Independently fixed feature paths and checks. Neither registered example
// walks nor the feature-evidence collection supplies these expectations.
const paths = [
  {
    id: 'positive-denominator-offset-real-bisection',
    domain: 'math',
    prefix: ['real-offset'],
    graph: 'real-offset-positive-conditions',
    guards: ['positive-distances', 'shared-offset', 'domain-precision'],
    terms: [/正/, /分母|速度/, /共通|同じ/, /実数|精度|誤差/, /定義域|下端|極/],
    source: 'ICPC', problemId: 'wf2017_e', year: '2017',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=9',
  },
  {
    id: 'weighted-squared-quantization-interval-dp',
    domain: 'dp',
    prefix: ['placement-time', 'squared-quantization'],
    graph: 'weighted-integer-quantization-conditions',
    guards: ['integer-domain', 'nearest-square', 'small-domain'],
    terms: [/整数/, /二乗|平方/, /最寄|最も近|近い/, /頻度|重み/, /256|255|小さ|値域/],
    source: 'ICPC', problemId: 'wf2017_f', year: '2017',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=11',
  },
  {
    id: 'row-column-maxima-height-matching',
    domain: 'grid-arrangements',
    prefix: ['color-numbers', 'height-silhouette'],
    graph: 'silhouette-maxima-support-conditions',
    guards: ['three-views', 'rearrangement', 'independent-maxima'],
    terms: [/行/, /列/, /最大/, /積み|再配置|並べ替/, /0|零|支持/, /対応|共有|マッチング/],
    source: 'ICPC', problemId: 'wf2017_c', year: '2017',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=5',
  },
  {
    id: 'independent-letter-rewrite-reachability',
    domain: 'strings',
    prefix: ['changes', 'letter-rules'],
    graph: 'letter-independent-rewrite-conditions',
    guards: ['local-rules', 'independent-positions', 'queries'],
    terms: [/文字/, /位置/, /独立|ほか|他の/, /有向|向き|方向/, /到達/, /0回|零回|同じ文字/],
    source: 'ICPC', problemId: 'wf2017_i', year: '2017',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=17',
  },
  {
    id: 'pareto-pruned-max-rectangle-monotone-partner',
    domain: 'flow-matching',
    prefix: ['pair-goals', 'rectangle-profit'],
    graph: 'rectangle-profit-pareto-conditions',
    guards: ['two-differences', 'positive', 'one-pair'],
    terms: [/差/, /積/, /正/, /一つ|一組|1組|一対/, /単調|逆転|支配/],
    source: 'ICPC', problemId: 'wf2017_d', year: '2017',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=7',
  },
  {
    id: 'hierarchical-reset-walk-count',
    domain: 'graphs',
    prefix: ['walk-goals', 'label-reset'],
    graph: 'hierarchical-label-walk-conditions',
    guards: ['reset-order', 'endpoints', 'bounded-sizes'],
    terms: [/大きい|大きな|上位/, /再使用|再利用|復活|リセット/, /始点/, /終点/, /最初/, /最後/, /60/, /空|0回|零回/],
    source: 'USACO', problemId: '1069', year: '2020',
    statementUrl: 'https://usaco.org/index.php?page=viewproblem2&cpid=1069',
  },
];
const ids = paths.map(item => item.id);
const candidates = value => value.current.techniques ?? [];
function walk(flow, domain, choices) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, `${domain}/${choices.join('/')}: every answer is consumed`);
  return value;
}
function replay(flow, domain, choices) {
  let state = flow.initialState(domain);
  for (const answer of choices) {
    while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
    state = flow.answerState(state, answer);
  }
  while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
  return state;
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}
async function loadCollections(expression) {
  const files = await readdir(path.join(site, 'data'));
  return (await Promise.all(files.filter(name => expression.test(name)).map(async name =>
    JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))))).flat();
}
const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

test('six independently specified feature paths require all three applicability checks', async () => {
  const { flow } = await implementation;
  assert.equal(new Set(ids).size, 6);
  for (const item of paths) {
    const initial = walk(flow, item.domain, item.prefix);
    assert.equal(initial.graph.id, item.graph, `${item.id}: problem features reach the applicability chart`);
    assert.equal(initial.current.id, item.guards[0]);
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard], `${item.id}: the necessary checks stay in order`);
      assert(ids.every(id => !candidates(value).includes(id)), `${item.id}: no result precedes a necessary check`);
      const options = flow.getNodeOptions(value.current);
      assert.deepEqual(options.map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const option of options)
        assert(option.label.length >= 2, `${item.id}/${value.current.id}/${option.id}: the answer has a readable label`);
    }
    const value = walk(flow, item.domain, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id], `${item.id}: all three premises select this technique`);
    const text = JSON.stringify(value.graph);
    for (const term of item.terms) assert.match(text, term, `${item.id}: applicability details are visible`);
    const diagram = flow.renderFlowSvg(value.graph);
    assert(diagram.includes(`/flowchartcp/techniques/${item.id}/`), `${item.id}: the result in the SVG links to its article`);
    let answerCount = 0;
    for (const node of value.graph.nodes) if (node.type === 'question') {
      for (const option of flow.getNodeOptions(node)) {
        ++answerCount;
        assert(diagram.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`), `${item.id}: every graph answer has an SVG edge`);
        assert(diagram.includes(`<title>${xml(option.label)}</title>`), `${item.id}: every drawn answer is labeled`);
      }
    }
    assert.equal((diagram.match(/class="flow-edge /g) ?? []).length, answerCount, `${item.id}: the SVG adds no answer edges`);
  }
  assert.equal(flow.entryGraphs.length, 15, 'the new charts stay under the existing fields');
});

test('no and unknown at each of the eighteen guards require condition checking', async () => {
  const { flow } = await implementation;
  for (const item of paths) {
    for (let guard = 0; guard < item.guards.length; ++guard) {
      for (const answer of ['no', 'unknown']) {
        const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes'), answer]);
        assert.equal(value.graph.id, 'condition-check', `${item.id}/${item.guards[guard]}/${answer}: unresolved premises remain explicit`);
        assert.equal(value.current.type, 'question');
        assert(ids.every(id => !candidates(value).includes(id)), `${item.id}/${answer}: no unsupported new technique is asserted`);
      }
    }
  }
});

test('question and diagram URLs preserve successes and unresolved premises through finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of paths) {
    const histories = [[...item.prefix, 'yes', 'yes', 'yes']];
    for (let guard = 0; guard < item.guards.length; ++guard)
      for (const answer of ['no', 'unknown'])
        histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item.domain, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
      for (let remaining = weight(state) + 1; ; --remaining) {
        assert(remaining > 0, `${item.id}: Back terminates`);
        assert.equal(flow.getFlowDomainId(state), item.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluation = flow.evaluateState(state);
        if (!diagrams.has(state.graph)) diagrams.set(state.graph, flow.renderFlowSvg(evaluation.graph));
        const diagram = diagrams.get(state.graph);
        assert(diagram.includes(`data-node="${evaluation.current.id}"`), `${item.id}: the current question or result exists in the SVG`);
        for (const node of evaluation.path)
          assert(diagram.includes(`data-node="${node.id}"`), `${item.id}: every highlighted node exists`);
        for (const edge of evaluation.edges)
          assert(diagram.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`), `${item.id}: every highlighted answer exists`);
        const hash = flow.serializeFlowHash(state);
        assert.deepEqual(flow.parseFlowHash(hash), state, `${item.id}: the question URL restores its history`);
        assert.deepEqual(viewer.diagramState(state.graph, hash), state, `${item.id}: the diagram restores the same history`);
        const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
        assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
        assert.equal(url.hash, hash, `${item.id}: the diagram URL shares the question history`);
        assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
        if (!weight(state)) break;
        const previous = flow.backFlowState(state);
        assert(weight(previous) < weight(state), `${item.id}: Back removes a canonical step`);
        state = previous;
      }
      assert.deepEqual(state, flow.initialState(item.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  }
});

test('all six articles have reviewed metadata, eight sections, one C++ implementation and original example walks', async () => {
  const { flow } = await implementation;
  const [metadata, references] = await Promise.all([
    loadCollections(/^techniques-.*\.json$/),
    loadCollections(/^references-.*\.json$/),
  ]);
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  for (const item of paths) {
    const registered = metadata.filter(row => row.id === item.id);
    assert.equal(registered.length, 1, `${item.id}: metadata is registered exactly once`);
    const technique = registered[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)), `${item.id}: an English name is searchable`);
    assert(technique.sources.includes(item.statementUrl), `${item.id}: the original problem is a metadata source`);
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert(article.includes(`techniqueId: ${item.id}\n`));
    const headings = ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'];
    assert.equal((article.match(/^## /gm) ?? []).length, headings.length);
    for (const heading of headings)
      assert.equal(article.split(`## ${heading}\n`).length - 1, 1, `${item.id}: one ${heading} section`);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, `${item.id}: one reusable C++ implementation`);
    assert(article.includes(`techniqueId="${item.id}"`), `${item.id}: verified examples are displayed`);
    for (const source of technique.sources)
      assert(article.includes(source), `${item.id}: metadata sources are accessible from the article`);
    if (item.source === 'ICPC')
      assert.match(article, /非公式|unofficial/i, `${item.id}: the published sketch is identified as unofficial`);
    const examples = references.filter(row => row.techniqueId === item.id);
    assert(examples.length, `${item.id}: there is a confirmed original example`);
    const original = examples.find(row => row.source === item.source && row.problemId === item.problemId);
    assert(original, `${item.id}: the independently fixed original problem is included`);
    assert.equal(original.url, item.statementUrl);
    for (const row of examples) {
      assert(['editorial', 'reference-solution', 'independent-analysis'].includes(row.verification));
      assert(row.evidence.length > 0);
      const record = walks.find(candidate => candidate.source === row.source && candidate.problemId === row.problemId && candidate.expectedTechniqueIds.includes(item.id));
      assert(record, `${item.id}/${row.source}/${row.problemId}: the reference has a root walk`);
      assert.equal(record.statementUrl, row.url);
      assert.equal(record.reviewStatus, 'verified');
      assert.equal(record.verificationKind, row.verification);
      assert(record.features.length >= 2);
      const value = walk(flow, record.entryGraphId, record.choices);
      assert(candidates(value).includes(item.id));
      assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
    }
  }
});

test('six fixed original problems preserve their feature evidence and only claim the verified year or month', async () => {
  const features = JSON.parse(await readFile(path.join(site, 'data/icpc-priority-problem-features.json'), 'utf8'));
  const references = (await loadCollections(/^references-.*\.json$/)).filter(row => ids.includes(row.techniqueId));
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  assert.equal(features.length, 6);
  const actualPairs = [];
  for (const item of paths) {
    const rows = features.filter(row => row.source === item.source && row.problemId === item.problemId);
    assert.equal(rows.length, 1, `${item.id}: the original problem has one feature record`);
    const feature = rows[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.cutoff, '2026-10-14');
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert(feature.features.length >= 2);
    assert(feature.evidenceUrl.startsWith('https://'));
    // Only a year/month has been verified for these six sources. A day
    // cannot be required or silently invented to pass this test.
    assert.equal(feature.publicationDate, undefined, `${item.id}: an exact day has not been verified`);
    const month = feature.publicationMonth ?? feature.contestYearMonth;
    if (month !== undefined) {
      assert.match(month, /^\d{4}-(0[1-9]|1[0-2])$/);
      assert.equal(month.slice(0, 4), item.year);
      assert(month < feature.cutoff.slice(0, 7), `${item.id}: the known month predates the cutoff month`);
    } else {
      const year = String(feature.publicationYear);
      assert.match(year, /^\d{4}$/);
      assert.equal(year, item.year);
      assert(year < feature.cutoff.slice(0, 4), `${item.id}: the known year predates the cutoff year`);
    }
    if (item.id === 'hierarchical-reset-walk-count')
      assert.equal(month, '2020-12', 'the USACO contest month is verified without a day');
    for (const id of feature.techniqueIds) {
      actualPairs.push(`${feature.source}/${feature.problemId}/${id}`);
      const reference = references.find(row => row.source === feature.source && row.problemId === feature.problemId && row.techniqueId === id);
      assert(reference, `${id}: feature evidence belongs to the confirmed reference`);
      assert.equal(reference.url, feature.url);
      assert.equal(reference.verification, feature.verification);
      assert(['source-before-cutoff', 'contest-before-cutoff'].includes(reference.cutoffVerification));
      const record = walks.find(row => row.source === feature.source && row.problemId === feature.problemId && row.expectedTechniqueIds.includes(id));
      assert(record);
      assert.deepEqual(record.features, feature.features);
      assert(['source-before-cutoff', 'contest-before-cutoff'].includes(record.cutoffVerification));
    }
  }
  assert.deepEqual(actualPairs.sort(), references.map(row => `${row.source}/${row.problemId}/${row.techniqueId}`).sort());
});
