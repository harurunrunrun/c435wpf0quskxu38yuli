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
  { id: 'monotone-paint-stroke-links-offline-containment', problemId: '1116', source: 'USACO',
    domain: 'ranges', prefix: ['aggregate-goals', 'static', 'paint-strokes'],
    parent: 'range-static', parentNode: 'kind', graph: 'monotone-paint-stroke-conditions',
    guards: ['ordered-overwrite', 'isolated-range', 'offline-bounds'],
    feature: 'data/monotone-paint-range-problem-features.json', group: 'range-patterns',
    statement: 'https://usaco.org/index.php?page=viewproblem2&cpid=1116',
    editorial: 'https://usaco.org/current/data/sol_prob1_platinum_feb21.html',
    sourceDate: '2021-02', datePrecision: 'month', exactDate: false,
    terms: [/薄い|濃い/, /上書き|戻せ/, /一筆|連続区間/, /独立/, /未塗装|未着色/, /20万|200000/],
    parentLabel: '薄い色へ戻せない区間塗装で、指定区間の最小筆数を求める',
    premiseText: [
      ['連続区間を一色に塗れ、濃い色を薄い色で上書きできない設定ですか？', '色には薄い順の全順序があります。完成させたい色の列は固定されています。'],
      ['指定区間の外を未塗装に残し、中を仕上げる最小の筆数を求めますか？', '各質問は、全て未塗装の状態から独立に考えます。前の質問で塗った状態は引き継ぎません。'],
      ['列長・質問数は20万以下で、全質問を先読みできますか？', '各質問の区間は列の中にあります。完成色は質問の間で変わりません。'],
    ],
    articleTerms: [/range_monotone_paint_strokes/, /std::int64_t/, /total_links/, /prefix/],
    checker: 'scripts/check_monotone_paint_range_cpp.py',
    cppSha256: 'e04fe2fe44a59765e06690d592aab60cdcedeb817dca165bc62b1194d31b767c' },
  { id: 'grid-enclosing-higher-boundary-rectangle-candidates', problemId: 'ioi2019_rect', source: 'IOI',
    domain: 'geometry', prefix: ['rectangle-aggregates', 'higher-enclosed-rectangles'],
    parent: 'geometry-rectangle-aggregates', parentNode: 'geometry-task', graph: 'higher-boundary-rectangle-conditions',
    guards: ['strict-four-borders', 'static-internal-rectangles', 'bounds'],
    feature: 'data/higher-boundary-rectangle-problem-features.json', group: 'planar-patterns',
    statement: 'https://ioinformatics.org/files/ioi2019problem3.pdf',
    editorial: 'https://ioi.te.lv/locations/ioi19/contest/day1/Rect/review.pdf',
    sourceDate: '2019-08-06', exactDate: true,
    terms: [/格子|盤面/, /真に|厳密/, /四|4|左右|上下/, /固定/, /外周/, /2500/, /7000000|700万/],
    parentLabel: '各行・各列で、内部より外側が高い長方形を数える',
    premiseText: [
      ['各内部セルは、同じ行・列の外側四セルより真に低い必要がありますか？', '同じ高さでは条件を満たしません。外側の四隅は比較に含めません。'],
      ['固定された高さの格子で、外周に触れない長方形を重複なく数えますか？', '一マスだけの長方形も含め、条件を満たす異なる長方形の個数を求めます。'],
      ['縦横2500以内・高さ0〜700万で、全盤面をまとめて処理できますか？', '行数・列数はそれぞれ1以上です。各行の長さはそろっています。'],
    ],
    articleTerms: [/count_strictly_enclosed_rectangles/, /count_rectangles/, /radix_sort/, /pair_index/],
    checker: 'scripts/check_enclosed_rectangle_candidates_cpp.py',
    cppSha256: '69a053a27c5d26d392eda313d2cfded6fbaa150c4f4ad959850e05cb914dd5d2' },
];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === current.source.toLowerCase() && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// This compact fixture contains only old graph/node IDs and original answer
// IDs, derived from the independent pre-batch raw freeze (458 graphs/3619 nodes).
// The hash below fixes every complete old graph/node field after projection,
// including labels and ordering, while future added branches remain possible.
const oldShape = JSON.parse(gunzipSync(Buffer.from('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', 'base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-rect-notime-flow-'));
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
    const addedOptions = flow.getNodeOptions(parent.current).filter(option => option.id === current.prefix.at(-1));
    assert.deepEqual(addedOptions, [{id: current.prefix.at(-1), label: current.parentLabel}]);
    for (let index = 0; index < 3; ++index) {
      const result = walk(flow, [...current.prefix, ...Array(index).fill('yes')], current.domain);
      assert.equal(result.graph.id, current.graph);
      assert.equal(result.current.id, current.guards[index]);
      assert.equal(result.current.type, 'question');
      assert.deepEqual([result.current.title, result.current.explanation], current.premiseText[index]);
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
    const checker=await readFile(path.join(site,current.checker),'utf8');
    assert(checker.includes(current.id+'.mdx'));
    assert(checker.includes('re.findall') && checker.includes(current.articleTerms[0].source));
    const originals = refs.filter(row => row.techniqueId === current.id && matches(row, current));
    assert.equal(originals.length, 1);
    const ref = originals[0];
    assert.equal(ref.url, current.statement);
    assert.equal(ref.editorialUrl, current.editorial);
    assert.equal(ref.verification, 'independent-analysis');
    assert.equal(ref.sourceDate, current.sourceDate);
    if (current.datePrecision) assert.equal(ref.sourceDatePrecision,current.datePrecision);
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
    assert.equal(feature.publicationDate,current.sourceDate);
    assert.equal(feature.exactDateVerified,current.exactDate);
    if (current.datePrecision) assert.equal(feature.publicationDatePrecision,current.datePrecision);
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

test('all 512 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 514);
  const previous = walks.slice(0, 512);
  assert.equal(digest(previous), 'b555105d8da3158e218a2f29471b40c0a8d16cfc8535eb0cbfbe9e1a6c33b19e');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // either article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '95cebdddb145b0d24f5636602819a2a91d115d981cacc2edef1ab3788c5d547e');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), '101b66a429ad757b3b6db00187e32e7f6ff8c8b52ea302ec4600c2f2412c4851');
});

test('every field of all 458 old graphs and 3619 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), 'adb211743c632dca3474fb8a6c3c88bdbd7873e4d8a5c3dae43750f1d2c39313');
  assert.equal(oldShape.length, 458);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3619);
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
  assert.equal(digest(stable(projection)), '1404e962eea108b315dde649e5dde702c68ef554aa0b866ca01ba70e82962492');
});


// Schemas and hashes were generated solely from the four pre-registration raw
// files. Selecting these old keys preserves initial records and all preexisting
// later evidence; live later additions remain independently checked below.
const baselineAudits=JSON.parse(gunzipSync(Buffer.from('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','base64')));
const auditFiles={ioi:'data/corpus-audits/ioi-2019.json',usaco:'data/corpus-audits/usaco-2021-february-us-open-platinum.json'};
function historical(audit,baseline) {
  assert.deepEqual(audit.records.map(row=>row.problemId),baseline.rowKeys.map(([id])=>id));
  const keys=new Map(baseline.rowKeys);
  const out=Object.fromEntries(baseline.topKeys.map(key=>[key,audit[key]]));
  out.records=audit.records.map(row=>Object.fromEntries(keys.get(row.problemId).map(key=>{
    assert(Object.hasOwn(row,key),row.problemId+': every historical field remains');
    return [key,row[key]];
  })));
  assert.equal(digest(out),baseline.fullSha256);
  assert.equal(digest(audit.status),baseline.statusSha256);
  assert.equal(digest(audit.selection),baseline.selectionSha256);
  assert.equal(digest(audit.snapshot),baseline.snapshotSha256);
  return out;
}
async function registeredResolution(row,current,plan) {
  assert.equal(row.resolution.status,'verified');
  assert.deepEqual(row.resolution.techniqueIds,[current.id]);
  assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
  assert.match(row.resolution.reviewedAt,/^\d{4}-\d{2}-\d{2}$/);
  assert(row.resolution.notes.trim().length>0);
  const gap=plan.knownGaps.find(gap=>gap.id===row.gap.id);
  assert.equal(gap.state,'resolved');assert.equal(gap.problemId,current.problemId);
  assert.deepEqual(gap.techniqueIds,[current.id]);
  const record=await json('research/technique-verifications/'+current.id+'.json');
  assert.equal(record.cppSha256,current.cppSha256);
  assert.equal(record.sourceVerification.numericBoundsVerified,true);
  assert.equal(record.reference.sourceDate,current.sourceDate);
  assert.equal(record.reference.difficulty,null);
  assert.equal(record.reference.verification,'independent-analysis');
  return record;
}

test('USACO six initial rows/status/selection/snapshot stay fixed, with only NoTime resolution added',async()=>{
  const [audit,plan]=await Promise.all([json(auditFiles.usaco),json('data/coverage-plan.json')]);
  const baseline=baselineAudits['usaco-audit'];const initial=historical(audit,baseline);
  assert.equal(audit.snapshot.articleCount,488);assert.equal(audit.snapshot.flowGraphCount,455);assert.equal(audit.snapshot.walkCount,509);
  assert.equal(audit.snapshot.flowRawSha256,'8e65013cc25d38030aed330d1f08d812f25cedd7dc78e33990386e03f238d256');
  assert.equal(audit.snapshot.walkRawSha256,'6a2fbef69e87ea9ae44c8b19d281c46c478293cdee4c80897ee32e7b3ee3ce90');
  assert.equal(createHash('sha256').update(await readFile(path.join(site,'research/snapshots/usaco-2021-february-us-open-platinum-baseline.tar.gz'))).digest('hex'),'be645b2f3192848bd482d5034e8fe79eca2e637e730d8ac893a6d5e5501c3913');
  assert(initial.records.every(isCorpusSolutionReviewed));
  assert.equal(initial.status.solutionReviewedCount,6);assert.equal(initial.status.coveredCount,0);
  assert.equal(initial.status.fixedCorpusResearchComplete,true);assert.equal(initial.status.fixedCorpusCoverageComplete,false);assert.equal(initial.status.globalCoverageComplete,false);
  const current=cases[0],row=audit.records.find(row=>matches(row,current));
  const oldKeys=new Map(baseline.rowKeys).get(current.problemId);
  assert.deepEqual(Object.keys(row).filter(key=>!oldKeys.includes(key)).sort(),['resolution']);
  assert.equal(row.classification,'missing-technique');assert.equal(row.reviewStatus,'verified');
  const record=await registeredResolution(row,current,plan);
  assert.equal(record.sourceVerification.exactContestDayVerified,false);
  assert.equal(record.sourceVerification.datePrecision,'month');
  assert.equal(record.sourceVerification.sourceBounds.N,'1..200000');assert.equal(record.sourceVerification.sourceBounds.Q,'1..200000');
  assert.match(record.sourceVerification.sourceBounds.colors,/1\.\.N/);
  assert.equal(record.verification.normal.checks,2702609);assert.equal(record.verification.asanUbsan.checks,2702609);
  assert.deepEqual(record.proof.unconfirmedLemmas,[]);
});

test('IOI2019 initial unconfirmed Rect stays unchanged; only explicit positive review and resolution supply its new proof',async()=>{
  const [audit,plan]=await Promise.all([json(auditFiles.ioi),json('data/coverage-plan.json')]);
  const baseline=baselineAudits['ioi2019-audit'];historical(audit,baseline);
  assert.equal(audit.snapshot.articleCount,472);assert.equal(audit.snapshot.specificTechniqueCount,394);assert.equal(audit.snapshot.flowGraphCount,439);
  for(const kind of ['flow','technique']){
    const raw=gunzipSync(await readFile(path.join(site,audit.snapshot[kind+'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'),audit.snapshot[kind+'Sha256']);
  }
  assert.equal(audit.snapshot.flowSha256,'39a3d2089b8f5ac9e684092543ac49f5005555d3b6e8c0d4be3cdc2a9b1e0181');
  assert.equal(audit.snapshot.techniqueSha256,'d37e0dd7a9ba814ecc61f4c5ac2bc1165dfe3f61deaf689e3a7c92d0210e1d40');
  for(const id of ['ioi2019_shoes','ioi2019_split','ioi2019_vision'])assert.equal(digest(audit.records.find(row=>row.problemId===id)),baseline.rowHashes[id]);
  const current=cases[1],row=audit.records.find(row=>matches(row,current)),oldKeys=new Map(baseline.rowKeys).get(current.problemId);
  assert.deepEqual(Object.keys(row).filter(key=>!oldKeys.includes(key)).sort(),['resolution','subsequentSolutionReviews']);
  assert.equal(row.classification,'unconfirmed');assert.equal(row.reviewStatus,'unconfirmed');
  assert.equal(row.constraints.numericBoundsVerified,false);assert.equal(row.materialStatus.officialEditorialVerified,false);
  assert.equal(row.technicalFindings.fullImplementationValidated,false);assert(row.technicalFindings.unconfirmedDetails.length>0);
  assert.equal(audit.status.solutionReviewedCount,3);assert.equal(audit.status.coveredCount,0);assert.equal(audit.status.fixedCorpusResearchComplete,false);assert.equal(audit.status.globalCoverageComplete,false);
  assert(Array.isArray(row.subsequentSolutionReviews)&&row.subsequentSolutionReviews.length>=1);
  const review=row.subsequentSolutionReviews[0];
  assert.equal(review.statementUrl,current.statement);assert.equal(review.reviewStatus,'verified');assert.equal(review.verification,'independent-analysis');
  assert.equal(review.materialStatus.solution,'retrieved-and-reviewed');assert.equal(review.materialStatus.officialEditorialVerified,false);
  assert(review.evidenceUrls.includes(current.statement)&&review.evidenceUrls.includes(current.editorial));assert(review.notes.trim().length>0);
  assert.equal(isCorpusSolutionReviewed(row),true);
  const absent=structuredClone(row);delete absent.subsequentSolutionReviews;
  assert.equal(isCorpusSolutionReviewed(absent),false,'a resolution alone cannot promote an unconfirmed solution');
  assert.equal(row.resolution.sourceVerification.numericBoundsVerified,true);
  assert.equal(row.resolution.sourceVerification.date,'2019-08-06');
  const record=await registeredResolution(row,current,plan);
  assert.equal(record.sourceVerification.apiContainsEntireSourceRange,true);
  assert.equal(record.sourceVerification.editorialFullFormulaTranscriptionVerified,false);
  assert.equal(record.sourceVerification.sourceBounds.rows,'1..2500');assert.equal(record.sourceVerification.sourceBounds.columns,'1..2500');
  assert.equal(record.sourceVerification.sourceBounds.height,'0..7000000');
  assert.equal(record.verification.maximumRows,2500);assert.equal(record.verification.maximumColumns,2500);assert.equal(record.verification.checks,2884927);
  assert.equal(record.verification.asanUbsan.passed,true);assert.deepEqual(record.proof.unconfirmedLemmas,[]);
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


test('registration-stage live evidence yields USACO6/6 research and1/6 coverage; no-resolution stays0/6',async()=>{
  const {flow}=await implementation;
  const [plan,audit,techniques,references,walks]=await Promise.all([json('data/coverage-plan.json'),json(auditFiles.usaco),collections(/^techniques-.*\.json$/),collections(/^references-.*\.json$/),json('data/problem-walks.json')]);
  const data=coverageData(flow,techniques,references,walks),selection={...plan.corpora.find(row=>row.id===audit.corpusId),cutoff:plan.cutoff};
  const stage=historical(audit,baselineAudits['usaco-audit']);
  stage.records.find(row=>row.problemId==='1116').resolution=structuredClone(audit.records.find(row=>row.problemId==='1116').resolution);
  const result=assessCorpus(stage,data,selection);assert.deepEqual(result.errors,[]);
  assert.equal(result.totalProblems,6);assert.equal(result.reviewedProblems,6);assert.equal(result.coveredProblems,1);assert.equal(result.researchComplete,true);assert.equal(result.coverageComplete,false);
  const live=assessCorpus(audit,data,selection);assert.deepEqual(live.errors,[]);assert.equal(live.reviewedProblems,6);assert(live.coveredProblems>=1);
  delete stage.records.find(row=>row.problemId==='1116').resolution;
  const absent=assessCorpus(stage,data,selection);assert.equal(absent.reviewedProblems,6);assert.equal(absent.coveredProblems,0);assert.equal(absent.coverageComplete,false);
});

test('registration-stage IOI2019 is4/6 researched/covered; removing new positive proof cannot be rescued by the article',async()=>{
  const {flow}=await implementation;
  const [plan,audit,techniques,references,walks]=await Promise.all([json('data/coverage-plan.json'),json(auditFiles.ioi),collections(/^techniques-.*\.json$/),collections(/^references-.*\.json$/),json('data/problem-walks.json')]);
  const data=coverageData(flow,techniques,references,walks),selection={...plan.corpora.find(row=>row.id===audit.corpusId),cutoff:plan.cutoff};
  const stage=historical(audit,baselineAudits['ioi2019-audit']);
  const liveRect=audit.records.find(row=>row.problemId==='ioi2019_rect'),row=stage.records.find(row=>row.problemId==='ioi2019_rect');
  row.subsequentSolutionReviews=[structuredClone(liveRect.subsequentSolutionReviews[0])];row.resolution=structuredClone(liveRect.resolution);
  const result=assessCorpus(stage,data,selection);assert.deepEqual(result.errors,[]);assert.equal(result.totalProblems,6);assert.equal(result.reviewedProblems,4);assert.equal(result.coveredProblems,4);assert.equal(result.researchComplete,false);assert.equal(result.coverageComplete,false);
  const live=assessCorpus(audit,data,selection);assert.deepEqual(live.errors,[]);assert(live.reviewedProblems>=4);assert(live.coveredProblems>=4);
  delete row.subsequentSolutionReviews;
  const noProof=assessCorpus(stage,data,selection);assert.equal(noProof.reviewedProblems,3);assert.equal(noProof.coveredProblems,3);assert.equal(noProof.researchComplete,false);
  row.subsequentSolutionReviews=[structuredClone(liveRect.subsequentSolutionReviews[0])];delete row.resolution;
  const noResolution=assessCorpus(stage,data,selection);assert.equal(noResolution.reviewedProblems,4);assert.equal(noResolution.coveredProblems,3);
});
function coverageData(flow,techniques,references,walks){
  return {techniques,references,walks,preflightPassed:true,isWalkValid:(row,id)=>{
    const value=flow.walkFromRoot(row.choices,row.entryGraphId);
    return flow.getGraph(row.entryGraphId).entry===true && value.consumed===row.choices.length
      && value.current.type==='result' && candidates(value).includes(id)
      && JSON.stringify(value.steps.map(({graph,node,answer})=>({graph,node,answer})))===JSON.stringify(row.steps);
  }};
}
