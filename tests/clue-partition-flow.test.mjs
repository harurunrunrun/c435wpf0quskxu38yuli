import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-clue-partition-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// These expectations come from the partition and observation model, independently
// of the example walk and the implementation's registered route.
const id = 'disjoint-candidate-sets-complement-lookup';
const domain = 'dp';
const prefix = ['hidden-partition'];
const graphId = 'disjoint-hidden-partition-conditions';
const guards = ['known-and-hidden', 'local-rules', 'size'];
const fullChoices = [...prefix, 'yes', 'yes', 'yes'];
const statementUrl = 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=3';
const sketchUrl = 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/finals2017solutions.pdf#page=3';
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const candidates = evaluation => evaluation.current.techniques ?? [];
const originalProblem = row => String(row.source).toLowerCase() === 'icpc' && row.problemId === 'wf2017_b';
const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

async function collections(expression) {
  const names = (await readdir(path.join(site, 'data'))).filter(name => expression.test(name));
  return (await Promise.all(names.map(name => json('data/' + name)))).flat();
}
function walk(flow, choices, entry = domain) {
  const evaluation = flow.walkFromRoot(choices, entry);
  assert.equal(evaluation.consumed, choices.length, `${entry}/${choices.join('/')}: consume every fixed answer`);
  return evaluation;
}
function enterRoutes(flow, state) {
  for (let remaining = 100; flow.evaluateState(state).current.type === 'route'; --remaining) {
    assert(remaining > 0, 'route entry terminates');
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
function svgMatchesGraph(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let edges = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: node is drawn`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'full answer text is available in the diagram');
    }
    if (node.type === 'result') for (const techniqueId of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${techniqueId}/`), 'result links to its technique article');
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges);
  return svg;
}

test('the feature entrance requires the known/hidden partition, local rules and bounds before its result', async () => {
  const { flow } = await implementation;
  assert.equal(flow.entryGraphs.length, 15, 'preserve all existing field entrances');
  assert(flow.entryGraphs.some(graph => graph.id === domain));
  const entrance = walk(flow, []);
  const option = flow.getNodeOptions(entrance.current).find(row => row.id === 'hidden-partition');
  assert(option);
  assert.doesNotMatch(option.label, /Get a Clue|ICPC|wf2017_b/i, 'the entrance describes observable problem features');
  const entered = walk(flow, prefix);
  assert.equal(entered.graph.id, graphId);
  assert.notEqual(entered.graph.entry, true, 'applicability checks remain below the field entrance');
  for (let guard = 0; guard < guards.length; ++guard) {
    const evaluation = walk(flow, [...prefix, ...Array(guard).fill('yes')]);
    assert.equal(evaluation.graph.id, graphId);
    assert.equal(evaluation.current.type, 'question');
    assert.equal(evaluation.current.id, guards[guard]);
    assert(!candidates(evaluation).includes(id), 'no required condition can be bypassed');
    const options = flow.getNodeOptions(evaluation.current);
    assert.deepEqual(options.map(row => row.id).sort(), ['no', 'unknown', 'yes']);
    for (const row of options) assert(row.label.length >= 2);
  }
  const result = walk(flow, fullChoices);
  assert.equal(result.current.type, 'result');
  assert.deepEqual(candidates(result), [id]);
  for (const term of [/既知/, /未知の三つの集合の要素数/, /三分類/, /互いに素/, /禁止/, /必須/, /一つ以上/, /21/, /16/, /150/, /補集合/, /候補0個/, /候補1個/])
    assert.match(JSON.stringify(result.graph), term);
  assert(svgMatchesGraph(flow, result.graph).includes(`/flowchartcp/techniques/${id}/`));
});

test('no and unknown at each required condition go to condition-check without recommending the technique', async () => {
  const { flow } = await implementation;
  for (let guard = 0; guard < guards.length; ++guard) for (const answer of ['no', 'unknown']) {
    const evaluation = walk(flow, [...prefix, ...Array(guard).fill('yes'), answer]);
    assert.equal(evaluation.graph.id, 'condition-check', `${guards[guard]}/${answer}`);
    assert.equal(evaluation.current.type, 'question');
    assert(!candidates(evaluation).includes(id));
  }
});

test('question and diagram displays share complete histories, highlights, URLs and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  const histories = [fullChoices];
  for (let guard = 0; guard < guards.length; ++guard) for (const answer of ['no', 'unknown'])
    histories.push([...prefix, ...Array(guard).fill('yes'), answer]);
  for (const choices of histories) {
    let state = replay(flow, choices);
    assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices).current);
    for (let remaining = weight(state) + 1; ; --remaining) {
      assert(remaining > 0, 'Back terminates');
      assert.equal(flow.getFlowDomainId(state), domain);
      assert.deepEqual(flow.sanitizeState(state), state);
      const evaluation = flow.evaluateState(state);
      if (!diagrams.has(state.graph)) diagrams.set(state.graph, svgMatchesGraph(flow, evaluation.graph));
      const svg = diagrams.get(state.graph);
      assert(svg.includes(`data-node="${evaluation.current.id}"`));
      for (const node of evaluation.path) assert(svg.includes(`data-node="${node.id}"`));
      for (const edge of evaluation.edges) assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
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

test('the reusable article, independently verified original reference, metadata, feature and example walk agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    collections(/-problem-features\.json$/), json('data/problem-walks.json'),
  ]);
  const registrations = metadata.filter(row => row.id === id);
  assert.equal(registrations.length, 1);
  const technique = registrations[0];
  assert.equal(technique.kind, 'technique');
  assert.equal(technique.status, 'reviewed');
  assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
  assert(technique.sources.includes(statementUrl));
  assert(technique.sources.includes(sketchUrl));
  const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
  assert(new RegExp(`^techniqueId: ["']?${id}["']?\\s*$`, 'm').test(article));
  assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
    ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
  assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, 'one complete visible reusable C++ example');
  assert(!/<(?:details|summary)\b/i.test(article));
  assert(article.includes(`techniqueId="${id}"`));
  for (const source of technique.sources) assert(article.includes(source));
  assert.match(article, /unofficial analysis/);
  assert.match(article, /5,5,4,4/);
  assert.match(article, /infer_disjoint_hands/);
  assert.match(article, /infer_card_history/);
  const originalReferences = references.filter(row => originalProblem(row) && row.techniqueId === id);
  assert.equal(originalReferences.length, 1);
  const reference = originalReferences[0];
  assert.equal(reference.title, 'Get a Clue!');
  assert.equal(reference.url, statementUrl);
  assert.equal(reference.editorialUrl, sketchUrl);
  assert.equal(reference.verification, 'independent-analysis', 'the public sketch is not an official editorial');
  assert.equal(reference.difficulty, null, 'the source provides no rating');
  assert(reference.evidence.trim().length > 0);
  assert(!/テスト|checker|コンパイル|乱択|ASan|UBSan/i.test(reference.evidence), 'evidence describes applicability, verificationNotes contain tests');
  assert(reference.verificationNotes.trim().length > 0);
  assert.match(reference.verificationNotes, /unofficial|非公式/i);
  const originalFeatures = features.filter(row => originalProblem(row) && row.techniqueIds.includes(id));
  assert.equal(originalFeatures.length, 1);
  const feature = originalFeatures[0];
  assert.deepEqual(feature.techniqueIds, [id]);
  assert.equal(feature.url, statementUrl);
  assert.equal(feature.evidenceUrl, sketchUrl);
  assert.equal(feature.verification, 'independent-analysis');
  assert.equal(feature.reviewStatus, 'verified');
  assert.equal(feature.cutoff, '2026-10-14');
  assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
  assert.equal(feature.publicationYear, 2017);
  assert(feature.features.length >= 2);
  const originalWalks = walks.filter(row => originalProblem(row) && row.expectedTechniqueIds.includes(id));
  assert.equal(originalWalks.length, 1);
  const record = originalWalks[0];
  assert.equal(record.statementUrl, statementUrl);
  assert.equal(record.entryGraphId, domain);
  assert.equal(record.reviewStatus, 'verified');
  assert.equal(record.verificationKind, 'independent-analysis');
  assert.deepEqual(record.choices, fullChoices);
  assert.deepEqual(record.features, feature.features);
  const result = walk(flow, record.choices);
  assert.deepEqual(candidates(result), [id]);
  assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
});

test('the original audit is resolved with the known year, unknown rating and accurate sketch provenance', async () => {
  const [references, features, walks, audit] = await Promise.all([
    collections(/^references-.*\.json$/), collections(/-problem-features\.json$/),
    json('data/problem-walks.json'), json('data/corpus-audits/icpc-2017-world-finals.json'),
  ]);
  const original = audit.records.find(originalProblem);
  assert(original);
  assert.equal(original.contest.year, 2017);
  assert.equal(original.contest.yearMonth, undefined, 'only the year was verified');
  assert.equal(original.contest.exactDateVerified, false);
  assert.equal(original.difficulty, null);
  assert.notEqual(original.technicalFindings.verification, 'official-editorial');
  const related = [original,
    ...references.filter(row => originalProblem(row) && row.techniqueId === id),
    ...features.filter(row => originalProblem(row) && row.techniqueIds.includes(id)),
    ...walks.filter(row => originalProblem(row) && row.expectedTechniqueIds.includes(id)),
  ];
  for (const row of related) {
    for (const field of ['publicationDate', 'publicationMonth', 'contestYearMonth', 'sourceYearMonth', 'publicationYearMonth'])
      assert.equal(row[field], undefined, `the unverified month or day is not invented as ${field}`);
    if (row.publicationYear !== undefined) assert.equal(row.publicationYear, 2017);
    if (row.difficulty !== undefined) assert.equal(row.difficulty, null);
    if (row.exactDateVerified !== undefined) assert.equal(row.exactDateVerified, false);
  }
  assert.equal(original.resolution.status, 'verified');
  assert.deepEqual(original.resolution.techniqueIds, [id]);
  assert.equal(isCorpusSolutionReviewed(original), true, 'a mapping does not replace solution review');
});

test('the frozen 490 original walks remain unchanged and replay with their complete steps and results', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  const original = walks.slice(0, 490);
  assert.equal(original.length, 490);
  assert.equal(createHash('sha256').update(JSON.stringify(original)).digest('hex'),
    'a5415141e7ecf72bd1d27f95ffdb0e75bf43dcea8312254dc9250659383802b3',
    'the full preexisting records are preserved in their original order');
  for (const record of original) {
    const result = walk(flow, record.choices, record.entryGraphId);
    assert.equal(result.current.type, 'result', `${record.source}/${record.problemId}`);
    assert(record.expectedTechniqueIds.every(techniqueId => candidates(result).includes(techniqueId)),
      `${record.source}/${record.problemId}: every originally required technique is still present`);
    assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
  }
});
