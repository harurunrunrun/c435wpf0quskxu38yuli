import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const base = new URL('../', import.meta.url);
const bytes = file => readFile(new URL(file, base));
const json = async file => JSON.parse(await bytes(file));
const sha = raw => createHash('sha256').update(raw).digest('hex');
const digest = value => sha(JSON.stringify(value));
const tasks = ['combo', 'seats', 'werewolf', 'doll', 'highway', 'meetings'];
const ids = tasks.map(task => 'ioi2018_' + task);
const hashes = {
  flow: '51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e',
  technique: '74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be',
  originalManifest: 'bc97c90a87d59f384a931ca5e315799372169b8ac5a78fbb4b3bced5d9a600bf',
  permanentManifest: '5f4e3a6d77568ffdd1fbd25f6632c6520bc06b09ec5713b5fcf82385c8cca104',
  manifestEntries: 'ccdb633a48e808042bd11343f074010512219d5406b5e3d47f872e55e6648111',
  records: 'ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523',
  status: '8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3',
  selection: '1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b',
};
const rowHashes = [
  '3991559f70d0799732507459248e61b295d2a68b798f57540e3d05c56d17dd6f',
  'f22eb738077dee6981bf355d08cd603b2b8ad1a68859f59a28a8c44419a201ce',
  '32f7d8bc07f59d3870dd9b2f942f552558bc62addbdbbda436e82c541c6d3df4',
  '61b52a8a13abc3debaad454cc46ce4dddd838e5951ca6e30d774c8e3e8a0f707',
  '5558584faa4db3c128bbd6161674fc92c8911e7611efcb0b950b740076308c38',
  '08b6f50130255e86ec5eece7d5fb2c532413b94fb2d26e96060555d3acefc768',
];
const needed = [
  'unique-first-symbol-prefix-oracle-multiplexing',
  'dynamic-grid-prefix-rectangle-corner-minimum-count',
  'two-threshold-component-merge-trees-rectangle-intersection',
  'alternating-switch-bit-reversal-pruned-router',
  'binary-weight-distance-oracle-edge-split-endpoint-search',
  'cartesian-prefix-meeting-cost-single-cross-envelope',
];
const routes = [
  ['interactive-oracles', ['other'], 'interactive-oracles', 'general-result'],
  ['grid-arrangements', ['color-numbers'], 'grid-color-numbers', 'goal'],
  ['graphs', ['network-connection', 'connectivity', 'static-or-add', 'static'], 'connectivity-static-or-add', 'components'],
  ['thinking', ['operation-goals'], 'thinking-operation-goals', 'reason-task'],
  ['interactive-oracles', ['other'], 'interactive-oracles', 'general-result'],
  ['ranges', ['aggregate-goals', 'static', 'aggregate-forms'], 'range-static-aggregate-forms', 'kind'],
];
const numeric = [
  { N: '1..2000', queryLength: '0..4N', hardQueryLimit: 8000, fullScoreQueries: '<=N+2',
    alphabet: 'A,B,X,Y; first symbol never repeats', adaptive: false },
  { H: 'positive', W: 'positive', HW: '<=1000000', Q: '1..50000',
    coordinates: '0<=R_i<H,0<=C_i<W, all distinct', swap: '0<=a,b<HW and a!=b' },
  { N: '2..200000', M: 'N−1..400000', Q: '1..200000', graph: 'simple undirected connected',
    queries: '0<=L<=S<N,0<=E<=R<N,S!=E,L<=R' },
  { M: '1..100000', N: '1..200000', A: '1..M, repeats allowed', hardSwitchLimit: 400000,
    stateChangesLimit: 20000000, fullScoreSwitches: 'S<=N+log2(N)' },
  { N: '2..90000', M: '1..130000', A_B: '1<=A<B<=1000000000', graph: 'simple undirected connected',
    hiddenEndpoints: '0<=S,T<N,S!=T, nonadaptive', hardQueryLimit: 100, fullScoreQueries: 50, partialScoreQueries: '51..52' },
  { N: '1..750000', Q: '1..750000', heights: '1..1000000000',
    queries: '0<=L<=R<N; all query endpoint pairs distinct', costBound: '<=750000000000000' },
];
const numericPdf = [
  'contest1/IND-combo.pdf', 'contest1/TWN-seats.pdf', 'contest1/CUB-werewolf.pdf',
  'contest2/SYR-doll.pdf', 'contest2/HKG-highway.pdf', 'contest2/TWN-meetings.pdf',
];
const originalRow = row => Object.fromEntries(Object.entries(row).filter(([key]) =>
  !['resolution', 'subsequentSolutionReviews', 'subsequentSourceVerifications'].includes(key)));
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));

// Replay only the retained raw JSON. Neither current product flow data nor
// walkFromRoot can rewrite the initial questions, answer labels or stops.
function replay(graphMap, row) {
  let graph = graphMap.get(row.entryGraphId), node = graph?.nodes.find(n => n.id === graph.root);
  assert.equal(graph?.entry, true);
  let used = 0;
  const steps = [], seen = new Set();
  for (;;) {
    assert(node, row.problemId);
    const key = JSON.stringify([graph.id, node.id, used]);
    assert(!seen.has(key), 'raw replay has no route loop');
    seen.add(key);
    if (node.type === 'route') {
      graph = graphMap.get(node.graph);
      assert(graph);
      node = graph.nodes.find(n => n.id === graph.root);
      continue;
    }
    if (node.type !== 'question' || used === row.choices.length) break;
    const answer = row.choices[used++], option = options(node).find(o => o.id === answer);
    assert(option);
    steps.push({ graphId: graph.id, nodeId: node.id, question: node.title, answer, answerLabel: option.label });
    node = graph.nodes.find(n => n.id === node.answers[answer]);
  }
  assert.equal(used, row.choices.length);
  return { steps, current: { graphId: graph.id, nodeId: node.id, type: node.type,
    title: node.title, options: options(node), techniques: node.techniques ?? [] } };
}

test('the six official tasks, dates, numeric evidence and every original row/status/provenance stay fixed', async () => {
  const audit = await json('data/corpus-audits/ioi-2018.json');
  assert.equal(audit.corpusId, 'ioi-2018');
  assert.equal(audit.cutoff, '2026-10-14');
  assert.equal(audit.selection.expectedProblems, 6);
  assert.equal(audit.selection.fixedBeforeTechniqueSearch, true);
  assert.equal(digest(audit.selection), hashes.selection);
  assert.equal(digest(audit.status), hashes.status);
  const initial = audit.records.map(originalRow);
  assert.equal(digest(initial), hashes.records);
  // Recover the original serialization from the normalized references. These
  // historical path strings are hash input only; no temporary files are read.
  const sourceAudit = structuredClone(audit);
  sourceAudit.records = initial;
  delete sourceAudit.preservation;
  const originalTemporaryRoot = '/tmp/' + 'flowchartcp-ioi2018-snapshot';
  Object.assign(sourceAudit.snapshot, {
    manifestFile: originalTemporaryRoot + '/manifest.json',
    manifestFileSha256: hashes.originalManifest,
    flowSnapshotFile: originalTemporaryRoot + '/flows.json.gz',
    techniqueSnapshotFile: originalTemporaryRoot + '/techniques-aggregate.json.gz',
    initialWorkspaceDirectory: originalTemporaryRoot,
  });
  for (const key of ['originalManifestFileSha256', 'permanentRawSnapshotCount',
    'allHistoricalRawFilesPermanentlyStored', 'allHistoricalMdxPermanentlyStored']) delete sourceAudit.snapshot[key];
  sourceAudit.validation.script = '/tmp/' + 'flowchartcp-ioi2018-validate.mjs';
  assert.equal(sha(JSON.stringify(sourceAudit, null, 2) + '\n'),
    'c497743e29f92ac8e8d9604b1e34dd85ee99a6c24cf610423aa05dabda1c3b5d');
  for (const rows of [initial, audit.selection.fixedProblems]) {
    assert.deepEqual(rows.map(row => row.problemId), ids);
    assert.equal(new Set(rows.map(row => row.problemId)).size, 6);
    assert(rows.every(row => row.source === 'ioi'));
  }
  assert.deepEqual(audit.selection.countEvidence.practiceTasksExcluded,
    ['bubblesort2', 'road_service', 'timecard', 'xylophone']);
  assert.equal(audit.selection.countEvidence.implementationNoticesExcluded, true);
  assert.equal(audit.selection.countEvidence.officialIndexUrl, 'https://ioi2018.jp/competition/tasks/');
  assert(Date.parse(audit.snapshot.createdAtUTC) < Date.parse(audit.selection.fixedAt));
  for (const [index, row] of initial.entries()) {
    const day = index < 3 ? 1 : 2;
    assert.equal(digest(row), rowHashes[index]);
    assert.equal(row.officialTaskId, tasks[index]);
    assert.equal(row.contest.day, day);
    assert.equal(row.contest.date, day === 1 ? '2018-09-03' : '2018-09-05');
    assert.equal(row.contest.exactDateVerified, true);
    assert.equal(row.difficulty, null);
    assert.equal(row.statementUrl, `https://www2.ioi-jp.org/ioi/2018/tasks/day${day}-${tasks[index]}.pdf`);
    assert.equal(row.editorialUrl, row.statementUrl.replace('.pdf', '-review.pdf'));
    assert.equal(row.hostStatementUrl, `https://ioi2018.jp/tasks/contest${day}/day${day}-${tasks[index]}.pdf`);
    assert.equal(row.constraints.numericBoundsVerified, true);
    assert.deepEqual(row.constraints.values, numeric[index]);
    assert(row.constraints.numericEvidenceUrls.includes('https://ioi2018.jp/tasks/' + numericPdf[index]));
    assert.equal(row.materialStatus.numericBounds, 'verified-in-organizer-hosted-translations-search-text');
    assert.equal(row.materialStatus.visualDetails, 'not-claimed');
    assert.equal(row.technicalFindings.verification, 'independent-analysis');
    assert(row.technicalFindings.sourceUrls.includes(row.editorialUrl));
    assert(row.technicalFindings.sourceUrls.includes('https://www.algonotes.com/en/solutions-ioi2018/'));
    assert.match(row.technicalFindings.editorialProvenance, /当日の公式Reviewそのものとは呼ばない/);
  }
  assert.equal(audit.materials.supplementRevision, '2020-03');
  assert.equal(audit.limits.primaryPdfVisualInspectionClaimed, false);
});

test('the original 607-SHA ledger and both distinct manifest byte hashes survive, while only two raw snapshots are retained', async () => {
  const audit = await json('data/corpus-audits/ioi-2018.json');
  const manifestRaw = await bytes(audit.snapshot.manifestFile);
  assert.equal(audit.snapshot.manifestFile, 'research/snapshots/ioi-2018-manifest.json');
  assert.equal(sha(manifestRaw), hashes.permanentManifest);
  const manifest = JSON.parse(manifestRaw);
  const sourceRaw = Buffer.from(manifest.originalManifestRawBase64, 'base64');
  assert.equal(sourceRaw.length, manifest.originalManifestByteCount);
  assert.equal(sha(sourceRaw), hashes.originalManifest);
  const source = JSON.parse(sourceRaw);
  assert.deepEqual(manifest.files, source.files);
  assert.equal(digest(manifest.files), hashes.manifestEntries);
  assert.equal(manifest.entriesSha256, hashes.manifestEntries);
  assert.equal(manifest.files.length, 607);
  assert.equal(new Set(manifest.files.map(file => file.path)).size, 607);
  assert.equal(manifest.files.filter(file => /^src\/content\/docs\/techniques\/.*\.mdx$/.test(file.path)).length, 482);
  assert.equal(manifest.originalManifestFileSha256, hashes.originalManifest);
  assert.equal(audit.snapshot.originalManifestFileSha256, hashes.originalManifest);
  assert.equal(audit.snapshot.manifestFileSha256, hashes.permanentManifest);
  assert.equal(audit.snapshot.manifestEntriesSha256, hashes.manifestEntries);
  assert.equal(manifest.snapshotRoot, 'research/snapshots');
  assert.equal(manifest.preservation.historicalFrozenRawFileCount, 607);
  assert.equal(manifest.preservation.permanentRawSnapshotCount, 2);
  assert.equal(manifest.preservation.allHistoricalRawFilesPermanentlyStored, false);
  assert.equal(manifest.preservation.allHistoricalMdxPermanentlyStored, false);
  assert.equal(audit.snapshot.allHistoricalMdxPermanentlyStored, false);
  assert.equal(audit.snapshot.articleCount, 482);
  assert.equal(audit.snapshot.specificTechniqueCount, 404);
  assert.equal(audit.snapshot.flowGraphCount, 449);
  assert.equal(audit.snapshot.walkCount, 503);
  for (const kind of ['flow', 'technique']) {
    const file = `research/snapshots/ioi-2018-${kind}.json.gz`;
    assert.equal(audit.snapshot[kind + 'SnapshotFile'], file);
    const raw = gunzipSync(await bytes(file));
    assert.equal(sha(raw), hashes[kind]);
    assert.equal(audit.snapshot[kind + 'Sha256'], hashes[kind]);
    const retained = manifest.preservation.permanentSnapshots.find(item => item.kind === kind);
    assert.equal(retained.file, file);
    assert.equal(retained.rawSha256, hashes[kind]);
    assert.equal(retained.rawBytes, raw.length);
    assert.equal(JSON.parse(raw).length, kind === 'flow' ? 449 : 482);
  }
});

test('all six first missing nodes, full answer labels and generic outputs replay only against the frozen 449 graphs', async () => {
  const audit = await json('data/corpus-audits/ioi-2018.json');
  const graphs = JSON.parse(gunzipSync(await bytes(audit.snapshot.flowSnapshotFile)));
  const graphMap = new Map(graphs.map(graph => [graph.id, graph]));
  assert.equal(graphs.filter(graph => graph.entry).length, 15);
  const metadata = JSON.parse(gunzipSync(await bytes(audit.snapshot.techniqueSnapshotFile)));
  const existing = new Set(metadata.map(row => row.id));
  assert.equal(existing.size, 482);
  assert.equal(metadata.filter(row => row.kind === 'technique').length, 404);
  const manifest = await json(audit.snapshot.manifestFile);
  const ledger = new Map(manifest.files.map(row => [row.path, row]));
  for (const [index, live] of audit.records.entries()) {
    const row = originalRow(live);
    const [entry, choices, graphId, nodeId] = routes[index];
    assert.equal(row.entryGraphId, entry);
    assert.deepEqual(row.choices, choices);
    const observed = replay(graphMap, row);
    assert.deepEqual(observed.steps, row.steps);
    assert.equal(digest(observed.steps), row.navigationReplay.stepsSha256);
    assert.deepEqual(observed.current, row.canonicalRouteEnd);
    assert.equal(observed.current.graphId, graphId);
    assert.equal(observed.current.nodeId, nodeId);
    assert.equal(row.gap.firstMissingGraphId, graphId);
    assert.equal(row.gap.firstMissingNodeId, nodeId);
    assert.equal(row.gap.stopNodeType, observed.current.type);
    assert.equal(row.gap.currentQuestion, observed.current.title);
    assert.deepEqual(row.gap.currentOptions, observed.current.options);
    assert.deepEqual(row.actualReachedTechniqueIds, observed.current.techniques);
    assert.deepEqual(row.expectedTechniqueIds, []);
    assert.equal(row.classification, 'missing-technique');
    assert.equal(row.gap.implementationNeeded, true);
    assert.deepEqual(row.gap.neededTechniqueIds, [needed[index]]);
    assert(row.gap.reason.trim().length > 0);
    for (const id of row.gap.existingRelatedTechniqueIds) assert(existing.has(id), id);
    for (const id of row.gap.neededTechniqueIds) assert(!existing.has(id), id);
    for (const related of row.relatedArticleReview) {
      assert(existing.has(related.techniqueId));
      assert.equal(ledger.get(related.file)?.sha256, related.sha256);
      assert(related.scopeMismatch.trim().length > 0);
    }
  }
  assert.deepEqual(audit.records[0].actualReachedTechniqueIds, ['interactive']);
  assert.deepEqual(audit.records[2].actualReachedTechniqueIds, ['bfs', 'union-find']);
  assert.deepEqual(audit.records[4].actualReachedTechniqueIds, ['interactive']);
});

test('six verified research methods remain six missing articles with zero completed implementations or coverage', async () => {
  const audit = await json('data/corpus-audits/ioi-2018.json');
  const initial = audit.records.map(originalRow);
  const counts = { 'missing-technique': 0, 'missing-route': 0, unconfirmed: 0, covered: 0 };
  for (const row of initial) {
    ++counts[row.classification];
    assert(isCorpusStatementReviewed(row));
    assert(isCorpusSolutionReviewed(row));
    assert.deepEqual(row.technicalFindings.unconfirmedDetails, []);
    assert(row.technicalFindings.independentProofSupplement.length >= 3);
    assert.equal(row.technicalFindings.fullImplementationValidated, false);
    assert(row.technicalFindings.remainingImplementationValidation.length > 0);
    for (const mutation of [{ reviewStatus: 'unconfirmed' },
      { materialStatus: { ...row.materialStatus, solution: 'retrieved-partially-reviewed' } },
      { technicalFindings: { ...row.technicalFindings, verification: 'official-tag' } }])
      assert.equal(isCorpusSolutionReviewed({ ...row, ...mutation }), false);
  }
  assert.deepEqual(counts, { 'missing-technique': 6, 'missing-route': 0, unconfirmed: 0, covered: 0 });
  assert.equal(audit.status.statementVerifiedCount, initial.filter(isCorpusStatementReviewed).length);
  assert.equal(audit.status.solutionReviewedCount, initial.filter(isCorpusSolutionReviewed).length);
  assert.equal(audit.status.numericBoundsVerifiedCount, initial.filter(row => row.constraints.numericBoundsVerified).length);
  assert.equal(audit.status.missingTechniqueCount, counts['missing-technique']);
  assert.equal(audit.status.missingRouteCount, counts['missing-route']);
  assert.equal(audit.status.unconfirmedCount, counts.unconfirmed);
  assert.equal(audit.status.coveredCount, counts.covered);
  assert.equal(audit.status.fullImplementationValidatedCount, 0);
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, true);
  assert.equal(audit.status.fixedCorpusCoverageComplete, false);
  assert.equal(audit.status.globalCoverageComplete, false);
  assert.equal(audit.status.articleResolutionComplete, false);
});

test('retained research results and independent review keep the equal-height counterexample and limited probe scope explicit', async () => {
  const audit = await json('data/corpus-audits/ioi-2018.json');
  const [probe, review] = await Promise.all([
    json(audit.preservation.researchCheckResults), json(audit.preservation.independentReviewResults),
  ]);
  const withoutTime = value => Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'seconds'));
  assert.deepEqual(withoutTime(probe), withoutTime(audit.validation.probeResults));
  assert.deepEqual(withoutTime(probe), withoutTime(review.probes));
  assert.equal(probe.combo.allLegalStringsLength1to8, 13120);
  assert.equal(probe.seats.allNonemptyBitmapsUpTo4x4, 74938);
  assert.equal(probe.seats.everySwap, 21784);
  assert.equal(probe.werewolf.allConnectedSimpleGraphsN2to5, 771);
  assert.equal(probe.werewolf.allValidQueries, 115398);
  assert.equal(probe.doll.allTwoTriggerSequencesLength1to8, 510);
  assert.equal(probe.doll.maximumN, 200000);
  assert.equal(probe.doll.switchesAtMaximum, 200012);
  assert.equal(probe.doll.changesAtMaximum, 3836286);
  assert.equal(probe.highway.allPairsTimesThreeTollSettings, 22563);
  assert.equal(probe.highway.fullQueryBound, 50);
  assert.equal(probe.meetings.allHeightArraysN1to7Values1to3, 3279);
  assert.equal(probe.meetings.allIntervalQueries, 81192);
  assert.equal(probe.meetings.allCartesianPrefixEntries, 63084);
  assert.equal(review.status, 'complete-no-substantive-findings');
  assert.equal(review.auditFile, 'data/corpus-audits/ioi-2018.json');
  // This raw hash describes the preserved version, while later resolutions
  // may append explicit reviews. The original projection remains hash-fixed.
  assert.equal(review.auditSha256, '1a5278aa3d548df4a8ded8f86e033a36c41c26e4519409622766bb2ca1ea897e');
  assert.equal(review.originalRecordsSha256, hashes.records);
  assert.match(review.auditSha256Scope, /later appended reviews/);
  assert.equal(review.originalAuditRawSha256, 'c497743e29f92ac8e8d9604b1e34dd85ee99a6c24cf610423aa05dabda1c3b5d');
  assert.equal(review.snapshot.historicalRawFilesVerifiedAtInitialReview, 607);
  assert.equal(review.snapshot.permanentRawSnapshotsRehashed, 2);
  assert.equal(review.preservation.allHistoricalRawBytesAvailable, false);
  assert.equal(review.preservation.allHistoricalMdxAvailable, false);
  assert.deepEqual(review.researchVsCoverage, { solutionsReviewed: 6, principalUnconfirmed: 0,
    missingConcreteTechniques: 6, covered: 0, fullImplementationValidated: 0, globalComplete: false });
  assert.deepEqual(review.additionalChecks.meetingsEqualMaximum, { array: [2, 1, 2],
    sameOriginalMaximumId: 5, wrongReverseLocalTieRule: 6, literalMeetingSiteOracle: 5 });
  assert.equal(review.additionalChecks.dollSwitchAndInversionBoundsForAllN, 200000);
  assert.equal(review.additionalChecks.dollFullSimulationAdditionalBoundaryLengths, 99);
  assert.equal(review.additionalChecks.highwayAllPossibleWeightVectors, 1938);
  assert.equal(review.additionalChecks.highwayLiteralSimplePathVsDijkstraPairs, 11418);
  for (const file of [audit.validation.script, audit.preservation.researchCheckScript,
    audit.preservation.independentReviewScript, 'research/ioi-2018-audit-notes.md']) {
    const content = (await bytes(file)).toString('utf8');
    assert(!content.includes('/tmp/' + 'flowchartcp-'), `${file}: no dependency on the temporary workspace`);
  }
});
