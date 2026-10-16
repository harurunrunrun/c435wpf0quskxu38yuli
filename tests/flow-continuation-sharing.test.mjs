import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frozen = JSON.parse(await readFile(path.join(site, 'tests/fixtures/flow-continuation-sharing.json'), 'utf8'));
const techniqueTitles = {};
for (const name of (await readdir(path.join(site, 'data'))).filter(name => /^techniques.*\.json$/.test(name))) {
  for (const item of JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))) techniqueTitles[item.id] = item.title;
}
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-continuation-sharing-'));
  await compileLocalModules(site, temporary);
  const [flow, viewer] = await Promise.all([
    import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  ]);
  return { flow, viewer };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Walk the frozen questions directly. Neither the current flow evaluator nor
// migration metadata determines which old prefixes or node values are checked.
function oldPrefixes(graph) {
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const prefixes = [];
  function visit(id, answers, active) {
    assert(!active.has(id), `${graph.id}: the frozen chart is acyclic`);
    const node = nodes.get(id);
    assert(node, `${graph.id}/${id}: frozen target exists`);
    prefixes.push({ answers, node });
    if (node.type !== 'question') return;
    const nextActive = new Set([...active, id]);
    for (const [answer, target] of Object.entries(node.answers)) visit(target, [...answers, answer], nextActive);
  }
  visit(graph.root, [], new Set());
  return prefixes;
}
const records = frozen.graphs.flatMap(graph => oldPrefixes(graph).map(prefix => ({ graph, ...prefix })));
const regroupedRoots = new Set(['shortest-path', 'tree-query', 'combinatorics']);

// Keep the former URL encoding independent of the current serializer.
function oldHash(graph, answers) {
  const short = { yes: 'y', no: 'n', unknown: 'u' };
  const steps = answers.map(answer => short[answer] ?? `c:${encodeURIComponent(answer)}`).join(',');
  return `#flow=${encodeURIComponent(graph)}&steps=${steps}`;
}
function label(record) { return `${record.graph.id}/${record.node.id}/${JSON.stringify(record.answers)}`; }
function rootWithoutChoices(node) {
  const { options, answers, ...rest } = node;
  return rest;
}
function assertFormerNode(current, record, description) {
  if (regroupedRoots.has(record.graph.id) && record.node.id === record.graph.root) {
    assert.deepEqual(rootWithoutChoices(current), rootWithoutChoices(record.node), `${description}: root changes only choices and targets`);
  } else if (record.graph.id === 'math-bits-digits' && record.node.id === record.graph.root) {
    // Vision adds one feature to this category root. Every former answer,
    // label, target, ordering and all other node fields remain frozen.
    const options = record.node.options.slice();
    options.splice(options.findIndex(option => option.id === 'unknown'), 0, {
      id: 'two-mark-distance-circuit',
      label: '二つの黒画素の距離を、画像を読む前に作った論理回路で判定する',
    });
    assert.deepEqual(current, { ...record.node, options,
      answers: { ...record.node.answers, 'two-mark-distance-circuit': 'two-mark-distance-circuit-route' } },
    `${description}: only the documented circuit feature is added`);
  } else {
    assert.deepEqual(current, record.node, `${description}: current node is unchanged in full`);
  }
}
function stateKey(state) {
  return JSON.stringify([state.graph, state.answers, (state.trail ?? []).map(context => [context.graph, context.answers])]);
}
function assertTrail(flow, state, description) {
  const contexts = [...(state.trail ?? []), { graph: state.graph, answers: state.answers }];
  for (let index = 0; index < contexts.length; index++) {
    const context = contexts[index];
    const graph = flow.graphs.find(graph => graph.id === context.graph);
    assert(graph, `${description}: canonical graph exists`);
    let node = graph.nodes.find(node => node.id === graph.root);
    for (const answer of context.answers) {
      assert.equal(node.type, 'question', `${description}: answers follow only questions`);
      assert(flow.getNodeOptions(node).some(option => option.id === answer), `${description}: canonical answer is selectable in its graph`);
      node = graph.nodes.find(candidate => candidate.id === node.answers[answer]);
      assert(node, `${description}: answer target exists`);
    }
    if (index === contexts.length - 1) continue;
    assert.equal(node.type, 'route', `${description}: history ends at a route`);
    assert.equal(node.graph, contexts[index + 1].graph, `${description}: history joins the next graph`);
    if (node.continuation === true) {
      assert.equal(flow.getGraph(node.graph).root, node.id, `${description}: continuation preserves the question id`);
    } else {
      const root = graph.nodes.find(candidate => candidate.id === graph.root);
      assert.equal(context.answers.length, 1, `${description}: category migration leaves directly from its root`);
      const answer = context.answers[0];
      assert.equal(root.answers[answer], node.id, `${description}: category root answer points to this route`);
      assert(Object.values(graph.legacyEntryChoices ?? {}).some(migration => migration.answer === answer && migration.graph === node.graph), `${description}: ordinary history route is an explicitly registered root category migration`);
    }
  }
}
function assertStable(flow, state, description) {
  assertTrail(flow, state, description);
  assert.deepEqual(flow.sanitizeState(state), state, `${description}: normalization is idempotent`);
  assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)), state, `${description}: canonical URL round trip`);
}

test('the frozen affected charts independently enumerate every old local answer prefix', async () => {
  const { flow } = await implementation;
  assert.equal(frozen.baselineGraphCount, 248);
  assert.equal(records.length, 834, 'every one of the original 834 answer prefixes remains checked');
  assert(frozen.graphs.length > 0, 'affected charts were frozen before extraction');
  assert.equal(new Set(frozen.graphs.map(graph => graph.id)).size, frozen.graphs.length);
  assert(flow.graphs.length > frozen.baselineGraphCount, 'continuations add detailed charts');
  for (const graph of frozen.graphs) {
    assert.equal(new Set(graph.nodes.map(node => node.id)).size, graph.nodes.length, `${graph.id}: unique frozen node ids`);
    assert(graph.nodes.some(node => node.id === graph.root), `${graph.id}: frozen root exists`);
    assert(flow.entryGraphs.some(entry => entry.id === graph.domain), `${graph.id}: original domain is recorded`);
    const prefixes = oldPrefixes(graph);
    const keys = new Set(prefixes.map(prefix => JSON.stringify(prefix.answers)));
    assert.equal(keys.size, prefixes.length, `${graph.id}: every local answer prefix occurs once`);
    const reached = new Set(prefixes.map(prefix => prefix.node.id));
    assert.deepEqual([...reached].sort(), graph.nodes.map(node => node.id).sort(), `${graph.id}: all frozen nodes are covered`);
    for (const prefix of prefixes) {
      for (const answer of Object.keys(prefix.node.answers ?? {})) {
        assert(keys.has(JSON.stringify([...prefix.answers, answer])), `${graph.id}/${prefix.node.id}: every old answer is covered`);
      }
    }
  }
});

test('later root regrouping forwards every frozen feature label and target exactly', async () => {
  const { flow } = await implementation;
  for (const old of frozen.graphs.filter(graph => regroupedRoots.has(graph.id))) {
    const graph = flow.getGraph(old.id);
    const root = graph.nodes.find(node => node.id === graph.root);
    const oldRoot = old.nodes.find(node => node.id === old.root);
    assert.deepEqual(rootWithoutChoices(root), rootWithoutChoices(oldRoot), `${old.id}: root identity, wording and applicability remain unchanged`);
    for (const option of flow.getNodeOptions(oldRoot)) {
      const migration = graph.legacyEntryChoices?.[option.id];
      if (!migration) {
        assert(flow.getNodeOptions(root).some(current => current.id === option.id && current.label === option.label), `${old.id}/${option.id}: retained feature label is exact`);
        assert.equal(root.answers[option.id], oldRoot.answers[option.id], `${old.id}/${option.id}: retained feature target is exact`);
        continue;
      }
      assert(flow.getNodeOptions(root).some(current => current.id === migration.answer), `${old.id}/${option.id}: new category is selectable`);
      const route = graph.nodes.find(node => node.id === root.answers[migration.answer]);
      assert.equal(route?.type, 'route', `${old.id}/${option.id}: category leaves through a route`);
      assert.equal(route.graph, migration.graph, `${old.id}/${option.id}: category destination agrees with migration`);
      const target = flow.getGraph(migration.graph);
      const categoryRoot = target.nodes.find(node => node.id === target.root);
      assert(flow.getNodeOptions(categoryRoot).some(current => current.id === option.id && current.label === option.label), `${old.id}/${option.id}: forwarded feature label is exact`);
      assert.equal(categoryRoot.answers[option.id], oldRoot.answers[option.id], `${old.id}/${option.id}: forwarded feature target is exact`);
    }
  }
});

test('all old local URLs preserve complete question, result and ordinary route data', async () => {
  const { flow, viewer } = await implementation;
  for (const record of records) {
    const description = label(record);
    const hash = oldHash(record.graph.id, record.answers);
    const state = flow.parseFlowHash(hash);
    assertFormerNode(flow.evaluateState(state).current, record, description);
    assert.deepEqual(flow.sanitizeState({ graph: record.graph.id, answers: record.answers }), state, `${description}: object and URL migration agree`);
    assert.deepEqual(viewer.diagramState(record.graph.id, hash), state, `${description}: former viewer URL preserves the local state`);
    assert.equal(flow.getFlowDomainId(state), record.graph.domain, `${description}: the originating domain is unchanged`);
    assertStable(flow, state, description);
    assert.deepEqual(flow.sanitizeState({ graph: record.graph.id, answers: [...record.answers, '__invalid_answer__', 'yes'] }), state, `${description}: invalid suffix is truncated`);
    if (record.node.type !== 'route') {
      const walked = flow.walkFromRoot(record.answers, record.graph.id);
      assert.equal(walked.consumed, record.answers.length, `${description}: original choices are consumed once`);
      assertFormerNode(walked.current, record, `${description}: root walking reaches the same complete node`);
    }
  }
});

test('every old local answer prefix backtracks through its normalized former prefixes to the original root', async () => {
  const { flow, viewer } = await implementation;
  for (const record of records) {
    const description = label(record);
    let state = flow.parseFlowHash(oldHash(record.graph.id, record.answers));
    const formerPrefixes = Array.from({ length: record.answers.length }, (_, index) => flow.parseFlowHash(oldHash(record.graph.id, record.answers.slice(0, record.answers.length - index - 1))));
    const weight = value => value.answers.length + (value.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
    let nextPrefix = 0;
    for (let remaining = weight(state) + 1; weight(state) > 0; remaining--) {
      assert(remaining > 0, `${description}: backtracking terminates`);
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state), `${description}: back removes a canonical history step`);
      assertStable(flow, previous, description);
      assert.equal(flow.getFlowDomainId(previous), record.graph.domain, `${description}: back preserves the domain`);
      assert.deepEqual(viewer.diagramState(previous.graph, flow.serializeFlowHash(previous)), previous, `${description}: backtracked viewer URL reloads`);
      if (nextPrefix < formerPrefixes.length && stateKey(previous) === stateKey(formerPrefixes[nextPrefix])) nextPrefix++;
      state = previous;
    }
    assert.equal(nextPrefix, formerPrefixes.length, `${description}: back visits every normalized former answer prefix in order`);
    assert.deepEqual(state, flow.initialState(record.graph.id), `${description}: back reaches the original chart root`);
    assert.deepEqual(flow.backFlowState(state), state, `${description}: root back is stable`);
  }
});

test('affected source diagrams contain fewer nodes and occupy less area after extraction', async () => {
  const { flow } = await implementation;
  for (const original of frozen.graphs) {
    const graph = flow.getGraph(original.id);
    assert.equal(graph.id, original.id, `${original.id}: original chart id is retained`);
    assert(graph.nodes.length < original.nodes.length, `${original.id}: the source chart has fewer nodes`);
    assert(Number.isFinite(original.width) && original.width > 0 && Number.isFinite(original.height) && original.height > 0, `${original.id}: original SVG dimensions are recorded`);
    const match = flow.renderFlowSvg(graph, '/flowchartcp/', techniqueTitles).match(/\bviewBox="([^"]+)"/);
    assert(match, `${original.id}: generated SVG has a viewBox`);
    const box = match[1].split(/\s+/).map(Number);
    assert(box.length === 4 && box.every(Number.isFinite), `${original.id}: valid current SVG dimensions`);
    assert(box[2] * box[3] < original.width * original.height, `${original.id}: the source SVG area shrinks`);
  }
});
