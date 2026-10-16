import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-joi-path-arrivals-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Fixed before registration, independently of the example walks under test.
const tasks = [
  {
    id: 'skyline-cartesian-star-paths', problemId: 'joi2020sc_constellation3',
    domain: 'geometry', prefix: ['skyline-stars'],
    graph: 'skyline-star-path-conditions', guards: ['skyline-rectangles', 'weighted-deletion', 'size'],
    alternate: { domain: 'graphs', prefix: ['rooted-tree-goals', 'tree-answer', 'ancestor-path-packing'],
      graph: 'ancestor-path-packing-conditions', guards: ['ancestor-paths', 'vertex-disjoint', 'size'] },
    gapId: 'skyline-star-conflicts-ancestor-path-packing',
    proposedIds: ['skyline-cartesian-star-paths', 'tree-ancestor-path-disjoint-packing'],
    terms: [/ビル/, /星/, /長方形/, /祖先/, /頂点/, /費用|重み/],
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day3/constellation3.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day3/constellation3-review.pdf',
  },
  {
    id: 'functional-graph-timed-arrivals-offline', problemId: 'joi2020sc_harvest',
    domain: 'geometry', prefix: ['circle-harvest'],
    graph: 'circle-timed-arrivals-conditions', guards: ['same-speed-circle', 'independent-arrivals', 'bounds'],
    alternate: { domain: 'graphs', prefix: ['timed-arrivals'],
      graph: 'timed-functional-arrivals-conditions', guards: ['one-successor', 'independent-sources', 'bounds'] },
    gapId: 'circle-cooldown-weighted-functional-arrivals',
    proposedIds: ['circle-cooldown-successor-reduction', 'functional-graph-timed-arrivals-offline'],
    terms: [/円周|行き先/, /正の|正|1\.\./, /独立/, /時刻/, /到着|取得|収穫/],
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day3/harvest.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day3/harvest-review.pdf',
  },
];
const ids = tasks.map(item => item.id);
const routes = tasks.flatMap(item => [item, { ...item, ...item.alternate }]);
const candidates = value => value.current.techniques ?? [];
const matches = (row, item) => String(row.source).toLowerCase() === 'joi' && row.problemId === item.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

async function collections(expression) {
  return (await Promise.all((await readdir(path.join(site, 'data')))
    .filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function walk(flow, item, choices) {
  const value = flow.walkFromRoot(choices, item.domain);
  assert.equal(value.consumed, choices.length, `${item.domain}/${choices.join('/')}: consume all fixed answers`);
  return value;
}
function enterRoutes(flow, state) {
  for (let limit = 0; flow.evaluateState(state).current.type === 'route'; ++limit) {
    assert(limit < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, item, choices) {
  let state = flow.initialState(item.domain);
  for (const answer of choices) state = flow.answerState(enterRoutes(flow, state), answer);
  return enterRoutes(flow, state);
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}
function checkSvg(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let edges = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: node is visible`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the complete answer label is readable');
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${id}/`));
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges, 'no answer edges are added');
  return svg;
}

test('all four independent feature entrances require the fixed three guards and select one completed article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15, 'the existing fields remain the only top-level entrances');
  for (const item of routes) {
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.id, item.guards[guard]);
      assert.equal(value.current.type, 'question');
      assert.notEqual(value.graph.entry, true);
      assert(ids.every(id => !candidates(value).includes(id)), 'a required premise cannot be skipped');
      assert.deepEqual(flow.getNodeOptions(value.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
    }
    const value = walk(flow, item, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id]);
    checkSvg(flow, value.graph);
    if (!item.alternate || item.graph === tasks.find(task => task.id === item.id).graph)
      for (const term of item.terms) assert.match(JSON.stringify(value.graph), term);
  }
});

test('every no and unknown answer preserves an explicit question for checking the missing premise', async () => {
  const { flow } = await implementation;
  for (const item of routes) for (let guard = 0; guard < 3; ++guard)
    for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(value.graph.id, 'condition-check', `${item.graph}/${item.guards[guard]}/${answer}`);
      assert.equal(value.current.type, 'question');
      assert(ids.every(id => !candidates(value).includes(id)));
    }
});

test('question text and diagrams expose every guard, answer label and result article', async () => {
  const { flow } = await implementation;
  const html = flow.renderFlowHtml('/flowchartcp/');
  assert(html.includes('data-view="questions"'));
  assert(html.includes('data-view="diagram"'));
  for (const item of routes) {
    const graph = flow.getGraph(item.graph);
    checkSvg(flow, graph);
    assert(html.includes(`data-graph-panel="${item.graph}"`));
    for (const node of graph.nodes) {
      assert(html.includes(`id="flow-text-${item.graph}-${node.id}"`));
      assert(html.includes(xml(node.title)));
      if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
        assert(html.includes(xml(option.label)));
        assert(html.includes(`#flow-text-${item.graph}-${node.answers[option.id]}`));
      }
    }
    assert(html.includes(`/flowchartcp/techniques/${item.id}/`));
  }
});

test('shared question and diagram URLs restore the same histories and Back returns to the original field', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of routes) {
    const histories = [[...item.prefix, 'yes', 'yes', 'yes']];
    for (let guard = 0; guard < 3; ++guard) for (const answer of ['no', 'unknown'])
      histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item, choices).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0, 'Back terminates');
        assert.equal(flow.getFlowDomainId(state), item.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluation = flow.evaluateState(state);
        if (!diagrams.has(state.graph)) diagrams.set(state.graph, checkSvg(flow, evaluation.graph));
        const svg = diagrams.get(state.graph);
        assert(svg.includes(`data-node="${evaluation.current.id}"`));
        for (const node of evaluation.path) assert(svg.includes(`data-node="${node.id}"`));
        for (const edge of evaluation.edges)
          assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
        const hash = flow.serializeFlowHash(state);
        assert.deepEqual(flow.parseFlowHash(hash), state);
        assert.deepEqual(viewer.diagramState(state.graph, hash), state);
        const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
        assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
        assert.equal(url.hash, hash);
        assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
        if (!weight(state)) break;
        const previous = flow.backFlowState(state);
        assert(weight(previous) < weight(state));
        state = previous;
      }
      assert.deepEqual(state, flow.initialState(item.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  }
});

test('the original 491 walks preserve their entire records, paths and terminal nodes', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 493);
  const previous = walks.slice(0, 491);
  // Records were frozen before either article was connected. The second hash
  // was computed using the separately preserved pre-integration flow JSON.
  assert.equal(digest(previous), '2937b43f5b4de5a17929a09ac2738632114d4f97a9f3b2b1954a829154da9b69');
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const id of row.expectedTechniqueIds) assert(candidates(value).includes(id));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'f2082b12217c50444dabacd110a676ed13c9aee8f0c3baff179aecb95d02b01e');
});

test('two full articles and original examples preserve March 22 provenance and merge both proposed technique pairs', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks, audit, plan] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/joi-path-arrivals-problem-features.json'), json('data/problem-walks.json'),
    json('data/corpus-audits/joi-2020-spring.json'), json('data/coverage-plan.json'),
  ]);
  assert.equal(features.length, 2);
  for (const item of tasks) {
    const registered = metadata.filter(row => row.id === item.id);
    assert.equal(registered.length, 1);
    const technique = registered[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert(technique.sources.includes(item.statementUrl));
    assert(technique.sources.includes(item.editorialUrl));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
      ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
    assert(!/<(?:details|summary)\b/i.test(article));
    assert(article.includes(`techniqueId="${item.id}"`));
    for (const source of technique.sources) assert(article.includes(source));
    const originals = references.filter(row => row.techniqueId === item.id && matches(row, item));
    assert.equal(originals.length, 1);
    const reference = originals[0];
    assert.equal(reference.url, item.statementUrl);
    assert.equal(reference.editorialUrl, item.editorialUrl);
    assert.equal(reference.verification, 'editorial');
    assert.equal(reference.difficulty, null);
    assert.equal(reference.cutoffVerification, 'contest-before-cutoff');
    assert(reference.evidence.trim().length > 0);
    const matchingFeatures = features.filter(row => matches(row, item));
    assert.equal(matchingFeatures.length, 1);
    const feature = matchingFeatures[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.evidenceUrl, item.editorialUrl);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, 'editorial');
    assert.equal(feature.publicationDate, '2020-03-22');
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, item.domain);
    assert.deepEqual(example.choices, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(example.statementUrl, item.statementUrl);
    assert.equal(example.reviewStatus, 'verified');
    assert.equal(example.verificationKind, 'editorial');
    assert.deepEqual(example.features, feature.features);
    assert.deepEqual(walk(flow, item, example.choices).steps
      .map(({ graph, node, answer }) => ({ graph, node, answer })), example.steps);
    const original = audit.records.find(row => matches(row, item));
    assert(original);
    assert.equal(original.contest.date, '2020-03-22');
    assert.equal(original.contest.day, 3);
    assert.equal(original.contest.exactDateVerified, true);
    assert.deepEqual(original.gap.neededTechniqueIds, item.proposedIds, 'retain the initial two-technique proposal');
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id], 'the completed reduction and general API share one article');
    assert(original.resolution.notes.trim().length > 0);
    assert.equal(isCorpusSolutionReviewed(original), true);
    const gap = plan.knownGaps.find(row => row.id === item.gapId);
    assert(gap);
    assert.equal(gap.state, 'resolved');
    assert.equal(gap.problemId, item.problemId);
    assert.deepEqual(gap.techniqueIds, [item.id]);
    assert.deepEqual(gap.originallyProposedTechniqueIds, item.proposedIds);
    for (const proposed of item.proposedIds.filter(id => id !== item.id))
      assert(!metadata.some(row => row.id === proposed), 'merged proposal is not registered as an extra article');
  }
});
