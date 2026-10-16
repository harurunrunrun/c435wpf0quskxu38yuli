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
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-frequency-rank-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Feature choices and necessary checks are specified independently of the
// registered example walks. An example cannot make its own route test pass.
const paths = [
  {
    domain: 'strings',
    prefix: ['extraction', 'palindrome', 'length-frequency'],
    graph: 'palindrome-length-frequency-conditions',
    guards: ['static', 'overlap', 'alphabet'],
    id: 'eertree-palindrome-length-frequency',
    terms: [/回文/, /出現/, /重な/, /小文字|26/],
  },
  {
    domain: 'strings',
    prefix: ['extraction', 'substrings', 'unique-common'],
    graph: 'shortest-common-unique-conditions',
    guards: ['two-strings', 'exactly-once', 'alphabet'],
    id: 'shortest-common-unique-substring',
    terms: [/二つ|2つ|2 つ/, /一回|1回|1 回/, /最短/, /小文字|26/],
  },
  {
    domain: 'ranges',
    prefix: ['aggregate-goals', 'window', 'sum-conditions', 'top-k-bounded'],
    graph: 'top-k-bounded-subarray-conditions',
    guards: ['length', 'overlap', 'small-k'],
    id: 'top-k-bounded-subarray-sums',
    terms: [/区間/, /上位|大きい/, /長さ/, /重な/],
  },
  {
    domain: 'ranges',
    prefix: ['selected-elements', 'pair-product-ratio', 'product-rank'],
    graph: 'signed-pair-product-conditions',
    guards: ['pairs', 'rank'],
    id: 'kth-signed-pair-product',
    terms: [/積/, /負/, /異なる|二つ|2つ|2 つ/, /順位|K|k/],
  },
  {
    domain: 'math',
    prefix: ['sum-divisor'],
    graph: 'digit-sum-divisor-conditions',
    guards: ['own-sum', 'small-range'],
    id: 'digit-sum-divides-value',
    terms: [/桁/, /和/, /割|剰余/, /固定/],
  },
  {
    domain: 'ranges',
    prefix: ['selected-elements', 'pair-product-ratio', 'floor-total'],
    graph: 'pair-floor-ratio-conditions',
    guards: ['positive', 'small-values', 'all-pairs'],
    id: 'pair-floor-ratio-frequency',
    terms: [/正|1以上|1 以上/, /値域|最大値|上限/, /全て|すべて|全組/, /切り捨|切捨|floor|商/],
  },
];
const ids = paths.map(item => item.id);
function candidates(value) { return value.current.techniques ?? []; }
function walk(flow, domain, choices) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, `${domain}/${choices.join('/')}: all answers are consumed`);
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

test('six new techniques are found from problem features only after the necessary conditions', async () => {
  const { flow } = await implementation;
  for (const item of paths) {
    const initial = walk(flow, item.domain, item.prefix);
    assert.equal(initial.graph.id, item.graph, `${item.id}: feature choices reach the applicability chart`);
    assert.equal(initial.current.id, item.guards[0]);
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard], `${item.id}: the next necessary property is checked`);
      assert(!candidates(value).includes(item.id));
    }
    const value = walk(flow, item.domain, [...item.prefix, ...Array(item.guards.length).fill('yes')]);
    assert(candidates(value).includes(item.id), `${item.id}: all properties select the intended technique`);
    const text = JSON.stringify(value.graph);
    for (const term of item.terms) assert.match(text, term, `${item.id}: applicability is explained`);
    assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${item.id}/`));
  }
  assert.equal(flow.entryGraphs.length, 15, 'new detailed charts remain under the existing fields');
});

test('every unsupported or unknown premise leads to further questions without asserting a new technique', async () => {
  const { flow } = await implementation;
  for (const item of paths) {
    for (let guard = 0; guard < item.guards.length; ++guard) for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert(ids.every(id => !candidates(value).includes(id)), `${item.id}/${item.guards[guard]}/${answer}: no unsupported conclusion`);
      assert.equal(value.current.type, 'question', `${item.id}/${answer}: a next question remains available`);
      assert.equal(value.graph.id, 'condition-check', `${item.id}/${answer}: the missing premise can be investigated`);
    }
  }
});

test('the pair-product and ratio selector offers distinct problem features and a next step for uncertainty', async () => {
  const { flow } = await implementation;
  const prefix = ['selected-elements', 'pair-product-ratio'];
  const selector = walk(flow, 'ranges', prefix);
  assert.equal(selector.graph.id, 'pair-product-ratio-goals');
  assert.equal(selector.current.type, 'question');
  assert.equal(selector.current.id, 'goal');
  const options = selector.current.options;
  for (const choice of ['product-rank', 'floor-total', 'unknown'])
    assert(options.some(option => option.id === choice), `${choice}: an explicit labeled feature choice`);
  for (const option of options) assert(option.label.length >= 2);
  const uncertain = walk(flow, 'ranges', [...prefix, 'unknown']);
  assert.equal(uncertain.graph.id, 'condition-check');
  assert.equal(uncertain.current.type, 'question');
  assert(ids.every(id => !candidates(uncertain).includes(id)));
});

test('question URLs and diagram-only URLs retain every new path and Back returns to the original field', async () => {
  const { flow, viewer } = await implementation;
  for (const item of paths) {
    const choices = [...item.prefix, ...Array(item.guards.length).fill('yes')];
    let state = replay(flow, item.domain, choices);
    assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
    for (let remaining = weight(state) + 1; ; --remaining) {
      assert(remaining > 0, `${item.id}: Back terminates`);
      assert.equal(flow.getFlowDomainId(state), item.domain);
      assert.deepEqual(flow.sanitizeState(state), state);
      const hash = flow.serializeFlowHash(state);
      assert.deepEqual(flow.parseFlowHash(hash), state, `${item.id}: question URL reloads`);
      assert.deepEqual(viewer.diagramState(state.graph, hash), state, `${item.id}: image page retains answers`);
      if (!weight(state)) break;
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state), `${item.id}: Back removes a canonical step`);
      state = previous;
    }
    assert.deepEqual(state, flow.initialState(item.domain));
    assert.deepEqual(flow.backFlowState(state), state);
  }
});

test('every new article has the full format, primary sources, one reusable implementation and confirmed example walks', async () => {
  const { flow } = await implementation;
  const [metadata, references] = await Promise.all([
    loadCollections(/^techniques-.*\.json$/),
    loadCollections(/^references-.*\.json$/),
  ]);
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  for (const id of ids) {
    const item = metadata.find(row => row.id === id);
    assert(item, `${id}: registered metadata`);
    assert.equal(item.kind, 'technique');
    assert.equal(item.status, 'reviewed');
    assert(item.aliases.some(alias => /[A-Za-z]/.test(alias)), `${id}: English searchable name`);
    const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
    for (const heading of ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'])
      assert.equal(article.split(`## ${heading}\n`).length - 1, 1, `${id}: one ${heading} section`);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, `${id}: one standalone C++ implementation`);
    assert(article.includes(`techniqueId="${id}"`), `${id}: confirmed examples are displayed`);
    for (const source of item.sources) assert(article.includes(source), `${id}: source is accessible from the article`);
    const examples = references.filter(row => row.techniqueId === id);
    assert(examples.length, `${id}: at least one confirmed original example`);
    for (const row of examples) {
      assert(['editorial', 'reference-solution', 'independent-analysis'].includes(row.verification));
      assert(row.evidence.length > 0);
      const record = walks.find(candidate => candidate.source === row.source && candidate.problemId === row.problemId && candidate.expectedTechniqueIds.includes(id));
      assert(record, `${id}/${row.source}/${row.problemId}: confirmed example has a root walk`);
      assert.equal(record.statementUrl, row.url);
      assert.equal(record.reviewStatus, 'verified');
      assert.equal(record.verificationKind, row.verification);
      assert(record.features.length >= 2);
      const value = walk(flow, record.entryGraphId, record.choices);
      assert(candidates(value).includes(id));
      assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
    }
  }
});

test('the six frequency and ranking problems preserve feature evidence and distinguish dated from undated archives', async () => {
  const features = JSON.parse(await readFile(path.join(site, 'data/frequency-rank-problem-features.json'), 'utf8'));
  const references = (await loadCollections(/^references-.*\.json$/)).filter(row => ids.includes(row.techniqueId));
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  assert.equal(features.length, 6);
  const actualPairs = [];
  for (const feature of features) {
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.cutoff, '2026-10-14');
    assert(feature.features.length >= 2);
    assert(feature.evidenceUrl.startsWith('https://'));
    for (const id of feature.techniqueIds) {
      actualPairs.push(`${feature.source}/${feature.problemId}/${id}`);
      const reference = references.find(row => row.source === feature.source && row.problemId === feature.problemId && row.techniqueId === id);
      assert(reference, `${id}: the feature evidence belongs to a confirmed mapping`);
      assert.equal(reference.url, feature.url);
      assert.equal(reference.verification, feature.verification);
      const record = walks.find(row => row.source === feature.source && row.problemId === feature.problemId && row.expectedTechniqueIds.includes(id));
      assert(record);
      assert.deepEqual(record.features, feature.features);
      if (feature.publicationDateStatus === 'undated-archive') {
        assert.equal(reference.cutoffVerification, 'undated-archive');
        assert.equal(record.cutoffVerification, 'undated-archive');
      } else {
        assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
        assert.match(feature.publicationDate, /^\d{4}-\d{2}-\d{2}$/);
        assert(feature.publicationDate <= feature.cutoff);
      }
    }
  }
  assert.deepEqual(actualPairs.sort(), references.map(row => `${row.source}/${row.problemId}/${row.techniqueId}`).sort());
});
