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
const id = 'unique-first-symbol-prefix-oracle-multiplexing';
const problemId = 'ioi2018_combo';
const domain = 'interactive-oracles';
// Fixed from problem features before examining the registered example walk.
const prefix = ['prefix-in-substring'];
const graphId = 'unique-initial-prefix-oracle-conditions';
const guards = ['prefix-oracle', 'unique-initial', 'query-budget'];
const statementUrl = 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-combo.pdf';
const editorialUrl = 'https://www2.ioi-jp.org/ioi/2018/tasks/day1-combo-review.pdf';
const boundsUrl = 'https://ioi2018.jp/tasks/contest1/CHE-combo.pdf';
const candidates = value => value.current.techniques ?? [];
const matches = row => String(row.source).toLowerCase() === 'ioi' && row.problemId === problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-combo-flow-'));
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
function walk(flow, choices) {
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
function replay(flow, choices) {
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

test('the fixed prefix-in-substring entrance requires every premise and selects one article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15);
  assert.equal(flow.getGraph(domain).entry, true);
  const before = walk(flow, prefix.slice(0, -1));
  assert.equal(before.graph.id, 'interactive-oracles');
  assert.equal(before.current.id, 'response');
  assert(flow.getNodeOptions(before.current).some(option => option.id === 'prefix-in-substring'));
  for (let index = 0; index < guards.length; ++index) {
    const value = walk(flow, [...prefix, ...Array(index).fill('yes')]);
    assert.equal(value.graph.id, graphId);
    assert.equal(value.current.id, guards[index]);
    assert.equal(value.current.type, 'question');
    assert.notEqual(value.graph.entry, true);
    assert.equal(flow.getFlowDomainId(flow.initialState(graphId)), domain);
    assert(!candidates(value).includes(id));
    assert.deepEqual(flow.getNodeOptions(value.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
  }
  const value = walk(flow, [...prefix, 'yes', 'yes', 'yes']);
  assert.equal(value.current.type, 'result');
  assert.deepEqual(candidates(value), [id]);
  for (const term of [/四種類|四記号|4/, /固定/, /接頭辞/, /部分文字列/, /先頭/, /2000/, /4N/, /N\+2/])
    assert.match(JSON.stringify(value.graph), term);
  checkSvg(flow, flow.getGraph('interactive-oracles'));
  checkSvg(flow, value.graph);
});

test('all six no or unknown premise answers lead to condition checking', async () => {
  const { flow } = await implementation;
  for (let index = 0; index < guards.length; ++index) for (const answer of ['no', 'unknown']) {
    const value = walk(flow, [...prefix, ...Array(index).fill('yes'), answer]);
    assert.equal(value.graph.id, 'condition-check', `${guards[index]}/${answer}`);
    assert.equal(value.current.type, 'question');
    assert(!candidates(value).includes(id));
  }
});

test('both displays show answer labels and the article, while sharing and Back preserve each history', async () => {
  const { flow, viewer } = await implementation;
  const html = flow.renderFlowHtml('/flowchartcp/');
  assert(html.includes('data-view="questions"'));
  assert(html.includes('data-view="diagram"'));
  for (const currentGraph of ['interactive-oracles', graphId]) {
    const graph = flow.getGraph(currentGraph);
    assert(html.includes(`data-graph-panel="${currentGraph}"`));
    checkSvg(flow, graph);
    for (const node of graph.nodes) {
      assert(html.includes(`id="flow-text-${currentGraph}-${node.id}"`));
      assert(html.includes(xml(node.title)));
      if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
        assert(html.includes(xml(option.label)));
        assert(html.includes(`#flow-text-${currentGraph}-${node.answers[option.id]}`));
      }
    }
  }
  assert(html.includes(`/flowchartcp/techniques/${id}/`));
  const histories = [[...prefix, 'yes', 'yes', 'yes']];
  for (let index = 0; index < guards.length; ++index) for (const answer of ['no', 'unknown'])
    histories.push([...prefix, ...Array(index).fill('yes'), answer]);
  const diagrams = new Map();
  for (const choices of histories) {
    let state = replay(flow, choices);
    assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices).current);
    for (let limit = weight(state) + 1; ; --limit) {
      assert(limit > 0, 'Back terminates');
      assert.equal(flow.getFlowDomainId(state), domain);
      assert.deepEqual(flow.sanitizeState(state), state);
      const evaluation = flow.evaluateState(state);
      if (!diagrams.has(state.graph)) diagrams.set(state.graph, checkSvg(flow, evaluation.graph));
      const svg = diagrams.get(state.graph);
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
    assert.deepEqual(state, flow.initialState(domain));
    assert.deepEqual(flow.backFlowState(state), state);
  }
});

test('all previous 505 records preserve every answer, target, label and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 506);
  const previous = walks.slice(0, 505);
  assert.equal(digest(previous), '312d8101fc910300e6ff3570a178f622b8f930ccdae7756f90ed14333b0f8db3');
  // Expected hashes were computed by replaying raw frozen JSON, without the
  // product walker, using the preserved pre-Combo 451-graph JSON.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const technique of row.expectedTechniqueIds) assert(candidates(value).includes(technique));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '473891fef561e71b38a6db0edd449d0c4260d36afb2551ff6c5acbeff3beaff2');
  const text = observed.map(value => {
    const graph = flow.getGraph(value.graph);
    return { graph: value.graph, node: value.node, type: value.type,
      title: graph.nodes.find(node => node.id === value.node).title, techniques: value.techniques,
      steps: value.steps.map(step => {
        const node = flow.getGraph(step.graph).nodes.find(node => node.id === step.node);
        return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
          answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label,
          target: step.target };
      }) };
  });
  assert.equal(digest(text), '7da50eb0ae345ed9d6c4bddbefaff3153362a7432cc55cc8db698abc1a138271');
});

test('the complete visible article, dated original, numeric evidence and canonical example agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/unique-initial-prefix-problem-features.json'), json('data/problem-walks.json'),
  ]);
  const registered = metadata.filter(row => row.id === id);
  assert.equal(registered.length, 1);
  const technique = registered[0];
  assert.equal(technique.kind, 'technique');
  assert.equal(technique.status, 'reviewed');
  assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
  for (const source of [statementUrl, editorialUrl, boundsUrl]) assert(technique.sources.includes(source));
  const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
  assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
    ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
  assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
  assert(!/<(?:details|summary)\b/i.test(article));
  assert(article.includes(`techniqueId="${id}"`));
  for (const source of technique.sources) assert(article.includes(source));
  for (const term of [/2000/, /4N/, /N\+2/, /8005993/, /8000/,
    /recover_unique_initial_sequence/]) assert.match(article, term);
  const originals = references.filter(row => row.techniqueId === id && matches(row));
  assert.equal(originals.length, 1);
  const reference = originals[0];
  assert.equal(reference.url, statementUrl);
  assert.equal(reference.editorialUrl, editorialUrl);
  assert.equal(reference.verification, 'independent-analysis');
  assert.equal(reference.sourceDate, '2018-09-03');
  assert.equal(reference.difficulty, null);
  assert.equal(reference.cutoffVerification, 'contest-before-cutoff');
  assert(reference.evidence.trim().length > 0);
  assert.equal(features.length, 1);
  const feature = features[0];
  assert(matches(feature));
  assert.deepEqual(feature.techniqueIds, [id]);
  assert.equal(feature.url, statementUrl);
  assert.equal(feature.evidenceUrl, editorialUrl);
  assert.equal(feature.sourceBoundsEvidenceUrl, boundsUrl);
  assert.equal(feature.originalNumericBoundsVerified, true);
  assert.equal(feature.reviewStatus, 'verified');
  assert.equal(feature.verification, 'independent-analysis');
  assert.equal(feature.publicationDate, '2018-09-03');
  assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
  assert.equal(feature.exactDateVerified, true);
  assert.equal(feature.difficulty, null);
  assert.equal(feature.cutoff, '2026-10-14');
  const examples = walks.filter(row => matches(row) && row.expectedTechniqueIds.includes(id));
  assert.equal(examples.length, 1);
  const example = examples[0];
  assert.equal(example.entryGraphId, domain);
  assert.deepEqual(example.choices, [...prefix, 'yes', 'yes', 'yes']);
  assert.deepEqual(example.expectedTechniqueIds, [id]);
  assert.equal(example.statementUrl, statementUrl);
  assert.equal(example.reviewStatus, 'verified');
  assert.equal(example.verificationKind, 'independent-analysis');
  assert.equal(example.cutoffVerification, 'contest-before-cutoff');
  assert.deepEqual(example.features, feature.features);
  assert.deepEqual(walk(flow, example.choices).steps.map(({ graph, node, answer }) => ({ graph, node, answer })), example.steps);
});


const previousRootNodeIds = ["response", "tree-positive", "tree-query-budget", "tree-oracle-result", "strict-unimodal", "reuse-value-budget", "unimodal-result", "rook-single-missing", "rook-budget", "rook-result", "one-defect", "bit-identity", "group-testing-result", "check", "fallback", "uncertain", "navigation-check", "general-result", "changing-color-count-route", "transition-count-route"];
const previousRootOptions = [{"id": "tree-distance", "label": "辺は未知だが、指定した二頂点の木距離"}, {"id": "unimodal-value", "label": "隠れた単峰列の、指定位置の値"}, {"id": "rectangle-count", "label": "各行列に高々一個の配置の、長方形内の個数"}, {"id": "batch-subsets", "label": "一つの不良対象を含むかを、任意部分集合ごとに同時判定"}, {"id": "navigation", "label": "今の隣接先一覧を返し、指定した隣接先へ移動する"}, {"id": "other", "label": "その他の返答形式・通信条件"}, {"id": "changing-color-count", "label": "任意集合の会合で、参加者によって変わる色の種類数"}, {"id": "transition-count", "label": "番号を並べると、隣り合う対象の種類が変わる回数が返る"}, {"id": "unknown", "label": "わからない"}];
const previousRootAnswers = {"tree-distance": "tree-positive", "unimodal-value": "strict-unimodal", "rectangle-count": "rook-single-missing", "batch-subsets": "one-defect", "unknown": "check", "navigation": "navigation-check", "other": "general-result", "changing-color-count": "changing-color-count-route", "transition-count": "transition-count-route"};
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;

test('the old interactive root keeps all previous nodes, option labels, order and targets', async () => {
  const { flow } = await implementation;
  const root = structuredClone(flow.getGraph(domain));
  assert.deepEqual(root.nodes.filter(node => previousRootNodeIds.includes(node.id)).map(node => node.id), previousRootNodeIds);
  const response = root.nodes.find(node => node.id === root.root);
  const previousIds = previousRootOptions.map(option => option.id);
  assert.deepEqual(flow.getNodeOptions(response).filter(option => previousIds.includes(option.id)), previousRootOptions);
  for (const [answer, target] of Object.entries(previousRootAnswers)) assert.equal(response.answers[answer], target);
  assert.equal(flow.getNodeOptions(response).filter(option => option.id === prefix[0]).length, 1);
  const route = root.nodes.find(node => node.id === response.answers[prefix[0]]);
  assert.equal(route.type, 'route');
  assert.equal(route.graph, graphId);
  // Project onto the frozen old root. Later added options can coexist, while
  // every old node, explanation, label and answer target stays exact.
  root.nodes = root.nodes.filter(node => previousRootNodeIds.includes(node.id));
  response.options = response.options.filter(option => previousIds.includes(option.id));
  response.answers = Object.fromEntries(Object.keys(previousRootAnswers).map(answer => [answer, response.answers[answer]]));
  assert.equal(digest(stable(root)), '167502a36137a0899eda4cae61cedb0217b66f55223cc35359127f68091e1ae4');
  const outputs = flow.graphs.flatMap(graph => graph.nodes.filter(node => (node.techniques ?? []).includes(id))
    .map(node => ({ graph: graph.id, node: node.id, type: node.type })));
  assert.deepEqual(outputs, [{ graph: graphId, node: 'result', type: 'result' }],
    'the new article is never asserted by an unguarded generic result');
});

test('only a later resolution closes Combo while all six first-pass records, proof status and 482/449 snapshot stay fixed', async () => {
  const [audit, plan] = await Promise.all([json('data/corpus-audits/ioi-2018.json'), json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.articleCount, 482);
  assert.equal(audit.snapshot.specificTechniqueCount, 404);
  assert.equal(audit.snapshot.flowGraphCount, 449);
  assert.equal(audit.snapshot.walkCount, 503);
  for (const [kind, hash] of Object.entries({ flow: '51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e',
    technique: '74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be' })) {
    assert.equal(audit.snapshot[kind + 'Sha256'], hash);
    const raw = gunzipSync(await readFile(path.join(site, audit.snapshot[kind + 'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'), hash);
  }
  assert.equal(digest(audit.status), '8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3');
  assert.equal(digest(audit.selection), '1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b');
  // All six solutions were researched already. Article completion appends a
  // resolution without changing the original research/provenance fields.
  const initial = audit.records.map(({ resolution, ...row }) => row);
  assert.equal(digest(initial), 'ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523');
  assert.deepEqual(initial.map(row => row.problemId), ['combo', 'seats', 'werewolf', 'doll', 'highway', 'meetings'].map(task => 'ioi2018_' + task));
  assert(initial.every(isCorpusSolutionReviewed));
  assert.equal(audit.status.solutionReviewedCount, 6);
  assert.equal(audit.status.coveredCount, 0);
  assert.equal(audit.status.missingTechniqueCount, 6);
  assert.equal(audit.status.fullImplementationValidatedCount, 0);
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, true);
  assert.equal(audit.status.fixedCorpusCoverageComplete, false);
  assert.equal(audit.status.globalCoverageComplete, false);
  const row = audit.records.find(matches), first = initial.find(matches);
  assert(row && first);
  assert.equal(digest(first), '3991559f70d0799732507459248e61b295d2a68b798f57540e3d05c56d17dd6f');
  assert.equal(first.classification, 'missing-technique');
  assert.equal(first.constraints.numericBoundsVerified, true);
  assert.equal(first.contest.date, '2018-09-03');
  assert.equal(first.contest.day, 1);
  assert.equal(first.difficulty, null);
  assert.equal(first.gap.firstMissingGraphId, domain);
  assert.equal(first.gap.firstMissingNodeId, 'general-result');
  assert.deepEqual(first.choices, ['other']);
  assert.deepEqual(first.actualReachedTechniqueIds, ['interactive']);
  assert.deepEqual(first.expectedTechniqueIds, []);
  assert.equal(row.resolution.status, 'verified');
  assert.deepEqual(row.resolution.techniqueIds, [id]);
  assert.equal(row.resolution.rootWalkFile, 'data/problem-walks.json');
  assert.match(row.resolution.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
  assert(row.resolution.notes.trim().length > 0);
  const corpus = plan.corpora.find(row => row.id === audit.corpusId);
  assert.equal(corpus.state, 'audited');
  assert.equal(corpus.expectedProblems, 6);
  assert.deepEqual(corpus.fixedProblems.map(row => row.problemId), initial.map(row => row.problemId));
  const gap = plan.knownGaps.find(row => row.id === first.gap.id);
  assert.equal(gap.state, 'resolved');
  assert.equal(gap.problemId, problemId);
  assert.deepEqual(gap.techniqueIds, [id]);
  // Old fallback and shared histories keep their original generic endpoint.
  const { flow } = await implementation;
  assert.deepEqual(candidates(walk(flow, ['other'])), ['interactive']);
  assert(!candidates(walk(flow, ['other'])).includes(id));
});
