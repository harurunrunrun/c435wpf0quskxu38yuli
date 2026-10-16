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
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-ray-rank-avoidance-flow-'));
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
    domain: 'ranges',
    prefix: ['aggregate-goals', 'window', 'aggregate-values', 'second-maximum'],
    graph: 'subarray-second-maximum-conditions',
    guards: ['all-intervals', 'second', 'duplicates'],
    id: 'second-maximum-subarray-contribution',
    terms: [/全|すべて/, /二番目|2番目/, /重複|同値|同じ値/, /左右|左|右/],
  },
  {
    domain: 'ranges',
    prefix: ['aggregate-goals', 'static', 'occurrence-goals', 'frequency-equals'],
    graph: 'frequency-equals-value-conditions',
    guards: ['fixed', 'positive', 'all-queries'],
    id: 'frequency-equals-value-offline',
    terms: [/正整数/, /出現回数|頻度/, /左端/, /右端/],
  },
  {
    domain: 'grid-arrangements',
    prefix: ['movement-cycles', 'ray-moves'],
    graph: 'grid-ray-path-conditions',
    guards: ['directions', 'walls', 'count-moves'],
    id: 'grid-ray-direction-prefix',
    terms: [/右/, /下/, /斜|右下/, /壁|障害/],
  },
  {
    domain: 'math',
    prefix: ['counting-totals', 'count', 'place-constraints', 'inversions'],
    graph: 'permutation-inversion-count-conditions',
    guards: ['permutation', 'inversions', 'small-k'],
    id: 'permutation-inversion-window-dp',
    terms: [/順列/, /転倒/, /K|k/, /累積|窓|足し引き|右端の加算と左端の除去/],
  },
  {
    domain: 'graphs',
    prefix: ['directed-progress', 'forward-avoidance'],
    graph: 'forward-vertex-avoidance-conditions',
    guards: ['forward', 'independent', 'unit'],
    id: 'forward-dag-vertex-avoidance-intervals',
    terms: [/頂点/, /前|先|大きい/, /独立|元の|一つ|一頂点/, /1|単位/],
  },
  {
    domain: 'graphs',
    prefix: ['network-connection', 'connectivity', 'direction-goals', 'tree-reversals'],
    graph: 'tree-root-reversal-conditions',
    guards: ['tree', 'outward', 'independent-costs'],
    id: 'tree-root-reversal-costs',
    terms: [/木/, /根/, /反転|逆/, /費用|コスト/],
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
      const options = flow.getNodeOptions(value.current);
      for (const answer of ['yes', 'no', 'unknown']) {
        const option = options.find(candidate => candidate.id === answer);
        assert(option && option.label.length >= 2, `${item.id}/${value.current.id}/${answer}: a labeled applicability choice`);
      }
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
      const diagramUrl = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
      assert.equal(diagramUrl.pathname, `/flowchartcp/diagrams/${state.graph}/`);
      assert.equal(diagramUrl.hash, hash, `${item.id}: diagram URL shares the question history`);
      assert.deepEqual(viewer.diagramState(state.graph, diagramUrl.hash), state);
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

test('the six original problems preserve feature evidence and distinguish dated from undated archives', async () => {
  const features = JSON.parse(await readFile(path.join(site, 'data/ray-rank-avoidance-problem-features.json'), 'utf8'));
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
