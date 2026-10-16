import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const techniqueIds = [
  'mst-equal-weight-edge-classification',
  'strict-second-mst-two-maxima',
  'sequence-cut-reverse-split-merge',
  'dynamic-sequence-affine-sum',
  'range-stabilizing-successor',
  'global-replace-reverse-map',
];
const batch = new Set(techniqueIds);
const json = relative => readFile(path.join(site, relative), 'utf8').then(JSON.parse);
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-specific-expansion-'));
  const modules = path.join(temporary, 'modules');
  await compileLocalModules(site, modules);
  const [flow, content, walks] = await Promise.all([
    import(pathToFileURL(path.join(modules, 'flow.js')).href),
    import(pathToFileURL(path.join(modules, 'content.js')).href),
    json('data/problem-walks.json'),
  ]);
  return { flow, content, walks };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

function graphById(flow, id) {
  const graph = flow.graphs.find(graph => graph.id === id);
  assert(graph, `missing detailed chart: ${id}`);
  return graph;
}
function successfulWalk(flow, entry, choices, technique) {
  const result = flow.walkFromRoot(choices, entry);
  assert.equal(result.consumed, choices.length, `${entry}: all feature choices are consumed`);
  assert.equal(result.current.type, 'result');
  assert(result.current.techniques?.includes(technique), `${entry}: expected ${technique}`);
  assert(result.current.conditions?.length, `${technique}: a candidate keeps its applicability conditions`);
  return result;
}
function interactiveReplay(flow, entry, steps) {
  let state = flow.initialState(entry);
  const enterRoutes = () => {
    for (let remaining = flow.graphs.length + 1; flow.evaluateState(state).current.type === 'route'; remaining--) {
      assert(remaining > 0, 'interactive routing terminates');
      state = flow.enterFlowRoute(state);
    }
  };
  for (const step of steps) {
    enterRoutes();
    const current = flow.evaluateState(state).current;
    assert.equal(state.graph, step.graph);
    assert.equal(current.id, step.node);
    assert.equal(current.type, 'question');
    state = flow.answerState(state, step.answer);
  }
  enterRoutes();
  return state;
}

test('six new specific techniques are registered with implementations, aliases and checked usage evidence', async () => {
  const { content } = await implementation;
  for (const id of techniqueIds) {
    const technique = content.techniqueById.get(id);
    assert(technique, `${id}: metadata is registered in the site`);
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]{3}/.test(alias)), `${id}: English search alias`);
    assert(technique.sources.length > 0 && technique.sources.every(source => /^https:\/\//.test(source)));
    for (const prerequisite of technique.prerequisites)
      assert(content.techniqueById.has(prerequisite), `${id}: registered prerequisite ${prerequisite}`);
    const article = await readFile(path.join(site, 'src/content/docs/techniques', `${id}.mdx`), 'utf8');
    for (const section of ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'])
      assert(article.includes(`## ${section}\n`), `${id}: ${section}`);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, `${id}: one standalone C++ example`);
    assert(article.includes(`<TechniqueReferences techniqueId="${id}" />`));
    const references = content.references.filter(reference => reference.techniqueId === id);
    assert(references.length > 0, `${id}: original usage examples`);
    for (const reference of references) {
      assert(/^https:\/\//.test(reference.url));
      assert(/^https:\/\//.test(reference.editorialUrl));
      assert(reference.evidence?.trim(), `${id}/${reference.problemId}: classification evidence`);
      assert(['editorial', 'reference-solution', 'independent-analysis'].includes(reference.verification),
        `${id}/${reference.problemId}: tags alone do not count as verified usage`);
    }
  }
});

test('all new usage mappings replay from field roots and retain shared interactive history', async () => {
  const { flow, content, walks } = await implementation;
  const references = content.references.filter(reference => batch.has(reference.techniqueId));
  assert(references.length >= 10, 'the batch supplies at least ten checked problem-to-technique mappings');
  for (const reference of references) {
    const applicable = walks.filter(walk => walk.source === reference.source && walk.problemId === reference.problemId
      && walk.expectedTechniqueIds.includes(reference.techniqueId));
    assert(applicable.length, `${reference.source}/${reference.problemId}/${reference.techniqueId}: a recorded walk exists`);
    for (const walk of applicable) {
      assert.equal(walk.reviewStatus, 'verified');
      assert(walk.features.length > 0);
      const entry = walk.entryGraphId ?? 'ranges';
      assert(flow.entryGraphs.some(graph => graph.id === entry), 'walks begin at a field entry');
      const result = successfulWalk(flow, entry, walk.choices, reference.techniqueId);
      assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), walk.steps);
      const state = interactiveReplay(flow, entry, result.steps);
      assert.deepEqual(flow.evaluateState(state).current, result.current);
      assert.equal(flow.getFlowDomainId(state), entry);
      assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)), state);
      let previous = state;
      const weight = current => current.answers.length + (current.trail ?? []).reduce((sum, item) => sum + item.answers.length + 1, 0);
      for (let remaining = weight(state) + 1; weight(previous) > 0; remaining--) {
        assert(remaining > 0, 'back traversal terminates');
        const next = flow.backFlowState(previous);
        assert(weight(next) < weight(previous), 'back removes an answer or chart boundary');
        assert.equal(flow.getFlowDomainId(next), entry);
        previous = next;
      }
      assert.deepEqual(previous, flow.initialState(entry));
    }
  }
});

test('new techniques are reachable by problem features from graph, sequence and string fields', async () => {
  const { flow } = await implementation;
  const cases = [
    ['graphs', ['network-connection', 'mst-roles', 'classification', 'yes', 'yes'], 'mst-equal-weight-edge-classification'],
    ['graphs', ['network-connection', 'mst-roles', 'strict-second', 'yes', 'yes', 'yes'], 'strict-second-mst-two-maxima'],
    ['ranges', ['sequence-changes', 'dynamic-sequence', 'order-only', 'yes'], 'sequence-cut-reverse-split-merge'],
    ['ranges', ['sequence-changes', 'dynamic-sequence', 'affine-sum', 'yes'], 'dynamic-sequence-affine-sum'],
    ['ranges', ['sequence-changes', 'dynamic-sequence', 'global-replace', 'yes'], 'global-replace-reverse-map'],
    ['strings', ['changes', 'global-replace', 'global-replace', 'yes'], 'global-replace-reverse-map'],
    ['ranges', ['aggregate-goals', 'change', 'limited-value-changes', 'stabilizing', 'yes', 'yes', 'yes'], 'range-stabilizing-successor'],
  ];
  for (const [entry, choices, technique] of cases) successfulWalk(flow, entry, choices, technique);
  for (const [id, choices] of [
    ['mst-edge-roles', ['classification', 'strict-second', 'unknown']],
    ['sequence-order-updates', ['order-only', 'affine-sum', 'global-replace', 'unknown']],
  ]) {
    const graph = graphById(flow, id), root = graph.nodes.find(node => node.id === graph.root);
    assert.equal(root.type, 'question');
    const options = flow.getNodeOptions(root);
    for (const choice of choices) assert(options.some(option => option.id === choice), `${id}: ${choice}`);
    for (const option of options)
      assert.doesNotMatch(option.label, /Treap|AVL|Kruskal|クラスカル|Union.?Find|セグメント木|ダブリング|後継DSU/i,
        `${id}: readers select problem features before algorithms`);
  }
});

test('no and unknown at every applicability guard keep the specialized candidate unselected', async () => {
  const { flow } = await implementation;
  const checks = [
    ['mst-edge-classification-conditions', []],
    ['mst-edge-classification-conditions', ['yes']],
    ['strict-second-mst-conditions', []],
    ['strict-second-mst-conditions', ['yes']],
    ['strict-second-mst-conditions', ['yes', 'yes']],
    ['sequence-order-updates', ['order-only']],
    ['sequence-order-updates', ['affine-sum']],
    ['sequence-order-updates', ['global-replace']],
    ['range-stabilizing-updates', []],
    ['range-stabilizing-updates', ['yes']],
    ['range-stabilizing-updates', ['yes', 'yes']],
  ];
  for (const [graph, prefix] of checks) {
    graphById(flow, graph);
    const waiting = flow.walkFromRoot(prefix, graph);
    assert.equal(waiting.consumed, prefix.length);
    assert.equal(waiting.current.type, 'question', `${graph}/${prefix.join('/')}: applicability check`);
    for (const answer of ['no', 'unknown']) {
      assert(flow.getNodeOptions(waiting.current).some(option => option.id === answer));
      const result = flow.walkFromRoot([...prefix, answer], graph);
      assert.equal(result.consumed, prefix.length + 1);
      assert.equal(result.graph.id, 'condition-check', `${graph}/${prefix.join('/')}/${answer}: unresolved conditions remain explicit`);
      assert.equal(result.current.type, 'question');
      assert(!(result.current.techniques ?? []).some(id => batch.has(id)));
    }
  }
  for (const graph of ['mst-edge-roles', 'sequence-order-updates']) {
    const result = flow.walkFromRoot(['unknown'], graph);
    assert.equal(result.graph.id, 'condition-check');
    assert.equal(result.current.type, 'question');
  }
});
