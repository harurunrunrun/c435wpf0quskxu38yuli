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
    "id": "parity-walk-profile-layer-greedy-realization",
    "problemId": "1117",
    "source": "USACO",
    "domain": "graphs",
    "prefix": [
      "network-connection",
      "walk-language-minimize"
    ],
    "parent": "graphs-network-connection",
    "parentNode": "shortest",
    "graph": "parity-walk-minimum-conditions",
    "guards": [
      "undirected-connected",
      "all-walk-lengths",
      "bounds"
    ],
    "feature": "data/parity-walk-minimum-problem-features.json",
    "group": "graph-extensions",
    "statement": "https://usaco.org/index.php?page=viewproblem2&cpid=1117",
    "editorial": "https://usaco.org/current/data/sol_prob2_platinum_feb21.html",
    "sourceDate": "2021-02",
    "datePrecision": "month",
    "exactDate": false,
    "parentLabel": "始点から到達できる全歩数を保ち、辺数を最小にする",
    "premiseText": [
      [
        "辺は無向で一歩に数え、自己ループを使える連結グラフですか？",
        "同じ頂点対を結ぶ辺は一本までです。各頂点は固定した始点から到達できます。"
      ],
      [
        "各頂点へ到達できる全歩数を保つ、最小の辺数を求めますか？",
        "始点と頂点のラベルを固定します。頂点や辺を繰り返し通れ、元にない辺も使えます。"
      ],
      [
        "頂点数は2〜10万、辺数は20万以下で、全ての辺が分かっていますか？",
        "二つの偶奇それぞれの最短歩数を求め、同じ距離の組をまとめられる入力です。"
      ]
    ],
    "checker": "scripts/check_parity_walk_minimum_cpp.py",
    "cppSha256": "1a04200fd167167a77a09ff5d98ca3a5354e6538025e2e36e41158636317693e"
  },
  {
    "id": "interval-unique-endpoints-singleton-middle-active-lazy",
    "problemId": "1140",
    "source": "USACO",
    "domain": "ranges",
    "prefix": [
      "aggregate-goals",
      "window",
      "unique-leader-triples"
    ],
    "parent": "range-window",
    "parentNode": "wanted",
    "graph": "interval-unique-leader-conditions",
    "guards": [
      "three-singleton-leaders",
      "all-fixed-intervals",
      "bounds"
    ],
    "feature": "data/interval-unique-leader-problem-features.json",
    "group": "range-patterns",
    "statement": "https://usaco.org/index.php?page=viewproblem2&cpid=1140",
    "editorial": "https://usaco.org/current/data/sol_prob1_platinum_open21.html",
    "sourceDate": "2021",
    "datePrecision": "year",
    "exactDate": false,
    "parentLabel": "両端と内部の一点が、区間内で一度だけ現れる三点組を数える",
    "premiseText": [
      [
        "区間の両端と内部の一点を選び、各値が区間全体で一度だけ現れる必要がありますか？",
        "選ばなかった位置も含めて出現回数を調べます。選ばない値が何度も現れても構いません。"
      ],
      [
        "固定された列について、全区間と内部の点の選び方の総数を求めますか？",
        "区間の端や内部の選択位置が違えば、別の選び方として数えます。"
      ],
      [
        "列長は20万以下で、O(N log N)時間・O(N)空間を使えますか？",
        "値は符号付き64ビット整数で表し、等しいかどうかだけを使います。答えにも64ビット整数を使います。"
      ]
    ],
    "checker": "scripts/check_interval_unique_leaders_cpp.py",
    "cppSha256": "407284b9682e4d15c74625be2294fe2234c79b8e7f6e4671366a8af92c4b6fcf"
  }
];
cases[0].terms = [/自己ループ/, /多重辺|重複/, /再訪|繰り返/, /全.*歩数|歩数.*全/, /10万|100000/, /20万|200000/];
cases[0].articleTerms = [/minimum_edges_preserving_root_walk_lengths/, /incoming/, /infinity/, /二部/];
cases[1].terms = [/両端/, /内部|内側/, /一度|1回/, /全区間|区間全体/, /固定/, /20万|200000/];
cases[1].articleTerms = [/count_interval_unique_leader_triples/, /second_last/, /replace/, /std::int64_t/];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === current.source.toLowerCase() && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// This compact fixture contains only old graph/node IDs and original answer
// IDs, derived from the independent pre-batch raw freeze (460 graphs/3631 nodes).
// The hash below fixes every complete old graph/node field after projection,
// including labels and ordering, while future added branches remain possible.
const oldShape = JSON.parse(gunzipSync(Buffer.from('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', 'base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-minedges-unitedcows-flow-'));
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
    assert.equal(current.problemId === '1117' ? ref.datePrecision : ref.sourceDatePrecision,current.datePrecision);
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
    if (current.problemId === '1117') {
      assert.equal(feature.publicationYearMonth, '2021-02');
      assert(!Object.hasOwn(feature, 'publicationDate'), 'unconfirmed day is not synthesized');
    } else assert.equal(feature.publicationDate,current.sourceDate);
    assert.equal(feature.exactDateVerified,current.exactDate);
    if (current.problemId === '1140') assert.equal(feature.exactMonthVerified, false);
    if (current.problemId === '1140') assert.equal(feature.publicationDatePrecision,'year');
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

test('all 514 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 516);
  const previous = walks.slice(0, 514);
  assert.equal(previous.filter(row => row.reviewStatus === 'verified').length, 510);
  assert.equal(digest(previous), '5527b4663bacfc09f71b0e4211a60fc7bea75c958d268fc2bea0a2b869ba2b47');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // either article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '8e3193a3a81eb6deafdea197d446bac156af33b99391e95bdbac7a5976bb62cc');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), '3a16166244c3ef52309e21549df5a14e4228d11cdfe551e3139e8f3839fd3eef');
});

test('every field of all 460 old graphs and 3631 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), 'f54bd734ed1442a179ad4f3398ae291227b01f41c4dee1c62b2e5ff6e61b7449');
  assert.equal(oldShape.length, 460);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3631);
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
  assert.equal(digest(stable(projection)), 'af0dca4239094cbd5a4420331684095a5f7f5847e72e4a2c38c22525dbe35c2b');
});



const baselineAudit = JSON.parse(gunzipSync(Buffer.from('H4sIAAAAAAAAA+1Xy47cKhD9F69nYYwBk12Ux1V0dRNp8thEsyigmEaija+NOxlF+fcUdLdnJvMLXrk4UMd1DmfDryan6V98WJpX35vFHvAI33BeQhqbm8ameVqXD47KHHLEAq05eU8FrC5kdK8z1QtGtPncs4wwLYdU4Qx5XUpThGUJPlgoh96iD2MoVdk7QsY5QCz1CWJwcCGK4RhyQacZF5xPVxzmHDzYukV/uMc3aR1pdXfTzOnHRcr3hjEmmxvSlNbZYqVJJuLxmZoyIR5xzF/nSEskSakMc17aNGZcqpJK8pYOF6LVxKsUQj5vKqs15N6mlEAXPK3WmB9o4ZGOkpoz95JnCGPVMeMp4I+N6fSc47l9V+8/rdmmYxmI5p8f/plhOlRx9pCCxbM9OJVvtRviLQJdcD0CYxqJL96mNeO7sWD4c6JLRPcF7WEM/6/4wZVecnrdWv/au4epmFlBInsfRhfG+6e3+mhOipeMbFC+kv0H00R928bZjUu2ZoxQcka3biPe1i2CRziF++rHLU4RirvrSKb6MB+rxKcefky5+gGRphoJOmEVXumXFNfq693dTY2N2mOzx+YxNtdYDHss9li8iEXf7rHYY/EyFmyPxR6Ll7Ho9ljssXgaC3q1+DXGzwfohGxeNeiZRs4088YNygnT4sANKomcdwxMr1Hw3gyiA+6cHpQQVg3gGEcjXXnyXJ5dG6NWSnSu1c5xDbJFOdheKbS6YxJY56E1nP6hB9+pXhsUUvIe26EntOdQM3l93z2SypYNetBadkxQn2jBd7KjNmR8kLw1njvNjVNcO9156yUXwKH3WrFeFDeuD8WNszceHVrpDJOcxqODrWJW6156kuscKAUOsHN+8EYy0fYKnRCDAwOuteUK0pdwxI2RA8m1CiSTKLxRvhPW0kQKaVByGLvWEYt0bas8iK7rHaJ3gweDLTDf/P4DpMd3sx8PAAA=','base64')));
const auditFile='data/corpus-audits/usaco-2021-february-us-open-platinum.json';
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


test('the initial six USACO records and every NoTime resolution field survive without duplicate positive research reviews',async()=>{
  const audit=await json(auditFile), old=historical(audit,baselineAudit);
  assert.equal(old.snapshot.articleCount,488);assert.equal(old.snapshot.flowGraphCount,455);assert.equal(old.snapshot.walkCount,509);
  assert.equal(old.snapshot.flowRawSha256,'8e65013cc25d38030aed330d1f08d812f25cedd7dc78e33990386e03f238d256');
  assert.equal(old.snapshot.walkRawSha256,'6a2fbef69e87ea9ae44c8b19d281c46c478293cdee4c80897ee32e7b3ee3ce90');
  assert.equal(digest(audit.records.find(row=>row.problemId==='1116')),baselineAudit.noTimeSha256);
  assert(old.records.every(isCorpusSolutionReviewed));
  assert(old.records.every(row=>row.classification==='missing-technique'));
  assert.equal(old.status.solutionReviewedCount,6);assert.equal(old.status.coveredCount,0);
  assert.equal(old.status.completeProductionApiCount,0);assert.equal(old.status.fixedCorpusResearchComplete,true);
  assert.equal(old.status.fixedCorpusCoverageComplete,false);assert.equal(old.status.globalCoverageComplete,false);
  const keys=new Map(baselineAudit.rowKeys);
  for(const current of cases){
    const row=audit.records.find(row=>matches(row,current));
    assert.deepEqual(Object.keys(row).filter(key=>!keys.get(row.problemId).includes(key)),['resolution']);
    assert(!Object.hasOwn(row,'subsequentSolutionReviews'),'already verified research needs no duplicate positive review');
    assert.equal(row.technicalFindings.fullImplementationValidated,false);
    assert.deepEqual(row.expectedTechniqueIds,[]);
    assert.equal(row.classification,'missing-technique');
    assert.equal(row.reviewStatus,'verified');
  }
});

test('both new resolutions point to complete C++ evidence and canonical root walks with truthful source precision',async()=>{
  const [audit,plan]=await Promise.all([json(auditFile),json('data/coverage-plan.json')]);
  for(const current of cases){
    const row=audit.records.find(row=>matches(row,current));
    assert.equal(row.resolution.status,'verified');
    assert.deepEqual(row.resolution.techniqueIds,[current.id]);
    assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
    assert.match(row.resolution.reviewedAt,/^\d{4}-\d{2}-\d{2}$/);
    assert(row.resolution.notes.trim().length>0);
    const gap=plan.knownGaps.find(gap=>gap.id===row.gap.id);
    assert.equal(gap.state,'resolved');assert.equal(gap.problemId,current.problemId);
    assert.deepEqual(gap.techniqueIds,[current.id]);
    const record=await json('research/technique-verifications/'+current.id+'.json');
    assert.equal(record.cppSha256??record.verification.cppSha256,current.cppSha256);
    assert.equal(record.reference.sourceDate,current.sourceDate);
    assert.equal(record.reference.difficulty,null);
    assert.equal(record.reference.verification,'independent-analysis');
    assert.deepEqual(record.proof.unconfirmedLemmas,[]);
    if(current.problemId==='1117'){
      assert.equal(record.sourceVerification.apiContainsEntireSourceRange,true);
      assert.equal(record.sourceVerification.statementAndAllNumericBoundsVerified,true);
      assert.equal(record.sourceVerification.sourceDate,'2021-02');
      assert.equal(record.sourceVerification.datePrecision,'month');
      assert.equal(record.sourceVerification.exactDateVerified,false);
      assert.equal(record.verification.checks,292700);
      assert.equal(record.verification.checksum,'18056148866444260320');
      assert.equal(record.relatedWork.countingGraphsApiImplemented,false);
    }else{
      assert.equal(record.sourceVerification.numericBoundsVerified,true);
      assert.equal(record.sourceVerification.date,'2021');
      assert.equal(record.sourceVerification.datePrecision,'year');
      assert.equal(record.sourceVerification.exactDateVerified,false);
      assert.equal(record.sourceVerification.exactContestMonthVerified,false);
      assert.equal(record.verification.normal.checks,8876842);
      assert.equal(record.verification.asanUbsan.checks,8876842);
      assert.equal(record.verification.normal.checksum,'11233411103425697573');
      assert.equal(record.verification.asanUbsan.checksum,'11233411103425697573');
    }
  }
});

test('the registration-stage target evidence proves6/6 research and3/6 coverage; removing the new resolutions returns1/6',async()=>{
  const {flow}=await implementation;
  const [plan,audit,techniques,references,walks]=await Promise.all([json('data/coverage-plan.json'),json(auditFile),collections(/^techniques-.*\.json$/),collections(/^references-.*\.json$/),json('data/problem-walks.json')]);
  const data=coverageData(flow,techniques,references,walks),selection={...plan.corpora.find(row=>row.id===audit.corpusId),cutoff:plan.cutoff};
  const stage=historical(audit,baselineAudit);
  for(const current of cases)stage.records.find(row=>matches(row,current)).resolution=structuredClone(audit.records.find(row=>matches(row,current)).resolution);
  const result=assessCorpus(stage,data,selection);assert.deepEqual(result.errors,[]);
  assert.equal(result.totalProblems,6);assert.equal(result.reviewedProblems,6);assert.equal(result.coveredProblems,3);
  assert.equal(result.researchComplete,true);assert.equal(result.coverageComplete,false);
  const live=assessCorpus(audit,data,selection);assert.deepEqual(live.errors,[]);
  assert.equal(live.reviewedProblems,6);assert(live.coveredProblems>=3,'future valid article resolutions are allowed');
  for(const current of cases)delete stage.records.find(row=>matches(row,current)).resolution;
  const prior=assessCorpus(stage,data,selection);assert.deepEqual(prior.errors,[]);
  assert.equal(prior.reviewedProblems,6);assert.equal(prior.coveredProblems,1);assert.equal(prior.coverageComplete,false);
  const noEvidence={...data,isWalkValid:(row,id)=>cases.some(item=>item.id===id)?false:data.isWalkValid(row,id)};
  for(const current of cases)stage.records.find(row=>matches(row,current)).resolution=structuredClone(audit.records.find(row=>matches(row,current)).resolution);
  const withoutTargets=assessCorpus(stage,noEvidence,selection);
  assert.equal(withoutTargets.reviewedProblems,6);assert.equal(withoutTargets.coveredProblems,1,
    'articles and positive resolution fields cannot replace actual validated root-walk targets');
});
