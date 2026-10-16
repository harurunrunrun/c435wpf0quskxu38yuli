import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const base = new URL('../', import.meta.url);
const json = async name => JSON.parse(await readFile(new URL(name, base), 'utf8'));
test('the fixed twelve JOI tasks replay against the preserved pre-expansion snapshot', async () => {
  const audit = await json('data/corpus-audits/joi-2020-spring.json');
  const plan = await json('data/coverage-plan.json');
  const selection = plan.corpora.find(row => row.id === 'joi-2020-spring');
  const snapshots = {};
  for (const name of ['flow', 'technique']) {
    const relative = audit.snapshot[name + 'SnapshotFile'];
    assert.match(relative, /^research\/snapshots\/joi-2020-(flow|technique)\.json\.gz$/);
    const bytes = gunzipSync(await readFile(new URL(relative, base)));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), audit.snapshot[name + 'Sha256']);
    snapshots[name] = JSON.parse(bytes);
  }
  assert.equal(snapshots.flow.length, 422);
  assert.equal(snapshots.technique.length, 457);
  const identities = ['building4', 'hamburg', 'sweeping', 'chameleon', 'joitter2', 'ruins3',
    'constellation3', 'harvest', 'stray', 'capital_city', 'dango2', 'treatment'].map(id => 'joi2020sc_' + id);
  assert.deepEqual(audit.records.map(row => row.problemId), identities);
  assert.deepEqual(selection.fixedProblems.map(row => row.problemId), identities);
  assert.equal(selection.expectedProblems, 12);
  assert.equal(audit.status.firstPassAuditComplete, true);
  assert.equal(audit.status.fixedCorpusResearchComplete, false);
  assert.equal(audit.status.fixedCorpusCoverageComplete, false);
  assert.equal(audit.records.filter(isCorpusStatementReviewed).length, 12);
  assert.equal(audit.records.filter(row => isCorpusSolutionReviewed({ ...row, subsequentSolutionReviews: undefined })).length, 8);
  assert.equal(audit.records.filter(row => row.classification === 'missing-technique').length, 8);
  assert.equal(audit.records.filter(row => row.classification === 'unconfirmed').length, 4);
  const graphMap = new Map(snapshots.flow.map(graph => [graph.id, graph]));
  const techniqueIds = new Set(snapshots.technique.map(row => row.id));
  const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
    label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));
  for (const record of audit.records) {
    let graph = graphMap.get(record.entryGraphId), node = graph.nodes.find(row => row.id === graph.root);
    assert.equal(graph.entry, true);
    const steps = [];
    let consumed = 0;
    for (let limit = 0; ; ++limit) {
      assert(limit < 1000, 'the preserved route terminates');
      if (node.type === 'route') {
        graph = graphMap.get(node.graph);
        node = graph.nodes.find(row => row.id === graph.root);
      } else if (node.type !== 'question' || consumed === record.choices.length) break;
      else {
        const answer = record.choices[consumed++];
        const option = options(node).find(row => row.id === answer);
        assert(option);
        steps.push({ graphId: graph.id, nodeId: node.id, question: node.title, answer, answerLabel: option.label });
        node = graph.nodes.find(row => row.id === node.answers[answer]);
        assert(node);
      }
    }
    assert.equal(consumed, record.choices.length);
    assert.deepEqual(steps, record.steps);
    assert.equal(graph.id, record.gap.firstMissingGraphId);
    assert.equal(node.id, record.gap.firstMissingNodeId);
    assert.deepEqual(options(node), record.gap.currentOptions);
    for (const id of record.gap.existingRelatedTechniqueIds) assert(techniqueIds.has(id));
    for (const id of record.gap.neededTechniqueIds) assert(!techniqueIds.has(id));
    const gap = plan.knownGaps.find(row => row.id === record.gap.id);
    assert(gap && gap.discoveredBy === audit.corpusId && gap.problemId === record.problemId);
  }
});
