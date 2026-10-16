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
  {
    "id": "skywalk-endpoint-sparse-shortest-path",
    "problemId": "ioi2019_walk",
    "source": "IOI",
    "domain": "graphs",
    "prefix": [
      "walk-goals",
      "distance",
      "many-connections",
      "skywalks"
    ],
    "parent": "shortest-shared-connection-goals",
    "parentNode": "movement",
    "graph": "skywalk-shortest-path-conditions",
    "guards": [
      "grounded-buildings",
      "endpoint-contacts",
      "bounds"
    ],
    "feature": "data/skywalk-shortest-path-problem-features.json",
    "group": "graph-extensions",
    "statement": "https://ioinformatics.org/files/ioi2019problem6.pdf",
    "editorial": "https://ioi.te.lv/locations/ioi19/contest/day2/Walk/review.pdf",
    "sourceDate": "2019-08-08",
    "exactDate": true,
    "parentLabel": "地面から伸びるビルと空中通路を伝う最短距離",
    "premiseText": [
      [
        "地面から伸びる鉛直ビルと水平通路の上だけを歩き、地上の横移動は禁止されていますか？",
        "通路の途中でも、そこまで届くビルとの交点で乗り換えられます。通路は正の高さにあり、両端のビルはその高さまで届きます。"
      ],
      [
        "通路同士は端点でだけ接し、指定二ビルの根元間の最短距離を求めますか？",
        "同じ高さの通路は内部で重なりません。始点・終点は中央のビルでもよく、到達できない場合も判定します。"
      ],
      [
        "ビル・通路は各10万以下で、座標と高さは10億以下ですか？",
        "ビルは一本以上あり、横位置は0以上で真に増加し、高さは正です。全ての線分と始点・終点が最初から分かり、距離は64ビット整数で扱います。"
      ]
    ],
    "checker": "scripts/check_skywalk_sparse_shortest_path_cpp.py",
    "cppSha256": "8623c4854f945e096e2b74d1f3fdcf0aa88da3543e9fe658b6ccec9d99595bd6"
  }
];
cases[0].terms = [/鉛直|ビル/, /水平|通路/, /端点/, /地上|地面/, /10万|100000/, /10億|1e9|10\^9/];
cases[0].articleTerms = [/skywalk_shortest_distance/, /build_validated/, /IndexedHeap/, /矩形/, /辞書式/];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === current.source.toLowerCase() && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// IDs/order fixture and full-field hashes come only from the pre-SkyWalk raw freeze.
const oldShape = JSON.parse(gunzipSync(Buffer.from('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','base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-skywalk-flow-'));
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
    assert(checker.includes('re.findall') && checker.includes('all_pairs'));
    assert(registered[0].sources.every(url=>article.includes(url)));
    const originals = refs.filter(row => row.techniqueId === current.id && matches(row, current));
    assert.equal(originals.length, 1);
    const ref = originals[0];
    assert.equal(ref.url, current.statement);
    assert.equal(ref.editorialUrl, current.editorial);
    assert.equal(ref.verification, 'independent-analysis');
    assert.equal(ref.sourceDate, current.sourceDate);

    assert.equal(ref.difficulty, null);
    assert.equal(ref.cutoffVerification, 'contest-before-cutoff');
    assert(ref.evidence.trim().length > 0);
    assert(!/ASan|checksum|checks|テスト件数/.test(ref.evidence), 'evidence describes applicability; tests belong in verificationNotes');
    assert.equal(features.length, 1);
    const feature = features[0];
    assert(matches(feature, current));
    assert.deepEqual(feature.techniqueIds, [current.id]);
    assert.equal(feature.url, current.statement);
    assert.equal(feature.evidenceUrl, current.editorial);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, 'independent-analysis');
    assert.equal(feature.publicationDate,current.sourceDate);
    assert.equal(feature.exactDateVerified,true);
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

test('all 516 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 517);
  const previous = walks.slice(0, 516);
  assert.equal(previous.filter(row => row.reviewStatus === 'verified').length, 512);
  assert.equal(digest(previous), 'afcc53795f0cf0bc64717a9a53a725f303503417c06378ce4371831d0d4d404b');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // either article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), 'c3b57e82bebae5dbcbf817f35bd450ddf7f507e96191cff01200de0232ddb306');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), '07a8539b8b65b4bcbe5d476e6a08bad6ca526dae6690f33e3773817e13c249e1');
});

test('every field of all 462 old graphs and 3643 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), 'e59786f6433caeb5c7b5e983a3bb0b6db2baeeb082083c69136b532db7708ee3');
  assert.equal(oldShape.length, 462);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3643);
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
      assert.deepEqual(Object.keys(node.answers).filter(answer => answers.includes(answer)), answers, 'all old answer-key order is preserved');
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
  assert.equal(digest(stable(projection)), '5c1514d0a76953a5e0913052c97a18bf0af270ccf1c4e6946ed6ab22ff41b661');
});



const baselineAudit = JSON.parse(gunzipSync(Buffer.from('H4sIAAAAAAAC/+1Xy27kNhD8F533wJf48C1AksUi2CSwnVwWRtBsNj2EZUmRKDvGYv89Lc14PDaSXHL0XGaobrLYVV168GtTh/Enepqbiy/NjDu6h99pmsvQNx8aHKZxmT8lHtZSO1pDSx1y5gEsqVRK31Uez9QR1v2auYdx3g1reCIGSDOP6IH6yrglF4TniRXqsiaxg3k+Zr6nXPqyjtbcXT889h8Z8ddpGIcZOo515b7UNfkAXUl7uBvebXg88PjSlKEoIcMfXAjxTGY2LBOu9Y/TEDu63zgxkYIFumuY77ZAgqftt9IJY+pvuzLvrg+Xa9l0z3R+m9ZiiFUYJgbZXx6zn8s0DdM+iENfaV4VGZfYPfPkiVdHCTZV3wiUylrf0tW1qEw8daJ5DzfXCUq/iTDRQ6HHq38W87lPvywVh/s9mzo9fZxg3G2McTcU3FDnSuPWqr9G7iWla8JdX/5c6NPWQcC6QHdJwBZ5m0Poh5537C6HpdIP/Qp8C+Oq4TaRMz+WPpX+dp19z8RXwV5KHrqDfY6h+rzBZxhHXndM7NkebPdwotfPQ93TWOJMvLCvV1vLTzV9m++WNXq5Qe7B50Osubn5cOKisSv17KKzi/6Xi/hpeDbRezLRiRH+yzGvTNKVns4meTcmedX7h7L/7Dp3//yeObxn/u1d8gjd3dko7+gxweebvHTd1Q5Ua5sLrk1D67UHQ04oyEYZ8D5rmYWUMTgbW5NTSypozOgpgaPUaim1Ns5oPJ6/jojBacFLBHqXJTo02jot0YakAmYfICUC7T14STY546xBkIYCWTQy6dNj4EuZ6KJV1MbUtlyXBZ1CQvQRZEvGiQhBCm+SDrElyraFJB35YIURRiKenCePmKBAqBTBKitiYILOs4ukUYGkaWVKTjsjHUYXgzRRAGTprOcikTXAwJjr7XM5PL5AahM85pwRDYuIxsQA4PhapmgURczCtLa1OuVW2pa5A8sUyFvhY1TrTdely+PN+gz89c1B9KKx4IksV2WjVo5AaArRC5YiBdIJo3dMALyWpFsrRGuJPP8apQOSELzT61PJRaO90GyGlK311CpKPqA2xvN/JhZJO8qMz9prxDYYQqHaHIzRBM45fwK5faJeNI7NpFCh1ortIGSWwCpLrSx6yfKalCI6q4JKcq0q55DBGwHsFeFFPEE8vNPYXlmwZ5ghtUGg1MJBAA/WxVaKyJ4wSgTpFDcSPVvNpiR5b7aFZ1pGN9++/Q1oJxi4qxAAAA==','base64')));
const auditFile='data/corpus-audits/ioi-2019.json';
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
    if (fixture.localPrefixes.includes(row)) {
      let previousState=state;
      for (let remaining=weight(previousState)+1;;--remaining) {
        assert(remaining>0);
        assert.equal(flow.getFlowDomainId(previousState),row.domain);
        assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(previousState)),previousState);
        if (!weight(previousState)) break;
        const back=flow.backFlowState(previousState);
        assert(weight(back)<weight(previousState));previousState=back;
      }
      assert.deepEqual(previousState,flow.initialState(row.domain));
    }
  }
});

test('Back preserves the full history of all404 completed historical share URLs', async () => {
  const {flow}=await implementation;
  const fixture=await json('tests/fixtures/flow-legacy-sharing.json');
  assert.equal(digest(fixture),'0c4fe53421b48c94c0975fa1fcfcd4fac6eaeef084fea773450aafad5a32f83e');
  assert.equal(fixture.completedWalks.length,404);
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



function coverageData(flow,techniques,references,walks){
  return {techniques,references,walks,preflightPassed:true,isWalkValid:(row,id)=>{
    const value=flow.walkFromRoot(row.choices,row.entryGraphId);
    return flow.getGraph(row.entryGraphId).entry===true && value.consumed===row.choices.length
      && value.current.type==='result' && candidates(value).includes(id)
      && JSON.stringify(value.steps.map(({graph,node,answer})=>({graph,node,answer})))===JSON.stringify(row.steps);
  }};
}



test('all six initial IOI2019 records, false flags and four prior resolutions remain historical facts',async()=>{
  const audit=await json(auditFile),old=historical(audit,baselineAudit);
  assert.equal(old.snapshot.articleCount,472);assert.equal(old.snapshot.flowGraphCount,439);
  assert.equal(old.status.solutionReviewedCount,3);assert.equal(old.status.coveredCount,0);
  assert.equal(old.status.numericBoundsVerifiedCount,0);
  assert.equal(old.status.fixedCorpusResearchComplete,false);assert.equal(old.status.fixedCorpusCoverageComplete,false);
  assert.equal(old.status.globalCoverageComplete,false);assert.equal(old.selection.fixedBeforeTechniqueSearch,true);
  assert.equal(Object.keys(baselineAudit.oldResolutionSha256).length,4);
  for(const [id,sha]of Object.entries(baselineAudit.oldResolutionSha256))
    assert.equal(digest(audit.records.find(row=>row.problemId===id).resolution),sha);
  const row=old.records.find(row=>row.problemId==='ioi2019_walk');
  assert.equal(digest(row),baselineAudit.walkRowSha256);
  assert.equal(row.reviewStatus,'unconfirmed');assert.equal(row.classification,'unconfirmed');
  assert.equal(row.constraints.numericBoundsVerified,false);
  assert.equal(row.technicalFindings.fullImplementationValidated,false);
  assert.equal(row.materialStatus.officialEditorialVerified,false);
  assert.equal(row.materialStatus.solution,'retrieved-partially-reviewed');
  assert.deepEqual(row.expectedTechniqueIds,[]);
  assert.deepEqual(row.choices,['walk-goals','distance','many-connections']);
  assert.equal(row.canonicalRouteEnd.graphId,'shortest-shared-connection-goals');
  assert.equal(row.canonicalRouteEnd.nodeId,'movement');
  assert(!row.canonicalRouteEnd.options.some(option=>option.id==='skywalks'));
  assert.deepEqual(row.canonicalRouteEnd.options,row.gap.currentOptions);
  const current=audit.records.find(row=>row.problemId==='ioi2019_walk');
  assert.deepEqual(Object.keys(current).filter(key=>!baselineAudit.rowKeys.find(([id])=>id==='ioi2019_walk')[1].includes(key)).sort(),['resolution','subsequentSolutionReviews']);
});

test('one later independent proof review and a concrete resolution record full source/API coverage',async()=>{
  const [audit,plan]=await Promise.all([json(auditFile),json('data/coverage-plan.json')]);
  const current=cases[0],row=audit.records.find(row=>matches(row,current));
  assert.equal(row.subsequentSolutionReviews.length,1);
  const review=row.subsequentSolutionReviews[0];
  assert.equal(review.reviewStatus,'verified');assert.equal(review.verification,'independent-analysis');
  assert.equal(review.collectionStatus,'statement-and-independent-analysis-verified');
  assert.equal(review.materialStatus.statement,'retrieved-and-reviewed');
  assert.equal(review.materialStatus.solution,'retrieved-and-reviewed');
  assert.equal(review.materialStatus.officialEditorialVerified,false);
  assert(review.evidenceUrls.includes(current.statement)&&review.evidenceUrls.includes(current.editorial));
  assert(review.notes.trim().length>0);assert.equal(isCorpusSolutionReviewed(row),true);
  assert.equal(row.resolution.status,'verified');assert.deepEqual(row.resolution.techniqueIds,[current.id]);
  assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
  const gap=plan.knownGaps.find(gap=>gap.id===row.gap.id);
  assert.equal(gap.state,'resolved');assert.equal(gap.problemId,current.problemId);
  assert.deepEqual(gap.techniqueIds,[current.id]);
  const record=await json('research/technique-verifications/'+current.id+'.json');
  assert.equal(record.cppSha256,current.cppSha256);assert.deepEqual(record.proof.unconfirmedLemmas,[]);
  const src=record.sourceVerification;
  assert.equal(src.numericBoundsVerified,true);assert.equal(src.apiContainsEntireSourceRange,true);
  assert.equal(src.fullOriginalContractVerified,true);assert.equal(src.originalAbsentPathNumericMarkerVerified,true);
  assert.equal(src.originalAbsentPathValue,-1);assert.deepEqual(src.unconfirmedOriginalNumericBounds,[]);
  assert.deepEqual(src.unconfirmedRequiredLemmas,[]);
  assert.equal(src.date,'2019-08-08');assert.equal(src.exactDateVerified,true);assert.equal(src.difficulty,null);
  assert.equal(src.officialEditorialRetrieved,true);assert.equal(src.officialEditorialVerified,false);
  assert.equal(src.sourceBounds.N,'1..100000');assert.equal(src.sourceBounds.M,'1..100000');
  assert.equal(src.sourceBounds.x,'0<=x[0]<...<x[N-1]<=1000000000');
  assert.equal(src.sourceBounds.h,'1..1000000000');
  assert.equal(src.sourceBounds['l/r'],'0<=l[j]<r[j]<N');
  assert.equal(src.sourceBounds.y,'1<=y[j]<=min(h[l[j]],h[r[j]])');
  assert.equal(src.sourceBounds['s/g'],'0<=s,g<N;s!=g');
  assert.equal(record.reference.sourceDate,current.sourceDate);assert.equal(record.reference.difficulty,null);
  assert.equal(record.reference.verification,'independent-analysis');
  assert.equal(record.verification.actualArticleFenceCompiled,true);
  assert.equal(record.verification.normal.cppSha256,current.cppSha256);
  assert.equal(record.verification.asanUbsan.cppSha256,current.cppSha256);
  assert.equal(record.verification.normal.checks,9280397);assert.equal(record.verification.asanUbsan.checks,9280397);
  assert.equal(record.verification.normal.checksum,'9377741248886004889');
  assert.equal(record.verification.asanUbsan.checksum,'9377741248886004889');
});

test('actual target evidence separates initial4/4, later research5/6 and article coverage5/6',async()=>{
  const {flow}=await implementation;
  const [plan,audit,techniques,references,walks]=await Promise.all([json('data/coverage-plan.json'),json(auditFile),collections(/^techniques-.*\.json$/),collections(/^references-.*\.json$/),json('data/problem-walks.json')]);
  const data=coverageData(flow,techniques,references,walks),selection={...plan.corpora.find(row=>row.id===audit.corpusId),cutoff:plan.cutoff};
  const stage=historical(audit,baselineAudit),current=cases[0];
  const row=stage.records.find(row=>matches(row,current)),liveRow=audit.records.find(row=>matches(row,current));
  function expect(value,research,coverage) {
    assert.deepEqual(value.errors,[]);assert.equal(value.totalProblems,6);
    assert.equal(value.reviewedProblems,research);assert.equal(value.coveredProblems,coverage);
    assert.equal(value.researchComplete,false);assert.equal(value.coverageComplete,false);
  }
  expect(assessCorpus(stage,data,selection),4,4);
  row.resolution=structuredClone(liveRow.resolution);
  expect(assessCorpus(stage,data,selection),4,4);
  row.subsequentSolutionReviews=structuredClone(liveRow.subsequentSolutionReviews);
  expect(assessCorpus(stage,data,selection),5,5);
  delete row.resolution;expect(assessCorpus(stage,data,selection),5,4);
  row.resolution=structuredClone(liveRow.resolution);
  const withoutWalk={...data,isWalkValid:(walk,id)=>id===current.id?false:data.isWalkValid(walk,id)};
  expect(assessCorpus(stage,withoutWalk,selection),5,4);
  const withoutRef={...data,references:references.filter(ref=>ref.techniqueId!==current.id)};
  expect(assessCorpus(stage,withoutRef,selection),5,4);
  const withoutArticle={...data,techniques:techniques.filter(technique=>technique.id!==current.id)};
  expect(assessCorpus(stage,withoutArticle,selection),5,4);
  const invalidReview=structuredClone(stage);invalidReview.records.find(row=>matches(row,current)).subsequentSolutionReviews[0].reviewStatus='unconfirmed';
  expect(assessCorpus(invalidReview,data,selection),4,4);
  const live=assessCorpus(audit,data,selection);assert.deepEqual(live.errors,[]);
  assert(live.reviewedProblems>=5&&live.coveredProblems>=5,'future valid resolutions are allowed');
});
