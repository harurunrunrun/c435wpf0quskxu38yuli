import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frozen = JSON.parse(await readFile(path.join(site, 'tests/fixtures/flow-string-graph-regrouping.json'), 'utf8'));
const techniqueTitles = {};
for (const name of (await readdir(path.join(site, 'data'))).filter(name => /^techniques.*\.json$/.test(name))) {
  for (const item of JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))) techniqueTitles[item.id] = item.title;
}
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-string-graph-regrouping-'));
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
const oldGraphIds = new Set(frozen.graphs.map(graph => graph.id));

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
function regroupedQuestion(record) {
  return record.node.type === 'question' && (record.node.id === record.graph.root || record.graph.regroupedQuestionIds?.includes(record.node.id));
}
function assertFormerNode(current, record, description) {
  if (regroupedQuestion(record)) {
    assert.deepEqual(rootWithoutChoices(current), rootWithoutChoices(record.node), `${description}: regrouped question changes only choices and targets`);
  } else {
    assert.deepEqual(current, record.node, `${description}: nonroot node is unchanged in full`);
  }
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

test('frozen string and graph charts cover all former nodes and every old answer prefix', () => {
  assert.equal(frozen.version, 1);
  assert.equal(frozen.baselineGraphCount, 278);
  assert.equal(frozen.baselineWalkCount, 404);
  assert.equal(frozen.completedWalks.length, 404);
  assert.deepEqual([...oldGraphIds].sort(), ['strings', 'string-match', 'string-substring', 'string-palindrome', 'tree-dp', 'flow-matching'].sort(), 'all six affected charts are frozen');
  assert.deepEqual(frozen.graphs.flatMap(graph => (graph.regroupedQuestionIds ?? []).map(id => `${graph.id}/${id}`)), ['strings/subsequence-check'], 'the only regrouped nonroot question is explicitly frozen');
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

test('regrouping preserves source metadata and every complete nonroot node in its original field', async () => {
  const { flow } = await implementation;
  for (const old of frozen.graphs) {
    const graph = flow.getGraph(old.id);
    const { nodes: oldNodes, legacyEntryChoices: oldLegacy, domain, width, height, regroupedQuestionIds, ...oldMetadata } = old;
    const { nodes: currentNodes, legacyEntryChoices: currentLegacy, ...currentMetadata } = graph;
    assert.deepEqual(currentMetadata, oldMetadata, `${old.id}: graph metadata and root identity are unchanged`);
    const remaining = [graph.id];
    const descendants = new Map();
    while (remaining.length) {
      const id = remaining.pop();
      if (descendants.has(id)) continue;
      const current = flow.getGraph(id);
      descendants.set(id, current);
      for (const node of current.nodes) if (node.type === 'route') remaining.push(node.graph);
    }
    for (const oldNode of oldNodes.filter(node => node.id !== old.root)) {
      const copies = [...descendants.values()].flatMap(candidate => candidate.nodes.filter(node => node.id === oldNode.id));
      if (regroupedQuestionIds?.includes(oldNode.id)) {
        assert(copies.some(node => isDeepStrictEqual(rootWithoutChoices(node), rootWithoutChoices(oldNode))), `${old.id}/${oldNode.id}: explicitly regrouped question survives with identical content`);
      } else {
        assert(copies.some(node => isDeepStrictEqual(node, oldNode)), `${old.id}/${oldNode.id}: complete nonroot node survives in a reachable chart`);
      }
    }
    assert.deepEqual(
      rootWithoutChoices(currentNodes.find(node => node.id === graph.root)),
      rootWithoutChoices(oldNodes.find(node => node.id === old.root)),
      `${old.id}: root changes only selectable choices and targets`,
    );
  }
});

test('all former string and graph prefixes preserve complete questions, conditions, candidates and routes', async () => {
  const { flow, viewer } = await implementation;
  for (const record of prefixes) {
    const description = label(record);
    const original = { graph: record.graph.id, answers: record.answers };
    const hash = oldHash(original);
    const state = flow.parseFlowHash(hash);
    const current = flow.evaluateState(state).current;
    assertFormerNode(current, record, description);
    if (!record.answers.length) {
      assert.equal(state.graph, record.graph.id, `${description}: an unanswered old URL stays at its original root`);
    }
    assert.equal(flow.getFlowDomainId(state), record.graph.domain, `${description}: original domain`);
    assert.deepEqual(flow.sanitizeState(original), state, `${description}: object and URL migration agree`);
    assert.deepEqual(viewer.diagramState(record.graph.id, hash), state, `${description}: former viewer URL preserves the state`);
    assertStable(flow, viewer, state, description);
    assert.deepEqual(flow.sanitizeState({ ...original, answers: [...original.answers, '__invalid_answer__', 'yes'] }), state, `${description}: invalid suffix is truncated`);
    if (record.answers.length && record.node.type !== 'route') {
      const walk = flow.walkFromRoot(record.answers, record.graph.id);
      assert.equal(walk.consumed, record.answers.length, `${description}: former answers are consumed once`);
      assertFormerNode(walk.current, record, `${description}: old root walk`);
    }
    const formerPrefixes = Array.from({ length: record.answers.length }, (_, index) => flow.parseFlowHash(oldHash({
      graph: record.graph.id, answers: record.answers.slice(0, record.answers.length - index - 1),
    })));
    assertBackTo(flow, viewer, state, record.graph.id, record.graph.domain, description, formerPrefixes);
  }
});

test('the explicitly regrouped subsequence question preserves every former label and target', async () => {
  const { flow } = await implementation;
  for (const old of frozen.graphs) for (const questionId of old.regroupedQuestionIds ?? []) {
    const question = old.nodes.find(node => node.id === questionId);
    const record = prefixes.find(record => record.graph.id === old.id && record.node.id === questionId);
    assert(record, `${old.id}/${questionId}: old question has an independently frozen prefix`);
    const state = flow.parseFlowHash(oldHash({ graph: old.id, answers: record.answers }));
    const graph = flow.getGraph(state.graph);
    const root = graph.nodes.find(node => node.id === graph.root);
    assert.equal(root.id, question.id, `${old.id}/${questionId}: question is the root of its detail chart`);
    assert.deepEqual(rootWithoutChoices(root), rootWithoutChoices(question), `${old.id}/${questionId}: question text and conditions are unchanged`);
    const options = flow.getNodeOptions(root);
    assert(options.length < flow.getNodeOptions(question).length, `${old.id}/${questionId}: detail root has fewer choices`);
    assert(options.length <= 7 && options.some(option => option.id === 'unknown'), `${old.id}/${questionId}: at most six categories plus unknown`);
    for (const option of flow.getNodeOptions(question)) {
      const description = `${old.id}/${questionId}/${option.id}`;
      const migration = graph.legacyEntryChoices?.[option.id];
      let target = root;
      if (migration) {
        const route = graph.nodes.find(node => node.id === root.answers[migration.answer]);
        assert.equal(route.type, 'route', `${description}: old choice maps to an explicit category route`);
        assert.equal(route.graph, migration.graph, `${description}: migration matches the actual route`);
        const category = flow.getGraph(migration.graph);
        target = category.nodes.find(node => node.id === category.root);
        assert.equal(flow.getFlowDomainId(flow.initialState(category.id)), old.domain, `${description}: category stays in the original field`);
      }
      assert(flow.getNodeOptions(target).some(candidate => candidate.id === option.id && candidate.label === option.label), `${description}: original label remains selectable`);
      assert.equal(target.answers[option.id], question.answers[option.id], `${description}: original answer target is unchanged`);
    }
  }
});

test('all 404 former completed problem URLs retain complete results and usable history after string and graph regrouping', async () => {
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
    const canonicalSteps = [...(state.trail ?? []), state].flatMap(context => {
      const graph = flow.getGraph(context.graph);
      let node = graph.nodes.find(node => node.id === graph.root);
      return context.answers.map(answer => {
        const target = node.answers[answer];
        const step = { graph: graph.id, node: node.id, answer, target };
        node = graph.nodes.find(candidate => candidate.id === target);
        return step;
      });
    });
    assert.deepEqual(walk.steps, canonicalSteps, `${description}: former walk and migrated URL have identical canonical steps`);
    assertBackTo(flow, viewer, state, record.domain, record.domain, description);
  }
});

test('former string and graph URLs reject unrelated history and retain valid local migrations', async () => {
  const { flow, viewer } = await implementation;
  for (const record of prefixes) {
    const description = label(record);
    const original = { graph: record.graph.id, answers: record.answers };
    const expected = flow.parseFlowHash(oldHash(original));
    const unrelated = flow.entryGraphs.find(graph => graph.id !== record.graph.domain && !oldGraphIds.has(graph.id));
    assert(unrelated, `${description}: unrelated domain is available for the malformed-history check`);
    const corrupt = { ...original, trail: [{ graph: unrelated.id, answers: [] }] };
    assert.deepEqual(flow.sanitizeState(corrupt), expected, `${description}: unrelated trail cannot erase valid local migration`);
    assert.deepEqual(flow.parseFlowHash(oldHash(corrupt)), expected, `${description}: corrupt old URL preserves valid local migration`);
    assert.deepEqual(viewer.diagramState(record.graph.id, oldHash(corrupt)), expected, `${description}: viewer handles corrupt old history consistently`);
    assert.deepEqual(flow.sanitizeState({ ...original, answers: [...original.answers, null, 'yes'] }), expected, `${description}: nonstring answer suffix is truncated`);
    assertStable(flow, viewer, expected, description);
  }
});

test('regrouped string and graph roots preserve former feature labels with at most six concrete categories', async () => {
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

test('regrouped string and graph diagrams preserve original URLs while occupying less area', async () => {
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
