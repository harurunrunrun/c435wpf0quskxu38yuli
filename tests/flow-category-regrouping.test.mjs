import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frozen = JSON.parse(await readFile(path.join(site, 'tests/fixtures/flow-category-regrouping.json'), 'utf8'));
const techniqueTitles = {};
for (const name of (await readdir(path.join(site, 'data'))).filter(name => /^techniques.*\.json$/.test(name))) {
  for (const item of JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))) techniqueTitles[item.id] = item.title;
}
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-category-regrouping-'));
  await compileLocalModules(site, temporary);
  const [flow, viewer] = await Promise.all([
    import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  ]);
  return { flow, viewer };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Enumerate the frozen questions, never the current migration metadata. This
// checks every former answer, including branches absent from the problem list.
function oldPrefixes(graph) {
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const prefixes = [];
  function visit(id, answers, active) {
    assert(!active.has(id), `${graph.id}: frozen graph is acyclic`);
    const node = nodes.get(id);
    assert(node, `${graph.id}/${id}: frozen answer target exists`);
    prefixes.push({ graph, answers, node });
    if (node.type !== 'question') return;
    const nextActive = new Set([...active, id]);
    for (const [answer, target] of Object.entries(node.answers)) visit(target, [...answers, answer], nextActive);
  }
  visit(graph.root, [], new Set());
  return prefixes;
}
const prefixes = frozen.graphs.flatMap(oldPrefixes);

// Preserve the former URL format independently of the current serializer.
function oldHash(state) {
  const short = { yes: 'y', no: 'n', unknown: 'u' };
  const steps = state.answers.map(answer => short[answer] ?? `c:${encodeURIComponent(answer)}`).join(',');
  return `#flow=${encodeURIComponent(state.graph)}&steps=${steps}${state.trail?.length ? `&trail=${encodeURIComponent(JSON.stringify(state.trail))}` : ''}`;
}
function label(record) {
  return record.problemId ? `${record.source}/${record.problemId}` : `${record.graph.id}/${record.node.id}/${JSON.stringify(record.answers)}`;
}
function rootWithoutChoices(node) {
  const { options, answers, ...rest } = node;
  return rest;
}
function stateKey(state) {
  return JSON.stringify([state.graph, state.answers, (state.trail ?? []).map(context => [context.graph, context.answers])]);
}
function assertCanonicalTrail(flow, state, description) {
  const contexts = [...(state.trail ?? []), { graph: state.graph, answers: state.answers }];
  for (let index = 0; index < contexts.length; index++) {
    const context = contexts[index];
    const graph = flow.graphs.find(graph => graph.id === context.graph);
    assert(graph, `${description}: history graph exists`);
    let node = graph.nodes.find(node => node.id === graph.root);
    for (const answer of context.answers) {
      assert.equal(node.type, 'question', `${description}: answers follow questions`);
      assert(flow.getNodeOptions(node).some(option => option.id === answer), `${description}: canonical answer is selectable`);
      node = graph.nodes.find(candidate => candidate.id === node.answers[answer]);
      assert(node, `${description}: canonical target exists`);
    }
    if (index < contexts.length - 1) {
      assert.equal(node.type, 'route', `${description}: history ends at a route`);
      assert.equal(node.graph, contexts[index + 1].graph, `${description}: history is contiguous`);
    }
  }
}
function assertStable(flow, viewer, state, description) {
  assertCanonicalTrail(flow, state, description);
  assert.deepEqual(flow.sanitizeState(state), state, `${description}: normalization is idempotent`);
  const hash = flow.serializeFlowHash(state);
  assert.deepEqual(flow.parseFlowHash(hash), state, `${description}: canonical shared URL reloads`);
  assert.deepEqual(viewer.diagramState(state.graph, hash), state, `${description}: canonical viewer URL reloads`);
}
function assertBackTo(flow, viewer, state, graph, domain, description, formerPrefixes = []) {
  const weight = value => value.answers.length + (value.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
  let nextPrefix = 0;
  for (let remaining = weight(state) + 1; weight(state) > 0; remaining--) {
    assert(remaining > 0, `${description}: backtracking terminates`);
    const previous = flow.backFlowState(state);
    assert(weight(previous) < weight(state), `${description}: back removes a canonical history step`);
    assert.equal(flow.getFlowDomainId(previous), domain, `${description}: back preserves the domain`);
    assertStable(flow, viewer, previous, description);
    if (nextPrefix < formerPrefixes.length && stateKey(previous) === stateKey(formerPrefixes[nextPrefix])) nextPrefix++;
    state = previous;
  }
  assert.equal(nextPrefix, formerPrefixes.length, `${description}: back visits every former answer prefix in order`);
  assert.deepEqual(state, flow.initialState(graph), `${description}: back reaches the original root`);
  assert.deepEqual(flow.backFlowState(state), state, `${description}: root back is stable`);
}

test('frozen affected charts cover all former nodes and every old answer prefix', () => {
  assert.equal(frozen.version, 1);
  assert.equal(frozen.baselineGraphCount, 258);
  assert.equal(frozen.baselineWalkCount, 404);
  assert.equal(frozen.completedWalks.length, 404);
  assert(frozen.graphs.length > 0, 'affected graphs are independently frozen');
  assert.equal(new Set(frozen.graphs.map(graph => graph.id)).size, frozen.graphs.length);
  for (const graph of frozen.graphs) {
    const records = prefixes.filter(record => record.graph.id === graph.id);
    const keys = new Set(records.map(record => JSON.stringify(record.answers)));
    assert.equal(keys.size, records.length, `${graph.id}: each old prefix occurs once`);
    assert.deepEqual([...new Set(records.map(record => record.node.id))].sort(), graph.nodes.map(node => node.id).sort(), `${graph.id}: every old node is reached`);
    for (const record of records) {
      for (const answer of Object.keys(record.node.answers ?? {})) {
        assert(keys.has(JSON.stringify([...record.answers, answer])), `${label(record)}: every old answer is covered`);
      }
    }
  }
});

test('all former shared prefixes preserve questions, conditions, candidates and ordinary routes', async () => {
  const { flow, viewer } = await implementation;
  for (const record of prefixes) {
    const description = label(record);
    const original = { graph: record.graph.id, answers: record.answers };
    const hash = oldHash(original);
    const state = flow.parseFlowHash(hash);
    const current = flow.evaluateState(state).current;
    if (record.answers.length) {
      assert.deepEqual(current, record.node, `${description}: nonroot node is unchanged in full`);
    } else {
      assert.equal(state.graph, record.graph.id, `${description}: an unanswered old URL stays at its original root`);
      assert.deepEqual(rootWithoutChoices(current), rootWithoutChoices(record.node), `${description}: only root choices are regrouped`);
    }
    assert.equal(flow.getFlowDomainId(state), record.graph.domain, `${description}: original domain`);
    assert.deepEqual(flow.sanitizeState(original), state, `${description}: object and URL migration agree`);
    assert.deepEqual(viewer.diagramState(record.graph.id, hash), state, `${description}: former viewer URL preserves the state`);
    assertStable(flow, viewer, state, description);
    assert.deepEqual(flow.sanitizeState({ ...original, answers: [...original.answers, '__invalid_answer__', 'yes'] }), state, `${description}: invalid suffix is truncated`);
    if (record.answers.length && record.node.type !== 'route') {
      const walk = flow.walkFromRoot(record.answers, record.graph.id);
      assert.equal(walk.consumed, record.answers.length, `${description}: former answers are consumed once`);
      assert.deepEqual(walk.current, record.node, `${description}: old root walk reaches the same complete node`);
    }
    const formerPrefixes = Array.from({ length: record.answers.length }, (_, index) => flow.parseFlowHash(oldHash({
      graph: record.graph.id, answers: record.answers.slice(0, record.answers.length - index - 1),
    })));
    assertBackTo(flow, viewer, state, record.graph.id, record.graph.domain, description, formerPrefixes);
  }
});

test('all 404 completed problem URLs preserve complete results, domains and usable history', async () => {
  const { flow, viewer } = await implementation;
  for (const record of frozen.completedWalks) {
    const description = label(record);
    assert.equal(record.expected.type, 'result', `${description}: completed frozen walk ends at a result`);
    const hash = oldHash(record.state);
    const state = flow.parseFlowHash(hash);
    assert.deepEqual(flow.evaluateState(state).current, record.expected, `${description}: complete result, conditions and candidates are unchanged`);
    for (const id of record.expectedTechniqueIds) assert(record.expected.techniques.includes(id), `${description}: listed technique belongs to the frozen result`);
    assert.equal(flow.getFlowDomainId(state), record.domain, `${description}: originating field is unchanged`);
    assert.deepEqual(flow.sanitizeState(record.state), state, `${description}: object and URL migration agree`);
    assert.deepEqual(viewer.diagramState(record.state.graph, hash), state, `${description}: original viewer URL reloads`);
    assertStable(flow, viewer, state, description);
    const choices = [...(record.state.trail ?? []), record.state].flatMap(context => context.answers);
    assert.deepEqual(choices, record.choices, `${description}: frozen completed state contains exactly its former choices`);
    const walk = flow.walkFromRoot(choices, record.domain);
    assert.equal(walk.consumed, choices.length, `${description}: all former problem choices are consumed`);
    assert.deepEqual(walk.current, record.expected, `${description}: former root walk reaches the same complete result`);
    assertBackTo(flow, viewer, state, record.domain, record.domain, description);
  }
});

test('regrouped roots expose at most six concrete categories and preserve every former choice label', async () => {
  const { flow } = await implementation;
  assert.equal(flow.entryGraphs.length, 15, 'the original fifteen fields remain the entry points');
  for (const old of frozen.graphs) {
    const graph = flow.getGraph(old.id);
    const root = graph.nodes.find(node => node.id === graph.root);
    const oldRoot = old.nodes.find(node => node.id === old.root);
    const options = flow.getNodeOptions(root);
    assert(options.length < flow.getNodeOptions(oldRoot).length, `${old.id}: root has fewer choices`);
    assert(options.length <= 7 && options.some(option => option.id === 'unknown'), `${old.id}: at most six categories plus unknown`);
    for (const oldOption of flow.getNodeOptions(oldRoot)) {
      const migration = graph.legacyEntryChoices?.[oldOption.id];
      if (!migration) {
        assert(options.some(option => option.id === oldOption.id && option.label === oldOption.label), `${old.id}/${oldOption.id}: retained original choice label`);
        continue;
      }
      const route = graph.nodes.find(node => node.id === root.answers[migration.answer]);
      assert.equal(route.type, 'route', `${old.id}/${oldOption.id}: category is an explicit route`);
      assert.equal(route.graph, migration.graph, `${old.id}/${oldOption.id}: category route matches migration`);
      const target = flow.getGraph(migration.graph);
      const categoryRoot = target.nodes.find(node => node.id === target.root);
      assert(flow.getNodeOptions(categoryRoot).some(option => option.id === oldOption.id && option.label === oldOption.label), `${old.id}/${oldOption.id}: category retains the original feature wording`);
      assert.equal(flow.getFlowDomainId(flow.initialState(target.id)), old.domain, `${old.id}/${oldOption.id}: category belongs to the original field`);
    }
  }
});

test('regrouped source diagrams contain fewer nodes and occupy less area', async () => {
  const { flow } = await implementation;
  for (const old of frozen.graphs) {
    const graph = flow.getGraph(old.id);
    assert.equal(graph.id, old.id, `${old.id}: original chart URL remains valid`);
    assert(graph.nodes.length < old.nodes.length, `${old.id}: source chart has fewer nodes`);
    assert(Number.isFinite(old.width) && old.width > 0 && Number.isFinite(old.height) && old.height > 0, `${old.id}: original dimensions are frozen`);
    const match = flow.renderFlowSvg(graph, '/flowchartcp/', techniqueTitles).match(/\bviewBox="([^"]+)"/);
    assert(match, `${old.id}: generated SVG has a viewBox`);
    const box = match[1].split(/\s+/).map(Number);
    assert(box.length === 4 && box.every(Number.isFinite), `${old.id}: valid SVG dimensions`);
    assert(box[2] < old.width, `${old.id}: root SVG is narrower`);
    assert(box[2] * box[3] < old.width * old.height, `${old.id}: source SVG area shrinks`);
  }
});
