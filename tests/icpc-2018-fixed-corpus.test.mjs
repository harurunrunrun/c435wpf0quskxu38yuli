import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { isCorpusStatementReviewed, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const base = new URL('../', import.meta.url);
const json = async file => JSON.parse(await readFile(new URL(file, base), 'utf8'));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const letters = [...'abcdefghijk'];
const hashes = {
  flow: '39a3d2089b8f5ac9e684092543ac49f5005555d3b6e8c0d4be3cdc2a9b1e0181',
  technique: '7b86efb4381ef4b36d502aa773d0c6cf372fde9927f18d9cb54001548d81706f',
};
const routes = [
  ['game-probability', ['repeated-trials'], 'probability-processes', 'goal'],
  ['strings', ['changes'], 'strings-change-goals', 'text-task'],
  ['flow-matching', ['quantity-goals', 'costs', 'yes'], 'assignment-quantity-goals', 'mincost'],
  ['game-probability', ['stateful-process'], 'stateful-random-process-features', 'goal'],
  ['geometry', ['travel-partition'], 'geometry-travel-partition', 'geometry-task'],
  ['dp', ['sequence-removals', 'split'], 'dp-sequence-removals', 'split-kind'],
  ['geometry', ['enclosing-regions', 'point-set-shapes'], 'point-set-shape-features', 'goal'],
  ['geometry', ['boundary-relations'], 'geometry-boundary-relations', 'geometry-task'],
  ['geometry', [], 'geometry', 'geometry-task'],
  ['grid-arrangements', ['movement-cycles'], 'grid-movement-cycles', 'goal'],
  ['thinking', ['operation-goals', 'graph-build'], 'graph-distance-construction', 'distance-two'],
];
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label: ({ yes: 'はい', no: 'いいえ', unknown: 'わからない' })[id] ?? id }));

function replay(map, row) {
  let graph = map.get(row.entryGraphId), node = graph?.nodes.find(n => n.id === graph.root), consumed = 0;
  assert.equal(graph?.entry, true);
  const steps = [];
  for (let limit = 0; ; ++limit) {
    assert(limit < 1000 && node, row.problemId);
    if (node.type === 'route') {
      graph = map.get(node.graph); assert(graph);
      node = graph.nodes.find(n => n.id === graph.root); continue;
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

test('ICPC2018 fixes all eleven tasks and distinguishes the unofficial sketches and two unresolved proofs', async () => {
  const a = await json('data/corpus-audits/icpc-2018-world-finals.json');
  const plan = await json('data/coverage-plan.json');
  const selection = plan.corpora.find(c => c.id === a.corpusId);
  assert.equal(a.cutoff, plan.cutoff);
  assert.equal(selection.expectedProblems, 11);
  assert.equal(a.selection.fixedBeforeTechniqueSearch, true);
  for (const rows of [a.records, a.selection.fixedProblems, selection.fixedProblems]) {
    assert.deepEqual(rows.map(r => r.problemId), letters.map(l => 'wf2018_' + l));
    assert(rows.every(r => r.source === 'icpc'));
  }
  assert.equal(a.status.firstPassAuditComplete, true);
  assert.equal(a.status.fixedCorpusResearchComplete, false);
  assert.equal(a.status.fixedCorpusCoverageComplete, false);
  assert.equal(a.status.globalCoverageComplete, false);
  assert.equal(a.status.statementVerifiedCount, 11);
  assert.equal(a.status.solutionReviewedCount, 9);
  assert.equal(a.status.officialEditorialVerifiedCount, 0);
  assert.equal(a.status.missingTechniqueCount, 9);
  assert.equal(a.status.unconfirmedCount, 2);
  assert.equal(a.status.coveredCount, 0);
  for (const [index, r] of a.records.entries()) {
    assert.equal(r.contest.date, '2018-04-19');
    assert.equal(r.contest.exactDateVerified, true);
    assert.equal(r.difficulty, null);
    assert.equal(r.statementUrl, `https://icpc.global/worldfinals/problems/2018-ICPC-World-Finals/icpc2018.pdf#page=${2 * index + 1}`);
    assert.equal(r.materialStatus.officialEditorialVerified, false);
    assert(isCorpusStatementReviewed(r));
    const initial = { ...r, subsequentSolutionReviews: undefined };
    const confirmed = !['c', 'j'].includes(letters[index]);
    assert.equal(isCorpusSolutionReviewed(initial), confirmed);
    assert.equal(r.classification, confirmed ? 'missing-technique' : 'unconfirmed');
    if (!confirmed) {
      assert(r.unconfirmedDetails.length > 0);
      assert.equal(isCorpusSolutionReviewed({ ...initial, reviewStatus: 'verified' }), false);
    }
    assert(r.technicalFindings.editorialProvenance.includes('unofficial'));
  }
});

test('all eleven first stops replay from the frozen 472 articles and 439 graphs without the product walker', async () => {
  const a = await json('data/corpus-audits/icpc-2018-world-finals.json');
  const plan = await json('data/coverage-plan.json');
  const data = {};
  for (const name of ['flow', 'technique']) {
    assert.equal(a.snapshot[name + 'SnapshotFile'], `research/snapshots/icpc-2018-${name}.json.gz`);
    const raw = gunzipSync(await readFile(new URL(a.snapshot[name + 'SnapshotFile'], base)));
    assert.equal(sha(raw), hashes[name]);
    assert.equal(a.snapshot[name + 'Sha256'], hashes[name]);
    data[name] = JSON.parse(raw);
  }
  assert.equal(data.flow.length, 439);
  assert.equal(data.flow.filter(g => g.entry).length, 15);
  const metadata = Object.values(data.technique).flat(), ids = new Set(metadata.map(t => t.id));
  assert.equal(metadata.length, 472); assert.equal(ids.size, 472);
  assert.equal(a.snapshot.articleCount, 472);
  assert.equal(a.snapshot.specificTechniqueCount, 394);
  const map = new Map(data.flow.map(g => [g.id, g]));
  const gaps = plan.knownGaps.filter(g => g.discoveredBy === a.corpusId);
  assert.equal(gaps.length, 11);
  for (const [index, r] of a.records.entries()) {
    const [entry, choices, graphId, nodeId] = routes[index];
    assert.equal(r.entryGraphId, entry); assert.deepEqual(r.choices, choices);
    const { graph, node, steps } = replay(map, r);
    assert.equal(graph.id, graphId); assert.equal(node.id, nodeId);
    assert.deepEqual(steps, r.steps);
    assert.deepEqual(r.initialReached, { graphId, nodeId, nodeType: node.type, title: node.title, techniqueIds: node.techniques ?? [] });
    assert.equal(r.gap.firstMissingGraphId, graphId); assert.equal(r.gap.firstMissingNodeId, nodeId);
    assert.equal(r.gap.currentQuestion, node.title); assert.deepEqual(options(node), r.gap.currentOptions);
    assert.deepEqual(r.expectedTechniqueIds, []);
    assert(r.gap.reason.length > 0);
    for (const id of r.gap.existingRelatedTechniqueIds) assert(ids.has(id), id);
    for (const id of r.gap.neededTechniqueIds) assert(!ids.has(id), id);
    const gap = gaps.find(g => g.id === r.gap.id); assert(gap);
    assert.equal(gap.problemId, r.problemId); assert.deepEqual(gap.techniqueIds, r.gap.neededTechniqueIds);
  }
  const manifest = await readFile(new URL(a.snapshot.manifestFile, base));
  assert.equal(sha(manifest), '246e41da7f29fbd319552dbb852f4727da46ca2dba3ef4e71f0b35f2bf896705');
});
