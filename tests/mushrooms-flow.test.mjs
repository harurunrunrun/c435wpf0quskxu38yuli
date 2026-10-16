import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '/home/admin2/flowchartcp/site/scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '/home/admin2/flowchartcp/site/scripts/lib/corpus-progress.mjs';

const site = '/home/admin2/flowchartcp/site';
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const id = 'interactive-transition-count-species-decision-trees';
const problemId = 'ioi2020_mushrooms';
const domain = 'interactive-oracles';
// Fixed from problem features before examining the registered example walk.
const prefix = ['transition-count'];
const graphId = 'two-species-transition-count-conditions';
const guards = ['two-species-anchor', 'distinct-transition-count', 'budget'];
const statementUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/day2-mushrooms-ISC.pdf';
const editorialUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/mushrooms-solutions-ISC.pdf';
const boundsUrl = 'https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2020-mushrooms/statement/mushrooms-en.pdf';
const modelUrl = 'https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2020-mushrooms/solution/decision-tree-endagorion.cpp';
const candidates = value => value.current.techniques ?? [];
const matches = row => String(row.source).toLowerCase() === 'ioi' && row.problemId === problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-mushrooms-flow-'));
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

test('the fixed transition-count entrance requires all three premises and selects one article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15);
  assert.equal(flow.getGraph(domain).entry, true);
  const before = walk(flow, prefix.slice(0, -1));
  assert.equal(before.graph.id, 'interactive-oracles');
  assert.equal(before.current.id, 'response');
  assert(flow.getNodeOptions(before.current).some(option => option.id === 'transition-count'));
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
  for (const term of [/二種類|二種|2種類/, /0/, /相異|重複/, /変化/, /226/, /20000|20.?000|2万/, /100000|100.?000|10万/])
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

test('all previous 503 records preserve every answer, target, label and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 504);
  const previous = walks.slice(0, 503);
  assert.equal(digest(previous), '548fed4d6a193d2cc21d8074be465d7864a20982c8c66db0c636082a1ef4edbc');
  // Expected hashes were computed by replaying raw frozen JSON, without the
  // product walker, using the preserved pre-Mushrooms 449-graph JSON.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const technique of row.expectedTechniqueIds) assert(candidates(value).includes(technique));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'a48140da1fd2af3c982338a40ebcf2e8ef03dda41443aaf68f97be2e9e57dd23');
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
  assert.equal(digest(text), 'c044a9f4558f878ab37b586a53b3688e1f180c927b3c7a29ad1da51f441c8621');
});

test('the complete visible article, dated original, numeric evidence and canonical example agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/transition-species-problem-features.json'), json('data/problem-walks.json'),
  ]);
  const registered = metadata.filter(row => row.id === id);
  assert.equal(registered.length, 1);
  const technique = registered[0];
  assert.equal(technique.kind, 'technique');
  assert.equal(technique.status, 'reviewed');
  assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
  for (const source of [statementUrl, editorialUrl, boundsUrl, modelUrl]) assert(technique.sources.includes(source));
  const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
  assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
    ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
  assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
  assert(!/<(?:details|summary)\b/i.test(article));
  assert(article.includes(`techniqueId="${id}"`));
  for (const source of technique.sources) assert(article.includes(source));
  for (const term of [/226/, /40306/, /110/, /TWO_SPECIES_IOI_GRADER/, /identify_five/,
    /count_two_species_from_transition_queries/, /count_mushrooms/]) assert.match(article, term);
  assert(article.includes('#ifdef TWO_SPECIES_IOI_GRADER'), 'original adapter stays opt-in for standalone callback linking');
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

test('a fifth solution is established by explicit later review while the old four and all first-pass history stay intact', async () => {
  const [audit, plan] = await Promise.all([json('data/corpus-audits/ioi-2020.json'), json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.techniqueMetadataCount, 466);
  assert.equal(audit.snapshot.flowGraphCount, 431);
  for (const [name, hash] of Object.entries({ flow: 'febb504779ef0f015744f28713408fc1d02eae89509fa910677c898bf2151ca7',
    technique: '2cd200111fd58479f6c5afb64de1d000558143ed201ae20a995c5aaf43bb116e' })) {
    assert.equal(audit.snapshot[name + 'Sha256'], hash);
    const bytes = gunzipSync(await readFile(path.join(site, audit.snapshot[name + 'SnapshotFile'])));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), hash);
  }
  assert.equal(digest(audit.status), '05e56539ff6c0862c5a3079a6ce5bd060cb49533ea7ea60a45011b767d40b930');
  assert.equal(audit.status.solutionReviewedCount, 1);
  assert.equal(audit.status.unconfirmedCount, 5);
  assert.equal(audit.status.globalCoverageComplete, false);
  const initial = audit.records.map(row => Object.fromEntries(Object.entries(row)
    .filter(([key]) => !['resolution', 'subsequentSolutionReviews', 'subsequentSourceVerifications'].includes(key))));
  assert.equal(digest(initial), '1ebcba91471a48b4bf627dfcb898e660f67c7be631e43f2397a5e2ee43fa2438');
  assert.deepEqual(initial.filter(isCorpusSolutionReviewed).map(row => row.problemId), ['ioi2020_tickets']);
  const previous = {
    ioi2020_supertrees: '38b8a37ac59a67718c5922d0fc19e32c020cc1458924dd6a70e3750372cedba0',
    ioi2020_tickets: '83c8c5b16c6761f6480e4b51740766e0d4e05ec9fbe1d000dbdf10bcadc7012b',
    ioi2020_biscuits: 'd5559d5ca96ea0422e2e5ad742c93cd674b624c7965a40667071753e86e2712c',
    ioi2020_stations: 'b39bf270e90dd53d227d26f6bb776d189a5a0e5288e808bffcb359df5fdfc698',
  };
  for (const [problem, hash] of Object.entries(previous)) {
    const row = audit.records.find(record => record.problemId === problem);
    assert(row);
    assert.equal(digest(row), hash, 'preserve old solution/source reviews, resolution and initial record');
    assert.equal(row.resolution.status, 'verified');
    assert.equal(isCorpusSolutionReviewed(row), true);
  }
  const original = audit.records.find(matches);
  assert(original);
  const { subsequentSolutionReviews, subsequentSourceVerifications, resolution, ...firstPass } = original;
  assert.equal(digest(firstPass), '753e57856184c7df02a0d22a3017e87e3fe1a4a3786130ff54d8d25b5b9db3fa');
  assert.equal(original.constraints.numericBoundsVerified, false);
  assert.equal(original.reviewStatus, 'unconfirmed');
  assert.equal(original.classification, 'unconfirmed');
  assert.equal(original.materialStatus.officialEditorialVerified, false);
  assert(original.technicalFindings.unconfirmedDetails.length > 0);
  assert.equal(isCorpusSolutionReviewed(firstPass), false);
  assert.equal(isCorpusSolutionReviewed({ ...firstPass, resolution }), false);
  assert.equal(isCorpusSolutionReviewed(original), true);
  const reviewed = audit.records.filter(isCorpusSolutionReviewed).map(row => row.problemId);
  for (const problem of [...Object.keys(previous), problemId]) assert(reviewed.includes(problem));
  // A later Plants review may add the sixth result; this test fixes the first
  // five explicit reviews rather than preventing subsequent corpus progress.
  assert(reviewed.length >= 5);
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
  assert.equal(review.materialStatus.solution, 'retrieved-and-reviewed');
  assert.equal(review.materialStatus.officialEditorialVerified, false);
  assert.equal(review.statementUrl, statementUrl);
  assert.match(review.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(review.originalNumericBoundsVerified, true);
  assert.equal(review.originalProblemScopeVerified, true);
  assert(review.evidenceUrls.includes(statementUrl));
  assert(review.evidenceUrls.includes(boundsUrl));
  assert(review.evidenceUrls.includes(modelUrl));
  assert(review.notes.trim().length > 0);
  for (const invalid of [{ verification: 'official-tag' }, { reviewStatus: 'unconfirmed' },
    { statementUrl: editorialUrl }, { reviewedAt: undefined }, { notes: '' }, { evidenceUrls: [] },
    { materialStatus: { ...review.materialStatus, solution: 'retrieved-partially-reviewed' } },
    { verification: 'official-editorial', materialStatus: { ...review.materialStatus, officialEditorialVerified: false } }])
    assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: [{ ...review, ...invalid }] }), false,
      'a resolution, retrieval or explicit negative review status cannot confirm a missing solution');
  const evidence = subsequentSourceVerifications.find(row => row.kind === 'national-committee-statement-distribution');
  assert(evidence);
  assert.equal(evidence.status, 'verified');
  assert.equal(evidence.statementUrl, statementUrl);
  assert.equal(evidence.originalNumericBoundsVerified, true);
  assert(evidence.evidenceUrls.includes(boundsUrl));
  assert.equal(evidence.initialAuditUnconfirmedAndNumericFalsePreserved, true);
  assert.equal(evidence.apiContainsEntireOriginalRange, true);
  const bounds = evidence.originalConstraints;
  assert.deepEqual(bounds.n, { minimum: 2, maximum: 20000 });
  assert.equal(bounds.anchor, 'species[0]=A');
  assert.equal(bounds.queryLength, '2..n');
  assert.equal(bounds.queryIndices, 'distinct integers0..n-1');
  assert.equal(bounds.hardQueryLimit, 20000);
  assert.equal(bounds.fullScoreQueryLimit, 226);
  assert.equal(bounds.totalQueryLengthLimit, 100000);
  assert(bounds.adaptive.trim().length > 0);
});
