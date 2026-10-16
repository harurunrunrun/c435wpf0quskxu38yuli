import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frozen = JSON.parse(await readFile(path.join(site, 'tests/fixtures/grid-arrangements-before-frontier.json'), 'utf8'));
const forestId = 'dynamic-forest-path-aggregate';
const frontierId = 'frontier-single-cycle';
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-forest-frontier-flow-'));
  await compileLocalModules(site, temporary);
  const [flow, viewer] = await Promise.all([
    import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  ]);
  return { flow, viewer };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Traverse only the frozen pre-regrouping graph, independently of the current
// branch data, migration table, and examples. Ordinary route nodes end a local
// prefix; their entire original route object is also an expected result.
function oldPrefixes(graph) {
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const records = [];
  function visit(id, answers, ancestors) {
    assert(!ancestors.has(id), `${graph.id}: frozen graph has no local cycle`);
    const node = nodes.get(id);
    assert(node, `${graph.id}/${id}: frozen answer has a target`);
    records.push({ answers, node });
    if (node.type !== 'question') return;
    for (const [answer, target] of Object.entries(node.answers))
      visit(target, [...answers, answer], new Set([...ancestors, id]));
  }
  visit(graph.root, [], new Set());
  return records;
}
const prefixes = oldPrefixes(frozen);
function oldHash(state) {
  const short = { yes: 'y', no: 'n', unknown: 'u' };
  const steps = state.answers.map(answer => short[answer] ?? `c:${encodeURIComponent(answer)}`).join(',');
  return `#flow=${encodeURIComponent(state.graph)}&steps=${steps}${state.trail?.length ? `&trail=${encodeURIComponent(JSON.stringify(state.trail))}` : ''}`;
}
function withoutChoices(node) { const { answers, options, ...rest } = node; return rest; }
function key(state) { return JSON.stringify([state.graph, state.answers, (state.trail ?? []).map(context => [context.graph, context.answers])]); }
function weight(state) { return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0); }
function assertFormerNode(current, record, description) {
  if (record.node.id === frozen.root) {
    assert.deepEqual(withoutChoices(current), withoutChoices(record.node), `${description}: only root choices may change`);
  } else {
    assert.deepEqual(current, record.node, `${description}: complete original node is preserved`);
  }
}
function assertCanonicalTrail(flow, state, description) {
  const contexts = [...(state.trail ?? []), { graph: state.graph, answers: state.answers }];
  for (let index = 0; index < contexts.length; ++index) {
    const context = contexts[index];
    const graph = flow.getGraph(context.graph);
    let node = graph.nodes.find(node => node.id === graph.root);
    for (const answer of context.answers) {
      assert.equal(node.type, 'question', `${description}: answers belong to actual questions`);
      assert(flow.getNodeOptions(node).some(option => option.id === answer), `${description}: canonical answer remains selectable`);
      node = graph.nodes.find(candidate => candidate.id === node.answers[answer]);
      assert(node, `${description}: canonical answer has a target`);
    }
    if (index < contexts.length - 1) {
      assert.equal(node.type, 'route', `${description}: context ends at a route`);
      assert.equal(node.graph, contexts[index + 1].graph, `${description}: history is contiguous`);
    }
  }
}
function assertStable(flow, viewer, state, description) {
  assertCanonicalTrail(flow, state, description);
  assert.deepEqual(flow.sanitizeState(state), state, `${description}: migration is idempotent`);
  const hash = flow.serializeFlowHash(state);
  assert.deepEqual(flow.parseFlowHash(hash), state, `${description}: current shared URL reloads`);
  assert.deepEqual(viewer.diagramState(state.graph, hash), state, `${description}: current diagram URL reloads`);
}
function walk(flow, domain, choices) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, `${domain}/${choices.join('/')}: every choice is consumed`);
  return value;
}
function candidates(value) { return value.current.techniques ?? []; }
function replay(flow, domain, choices) {
  let state = flow.initialState(domain);
  for (const answer of choices) {
    while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
    state = flow.answerState(state, answer);
  }
  while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
  return state;
}

test('the frozen grid chart independently covers all 20 former nodes and 37 answer prefixes', () => {
  assert.equal(frozen.id, 'grid-arrangements');
  assert.equal(frozen.entry, true);
  assert.equal(frozen.nodes.length, 20);
  assert.equal(frozen.legacyEntryChoices, undefined, 'the fixture predates the first grid category migration');
  assert.equal(prefixes.length, 37);
  const covered = new Set(prefixes.map(record => record.node.id));
  assert.deepEqual([...covered].sort(), frozen.nodes.map(node => node.id).sort());
  const answerPrefixes = new Set(prefixes.map(record => JSON.stringify(record.answers)));
  assert.equal(answerPrefixes.size, prefixes.length);
  for (const record of prefixes) for (const answer of Object.keys(record.node.answers ?? {}))
    assert(answerPrefixes.has(JSON.stringify([...record.answers, answer])), `${record.node.id}/${answer}: old edge is covered`);
});

test('grid feature categories retain original metadata, full nonroot nodes, and every original label and target', async () => {
  const { flow } = await implementation;
  const graph = flow.getGraph(frozen.id);
  const { nodes: oldNodes, ...oldMetadata } = frozen;
  const { nodes: newNodes, legacyEntryChoices, ...newMetadata } = graph;
  assert.deepEqual(newMetadata, oldMetadata);
  const root = newNodes.find(node => node.id === graph.root);
  const oldRoot = oldNodes.find(node => node.id === frozen.root);
  assert.deepEqual(withoutChoices(root), withoutChoices(oldRoot));
  assert.deepEqual(flow.getNodeOptions(root).map(option => option.id), ['pairing-cover', 'movement-cycles', 'color-numbers', 'unknown']);
  const descendants = new Map();
  const remaining = [graph.id];
  while (remaining.length) {
    const id = remaining.pop();
    if (descendants.has(id)) continue;
    const child = flow.getGraph(id);
    descendants.set(id, child);
    for (const node of child.nodes) if (node.type === 'route') remaining.push(node.graph);
  }
  for (const oldNode of oldNodes.filter(node => node.id !== frozen.root)) {
    const copies = [...descendants.values()].flatMap(child => child.nodes.filter(node => node.id === oldNode.id));
    assert(copies.some(node => isDeepStrictEqual(node, oldNode)), `${oldNode.id}: complete node survives in a reachable chart`);
  }
  for (const option of flow.getNodeOptions(oldRoot)) {
    const mapping = legacyEntryChoices?.[option.id];
    let targetRoot = root;
    if (mapping) {
      const route = newNodes.find(node => node.id === root.answers[mapping.answer]);
      assert.equal(route.type, 'route');
      assert.equal(route.graph, mapping.graph);
      const category = flow.getGraph(mapping.graph);
      targetRoot = category.nodes.find(node => node.id === category.root);
      assert.equal(flow.getFlowDomainId(flow.initialState(category.id)), frozen.id);
    }
    assert(flow.getNodeOptions(targetRoot).some(candidate => candidate.id === option.id && candidate.label === option.label), `${option.id}: original feature label remains selectable`);
    assert.equal(targetRoot.answers[option.id], oldRoot.answers[option.id], `${option.id}: original target is unchanged`);
  }
  assert.equal(legacyEntryChoices?.unknown, undefined, 'the unknown choice stays at the original root');
  assert.equal(root.answers.unknown, 'check');
  assert.deepEqual(newNodes.find(node => node.id === 'check'), oldNodes.find(node => node.id === 'check'));
  assert.equal(flow.entryGraphs.length, 15);
});

test('every former grid prefix preserves full state through old URLs, objects, diagram URLs and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  for (const record of prefixes) {
    const description = `${frozen.id}/${record.answers.join('/') || '<root>'}`;
    const original = { graph: frozen.id, answers: record.answers };
    const hash = oldHash(original);
    let state = flow.parseFlowHash(hash);
    assertFormerNode(flow.evaluateState(state).current, record, description);
    assert.equal(flow.getFlowDomainId(state), frozen.id, `${description}: originating field is preserved`);
    assert.deepEqual(flow.sanitizeState(original), state, `${description}: old object migration agrees`);
    assert.deepEqual(viewer.diagramState(frozen.id, hash), state, `${description}: old diagram URL agrees`);
    assert.deepEqual(flow.sanitizeState({ ...original, answers: [...record.answers, '__invalid__', 'yes'] }), state, `${description}: invalid answer suffix is truncated`);
    assertStable(flow, viewer, state, description);
    if (record.node.type !== 'route') assertFormerNode(walk(flow, frozen.id, record.answers).current, record, `${description}: old root walk`);

    const formerPrefixes = Array.from({ length: record.answers.length }, (_, index) =>
      flow.parseFlowHash(oldHash({ graph: frozen.id, answers: record.answers.slice(0, record.answers.length - index - 1) })));
    let nextPrefix = 0;
    for (let remainingSteps = weight(state) + 1; weight(state); --remainingSteps) {
      assert(remainingSteps > 0, `${description}: Back terminates`);
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state), `${description}: Back removes a canonical step`);
      assert.equal(flow.getFlowDomainId(previous), frozen.id, `${description}: Back preserves the field`);
      assertStable(flow, viewer, previous, description);
      if (nextPrefix < formerPrefixes.length && key(previous) === key(formerPrefixes[nextPrefix])) ++nextPrefix;
      state = previous;
    }
    assert.equal(nextPrefix, formerPrefixes.length, `${description}: Back visits every normalized former prefix in order`);
    assert.deepEqual(state, flow.initialState(frozen.id), `${description}: Back reaches the original grid root`);
    assert.deepEqual(flow.backFlowState(state), state);
  }
});

const forestPrefixes = [
  ['rooted-tree-goals', 'tree-range', 'changing-forest'],
  ['network-connection', 'connectivity', 'forest-path-values'],
];
const cyclePrefix = ['movement-cycles', 'single-cycle'];

test('changing-tree and changing-connectivity features reach the forest technique with explicit applicability guards', async () => {
  const { flow, viewer } = await implementation;
  for (const prefix of forestPrefixes) for (const kind of ['commutative', 'ordered']) {
    const choices = [...prefix, 'yes', kind, 'yes'];
    const value = walk(flow, 'graphs', choices);
    assert(candidates(value).includes(forestId));
    const conditions = value.current.conditions.join(' ');
    assert.match(conditions, /森/);
    assert.match(conditions, /閉路.*作らず/);
    assert.match(conditions, /結合的.*単位元/);
    assert.match(conditions, /要約の大きさ.*定数/);
    assert.match(conditions, /正順.*逆順/);
    assert.match(conditions, /一点.*部分木/);
    assert.match(conditions, /償却 O\(log N\)/);
    assert.match(conditions, /最悪一回.*保証.*異な/);
    const state = replay(flow, 'graphs', choices);
    assert.deepEqual(flow.evaluateState(state).current, value.current);
    assert.equal(flow.getFlowDomainId(state), 'graphs');
    assertStable(flow, viewer, state, choices.join('/'));
    assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${forestId}/`));
  }
  for (const prefix of forestPrefixes) {
    for (const answer of ['no', 'unknown']) {
      assert(!candidates(walk(flow, 'graphs', [...prefix, answer])).includes(forestId), `${prefix}/${answer}: an unproved forest cannot select the technique`);
      for (const kind of ['commutative', 'ordered']) {
        const value = walk(flow, 'graphs', [...prefix, 'yes', kind, answer]);
        assert(!candidates(value).includes(forestId), `${kind}/${answer}: missing combine or reversal cannot select the technique`);
        if (answer === 'unknown') assert.equal(value.current.id, 'check');
      }
    }
    assert(!candidates(walk(flow, 'graphs', [...prefix, 'yes', 'other'])).includes(forestId), 'unsupported subtree/bulk updates cannot select the implementation');
    assert.equal(walk(flow, 'graphs', [...prefix, 'yes', 'unknown']).current.id, 'check');
  }
  const article = await readFile(path.join(site, 'src/content/docs/techniques', forestId + '.mdx'), 'utf8');
  assert.match(article, /long long.*収まる/);
  assert.match(article, /交換法則は不要/);
  assert.match(article, /逆関数は必要ありません/);
});

test('single-cycle grid counting requires small width, endpoint connectivity and final-only closure', async () => {
  const { flow, viewer } = await implementation;
  const choices = [...cyclePrefix, 'yes', 'yes', 'yes', 'yes'];
  const value = walk(flow, 'grid-arrangements', choices);
  assert(candidates(value).includes(frontierId));
  const conditions = value.current.conditions.join(' ');
  assert.match(conditions, /次数を 2.*閉路を一つ/);
  assert.match(conditions, /行末.*境界.*ずらす/);
  assert.match(conditions, /正規化.*途中.*閉路.*許さない/);
  assert.match(conditions, /幅.*ビット.*上限/);
  assert.match(conditions, /多倍長整数/);
  const state = replay(flow, 'grid-arrangements', choices);
  assert.deepEqual(flow.evaluateState(state).current, value.current);
  assert.equal(flow.getFlowDomainId(state), 'grid-arrangements');
  assertStable(flow, viewer, state, 'single cycle');
  assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${frontierId}/`));
  for (let guard = 0; guard < 4; ++guard) for (const answer of ['no', 'unknown']) {
    const rejected = walk(flow, 'grid-arrangements', [...cyclePrefix, ...Array(guard).fill('yes'), answer]);
    assert(!candidates(rejected).includes(frontierId), `guard ${guard}/${answer}: missing properties cannot select the technique`);
    if (answer === 'unknown') assert.equal(rejected.current.id, 'check');
  }
  const width = walk(flow, 'grid-arrangements', [...cyclePrefix, 'yes']).current;
  assert.equal(width.id, 'width');
  assert.match(width.title, /短い辺.*幅/);
  assert.match(width.explanation, /転置/);
  const closing = walk(flow, 'grid-arrangements', [...cyclePrefix, 'yes', 'yes', 'yes']).current;
  assert.equal(closing.id, 'closing');
  assert.match(closing.title, /最後.*使用マス.*境界.*空/);
  assert.match(closing.explanation, /右下とは限りません/);
});

test('both forest variants and the single-cycle example have reviewed evidence, canonical root walks and article links', async () => {
  const { flow } = await implementation;
  const files = await readdir(path.join(site, 'data'));
  const load = async expression => (await Promise.all(files.filter(name => expression.test(name)).map(async name =>
    JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))))).flat();
  const metadata = await load(/^techniques.*\.json$/);
  const references = await load(/^references.*\.json$/);
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  const expectedExamples = [
    [forestId, 'Library Checker', 'dynamic_tree_vertex_add_path_sum'],
    [forestId, 'Library Checker', 'dynamic_tree_vertex_set_path_composite'],
    [frontierId, 'Timus', '1519'],
  ];
  for (const id of [forestId, frontierId]) {
    const technique = metadata.find(item => item.id === id);
    assert(technique, `${id}: technique metadata exists`);
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)), `${id}: English search name exists`);
    assert(technique.sources.length > 0);
  }
  for (const [id, source, problemId] of expectedExamples) {
    const reference = references.find(item => item.techniqueId === id && item.source === source && item.problemId === problemId);
    assert(reference, `${source}/${problemId}: original example exists`);
    assert(['reference-solution', 'independent-analysis'].includes(reference.verification));
    assert(reference.evidence.length > 0 && reference.verificationNotes.length > 0);
    const record = walks.find(item => item.statementUrl === reference.url && item.expectedTechniqueIds.includes(id));
    assert(record, `${source}/${problemId}: example has a root walk`);
    assert.equal(record.reviewStatus, 'verified');
    assert.equal(record.verificationKind, reference.verification);
    assert(record.features.length >= 2);
    assert.equal(record.cutoffVerification, 'undated-archive', 'undated originals are not asserted to predate the cutoff');
    const value = walk(flow, record.entryGraphId, record.choices);
    assert(candidates(value).includes(id));
    assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps, 'saved example steps are canonical');
    assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${id}/`));
  }
});
