import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-ioi2019-three-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// These feature paths and guards were specified independently of the newly
// registered problem walks. The example records cannot select their own route.
const tasks = [
  {
    id: 'oriented-equal-pair-adjacent-swaps-fenwick', task: 'shoes', number: 1,
    domain: 'ranges', prefix: ['sequence-changes', 'oriented-pairs'],
    graph: 'oriented-pair-swaps-conditions', guards: ['oriented-equal-pairs', 'adjacent-only', 'balanced-and-bounds'],
    verification: 'editorial', featureVerification: 'official-editorial', day: 1, date: '2019-08-06',
    terms: [/左/, /右/, /隣接/, /同.*サイズ/, /64/],
  },
  {
    id: 'rotated-manhattan-two-mark-boolean-circuit', task: 'vision', number: 5,
    domain: 'math', prefix: ['bits-digits', 'two-mark-distance-circuit'],
    graph: 'two-mark-manhattan-circuit-conditions', guards: ['two-unknown-marks', 'sequential-gates', 'size'],
    verification: 'independent-analysis', featureVerification: 'independent-analysis', day: 2, date: '2019-08-08',
    terms: [/二つ|2つ/, /画像/, /最後/, /空入力/, /200/, /3190/, /86368/],
  },
  {
    id: 'dfs-lowlink-three-size-two-connected-partition', task: 'split', number: 2,
    domain: 'graphs', prefix: ['group-constraints', 'three-size-two-connected'],
    graph: 'three-size-two-connected-conditions', guards: ['connected-undirected', 'positive-three-sizes', 'two-connected-enough'],
    verification: 'independent-analysis', featureVerification: 'independent-analysis', day: 1, date: '2019-08-06',
    terms: [/無向/, /連結/, /正/, /三|3/, /少なくとも二つ|少なくとも二|少なくとも2/],
  },
].map(item => ({ ...item, problemId: 'ioi2019_' + item.task,
  statementUrl: `https://ioinformatics.org/files/ioi2019problem${item.number}.pdf`,
  editorialUrl: `https://ioi.te.lv/locations/ioi19/contest/day${item.day}/${item.task[0].toUpperCase() + item.task.slice(1)}/review.pdf` }));
const ids = tasks.map(item => item.id);
const candidates = value => value.current.techniques ?? [];
const matches = (row, item) => String(row.source).toLowerCase() === 'ioi' && row.problemId === item.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
async function collections(expression) {
  return (await Promise.all((await readdir(path.join(site, 'data')))
    .filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function walk(flow, item, choices) {
  const value = flow.walkFromRoot(choices, item.domain);
  assert.equal(value.consumed, choices.length, `${item.domain}/${choices.join('/')}: consume every fixed answer`);
  return value;
}
function enterRoutes(flow, state) {
  for (let limit = 0; flow.evaluateState(state).current.type === 'route'; ++limit) {
    assert(limit < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, item, choices) {
  let state = flow.initialState(item.domain);
  for (const answer of choices) state = flow.answerState(enterRoutes(flow, state), answer);
  return enterRoutes(flow, state);
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}
function checkSvg(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let edges = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: node is visible`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the full answer label is readable');
    }
    if (node.type === 'result') for (const id of node.techniques ?? [])
      assert(svg.includes(`href="/flowchartcp/techniques/${id}/"`), 'the result links to its article');
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges, 'no answer edges are added');
  return svg;
}

test('the three IOI 2019 fixed feature paths require all nine guards and select one article each', async () => {
  const { flow } = await implementation;
  assert.deepEqual(flow.validateGraphs(), []);
  assert.equal(flow.entryGraphs.length, 15, 'the original fields remain the top-level entrances');
  for (const item of tasks) {
    assert.equal(flow.getGraph(item.domain).entry, true);
    for (let guard = 0; guard < 3; ++guard) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes')]);
      assert.equal(value.graph.id, item.graph);
      assert.equal(value.current.type, 'question');
      assert.equal(value.current.id, item.guards[guard]);
      assert.notEqual(value.graph.entry, true);
      assert.equal(flow.getFlowDomainId(flow.initialState(item.graph)), item.domain);
      assert(ids.every(id => !candidates(value).includes(id)));
      assert.deepEqual(flow.getNodeOptions(value.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
    }
    const value = walk(flow, item, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(value.current.type, 'result');
    assert.deepEqual(candidates(value), [item.id]);
    for (const term of item.terms) assert.match(JSON.stringify(value.graph), term);
    checkSvg(flow, value.graph);
  }
});

test('no and unknown at each of the nine guards require condition checking and never assert a new technique', async () => {
  const { flow } = await implementation;
  for (const item of tasks) for (let guard = 0; guard < 3; ++guard)
    for (const answer of ['no', 'unknown']) {
      const value = walk(flow, item, [...item.prefix, ...Array(guard).fill('yes'), answer]);
      assert.equal(value.graph.id, 'condition-check', `${item.graph}/${item.guards[guard]}/${answer}`);
      assert.equal(value.current.type, 'question');
      assert(ids.every(id => !candidates(value).includes(id)));
    }
});

test('question and diagram sharing restore every new history, highlights and finite Back steps', async () => {
  const { flow, viewer } = await implementation;
  const diagrams = new Map();
  for (const item of tasks) {
    const histories = [[...item.prefix, 'yes', 'yes', 'yes']];
    for (let guard = 0; guard < 3; ++guard) for (const answer of ['no', 'unknown'])
      histories.push([...item.prefix, ...Array(guard).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, item, choices);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, item, choices).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0, 'Back terminates');
        assert.equal(flow.getFlowDomainId(state), item.domain, 'retain the originating field');
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluation = flow.evaluateState(state);
        if (!diagrams.has(state.graph)) diagrams.set(state.graph, checkSvg(flow, evaluation.graph));
        const svg = diagrams.get(state.graph);
        assert(svg.includes(`data-node="${evaluation.current.id}"`));
        for (const node of evaluation.path) assert(svg.includes(`data-node="${node.id}"`));
        for (const edge of evaluation.edges)
          assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
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

test('the pre-integration 498 records preserve every answer step and terminal node', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 501);
  const previous = walks.slice(0, 498);
  // The terminal hash was produced from the independently preserved old flow
  // JSON, including target IDs, rather than the implementation under test.
  assert.equal(digest(previous), '2a9a41af005f79a7d895b6ee45740a77a3642236309b10952ceeec76d7cc8b1e');
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const id of row.expectedTechniqueIds) assert(candidates(value).includes(id));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'c3329a5d61831466ebc77580fa675d64119af2416b44513ededa19cd8c55c769');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getGraph(value.graph).nodes.find(node => node.id === value.node).title,
    techniques: value.techniques, steps: value.steps.map(step => {
      const node = flow.getGraph(step.graph).nodes.find(node => node.id === step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), '2b51791789485172d1f92a212de25cb8cc3c166cc696fb623e50bc35c5e42c00');
  assert.equal(digest(flow.getGraph('range-sequence-changes').nodes.find(node => node.id === 'reorder-operation')),
    '103d173fe992b42cd20d569a57cd51bd4bfbe84e2f171ef19597b91889fad13e',
    'the frozen nonroot reorder-operation question is untouched');

});

test('the three visible reusable articles, references, dated originals and example walks agree', async () => {
  const { flow } = await implementation;
  const [metadata, references, features, walks] = await Promise.all([
    collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/),
    collections(/problem-features\.json$/), json('data/problem-walks.json'),
  ]);
  for (const item of tasks) {
    const registered = metadata.filter(row => row.id === item.id);
    assert.equal(registered.length, 1);
    const technique = registered[0];
    assert.equal(technique.kind, 'technique');
    assert.equal(technique.status, 'reviewed');
    assert(technique.aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert(technique.sources.includes(item.statementUrl));
    assert(technique.sources.includes(item.editorialUrl));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', item.id + '.mdx'), 'utf8');
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
      ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
    assert(!/<(?:details|summary)\b/i.test(article));
    assert(article.includes(`techniqueId="${item.id}"`));
    for (const source of technique.sources) assert(article.includes(source));
    const originals = references.filter(row => row.techniqueId === item.id && matches(row, item));
    assert.equal(originals.length, 1);
    const reference = originals[0];
    assert.equal(reference.url, item.statementUrl);
    assert.equal(reference.editorialUrl, item.editorialUrl);
    assert.equal(reference.verification, item.verification);
    assert.equal(reference.sourceDate, item.date);
    assert.equal(reference.difficulty, null, 'an unverified difficulty is not invented');
    assert(reference.evidence.trim().length > 0);
    const matchingFeatures = features.filter(row => matches(row, item));
    assert.equal(matchingFeatures.length, 1);
    const feature = matchingFeatures[0];
    assert.deepEqual(feature.techniqueIds, [item.id]);
    assert.equal(feature.url, item.statementUrl);
    assert.equal(feature.evidenceUrl, item.editorialUrl);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, item.featureVerification);
    assert.equal(feature.publicationDate, item.date);
    assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, item) && row.expectedTechniqueIds.includes(item.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, item.domain);
    assert.deepEqual(example.choices, [...item.prefix, 'yes', 'yes', 'yes']);
    assert.equal(example.statementUrl, item.statementUrl);
    assert.equal(example.reviewStatus, 'verified');
    assert.equal(example.verificationKind, item.verification);
    assert.equal(example.cutoffVerification, 'contest-before-cutoff');
    assert.deepEqual(example.features, feature.features);
    assert.deepEqual(walk(flow, item, example.choices).steps
      .map(({ graph, node, answer }) => ({ graph, node, answer })), example.steps);
  }
});

test('the initial IOI 2019 six records and numeric uncertainty are preserved while three implementation gaps resolve', async () => {
  const [audit, plan] = await Promise.all([json('data/corpus-audits/ioi-2019.json'), json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.techniqueMetadataCount, 472);
  assert.equal(audit.snapshot.flowGraphCount, 439);
  const hashes = { flow: '39a3d2089b8f5ac9e684092543ac49f5005555d3b6e8c0d4be3cdc2a9b1e0181',
    technique: 'd37e0dd7a9ba814ecc61f4c5ac2bc1165dfe3f61deaf689e3a7c92d0210e1d40' };
  for (const name of ['flow', 'technique']) {
    const bytes = gunzipSync(await readFile(path.join(site, audit.snapshot[name + 'SnapshotFile'])));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), hashes[name]);
    assert.equal(audit.snapshot[name + 'Sha256'], hashes[name]);
  }
  assert.equal(digest(audit.status), '97304fd0c87f1c7c436731c69d29cf89addea388a81e6d74764ca14e9e6c41d3');
  assert.equal(audit.status.solutionReviewedCount, 3);
  assert.equal(audit.status.numericBoundsVerifiedCount, 0);
  assert.equal(audit.status.unconfirmedCount, 3);
  assert.equal(audit.status.globalCoverageComplete, false);
  const originalHashes = {
    ioi2019_shoes: '7a2b5a121b4902bf4504335b3bbf25ea303fc3b1eab842f3fefe9a365b94ffd5',
    ioi2019_split: 'bbbbbb9e1cc5453500fe4a26eed697ad2d8987eea604346dfe6b8f559bf5aa48',
    ioi2019_rect: 'bfb941edb35dfbf0e60425253af55ae7e2612437ceae943fd004e449d7a467db',
    ioi2019_line: '5f849b3da2699b4421788ade413c553bbbc2cf2cf6d8a63436cb06c02fb519e8',
    ioi2019_vision: 'b5816802d772bf36f4979c857036725ffefa468e2603bff0c3019cd8e10a2131',
    ioi2019_walk: 'a3498cfffcc48f3c44b9aa7ffc1db42ebcf0456563df5165764a87f9e8608bb2',
  };
  assert.equal(audit.records.length, 6);
  const initial = audit.records.map(row => Object.fromEntries(Object.entries(row)
    .filter(([key]) => !['resolution', 'subsequentSolutionReviews', 'subsequentSourceVerifications'].includes(key))));
  for (const row of initial) {
    assert.equal(digest(row), originalHashes[row.problemId], row.problemId + ': every initial field is intact');
    assert.equal(row.constraints.numericBoundsVerified, false);
  }
  assert.deepEqual(initial.filter(isCorpusSolutionReviewed).map(row => row.problemId).sort(),
    ['ioi2019_shoes', 'ioi2019_split', 'ioi2019_vision']);
  for (const row of initial.filter(row => ['rect', 'line', 'walk'].includes(row.officialTaskId))) {
    assert.equal(row.reviewStatus, 'unconfirmed');
    assert.equal(row.resolution, undefined);
    assert.equal(isCorpusSolutionReviewed(row), false);
  }
  for (const item of tasks) {
    const original = audit.records.find(row => matches(row, item));
    assert(original);
    assert.equal(original.contest.date, item.date);
    assert.equal(original.contest.day, item.day);
    assert.equal(original.contest.exactDateVerified, true);
    assert.equal(original.difficulty, null);
    assert.equal(original.resolution.status, 'verified');
    assert.deepEqual(original.resolution.techniqueIds, [item.id]);
    assert(original.resolution.notes.trim().length > 0);
    assert.equal(isCorpusSolutionReviewed(original), true);
    const gap = plan.knownGaps.find(row => row.id === original.gap.id);
    assert(gap);
    assert.equal(gap.state, 'resolved');
    assert.equal(gap.problemId, item.problemId);
    assert.deepEqual(gap.techniqueIds, [item.id]);
    const sourceReview = original.subsequentSourceVerifications.find(row => row.status === 'verified'
      && (row.originalNumericBoundsVerified === true || row.numericBoundsVerified === true));
    assert(sourceReview, 'later explicit numeric evidence is required; the initial false stays false');
    assert.match(sourceReview.checkedAt, /^\d{4}-\d{2}-\d{2}$/);
    if (item.task === 'shoes') {
      assert.equal(sourceReview.kind, 'authorized-statement-translations');
      for (const language of ['JPN', 'PSE'])
        assert(sourceReview.evidenceUrls.includes(`https://ioi.te.lv/locations/ioi19/contest/day1/Shoes/${language}.pdf`));
    } else if (item.task === 'vision') {
      assert.equal(sourceReview.kind, 'national-committee-statement-distribution');
      assert(sourceReview.evidenceUrls.includes('https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2019-vision/statement/vision-en.pdf'));
      assert(sourceReview.evidenceUrls.includes('https://github.com/austrian-olympiad-informatics/ioi-tasks/blob/main/ioi2019-vision/grader/grader.cpp'));
    } else {
      assert.equal(sourceReview.kind, 'official-statement-public-mirror');
      assert.equal(sourceReview.statementUrl, 'https://jonathanirvin.gs/files/ioi2019/split-ISC.pdf');
      assert.equal(sourceReview.originalEnglishStatementUrl, item.statementUrl);
      assert.deepEqual(sourceReview.originalConstraints.n, { minimum: 3, maximum: 100000 });
      assert.deepEqual(sourceReview.originalConstraints.m, { minimum: 2, maximum: 200000 });
      assert.deepEqual(sourceReview.originalConstraints.a_b_c, { minimum: 1, maximum: 'n' });
      assert.equal(sourceReview.originalConstraints.sizeSum, 'a+b+c=n');
      assert.equal(sourceReview.originalConstraints.connected, true);
      assert.equal(sourceReview.originalConstraints.undirected, true);
      assert.equal(sourceReview.originalConstraints.selfLoops, false);
      assert.equal(sourceReview.originalConstraints.parallelEdges, false);
      assert(sourceReview.apiContainmentProof.length >= 4);
    }
  }
});
