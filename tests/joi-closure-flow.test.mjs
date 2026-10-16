import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-joi-closure-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// These expectations were fixed before the new routes were connected. Neither
// flows.json, the example walks, nor feature records generate the expected path.
const tasks = [
  {
    id: 'two-choice-nondecreasing-count-interval-reconstruction',
    domain: 'dp', prefix: ['generation-history', 'two-choice-count'],
    graph: 'two-choice-count-conditions', guards: ['two-options', 'ordered-count', 'length'],
    terms: [/二つ|二択|2択/, /非減少|単調/, /個数|回数/, /復元|構成|選択列/, /1000000|1,000,000|10\^6|100万|百万|1e6/],
    problemId: 'joi2020sc_building4', day: 1, date: '2020-03-20', verification: 'independent-analysis',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day1/building4.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day1/building4-review.pdf',
  },
  {
    id: 'interactive-hidden-bipartite-edge-color-pair-recovery',
    domain: 'interactive-oracles', prefix: ['changing-color-count'],
    graph: 'hidden-color-pair-conditions', guards: ['paired-colors', 'color-query', 'budget'],
    terms: [/色/, /全単射|一対一|1対1/, /好/, /集合|会合/, /500/, /19000|19,000/],
    problemId: 'joi2020sc_chameleon', day: 2, date: '2020-03-21', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/chameleon.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/chameleon-review.pdf',
  },
  {
    id: 'tree-color-closure-sink-scc',
    domain: 'graphs', prefix: ['group-constraints', 'tree-color-union'],
    alternatePrefix: ['rooted-tree-goals', 'tree-color-union'],
    graph: 'tree-color-closure-conditions', guards: ['tree', 'whole-color', 'one-connected', 'size'],
    terms: [/木/, /同じ色|同色|色/, /全て|すべて|丸ごと/, /連結/, /最小|最少/],
    problemId: 'joi2020sc_capital_city', day: 4, date: '2020-03-23', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day4/capital_city.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day4/capital_city-review.pdf',
  },
  {
    id: 'grid-triplet-conflict-packing',
    domain: 'heuristic', prefix: ['triplet-packing'],
    graph: 'grid-triplet-packing-conditions', guards: ['straight-three', 'disjoint-cells', 'budgeted-search'],
    terms: [/三マス|3マス|三つ|3つ/, /P/, /W/, /G/, /重複|共有/, /最適|保証/, /探索|反復/],
    problemId: 'joi2020sc_dango2', day: 4, date: '2020-03-23', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day4/dango2.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day4/dango2-review.pdf',
  },
];
const ids = tasks.map(item => item.id);
const routes = tasks.flatMap(item => item.alternatePrefix
  ? [item, { ...item, prefix: item.alternatePrefix }]
  : [item]);
const candidates = value => value.current.techniques ?? [];
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const isJoi = row => String(row.source).toLowerCase() === 'joi';
const matchesOriginal = (row, item) => isJoi(row) && row.problemId === item.problemId;
const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function walk(flow, domain, choices) {
  const result = flow.walkFromRoot(choices, domain);
  assert.equal(result.consumed, choices.length, `${domain}/${choices.join('/')}: all fixed answers are consumed`);
  return result;
}
function enterRoutes(flow, state) {
  for (let remaining = 100; flow.evaluateState(state).current.type === 'route'; --remaining) {
    assert(remaining > 0, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, domain, choices) {
  let state = flow.initialState(domain);
  for (const answer of choices) state = flow.answerState(enterRoutes(flow, state), answer);
  return enterRoutes(flow, state);
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}
async function loadCollections(expression) {
  const files = await readdir(path.join(site, 'data'));
  return (await Promise.all(files.filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function svgMatchesGraph(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let answerCount = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: every node is drawn`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++answerCount;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`),
        `${graph.id}/${node.id}/${option.id}: every answer has its SVG edge`);
      assert(svg.includes(`<title>${xml(option.label)}</title>`),
        `${graph.id}/${node.id}/${option.id}: every answer has its full readable label`);
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${id}/`), `${graph.id}/${id}: the result links to its article`);
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, answerCount,
    `${graph.id}: the SVG contains exactly the graph's answer edges`);
  return svg;
}

test('four JOI techniques and both tree entrances follow independently fixed feature paths and all thirteen guards', async () => {
  const { flow } = await implementation;
  assert.equal(new Set(ids).size, 4);
  assert.equal(tasks.reduce((sum, item) => sum + item.guards.length, 0), 13);
  assert.equal(routes.length, 5);
  for (const item of routes) {
    const initial = walk(flow, item.domain, item.prefix);
    assert.equal(initial.graph.id, item.graph, `${item.id}/${item.prefix.join('/')}: feature choices reach the right chart`);
    assert.equal(initial.current.id, item.guards[0]);
    assert.notEqual(initial.graph.entry, true, 'the applicability chart is under an existing domain');
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard], `${item.id}: every applicability check stays in the fixed order`);
      assert(ids.every(id => !candidates(value).includes(id)), 'no conclusion skips an applicability check');
      const options = flow.getNodeOptions(value.current);
      assert.deepEqual(options.map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const option of options) assert(option.label.length >= 2, 'answers have readable labels');
    }
    const value = walk(flow, item.domain, [...item.prefix, ...Array(item.guards.length).fill('yes')]);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id], `${item.id}: all premises select this single technique`);
    const text = JSON.stringify(value.graph);
    for (const term of item.terms) assert.match(text, term, `${item.id}: the necessary problem features are explained`);
    const svg = svgMatchesGraph(flow, value.graph);
    assert(svg.includes(`/flowchartcp/techniques/${item.id}/`));
  }
  assert.equal(flow.entryGraphs.length, 15, 'the existing fifteen field entrances are retained');
  for (const domain of new Set(tasks.map(item => item.domain)))
    assert(flow.entryGraphs.some(graph => graph.id === domain));
});

test('no or unknown at every fixed guard routes to condition checking without a premature result', async () => {
  const { flow } = await implementation;
  for (const item of routes) for (let guard = 0; guard < item.guards.length; ++guard) {
    for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(value.graph.id, 'condition-check', `${item.id}/${item.guards[guard]}/${answer}: check the unsupported premise`);
      assert.equal(value.current.type, 'question');
      assert(ids.every(id => !candidates(value).includes(id)), 'no unsupported new technique is returned');
    }
  }
});

test('question and diagram links restore successes, failures, path highlights and finite Back history', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of routes) {
    const histories = [[...item.prefix, ...Array(item.guards.length).fill('yes')]];
    for (let guard = 0; guard < item.guards.length; ++guard)
      for (const answer of ['no', 'unknown'])
        histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item.domain, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
      for (let remaining = weight(state) + 1; ; --remaining) {
        assert(remaining > 0, `${item.id}: Back terminates`);
        assert.equal(flow.getFlowDomainId(state), item.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluation = flow.evaluateState(state);
        if (!diagrams.has(state.graph)) diagrams.set(state.graph, svgMatchesGraph(flow, evaluation.graph));
        const svg = diagrams.get(state.graph);
        assert(svg.includes(`data-node="${evaluation.current.id}"`), 'the current node is present in the diagram');
        for (const node of evaluation.path) assert(svg.includes(`data-node="${node.id}"`), 'every highlighted path node exists');
        for (const edge of evaluation.edges)
          assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`), 'every highlighted path edge exists');
        const hash = flow.serializeFlowHash(state);
        assert.deepEqual(flow.parseFlowHash(hash), state, 'the question URL restores its full route history');
        assert.deepEqual(viewer.diagramState(state.graph, hash), state, 'the diagram restores the same state');
        const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
        assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
        assert.equal(url.hash, hash, 'the shared diagram URL retains the question state');
        assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
        if (!weight(state)) break;
        const previous = flow.backFlowState(state);
        assert(weight(previous) < weight(state), 'Back removes a canonical history step');
        state = previous;
      }
      assert.deepEqual(state, flow.initialState(item.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  }
});

test('the four articles have reviewed metadata, visible eight-section explanations, implementations and matching original walks', async () => {
  const { flow } = await implementation;
  const [metadata, references, walks] = await Promise.all([
    loadCollections(/^techniques-.*\.json$/), loadCollections(/^references-.*\.json$/), json('data/problem-walks.json'),
  ]);
  const headings = ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'];
  for (const item of tasks) {
    const rows = metadata.filter(row => row.id === item.id);
    assert.equal(rows.length, 1, `${item.id}: exactly one metadata registration`);
    const technique = rows[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)), 'an English alias is searchable');
    assert(technique.sources.includes(item.statementUrl), 'metadata identifies the fixed original problem');
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert(new RegExp(`^techniqueId: ["']?${item.id}["']?\\s*$`, 'm').test(article));
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]), headings, 'all eight sections appear once in order');
    assert((article.match(/^```cpp\s*$/gm) ?? []).length >= 1, 'a reusable C++ implementation is displayed');
    assert(!/<(?:details|summary)\b/i.test(article), 'the explanation and implementation are initially visible');
    assert(article.includes(`techniqueId="${item.id}"`), 'the original-example component is present');
    for (const source of technique.sources) assert(article.includes(source), 'each metadata source is linked from the article');
    assert(article.includes(item.statementUrl) && article.includes(item.editorialUrl), 'both official source URLs are visible');
    const originals = references.filter(row => row.techniqueId === item.id && matchesOriginal(row, item));
    assert.equal(originals.length, 1, `${item.id}: one confirmed original reference`);
    const original = originals[0];
    assert.equal(original.url, item.statementUrl);
    assert.equal(original.verification, item.verification);
    assert.equal(original.cutoffVerification, 'contest-before-cutoff');
    assert(original.evidence.trim().length > 0);
    const records = walks.filter(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(records.length, 1, `${item.id}: one original root walk`);
    const record = records[0];
    assert.equal(record.statementUrl, item.statementUrl);
    assert.equal(record.reviewStatus, 'verified');
    assert.equal(record.verificationKind, item.verification);
    assert.equal(record.cutoffVerification, 'contest-before-cutoff');
    assert.equal(record.entryGraphId, item.domain);
    assert.deepEqual(record.choices, [...item.prefix, ...Array(item.guards.length).fill('yes')], 'the registered walk follows the independent fixed path');
    assert(record.features.length >= 2);
    const value = walk(flow, record.entryGraphId, record.choices);
    assert.deepEqual(candidates(value), [item.id]);
    assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
  }
});

test('the four fixed original records preserve exact official contest dates, cutoff evidence and feature identity', async () => {
  const [features, references, walks, audit] = await Promise.all([
    json('data/joi-closure-problem-features.json'), loadCollections(/^references-.*\.json$/),
    json('data/problem-walks.json'), json('data/corpus-audits/joi-2020-spring.json'),
  ]);
  assert.equal(features.length, 4);
  const actualPairs = [];
  for (const item of tasks) {
    const rows = features.filter(row => matchesOriginal(row, item));
    assert.equal(rows.length, 1, 'each fixed original has one feature record');
    const feature = rows[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, item.verification);
    assert.equal(feature.cutoff, '2026-10-14');
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert.equal(feature.publicationDate, item.date, 'the exact day is supported by the official contest schedule');
    assert(feature.publicationDate < feature.cutoff);
    assert(feature.features.length >= 2);
    assert(feature.evidenceUrl.startsWith('https://'));
    const originalAudit = audit.records.find(row => matchesOriginal(row, item));
    assert.equal(originalAudit.contest.date, item.date);
    assert.equal(originalAudit.contest.day, item.day);
    assert.equal(originalAudit.contest.exactDateVerified, true);
    const reference = references.find(row => matchesOriginal(row, item) && row.techniqueId === item.id);
    const record = walks.find(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert(reference && record);
    assert.equal(reference.url, feature.url);
    assert.equal(reference.verification, feature.verification);
    assert.deepEqual(record.features, feature.features);
    actualPairs.push(`${item.problemId}/${item.id}`);
  }
  assert.deepEqual(actualPairs.sort(), references.filter(row => ids.includes(row.techniqueId))
    .map(row => `${row.problemId}/${row.techniqueId}`).sort(), 'the four feature mappings and original references agree exactly');
});

test('all four resolutions are explicit and Building 4 preserves its initial unconfirmed review beside the later proof', async () => {
  const audit = await json('data/corpus-audits/joi-2020-spring.json');
  assert.equal(audit.records.length, 12, 'the original fixed corpus is not reduced to the implemented subset');
  assert.equal(audit.status.fixedCorpusCoverageComplete, false, 'four implementations do not cover all twelve tasks');
  for (const item of tasks) {
    const original = audit.records.find(row => matchesOriginal(row, item));
    assert(original);
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id]);
    assert.match(original.resolution.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
    assert(original.resolution.notes.trim().length > 0);
    assert.equal(isCorpusSolutionReviewed(original), true, 'the solution proof and implementation mapping are both confirmed');
  }
  const original = audit.records.find(row => row.problemId === 'joi2020sc_building4');
  assert.equal(original.reviewStatus, 'unconfirmed');
  assert.equal(original.classification, 'unconfirmed');
  assert.equal(original.materialStatus.officialEditorialVerified, false);
  assert.equal(original.technicalFindings.fullImplementationValidated, false, 'the historical first-pass implementation claim is preserved');
  assert.match(original.technicalFindings.verification, /unconfirmed/);
  assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: undefined }), false,
    'later proof does not rewrite the original missing-proof finding');
  assert(Array.isArray(original.subsequentSolutionReviews));
  const proof = original.subsequentSolutionReviews.find(row => row.verification === 'independent-analysis');
  assert(proof, 'the new interval lemma has an explicit independent-proof review');
  assert.equal(proof.reviewStatus, 'verified');
  assert.equal(proof.statementUrl, tasks[0].statementUrl);
  assert.equal(proof.collectionStatus, 'statement-and-independent-analysis-verified');
  assert.match(proof.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
  assert(proof.evidenceUrls.includes(tasks[0].statementUrl));
  assert(proof.notes.trim().length > 0);
});
