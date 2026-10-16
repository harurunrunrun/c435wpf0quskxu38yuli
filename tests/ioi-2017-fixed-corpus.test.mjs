import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, readdir, mkdtemp, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const execute = promisify(execFile);

// The override is solely for a draft staged-site run. The installed test uses
// its own repository and has no dependency on the author's temporary files.
const root = process.env.FLOWCHARTCP_SITE_ROOT ?? fileURLToPath(new URL('../', import.meta.url));
const bytes = file => readFile(path.join(root, file));
const json = async file => JSON.parse(await bytes(file));
const sha = data => createHash('sha256').update(data).digest('hex');
const digest = value => sha(JSON.stringify(value));
const EXPECTED = {
  "initialAuditSha256": "112606343ee4912aac10132d0a0e0aea1c062635aa6642acb14a03396379f78e",
  "recordsSha256": "8e66e1ba9a559b0f3e879686cd281f961f0fefcd998e68c02ef24fc3a75cb2cb",
  "statusSha256": "e8a5099863b9c0057c4dd6a64e9d2f619477eb84521482b66e6b50a834fb0d73",
  "selectionSha256": "bb013c3e8c0bcd395c856d51dab383be26e82b8907d3e74a9ebce5f18b170d61",
  "manifestSha256": "b90b3af7a72cc9c6485662606109f1bea9ac4bb2eef8a643c9b46fd79514beae",
  "snapshotRawHashes": {
    "flow": "5e86b750545b089d2e1427c4a956287e6925f8d69cabae4a89cfa1e5a1bb0c38",
    "technique": "56432346cc04f996751bea2bbf5eabf702a34af24a23b98e3acdee954611b6e1",
    "walk": "4d0fd03bc210fd47f941af4ba336289d354a9012d9e3238f5b34b3a56b680adb",
    "reference": "76e8d8f01068c3d478906078b1ccc2a702f98e4f1b4668679cf423d7cb54eda5",
    "source": "c21f623232bc680f62603bc52fc6e5b7773930d68e234272494764369d6e8c2d",
    "retained-raw": "7a876603dce38e900529c69e94d0a1e229be9a7d79b7301628e7e8076daee252",
    "original-audit": "112606343ee4912aac10132d0a0e0aea1c062635aa6642acb14a03396379f78e",
    "original-probe": "18a76ae16bc2ab3ca68dfa3e74672acb57099a9ad6dbb78679735e387a906993",
    "original-notes": "096921befd3eec4a6e0c5751efe2e35037c32d6be86ed7b590ac034aa92e99a6"
  },
  "rowSha256": [
    "c2461c80c341ca1df61354d1a4f81ad257716459f2800b1e24364379b82c8730",
    "af3d259a8be217479114def539e28065190e1128f2e98d4b3fd779aacdcb276d",
    "9055f45bc2759b7cfa83a5dc1f0fce10eeddc6b3e7387be43a919c31804c1a22",
    "63966c3e096ba2e26adab6df0d1fa9188f54ba9fd87b0d69abf7fedabcc2fb55",
    "b7f3b659586190f013709244daa41a167f8503af17f6228448a3d0919b1616fa",
    "dc9c66dc58404071b4123599d6cb1528c9d3aebe29c0369728f67c7f494a6e0e"
  ],
  "originalManifestSha256": "a9e8a03f631af26f183e9c1839b76226f2857bd8d6b8ffb369285c4d7d40d8e0",
  "old8": {
    "data/corpus-audits/icpc-2017-world-finals.json": "f6e504a921e6c263f89b4443e459df1d6c81d43190bc3787a24ff89c590a13a2",
    "data/corpus-audits/icpc-2018-world-finals.json": "54314a33268feb8b20e15d864a6c100c663320db601a8bc3da2492af89fdae8d",
    "data/corpus-audits/ioi-2018.json": "0d9a04e7c024248cdc6a8be90394ca282e7cb7836c289f3524c0d5861b366eda",
    "data/corpus-audits/ioi-2019.json": "d3f75c60af792837d579c1ff14ec9fee73d243fae7204b69a4172129b41dbad5",
    "data/corpus-audits/ioi-2020.json": "237f84501b3a0928d3e47ab75eaa41842d392918921f4acbf86bbf7f48e77445",
    "data/corpus-audits/joi-2020-spring.json": "3957417c7a82cc15a85279713c30b154a0c04050b04a6782b9ef8a5733bde28d",
    "data/corpus-audits/usaco-2020-dec-2021-jan-platinum.json": "d4229180493cdabd1ab1280118b290fbe86f85da28cc6866a4ea57b62c76509d",
    "data/corpus-audits/usaco-2021-february-us-open-platinum.json": "9ddc7902e5ff96342923c08f5ca5c6f6acd890725ac58032019237f14fb4b913"
  },
  "normalizedProbeSha256": "9377be37621997f5c06c996cab3c1c6fc54b06da72bea58ea27fa50bbdf5eefa",
  "normalizedResultsSha256": "3aa1f44357dde8ef331b3df6a48a07e38f766858b03b7c6592e074c360123084"
};
const tasks = ['nowruz', 'wiring', 'train', 'prize', 'simurgh', 'books'];
const ids = tasks.map(t => 'ioi2017_' + t);
const positive = new Set(['wiring', 'train', 'simurgh', 'books']);
const needed = ['induced-grid-tree-single-neighbor-leaf-growth',
  'line-bipartite-edge-cover-monochromatic-block-prefix-dp',
  'buchi-owned-graph-repeated-target-attractor-elimination',
  'rank-count-oracle-equal-level-interval-pruning',
  'spanning-tree-overlap-oracle-reference-labeling-leaf-peeling',
  'permutation-cycle-interval-closure-two-sided-walk-greedy'];
const routes = [
  ['fixed-output', [], 'fixed-output', 'output-result'],
  ['flow-matching', ['quantity-goals','costs','yes'], 'assignment-quantity-goals', 'mincost'],
  ['game-probability', ['win','other','no'], 'game-general', 'fallback'],
  ['interactive-oracles', ['other'], 'interactive-oracles', 'general-result'],
  ['interactive-oracles', ['other'], 'interactive-oracles', 'general-result'],
  ['ranges', ['sequence-changes','reorder-cost'], 'range-sequence-changes', 'reorder-operation'],
];
const completed = [];
function check(name, body) { test(name, async () => { await body(); completed.push(name); }); }
after(async () => {
  if (process.env.FLOWCHARTCP_IOI2017_RESULTS) await writeFile(process.env.FLOWCHARTCP_IOI2017_RESULTS,
    JSON.stringify({ suite:'ioi-2017-fixed-corpus', caseCount:9, passed:completed.length,
      failed:9-completed.length, status:completed.length===9?'passed':'failed', cases:completed,
      fixedProblems:6, initialStatements:6, initialResearchSolutions:4, initialUnconfirmed:2,
      initialFullApis:0, initialCoverage:0, initialCoreRaw:921, laterDependencyRaw:571,
      initialArticles:498, initialGraphs:465, initialWalks:519, preservedOldCorpora:8,
      retainedOriginalRawFiles:32, retainedFullNearbyMdx:13,
      allHistoricalRawFilesPermanentlyStored:false, allHistoricalMdxPermanentlyStored:false }, null, 2)+'\n');
});
let cache;
async function evidence() {
  if (cache) return cache;
  const audit = await json('data/corpus-audits/ioi-2017.json');
  const manifestBytes = await bytes('research/snapshots/ioi-2017-manifest.json');
  assert.equal(sha(manifestBytes), EXPECTED.manifestSha256);
  const manifest = JSON.parse(manifestBytes), snapshots = {};
  for (const [kind, item] of Object.entries(manifest.retainedSnapshots)) {
    const raw = gunzipSync(await bytes(item.file));
    assert.equal(sha(raw), EXPECTED.snapshotRawHashes[kind]);
    assert.equal(sha(raw), item.rawSha256);
    assert.equal(raw.length, item.rawBytes);
    snapshots[kind] = raw;
  }
  const original = JSON.parse(snapshots['original-audit']);
  const bundle = JSON.parse(snapshots['retained-raw']);
  const rawFiles = new Map(bundle.files.map(f => [f.path, Buffer.from(f.rawBase64, 'base64')]));
  cache = { audit, manifest, snapshots, original, bundle, rawFiles };
  return cache;
}
const projection = (current, original) => Object.fromEntries(Object.keys(original).map(key => [key,current[key]]));
const options = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id,
  label:({yes:'はい',no:'いいえ',unknown:'わからない'})[id] ?? id }));
// Separate from both the Python probe and the product walker. Only frozen raw
// questions/answers determine the historical stop; current flows never do.
function replay(graphs, row) {
  let graph = graphs.get(row.entryGraphId), node = graph?.nodes.find(n=>n.id===graph.root);
  assert.equal(graph?.entry,true); let used=0; const steps=[], transitions=[], seen=new Set();
  for (;;) {
    assert(node,row.problemId); const key=JSON.stringify([graph.id,node.id,used]); assert(!seen.has(key)); seen.add(key);
    if (node.type==='route') {
      transitions.push({fromGraphId:graph.id,fromNodeId:node.id,toGraphId:node.graph});
      graph=graphs.get(node.graph); assert(graph); node=graph.nodes.find(n=>n.id===graph.root); continue;
    }
    if (node.type!=='question'||used===row.choices.length) break;
    const answer=row.choices[used++], option=options(node).find(o=>o.id===answer); assert(option);
    steps.push({graphId:graph.id,nodeId:node.id,question:node.title,answer,answerLabel:option.label});
    node=graph.nodes.find(n=>n.id===node.answers[answer]);
  }
  assert.equal(used,row.choices.length);
  return {steps,transitions,current:{graphId:graph.id,nodeId:node.id,type:node.type,title:node.title,
    options:options(node),techniques:node.techniques??[]}};
}

check('the preselected six identities, exact competition dates, original numeric bounds and initial rows remain fixed', async()=>{
  const {audit,original,snapshots}=await evidence();
  assert.equal(sha(snapshots['original-audit']),EXPECTED.initialAuditSha256);
  assert.equal(audit.corpusId,'ioi-2017');assert.equal(audit.cutoff,'2026-10-14');
  assert.equal(digest(audit.status),EXPECTED.statusSha256);
  assert.equal(digest(projection(audit.selection,original.selection)),EXPECTED.selectionSha256);
  assert.equal(audit.selection.fixedBeforeTechniqueSearch,true);
  assert.equal(audit.selection.selectionBeforeTechniqueMatching,true);assert.equal(audit.selection.totalProblems,6);
  assert.equal(audit.selection.indexUrl,'https://www2.ioi-jp.org/ioi/2017/tasks/index.html');
  assert.equal(audit.selection.fixedProblemListComplete,true);
  assert.deepEqual(audit.records.map(r=>r.problemId),ids);
  const initial=audit.records.map((r,i)=>projection(r,original.records[i]));
  assert.equal(digest(initial),EXPECTED.recordsSha256);assert.deepEqual(initial,original.records);
  const boundKeys=[['rows','columns','fixedInputs'],['redPoints','bluePoints','coordinates'],
    ['N','M','outdegree'],['N','hardQueryLimit','fullScoreQueries'],['N','M','queryLimits'],['N','s','p']];
  const boundValues=[['1..1024','1..1024',10],['1..100000','1..100000','0..1000000000'],
    ['1..5000','N..20000','>=1'],['3..200000',10000,5000],
    ['2..500','N−1..N(N−1)/2',{firstThreeSubtasks:30000,completeGraphSubtask:12000,fullScoreFinalSubtask:8000}],
    ['1..1000000','0..N−1','permutation of0..N−1']];
  for (const [i,row] of initial.entries()) {
    assert.equal(digest(row),EXPECTED.rowSha256[i]);assert.equal(row.officialTaskId,tasks[i]);
    assert.equal(row.source,'ioi');assert.equal(row.difficulty,null);
    assert.equal(row.date,i<3?'2017-07-30':'2017-08-01');assert.equal(row.datePrecision,'day');
    assert.equal(row.contest.day,i<3?1:2);assert.equal(row.contest.exactDateVerified,true);
    const day=i<3?1:2;
    assert.equal(row.statementUrl,tasks[i]==='train'?'https://ioi.te.lv/locations/ioi17/contest/day1/train.pdf':
      `https://www2.ioi-jp.org/ioi/2017/tasks/day${day}-${tasks[i]}-ISC.pdf`);
    assert.equal(row.editorialUrl,`https://ioi.te.lv/locations/ioi17/contest/day${day}/editorial/${tasks[i]}.pdf`);
    assert.equal(row.constraints.numericBoundsVerified,true);
    assert.deepEqual(boundKeys[i].map(k=>row.constraints.values[k]),boundValues[i]);
    assert(row.constraints.numericEvidenceUrls.length>0);assert(row.constraints.numericEvidenceSearchQueries.length>0);
    assert.equal(row.materialStatus.visualDetails,'not-claimed');
  }
  const books=initial[5].technicalFindings;
  assert.equal(books.oldDraftApi,'booksort(N,S,order)');assert.equal(books.finalApi,'minimum_walk(p,s)');
  assert.match(books.editorialProvenance,/旧稿/);assert.match(books.editorialProvenance,/最終KOR\/ISCだけ/);
  assert.equal(initial[4].technicalFindings.officialEarDecompositionVerified,false);
  assert.equal(initial[4].technicalFindings.chosenFullSolutionVerified,true);
});

check('the immutable 921 core and separate vendor105/public466 epoch keep their exact raw ledgers',async()=>{
  const {audit,manifest}=await evidence();
  const originalBytes=Buffer.from(manifest.originalManifestRawBase64,'base64');
  assert.equal(sha(originalBytes),EXPECTED.originalManifestSha256);
  const old=JSON.parse(originalBytes);
  const coreBefore=Buffer.from(manifest.originalCoreBeforeRawBase64,'base64');
  const coreAfter=Buffer.from(manifest.originalCoreAfterRawBase64,'base64');
  const extendedBefore=Buffer.from(manifest.originalExtendedBeforeRawBase64,'base64');
  const extendedAfter=Buffer.from(manifest.originalExtendedAfterRawBase64,'base64');
  assert.deepEqual(coreBefore,coreAfter);assert.deepEqual(extendedBefore,extendedAfter);
  const core=JSON.parse(coreBefore),all=JSON.parse(extendedBefore);
  assert.equal(Object.keys(core).length,921);assert.equal(Object.keys(all).length,1492);
  assert.deepEqual(Object.fromEntries(manifest.files.map(f=>[f.path,f.sha256])),all);
  assert.equal(new Set(manifest.files.map(f=>f.path)).size,1492);
  for(const [file,h]of Object.entries(core))assert.equal(all[file],h);
  assert.equal(manifest.files.filter(f=>f.epoch==='initial-core').length,921);
  const extension=manifest.files.filter(f=>f.epoch==='later-dependency-extension');
  assert.equal(extension.length,571);assert.equal(extension.filter(f=>f.path.startsWith('vendor/')).length,105);
  assert.equal(extension.filter(f=>f.path.startsWith('public/')).length,466);
  assert.equal(sha(Buffer.from(manifest.originalExtendedLedgerRawBase64,'base64')),
    '1c2d89f4e92c6dcf6279b26a1a206082331906385f8be2a866e10f50e0765bac');
  assert.equal(old.coreLedgerSha256,'718d89756d8413a1836046b321415fa220edb68718173fb5797039574fa7e71e');
  assert.equal(old.freezeExtension.originalCoreRemainsUnchangedInSnapshot,true);
  assert(old.freezeExtension.original921LiveChangesAtExtension.includes('data/flows.json'));
  assert.equal(manifest.files.filter(f=>f.epoch==='initial-core'&&/^src\/content\/docs\/techniques\/.*\.mdx$/.test(f.path)).length,498);
  assert.equal(manifest.files.some(f=>f.path.split('/').some(part=>part.startsWith('.env'))),false);
  assert.equal(manifest.allHistoricalRawFilesPermanentlyStored,false);
  assert.equal(manifest.allHistoricalMdxPermanentlyStored,false);
  assert.equal(audit.snapshot.allHistoricalMdxPermanentlyStored,false);
  assert.equal(audit.snapshot.coreRawFileCount,921);assert.equal(audit.snapshot.dependencyExtensionFileCount,571);
  assert.deepEqual(audit.snapshot.initialCounts,{allTechniqueMdx:498,flowcharts:465,walks:519,
    metadataRecords:498,referenceRecords:519,specificTechniques:420,entryDomains:15});
  assert.equal(manifest.compilerDependency.copiedInInitialCore,false);
});

check('retained flow, metadata, old walks, refs, source and13 full nearby articles match their original raw hashes',async()=>{
  const {manifest,snapshots,bundle,rawFiles,audit}=await evidence();
  const ledger=new Map(manifest.files.map(f=>[f.path,f.sha256]));
  assert.equal(JSON.parse(snapshots.flow).length,465);assert.equal(JSON.parse(snapshots.technique).length,498);
  assert.equal(JSON.parse(snapshots.walk).length,519);assert.equal(JSON.parse(snapshots.reference).length,519);
  assert.equal(sha(snapshots.flow),ledger.get('data/flows.json'));
  assert.equal(sha(snapshots.walk),ledger.get('data/problem-walks.json'));
  assert.equal(sha(snapshots.source),ledger.get('data/sources.json'));
  assert.equal(bundle.files.length,29);assert.equal(rawFiles.size,29);
  assert.equal(manifest.retainedOriginalRawFileCount,32);
  for(const f of bundle.files){assert.equal(sha(rawFiles.get(f.path)),f.sha256);assert.equal(f.sha256,ledger.get(f.path));}
  const articleFiles=bundle.files.filter(f=>f.path.startsWith('src/content/docs/techniques/'));
  assert.equal(articleFiles.length,13);assert.equal(bundle.files.filter(f=>f.path.startsWith('src/lib/')).length,7);
  const nearby=audit.records.flatMap(r=>r.relatedArticleReview);assert.equal(nearby.length,15);
  assert.equal(new Set(nearby.map(r=>r.techniqueId)).size,13);
  for(const row of nearby){
    const raw=rawFiles.get(row.file);assert(raw);assert.equal(sha(raw),row.sha256);
    assert.equal(row.fullArticleAndAllCodeRead,true);assert.equal(row.originalFullRangeApiReusable,false);
    assert.equal(row.fullImplementationRevalidatedForOriginal,false);assert(row.scopeMismatch.length>0);
    const fences=[...raw.toString().matchAll(/^```cpp\s*\n([\s\S]*?)^```\s*$/gm)];
    if(row.cppFenceSha256)assert.equal(sha(fences[0][1]),row.cppFenceSha256);else assert.equal(fences.length,0);
  }
});

check('all six complete steps, answer labels, actual stops and gaps replay independently from465 frozen graphs',async()=>{
  const {audit,snapshots}=await evidence(), flow=JSON.parse(snapshots.flow);
  const graphs=new Map(flow.map(g=>[g.id,g])), metadata=new Set(JSON.parse(snapshots.technique).map(t=>t.id));
  assert.equal(flow.filter(g=>g.entry===true).length,15);
  for(const [i,row]of audit.records.entries()){
    const [entry,choices,g,n]=routes[i];assert.equal(row.entryGraphId,entry);assert.deepEqual(row.choices,choices);
    const got=replay(graphs,row);assert.deepEqual(got.steps,row.steps);
    assert.equal(digest(got.steps),row.navigationReplay.stepsSha256);
    assert.deepEqual(got.transitions,row.navigationReplay.routeTransitions);
    for(const field of ['initialReached','originalRootReached','canonicalRouteEnd'])assert.deepEqual(got.current,row[field]);
    assert.equal(got.current.graphId,g);assert.equal(got.current.nodeId,n);
    assert.equal(row.gap.firstMissingGraphId,g);assert.equal(row.gap.firstMissingNodeId,n);
    assert.equal(row.gap.currentQuestion,got.current.title);assert.deepEqual(row.gap.currentOptions,got.current.options);
    assert.equal(row.gap.stopNodeType,got.current.type);assert.deepEqual(row.actualReachedTechniqueIds,got.current.techniques);
    assert.deepEqual(row.expectedTechniqueIds,[]);assert.deepEqual(row.gap.neededTechniqueIds,[needed[i]]);
    assert(!metadata.has(needed[i]));for(const t of row.gap.existingRelatedTechniqueIds)assert(metadata.has(t));
    const proposed=row.gap.proposedBranchAt, question=graphs.get(proposed.graphId).nodes.find(n=>n.id===proposed.nodeId);
    assert.equal(proposed.question,question.title);assert.deepEqual(proposed.currentOptions,options(question));
    assert.deepEqual(row.navigationReplay.all15EntryDomainsConsidered,flow.filter(g=>g.entry===true).map(g=>g.id));
  }
});

check('all13 frozen nearby APIs retain their contracts; twelve C++ fences and the output-save Python run distinct scope witnesses',async()=>{
  const {audit,rawFiles}=await evidence();const ids=[...new Set(audit.records.flatMap(r=>r.relatedArticleReview.map(a=>a.techniqueId)))].filter(id=>id!=='output-only');assert.equal(ids.length,12);
  const fences=ids.map(id=>{
    const s=rawFiles.get(`src/content/docs/techniques/${id}.mdx`).toString();
    const blocks=[...s.matchAll(/^```cpp\s*\n([\s\S]*?)^```\s*$/gm)];assert.equal(blocks.length,1);return blocks[0][1];
  });
  const expected=audit.validation.checks.existingApiScopeChecks;
  ids.forEach((id,i)=>{if(expected.compiledActualFrozenCppFences[id])assert.equal(sha(fences[i]),expected.compiledActualFrozenCppFences[id]);});
  const folder=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2017-scope-test-'));
  try{
    const cpp=path.join(folder,'scope.cpp'), exe=path.join(folder,'scope');
    await writeFile(cpp,fences.join('\n')+`\n#include <iostream>\nint main(){
      auto p=bipartite_match({{0},{0}},1);int got=0;for(int x:p)got+=(x>=0);if(got!=1)return 1;
      if(classify_normal_graph_game({{0,1},{0,1}})!=std::vector<int>{0,0})return 2;
      if(sort_permutation_swaps({2,1,0}).size()!=1)return 3;
      // A legal tile-unique path may touch itself through an unchosen edge;
      // the four chosen cells below induce a cycle, illegal in Nowruz.
      TilePath tile(2,3,{0,1,2,3,4,5},{1,1,1,1,1,1},{0,1,4,3});
      if(tile.path().size()!=4)return 4;
      // Fixed total quantity alone allows leaving red100 unused: flow3 vs
      // literal every-point edge cover99. A lower-degree model is missing.
      MinCostFlow cost(6);cost.add(4,0,2,0);cost.add(4,1,2,0);
      cost.add(0,2,2,1);cost.add(0,3,2,2);cost.add(1,2,2,99);cost.add(1,3,2,98);
      cost.add(2,5,1,0);cost.add(3,5,1,0);if(cost.flow(4,5,2)!=std::pair<long long,long long>{2,3})return 5;
      // Valid DAG input confirms the finite normal-play contract. Cyclic
      // owned repeated-target play has no representation in that signature.
      if(grundy_dag({{},{0}})!=std::vector<int>{0,1})return 6;
      auto components=scc_ids({{0,1},{1}});if(components[0]==components[1])return 7;
      // ask_interval consumes one scalar; Prize requires a pair. Supplying
      // the pair leaves the second integer unread, as its contract predicts.
      std::istringstream input("7 9");std::ostringstream output;
      auto oldin=std::cin.rdbuf(input.rdbuf());auto oldout=std::cout.rdbuf(output.rdbuf());int used=0;
      int scalar=ask_interval(0,1,used,2),second=-1;std::cin>>second;
      std::cin.rdbuf(oldin);std::cout.rdbuf(oldout);
      if(scalar!=7||second!=9||used!=1)return 8;
      auto groups=binary_test_groups(3);if(groups.size()!=2||groups[0].size()!=1||decode_binary_test(3,"10")!=1)return 9;
      // The arbitrary singleton groups cannot be a full spanning-tree query
      // in a four-vertex path. The API is valid in its original oracle model.
      std::vector<long long> peak{1,3,8,6,2};if(fibonacci_peak_value(5,[&](int i){return peak[i];})!=8)return 10;
      auto pair=find_binary_weight_hidden_pair(2,std::vector<int>{0},std::vector<int>{1},1,2,
        [](const std::vector<int>& weighting)->std::int64_t{return 1+weighting[0];});
      if(std::min(pair.first,pair.second)!=0||std::max(pair.first,pair.second)!=1)return 11;
      auto edge_swaps=sort_permutation_on_edges({2,1,0},{{0,1},{1,2}});
      if(!edge_swaps||edge_swaps->size()!=3)return 12;
      std::cout<<"scope-counterexamples-pass";
    }\n`);
    await execute('g++',['-std=c++20','-O2','-Wall','-Wextra','-Werror',cpp,'-o',exe],{encoding:'utf8',maxBuffer:4194304});
    const run=await execute(exe,[],{encoding:'utf8',maxBuffer:4194304});
    assert.equal(run.stdout,'scope-counterexamples-pass');
    const source=rawFiles.get('src/content/docs/techniques/output-only.mdx').toString();
    const python=[...source.matchAll(/^```python\s*\n([\s\S]*?)^```\s*$/gm)][0][1];
    const program=python+'\nimport sys\nfrom pathlib import Path\np=Path(sys.argv[1])\nassert save_if_better(p,"arbitrary text",lambda _:True,lambda _:1)\nassert p.read_text()=="arbitrary text"\n';
    await execute('python3',['-c',program,path.join(folder,'candidate.txt')],{encoding:'utf8',maxBuffer:4194304});
    // Literal target models: two red points both need covering, either owner
    // can recharge at0, and one held book must enter and leave the outer cycle.
    const x=[0,1], y=[2];assert.equal(x.reduce((s,v)=>s+Math.abs(v-y[0]),0),3);
    const out=[[0,1],[0,1]], owner=[0,1], charge=[1,0];
    function fixedTrain(s,choices){const seen=new Map(),walk=[];while(!seen.has(s)){seen.set(s,walk.length);walk.push(s);s=choices[s];}
      return walk.slice(seen.get(s)).some(v=>charge[v]);}
    for(const start of [0,1]){let win=false;for(const a of out[1]){let every=true;for(const b of out[0])every&&=fixedTrain(start,[b,a]);win ||= every;}assert.equal(win,true);}
    // p[2,1,0],s1 needs one step to an outer-cycle vertex, four units of
    // book transport and one step back. All physical state BFS agrees below.
    const key=(items,pos)=>items.join(',')+':'+pos;const start={a:[0,1,2,3],p:1,d:0};
    const queue=[start],dist=new Map([[key(start.a,start.p),0]]);
    while(queue.length){const q=queue.shift();if(q.d!==dist.get(key(q.a,q.p)))continue;
      const a=q.a.slice();[a[q.p],a[3]]=[a[3],a[q.p]];
      const successors=[{a,p:q.p,d:q.d},...[q.p-1,q.p+1].filter(p=>p>=0&&p<3).map(p=>({a:q.a,p,d:q.d+1}))];
      for(const v of successors){const k=key(v.a,v.p);if(v.d<(dist.get(k)??Infinity)){dist.set(k,v.d);queue.push(v);}}
    }assert.equal(dist.get(key([2,1,0,3],1)),6);assert.equal(owner.length,2);
  }finally{await rm(folder,{recursive:true,force:true});}
});

check('the accepted progress schema yields original6 statements,4 solutions,2 unconfirmed and no completed API/coverage',async()=>{
  const {audit,original}=await evidence();
  const {isCorpusStatementReviewed,isCorpusSolutionReviewed}=await import(pathToFileURL(path.join(root,'scripts/lib/corpus-progress.mjs')));
  const rows=audit.records.map((r,i)=>projection(r,original.records[i]));
  assert.equal(rows.filter(isCorpusStatementReviewed).length,6);assert.equal(rows.filter(isCorpusSolutionReviewed).length,4);
  for(const row of rows){const yes=positive.has(row.officialTaskId);
    assert.equal(row.researchSolutionConfirmed,yes);assert.equal(row.reviewStatus,yes?'verified':'unconfirmed');
    assert.equal(row.classification,yes?'missing-technique':'unconfirmed');
    assert.equal(row.technicalFindings.fullImplementationValidated,false);assert.equal(row.completedApiCoverage,false);
    assert.equal(row.technicalFindings.chosenFullSolutionVerified,yes);assert.equal(row.gap.implementationNeeded,true);
    assert(row.technicalFindings.remainingImplementationValidation.length>0);
    if(yes){assert.equal(row.materialStatus.solution,'retrieved-and-reviewed');
      assert.equal(row.collectionStatus,'statement-and-independent-analysis-verified');assert.equal(row.verification,'independent-analysis');
      for(const mutation of [{reviewStatus:'unconfirmed'},{materialStatus:{...row.materialStatus,solution:'retrieved-partially-reviewed'}},
        {verification:'tag-guess'},{collectionStatus:'statement-only'}])assert.equal(isCorpusSolutionReviewed({...row,...mutation}),false);
    }else{assert(row.technicalFindings.unconfirmedDetails.length>0);assert.equal(isCorpusSolutionReviewed({...row,reviewStatus:'verified'}),false);}
  }
  assert.equal(audit.status.solutionReviewedCount,4);assert.equal(audit.status.unconfirmedCount,2);
  assert.equal(audit.status.coveredCount,0);assert.equal(audit.status.fullImplementationValidatedCount,0);
  for(const flag of ['fixedCorpusResearchComplete','fixedCorpusCoverageComplete','globalCoverageComplete','articleResolutionComplete'])assert.equal(audit.status[flag],false);
});

check('live resolutions require actual reviewed articles, references and valid root walks while initial4/6 and0 coverage stay fixed',async()=>{
  const {audit,original}=await evidence();const plan=await json('data/coverage-plan.json'),selection=plan.corpora.find(c=>c.id==='ioi-2017');
  assert(selection);assert.equal(selection.expectedProblems,6);assert.equal(selection.auditFile,'data/corpus-audits/ioi-2017.json');
  assert.deepEqual(selection.fixedProblems.map(r=>r.problemId),ids);assert.equal(selection.fixedProblems.length,6);
  assert.equal(audit.cutoff,plan.cutoff);for(const [i,r]of selection.fixedProblems.entries())
    for(const k of ['source','problemId','officialTaskId','day','date','statementUrl','editorialUrl'])assert.deepEqual(r[k],audit.records[i][k]);
  const gaps=plan.knownGaps.filter(g=>g.discoveredBy==='ioi-2017');assert.equal(gaps.length,6);
  const {readCorpusProgress}=await import(pathToFileURL(path.join(root,'scripts/lib/corpus-progress.mjs')));
  const progress=await readCorpusProgress(root,await json('data/sources.json'));
  const selected=progress.filter(r=>ids.includes(r.problemId));assert.equal(selected.length,6);
  assert.equal(selected.filter(r=>r.statementVerified).length,6);assert(selected.filter(r=>r.solutionVerified).length>=4);
  for(const task of positive)assert.equal(selected.find(r=>r.problemId==='ioi2017_'+task)?.solutionVerified,true);
  const ledger=await json('data/research-ledger.json');
  assert.equal(ledger.corpusStatementsReviewed,progress.filter(r=>r.statementVerified).length);
  assert.equal(ledger.corpusSolutionsReviewed,progress.filter(r=>r.solutionVerified).length);
  const walks=await json('data/problem-walks.json');
  const names=await readdir(path.join(root,'data'));
  const collection=async prefix=>(await Promise.all(names.filter(n=>n.startsWith(prefix)&&n.endsWith('.json')).map(n=>json('data/'+n)))).flat();
  const [techniques,references]=await Promise.all([collection('techniques-'),collection('references-')]);
  const {assessCorpus}=await import(pathToFileURL(path.join(root,'scripts/audit-coverage.mjs')));
  const {validateSite}=await import(pathToFileURL(path.join(root,'scripts/validate.mjs')));
  const preflight=await validateSite(root);assert.deepEqual(preflight.errors,[]);
  const {compileLocalModules}=await import(pathToFileURL(path.join(root,'scripts/local-modules.mjs')));
  const folder=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2017-live-'));
  try{
    await compileLocalModules(root,folder);const flow=await import(pathToFileURL(path.join(folder,'flow.js')));
    const entries=new Set(flow.entryGraphs.map(g=>g.id));
    const data={techniques,references,walks,preflightPassed:true,isWalkValid(walk,id){
      if(!entries.has(walk.entryGraphId)||!Array.isArray(walk.choices))return false;
      try{const got=flow.walkFromRoot(walk.choices,walk.entryGraphId);
        return got.consumed===walk.choices.length&&got.current.type==='result'&&got.current.techniques.includes(id)
          &&JSON.stringify(got.steps.map(({graph,node,answer})=>({graph,node,answer})))===JSON.stringify(walk.steps);
      }catch{return false;}
    }};
    const fixed={...selection,cutoff:plan.cutoff};
    // Historical rows have no resolution even if live articles are later added.
    const initial=assessCorpus(original,data,fixed);assert.deepEqual(initial.errors,[]);
    assert.equal(initial.reviewedProblems,4);assert.equal(initial.coveredProblems,0);assert.equal(initial.coverageComplete,false);
    const live=assessCorpus(audit,data,fixed);assert.deepEqual(live.errors,[]);assert(live.reviewedProblems>=4);
    for(const row of audit.records){
      const gap=gaps.find(g=>g.id===row.gap.id);assert(gap);assert.equal(gap.problemId,row.problemId);
      assert.deepEqual(gap.techniqueIds,row.gap.neededTechniqueIds);
      const result=live.records.find(r=>r.problemId===row.problemId);assert(result);
      const useWalks=walks.filter(w=>String(w.source).toLowerCase()==='ioi'&&w.problemId===row.problemId);
      const hasResolution=row.resolution!==undefined;
      if(gap.state==='resolved'||hasResolution||useWalks.length){
        assert.equal(result.currentClassification,'covered',row.problemId+' actual article/reference/root-walk coverage');
        assert.equal(result.resolved,true);assert.equal(row.resolution?.status,'verified');assert.equal(gap.state,'resolved');
        assert(useWalks.length>0);assert(row.resolution.techniqueIds.length>0);
        for(const id of row.gap.neededTechniqueIds)assert(row.resolution.techniqueIds.includes(id),'resolution includes the precise missing technique');
        for(const id of row.resolution.techniqueIds){
          const meta=techniques.find(t=>t.id===id);assert.equal(meta?.status,'reviewed');
          const article=await bytes('src/content/docs/techniques/'+id+'.mdx');assert(article.length>0);
          assert(references.some(r=>r.techniqueId===id&&String(r.source).toLowerCase()==='ioi'&&r.problemId===row.problemId&&r.url===row.statementUrl));
          assert(useWalks.some(w=>w.expectedTechniqueIds.includes(id)&&data.isWalkValid(w,id)));
        }
        // Merely retaining a resolution cannot rescue missing live evidence.
        for(const absent of [{...data,preflightPassed:false},
          {...data,walks:data.walks.filter(w=>w.problemId!==row.problemId)},
          {...data,references:data.references.filter(r=>r.problemId!==row.problemId)},
          {...data,techniques:data.techniques.filter(t=>!row.resolution.techniqueIds.includes(t.id))}]){
          assert.equal(assessCorpus(audit,absent,fixed).records.find(r=>r.problemId===row.problemId).resolved,false);
        }
        const noResolution=structuredClone(audit);delete noResolution.records.find(r=>r.problemId===row.problemId).resolution;
        assert.equal(assessCorpus(noResolution,data,fixed).records.find(r=>r.problemId===row.problemId).resolved,false);
      }else{assert(['pending','unconfirmed'].includes(gap.state));assert.equal(result.resolved,false);}
    }
    // A forged positive resolution to a nonexistent article must fail even
    // when the original source and major proof were already reviewed.
    const forged=structuredClone(original),fake='ioi2017-regression-nonexistent-article';
    assert(!techniques.some(t=>t.id===fake));forged.records[1].resolution={status:'verified',techniqueIds:[fake]};
    assert.equal(assessCorpus(forged,data,fixed).records[1].resolved,false);
    assert.equal(assessCorpus(forged,{...data,isWalkValid:()=>true},fixed).records[1].resolved,false);
  }finally{await rm(folder,{recursive:true,force:true});}
});

check('all old fields of the eight earlier audits survive, including already present resolutions and positive reviews',async()=>{
  const {rawFiles}=await evidence();const prior=[...rawFiles].filter(([f])=>f.startsWith('data/corpus-audits/'));
  assert.equal(prior.length,8);
  for(const [file,raw]of prior){assert.equal(sha(raw),EXPECTED.old8[file]);const before=JSON.parse(raw),current=await json(file);
    assert.deepEqual(projection(current,Object.fromEntries(Object.entries(before).filter(([k])=>k!=='records'))),
      Object.fromEntries(Object.entries(before).filter(([k])=>k!=='records')),file+' old top fields');
    assert.equal(current.records.length,before.records.length);
    before.records.forEach((r,i)=>{
      // Every key already present in the baseline is fixed as a complete
      // value. Only new row keys, e.g. a new Line or K resolution, are allowed.
      assert.deepEqual(projection(current.records[i],r),r,file+':'+r.problemId);
    });
  }
});

check('the normalized manual probe reproduces every mathematical counter and discloses its limited permanent bytes',async()=>{
  const {audit,snapshots}=await evidence();
  const initial=await json('research/probes/ioi-2017-initial-probe-results.json');
  const normalizedRaw=await bytes('research/probes/ioi-2017-research-checks-results.json');
  assert.equal(sha(normalizedRaw),EXPECTED.normalizedResultsSha256);const normalized=JSON.parse(normalizedRaw);
  const script=await bytes('research/probes/ioi-2017-research-checks.py');
  assert.equal(sha(script),EXPECTED.normalizedProbeSha256);assert.equal(sha(script),audit.validation.probeSha256);
  assert.equal(sha(snapshots['original-probe']),'18a76ae16bc2ab3ca68dfa3e74672acb57099a9ad6dbb78679735e387a906993');
  assert(!script.toString().includes('/tmp/'+'flowchartcp-'));
  for(const key of [...tasks,'routes','productRuntimeCrosscheck','existingApiScopeChecks'])assert.deepEqual(normalized[key],initial[key],key);
  assert.equal(normalized.productionImplementationValidated,false);
  assert.equal(normalized.baseline.historicalRawHashLedgerEntries,1492);
  assert.equal(normalized.baseline.retainedOriginalRawFilesRehashed,32);
  assert.equal(normalized.baseline.retainedFullMdxCount,13);
  assert.equal(normalized.baseline.allHistoricalRawBytesAvailable,false);
  assert.equal(normalized.baseline.allHistoricalMdxAvailable,false);
  assert.equal(normalized.wiring.allBipartiteEdgeSubsets,701112);assert.equal(normalized.wiring.maximumCombinedN200000Cases,3);
  assert.equal(normalized.train.allOwnerAndNonemptyChargerAssignments,19318);
  assert.equal(normalized.prize.maximumNonCheapestPrizesForN200000,472);
  assert.equal(normalized.simurgh.everyHiddenSpanningTreeForEveryGraph,8135);
  assert.equal(normalized.simurgh.allN500UpperBound,5990);assert(5990<8000);
  assert.equal(normalized.books.allPermutationsN1to6AllStarts,5039);
  assert.equal(normalized.books.literalPickupSwapPutdownAdjacentMoveStates,201602);
  assert.equal(audit.preservation.automaticCollectorOrScheduleAdded,false);
});
