import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const root = new URL('../', import.meta.url);
const runFile = promisify(execFile);
const auditFile = 'data/corpus-audits/usaco-2021-february-us-open-platinum.json';
const snapshotFile = 'research/snapshots/usaco-2021-february-us-open-platinum-baseline.tar.gz';
const probeFile = 'research/probes/usaco-2021-spring-research-checks.py';
const reviewFile = 'research/probes/usaco-2021-spring-independent-review.json';
const bytes = file => readFile(new URL(file, root));
const json = async file => JSON.parse(await bytes(file));
const sha = raw => createHash('sha256').update(raw).digest('hex');
const digest = value => sha(JSON.stringify(value));
const originalRow = row => Object.fromEntries(Object.entries(row).filter(([key]) =>
  !['resolution', 'subsequentSolutionReviews'].includes(key)));
const ids = ['1116', '1117', '1118', '1140', '1141', '1142'];
const titles = ['No Time to Dry', 'Minimizing Edges', 'Counting Graphs',
  'United Cows of Farmer John', 'Routing Schemes', 'Balanced Subsets'];
const needed = ['monotone-paint-stroke-links-offline-containment',
  'parity-walk-profile-layer-greedy-realization', 'parity-walk-profile-layer-inclusion-exclusion-count',
  'interval-unique-endpoints-singleton-middle-active-lazy',
  'almost-dag-edge-routing-pairing-frontier-cycle-count', 'orthogonally-convex-row-interval-phase-prefix-dp'];
const routes = [
  ['ranges', ['aggregate-goals', 'static'], 'range-static', 'kind'],
  ['graphs', ['network-connection'], 'graphs-network-connection', 'shortest'],
  ['graphs', ['network-connection'], 'graphs-network-connection', 'shortest'],
  ['ranges', ['aggregate-goals', 'window'], 'range-window', 'wanted'],
  ['graphs', ['walk-goals'], 'graphs-walk-goals', 'shortest'],
  ['grid-arrangements', ['color-numbers'], 'grid-color-numbers', 'goal'],
];
const hashes = {
  "selection": "960189899621527450af262e08e138630bf3d93bd739d92fcf635a3a4f97145d",
  "status": "97752d09dd39a60e68c477ec9216a12fa0b3e8398f2749be56634e0843e843ae",
  "snapshot": "4bfedec6db163c92714071c9946f52adda77adae2df8fb615047ed558dabad0c",
  "records": "bc2de4b45dc7d449a1f4726c15c6887140484526f3941b731d0ed8c02b16941e",
  "tar": "be645b2f3192848bd482d5034e8fe79eca2e637e730d8ac893a6d5e5501c3913",
  "ledger": "94fe3a533a7bea30ceab38e0134388265176d409c2ee414cfa5b1e7b4ea65b5c",
  "flow": "8e65013cc25d38030aed330d1f08d812f25cedd7dc78e33990386e03f238d256",
  "walk": "6a2fbef69e87ea9ae44c8b19d281c46c478293cdee4c80897ee32e7b3ee3ce90"
};
const rowHashes = [
  "554f68fae3151dd6be983fcff4b3987c04d02edc3492eb59149f3f4185ddcf5a",
  "ee435cc2b54eae6677e934ef6ea085ae2e9bcfa6aaea340b500c2c32919bb27b",
  "519fc1d3721438c908bea5e0aa30c0686c2a1f3f19931ec5b6d9682faec2de16",
  "9fdaf3fe570da04437cf095af59e8291d3c380c2008bd117a5b89df7ffef2508",
  "3897087c137a8327a18f2b8d119618b7e1af49a2b91ae701d5bb5e4b7a74b071",
  "5d6de994524e9ce65e4817170c0d4b578379c40c0e519935d1f7c1efaa24125f"
];

// This archive contains every historical article and raw JSON, not just their
// manifest. Read regular ustar members in memory; never execute archive paths.
function tarMembers(raw) {
  const files = new Map();
  for (let offset = 0; offset + 512 <= raw.length;) {
    const header = raw.subarray(offset, offset + 512);
    if (header.every(byte => byte === 0)) break;
    const string = (start, end) => header.subarray(start, end).toString('utf8').replace(/\0.*$/s, '');
    const octal = (start, end) => parseInt(string(start, end).trim() || '0', 8);
    const expected = octal(148, 156);
    let checksum = 0;
    for (let i = 0; i < 512; ++i) checksum += i >= 148 && i < 156 ? 32 : header[i];
    assert.equal(checksum, expected, 'tar header checksum');
    assert.equal(String.fromCharCode(header[156]), '0', 'only regular historical files');
    const prefix = string(345, 500), name = (prefix ? prefix + '/' : '') + string(0, 100);
    assert(name && !name.startsWith('/') && !name.split('/').includes('..'));
    assert(!files.has(name), 'unique archive member');
    const size = octal(124, 136);
    assert(Number.isSafeInteger(size) && size >= 0 && offset + 512 + size <= raw.length);
    files.set(name, raw.subarray(offset + 512, offset + 512 + size));
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  return files;
}
let archivePromise;
function archive() {
  return archivePromise ??= (async () => {
    const compressed = await bytes(snapshotFile);
    assert.equal(sha(compressed), hashes.tar);
    const files = tarMembers(gunzipSync(compressed));
    const getJson = file => { assert(files.has(file), file); return JSON.parse(files.get(file)); };
    return { files, getJson };
  })();
}
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));
// A separate raw interpreter preserves the first audit even when the current
// product walker, graphs and article resolutions advance.
function replay(graphMap, row) {
  let graph = graphMap.get(row.entryGraphId), node = graph?.nodes.find(n => n.id === graph.root);
  assert.equal(graph?.entry, true);
  const steps = [], transitions = [], seen = new Set();
  let used = 0;
  for (;;) {
    assert(node, row.problemId);
    const key = JSON.stringify([graph.id, node.id, used]);
    assert(!seen.has(key), 'no raw route cycle'); seen.add(key);
    if (node.type === 'route') {
      transitions.push({ fromGraphId: graph.id, fromNodeId: node.id, toGraphId: node.graph });
      graph = graphMap.get(node.graph); assert(graph);
      node = graph.nodes.find(n => n.id === graph.root); continue;
    }
    if (node.type !== 'question' || used === row.choices.length) break;
    const answer = row.choices[used++], selected = options(node).find(o => o.id === answer);
    assert(selected, row.problemId + ': valid original answer');
    steps.push({ graphId: graph.id, nodeId: node.id, question: node.title, answer, answerLabel: selected.label });
    node = graph.nodes.find(n => n.id === node.answers[answer]);
  }
  assert.equal(used, row.choices.length);
  return { steps, transitions, current: { graphId: graph.id, nodeId: node.id,
    type: node.type, title: node.title, options: options(node), techniques: node.techniques ?? [] } };
}
const withoutSeconds = value => Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'seconds'));
const sortedJson = value => JSON.stringify(Object.fromEntries(Object.keys(value).sort().map(key => [key,
  value[key] && typeof value[key] === 'object' && !Array.isArray(value[key])
    ? JSON.parse(sortedJson(value[key])) : value[key]])));

test('the fixed six identities, initial records, selection, status and snapshot remain immutable', async () => {
  const audit = await json(auditFile);
  assert.equal(audit.corpusId, 'usaco-2021-february-us-open-platinum');
  assert.equal(audit.cutoff, '2026-10-14');
  assert.equal(digest(audit.selection), hashes.selection);
  assert.equal(digest(audit.status), hashes.status);
  assert.equal(digest(audit.snapshot), hashes.snapshot);
  const initial = audit.records.map(originalRow);
  assert.equal(digest(initial), hashes.records);
  assert.deepEqual(initial.map(row => row.problemId), ids);
  assert.deepEqual(initial.map(row => row.title), titles);
  assert.equal(audit.selection.fixedBeforeTechniqueSearch, true);
  assert.equal(audit.selection.fixedProblemListComplete, true);
  assert.equal(audit.selection.problemCount, 6);
  assert.deepEqual(audit.selection.problemIds, ids);
  assert.equal(audit.selection.noProblemSubstitution, true);
  assert.equal(audit.selection.sameNamedGoldAndOtherSourceProblemsExcluded, true);
  assert(audit.selection.sequence.length >= 6);
  assert.match(audit.selection.sequence[0], /official final-results/);
  for (const [i, row] of initial.entries()) {
    assert.equal(digest(row), rowHashes[i]);
    assert.equal(row.source, 'usaco');
    assert.equal(row.contest.division, 'Platinum');
    assert.equal(row.contest.number, i % 3 + 1);
    assert.equal(row.sourceDate, i < 3 ? '2021-02' : '2021');
    assert.equal(row.contest.datePrecision, i < 3 ? 'month' : 'year');
    assert.equal(row.contest.exactDateVerified, false);
    assert.equal(row.difficulty, null);
    assert.equal(row.statementUrl, `https://usaco.org/index.php?page=viewproblem2&cpid=${ids[i]}`);
    assert.equal(row.editorialUrl, `https://usaco.org/current/data/sol_prob${i % 3 + 1}_platinum_${i < 3 ? 'feb' : 'open'}21.html`);
    assert.equal(row.constraints.numericBoundsVerified, true);
  }
  // Later work may append results without rewriting any historical field.
  const later = initial.map(row => ({ ...row, resolution: { status: 'example' }, subsequentSolutionReviews: [] }));
  assert.deepEqual(later.map(originalRow), initial);
});

test('the permanent tar retains all 620 raw bytes and original four ledgers, including 488 full MDX articles', async () => {
  const { files, getJson } = await archive();
  assert.equal(files.size, 624);
  const before = getJson('hashes-before.json'), after = getJson('hashes-after.json');
  assert.deepEqual(before, after);
  assert.equal(Object.keys(before).length, 620);
  assert.equal(sha(files.get('SHA256SUMS')), hashes.ledger);
  const ledger = files.get('SHA256SUMS').toString('utf8').trimEnd().split('\n');
  assert.equal(ledger.length, 620);
  for (const line of ledger) {
    const match = /^([0-9a-f]{64})  (.+)$/.exec(line); assert(match);
    assert.equal(before[match[2]], match[1]);
  }
  for (const [file, expected] of Object.entries(before)) {
    assert(files.has(file), file);
    assert.equal(sha(files.get(file)), expected, file);
  }
  assert.deepEqual([...files.keys()].filter(file => !(file in before)).sort(),
    ['SHA256SUMS', 'hashes-after.json', 'hashes-before.json', 'manifest.json']);
  assert.equal([...files.keys()].filter(file => /^src\/content\/docs\/techniques\/[^/]+\.mdx$/.test(file)).length, 488);
  const metadata = [...files.keys()].filter(file => /^data\/techniques-.*\.json$/.test(file)).flatMap(getJson);
  const references = [...files.keys()].filter(file => /^data\/references-.*\.json$/.test(file)).flatMap(getJson);
  assert.equal(metadata.length, 488); assert.equal(new Set(metadata.map(row => row.id)).size, 488);
  assert.equal(references.length, 509);
  assert.equal(getJson('data/flows.json').length, 455);
  assert.equal(getJson('data/problem-walks.json').length, 509);
  assert.equal(sha(files.get('data/flows.json')), hashes.flow);
  assert.equal(sha(files.get('data/problem-walks.json')), hashes.walk);
  const manifest = getJson('manifest.json');
  assert.equal(manifest.articleCount, 488); assert.equal(manifest.flowGraphCount, 455); assert.equal(manifest.walkCount, 509);
  assert.equal(manifest.stableBeforeCopyAfter, true);
});

test('six historical feature walks preserve all eight questions, answer labels, options and first gaps', async () => {
  const audit = await json(auditFile), { getJson } = await archive();
  const graphs = getJson('data/flows.json'), graphMap = new Map(graphs.map(graph => [graph.id, graph]));
  assert.equal(graphs.filter(graph => graph.entry).length, 15);
  let questions = 0;
  for (const [i, live] of audit.records.entries()) {
    const row = originalRow(live), [entry, choices, graphId, nodeId] = routes[i];
    assert.equal(row.entryGraphId, entry); assert.deepEqual(row.choices, choices);
    const found = replay(graphMap, row);
    assert.deepEqual(found.steps, row.steps);
    assert.equal(digest(found.steps), row.navigationReplay.stepsSha256);
    assert.deepEqual(found.transitions, row.navigationReplay.routeTransitions);
    assert.deepEqual(found.current, row.initialReached);
    assert.deepEqual(found.current, row.canonicalRouteEnd);
    assert.equal(found.current.graphId, graphId); assert.equal(found.current.nodeId, nodeId);
    assert.equal(row.gap.firstMissingGraphId, graphId); assert.equal(row.gap.firstMissingNodeId, nodeId);
    assert.equal(row.gap.stopNodeType, found.current.type);
    assert.equal(row.gap.currentQuestion, found.current.title);
    assert.deepEqual(row.gap.currentOptions, found.current.options);
    assert.deepEqual(row.actualReachedTechniqueIds, []); assert.deepEqual(row.expectedTechniqueIds, []);
    questions += found.steps.length;
  }
  assert.equal(questions, 8);
});

test('all eighteen nearby article comparisons use retained MDX bytes and retain specific scope differences', async () => {
  const audit = await json(auditFile), { files, getJson } = await archive();
  const metadata = [...files.keys()].filter(file => /^data\/techniques-.*\.json$/.test(file)).flatMap(getJson);
  const existing = new Set(metadata.map(row => row.id));
  const unique = new Set(); let comparisons = 0;
  for (const [i, row] of audit.records.entries()) {
    assert.deepEqual(row.gap.neededTechniqueIds, [needed[i]]);
    assert(!existing.has(needed[i])); assert.equal(row.gap.implementationNeeded, true);
    assert.equal(row.relatedArticleReview.length, 3);
    for (const related of row.relatedArticleReview) {
      assert(existing.has(related.techniqueId));
      assert.equal(sha(files.get(related.file)), related.sha256);
      assert(related.scopeMismatch.trim().length > 30);
      assert.deepEqual(related.reviewedSections, ['scope', 'applicability', 'proof', 'API contract']);
      const body = files.get(related.file).toString('utf8');
      assert(body.includes('## 使う場面') && body.includes('## 適用条件') && body.includes('## 実装'));
      unique.add(related.techniqueId); ++comparisons;
    }
  }
  assert.equal(comparisons, 18); assert.equal(unique.size, 15);
});

test('research six of six remains zero completed APIs and zero coverage, independent of later resolutions', async () => {
  const audit = await json(auditFile), rows = audit.records.map(originalRow);
  assert.equal(rows.filter(isCorpusStatementReviewed).length, 6);
  assert.equal(rows.filter(isCorpusSolutionReviewed).length, 6);
  assert(rows.every(row => row.classification === 'missing-technique'));
  for (const row of rows) {
    assert.equal(row.verification, 'independent-analysis');
    assert.equal(row.materialStatus.solution, 'retrieved-and-reviewed');
    assert.equal(row.technicalFindings.chosenFullSolutionVerified, true);
    assert.equal(row.technicalFindings.fullImplementationValidated, false);
    assert.deepEqual(row.technicalFindings.unconfirmedRequiredLemmas, []);
    assert(row.technicalFindings.independentProofSupplement.length >= 3);
    assert(row.technicalFindings.implementationRequirements.length >= 3);
    assert.equal(isCorpusSolutionReviewed({ ...row, materialStatus: { ...row.materialStatus, solution: 'unreviewed' } }), false);
  }
  for (const key of ['fixedCorpusResearchComplete', 'firstPassAuditComplete']) assert.equal(audit.status[key], true);
  for (const key of ['fixedCorpusCoverageComplete', 'globalCoverageComplete']) assert.equal(audit.status[key], false);
  assert.equal(audit.status.solutionReviewedCount, 6); assert.equal(audit.status.missingTechniqueCount, 6);
  assert.equal(audit.status.coveredCount, 0); assert.equal(audit.status.completeProductionApiCount, 0);
  assert.equal(audit.status.registeredTechniqueCount, 0); assert.equal(audit.status.requiredSolutionLemmasUnconfirmedCount, 0);
  for (const key of ['productionCodeCompiled', 'productionSanitizersRun', 'productionMaximumCasesRun']) assert.equal(audit.validation[key], false);
  assert.equal(audit.records[4].technicalFindings.unconfirmedOptionalApproaches.length, 1);
});

test('retained independent review preserves exact source precision, probe counters and the separate terminal PIE oracle', async () => {
  const review = await json(reviewFile), audit = await json(auditFile);
  assert.equal(review.decision, 'accepted-as-fixed-corpus-research-audit');
  assert.deepEqual(review.substantiveFindings, []); assert.deepEqual(review.unconfirmedRequiredMajorLemmas, []);
  assert.deepEqual(review.fixedSelection.problemIds, ids);
  assert.equal(review.snapshot.rawFiles, 620);
  assert.equal(review.rawNavigation.recordsReplayed, 6); assert.equal(review.rawNavigation.questionAndAnswerLabelsChecked, 8);
  assert.equal(review.nearbyScopeReview.frozenArticleReferences, 18);
  assert.equal(review.nearbyScopeReview.uniqueFrozenArticles, 15);
  assert.equal(review.nearbyScopeReview.counterexampleToMissingTechniqueClassificationFound, false);
  assert.deepEqual(review.separateIndependentExperiments, { graphsN0to5: 33867, requiredDegreeConditions: 21 });
  assert.equal(review.completionBoundary.coveredCount, 0); assert.equal(review.completionBoundary.productionReusableApiCount, 0);
  const result = review.researchProbeRerun.result;
  assert.equal(result['1116'].arrays, 1092); assert.equal(result['1116'].allSubintervals, 19956);
  assert.equal(result['1116'].literalPaintingBFSStates, 5460);
  assert.equal(result['1117'].allConnectedUndirectedGraphsWithOptionalLoopsN2to5, 23940);
  assert.equal(result['1117'].completeInfiniteWalkLanguageGroups, 932);
  assert.equal(result['1117'].literalParityFeasibilityComparisons, 595764);
  assert.equal(result['1118'].completeInfiniteWalkLanguageGroups, 932);
  assert.equal(result['1140'].allArraysLength1to8AlphabetAtMost3, 9833);
  assert.equal(result['1140'].allLeaderTriplesTested, 461322);
  assert.equal(result['1141'].allDirectedSimpleGraphsN2to4WithAtMostTwoBackwardEdges, 1468);
  assert.equal(result['1141'].allDegreeBalancedRoleConfigurationsWithSender, 574);
  assert.equal(result['1141'].validInstances, 562); assert.equal(result['1141'].balancedButNoValidScheme, 12);
  assert.equal(result['1141'].allLiteralTrailSchemes, 1481);
  assert.equal(result['1142'].everyNonemptyBitmapEveryH_W1to4, 74938);
  assert.equal(result['1142'].allGrassBoardsN1to3AndRandom4, 1556);
  for (const row of audit.records) assert.deepEqual(row.technicalFindings.probeResult, result[row.problemId]);
  assert.equal(sha(sortedJson(result)), '915c586f90b6224b194dbe3b5b9cb68c1770f8b7147a6168614525e3446a559b');
});

test('the permanent research probe reruns from its retained raw archive without temporary author files', async () => {
  const script = (await bytes(probeFile)).toString('utf8');
  assert(!script.includes('/tmp/' + 'flowchartcp-'), 'no dependency on author workspace');
  assert(script.includes('from usaco_spring_snapshot import open_snapshot'));
  const loader = (await bytes('research/probes/usaco_spring_snapshot.py')).toString('utf8');
  assert(loader.includes('usaco-2021-february-us-open-platinum-baseline.tar.gz'));
  assert(!loader.includes('/tmp/' + 'flowchartcp-'));
  const preservation = await json('research/snapshots/usaco-2021-spring-preservation.json');
  assert.equal(sha(await bytes(probeFile)), preservation.normalizedProbeSha256.research);
  assert.equal(preservation.allRawFilesRetained, true);
  assert.equal(preservation.rawBaselineFiles, 620);
  const run = await runFile('python3', [fileURLToPath(new URL(probeFile, root))], {
    cwd: fileURLToPath(root), encoding: 'utf8', timeout: 60000, maxBuffer: 8 * 1024 * 1024,
  });
  const start = run.stdout.indexOf('{'); assert(start >= 0);
  const observed = withoutSeconds(JSON.parse(run.stdout.slice(start)));
  const review = await json(reviewFile);
  assert.deepEqual(observed, review.researchProbeRerun.result);
  assert.equal(observed.navigation.recordsReplayed, 6);
  assert.equal(observed.navigation.frozenFilesShaRechecked, 620);
});

test('coverage plan keeps its eighth fixed six-problem selection and the six independently researched gaps', async () => {
  const audit = await json(auditFile), plan = await json('data/coverage-plan.json');
  const index = plan.corpora.findIndex(item => item.id === audit.corpusId);
  assert.equal(index, 7);
  const selection = plan.corpora[index];
  assert.equal(selection.auditFile, auditFile); assert.equal(selection.expectedProblems, 6);
  assert.deepEqual(selection.fixedProblems.map(row => [row.source, row.problemId]), ids.map(id => ['usaco', id]));
  assert.equal(audit.cutoff, plan.cutoff);
  const gaps = plan.knownGaps.filter(row => row.discoveredBy === audit.corpusId);
  assert.equal(gaps.length, 6);
  for (const [i, row] of audit.records.entries()) {
    const gap = gaps.find(item => item.id === row.gap.id); assert(gap);
    assert.equal(gap.problemId, ids[i]);
    assert.deepEqual(gap.techniqueIds, [needed[i]]);
  }
});
