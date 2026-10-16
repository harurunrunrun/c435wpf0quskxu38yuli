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

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const id = 'bounded-power-two-equal-bag-prefix-cap-memoization';
const problemId = 'ioi2020_biscuits';
const domain = 'math';
// Fixed from problem features before examining the registered example walk.
const prefix = ['counting-totals', 'count', 'select-values', 'equal-bag-values'];
const graphId = 'power-two-equal-bag-conditions';
const guards = ['power-two-supply', 'distinct-equal-values', 'bounded-supply'];
const statementUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/day2-biscuits-ISC.pdf';
const editorialUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/biscuits-solutions-ISC.pdf';
const archiveUrl = 'https://ioi.te.lv/locations/ioi20/contest/';
const boundsUrl = archiveUrl + 'day2/Biscuits/HUN.pdf';
const candidates = value => value.current.techniques ?? [];
const matches = row => String(row.source).toLowerCase() === 'ioi' && row.problemId === problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-equal-bag-flow-'));
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
async function historicalAudit() {
  const bytes = gunzipSync(await readFile(path.join(site,
    'tests/fixtures/ioi-three-resolution-before-biscuits.json.gz')));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),
    '9208ac8515a979dd9ec7213d990a95c2a1b4aac736916f364b072b00cea460a2');
  return JSON.parse(bytes);
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

test('the fixed equal-bag entrance requires all three premises and selects one article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15);
  assert.equal(flow.getGraph(domain).entry, true);
  const before = walk(flow, prefix.slice(0, -1));
  assert.equal(before.graph.id, 'count-selected-values');
  assert.equal(before.current.id, 'count-kind');
  assert(flow.getNodeOptions(before.current).some(option => option.id === 'equal-bag-values'));
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
  for (const term of [/1,2,4/, /有限/, /相異なる/, /配り方/, /空袋/, /63/, /2\^63/, /正の/])
    assert.match(JSON.stringify(value.graph), term);
  checkSvg(flow, flow.getGraph('count-selected-values'));
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
  for (const currentGraph of ['count-selected-values', graphId]) {
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

test('all previous 496 records preserve every answer, target, label and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 497);
  const previous = walks.slice(0, 496);
  assert.equal(digest(previous), '93ccd0a168cb6849dfd287e008c2fc17361f07981d989fa545f8f4c2549b04a0');
  // Expected hashes were computed by replaying raw frozen JSON, without the
  // product walker. Frozen flow bytes SHA256:
  // 5823d52efcf537b95aaf806246ad26fbae68928920b2fcc0b226e0be911de79c.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const technique of row.expectedTechniqueIds) assert(candidates(value).includes(technique));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '417bb4c42dde6ddca651505f7b564a3f22c50391487cdc9c098ca5ae04a44e4d');
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
  assert.equal(digest(text), '39d881867d79a7769432bf015635e734abb2bb0f45d8c58ab498a40e36a76c7e');
});

test('the complete visible article, dated original, numeric evidence and canonical example agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/equal-bag-values-problem-features.json'), json('data/problem-walks.json'),
  ]);
  const registered = metadata.filter(row => row.id === id);
  assert.equal(registered.length, 1);
  const technique = registered[0];
  assert.equal(technique.kind, 'technique');
  assert.equal(technique.status, 'reviewed');
  assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
  for (const source of [statementUrl, editorialUrl, archiveUrl, boundsUrl]) assert(technique.sources.includes(source));
  const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
  assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
    ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
  assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
  assert(!/<(?:details|summary)\b/i.test(article));
  assert(article.includes(`techniqueId="${id}"`));
  for (const source of technique.sources) assert(article.includes(source));
  for (const term of [/種類数0〜63/, /T\\le\\mathrm\{INT64/, /k\\le60/, /q\\le1000/,
    /10\^\{18\}\+1/, /1830/, /uint64_t/, /int64_t/]) assert.match(article, term);
  const originals = references.filter(row => row.techniqueId === id && matches(row));
  assert.equal(originals.length, 1);
  const reference = originals[0];
  assert.equal(reference.url, statementUrl);
  assert.equal(reference.editorialUrl, editorialUrl);
  assert.equal(reference.verification, 'independent-analysis');
  assert.equal(reference.sourceDate, '2020-09-19');
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
  assert.equal(feature.publicationDate, '2020-09-19');
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

test('later numeric evidence and an explicit independent review resolve Biscuits without rewriting its initial uncertainty', async () => {
  const [audit, plan, historical] = await Promise.all([
    json('data/corpus-audits/ioi-2020.json'), json('data/coverage-plan.json'), historicalAudit(),
  ]);
  assert.equal(audit.snapshot.techniqueMetadataCount, 466);
  assert.equal(audit.snapshot.flowGraphCount, 431);
  assert.equal(audit.snapshot.flowSha256, 'febb504779ef0f015744f28713408fc1d02eae89509fa910677c898bf2151ca7');
  assert.equal(audit.snapshot.techniqueSha256, '2cd200111fd58479f6c5afb64de1d000558143ed201ae20a995c5aaf43bb116e');
  assert.deepEqual(audit.status, historical.status, 'first-pass counts remain historical, including one reviewed solution');
  assert.equal(audit.status.solutionReviewedCount, 1);
  assert.equal(audit.status.unconfirmedCount, 5);
  assert.equal(audit.status.globalCoverageComplete, false);
  const original = audit.records.find(matches);
  const old = historical.records.find(matches);
  assert(original && old);
  const { subsequentSolutionReviews, subsequentSourceVerifications, resolution, ...initial } = original;
  assert.deepEqual(initial, old, 'preserve every initial feature, source status, missing proof and stopped path');
  assert.equal(original.constraints.numericBoundsVerified, false);
  assert.equal(original.reviewStatus, 'unconfirmed');
  assert.equal(original.classification, 'unconfirmed');
  assert.equal(original.materialStatus.officialEditorialVerified, false);
  assert(original.technicalFindings.unconfirmedDetails.length > 0);
  assert.equal(isCorpusSolutionReviewed(initial), false);
  assert.equal(isCorpusSolutionReviewed({ ...initial, resolution }), false);
  assert.equal(isCorpusSolutionReviewed(original), true);
  assert.equal(original.contest.date, '2020-09-19');
  assert.equal(original.contest.day, 2);
  assert.equal(original.contest.exactDateVerified, true);
  assert.equal(original.difficulty, null);
  assert.equal(resolution.status, 'verified');
  assert.deepEqual(resolution.techniqueIds, [id]);
  assert(resolution.notes.trim().length > 0);
  const gap = plan.knownGaps.find(row => row.id === original.gap.id);
  assert(gap);
  assert.equal(gap.state, 'resolved');
  assert.equal(gap.problemId, problemId);
  assert.deepEqual(gap.techniqueIds, [id]);
  assert.deepEqual(original.gap.neededTechniqueIds, [id]);
  const review = subsequentSolutionReviews.find(row => row.verification === 'independent-analysis');
  assert(review);
  assert.equal(review.reviewStatus, 'verified');
  assert.equal(review.collectionStatus, 'statement-and-independent-analysis-verified');
  assert.equal(review.materialStatus.officialEditorialVerified, false, 'unread official formula images are not promoted');
  assert.equal(review.statementUrl, statementUrl);
  assert.match(review.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(review.originalNumericBoundsVerified, true);
  assert.equal(review.originalProblemScopeVerified, true);
  assert(review.evidenceUrls.includes(statementUrl));
  assert(review.evidenceUrls.includes(boundsUrl));
  assert(review.notes.trim().length > 0);
  for (const invalid of [{ verification: 'official-tag' }, { reviewStatus: 'unconfirmed' },
    { statementUrl: editorialUrl }, { reviewedAt: undefined }, { notes: '' }, { evidenceUrls: [] }])
    assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: [{ ...review, ...invalid }] }), false);
  const evidence = subsequentSourceVerifications.find(row => row.statementUrl === boundsUrl);
  assert(evidence);
  assert.equal(evidence.status, 'verified');
  assert.equal(evidence.kind, 'authorized-statement-translation');
  assert.equal(evidence.sourceVerified, true);
  assert.equal(evidence.originalNumericBoundsVerified, true);
  assert.equal(evidence.archiveIndexUrl, archiveUrl);
  assert.equal(evidence.originalEnglishStatementUrl, statementUrl);
  assert.equal(evidence.initialAuditPreserved, true);
  const bounds = evidence.originalConstraints;
  assert.deepEqual(bounds.k, { minimum: 1, maximum: 60 });
  assert.deepEqual(bounds.q, { minimum: 1, maximum: 1000 });
  assert.deepEqual(bounds.x, { minimum: 1, maximum: '1000000000000000000' });
  assert.deepEqual(bounds.a_i, { minimum: 0, maximum: '1000000000000000000' });
  assert.equal(bounds.weightedSupply.expression, 'sum(a[i] * 2^i)');
  assert.equal(bounds.weightedSupply.maximum, '1000000000000000000');
  assert.equal(bounds.weightedSupply.atLeastPerCall, true);
  assert.equal(bounds.denomination, '2^i');
  assert.equal(bounds.independentCalls, true);
  assert(bounds.k.maximum <= 63);
  const signedMaximum = (1n << 63n) - 1n;
  for (const bound of [bounds.x.maximum, bounds.a_i.maximum, bounds.weightedSupply.maximum])
    assert(BigInt(bound) < signedMaximum, 'all original scalar and weighted inputs fit the published API');
  assert(BigInt(bounds.weightedSupply.maximum) + 1n < signedMaximum, 'the IOI int64 return value fits');
  assert.equal(evidence.originalMaxBitWidth, 60);
  assert.equal(evidence.originalStateBound, 60 * 61 / 2);
  assert.equal(evidence.originalMaxRecursionDepth, 61);
  assert(evidence.apiContainmentProof.length > 0);
});
