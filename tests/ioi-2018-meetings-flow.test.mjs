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
import { assessCorpus } from '../scripts/audit-coverage.mjs';

const site = fileURLToPath(new URL('../', import.meta.url));
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const cases = [
  { id: 'cartesian-prefix-meeting-cost-single-cross-envelope', problemId: 'ioi2018_meetings',
    domain: 'ranges', prefix: ['aggregate-goals', 'meeting-costs'],
    parent: 'range-aggregate-goals', parentNode: 'updates', graph: 'range-maximum-meeting-cost-conditions',
    parentLabel: '区間内で会場を選び、道中の最大高さの費用を最小にする',
    guards: ['fixed-positive-heights', 'interval-meeting-cost', 'offline-bounds'],
    guardTitles: ['固定された正の高さ列で、位置ごとに一人ずつ参加者がいますか？',
      '道中の最大高さを各人の費用とし、区間内の最適な会場を選びますか？',
      '列長・質問数は75万以下で、全質問を先読みできますか？'],
    guardExplanations: ['高さは変わらず、各参加者の費用を同じ重みで足します。',
      '道中には出発点と会場を含めます。質問区間の全員について費用を足し、その最小値を求めます。',
      '列長は1以上、高さは1以上10億以下です。各質問は列内の空でない閉区間で、答えは64bit整数で扱います。'],
    resultTitle: '最大位置で分け、区間の左端からの最適費用をまとめて持つ',
    feature: 'data/range-maximum-meeting-cost-problem-features.json', group: 'dp-patterns',
    statement: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-meetings.pdf',
    editorial: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-meetings-review.pdf',
    terms: [/固定/, /正の高さ/, /最大高さ/, /会場/, /75万/, /10億/, /先読み/, /64bit/],
    articleTerms: [/minimum_interval_meeting_costs/, /std::map/, /pieces\.extract/, /original_peak/],
    cppSha256: '7241cb7bc2c5a4f6786a342a8a78592f0ba37097f2b01894afc4790c5263f1b1' },
];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === 'ioi' && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// This compact fixture contains only old graph/node IDs and original answer
// IDs, derived from the independent pre-batch raw freeze (457 graphs/3613 nodes).
// The hash below fixes every complete old graph/node field after projection,
// including labels and ordering, while future added branches remain possible.
const oldShape = JSON.parse(gunzipSync(Buffer.from('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', 'base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-meetings-flow-'));
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
function walk(flow, choices, domain) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, choices.join('/') + ': consume every fixed answer');
  return value;
}
function enterRoutes(flow, state) {
  for (let limit = 0; flow.evaluateState(state).current.type === 'route'; ++limit) {
    assert(limit < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, choices, domain) {
  let state = flow.initialState(domain);
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
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: visible node`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the complete answer label is readable');
    }
    if (node.type === 'result') for (const technique of node.techniques ?? [])
      assert(svg.includes(`href="/flowchartcp/techniques/${technique}/"`));
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges);
  return svg;
}


let html;
const svgCache = new Map();
for (const current of cases) {
  test(current.problemId + ': all premises gate the sole concrete result and no/unknown stays unresolved', async () => {
    const { flow } = await implementation;
    assert.deepEqual(flow.validateGraphs(), []);
    assert.equal(flow.getGraph(current.domain).entry, true);
    assert.equal(flow.getFlowDomainId(flow.initialState(current.graph)), current.domain);
    const parent = walk(flow, current.prefix.slice(0, -1), current.domain);
    assert.equal(parent.graph.id, current.parent);
    assert.equal(parent.current.id, current.parentNode);
    assert.equal(flow.getNodeOptions(parent.current).filter(option => option.id === current.prefix.at(-1)).length, 1);
    assert.equal(flow.getNodeOptions(parent.current).find(option => option.id === current.prefix.at(-1)).label, current.parentLabel);
    for (let index = 0; index < 3; ++index) {
      const result = walk(flow, [...current.prefix, ...Array(index).fill('yes')], current.domain);
      assert.equal(result.graph.id, current.graph);
      assert.equal(result.current.id, current.guards[index]);
      assert.equal(result.current.title, current.guardTitles[index]);
      assert.equal(result.current.explanation, current.guardExplanations[index]);
      assert.equal(result.current.type, 'question');
      assert.notEqual(result.graph.entry, true);
      assert(!candidates(result).includes(current.id));
      assert.deepEqual(flow.getNodeOptions(result.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const answer of ['no', 'unknown']) {
        const fallback = walk(flow, [...current.prefix, ...Array(index).fill('yes'), answer], current.domain);
        assert.equal(fallback.graph.id, 'condition-check');
        assert.equal(fallback.current.type, 'question');
        assert(!candidates(fallback).includes(current.id));
      }
    }
    const result = walk(flow, [...current.prefix, 'yes', 'yes', 'yes'], current.domain);
    assert.equal(result.current.type, 'result');
    assert.deepEqual(candidates(result), [current.id]);
    assert.equal(result.current.title, current.resultTitle);
    for (const term of current.terms) assert.match(JSON.stringify(result.graph), term);
    const occurrences = flow.graphs.flatMap(graph => graph.nodes.filter(node => (node.techniques ?? []).includes(current.id))
      .map(node => ({ graph: graph.id, node: node.id, type: node.type })));
    assert.deepEqual(occurrences, [{ graph: current.graph, node: 'result', type: 'result' }],
      'new techniques occur only inside their premise graph result');
  });

  test(current.problemId + ': both displays, complete SVG labels, shared URLs and Back retain all premise histories', async () => {
    const { flow, viewer } = await implementation;
    html ??= flow.renderFlowHtml('/flowchartcp/');
    assert(html.includes('data-view="questions"') && html.includes('data-view="diagram"'));
    for (const graphId of [current.domain, current.parent, current.graph]) {
      const graph = flow.getGraph(graphId);
      assert(html.includes(`data-graph-panel="${graphId}"`));
      if (!svgCache.has(graphId)) svgCache.set(graphId, checkSvg(flow, graph));
      for (const node of graph.nodes) {
        assert(html.includes(`id="flow-text-${graphId}-${node.id}"`));
        assert(html.includes(xml(node.title)));
        if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
          assert(html.includes(xml(option.label)));
          assert(html.includes(`#flow-text-${graphId}-${node.answers[option.id]}`));
        }
      }
    }
    assert(html.includes(`/flowchartcp/techniques/${current.id}/`));
    const histories = [[...current.prefix, 'yes', 'yes', 'yes']];
    for (let index = 0; index < 3; ++index) for (const answer of ['no', 'unknown'])
      histories.push([...current.prefix, ...Array(index).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, choices, current.domain);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices, current.domain).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0);
        assert.equal(flow.getFlowDomainId(state), current.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluated = flow.evaluateState(state);
        if (!svgCache.has(state.graph)) svgCache.set(state.graph, checkSvg(flow, evaluated.graph));
        const svg = svgCache.get(state.graph);
        for (const node of evaluated.path) assert(svg.includes(`data-node="${node.id}"`));
        for (const edge of evaluated.edges) assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
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
      assert.deepEqual(state, flow.initialState(current.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  });

  test(current.problemId + ': dated original, complete article, grouped metadata and one canonical example agree', async () => {
    const { flow } = await implementation;
    const [metadata, refs, features, walks] = await Promise.all([
      collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/), json(current.feature), json('data/problem-walks.json'),
    ]);
    const registered = metadata.filter(row => row.id === current.id);
    assert.equal(registered.length, 1);
    assert.equal(registered[0].kind, 'technique');
    assert.equal(registered[0].status, 'reviewed');
    assert(registered[0].aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert((await json('data/techniques-specific-' + current.group + '.json')).some(row => row.id === current.id));
    assert((await json('data/references-specific-' + current.group + '.json')).some(row => row.techniqueId === current.id && matches(row, current)));
    assert(registered[0].sources.includes(current.statement));
    assert(registered[0].sources.includes(current.editorial));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', current.id + '.mdx'), 'utf8');
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
      ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
    const cpp = [...article.matchAll(/^```cpp\s*\n(.*?)^```\s*$/gms)][0][1];
    assert.equal(createHash('sha256').update(cpp).digest('hex'), current.cppSha256);
    assert(!/<(?:details|summary)\b/i.test(article));
    for (const term of current.articleTerms) assert.match(article, term);
    assert(article.includes(current.statement) && article.includes(current.editorial));
    assert(article.includes(`techniqueId="${current.id}"`));
    const originals = refs.filter(row => row.techniqueId === current.id && matches(row, current));
    assert.equal(originals.length, 1);
    const ref = originals[0];
    assert.equal(ref.url, current.statement);
    assert.equal(ref.editorialUrl, current.editorial);
    assert.equal(ref.verification, 'independent-analysis');
    assert.equal(ref.sourceDate, '2018-09-05');
    assert.equal(ref.difficulty, null);
    assert.equal(ref.cutoffVerification, 'contest-before-cutoff');
    assert(ref.evidence.trim().length > 0);
    assert.equal(features.length, 1);
    const feature = features[0];
    assert(matches(feature, current));
    assert.deepEqual(feature.techniqueIds, [current.id]);
    assert.equal(feature.url, current.statement);
    assert.equal(feature.evidenceUrl, current.editorial);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, 'independent-analysis');
    assert.equal(feature.publicationDate, '2018-09-05');
    assert.equal(feature.exactDateVerified, true);
    assert.equal(feature.originalNumericBoundsVerified, true);
    assert.equal(feature.difficulty, null);
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, current) && row.expectedTechniqueIds.includes(current.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, current.domain);
    assert.deepEqual(example.choices, [...current.prefix, 'yes', 'yes', 'yes']);
    assert.deepEqual(example.expectedTechniqueIds, [current.id]);
    assert.equal(example.statementUrl, current.statement);
    assert.equal(example.verificationKind, 'independent-analysis');
    assert.equal(example.reviewStatus, 'verified');
    assert.deepEqual(example.features, feature.features);
    const reached = walk(flow, example.choices, current.domain);
    assert.deepEqual(reached.steps.map(({graph,node,answer}) => ({graph,node,answer})), example.steps);
  });
}

test('all 511 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 512);
  const previous = walks.slice(0, 511);
  assert.equal(digest(previous), 'b655b1c53e7a887f8e1f05eed7f3159b1a688bbba58e01f10fae1170a572e876');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // this article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'b116eafafe167ae81889255f78923e60982f4c019fcb765bb87707e6a4a01e8d');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), 'b1cdbb5eaa6f42dc9c88dcbf77fa1c0be752e18546e1e3de710dbed967a7aa46');
});

test('every field of all 457 old graphs and 3613 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), 'f680446b546527b661d85554247468a7c13289285b4efdd74b02895deb563f71');
  assert.equal(oldShape.length, 457);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3613);
  const shapeMap = new Map(oldShape);
  const oldIds = oldShape.map(([id]) => id);
  const projection = structuredClone(flow.graphs.filter(graph => shapeMap.has(graph.id)));
  assert.deepEqual(projection.map(graph => graph.id), oldIds);
  for (const graph of projection) {
    const shape = new Map(shapeMap.get(graph.id).map(([id,answers,explicitOptions]) => [id,{answers,explicitOptions}]));
    const nodeIds = shapeMap.get(graph.id).map(([id]) => id);
    graph.nodes = graph.nodes.filter(node => shape.has(node.id));
    assert.deepEqual(graph.nodes.map(node => node.id), nodeIds);
    for (const node of graph.nodes) {
      const { answers, explicitOptions } = shape.get(node.id);
      if (!answers) continue;
      assert.equal(node.type, 'question');
      for (const answer of answers) assert(Object.hasOwn(node.answers, answer));
      if (explicitOptions) {
        assert(Array.isArray(node.options));
        node.options = node.options.filter(option => answers.includes(option.id));
      } else if (node.options !== undefined) {
        assert.deepEqual(node.options.filter(option => answers.includes(option.id)),
          answers.map(id => ({id,label:({yes:'はい',no:'いいえ',unknown:'わからない'})[id] ?? id})));
        delete node.options;
      }
      node.answers = Object.fromEntries(answers.map(answer => [answer,node.answers[answer]]));
    }
  }
  assert.equal(digest(stable(projection)), '7278f313e2501a084e5f1ca55a62a88d80504b0c1d92b457650bec2f19fffa5c');
});

test('initial IOI2018 six rows/status/snapshot and all five existing resolutions stay fixed while only Meetings resolution is appended', async () => {
  const [audit,plan] = await Promise.all([json('data/corpus-audits/ioi-2018.json'),json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.articleCount, 482);
  assert.equal(audit.snapshot.specificTechniqueCount, 404);
  assert.equal(audit.snapshot.flowGraphCount, 449);
  assert.equal(audit.snapshot.walkCount, 503);
  for (const [kind,hash] of Object.entries({ flow:'51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e',
    technique:'74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be' })) {
    const raw=gunzipSync(await readFile(path.join(site,audit.snapshot[kind+'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'),hash);
    assert.equal(audit.snapshot[kind+'Sha256'],hash);
  }
  assert.equal(digest(audit.status),'8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3');
  assert.equal(digest(audit.selection),'1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b');
  const initial=audit.records.map(({resolution,...row})=>row);
  assert.equal(digest(audit.snapshot),'e9a05e628b56d537044c17819d94a724c69346e8f43755451286d3fddd188ce8');
  assert.equal(digest({...audit,records:initial}),'f5e76547307cc473c8be103d7bbe7badd9c362fdf3b5b25e6e4ae6200768e4cf');
  assert.equal(digest(initial),'ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523');
  assert(initial.every(isCorpusSolutionReviewed));
  assert.equal(audit.status.solutionReviewedCount,6);
  assert.equal(audit.status.coveredCount,0);
  assert.equal(audit.status.fullImplementationValidatedCount,0);
  assert.equal(audit.status.fixedCorpusResearchComplete,true);
  assert.equal(audit.status.fixedCorpusCoverageComplete,false);
  assert.equal(audit.status.globalCoverageComplete,false);
  for (const [problemId,hash] of Object.entries({"ioi2018_combo":"b95a8da558f4c0bae5119cf7ddc425d61a331bfd0c41140ae545143dbccd43b1","ioi2018_seats":"b3a80c33e0994f177dbc985b9e7b84e747ac594bab2526012ea543236d190a19","ioi2018_werewolf":"11fe9b7f4ac8041b0c12cd7fc2aee1735b81206790dd55e8a5ac06d5d19ec4e7","ioi2018_doll":"0c2f63b0087f0c9d099d154ba44aa6bd7b0284bb8d020ef0a71c044aa04cb34a","ioi2018_highway":"9398cf68cfd7e2031e21ae1a9b4bb2ab8804508618684df81588fa60a5b05384"}))
    assert.equal(digest(audit.records.find(row=>row.problemId===problemId)),hash);
  const corpus=plan.corpora.find(row=>row.id==='ioi-2018');
  assert.equal(corpus.expectedProblems,6);
  assert.equal(corpus.state,'audited');
  assert.deepEqual(corpus.fixedProblems.map(row=>row.problemId),initial.map(row=>row.problemId));
  for (const current of cases) {
    const row=audit.records.find(row=>matches(row,current));
    const first=initial.find(row=>matches(row,current));
    assert.equal(first.classification,'missing-technique');
    assert.equal(first.technicalFindings.fullImplementationValidated,false);
    assert.deepEqual(first.expectedTechniqueIds,[]);
    assert.equal(row.resolution.status,'verified');
    assert.deepEqual(row.resolution.techniqueIds,[current.id]);
    assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
    assert.match(row.resolution.reviewedAt,/^\d{4}-\d{2}-\d{2}$/);
    assert(row.resolution.notes.trim().length>0);
    const gap=plan.knownGaps.find(gap=>gap.id===first.gap.id);
    assert.equal(gap.state,'resolved');
    assert.equal(gap.problemId,current.problemId);
    assert.deepEqual(gap.techniqueIds,[current.id]);
    const record=await json('research/technique-verifications/'+current.id+'.json');
    assert.equal(record.sourceVerification.numericBoundsVerified,true);
    assert.equal(record.cppSha256,current.cppSha256);
    assert.equal(record.reference.verification,'independent-analysis');
    assert.equal(record.sourceVerification.date,'2018-09-05');
    assert.equal(record.sourceVerification.apiContainsEntireSourceRange,true);
    assert.equal(record.sourceVerification.editorialFullFormulaTranscriptionVerified,false);
    assert.deepEqual(record.sourceVerification.unconfirmedIndependentLemmas,[]);
    assert.equal(record.sourceVerification.sourceBounds.N,'1..750000');
    assert.equal(record.sourceVerification.sourceBounds.Q,'1..750000');
    assert.equal(record.sourceVerification.sourceBounds.H,'1..1000000000');
    assert.match(record.sourceVerification.sourceBounds.queries,/all endpoint pairs distinct/);
    assert.match(record.sourceVerification.sourceBounds.costBound,/750000000000000/);
    assert.equal(record.verification.maximumN,750000);
    assert.equal(record.verification.maximumQPerCase,750000);
    assert.equal(record.verification.maximumOriginalDistinctQueryPairs,true);
    assert.equal(record.verification.maximumCostAttained,750000000000000);
    assert.equal(record.verification.checks,10223222);
    assert.equal(record.verification.asanUbsan.passed,true);
    assert.deepEqual(record.proof.unconfirmedLemmas,[]);
    const checker=await readFile(path.join(site,'scripts/check_cartesian_meeting_cost_cpp.py'),'utf8');
    assert(checker.includes(current.id+'.mdx'));
    assert(checker.includes('re.findall') && checker.includes('minimum_interval_meeting_costs'));
    assert.equal(record.reference.difficulty,null);
    assert.equal(record.reference.sourceDate,'2018-09-05');
  }
  const firstMeeting=initial.find(row=>row.problemId==='ioi2018_meetings');
  assert.equal(firstMeeting.gap.firstMissingGraphId,'range-static-aggregate-forms');
  assert.equal(firstMeeting.gap.firstMissingNodeId,'kind');
  assert.deepEqual(firstMeeting.choices,['aggregate-goals','static','aggregate-forms']);
});


test('all historical local and completed shared URLs retain their candidates, domains and Back histories', async () => {
  const {flow,viewer}=await implementation;
  const fixture=await json('tests/fixtures/flow-legacy-sharing.json');
  assert.equal(digest(fixture),'0c4fe53421b48c94c0975fa1fcfcd4fac6eaeef084fea773450aafad5a32f83e');
  assert.equal(fixture.localPrefixes.length,593);
  assert.equal(fixture.completedWalks.length,404);
  for (const row of [...fixture.localPrefixes,...fixture.completedWalks]) {
    const state=flow.parseFlowHash(row.hash);
    const node=flow.evaluateState(state).current;
    assert.equal(node.id,row.expected.id);
    assert.equal(node.type,row.expected.type);
    assert.deepEqual(node.techniques??[],row.expected.techniques);
    if (row.expected.routeGraph) assert.equal(node.graph,row.expected.routeGraph);
    assert.equal(flow.getFlowDomainId(state),row.domain);
    assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)),state);
    assert.deepEqual(viewer.diagramState(state.graph,flow.serializeFlowHash(state)),state);
  }
  for (const row of fixture.completedWalks) {
    let state=flow.parseFlowHash(new URL(row.url).hash);
    for (let remaining=weight(state)+1;;--remaining) {
      assert(remaining>0);
      assert.equal(flow.getFlowDomainId(state),row.domain);
      assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)),state);
      if (!weight(state)) break;
      const previous=flow.backFlowState(state);
      assert(weight(previous)<weight(state));
      state=previous;
    }
    assert.deepEqual(state,flow.initialState(row.domain));
  }
});

test('current IOI2018 research and article coverage are6/6 without changing historical covered0/6', async () => {
  const {flow}=await implementation;
  const [audit,plan,techniques,references,walks]=await Promise.all([
    json('data/corpus-audits/ioi-2018.json'),json('data/coverage-plan.json'),
    collections(/^techniques-.*\.json$/),collections(/^references-.*\.json$/),json('data/problem-walks.json'),
  ]);
  const selection={...plan.corpora.find(row=>row.id==='ioi-2018'),cutoff:plan.cutoff};
  const data={techniques,references,walks,preflightPassed:true,isWalkValid:(row,id)=>{
    const value=flow.walkFromRoot(row.choices,row.entryGraphId);
    return flow.getGraph(row.entryGraphId).entry===true && value.consumed===row.choices.length
      && value.current.type==='result' && candidates(value).includes(id)
      && JSON.stringify(value.steps.map(({graph,node,answer})=>({graph,node,answer})))===JSON.stringify(row.steps);
  }};
  const current=assessCorpus(audit,data,selection);
  assert.deepEqual(current.errors,[]);
  assert.equal(current.totalProblems,6);
  assert.equal(current.reviewedProblems,6);
  assert.equal(current.coveredProblems,6);
  assert.equal(current.researchComplete,true);
  assert.equal(current.coverageComplete,true);
  assert(current.records.every(row=>row.resolved && row.currentClassification==='covered'));
  assert.equal(audit.status.coveredCount,0);
  assert.equal(audit.status.globalCoverageComplete,false);
  for (const row of audit.records) {
    assert.equal(row.classification,'missing-technique');
    assert.equal(row.resolution.status,'verified');
    const gap=plan.knownGaps.find(gap=>gap.id===row.gap.id);
    assert.equal(gap.state,'resolved');
    assert.deepEqual(gap.techniqueIds,row.resolution.techniqueIds);
  }
  const previous=structuredClone(audit);
  delete previous.records.find(row=>row.problemId==='ioi2018_meetings').resolution;
  const pending=assessCorpus(previous,data,selection);
  assert.equal(pending.reviewedProblems,6);
  assert.equal(pending.researchComplete,true);
  assert.equal(pending.coveredProblems,5);
  assert.equal(pending.coverageComplete,false,'research and registered article coverage are separate stages');
});
