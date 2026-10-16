import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { inflateRawSync } from 'node:zlib';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const id = 'two-source-concave-flow-mixture-decomposition';
const domain = 'flow-matching';
const prefix = ['quantity-goals', 'two-source-mixture'];
const graphId = 'two-source-mixture-conditions';
const guards = ['two-source-shared-capacity', 'multiplicative-objective', 'size'];
const fullChoices = [...prefix, 'yes', 'yes', 'yes'];
const statementUrl = 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=19';
const sketchUrl = 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/finals2017solutions.pdf#page=9';
const matches = row => String(row.source).toLowerCase() === 'icpc' && row.problemId === 'wf2017_j';
const candidates = evaluation => evaluation.current.techniques ?? [];
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-two-source-mixture-flow-'));
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
function walk(flow, choices, entry = domain) {
  const value = flow.walkFromRoot(choices, entry);
  assert.equal(value.consumed, choices.length, `${entry}/${choices.join('/')}: every feature answer is consumed`);
  return value;
}
function enterRoutes(flow, state) {
  for (let count = 0; flow.evaluateState(state).current.type === 'route'; ++count) {
    assert(count < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, choices) {
  let state = flow.initialState(domain);
  for (const answer of choices) state = flow.answerState(enterRoutes(flow, state), answer);
  return enterRoutes(flow, state);
}
const weight = state => state.answers.length + (state.trail ?? [])
  .reduce((sum, context) => sum + context.answers.length + 1, 0);
function checkSvg(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let edges = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: node is drawn`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the complete answer label is readable');
    }
    if (node.type === 'result') for (const techniqueId of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${techniqueId}/`));
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges);
  return svg;
}

// This interpreter uses only raw JSON. Its hashes were independently calculated
// from before-mixture-flows/walks, before consulting the newly registered walk.
function rawWalk(graphs, record) {
  const byId = new Map(graphs.map(graph => [graph.id, graph]));
  let graph = byId.get(record.entryGraphId ?? 'ranges');
  assert(graph, 'the original field exists');
  let node = graph.nodes.find(node => node.id === graph.root), consumed = 0;
  const steps = [];
  for (let limit = 0; limit < 2000; ++limit) {
    assert(node, 'the referenced node exists');
    if (node.type === 'route') {
      graph = byId.get(node.graph); assert(graph, 'the route target exists');
      node = graph.nodes.find(node => node.id === graph.root); continue;
    }
    if (node.type !== 'question' || consumed === record.choices.length) {
      assert.equal(consumed, record.choices.length);
      return { graph: graph.id, node: node.id, type: node.type,
        techniques: node.techniques ?? [], steps };
    }
    const answer = record.choices[consumed++];
    assert(Object.hasOwn(node.answers, answer), 'each original answer remains available');
    const target = node.answers[answer];
    steps.push({ graph: graph.id, node: node.id, answer, target });
    node = graph.nodes.find(node => node.id === target);
  }
  assert.fail('raw route replay did not terminate');
}
const frozenTerminalKeys = JSON.parse(inflateRawSync(Buffer.from('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', 'base64')).toString('utf8'));

test('the feature entrance requires shared capacity, multiplicative objective and numeric bounds in order', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15);
  const category = walk(flow, ['quantity-goals']);
  const option = flow.getNodeOptions(category.current).find(option => option.id === 'two-source-mixture');
  assert(option);
  assert.doesNotMatch(option.label, /ICPC|Pipe Stream|wf2017_j/i);
  for (let at = 0; at < guards.length; ++at) {
    const value = walk(flow, [...prefix, ...Array(at).fill('yes')]);
    assert.equal(value.graph.id, graphId);
    assert.notEqual(value.graph.entry, true);
    assert.equal(value.current.type, 'question');
    assert.equal(value.current.id, guards[at]);
    assert(!candidates(value).includes(id));
    assert.deepEqual(flow.getNodeOptions(value.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
  }
  const result = walk(flow, fullChoices);
  assert.equal(result.current.type, 'result');
  assert.deepEqual(candidates(result), [id]);
  const text = JSON.stringify(result.graph);
  for (const term of [/二種類/, /別々の始点/, /一つの終点/, /共有/, /保存則/, /逆向き/, /分離/, /幾何平均/, /一定/, /200/, /0〜10/, /100億|10\^10/, /自己ループ/, /重複/, /小数10桁/, /非連結/])
    assert.match(text, term);
});

test('all no and unknown guard answers go to condition-check without recommending the technique', async () => {
  const { flow } = await implementation;
  for (let at = 0; at < guards.length; ++at) for (const answer of ['no', 'unknown']) {
    const value = walk(flow, [...prefix, ...Array(at).fill('yes'), answer]);
    assert.equal(value.graph.id, 'condition-check', `${guards[at]}/${answer}`);
    assert.equal(value.current.type, 'question');
    assert(!candidates(value).includes(id));
  }
});

test('question and diagram views expose every answer label and the reusable article href', async () => {
  const { flow } = await implementation;
  const graph = flow.getGraph(graphId), svg = checkSvg(flow, graph);
  assert(svg.includes(`/flowchartcp/techniques/${id}/`));
  const html = flow.renderFlowHtml('/flowchartcp/');
  assert(html.includes('data-view="questions"'));
  assert(html.includes('data-view="diagram"'));
  assert(html.includes(`data-graph-panel="${graphId}"`));
  for (const node of graph.nodes) {
    assert(html.includes(`id="flow-text-${graphId}-${node.id}"`));
    assert(html.includes(xml(node.title)));
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      assert(html.includes(xml(option.label)));
      assert(html.includes(`#flow-text-${graphId}-${node.answers[option.id]}`));
    }
  }
  assert(html.includes(`/flowchartcp/techniques/${id}/`));
});

test('share URLs, diagrams, path highlights and Back preserve the same complete history', async () => {
  const { flow, viewer } = await implementation;
  const histories = [fullChoices];
  for (let at = 0; at < guards.length; ++at) for (const answer of ['no', 'unknown'])
    histories.push([...prefix, ...Array(at).fill('yes'), answer]);
  const diagrams = new Map();
  for (const choices of histories) {
    let state = replay(flow, choices);
    assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices).current);
    for (let limit = weight(state) + 1; ; --limit) {
      assert(limit > 0, 'Back terminates');
      assert.equal(flow.getFlowDomainId(state), domain);
      assert.deepEqual(flow.sanitizeState(state), state);
      const value = flow.evaluateState(state);
      if (!diagrams.has(state.graph)) diagrams.set(state.graph, checkSvg(flow, value.graph));
      const svg = diagrams.get(state.graph);
      assert(svg.includes(`data-node="${value.current.id}"`));
      for (const node of value.path) assert(svg.includes(`data-node="${node.id}"`));
      for (const edge of value.edges) assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
      const hash = flow.serializeFlowHash(state);
      assert.deepEqual(flow.parseFlowHash(hash), state);
      assert.deepEqual(viewer.diagramState(state.graph, hash), state);
      const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
      assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
      assert.equal(url.hash, hash);
      assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
      if (!weight(state)) break;
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state)); state = previous;
    }
    assert.deepEqual(state, flow.initialState(domain));
    assert.deepEqual(flow.backFlowState(state), state);
  }
});

test('metadata, article, independently verified reference, feature and example walk agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    json('data/two-source-mixture-problem-features.json'), json('data/problem-walks.json'),
  ]);
  const registrations = metadata.filter(row => row.id === id);
  assert.equal(registrations.length, 1);
  const technique = registrations[0];
  assert.equal(technique.kind, 'technique'); assert.equal(technique.status, 'reviewed');
  assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
  assert(technique.sources.includes(statementUrl)); assert(technique.sources.includes(sketchUrl));
  const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
  assert(new RegExp(`^techniqueId: ["']?${id}["']?\\s*$`, 'm').test(article));
  assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
    ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
  assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
  assert(!/<(?:details|summary)\b/i.test(article));
  assert(article.includes(`techniqueId="${id}"`));
  for (const source of technique.sources) assert(article.includes(source));
  for (const term of [/unofficial analysis/, /parse_decimal_10/, /optimize_two_source_mixture/, /int64_t/, /EPS/, /5回/, /非連結/, /0〜10/, /0\.01〜0\.99/, /10桁/, /10\^\{10\}/]) assert.match(article, term);
  const originalReferences = references.filter(row => matches(row) && row.techniqueId === id);
  assert.equal(originalReferences.length, 1);
  const reference = originalReferences[0];
  assert.equal(reference.url, statementUrl); assert.equal(reference.editorialUrl, sketchUrl);
  assert.equal(reference.verification, 'independent-analysis'); assert.equal(reference.difficulty, null);
  assert(reference.evidence.trim().length > 0);
  assert(!/checker|コンパイル|乱択|ASan|UBSan/.test(reference.evidence));
  assert.match(reference.verificationNotes, /unofficial analysis/);
  assert.match(reference.verificationNotes, /小数10桁/);
  const originals = features.filter(matches); assert.equal(originals.length, 1);
  const feature = originals[0];
  assert.deepEqual(feature.techniqueIds, [id]); assert.equal(feature.url, statementUrl);
  assert.equal(feature.evidenceUrl, sketchUrl); assert.equal(feature.reviewStatus, 'verified');
  assert.equal(feature.verification, 'independent-analysis');
  assert.equal(feature.publicationYear, 2017); assert.equal(feature.cutoff, '2026-10-14');
  assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
  const examples = walks.filter(row => matches(row) && row.expectedTechniqueIds.includes(id));
  assert.equal(examples.length, 1); const example = examples[0];
  assert.equal(example.entryGraphId, domain); assert.deepEqual(example.choices, fullChoices);
  assert.equal(example.statementUrl, statementUrl); assert.equal(example.reviewStatus, 'verified');
  assert.equal(example.verificationKind, 'independent-analysis'); assert.deepEqual(example.features, feature.features);
  assert.deepEqual(walk(flow, example.choices).steps.map(({ graph, node, answer }) => ({ graph, node, answer })), example.steps);
});

test('the resolved original keeps its unknown rating, verified year and unofficial-sketch provenance', async () => {
  const [references, features, walks, audit, plan] = await Promise.all([
    collections(/^references-.*\.json$/), json('data/two-source-mixture-problem-features.json'),
    json('data/problem-walks.json'), json('data/corpus-audits/icpc-2017-world-finals.json'), json('data/coverage-plan.json'),
  ]);
  const original = audit.records.find(matches); assert(original);
  assert.equal(original.contest.year, 2017); assert.equal(original.contest.exactDateVerified, false);
  assert.equal(original.difficulty, null); assert.notEqual(original.technicalFindings.verification, 'official-editorial');
  for (const row of [original, ...references.filter(row => matches(row) && row.techniqueId === id),
    ...features.filter(matches), ...walks.filter(row => matches(row) && row.expectedTechniqueIds.includes(id))]) {
    for (const key of ['publicationDate', 'publicationMonth', 'sourceDate', 'sourceMonth', 'contestYearMonth', 'publicationYearMonth'])
      assert.equal(row[key], undefined, `an unverified month or day is not invented in ${key}`);
    if (row.publicationYear !== undefined) assert.equal(row.publicationYear, 2017);
    if (row.difficulty !== undefined) assert.equal(row.difficulty, null);
    if (row.exactDateVerified !== undefined) assert.equal(row.exactDateVerified, false);
    if (row.contest) for (const key of ['date', 'yearMonth', 'month', 'day']) assert.equal(row.contest[key], undefined);
  }
  assert.equal(original.resolution.status, 'verified'); assert.deepEqual(original.resolution.techniqueIds, [id]);
  assert(original.resolution.notes.trim().length > 0); assert.equal(isCorpusSolutionReviewed(original), true);
  const gap = plan.knownGaps.find(row => row.id === id); assert(gap);
  assert.equal(gap.state, 'resolved'); assert.deepEqual(gap.techniqueIds, [id]);
});

test('the frozen 497 records retain every answer, step and exact terminal result', async () => {
  const { flow } = await implementation;
  const [walks, graphs] = await Promise.all([json('data/problem-walks.json'), json('data/flows.json')]);
  const previous = walks.slice(0, 497); assert.equal(previous.length, 497);
  assert.equal(digest(previous), '26352e4136a71d304b2981987b82a5874ff76e7b35c674d18cf4aa452c0ad59b');
  const observed = previous.map(row => rawWalk(graphs, row));
  assert.equal(digest(observed), '1d7a46ea4c4436556adc6fe4080b62795fc9e52ca9086a02b7b7ce811cf25063');
  assert.equal(digest(observed.map(row => row.steps)), 'c88642bedcfb3169091d0c3268a07668d0557a5c7c591f628e032bc9e937543a');
  previous.forEach((record, index) => {
    const value = walk(flow, record.choices, record.entryGraphId);
    assert.deepEqual({ graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps }, observed[index]);
    assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
    for (const techniqueId of record.expectedTechniqueIds) assert(candidates(value).includes(techniqueId));
  });
});

test('all 968 original terminal nodes keep their exact identities and technique lists', async () => {
  const graphs = await json('data/flows.json'), byId = new Map(graphs.map(graph => [graph.id, graph]));
  assert.equal(frozenTerminalKeys.length, 968);
  const terminals = frozenTerminalKeys.map(([graphId, nodeId]) => {
    const graph = byId.get(graphId); assert(graph);
    const node = graph.nodes.find(node => node.id === nodeId); assert(node);
    return { graph: graphId, node: nodeId, type: node.type, techniques: node.techniques ?? [] };
  });
  assert.equal(digest(terminals), '2bab121835e133cd4c5841b8d41a394cc3d0ce7e732256a3229747d14e0da9e1');
});
