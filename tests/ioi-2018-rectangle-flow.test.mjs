import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = fileURLToPath(new URL('../', import.meta.url));
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const cases = [
  { id: 'dynamic-grid-prefix-rectangle-corner-minimum-count', problemId: 'ioi2018_seats',
    domain: 'grid-arrangements', prefix: ['color-numbers', 'prefix-rectangles'],
    parent: 'grid-color-numbers', parentNode: 'goal', graph: 'grid-prefix-rectangle-conditions',
    guards: ['permutation-prefix', 'swaps-only', 'bounds'],
    feature: 'data/grid-prefix-rectangle-problem-features.json', group: 'range-patterns',
    statement: 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-seats.pdf',
    editorial: 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-seats-review.pdf',
    terms: [/長方形/, /番号/, /交換/, /prefix|小さい|0から|0.*t/, /1000000|100万|10.*6/],
    articleTerms: [/PrefixRectangleGrid/, /rectangle_prefixes/, /swap_labels/] },
  { id: 'two-threshold-component-merge-trees-rectangle-intersection', problemId: 'ioi2018_werewolf',
    domain: 'graphs', prefix: ['network-connection', 'two-threshold-switch'],
    parent: 'graphs-network-connection', parentNode: 'shortest', graph: 'two-threshold-switch-conditions',
    guards: ['undirected-connected', 'single-threshold-switch', 'bounds'],
    feature: 'data/two-threshold-switch-problem-features.json', group: 'graph-extensions',
    statement: 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-werewolf.pdf',
    editorial: 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-werewolf-review.pdf',
    terms: [/無向/, /連結/, /L/, /R/, /一度/, /20万|200000/, /40万|400000/],
    articleTerms: [/threshold_component_intersection_counts/, /threshold_switch_reachability/] },
];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === 'ioi' && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// This compact fixture contains only old graph/node IDs and original answer
// IDs, derived from the independent pre-batch raw freeze (453 graphs/3589 nodes).
// The hash below fixes every complete old graph/node field after projection,
// including labels and ordering, while future added branches remain possible.
const oldShape = JSON.parse(gunzipSync(Buffer.from('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', 'base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-rectangle-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

async function collections(expression) {
  return (await Promise.all((await readdir(path.join(site, 'data')))
    .filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function walk(flow, choices, domain) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, choices.join('/') + ': consume every fixed answer');
  return value;
}
function enterRoutes(flow, state) {
  for (let limit = 0; flow.evaluateState(state).current.type === 'route'; ++limit) {
    assert(limit < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, choices, domain) {
  let state = flow.initialState(domain);
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
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: visible node`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the complete answer label is readable');
    }
    if (node.type === 'result') for (const technique of node.techniques ?? [])
      assert(svg.includes(`href="/flowchartcp/techniques/${technique}/"`));
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges);
  return svg;
}


let html;
const svgCache = new Map();
for (const current of cases) {
  test(current.problemId + ': all premises gate the sole concrete result and no/unknown stays unresolved', async () => {
    const { flow } = await implementation;
    assert.deepEqual(flow.validateGraphs(), []);
    assert.equal(flow.getGraph(current.domain).entry, true);
    assert.equal(flow.getFlowDomainId(flow.initialState(current.graph)), current.domain);
    const parent = walk(flow, current.prefix.slice(0, -1), current.domain);
    assert.equal(parent.graph.id, current.parent);
    assert.equal(parent.current.id, current.parentNode);
    assert.equal(flow.getNodeOptions(parent.current).filter(option => option.id === current.prefix.at(-1)).length, 1);
    for (let index = 0; index < 3; ++index) {
      const result = walk(flow, [...current.prefix, ...Array(index).fill('yes')], current.domain);
      assert.equal(result.graph.id, current.graph);
      assert.equal(result.current.id, current.guards[index]);
      assert.equal(result.current.type, 'question');
      assert.notEqual(result.graph.entry, true);
      assert(!candidates(result).includes(current.id));
      assert.deepEqual(flow.getNodeOptions(result.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const answer of ['no', 'unknown']) {
        const fallback = walk(flow, [...current.prefix, ...Array(index).fill('yes'), answer], current.domain);
        assert.equal(fallback.graph.id, 'condition-check');
        assert.equal(fallback.current.type, 'question');
        assert(!candidates(fallback).includes(current.id));
      }
    }
    const result = walk(flow, [...current.prefix, 'yes', 'yes', 'yes'], current.domain);
    assert.equal(result.current.type, 'result');
    assert.deepEqual(candidates(result), [current.id]);
    for (const term of current.terms) assert.match(JSON.stringify(result.graph), term);
    const occurrences = flow.graphs.flatMap(graph => graph.nodes.filter(node => (node.techniques ?? []).includes(current.id))
      .map(node => ({ graph: graph.id, node: node.id, type: node.type })));
    assert.deepEqual(occurrences, [{ graph: current.graph, node: 'result', type: 'result' }],
      'new techniques occur only inside their premise graph result');
  });

  test(current.problemId + ': both displays, complete SVG labels, shared URLs and Back retain all premise histories', async () => {
    const { flow, viewer } = await implementation;
    html ??= flow.renderFlowHtml('/flowchartcp/');
    assert(html.includes('data-view="questions"') && html.includes('data-view="diagram"'));
    for (const graphId of [current.domain, current.parent, current.graph]) {
      const graph = flow.getGraph(graphId);
      assert(html.includes(`data-graph-panel="${graphId}"`));
      if (!svgCache.has(graphId)) svgCache.set(graphId, checkSvg(flow, graph));
      for (const node of graph.nodes) {
        assert(html.includes(`id="flow-text-${graphId}-${node.id}"`));
        assert(html.includes(xml(node.title)));
        if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
          assert(html.includes(xml(option.label)));
          assert(html.includes(`#flow-text-${graphId}-${node.answers[option.id]}`));
        }
      }
    }
    assert(html.includes(`/flowchartcp/techniques/${current.id}/`));
    const histories = [[...current.prefix, 'yes', 'yes', 'yes']];
    for (let index = 0; index < 3; ++index) for (const answer of ['no', 'unknown'])
      histories.push([...current.prefix, ...Array(index).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, choices, current.domain);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices, current.domain).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0);
        assert.equal(flow.getFlowDomainId(state), current.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluated = flow.evaluateState(state);
        if (!svgCache.has(state.graph)) svgCache.set(state.graph, checkSvg(flow, evaluated.graph));
        const svg = svgCache.get(state.graph);
        for (const node of evaluated.path) assert(svg.includes(`data-node="${node.id}"`));
        for (const edge of evaluated.edges) assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
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
      assert.deepEqual(state, flow.initialState(current.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  });

  test(current.problemId + ': dated original, complete article, grouped metadata and one canonical example agree', async () => {
    const { flow } = await implementation;
    const [metadata, refs, features, walks] = await Promise.all([
      collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/), json(current.feature), json('data/problem-walks.json'),
    ]);
    const registered = metadata.filter(row => row.id === current.id);
    assert.equal(registered.length, 1);
    assert.equal(registered[0].kind, 'technique');
    assert.equal(registered[0].status, 'reviewed');
    assert(registered[0].aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert((await json('data/techniques-specific-' + current.group + '.json')).some(row => row.id === current.id));
    assert((await json('data/references-specific-' + current.group + '.json')).some(row => row.techniqueId === current.id && matches(row, current)));
    assert(registered[0].sources.includes(current.statement));
    assert(registered[0].sources.includes(current.editorial));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', current.id + '.mdx'), 'utf8');
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
      ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
    assert(!/<(?:details|summary)\b/i.test(article));
    for (const term of current.articleTerms) assert.match(article, term);
    assert(article.includes(current.statement) && article.includes(current.editorial));
    assert(article.includes(`techniqueId="${current.id}"`));
    const originals = refs.filter(row => row.techniqueId === current.id && matches(row, current));
    assert.equal(originals.length, 1);
    const ref = originals[0];
    assert.equal(ref.url, current.statement);
    assert.equal(ref.editorialUrl, current.editorial);
    assert.equal(ref.verification, 'independent-analysis');
    assert.equal(ref.sourceDate, '2018-09-03');
    assert.equal(ref.difficulty, null);
    assert.equal(ref.cutoffVerification, 'contest-before-cutoff');
    assert(ref.evidence.trim().length > 0);
    assert.equal(features.length, 1);
    const feature = features[0];
    assert(matches(feature, current));
    assert.deepEqual(feature.techniqueIds, [current.id]);
    assert.equal(feature.url, current.statement);
    assert.equal(feature.evidenceUrl, current.editorial);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, 'independent-analysis');
    assert.equal(feature.publicationDate, '2018-09-03');
    assert.equal(feature.exactDateVerified, true);
    assert.equal(feature.originalNumericBoundsVerified, true);
    assert.equal(feature.difficulty, null);
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, current) && row.expectedTechniqueIds.includes(current.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, current.domain);
    assert.deepEqual(example.choices, [...current.prefix, 'yes', 'yes', 'yes']);
    assert.deepEqual(example.expectedTechniqueIds, [current.id]);
    assert.equal(example.statementUrl, current.statement);
    assert.equal(example.verificationKind, 'independent-analysis');
    assert.equal(example.reviewStatus, 'verified');
    assert.deepEqual(example.features, feature.features);
    const reached = walk(flow, example.choices, current.domain);
    assert.deepEqual(reached.steps.map(({graph,node,answer}) => ({graph,node,answer})), example.steps);
  });
}

test('all 507 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 509);
  const previous = walks.slice(0, 507);
  assert.equal(digest(previous), '1bc68def7bb2fcaf85887886fd50c3715c468b9b16af3fcaf9740820d807d509');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // either article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '519d4b13ddd064e4666d0cac47f5c14f0830b94024a23b75993f1d0823e2e68a');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), 'ab1525d0751470de9be362286254d32fdc4ef8e7bfd622b1a3ad88513239f790');
});

test('every field of all 453 old graphs and 3589 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), '4ae6905dcd0a68a248dd4a46686100e964657d9dce68a848fddef8a4b8986e1a');
  assert.equal(oldShape.length, 453);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3589);
  const shapeMap = new Map(oldShape);
  const oldIds = oldShape.map(([id]) => id);
  const projection = structuredClone(flow.graphs.filter(graph => shapeMap.has(graph.id)));
  assert.deepEqual(projection.map(graph => graph.id), oldIds);
  for (const graph of projection) {
    const shape = new Map(shapeMap.get(graph.id).map(([id,answers,explicitOptions]) => [id,{answers,explicitOptions}]));
    const nodeIds = shapeMap.get(graph.id).map(([id]) => id);
    graph.nodes = graph.nodes.filter(node => shape.has(node.id));
    assert.deepEqual(graph.nodes.map(node => node.id), nodeIds);
    for (const node of graph.nodes) {
      const { answers, explicitOptions } = shape.get(node.id);
      if (!answers) continue;
      assert.equal(node.type, 'question');
      for (const answer of answers) assert(Object.hasOwn(node.answers, answer));
      if (explicitOptions) {
        assert(Array.isArray(node.options));
        node.options = node.options.filter(option => answers.includes(option.id));
      } else if (node.options !== undefined) {
        assert.deepEqual(node.options.filter(option => answers.includes(option.id)),
          answers.map(id => ({id,label:({yes:'はい',no:'いいえ',unknown:'わからない'})[id] ?? id})));
        delete node.options;
      }
      node.answers = Object.fromEntries(answers.map(answer => [answer,node.answers[answer]]));
    }
  }
  assert.equal(digest(stable(projection)), 'c6f3c66fcab4868d9c9b4cb217109a078c35e522d12be9ac1574b0353865093b');
});

test('initial IOI2018 six rows/status/snapshot and Combo resolution stay fixed while only the two new resolutions are appended', async () => {
  const [audit,plan] = await Promise.all([json('data/corpus-audits/ioi-2018.json'),json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.articleCount, 482);
  assert.equal(audit.snapshot.specificTechniqueCount, 404);
  assert.equal(audit.snapshot.flowGraphCount, 449);
  assert.equal(audit.snapshot.walkCount, 503);
  for (const [kind,hash] of Object.entries({ flow:'51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e',
    technique:'74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be' })) {
    const raw=gunzipSync(await readFile(path.join(site,audit.snapshot[kind+'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'),hash);
    assert.equal(audit.snapshot[kind+'Sha256'],hash);
  }
  assert.equal(digest(audit.status),'8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3');
  assert.equal(digest(audit.selection),'1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b');
  const initial=audit.records.map(({resolution,...row})=>row);
  assert.equal(digest(initial),'ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523');
  assert(initial.every(isCorpusSolutionReviewed));
  assert.equal(audit.status.solutionReviewedCount,6);
  assert.equal(audit.status.coveredCount,0);
  assert.equal(audit.status.fullImplementationValidatedCount,0);
  assert.equal(audit.status.fixedCorpusResearchComplete,true);
  assert.equal(audit.status.fixedCorpusCoverageComplete,false);
  assert.equal(audit.status.globalCoverageComplete,false);
  assert.equal(digest(audit.records.find(row=>row.problemId==='ioi2018_combo')),
    'b95a8da558f4c0bae5119cf7ddc425d61a331bfd0c41140ae545143dbccd43b1');
  const corpus=plan.corpora.find(row=>row.id==='ioi-2018');
  assert.equal(corpus.expectedProblems,6);
  assert.equal(corpus.state,'audited');
  assert.deepEqual(corpus.fixedProblems.map(row=>row.problemId),initial.map(row=>row.problemId));
  for (const current of cases) {
    const row=audit.records.find(row=>matches(row,current));
    const first=initial.find(row=>matches(row,current));
    assert.equal(first.classification,'missing-technique');
    assert.equal(first.technicalFindings.fullImplementationValidated,false);
    assert.deepEqual(first.expectedTechniqueIds,[]);
    assert.equal(row.resolution.status,'verified');
    assert.deepEqual(row.resolution.techniqueIds,[current.id]);
    assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
    assert.match(row.resolution.reviewedAt,/^\d{4}-\d{2}-\d{2}$/);
    assert(row.resolution.notes.trim().length>0);
    const gap=plan.knownGaps.find(gap=>gap.id===first.gap.id);
    assert.equal(gap.state,'resolved');
    assert.equal(gap.problemId,current.problemId);
    assert.deepEqual(gap.techniqueIds,[current.id]);
    const record=await json('research/technique-verifications/'+current.id+'.json');
    assert.equal(record.sourceVerification.numericBoundsVerified,true);
    assert.equal(record.reference.difficulty,null);
    assert.equal(record.reference.sourceDate,'2018-09-03');
  }
  assert.equal(initial.find(row=>row.problemId==='ioi2018_seats').gap.firstMissingGraphId,'grid-color-numbers');
  assert.equal(initial.find(row=>row.problemId==='ioi2018_werewolf').gap.firstMissingNodeId,'components');
});
