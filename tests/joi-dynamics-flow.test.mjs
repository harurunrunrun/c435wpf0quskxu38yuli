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
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-joi-dynamics-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// Fixed independently before registration: data and example walks are the
// subjects of these assertions, never the source of expected routes or dates.
const tasks = [
  {
    id: 'directed-reciprocal-closure-dsu-small-to-large', source: 'joi',
    domain: 'graphs', prefix: ['network-connection', 'connectivity', 'direction-goals', 'reciprocal-closure'],
    graph: 'reciprocal-closure-conditions', guards: ['closure-rule', 'insert-only', 'size'],
    terms: [/有向|向き|方向/, /相互|双方向|互い/, /追加|挿入/, /追加.*だけ|追加.*のみ|挿入.*だけ|挿入.*のみ|削除.*な/, /閉包|規則/],
    problemId: 'joi2020sc_joitter2', day: 2, date: '2020-03-21', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/joitter2.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/joitter2-review.pdf',
    auditFile: 'data/corpus-audits/joi-2020-spring.json',
  },
  {
    id: 'interval-stabbing-endpoint-contraction-dsu', source: 'joi',
    domain: 'geometry', prefix: ['travel-partition', 'conditional-point-moves', 'triangle'],
    alternateRoutes: [{ domain: 'ranges', prefix: ['interval-endpoint-shrink', 'intervals'],
      guards: ['shrink-only', 'known-coordinates', 'size'] }],
    graph: 'conditional-point-contractions', guards: ['triangle-condition', 'shrink-only', 'known-coordinates', 'size'],
    terms: [/三角|x\s*\+\s*y|X\s*\+\s*Y/, /端点/, /縮|狭/, /既知|事前|先に|全て|すべて/],
    problemId: 'joi2020sc_sweeping', day: 1, date: '2020-03-20', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day1/sweeping.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day1/sweeping-review.pdf',
    auditFile: 'data/corpus-audits/joi-2020-spring.json',
  },
  {
    id: 'paired-height-survivors-weighted-dyck-dp', source: 'joi',
    domain: 'dp', prefix: ['generation-history', 'paired-survivors'],
    graph: 'paired-height-survivor-conditions', guards: ['paired-heights', 'simultaneous-decay', 'bounded-survivors'],
    terms: [/二つ|二個|2つ|二本|対|ペア/, /同時|一斉/, /減|崩|消/, /残|生存/, /高さ/],
    problemId: 'joi2020sc_ruins3', day: 2, date: '2020-03-21', verification: 'editorial',
    statementUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/ruins3.pdf',
    editorialUrl: 'https://www2.ioi-jp.org/camp/2020/2020-sp-tasks/day2/ruins3-review.pdf',
    auditFile: 'data/corpus-audits/joi-2020-spring.json',
  },
  {
    id: 'nested-rectangle-corner-sweep-and-validation', source: 'icpc',
    domain: 'geometry', prefix: ['boundary-relations', 'paired-corners'],
    graph: 'nested-corner-conditions', guards: ['corner-model', 'laminar-boundaries', 'size'],
    terms: [/左上/, /右下/, /包含|入れ子/, /境界/, /交差|接触/],
    problemId: 'wf2017_l', year: 2017, verification: 'independent-analysis',
    statementUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/icpc2017.pdf#page=23',
    editorialUrl: 'https://icpc.global/worldfinals/problems/2017-ICPC-World-Finals/finals2017solutions.pdf#page=11',
    auditFile: 'data/corpus-audits/icpc-2017-world-finals.json',
  },
];
const ids = tasks.map(item => item.id);
const routes = tasks.flatMap(item => [item, ...(item.alternateRoutes ?? []).map(route => ({ ...item, ...route }))]);
const candidates = value => value.current.techniques ?? [];
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const matchesOriginal = (row, item) => String(row.source).toLowerCase() === item.source && row.problemId === item.problemId;
const xml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

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
        `${graph.id}/${node.id}/${option.id}: each graph answer has its SVG edge`);
      assert(svg.includes(`<title>${xml(option.label)}</title>`),
        `${graph.id}/${node.id}/${option.id}: each answer has its full readable label`);
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`/flowchartcp/techniques/${id}/`), `${graph.id}/${id}: the article link is drawn`);
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, answerCount, 'the SVG adds no answer edges');
  return svg;
}

test('the fixed five feature paths reach four single-technique results only after every required guard', async () => {
  const { flow } = await implementation;
  assert.equal(new Set(ids).size, 4);
  assert.equal(routes.length, 5);
  assert.equal(tasks.reduce((sum, item) => sum + item.guards.length, 0), 13);
  for (const item of routes) {
    const initial = walk(flow, item.domain, item.prefix);
    assert.equal(initial.graph.id, item.graph, `${item.id}/${item.domain}: reach the fixed applicability chart`);
    assert.equal(initial.current.id, item.guards[0]);
    assert.notEqual(initial.graph.entry, true, 'the chart stays under existing field entrances');
    for (let guard = 0; guard < item.guards.length; ++guard) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard], `${item.id}: check each necessary premise in order`);
      assert(ids.every(id => !candidates(value).includes(id)), 'no technique result skips a guard');
      const options = flow.getNodeOptions(value.current);
      assert.deepEqual(options.map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const option of options) assert(option.label.length >= 2, 'applicability answers have readable labels');
    }
    const value = walk(flow, item.domain, [...item.prefix, ...Array(item.guards.length).fill('yes')]);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id], 'all yes selects exactly the expected technique');
    for (const term of item.terms) assert.match(JSON.stringify(value.graph), term, `${item.id}: show the necessary problem features`);
    assert(svgMatchesGraph(flow, value.graph).includes(`/flowchartcp/techniques/${item.id}/`));
  }
  assert.equal(flow.entryGraphs.length, 15, 'the fifteen existing field entrances are preserved');
  for (const domain of new Set(routes.map(item => item.domain)))
    assert(flow.entryGraphs.some(graph => graph.id === domain));
});

test('no and unknown at every guard, and unknown movement kind from either entrance, require condition checking', async () => {
  const { flow } = await implementation;
  for (const item of routes) for (let guard = 0; guard < item.guards.length; ++guard) {
    for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item.domain, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(value.graph.id, 'condition-check', `${item.id}/${item.guards[guard]}/${answer}: check the missing premise`);
      assert.equal(value.current.type, 'question');
      assert(ids.every(id => !candidates(value).includes(id)), 'unsupported premises do not assert a new technique');
    }
  }
  for (const item of routes.filter(row => row.id === 'interval-stabbing-endpoint-contraction-dsu')) {
    const beforeKind = walk(flow, item.domain, item.prefix.slice(0, -1));
    assert.equal(beforeKind.graph.id, 'conditional-point-contractions');
    assert.equal(beforeKind.graph.root, 'movement-kind');
    assert.equal(beforeKind.current.id, 'movement-kind');
    assert.equal(beforeKind.current.type, 'question');
    const value = walk(flow, item.domain, [...item.prefix.slice(0, -1), 'unknown']);
    assert.equal(value.graph.id, 'condition-check', 'unknown movement kind never guesses an interval or triangle model');
    assert.equal(value.current.type, 'question');
    assert(ids.every(id => !candidates(value).includes(id)));
  }
});

test('question and diagram sharing restores path highlights, all histories and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of routes) {
    const histories = [[...item.prefix, ...Array(item.guards.length).fill('yes')]];
    for (let guard = 0; guard < item.guards.length; ++guard)
      for (const answer of ['no', 'unknown'])
        histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    if (item.id === 'interval-stabbing-endpoint-contraction-dsu')
      histories.push([...item.prefix.slice(0, -1), 'unknown']);
    for (const choices of histories) {
      let state = replay(flow, item.domain, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
      for (let remaining = weight(state) + 1; ; --remaining) {
        assert(remaining > 0, 'Back terminates');
        assert.equal(flow.getFlowDomainId(state), item.domain, 'retain the entrance used for this history');
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluation = flow.evaluateState(state);
        if (!diagrams.has(state.graph)) diagrams.set(state.graph, svgMatchesGraph(flow, evaluation.graph));
        const svg = diagrams.get(state.graph);
        assert(svg.includes(`data-node="${evaluation.current.id}"`), 'the current position exists in the diagram');
        for (const node of evaluation.path) assert(svg.includes(`data-node="${node.id}"`), 'every highlighted node exists');
        for (const edge of evaluation.edges)
          assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`), 'every highlighted answer edge exists');
        const hash = flow.serializeFlowHash(state);
        assert.deepEqual(flow.parseFlowHash(hash), state, 'the question URL restores the canonical history');
        assert.deepEqual(viewer.diagramState(state.graph, hash), state, 'the diagram restores the same question state');
        const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
        assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
        assert.equal(url.hash, hash, 'the shared diagram URL retains the full history');
        assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
        if (!weight(state)) break;
        const previous = flow.backFlowState(state);
        assert(weight(previous) < weight(state), 'Back removes a canonical step');
        state = previous;
      }
      assert.deepEqual(state, flow.initialState(item.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  }
});

test('four new articles have reviewed metadata, searchable aliases, eight visible sections, C++ and fixed original walks', async () => {
  const { flow } = await implementation;
  const [metadata, references, walks] = await Promise.all([
    loadCollections(/^techniques-.*\.json$/), loadCollections(/^references-.*\.json$/), json('data/problem-walks.json'),
  ]);
  const headings = ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'];
  for (const item of tasks) {
    const registered = metadata.filter(row => row.id === item.id);
    assert.equal(registered.length, 1, 'each technique has exactly one registration');
    const technique = registered[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)), 'an English alias is searchable');
    assert(technique.sources.includes(item.statementUrl), 'metadata identifies the fixed original');
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert(new RegExp(`^techniqueId: ["']?${item.id}["']?\\s*$`, 'm').test(article));
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]), headings);
    assert((article.match(/^```cpp\s*$/gm) ?? []).length >= 1, 'a reusable C++ implementation is displayed');
    assert(!/<(?:details|summary)\b/i.test(article), 'the explanation and implementation are initially visible');
    assert(article.includes(`techniqueId="${item.id}"`), 'the verified-original component is present');
    for (const source of technique.sources) assert(article.includes(source), 'all metadata sources are accessible from the article');
    assert(article.includes(item.statementUrl), 'the original problem URL is visible');
    if (item.source === 'icpc') {
      assert.match(article, /非公式|unofficial/i, 'the public sketch is explicitly identified as unofficial');
      assert.match(article, /独立|independent/i, 'independent construction or validation is distinguished from the public sketch');
    }
    const originals = references.filter(row => row.techniqueId === item.id && matchesOriginal(row, item));
    assert.equal(originals.length, 1, 'the fixed original reference is registered exactly once');
    const original = originals[0];
    assert.equal(original.url, item.statementUrl);
    assert.equal(original.verification, item.verification);
    assert.equal(original.cutoffVerification, 'contest-before-cutoff');
    assert(original.evidence.trim().length > 0);
    const records = walks.filter(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(records.length, 1, 'the original has one confirmed root walk');
    const record = records[0];
    assert.equal(record.statementUrl, item.statementUrl);
    assert.equal(record.reviewStatus, 'verified');
    assert.equal(record.verificationKind, item.verification);
    assert.equal(record.cutoffVerification, 'contest-before-cutoff');
    assert.equal(record.entryGraphId, item.domain);
    assert.deepEqual(record.choices, [...item.prefix, ...Array(item.guards.length).fill('yes')], 'the example follows the independent fixed feature path');
    assert(record.features.length >= 2);
    const value = walk(flow, record.entryGraphId, record.choices);
    assert.deepEqual(candidates(value), [item.id]);
    assert.deepEqual(value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), record.steps);
  }
});

test('the four feature records match original refs and walks, preserving exact JOI days and only the verified ICPC year', async () => {
  const [features, references, walks, joi, icpc] = await Promise.all([
    json('data/joi-dynamics-problem-features.json'), loadCollections(/^references-.*\.json$/),
    json('data/problem-walks.json'), json('data/corpus-audits/joi-2020-spring.json'),
    json('data/corpus-audits/icpc-2017-world-finals.json'),
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
    assert(feature.features.length >= 2);
    assert(feature.evidenceUrl.startsWith('https://'));
    const audit = item.source === 'joi' ? joi : icpc;
    const originalAudit = audit.records.find(row => matchesOriginal(row, item));
    assert(originalAudit);
    if (item.source === 'joi') {
      assert.equal(feature.publicationDate, item.date);
      assert(feature.publicationDate < feature.cutoff);
      assert.equal(originalAudit.contest.date, item.date);
      assert.equal(originalAudit.contest.day, item.day);
      assert.equal(originalAudit.contest.exactDateVerified, true);
    } else {
      assert.equal(String(feature.publicationYear), '2017');
      assert.equal(feature.publicationDate, undefined, 'do not invent an unverified ICPC contest day');
      assert.equal(feature.publicationMonth, undefined, 'only the year is verified for this original');
      assert.equal(feature.contestYearMonth, undefined);
      assert(String(feature.publicationYear) < feature.cutoff.slice(0, 4));
      assert.equal(originalAudit.contest.year, item.year);
      assert.equal(originalAudit.contest.exactDateVerified, false);
    }
    const reference = references.find(row => matchesOriginal(row, item) && row.techniqueId === item.id);
    const record = walks.find(row => matchesOriginal(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert(reference && record);
    assert.equal(reference.url, feature.url);
    assert.equal(reference.verification, feature.verification);
    assert.deepEqual(record.features, feature.features);
    actualPairs.push(`${item.source}/${item.problemId}/${item.id}`);
  }
  assert.deepEqual(actualPairs.sort(), references.filter(row => ids.includes(row.techniqueId))
    .map(row => `${String(row.source).toLowerCase()}/${row.problemId}/${row.techniqueId}`).sort(),
  'the new four feature mappings and fixed original references agree without relying on an old corpus size');
});

test('the four new implementations append explicit verified resolutions to their original fixed-corpus records', async () => {
  const audits = new Map(await Promise.all([...new Set(tasks.map(item => item.auditFile))]
    .map(async relative => [relative, await json(relative)])));
  for (const item of tasks) {
    const original = audits.get(item.auditFile).records.find(row => matchesOriginal(row, item));
    assert(original);
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id]);
    assert.match(original.resolution.reviewedAt, /^\d{4}-\d{2}-\d{2}$/);
    assert(original.resolution.notes.trim().length > 0);
    assert.equal(isCorpusSolutionReviewed(original), true, 'the reference mapping does not replace the underlying solution review');
  }
});
