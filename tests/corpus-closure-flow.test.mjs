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
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-corpus-closure-flow-'));
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
    domain: 'graphs',
    prefix: ['network-connection', 'steiner-terminals'],
    graph: 'steiner-terminal-conditions',
    guards: ['undirected', 'shared-cost', 'few-terminals'],
    id: 'steiner-terminal-subset-shortest',
    terms: [/指定|端点/, /共有|一度|一回/, /非負/, /少数|部分集合|10/],
  },
  {
    domain: 'graphs',
    prefix: ['network-connection', 'spanning-count'],
    graph: 'spanning-tree-count-conditions',
    guards: ['undirected', 'spanning-trees', 'modulus-size'],
    id: 'spanning-tree-laplacian-minor',
    terms: [/全域木/, /無向/, /多重|並行|同じ二頂点/, /素数|998244353/],
  },
  {
    domain: 'flow-matching',
    prefix: ['pair-goals', 'general-pairs'],
    graph: 'general-pair-maximum-conditions',
    guards: ['pair-edges', 'cardinality', 'cubic'],
    id: 'general-matching-blossom-contraction',
    terms: [/組数|本数|辺数/, /奇閉路|二部/, /無向/, /増加|縮約|Blossom/],
  },
  {
    domain: 'strings',
    prefix: ['comparison', 'common-subsequence-length'],
    graph: 'lcs-bit-length-conditions',
    guards: ['subsequence', 'unweighted-length', 'word-budget'],
    id: 'lcs-bit-parallel-length',
    terms: [/部分列/, /長さ/, /重み|文字/, /ビット|ワード|64/],
  },
  {
    domain: 'flow-matching',
    prefix: ['pair-goals', 'maximal-count'],
    graph: 'maximal-threshold-count-conditions',
    guards: ['threshold', 'maximal', 'distinct'],
    id: 'maximal-threshold-matching-sweep-dp',
    terms: [/極大/, /大小|以下|≦|≤/, /区別|識別/, /未使用|未対応/],
  },
  {
    domain: 'graphs',
    prefix: ['walk-goals', 'synchronous-factors'],
    graph: 'synchronous-product-distance-conditions',
    guards: ['undirected', 'simultaneous', 'size'],
    id: 'synchronous-product-parity-distance-sum',
    terms: [/同時/, /無向/, /偶奇|偶数|奇数/, /直積|積グラフ|組状態/],
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
    const diagram = flow.renderFlowSvg(value.graph);
    assert(diagram.includes(`/flowchartcp/techniques/${item.id}/`));
    const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    let answerCount = 0;
    for (const node of value.graph.nodes) if (node.type === 'question') {
      for (const option of flow.getNodeOptions(node)) {
        ++answerCount;
        assert(diagram.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`), `${item.id}: the graph answer is drawn`);
        assert(diagram.includes(`<title>${xml(option.label)}</title>`), `${item.id}: the drawn answer is labeled`);
      }
    }
    assert.equal((diagram.match(/class="flow-edge /g) ?? []).length, answerCount, `${item.id}: no extra diagram answers`);
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
  const diagrams = new Map();
  for (const item of paths) {
    const histories = [[...item.prefix, ...Array(item.guards.length).fill('yes')]];
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
      assert(diagram.includes(`data-node="${evaluation.current.id}"`), `${item.id}: the current position exists in the SVG`);
      for (const node of evaluation.path)
        assert(diagram.includes(`data-node="${node.id}"`), `${item.id}: every highlighted path node exists`);
      for (const edge of evaluation.edges)
        assert(diagram.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`), `${item.id}: every highlighted answer edge exists`);
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
  }
});

test('every new article has the full format, primary sources, one reusable implementation and confirmed example walks', async () => {
  const { flow } = await implementation;
  const [metadata, references] = await Promise.all([
    loadCollections(/^techniques-.*\.json$/),
    loadCollections(/^references-.*\.json$/),
  ]);
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  assert(metadata.filter(row => row.kind === 'technique').length >= 367 + ids.length, 'the previous 367 concrete techniques and all six additions remain registered');
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
  const features = JSON.parse(await readFile(path.join(site, 'data/corpus-closure-problem-features.json'), 'utf8'));
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
        if (feature.publicationDate !== undefined) {
          assert.match(feature.publicationDate, /^\d{4}-\d{2}-\d{2}$/);
          assert(feature.publicationDate <= feature.cutoff);
        } else {
          assert.match(feature.publicationMonth, /^\d{4}-(0[1-9]|1[0-2])$/);
          assert(feature.publicationMonth < feature.cutoff.slice(0, 7), `${feature.problemId}: a month before the cutoff month is sufficient without inventing a day`);
        }
      }
    }
  }
  assert.deepEqual(actualPairs.sort(), references.map(row => `${row.source}/${row.problemId}/${row.techniqueId}`).sort());
});
