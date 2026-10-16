import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const base = new URL('../', import.meta.url);
const json = async file => JSON.parse(await readFile(new URL(file, base), 'utf8'));
const tasks = ['shoes', 'split', 'rect', 'line', 'vision', 'walk'];
const reviewed = new Set(['shoes', 'split', 'vision']);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const hashes = {
  flow: '39a3d2089b8f5ac9e684092543ac49f5005555d3b6e8c0d4be3cdc2a9b1e0181',
  technique: 'd37e0dd7a9ba814ecc61f4c5ac2bc1165dfe3f61deaf689e3a7c92d0210e1d40',
};
const routes = [
  ['ranges', ['sequence-changes', 'reorder-cost'], 'range-sequence-changes', 'reorder-operation'],
  ['graphs', ['group-constraints'], 'graphs-group-constraints', 'shortest'],
  ['geometry', ['rectangle-aggregates'], 'geometry-rectangle-aggregates', 'geometry-task'],
  ['heuristic', ['yes'], 'heuristic', 'output'],
  ['math', ['bits-digits'], 'math-bits-digits', 'number-task'],
  ['graphs', ['walk-goals', 'distance', 'many-connections'], 'shortest-shared-connection-goals', 'movement'],
];
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));

// Use only the frozen JSON. A change in the product walker cannot alter what
// the first audit actually reached, including its generic output-only result.
function replay(graphMap, row) {
  let graph = graphMap.get(row.entryGraphId), node = graph?.nodes.find(n => n.id === graph.root);
  assert.equal(graph?.entry, true);
  const steps = [];
  let consumed = 0;
  for (let limit = 0; ; ++limit) {
    assert(limit < 1000 && node, row.problemId);
    if (node.type === 'route') {
      graph = graphMap.get(node.graph);
      assert(graph);
      node = graph.nodes.find(n => n.id === graph.root);
      continue;
    }
    if (node.type !== 'question' || consumed === row.choices.length) break;
    const answer = row.choices[consumed++], option = options(node).find(o => o.id === answer);
    assert(option);
    steps.push({ graphId: graph.id, nodeId: node.id, question: node.title, answer, answerLabel: option.label });
    node = graph.nodes.find(n => n.id === node.answers[answer]);
  }
  assert.equal(consumed, row.choices.length);
  return { graph, node, steps };
}

test('IOI2019 keeps its complete six-task selection, original dates and partial proof status', async () => {
  const audit = await json('data/corpus-audits/ioi-2019.json');
  const plan = await json('data/coverage-plan.json');
  const selection = plan.corpora.find(c => c.id === audit.corpusId);
  assert.equal(audit.cutoff, plan.cutoff);
  assert.equal(selection.expectedProblems, 6);
  assert.equal(audit.selection.fixedBeforeTechniqueSearch, true);
  const ids = tasks.map(id => 'ioi2019_' + id);
  for (const rows of [audit.records, selection.fixedProblems, audit.selection.fixedProblems]) {
    assert.deepEqual(rows.map(r => r.problemId), ids);
    assert(rows.every(r => r.source === 'ioi'));
  }
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, false);
  assert.equal(audit.status.fixedCorpusCoverageComplete, false);
  assert.equal(audit.status.globalCoverageComplete, false);
  assert.equal(audit.status.statementVerifiedCount, 6);
  assert.equal(audit.status.officialEditorialRetrievedCount, 6);
  assert.equal(audit.status.solutionReviewedCount, 3);
  assert.equal(audit.status.coveredCount, 0);
  assert.equal(audit.status.missingTechniqueCount, 3);
  assert.equal(audit.status.unconfirmedCount, 3);
  for (const [i, row] of audit.records.entries()) {
    assert.equal(row.officialTaskId, tasks[i]);
    assert.equal(row.contest.date, i < 3 ? '2019-08-06' : '2019-08-08');
    assert.equal(row.contest.exactDateVerified, true);
    assert.equal(row.statementUrl, `https://ioinformatics.org/files/ioi2019problem${i + 1}.pdf`);
    assert.equal(row.difficulty, null);
    assert.equal(row.constraints.numericBoundsVerified, false);
    assert(isCorpusStatementReviewed(row));
    const initial = { ...row, subsequentSolutionReviews: undefined };
    assert.equal(isCorpusSolutionReviewed(initial), reviewed.has(tasks[i]));
    assert.equal(row.classification, reviewed.has(tasks[i]) ? 'missing-technique' : 'unconfirmed');
    if (!reviewed.has(tasks[i])) {
      assert(row.technicalFindings.unconfirmedDetails.length > 0);
      assert.equal(isCorpusSolutionReviewed({ ...initial, reviewStatus: 'verified' }), false);
    }
  }
});

test('all six initial stops and candidate gaps replay against the exact 472 article and 439 graph data', async () => {
  const audit = await json('data/corpus-audits/ioi-2019.json');
  const plan = await json('data/coverage-plan.json');
  const snapshots = {};
  for (const name of ['flow', 'technique']) {
    assert.equal(audit.snapshot[name + 'SnapshotFile'], `research/snapshots/ioi-2019-${name}.json.gz`);
    const raw = gunzipSync(await readFile(new URL(audit.snapshot[name + 'SnapshotFile'], base)));
    assert.equal(sha(raw), hashes[name]);
    assert.equal(audit.snapshot[name + 'Sha256'], hashes[name]);
    snapshots[name] = JSON.parse(raw);
  }
  assert.equal(snapshots.flow.length, 439);
  assert.equal(snapshots.technique.length, 472);
  assert.equal(audit.snapshot.articleCount, 472);
  assert.equal(audit.snapshot.specificTechniqueCount, 394);
  const ids = new Set(snapshots.technique.map(t => t.id));
  assert.equal(ids.size, 472);
  const graphs = new Map(snapshots.flow.map(g => [g.id, g]));
  const gaps = plan.knownGaps.filter(g => g.discoveredBy === audit.corpusId);
  assert.equal(gaps.length, 6);
  for (const [index, row] of audit.records.entries()) {
    const [entry, choices, graphId, nodeId] = routes[index];
    assert.equal(row.entryGraphId, entry);
    assert.deepEqual(row.choices, choices);
    const { graph, node, steps } = replay(graphs, row);
    assert.equal(graph.id, graphId);
    assert.equal(node.id, nodeId);
    assert.equal(node.type, row.gap.stopNodeType);
    assert.deepEqual(steps, row.steps);
    assert.deepEqual(options(node), row.gap.currentOptions);
    assert.equal(row.gap.firstMissingGraphId, graphId);
    assert.equal(row.gap.firstMissingNodeId, nodeId);
    assert.equal(row.gap.currentQuestion, node.title);
    assert.deepEqual(row.actualReachedTechniqueIds, node.type === 'result' ? node.techniques : []);
    assert.deepEqual(row.expectedTechniqueIds, []);
    assert(row.gap.reason.length > 0);
    for (const id of row.gap.existingRelatedTechniqueIds) assert(ids.has(id), id);
    for (const id of row.gap.neededTechniqueIds) assert(!ids.has(id), id);
    const gap = gaps.find(g => g.id === row.gap.id);
    assert(gap);
    assert.equal(gap.problemId, row.problemId);
    assert.deepEqual(gap.techniqueIds, row.gap.neededTechniqueIds);
  }
  const manifest = await readFile(new URL(audit.snapshot.manifestFile, base));
  assert.equal(sha(manifest), 'd39f6068cb6ee8ffa0d2ea5bf24e26bc42835dc6ca888a1e3c76c8539f8b0e51');
});
