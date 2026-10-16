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
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-usaco-interval-grid-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Specify the feature entrances, applicability checks and source months
// independently of the registered example walks.
const tasks = [
  {
    id: 'xor-bounded-triples-intervals', problemId: '1070', title: 'Cowmistry',
    domain: 'math', prefix: ['counting-totals', 'count', 'xor-triples'],
    graph: 'xor-interval-triples-conditions', guards: ['interval-union', 'pairwise-limit', 'size'],
    yearMonth: '2020-12',
    statementUrl: 'https://usaco.org/index.php?page=viewproblem2&cpid=1070',
    editorialUrl: 'https://usaco.org/current/data/sol_prob3_platinum_dec20.html',
    terms: [/区間/, /三数|三つ|3.*数/, /全.*組|全.*対|三組|3組|各組/, /XOR/, /重なら|重複/, /20000|20,000|2万/],
  },
  {
    id: 'grid-rectangle-components-euler-boundary', problemId: '1094', title: 'Paint by Letters',
    domain: 'grid-arrangements', prefix: ['color-numbers', 'rectangle-components'],
    graph: 'grid-rectangle-components-conditions', guards: ['static-grid', 'rectangle-only', 'size'],
    yearMonth: '2021-01',
    statementUrl: 'https://usaco.org/index.php?page=viewproblem2&cpid=1094',
    editorialUrl: 'https://usaco.org/current/data/sol_prob3_platinum_jan21.html',
    terms: [/静的|変わら|変化せず|更新.*な/, /長方形/, /四方向|4方向|上下左右|辺.*共有/, /外|内部/, /1000|1,000/],
  },
];
const ids = tasks.map(item => item.id);
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const candidates = value => value.current.techniques ?? [];
const matchesOriginal = (row, item) => String(row.source).toLowerCase() === 'usaco' && row.problemId === item.problemId;
const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
async function collections(expression) {
  const names = (await readdir(path.join(site, 'data'))).filter(name => expression.test(name));
  return (await Promise.all(names.map(name => json('data/' + name)))).flat();
}
function walk(flow, domain, choices) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, `${domain}/${choices.join('/')}: consume every fixed answer`);
  return value;
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
function svgMatchesGraph(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let answers = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: node is drawn`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++answers;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'full answer text is available in the diagram');
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${id}/`), 'diagram results link to the article');
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, answers);
  return svg;
}

test('both fixed feature paths require all three applicability checks before the single-technique result', async () => {
  const { flow } = await implementation;
  assert.equal(flow.entryGraphs.length, 15, 'preserve all existing field entrances');
  for (const item of tasks) {
    assert(flow.entryGraphs.some(graph => graph.id === item.domain));
    const initial = walk(flow, item.domain, item.prefix);
    assert.equal(initial.graph.id, item.graph);
    assert.notEqual(initial.graph.entry, true, 'new conditions remain below a field entrance');
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard]);
      assert(ids.every(id => !candidates(value).includes(id)), 'no guard can be bypassed');
      const options = flow.getNodeOptions(value.current);
      assert.deepEqual(options.map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const option of options) assert(option.label.length >= 2);
    }
    const result = walk(flow, item.domain, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(result.current.type, 'result');
    assert.deepEqual(candidates(result), [item.id]);
    for (const term of item.terms) assert.match(JSON.stringify(result.graph), term);
    assert(svgMatchesGraph(flow, result.graph).includes(`/flowchartcp/techniques/${item.id}/`));
  }
});

test('no and unknown at every required condition go to condition-check', async () => {
  const { flow } = await implementation;
  for (const item of tasks) for (let guard = 0; guard < item.guards.length; ++guard)
    for (const answer of ['no', 'unknown']) {
      const result = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(result.graph.id, 'condition-check', `${item.id}/${item.guards[guard]}/${answer}`);
      assert.equal(result.current.type, 'question');
      assert(ids.every(id => !candidates(result).includes(id)));
    }
});

test('question and diagram displays share complete histories, highlights, URLs and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of tasks) {
    const histories = [[...item.prefix, 'yes', 'yes', 'yes']];
    for (let guard = 0; guard < item.guards.length; ++guard)
      for (const answer of ['no', 'unknown']) histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item.domain, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
      for (let remaining = weight(state) + 1; ; --remaining) {
        assert(remaining > 0, 'Back terminates');
        assert.equal(flow.getFlowDomainId(state), item.domain);
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
      assert.deepEqual(state, flow.initialState(item.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  }
});

test('new articles, reviewed references, searchable metadata and original walks agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    collections(/-problem-features\.json$/), json('data/problem-walks.json'),
  ]);
  const headings = ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'];
  for (const item of tasks) {
    const registrations = metadata.filter(row => row.id === item.id);
    assert.equal(registrations.length, 1);
    const technique = registrations[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert(technique.sources.includes(item.statementUrl));
    assert(technique.sources.includes(item.editorialUrl));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert(new RegExp(`^techniqueId: ["']?${item.id}["']?\\s*$`, 'm').test(article));
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]), headings);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, 'one complete visible reusable C++ example');
    assert(!/<(?:details|summary)\b/i.test(article));
    assert(article.includes(`techniqueId="${item.id}"`));
    for (const source of technique.sources) assert(article.includes(source));
    const originalRefs = references.filter(row => matchesOriginal(row, item) && row.techniqueId === item.id);
    assert.equal(originalRefs.length, 1);
    const reference = originalRefs[0];
    assert.equal(reference.url, item.statementUrl);
    assert.equal(reference.editorialUrl, item.editorialUrl);
    assert.equal(reference.verification, 'editorial');
    assert.equal(reference.difficulty, 'USACO Platinum');
    assert(reference.evidence.trim().length > 0);
    assert(!/テスト|checker|コンパイル|乱択|ASan|UBSan/i.test(reference.evidence), 'evidence describes applicability, verificationNotes contain tests');
    assert(reference.verificationNotes.trim().length > 0);
    const originalFeatures = features.filter(row => matchesOriginal(row, item) && row.techniqueIds.includes(item.id));
    assert.equal(originalFeatures.length, 1);
    const feature = originalFeatures[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.verification, 'editorial');
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.cutoff, '2026-10-14');
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert(feature.features.length >= 2);
    const originalWalks = walks.filter(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(originalWalks.length, 1);
    const record = originalWalks[0];
    assert.equal(record.statementUrl, item.statementUrl);
    assert.equal(record.entryGraphId, item.domain);
    assert.equal(record.reviewStatus, 'verified');
    assert.equal(record.verificationKind, 'editorial');
    assert.deepEqual(record.choices, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.deepEqual(record.features, feature.features);
    const result = walk(flow, record.entryGraphId, record.choices);
    assert.deepEqual(candidates(result), [item.id]);
    assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
  }
});

test('original references preserve the verified contest month without inventing publication days', async () => {
  const [references, features, walks, audit] = await Promise.all([
    collections(/^references-.*\.json$/), collections(/-problem-features\.json$/),
    json('data/problem-walks.json'), json('data/corpus-audits/usaco-2020-dec-2021-jan-platinum.json'),
  ]);
  for (const item of tasks) {
    const original = audit.records.find(row => matchesOriginal(row, item));
    assert(original);
    assert.equal(original.contest.yearMonth, item.yearMonth);
    assert.equal(original.contest.exactDateVerified, false);
    assert.equal(original.difficulty, 'USACO Platinum');
    const related = [original,
      ...references.filter(row => matchesOriginal(row, item) && row.techniqueId === item.id),
      ...features.filter(row => matchesOriginal(row, item) && row.techniqueIds.includes(item.id)),
      ...walks.filter(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id)),
    ];
    for (const row of related) {
      assert.equal(row.publicationDate, undefined, 'the exact date is unverified');
      if (row.contestYearMonth !== undefined) assert.equal(row.contestYearMonth, item.yearMonth);
    }
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id]);
    assert.equal(isCorpusSolutionReviewed(original), true, 'a mapping does not replace independent solution review');
  }
});

test('the frozen 487 original walks are unchanged and still replay with the same complete steps and results', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  const original = walks.slice(0, 487);
  assert.equal(original.length, 487);
  assert.equal(createHash('sha256').update(JSON.stringify(original)).digest('hex'),
    '152a26567809664bfb31c56c3d4ad6cfd8aaaa5a2dfe0887a2721db1e93840f4',
    'the full preexisting records are preserved in their original order');
  for (const record of original) {
    const result = walk(flow, record.entryGraphId, record.choices);
    assert.equal(result.current.type, 'result', `${record.source}/${record.problemId}`);
    assert(record.expectedTechniqueIds.every(id => candidates(result).includes(id)),
      `${record.source}/${record.problemId}: every originally required technique is still present`);
    assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
  }
});
