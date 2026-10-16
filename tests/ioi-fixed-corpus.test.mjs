import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const base = new URL('../', import.meta.url);
const json = async name => JSON.parse(await readFile(new URL(name, base), 'utf8'));
const taskIds = ['plants', 'supertrees', 'tickets', 'biscuits', 'mushrooms', 'stations'];
const identities = taskIds.map(id => 'ioi2020_' + id);
const hashes = {
  flow: 'febb504779ef0f015744f28713408fc1d02eae89509fa910677c898bf2151ca7',
  technique: '2cd200111fd58479f6c5afb64de1d000558143ed201ae20a995c5aaf43bb116e',
};
const routes = {
  plants: ['graphs', ['group-constraints'], 'graphs-group-constraints', 'shortest'],
  supertrees: ['graphs', ['network-connection'], 'graphs-network-connection', 'shortest'],
  tickets: ['flow-matching', ['quantity-goals'], 'assignment-quantity-goals', 'purpose'],
  biscuits: ['math', ['counting-totals', 'count', 'select-values'], 'count-selected-values', 'count-kind'],
  mushrooms: ['interactive-oracles', [], 'interactive-oracles', 'response'],
  stations: ['graphs', ['rooted-tree-goals', 'tree-range', 'ancestors-and-paths'], 'tree-ancestor-path-goals', 'target'],
};
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));

// Replay the saved JSON directly so changes to the product walker cannot make
// an incorrect historical audit validate itself.
function replay(graphMap, record) {
  let graph = graphMap.get(record.entryGraphId);
  assert(graph, record.problemId + ': entry graph exists');
  assert.equal(graph.entry, true);
  let node = graph.nodes.find(row => row.id === graph.root);
  const steps = [];
  let consumed = 0;
  for (let limit = 0; ; ++limit) {
    assert(limit < 1000, record.problemId + ': preserved route terminates');
    assert(node, record.problemId + ': node exists');
    if (node.type === 'route') {
      graph = graphMap.get(node.graph);
      assert(graph, record.problemId + ': target graph exists');
      node = graph.nodes.find(row => row.id === graph.root);
    } else if (node.type !== 'question' || consumed === record.choices.length) break;
    else {
      const answer = record.choices[consumed++];
      const option = options(node).find(row => row.id === answer);
      assert(option, record.problemId + ': answer is selectable');
      steps.push({ graphId: graph.id, nodeId: node.id, question: node.title,
        answer, answerLabel: option.label });
      node = graph.nodes.find(row => row.id === node.answers[answer]);
    }
  }
  assert.equal(consumed, record.choices.length);
  return { graph, node, steps };
}

test('the six official IOI 2020 tasks remain fixed with one confirmed solution and five unresolved proofs', async () => {
  const audit = await json('data/corpus-audits/ioi-2020.json');
  const plan = await json('data/coverage-plan.json');
  const selection = plan.corpora.find(row => row.id === 'ioi-2020');
  assert(selection);
  assert.equal(audit.corpusId, 'ioi-2020');
  assert.equal(audit.cutoff, plan.cutoff);
  assert.equal(selection.auditFile, 'data/corpus-audits/ioi-2020.json');
  assert.equal(selection.state, 'audited');
  assert.equal(selection.expectedProblems, 6);
  assert.equal(audit.selection.expectedProblems, 6);
  assert.equal(audit.selection.fixedBeforeTechniqueSearch, true);
  for (const rows of [audit.records, selection.fixedProblems, audit.selection.fixedProblems]) {
    assert.deepEqual(rows.map(row => row.problemId), identities);
    assert(rows.every(row => row.source === 'ioi'));
  }
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, false);
  assert.equal(audit.status.fixedCorpusCoverageComplete, false);
  assert.equal(audit.status.globalCoverageComplete, false);
  assert.equal(audit.status.articleResolutionComplete, false);
  assert.equal(audit.status.recordCount, 6);
  assert.equal(audit.status.statementVerifiedCount, 6);
  assert.equal(audit.status.officialEditorialRetrievedCount, 6);
  assert.equal(audit.status.officialEditorialVerifiedCount, 1);
  assert.equal(audit.status.solutionReviewedCount, 1);
  assert.equal(audit.status.missingTechniqueCount, 1);
  assert.equal(audit.status.unconfirmedCount, 5);
  assert.equal(audit.status.coveredCount, 0);
  assert.equal(audit.status.missingRouteCount, 0);
  assert.equal(audit.records.filter(isCorpusStatementReviewed).length, 6);
  const initial = audit.records.map(row => ({ ...row, subsequentSolutionReviews: undefined }));
  assert.deepEqual(initial.filter(isCorpusSolutionReviewed).map(row => row.problemId), ['ioi2020_tickets']);
  for (const [index, row] of audit.records.entries()) {
    const taskId = taskIds[index], day = index < 3 ? 1 : 2;
    assert.equal(row.officialTaskId, taskId);
    assert.equal(row.contest.day, day);
    assert.equal(row.contest.date, day === 1 ? '2020-09-16' : '2020-09-19');
    assert.equal(row.contest.exactDateVerified, true);
    assert.equal(row.statementUrl,
      `https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/day${day}-${taskId}-ISC.pdf`);
    assert.equal(row.editorialUrl,
      `https://ioi2020.sg/wp-content/uploads/sites/4/2020/09/${taskId}-solutions-ISC.pdf`);
    assert.equal(row.materialStatus.officialEditorialRetrieved, true);
    assert.equal(row.classification, taskId === 'tickets' ? 'missing-technique' : 'unconfirmed');
    assert.equal(row.reviewStatus, taskId === 'tickets' ? 'verified' : 'unconfirmed');
    assert.equal(row.materialStatus.officialEditorialVerified, taskId === 'tickets');
    assert.equal(row.technicalFindings.verification,
      taskId === 'tickets' ? 'official-editorial' : 'official-editorial-partial-with-unconfirmed-detail');
    if (taskId !== 'tickets') {
      assert(row.technicalFindings.unconfirmedDetails.length > 0);
      assert.equal(isCorpusSolutionReviewed({ ...row, reviewStatus: 'verified', subsequentSolutionReviews: undefined }), false,
        'retrieving a PDF or changing the status cannot confirm a missing proof');
    }
  }
});

test('all six IOI audit paths independently replay against the exact 466 article and 431 graph snapshot', async () => {
  const audit = await json('data/corpus-audits/ioi-2020.json');
  const plan = await json('data/coverage-plan.json');
  const snapshots = {};
  for (const name of ['flow', 'technique']) {
    const relative = audit.snapshot[name + 'SnapshotFile'];
    assert.equal(relative, `research/snapshots/ioi-2020-${name}.json.gz`);
    const bytes = gunzipSync(await readFile(new URL(relative, base)));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), hashes[name]);
    assert.equal(audit.snapshot[name + 'Sha256'], hashes[name]);
    snapshots[name] = JSON.parse(bytes);
  }
  const techniques = Object.values(snapshots.technique).flat();
  assert.equal(snapshots.flow.length, 431);
  assert.equal(techniques.length, 466);
  assert.equal(Object.entries(snapshots.technique)
    .filter(([file]) => file.includes('specific')).flatMap(([, rows]) => rows).length, 388);
  assert.equal(audit.snapshot.articleCount, 466);
  assert.equal(audit.snapshot.registeredArticleCount, 466);
  assert.equal(audit.snapshot.techniqueMetadataCount, 466);
  assert.equal(audit.snapshot.specificTechniqueCount, 388);
  assert.equal(audit.snapshot.flowGraphCount, 431);
  const graphMap = new Map(snapshots.flow.map(graph => [graph.id, graph]));
  const techniqueIds = new Set(techniques.map(row => row.id));
  const gaps = plan.knownGaps.filter(row => row.discoveredBy === audit.corpusId);
  assert.equal(gaps.length, 6);
  for (const record of audit.records) {
    const [entry, choices, missingGraph, missingNode] = routes[record.officialTaskId];
    assert.equal(record.entryGraphId, entry);
    assert.deepEqual(record.choices, choices);
    const { graph, node, steps } = replay(graphMap, record);
    assert.equal(node.type, 'question');
    assert.deepEqual(steps, record.steps);
    assert.equal(graph.id, missingGraph);
    assert.equal(node.id, missingNode);
    assert.equal(record.gap.firstMissingGraphId, graph.id);
    assert.equal(record.gap.firstMissingNodeId, node.id);
    assert.equal(record.gap.currentQuestion, node.title);
    assert.deepEqual(options(node), record.gap.currentOptions);
    assert(record.gap.reason.length > 0);
    assert(record.gap.neededTechniqueIds.length > 0);
    assert(record.gap.existingRelatedTechniqueIds.length > 0);
    assert.equal(record.gap.implementationNeeded, true);
    for (const id of record.gap.existingRelatedTechniqueIds) assert(techniqueIds.has(id), id);
    for (const id of record.gap.neededTechniqueIds) assert(!techniqueIds.has(id), id);
    const gap = gaps.find(row => row.id === record.gap.id);
    assert(gap, record.problemId + ': proposed gap is retained in the plan');
    assert.equal(gap.problemId, record.problemId);
    assert.deepEqual(gap.techniqueIds, record.gap.neededTechniqueIds);
  }
});
