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
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-ioi-local-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// These feature paths and guards were specified independently of the newly
// registered problem walks. The example records cannot select their own route.
const tasks = [
  {
    id: 'median-ticket-extreme-selection-round-decomposition', task: 'tickets',
    domain: 'flow-matching', prefix: ['quantity-goals', 'median-rounds'],
    graph: 'median-ticket-round-conditions', guards: ['color-rounds', 'median-deviation', 'bounds'],
    verification: 'editorial', featureVerification: 'official-editorial', day: 1, date: '2020-09-16',
    terms: [/偶数/, /各色|全.*色/, /一枚/, /中央値/, /最大/, /割当|割り/, /非負|0\.\.10/],
  },
  {
    id: 'tree-local-routing-alternating-dfs-labels', task: 'stations',
    domain: 'graphs', prefix: ['rooted-tree-goals', 'tree-range', 'ancestors-and-paths', 'local-routing-labels'],
    graph: 'tree-local-routing-label-conditions', guards: ['tree-two-phases', 'local-next-hop', 'bounds'],
    verification: 'independent-analysis', featureVerification: 'independent-analysis', day: 2, date: '2020-09-19',
    terms: [/木/, /別プロセス/, /隣接/, /保存|引き継/, /一歩/, /同じ.*変換|単調増加/],
  },
  {
    id: 'simple-path-count-matrix-tree-cycle-construction', task: 'supertrees',
    domain: 'graphs', prefix: ['network-connection', 'path-count-table'],
    graph: 'simple-path-count-matrix-conditions', guards: ['simple-graph', 'exact-path-counts', 'size'],
    verification: 'independent-analysis', featureVerification: 'independent-analysis', day: 1, date: '2020-09-16',
    terms: [/無向/, /単純路/, /自己ループ/, /多重辺/, /補助頂点/, /正確/, /代表.*2|2個/],
  },
].map(item => ({ ...item, problemId: 'ioi2020_' + item.task,
  statementUrl: `https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/day${item.day}-${item.task}-ISC.pdf`,
  editorialUrl: `https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/${item.task}-solutions-ISC.pdf` }));
const ids = tasks.map(item => item.id);
const candidates = value => value.current.techniques ?? [];
const matches = (row, item) => String(row.source).toLowerCase() === 'ioi' && row.problemId === item.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
async function collections(expression) {
  return (await Promise.all((await readdir(path.join(site, 'data')))
    .filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function walk(flow, item, choices) {
  const value = flow.walkFromRoot(choices, item.domain);
  assert.equal(value.consumed, choices.length, `${item.domain}/${choices.join('/')}: consume every fixed answer`);
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
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the full answer label is readable');
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`href="/flowchartcp/techniques/${id}/"`), 'the result links to its article');
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges, 'no answer edges are added');
  return svg;
}

test('the three fixed feature paths require all nine applicability guards before selecting their single article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15, 'the original fields remain the top-level entrances');
  for (const item of tasks) {
    assert.equal(flow.getGraph(item.domain).entry, true);
    for (let guard = 0; guard < 3; ++guard) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard]);
      assert.notEqual(value.graph.entry, true);
      assert.equal(flow.getFlowDomainId(flow.initialState(item.graph)), item.domain);
      assert(ids.every(id => !candidates(value).includes(id)));
      assert.deepEqual(flow.getNodeOptions(value.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
    }
    const value = walk(flow, item, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id]);
    for (const term of item.terms) assert.match(JSON.stringify(value.graph), term);
    checkSvg(flow, value.graph);
  }
});

test('no and unknown at each of the nine guards require condition checking and never assert a new technique', async () => {
  const { flow } = await implementation;
  for (const item of tasks) for (let guard = 0; guard < 3; ++guard)
    for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(value.graph.id, 'condition-check', `${item.graph}/${item.guards[guard]}/${answer}`);
      assert.equal(value.current.type, 'question');
      assert(ids.every(id => !candidates(value).includes(id)));
    }
});

test('question and diagram sharing restore every new history, highlights and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of tasks) {
    const histories = [[...item.prefix, 'yes', 'yes', 'yes']];
    for (let guard = 0; guard < 3; ++guard) for (const answer of ['no', 'unknown'])
      histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item, choices).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0, 'Back terminates');
        assert.equal(flow.getFlowDomainId(state), item.domain, 'retain the originating field');
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

test('the pre-integration 493 records preserve every answer step and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 496);
  const previous = walks.slice(0, 493);
  // The terminal hash was produced from the independently preserved old flow
  // JSON, including target IDs, rather than the implementation under test.
  assert.equal(digest(previous), 'f32a87a244f1bcd71061f2a3099c7a1c8761da5506bccaf630201a4bd8341c21');
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const id of row.expectedTechniqueIds) assert(candidates(value).includes(id));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '98ab7da647b862f8af517c71e0d01b2564791341862badb2f251350cebae8c27');
});

test('the three visible reusable articles, references, dated originals and example walks agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/ioi-local-construction-problem-features.json'), json('data/problem-walks.json'),
  ]);
  assert.equal(features.length, 3);
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
    assert.equal(reference.verification, item.verification);
    assert.equal(reference.sourceDate, item.date);
    assert.equal(reference.difficulty, null, 'an unverified difficulty is not invented');
    assert(reference.evidence.trim().length > 0);
    const matchingFeatures = features.filter(row => matches(row, item));
    assert.equal(matchingFeatures.length, 1);
    const feature = matchingFeatures[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.evidenceUrl, item.editorialUrl);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, item.featureVerification);
    assert.equal(feature.publicationDate, item.date);
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, item.domain);
    assert.deepEqual(example.choices, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(example.statementUrl, item.statementUrl);
    assert.equal(example.reviewStatus, 'verified');
    assert.equal(example.verificationKind, item.verification);
    assert.equal(example.cutoffVerification, 'contest-before-cutoff');
    assert.deepEqual(example.features, feature.features);
    assert.deepEqual(walk(flow, item, example.choices).steps
      .map(({ graph, node, answer }) => ({ graph, node, answer })), example.steps);
  }
});

test('explicit subsequent independent reviews resolve two proofs while the original one-of-six audit remains intact', async () => {
  const [audit, plan, historicalBytes] = await Promise.all([
    json('data/corpus-audits/ioi-2020.json'), json('data/coverage-plan.json'),
    readFile(path.join(site, 'tests/fixtures/ioi-three-resolution-before-biscuits.json.gz')).then(gunzipSync),
  ]);
  assert.equal(createHash('sha256').update(historicalBytes).digest('hex'),
    '9208ac8515a979dd9ec7213d990a95c2a1b4aac736916f364b072b00cea460a2');
  const historical = JSON.parse(historicalBytes);
  assert.equal(audit.snapshot.techniqueMetadataCount, 466);
  assert.equal(audit.snapshot.flowGraphCount, 431);
  assert.equal(audit.snapshot.flowSha256, 'febb504779ef0f015744f28713408fc1d02eae89509fa910677c898bf2151ca7');
  assert.equal(audit.snapshot.techniqueSha256, '2cd200111fd58479f6c5afb64de1d000558143ed201ae20a995c5aaf43bb116e');
  assert.equal(audit.status.solutionReviewedCount, 1);
  assert.equal(audit.status.officialEditorialVerifiedCount, 1);
  assert.equal(audit.status.unconfirmedCount, 5);
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, false);
  assert.equal(audit.status.globalCoverageComplete, false);
  assert.deepEqual(audit.records.filter(row => isCorpusSolutionReviewed({ ...row, subsequentSolutionReviews: undefined }))
    .map(row => row.problemId), ['ioi2020_tickets']);
  // The completed three-article stage is immutable evidence. Later articles
  // may resolve more tasks while these three live reviews remain required.
  assert.deepEqual(historical.records.filter(isCorpusSolutionReviewed).map(row => row.problemId).sort(),
    ['ioi2020_stations', 'ioi2020_supertrees', 'ioi2020_tickets']);
  for (const item of tasks) {
    const original = audit.records.find(row => matches(row, item));
    assert(original);
    assert.equal(original.contest.date, item.date);
    assert.equal(original.contest.day, item.day);
    assert.equal(original.contest.exactDateVerified, true);
    assert.equal(original.difficulty, null);
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id]);
    assert(original.resolution.notes.trim().length > 0);
    const gap = plan.knownGaps.find(row => row.id === original.gap.id);
    assert(gap);
    assert.equal(gap.state, 'resolved');
    assert.equal(gap.problemId, item.problemId);
    assert.deepEqual(gap.techniqueIds, [item.id]);
    if (item.task === 'tickets') continue;
    assert.equal(original.reviewStatus, 'unconfirmed');
    assert.equal(original.classification, 'unconfirmed');
    assert.equal(original.materialStatus.officialEditorialVerified, false);
    assert(original.technicalFindings.unconfirmedDetails.length > 0);
    const initial = { ...original, subsequentSolutionReviews: undefined };
    assert.equal(isCorpusSolutionReviewed(initial), false, 'a resolution alone does not confirm a missing proof');
    const reviews = original.subsequentSolutionReviews;
    assert.equal(reviews.length, 1);
    const review = reviews[0];
    assert.equal(review.verification, 'independent-analysis');
    assert.equal(review.reviewStatus, 'verified');
    assert.equal(review.collectionStatus, 'statement-and-independent-analysis-verified');
    assert.equal(review.statementUrl, item.statementUrl);
    assert.match(review.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
    assert(review.evidenceUrls.includes(item.statementUrl));
    assert(review.notes.trim().length > 0);
    assert.equal(isCorpusSolutionReviewed(original), true);
    for (const invalid of [{ verification: 'official-tag' }, { reviewStatus: 'unconfirmed' },
      { statementUrl: item.editorialUrl }, { reviewedAt: undefined }, { notes: '' }, { evidenceUrls: [] }])
      assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: [{ ...review, ...invalid }] }), false,
        'only a matching explicit positive review can resolve the historical uncertainty');
  }
  for (const task of ['plants', 'biscuits', 'mushrooms']) {
    const row = historical.records.find(item => item.problemId === 'ioi2020_' + task);
    assert.equal(row.reviewStatus, 'unconfirmed');
    assert.equal(row.resolution, undefined);
    assert.equal(isCorpusSolutionReviewed(row), false);
  }
});
