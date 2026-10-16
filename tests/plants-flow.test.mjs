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
const id = 'cyclic-window-height-poset-two-neighbor-doubling';
const problemId = 'ioi2020_plants';
const domain = 'graphs';
// Fixed from problem features before examining the registered example walk.
const prefix = ['group-constraints', 'cyclic-ranks'];
const graphId = 'cyclic-window-height-order-conditions';
const guards = ['fixed-cyclic-window', 'all-configurations', 'bounds'];
const statementUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/day1-plants-ISC.pdf';
const editorialUrl = 'https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/plants-solutions-ISC.pdf';
const boundsUrl = 'https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2020-plants/statement/plants-en.pdf';
const modelUrl = 'https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2020-plants/solution/plants-original-ac.cpp';
const candidates = value => value.current.techniques ?? [];
const matches = row => String(row.source).toLowerCase() === 'ioi' && row.problemId === problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-plants-flow-'));
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

test('the fixed cyclic-ranks entrance requires every premise and selects one article', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15);
  assert.equal(flow.getGraph(domain).entry, true);
  const before = walk(flow, prefix.slice(0, -1));
  assert.equal(before.graph.id, 'graphs-group-constraints');
  assert.equal(before.current.id, 'shortest');
  assert(flow.getNodeOptions(before.current).some(option => option.id === 'cyclic-ranks'));
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
  for (const term of [/円周/, /時計回り/, /K/, /固定/, /全配置|全ての配置/, /相異|異なり/, /曖昧/, /200000|20万/])
    assert.match(JSON.stringify(value.graph), term);
  checkSvg(flow, flow.getGraph(domain));
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
  for (const currentGraph of ['graphs', 'graphs-group-constraints', graphId]) {
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

test('all previous 506 records preserve every answer, target, label and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 507);
  const previous = walks.slice(0, 506);
  assert.equal(digest(previous), 'a03e62ef60243ffd54577157336b0a9f5289b1a85f7850dbb6882af9f104c0c5');
  // Expected hashes were computed by replaying raw frozen JSON, without the
  // product walker, using the preserved pre-Plants 452-graph JSON.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const technique of row.expectedTechniqueIds) assert(candidates(value).includes(technique));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'dcfbb1a284653f4ca761758f6d93f9116616ee6251a7b9dcd93c7cb7d7e1aa68');
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
  assert.equal(digest(text), '65bafe5b7e4ca6aa1f1e72d175780b9de44ea9cf6de5d9df938d58ba5fe7c5a0');
});

test('the complete visible article, dated original, numeric evidence and canonical example agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/cyclic-window-order-problem-features.json'), json('data/problem-walks.json'),
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
  for (const term of [/200000/, /CyclicWindowOrder/, /representative_rank/, /compare/]) assert.match(article, term);
  const originals = references.filter(row => row.techniqueId === id && matches(row));
  assert.equal(originals.length, 1);
  const reference = originals[0];
  assert.equal(reference.url, statementUrl);
  assert.equal(reference.editorialUrl, editorialUrl);
  assert.equal(reference.verification, 'independent-analysis');
  assert.equal(reference.sourceDate, '2020-09-16');
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
  assert.equal(feature.publicationDate, '2020-09-16');
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


const oldGroupNodeIds = ["shortest", "check", "uncertain", "flow-route", "fallback", "small-groups-route", "constraints-route", "tree-color-union-route", "three-size-two-connected-route"];
const oldGroupOptions = [{"id": "assignment", "label": "組を選ぶ・容量を割り当てる"}, {"id": "partition-small", "label": "少数の頂点を、内部の全組に辺があるグループへ分ける"}, {"id": "constraints", "label": "二つの値の禁止組・偶奇・差の条件を満たせるか"}, {"id": "tree-color-union", "label": "木の色を丸ごと併合し、一色の全頂点を連結にする"}, {"id": "three-size-two-connected", "label": "全頂点を指定の三サイズへ分け、少なくとも二集合を連結にする"}, {"id": "unknown", "label": "わからない"}];
const oldGroupAnswers = {"assignment": "flow-route", "unknown": "check", "partition-small": "small-groups-route", "constraints": "constraints-route", "tree-color-union": "tree-color-union-route", "three-size-two-connected": "three-size-two-connected-route"};
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;

test('the existing group-constraint choices, order, targets and old nodes stay intact with one guarded new result', async () => {
  const { flow } = await implementation;
  const group = structuredClone(flow.getGraph('graphs-group-constraints'));
  assert.deepEqual(group.nodes.filter(node => oldGroupNodeIds.includes(node.id)).map(node => node.id), oldGroupNodeIds);
  const question = group.nodes.find(node => node.id === group.root);
  const previousIds = oldGroupOptions.map(option => option.id);
  assert.deepEqual(flow.getNodeOptions(question).filter(option => previousIds.includes(option.id)), oldGroupOptions);
  for (const [answer, target] of Object.entries(oldGroupAnswers)) assert.equal(question.answers[answer], target);
  assert.equal(flow.getNodeOptions(question).filter(option => option.id === prefix[1]).length, 1);
  const route = group.nodes.find(node => node.id === question.answers[prefix[1]]);
  assert.equal(route.type, 'route');
  assert.equal(route.graph, graphId);
  group.nodes = group.nodes.filter(node => oldGroupNodeIds.includes(node.id));
  question.options = question.options.filter(option => previousIds.includes(option.id));
  question.answers = Object.fromEntries(Object.keys(oldGroupAnswers).map(answer => [answer, question.answers[answer]]));
  assert.equal(digest(stable(group)), '3e2a52e90eea04436dc8fd64e6b95b704583bd6e678ed49fe5242772a0a90cb5');
  const outputs = flow.graphs.flatMap(graph => graph.nodes.filter(node => (node.techniques ?? []).includes(id))
    .map(node => ({ graph: graph.id, node: node.id, type: node.type })));
  assert.deepEqual(outputs, [{ graph: graphId, node: 'result', type: 'result' }]);
});

test('only explicit later independent proof confirms Plants, preserving the original five reviews and every initial field', async () => {
  const [audit, plan, evidence] = await Promise.all([json('data/corpus-audits/ioi-2020.json'),
    json('data/coverage-plan.json'), json('research/technique-verifications/' + id + '.json')]);
  assert.equal(audit.snapshot.techniqueMetadataCount, 466);
  assert.equal(audit.snapshot.flowGraphCount, 431);
  for (const [kind, hash] of Object.entries({ flow: 'febb504779ef0f015744f28713408fc1d02eae89509fa910677c898bf2151ca7',
    technique: '2cd200111fd58479f6c5afb64de1d000558143ed201ae20a995c5aaf43bb116e' })) {
    assert.equal(audit.snapshot[kind + 'Sha256'], hash);
    const raw = gunzipSync(await readFile(path.join(site, audit.snapshot[kind + 'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'), hash);
  }
  assert.equal(digest(audit.status), '05e56539ff6c0862c5a3079a6ce5bd060cb49533ea7ea60a45011b767d40b930');
  assert.equal(digest(audit.selection), '89ffee7d700aa064f258ddb974d10e2a7edd54d7d918b6e0f00b41833b93d638');
  const initial = audit.records.map(row => Object.fromEntries(Object.entries(row).filter(([key]) =>
    !['resolution', 'subsequentSolutionReviews', 'subsequentSourceVerifications'].includes(key))));
  assert.equal(digest(initial), '1ebcba91471a48b4bf627dfcb898e660f67c7be631e43f2397a5e2ee43fa2438');
  assert.deepEqual(initial.filter(isCorpusSolutionReviewed).map(row => row.problemId), ['ioi2020_tickets']);
  assert.equal(audit.status.solutionReviewedCount, 1);
  assert.equal(audit.status.unconfirmedCount, 5);
  assert.equal(audit.status.coveredCount, 0);
  assert.equal(audit.status.globalCoverageComplete, false);
  const previous = {"ioi2020_supertrees": "38b8a37ac59a67718c5922d0fc19e32c020cc1458924dd6a70e3750372cedba0", "ioi2020_tickets": "83c8c5b16c6761f6480e4b51740766e0d4e05ec9fbe1d000dbdf10bcadc7012b", "ioi2020_biscuits": "d5559d5ca96ea0422e2e5ad742c93cd674b624c7965a40667071753e86e2712c", "ioi2020_mushrooms": "290e6f3455e72484ea29053701ddd09e3bc81479a6a55c238073e4eaa174d179", "ioi2020_stations": "b39bf270e90dd53d227d26f6bb776d189a5a0e5288e808bffcb359df5fdfc698"};
  for (const [problem, hash] of Object.entries(previous)) {
    const row = audit.records.find(row => row.problemId === problem);
    assert.equal(digest(row), hash, 'all previous source/solution/resolution fields stay unchanged');
    assert.equal(isCorpusSolutionReviewed(row), true);
    assert.equal(row.resolution.status, 'verified');
  }
  const row = audit.records.find(matches), first = initial.find(matches);
  assert(row && first);
  assert.equal(digest(first), '7430a6a0cb427bfdc3c0980b08d7ca5f6c143466317d0d6f2b908987468db97c');
  assert.equal(first.classification, 'unconfirmed');
  assert.equal(first.reviewStatus, 'unconfirmed');
  assert.equal(first.constraints.numericBoundsVerified, false);
  assert.equal(first.materialStatus.officialEditorialVerified, false);
  assert(first.technicalFindings.unconfirmedDetails.length > 0);
  assert.equal(first.contest.date, '2020-09-16');
  assert.equal(first.contest.day, 1);
  assert.equal(first.difficulty, null);
  assert.equal(first.gap.firstMissingGraphId, 'graphs-group-constraints');
  assert.equal(first.gap.firstMissingNodeId, 'shortest');
  assert.equal(isCorpusSolutionReviewed(first), false);
  assert.equal(isCorpusSolutionReviewed({ ...first, resolution: row.resolution }), false);
  assert.equal(isCorpusSolutionReviewed(row), true);
  assert.equal(audit.records.filter(isCorpusSolutionReviewed).length, 6);
  assert.equal(audit.records.filter(record => record.resolution?.status === 'verified').length, 6);
  assert.equal(row.resolution.status, 'verified');
  assert.deepEqual(row.resolution.techniqueIds, [id]);
  const gap = plan.knownGaps.find(gap => gap.id === first.gap.id);
  assert.equal(gap.state, 'resolved');
  assert.equal(gap.problemId, problemId);
  assert.deepEqual(gap.techniqueIds, [id]);
  const review = row.subsequentSolutionReviews.find(review => review.verification === 'independent-analysis');
  assert.equal(review.reviewStatus, 'verified');
  assert.equal(review.collectionStatus, 'statement-and-independent-analysis-verified');
  assert.equal(review.materialStatus.solution, 'retrieved-and-reviewed');
  assert.equal(review.materialStatus.officialEditorialVerified, false);
  assert.equal(review.statementUrl, statementUrl);
  assert.match(review.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
  assert(review.evidenceUrls.includes(statementUrl));
  assert(review.evidenceUrls.includes(boundsUrl));
  assert(review.evidenceUrls.includes(modelUrl));
  assert(review.notes.trim().length > 0);
  for (const mutation of [{ verification: 'official-tag' }, { reviewStatus: 'unconfirmed' },
    { statementUrl: editorialUrl }, { reviewedAt: undefined }, { notes: '' }, { evidenceUrls: [] },
    { materialStatus: { ...review.materialStatus, solution: 'retrieved-partially-reviewed' } },
    { verification: 'official-editorial', materialStatus: { ...review.materialStatus, officialEditorialVerified: false } }])
    assert.equal(isCorpusSolutionReviewed({ ...row, subsequentSolutionReviews: [{ ...review, ...mutation }] }), false);
  const source = row.subsequentSourceVerifications.find(source => source.kind === 'official-committee-distributed-original-pdf-images');
  assert.equal(source.status, 'verified');
  assert.equal(source.statementUrl, statementUrl);
  assert.equal(source.numericBoundsVerified, true);
  assert(source.evidenceUrls.includes(boundsUrl));
  assert(source.notes.trim().length > 0);
  const verified = evidence.sourceVerification;
  assert.equal(verified.numericBoundsVerified, true);
  assert.equal(verified.apiContainsEntireOriginalRange, true);
  assert.equal(verified.initialAuditNumericUnconfirmedPreserved, true);
  assert.equal(verified.initialAuditProofUnconfirmedPreserved, true);
  assert.equal(verified.officialEditorialFullFormulaTranscriptionVerified, false);
  assert.deepEqual(verified.sourceBounds, { N: '2..200000', K: '2..N', Q: '1..200000',
    r: '0..K−1 at all original positions', query: '0<=x<y<N',
    height: 'all distinct; only relative order matters', consistency: 'at least one valid configuration exists' });
  assert.equal(evidence.integration.normalizedSolutionStatus, 'retrieved-and-reviewed');
  assert.equal(evidence.subsequentSolutionReview.materialStatus.solution, 'independently-proved-and-validated');
  assert.equal(evidence.integration.originalAuthorSidecarStatusPreserved, true);
  assert.deepEqual(evidence.proof.unconfirmedLemmas, []);
});
