import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir,writeFile,mkdir,mkdtemp,rm,symlink,unlink} from 'node:fs/promises';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath,pathToFileURL} from 'node:url';
const run=promisify(execFile),directory=path.dirname(fileURLToPath(import.meta.url));
const site=path.basename(directory)==='tests'?path.dirname(directory):process.cwd();
const stage=process.argv.includes('--stage');
const root=stage?'/tmp/flowchartcp-ioi2016-registration-stage':site;
const bytes=file=>readFile(path.join(root,file));
const json=async file=>JSON.parse(await bytes(file));
const liveJson=async file=>JSON.parse(await readFile(path.join(site,file),'utf8'));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const canonical=value=>{const sorted=x=>Array.isArray(x)?x.map(sorted):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,sorted(x[k])])):x;return sha(JSON.stringify(sorted(value)));};
const omit=(value,keys)=>Object.fromEntries(Object.entries(value).filter(([k])=>!keys.includes(k)));
const projection=(value,original)=>Array.isArray(original)?original.map((x,i)=>projection(value?.[i],x)):original&&typeof original==='object'?Object.fromEntries(Object.keys(original).map(k=>[k,projection(value?.[k],original[k])])):value;
const tasks=['molecules','railroad','shortcut','paint','messy','aliens'];
const ids=tasks.map(s=>'ioi2016_'+s);
const auditFile='data/corpus-audits/ioi-2016.json';
const NORMALIZED_VALIDATION={"keys": ["manualCommand", "probeFile", "probeSha256", "probeOutputFile", "probeOutputSha256", "checks", "independentRawWalker", "actualFrozenRuntimeReplay", "runtimeReplay", "scopeChecker", "scopeChecks", "sanitizerOrProductionScopeClaimed", "originalProbeFile", "originalProbeSha256", "actualFrozenRuntimeReplayCommand", "independentReview", "normalization"], "sha256": "84d9e835b2a229541ba16322075b6fa79e146dc34620992fa81c33a666a7252f"};
const FROZEN={
  "research/ioi-2016-audit-notes.md": "2c0f0dde6082a0da823fd15c20334feafdaf6410a4ac6abb54fc380ed1128cbe",
  "research/probes/ioi-2016-frozen-runtime.mjs": "d0dff366418a8460719227b671a7aeb576cc705f7f494623d540ed0effe00b42",
  "research/probes/ioi-2016-frozen-scope.py": "d9157fb1629bfc4e0f75849a072b6a047dc80f6e73c83c8cb5b027ee10848d32",
  "research/probes/ioi-2016-independent-checks-results.json": "7c12c840a484caa51c100caa0977a752ecb73e9a772c2f0280fd3c066390ffd3",
  "research/probes/ioi-2016-independent-checks.py": "f48abd3335c856a6453b124d1029da4c02d88c400d74c3d0b394a9c92673c063",
  "research/probes/ioi-2016-independent-review.json": "0545411718e1f207c90daa81295fc2117c5cf475333075b558b8e052c54e888a",
  "research/probes/ioi-2016-independent-schema-results.json": "2d95c897e77cb0861f6623db25f083498c491aeffce8b39e767d3ffc2683b414",
  "research/probes/ioi-2016-initial-probe-results.json": "f029dfc00a9010178d3e4ba14adabcbf42aba54c86a401ac5b26d409d0152908",
  "research/probes/ioi-2016-initial-scope-results.json": "df7d2079ca944a1a0c42f813e371cd2104e96e22c24377855f82a5f004a84b93",
  "research/probes/ioi-2016-probe-normalizations.json": "a59cc3f0277caa3b4b2563bea08b1ffb5fd78faca51acf3ed908f1c55783c270",
  "research/probes/ioi-2016-registration-plan.json": "d926952b065a6fed3f64edef1f544ae1e9a9875873df68116468799ea73a6bbf",
  "research/probes/ioi-2016-research-checks.py": "e02b22d5425b4939f22815674b8c314f43bb88242d7a1afcadb2e24dd02eb336",
  "research/probes/ioi-2016-root-replay.py": "53c62e171acd1308c9eb4b484065e25f4b08b076848398985e16693cb550db66",
  "research/probes/ioi_2016_snapshot.py": "9bbae5afb43e48e02ddb482bef74ed4016b0abe886737ae3a71f0c981b402dea",
  "research/snapshots/ioi-2016-initial-raw.json.gz": "8254a22da9aecd929f728bf79275a560645c0718ae219dc54f2358264c929542",
  "research/snapshots/ioi-2016-manifest.json": "ec6186bf2f2d8a79cc70782d8c44703bf6d8908083fc2740169ae25c17946a3f",
  "research/snapshots/ioi-2016-original-assess-corpus.json.gz": "7aa48c08c8fe3a54f620b7a42b55d169981907995b3db4a811a7deb47a39c0da",
  "research/snapshots/ioi-2016-original-audit-notes.md.gz": "c4da0baf8f744359a72df8994f8de3c1c1cd3a614ebdad908c4d8f4541d8ee3c",
  "research/snapshots/ioi-2016-original-audit.json.gz": "895f7bff548c2e6bcc0c4f19610336a1dd6f0b4fcd6274b670141491ec1eaf62",
  "research/snapshots/ioi-2016-original-build-audit.py.gz": "30ba898e86d6ee3837fd8446a2791945b74b0db1c4a4ba445b25219265cd3c66",
  "research/snapshots/ioi-2016-original-frozen-scope-checks.cpp.gz": "84ef939f8344743a1688e1a69c93b6d88fed9890e97f04f891b48e25cb164665",
  "research/snapshots/ioi-2016-original-independent-probe-results.json.gz": "eb22b866b6464a638e67b1ce64757598f4efeeca010e4902ce041f4fd31eb0db",
  "research/snapshots/ioi-2016-original-independent-probe.py.gz": "7b29dfeda3a7d684df6851ebfd229f6b4bac52b457a2144532e1985b4c0081ce",
  "research/snapshots/ioi-2016-original-independent-review.json.gz": "f4a6ed6dbb727035d8f372b8e2bfbb754d8b6abb086c7022e48e3622b7d8ae6d",
  "research/snapshots/ioi-2016-original-independent-schema-results.json.gz": "9f1dc2b794d52acd850ac5883902a483f5b2e51b7317db23a11c18fe38147bbc",
  "research/snapshots/ioi-2016-original-independent-schema.mjs.gz": "0aef027b523907a154a2ed483b59efb8ed8d0f7c05b1c9e221db690df4e94a1f",
  "research/snapshots/ioi-2016-original-probe.json.gz": "68aa568be73ee612ab1b3f0f5f402625582a4c2473c2e89fe7b4cd564f0e7282",
  "research/snapshots/ioi-2016-original-probe.py.gz": "4e9c5dd060d82ae89bebefba58be56127d10aa0468294876c5fc6ff0c33352cf",
  "research/snapshots/ioi-2016-original-registration-proposal.json.gz": "ad1453c865faa2e91878d9971664dd1ceff16e305f6914a1318ee2b37987fa18",
  "research/snapshots/ioi-2016-original-replay.py.gz": "aabdb8434d18c32998501b89164bb3752d3a26e77a133ac2cde42b000f9b1eab",
  "research/snapshots/ioi-2016-original-routes.json.gz": "e819593ba80950e4af976b75d40547ca4fcc5eb70a3cbaa8f405a1caf0a4dbc9",
  "research/snapshots/ioi-2016-original-runtime-replay.json.gz": "a0f1543f2327a584f8781deb535fc16805f9e71ce3055fea1a443c72a9f44a93",
  "research/snapshots/ioi-2016-original-runtime-replay.mjs.gz": "cf14e8373133d6c9ad5cf01209da2eaeebf70b8f1d36e88212e7f020379af283",
  "research/snapshots/ioi-2016-original-schema-check.json.gz": "6bafe9fc0ade1d6bd3342f743bfe5df0b7ed861de93b0ce2e59a443660a5aab4",
  "research/snapshots/ioi-2016-original-scope-checks.json.gz": "ce2881df5c45ed0758395bae2931c8fae59613f836828536aeb8ebd2dc0799aa",
  "research/snapshots/ioi-2016-original-scope-checks.py.gz": "358fb9924e70d0a111c394a648909458e8de506088279d5e883d94b67a644b9e",
  "research/snapshots/ioi-2016-original-selection.json.gz": "635dfcc43fe302cc35ccf4b256dd5ae5450865d7911f81826efb23cb97d33c9f",
  "research/snapshots/ioi-2016-original-sidecar.json.gz": "db30d33fc44e45b34fbe1ba2d362d4e13935bca55f2f07d63bc49e2ac18166f9",
  "research/snapshots/ioi-2016-selection.json": "3505ba77043d0ff594b6b66fe763cf9e7b1cd97082a79ff4dc30cbca809c3350",
  "research/snapshots/ioi-2016-vendor-raw.json.gz": "f78c62079ff057a7dd833583c14aee3bfc8c0890b95aceb4b99ff0cecf65523e"
};
let evidencePromise;
async function evidence(){return evidencePromise??=(async()=>{
 const manifest=await json('research/snapshots/ioi-2016-manifest.json');
 const originalManifestRaw=Buffer.from(manifest.originalManifestRawBase64,'base64');
 assert.equal(sha(originalManifestRaw),'cc27a3e4b8fc71957827f96c970bd67c62ca859c300930e54fa7636574dffdf7');
 const originalManifest=JSON.parse(originalManifestRaw),rawFiles=new Map(),vendorFiles=new Map(),originals=new Map();
 for(const[key,count,dest]of [['initialBundle',1431,rawFiles],['vendorBundle',105,vendorFiles]]){
  const entry=manifest[key],compressed=await bytes(entry.path);assert.equal(sha(compressed),FROZEN[entry.path]);assert.equal(sha(compressed),entry.sha256);
  const bundle=JSON.parse(gunzipSync(compressed));assert.equal(bundle.corpusId,'ioi-2016');assert.equal(bundle.files.length,count);
  for(const item of bundle.files){assert(!path.isAbsolute(item.path)&&!item.path.split('/').some(p=>p==='..'||p.startsWith('.env')));assert(!dest.has(item.path));
   const value=Buffer.from(item.rawBase64,'base64');assert.equal(sha(value),item.sha256,item.path);dest.set(item.path,value);}
 }
 for(const name of Object.keys(FROZEN).filter(f=>/ioi-2016-original-.*\.gz$/.test(f))){const compressed=await bytes(name);assert.equal(sha(compressed),FROZEN[name]);originals.set(path.basename(name).replace(/^ioi-2016-original-/,'').replace(/\.gz$/,''),gunzipSync(compressed));}
 for(const item of manifest.originalArtifacts){assert(originals.has(item.artifact));assert.equal(sha(originals.get(item.artifact)),item.uncompressedSha256);}
 const original=JSON.parse(originals.get('audit.json')),audit=await json(auditFile);
 return {manifest,originalManifest,originalManifestRaw,rawFiles,vendorFiles,originals,original,audit};
})();}
const options=node=>node.options??Object.keys(node.answers??{}).map(id=>({id,label:({yes:'はい',no:'いいえ',unknown:'わからない'})[id]??id}));
function replay(graphs,entry,choices){
 const by=new Map(graphs.map(g=>[g.id,g]));let g=by.get(entry),n=g.nodes.find(n=>n.id===g.root),used=0;const steps=[],seen=new Set(),routes=[];
 assert.equal(g.entry,true);
 for(;;){const key=JSON.stringify([g.id,n.id,used]);assert(!seen.has(key));seen.add(key);
  if(n.type==='route'){routes.push(g.id+'/'+n.id);g=by.get(n.graph);n=g.nodes.find(n=>n.id===g.root);continue;}
  if(n.type!=='question'||used===choices.length)break;
  const a=choices[used++],target=n.answers[a];const label=options(n).find(o=>o.id===a)?.label;assert(label);
  steps.push({graphId:g.id,nodeId:n.id,question:n.title,answer:a,answerLabel:label,target});n=g.nodes.find(n=>n.id===target);assert(n);
 }
 assert.equal(used,choices.length);
 return {steps,routeBoundaries:routes,reached:{graphId:g.id,nodeId:n.id,type:n.type,title:n.title,options:options(n),techniques:n.techniques??[],conditions:n.conditions??[]}};
}
async function collection(prefix){const names=await readdir(path.join(site,'data'));return(await Promise.all(names.filter(n=>n.startsWith(prefix)&&n.endsWith('.json')).map(n=>liveJson('data/'+n)))).flat();}
let productPromise;
function product(){return productPromise??=(async()=>{
 const [{assessCorpus},{validateSite},{compileLocalModules}]=await Promise.all(['scripts/audit-coverage.mjs','scripts/validate.mjs','scripts/local-modules.mjs'].map(f=>import(pathToFileURL(path.join(site,f)))));
 const folder=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2016-live-test-'));
 try{await compileLocalModules(site,folder);const flow=await import(pathToFileURL(path.join(folder,'flow.js')));
  const [techniques,references,walks,plan,preflight]=await Promise.all([collection('techniques-'),collection('references-'),liveJson('data/problem-walks.json'),liveJson('data/coverage-plan.json'),validateSite(site)]);
  const entries=new Set(flow.entryGraphs.map(g=>g.id));const data={techniques,references,walks,preflightPassed:preflight.errors.length===0,isWalkValid(walk,id){
   if(!entries.has(walk.entryGraphId)||!Array.isArray(walk.choices))return false;
   try{const got=flow.walkFromRoot(walk.choices,walk.entryGraphId);return got.consumed===walk.choices.length&&got.current.type==='result'&&got.current.techniques.includes(id)
    &&JSON.stringify(got.steps.map(({graph,node,answer})=>({graph,node,answer})))===JSON.stringify(walk.steps);}catch{return false;}
  }};
  return {assessCorpus,validateSite,flow,data,plan,preflight};
 }finally{await rm(folder,{recursive:true,force:true});}
})();}

// All file contents are preserved. The fixed gzip SHA and per-file SHA are both
// checked before decoding historic JSON or compiling a frozen fence.
test('all1431 initial raw bytes,504 full articles and separate105 vendor bytes are permanently recoverable',async()=>{
 const e=await evidence(),m=e.manifest,o=e.originalManifest;
 assert.equal(sha(await bytes('research/snapshots/ioi-2016-manifest.json')),FROZEN['research/snapshots/ioi-2016-manifest.json']);
 assert.equal(m.initialRawFiles,1431);assert.equal(m.coreRawFiles,959);assert.equal(m.publicRawFiles,472);assert.equal(m.fullMdxCount,504);
 for(const flag of ['allHistoricalInitialRawFilesPermanentlyStored','allHistoricalMdxPermanentlyStored','retentionExtendedBeyondDraftProposal'])assert.equal(m[flag],true);
 assert.deepEqual(m.initialCounts,{allTechniqueMdx:504,metadataRecords:504,referenceRecords:525,flowcharts:471,walks:525,oldCorpusAudits:9});
 assert.deepEqual(m.initialCounts,o.rawCounts);assert.equal(o.publicEpochSameAsCore,true);
 assert.deepEqual([...e.rawFiles].map(([p,b])=>[p,sha(b)]),Object.entries(o.fullRawHashes));
 for(const f of ['SHA256SUMS','CORE_SHA256SUMS','hashes-before.json','hashes-after.json','vendor-hashes-before.json','vendor-hashes-after.json'])assert.equal(sha(Buffer.from(m[f].rawBase64,'base64')),m[f].sha256);
 const before=JSON.parse(Buffer.from(m['hashes-before.json'].rawBase64,'base64')),after=JSON.parse(Buffer.from(m['hashes-after.json'].rawBase64,'base64'));
 assert.deepEqual(before,after);assert.deepEqual(before,o.fullRawHashes);
 const ledger=Buffer.from(m.SHA256SUMS.rawBase64,'base64');assert.equal(sha(ledger),'dd7151810d712521a5f3f19c206eecb7630c3b9688575c6243dee4b170992a56');
 assert.deepEqual(Object.fromEntries(ledger.toString().trimEnd().split('\n').map(s=>[s.slice(66),s.slice(0,64)])),before);
 assert.equal([...e.rawFiles.keys()].filter(p=>p.startsWith('public/')).length,472);
 assert.equal([...e.rawFiles.keys()].filter(p=>/^src\/content\/docs\/techniques\/.*\.mdx$/.test(p)).length,504);
 const vb=JSON.parse(Buffer.from(m['vendor-hashes-before.json'].rawBase64,'base64')),va=JSON.parse(Buffer.from(m['vendor-hashes-after.json'].rawBase64,'base64'));
 assert.deepEqual(vb,va);assert.equal(e.vendorFiles.size,105);assert.deepEqual(Object.fromEntries([...e.vendorFiles].map(([p,b])=>[p,sha(b)])),vb);
 for(const p of e.vendorFiles.keys())assert(!e.rawFiles.has(p));assert.match(m.vendorBundle.epoch,/later/);assert.match(m.vendorBundle.epoch,/no initialSVG/);
});

test('every original gzip is fixed and the normalized audit changes only disclosed paths and retention fields',async()=>{
 const e=await evidence();for(const[file,hash]of Object.entries(FROZEN))if(/snapshots\//.test(file))assert.equal(sha(await bytes(file)),hash,file);
 assert.equal(sha(e.originals.get('selection.json')),'3505ba77043d0ff594b6b66fe763cf9e7b1cd97082a79ff4dc30cbca809c3350');
 assert.equal(sha(e.originals.get('audit.json')),'d69b49d6672dcbf4145ef36c7d265bc135fb848a3561f4523677bd76d7318b83');
 assert.equal(sha(e.originals.get('independent-review.json')),'460cf6a1e39f0d710e9021ce5d96c997972dd2f1b807e7adfa5d3443ae341a29');
 const original=e.original,audit=e.audit;
 assert.deepEqual(projection(audit,omit(original,['snapshot','validation','records'])),omit(original,['snapshot','validation','records']));
 assert.equal(audit.records.length,6);audit.records.forEach((r,i)=>assert.deepEqual(projection(r,original.records[i]),original.records[i]));
 const snap=structuredClone(audit.snapshot);assert.equal(snap.snapshotRoot,'research/snapshots/ioi-2016-manifest.json');snap.snapshotRoot=snap.historicalSnapshotRoot;
 assert.deepEqual(projection(snap,original.snapshot),original.snapshot);
 assert.equal(audit.snapshot.all504MdxPermanentlyRetained,true);assert.equal(audit.snapshot.allInitialRawPermanentlyRetained,true);
 const normal=await json('research/probes/ioi-2016-probe-normalizations.json');
 const v=structuredClone(audit.validation);for(const key of ['probeFile','probeSha256','scopeChecker','actualFrozenRuntimeReplay','independentRawWalker','manualCommand','probeOutputFile'])v[key]=original.validation[key];
 assert.deepEqual(projection(v,original.validation),original.validation);
 assert.equal(audit.validation.probeFile,'research/probes/ioi-2016-research-checks.py');assert.equal(audit.validation.probeSha256,normal['ioi-2016-research-checks.py'].normalizedSha256);
 assert.equal(audit.validation.originalProbeSha256,original.validation.probeSha256);assert.equal(canonical(Object.fromEntries(NORMALIZED_VALIDATION.keys.map(k=>[k,audit.validation[k]]))),NORMALIZED_VALIDATION.sha256,'all initial normalized validation values stay fixed');assert.equal(audit.snapshot.permanentInitialRawArchive,e.manifest.initialBundle.path);assert.equal(audit.snapshot.permanentLaterVendorArchive,e.manifest.vendorBundle.path);assert.equal(sha(await bytes('research/ioi-2016-audit-notes.md')),FROZEN['research/ioi-2016-audit-notes.md']);
 const proposal=JSON.parse(e.originals.get('registration-proposal.json'));assert.equal(proposal.permanentSnapshotPlan.all504MdxPermanentlyStored,false);
 assert.equal(e.manifest.retentionExtendedBeyondDraftProposal,true);
});

test('the selection predates matching and fixes all six identities,exact dates,null difficulty,numeric bounds and research-only flags',async()=>{
 const {audit,original,originals}=await evidence(),selection=await json('research/snapshots/ioi-2016-selection.json');
 assert.deepEqual(selection,JSON.parse(originals.get('selection.json')));assert.equal(selection.fixedBeforeTechniqueSearch,true);assert.equal(selection.solutionsAndCoverageNotYetAssessedAtSelection,true);
 assert.deepEqual(selection.problems.map(r=>r.officialTaskId),tasks);assert.equal(selection.count,6);
 assert.deepEqual(audit.selection,original.selection);assert.deepEqual(audit.status,original.status);
 audit.records.forEach((r,i)=>{
  assert.equal(r.problemId,ids[i]);assert.equal(r.officialTaskId,tasks[i]);assert.equal(r.day,i<3?1:2);assert.equal(r.date,i<3?'2016-08-14':'2016-08-16');
  assert.equal(r.datePrecision,'day');assert.equal(r.exactDateVerified,true);assert.equal(r.difficulty,null);assert.equal(r.constraints.numericBoundsVerified,true);assert.equal(r.constraints.cppHeadersRetrieved,false);
  assert.equal(r.technicalFindings.chosenFullSolutionVerified,true);assert.equal(r.technicalFindings.fullImplementationValidated,false);assert.equal(r.completedApiCoverage,false);
  assert.equal(r.classification,'missing-technique');assert.equal(r.verification,'independent-analysis');assert.deepEqual(r.expectedTechniqueIds,[]);assert.equal(r.gap.implementationNeeded,true);
  assert.deepEqual(r.technicalFindings.unconfirmedDetails,[]);assert.equal(r.materialStatus.solution,'retrieved-and-reviewed');assert.equal(r.materialStatus.officialEditorialVerified,true);
 });
 const mol=audit.records[0].constraints;assert.equal(mol.apiEditions.jpCommitteeGeneric,'int[] solve(int l,int u,int[] w)');assert.equal(mol.apiEditions.officialArchiveApiGeneric,'int[] find_subset(int l,int u,int[] w)');assert.match(mol.apiEditions.chronology,/not verified/);
 assert.deepEqual(audit.records[2].constraints.values.N,[2,1000000]);assert.deepEqual(audit.records[3].constraints.values.K,[1,100]);
 assert.deepEqual(audit.records[4].constraints.values.strictFullBudget,{N:128,w:896,r:896});assert.deepEqual(audit.records[5].constraints.values.M,[1,1000000]);
 assert.equal(audit.status.solutionReviewedCount,6);assert.equal(audit.status.coveredCount,0);assert.equal(audit.status.fullImplementationValidatedCount,0);
 for(const flag of ['fixedCorpusCoverageComplete','globalCoverageComplete','globalLearningComplete','articleResolutionComplete'])assert.equal(audit.status[flag],false);
});

test('all15 roots,six frozen traces/eight full answer labels and525 previous walks retain actual stops and labels',async()=>{
 const e=await evidence(),graphs=JSON.parse(e.rawFiles.get('data/flows.json')),routes=JSON.parse(e.originals.get('routes.json'));
 const roots=graphs.filter(g=>g.entry).map(g=>g.id);assert.equal(roots.length,15);assert.equal(graphs.length,471);let answers=0;
 for(const r of e.original.records){const got=replay(graphs,r.entryGraphId,r.choices),expected=routes[r.officialTaskId];assert.deepEqual(got.steps,expected.steps);assert.deepEqual(got.reached,r.initialReached);
  assert.deepEqual(got.reached,expected.reached);assert.deepEqual(got.routeBoundaries,expected.routeBoundaries);assert.equal(canonical(got.steps),r.navigationReplay.stepsSha256);
  assert.equal(got.reached.graphId,r.gap.firstMissingGraphId);assert.equal(got.reached.nodeId,r.gap.firstMissingNodeId);assert.equal(got.reached.title,r.gap.currentQuestion);assert.deepEqual(got.reached.options,r.gap.currentOptions);
  assert.deepEqual(r.navigationReplay.all15EntryDomainsConsidered,roots);answers+=got.steps.length;
 }assert.equal(answers,8);assert.deepEqual(routes.messy.reached.techniques,['interactive']);assert.equal(e.original.records[4].completedApiCoverage,false);
 const currentGraphs=await liveJson('data/flows.json'),currentWalks=await liveJson('data/problem-walks.json'),oldWalks=JSON.parse(e.rawFiles.get('data/problem-walks.json'));assert.equal(oldWalks.length,525);assert.deepEqual(currentWalks.slice(0,oldWalks.length),oldWalks,'all525 original record fields and order');
 let steps=0;for(const r of oldWalks){const old=replay(graphs,r.entryGraphId,r.choices),live=replay(currentGraphs,r.entryGraphId,r.choices);assert.deepEqual(live,old,r.problemId);
  old.steps.forEach((s,i)=>assert.deepEqual(omit(s,['question','answerLabel','target']),{graphId:r.steps[i].graph,nodeId:r.steps[i].node,answer:r.steps[i].answer}));steps+=old.steps.length;
 }assert.equal(steps,2781);
 // Existing graph/node fields and relative ordering survive appended branches.
 for(const g of graphs){const now=currentGraphs.find(x=>x.id===g.id);assert(now);assert.deepEqual(projection(omit(now,['nodes']),omit(g,['nodes'])),omit(g,['nodes']));
  assert.deepEqual(now.nodes.filter(n=>g.nodes.some(o=>o.id===n.id)).map(n=>n.id),g.nodes.map(n=>n.id));
  for(const n of g.nodes){const z=now.nodes.find(q=>q.id===n.id);assert(z);assert.deepEqual(projection(omit(z,['options','answers']),omit(n,['options','answers'])),omit(n,['options','answers']));
   if(n.options)assert.deepEqual(z.options.filter(a=>n.options.some(b=>b.id===a.id)),n.options);
   if(n.answers){assert.deepEqual(Object.keys(z.answers).filter(a=>Object.hasOwn(n.answers,a)),Object.keys(n.answers));for(const a in n.answers)assert.deepEqual(z.answers[a],n.answers[a]);}
  }
 }
});

test('nineteen complete frozen articles and fences retain their exact scope and normalized algorithm bodies',async()=>{
 const e=await evidence(),seen=new Set();for(const row of e.original.records)for(const r of row.relatedArticleReview){
  const raw=e.rawFiles.get(r.file);assert(raw);assert.equal(sha(raw),r.sha256);const blocks=[...raw.toString().matchAll(/^```cpp\s*\n([\s\S]*?)^```\s*$/gm)];assert.equal(blocks.length,1);assert.equal(sha(blocks[0][1]),r.cppFenceSha256);
  assert.equal(r.originalFullRangeApiReusable,false);assert.equal(r.fullImplementationRevalidatedForOriginal,false);assert(r.scopeMismatch.length>0);seen.add(r.techniqueId);
  for(const m of r.metadataSourceFiles)assert.equal(sha(e.rawFiles.get(m.file)),m.sha256);
 }assert.equal(seen.size,19);
 for(const[file,hash]of Object.entries(FROZEN))if(file.startsWith('research/probes/'))assert.equal(sha(await bytes(file)),hash,file);
 // Parse both Python sources without executing their algorithm or bootstrap.
 const source=await bytes('research/probes/ioi-2016-research-checks.py'),old=e.originals.get('probe.py');
 const folder=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2016-ast-'));
 try{await writeFile(path.join(folder,'old.py'),old);await writeFile(path.join(folder,'new.py'),source);
  const ast=`import ast,sys,json\na=ast.parse(open(sys.argv[1]).read());b=ast.parse(open(sys.argv[2]).read())\nf=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='main'}\nassert f(a)==f(b)\nprint(json.dumps({'unchangedTopLevelFunctionsAndClasses':len(f(a))}))`;
  const r=await run('python3',['-c',ast,path.join(folder,'old.py'),path.join(folder,'new.py')],{encoding:'utf8'});assert(JSON.parse(r.stdout).unchangedTopLevelFunctionsAndClasses==19);
 }finally{await rm(folder,{recursive:true,force:true});}
});

test('permanent manual probes restore every raw byte and reproduce math,raw routes,actual runtime and19 component scopes',async()=>{
 // Python stdlib relays the actual Node command because nested Node stdout
 // capture is unreliable in this environment; source and assertions are unchanged.
 const e=await evidence();const execute=async file=>{const nodeWrapper="import subprocess,sys; r=subprocess.run(['node',sys.argv[1]],capture_output=True,text=True); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); sys.exit(r.returncode)";const args=file.endsWith('.mjs')?['-B','-c',nodeWrapper,path.join(root,file)]:['-B',path.join(root,file)];const r=await run('python3',args,{encoding:'utf8',maxBuffer:8*1024*1024,timeout:120000});assert.equal(r.stderr,'');assert(r.stdout.trim().startsWith('{'),'actual child JSON output '+file);return JSON.parse(r.stdout);};
 const normalized=await execute('research/probes/ioi-2016-research-checks.py'),initial=JSON.parse(e.originals.get('probe.json'));
 assert.deepEqual(omit(normalized,['elapsedSeconds']),omit(initial,['elapsedSeconds']));assert.equal(normalized.productionImplementationValidated,false);
 const independent=await execute('research/probes/ioi-2016-independent-checks.py'),expected=JSON.parse(e.originals.get('independent-probe-results.json'));
 assert.deepEqual(omit(independent,['elapsedSeconds']),omit(expected,['elapsedSeconds']));assert.equal(independent.additionalMath.productionApiValidated,false);assert.equal(independent.additionalMath.sanitizerRun,false);
 assert.deepEqual(await execute('research/probes/ioi-2016-root-replay.py'),JSON.parse(e.originals.get('routes.json')));
 assert.deepEqual(await execute('research/probes/ioi-2016-frozen-runtime.mjs'),JSON.parse(e.originals.get('runtime-replay.json')));
 assert.deepEqual(await execute('research/probes/ioi-2016-frozen-scope.py'),JSON.parse(e.originals.get('scope-checks.json')));
 assert.equal(normalized.molecules.allSubsetAssignmentsRepresented,471040);assert.equal(normalized.railroad.literalSectionPermutations,1174270);assert.equal(normalized.shortcut.decisionThresholdsCompared,21861);
 assert.equal(normalized.paint.allConsistentCluesAndPartialRowsN1to8,62701);assert.equal(normalized.messy.allPermutationsN1_2_4_8,40347);assert.equal(normalized.aliens.literalSquarePhotoSubsets,437);
});

test('independent reviews and the accepted schema keep research6 distinct from zero completed APIs and initial coverage',async()=>{
 const e=await evidence(),review=await json('research/probes/ioi-2016-independent-review.json');assert.equal(review.status,'passed-initial-fixed-corpus-research-audit');assert.deepEqual(review.materialIssues,[]);assert.deepEqual(review.unconfirmedRequiredLemmas,[]);
 const {isCorpusStatementReviewed,isCorpusSolutionReviewed}=await import(pathToFileURL(path.join(site,'scripts/lib/corpus-progress.mjs')));
 assert.equal(e.original.records.filter(isCorpusStatementReviewed).length,6);assert.equal(e.original.records.filter(isCorpusSolutionReviewed).length,6);
 for(const row of e.original.records)for(const mutation of [{reviewStatus:'unconfirmed'},{materialStatus:{...row.materialStatus,solution:'retrieved-partially-reviewed'}},{verification:'tag-guess'},{collectionStatus:'statement-only'}])assert.equal(isCorpusSolutionReviewed({...row,...mutation}),false);
 const p=await product(),proposal=JSON.parse(e.originals.get('registration-proposal.json')),selection={...proposal.planCorpusEntry,cutoff:e.original.cutoff};
 const initial=p.assessCorpus(e.original,p.data,selection);assert.deepEqual(initial.errors,[]);assert.equal(initial.reviewedProblems,6);assert.equal(initial.coveredProblems,0);assert.equal(initial.researchComplete,true);assert.equal(initial.coverageComplete,false);
 const fake=structuredClone(e.original);fake.records[0].resolution={status:'verified',techniqueIds:['ioi2016-nonexistent-production-api']};
 assert.equal(p.assessCorpus(fake,p.data,selection).coveredProblems,0);assert.equal(p.assessCorpus(fake,{...p.data,isWalkValid:()=>true},selection).coveredProblems,0);
});

test('all old fields of nine earlier audits survive while genuinely new resolution/review fields remain allowed',async()=>{
 const e=await evidence(),prior=[...e.rawFiles].filter(([file])=>file.startsWith('data/corpus-audits/'));assert.equal(prior.length,9);let oldRes=0,addedRes=0;
 for(const[file,raw]of prior){const old=JSON.parse(raw),now=await liveJson(file);assert.deepEqual(projection(omit(now,['records']),omit(old,['records'])),omit(old,['records']),file);assert.equal(now.records.length,old.records.length);
  old.records.forEach((r,i)=>{assert.deepEqual(projection(now.records[i],r),r,file+':'+r.problemId);oldRes+=Number(Object.hasOwn(r,'resolution'));addedRes+=Number(!Object.hasOwn(r,'resolution')&&Object.hasOwn(now.records[i],'resolution'));});
 }
 assert(oldRes>0);assert(addedRes>=3,'post-baseline Train,Books,Simurgh resolutions are retained; Wiring already existed');const ioi2017=await liveJson('data/corpus-audits/ioi-2017.json');for(const task of ['wiring','train','books','simurgh'])assert.equal(ioi2017.records.find(r=>r.officialTaskId===task).resolution?.status,'verified');
 // Prove the projection policy permits a newly appended Prize proof without
 // permitting a rewrite of its original unconfirmed status or source facts.
 const old=JSON.parse(e.rawFiles.get('data/corpus-audits/ioi-2017.json')),prize=old.records.find(r=>r.officialTaskId==='prize');assert(prize);
 const later={...structuredClone(prize),subsequentSolutionReviews:[{reviewStatus:'verified',verification:'independent-analysis'}]};assert.deepEqual(projection(later,prize),prize);
 later.reviewStatus='verified';assert.notDeepEqual(projection(later,prize),prize);
});

test('the actual content preflight rejects an empty visible fence and gates real corpus production coverage',async()=>{
 const p=await product();assert.deepEqual(p.preflight.errors,[]);const mirror=await mkdtemp(path.join(tmpdir(),'flowchartcp-ioi2016-invalid-'));
 const relative='src/content/docs/techniques/aliens-trick.mdx',original=await readFile(path.join(site,relative)),oldHash=sha(original);
 async function linkedTree(src,dst){await mkdir(dst,{recursive:true});for(const entry of await readdir(src,{withFileTypes:true})){if(entry.name.startsWith('.'))continue;const a=path.join(src,entry.name),b=path.join(dst,entry.name);if(entry.isDirectory())await linkedTree(a,b);else await symlink(a,b);}}
 try{await linkedTree(path.join(site,'src'),path.join(mirror,'src'));for(const dir of ['data','public','research','vendor'])await symlink(path.join(site,dir),path.join(mirror,dir),'dir');
  const clean=await p.validateSite(mirror);assert.deepEqual(clean.errors,[]);
  const target=path.join(mirror,relative);await unlink(target);const broken=original.toString().replace(/^```cpp\s*\n[\s\S]*?^```\s*$/m,'```cpp\n```');assert.notEqual(broken,original.toString());await writeFile(target,broken);
  const invalid=await p.validateSite(mirror);assert(invalid.errors.some(s=>s.includes('aliens-trick')&&s.includes('再利用可能な実装例')));
  let realCovered=0;for(const c of p.plan.corpora){const a=await liveJson(c.auditFile),selection={...c,cutoff:p.plan.cutoff};const live=p.assessCorpus(a,p.data,selection);assert.deepEqual(live.errors,[]);realCovered+=live.coveredProblems;
   assert.equal(p.assessCorpus(a,{...p.data,preflightPassed:invalid.errors.length===0},selection).coveredProblems,0);}
  assert(realCovered>0,'gate tested against actual previously resolved source mappings');
 }finally{await rm(mirror,{recursive:true,force:true});}
 assert.equal(sha(await readFile(path.join(site,relative))),oldHash);
});

test('production adds the tenth fixed corpus with six pending precise gaps and accepts only actual future resolution evidence',{skip:stage},async()=>{
 const e=await evidence(),p=await product(),selection=p.plan.corpora.find(c=>c.id==='ioi-2016');assert(selection);assert.equal(p.plan.corpora[9].id,'ioi-2016');assert(p.plan.corpora.length>=10);
 assert.equal(selection.expectedProblems,6);assert.equal(selection.auditFile,auditFile);assert.deepEqual(selection.fixedProblems.map(r=>r.problemId),ids);assert.equal(e.audit.cutoff,p.plan.cutoff);
 const gaps=p.plan.knownGaps.filter(g=>g.discoveredBy==='ioi-2016');assert.equal(gaps.length,6);
 const {readCorpusProgress}=await import(pathToFileURL(path.join(site,'scripts/lib/corpus-progress.mjs')));
 const progress=await readCorpusProgress(site,await liveJson('data/sources.json')),selected=progress.filter(r=>ids.includes(r.problemId));assert.equal(selected.length,6);assert.equal(selected.filter(r=>r.statementVerified).length,6);assert.equal(selected.filter(r=>r.solutionVerified).length,6);
 const ledger=await liveJson('data/research-ledger.json');assert.equal(ledger.corpusStatementsReviewed,progress.filter(r=>r.statementVerified).length);assert.equal(ledger.corpusSolutionsReviewed,progress.filter(r=>r.solutionVerified).length);
 const fixed={...selection,cutoff:p.plan.cutoff},live=p.assessCorpus(e.audit,p.data,fixed);assert.deepEqual(live.errors,[]);assert.equal(live.reviewedProblems,6);
 for(const row of e.audit.records){const gap=gaps.find(g=>g.id===row.gap.id);assert(gap);assert.equal(gap.problemId,row.problemId);assert.deepEqual(gap.techniqueIds,row.gap.neededTechniqueIds);
  const result=live.records.find(r=>r.problemId===row.problemId);assert(result);
  const actualWalks=p.data.walks.filter(w=>w.problemId===row.problemId&&String(w.source).toLowerCase()==='ioi');
  if(row.resolution!==undefined||gap.state==='resolved'||actualWalks.length){
   assert.equal(result.resolved,true,'genuine target/reference/steps required');assert.equal(gap.state,'resolved');assert.equal(row.resolution?.status,'verified');assert(actualWalks.length);
   for(const id of row.gap.neededTechniqueIds)assert(row.resolution.techniqueIds.includes(id));
   for(const id of row.resolution.techniqueIds){assert.equal(p.data.techniques.find(t=>t.id===id)?.status,'reviewed');assert((await readFile(path.join(site,'src/content/docs/techniques/'+id+'.mdx'))).length>0);
    assert(p.data.references.some(r=>r.techniqueId===id&&r.problemId===row.problemId&&r.url===row.statementUrl));assert(actualWalks.some(w=>w.expectedTechniqueIds.includes(id)&&p.data.isWalkValid(w,id)));}
   for(const mutation of [{...p.data,preflightPassed:false},{...p.data,walks:p.data.walks.filter(w=>w.problemId!==row.problemId)},{...p.data,references:p.data.references.filter(r=>r.problemId!==row.problemId)},{...p.data,techniques:p.data.techniques.filter(t=>!row.resolution.techniqueIds.includes(t.id))}])assert.equal(p.assessCorpus(e.audit,mutation,fixed).records.find(r=>r.problemId===row.problemId).resolved,false);
   const noResolution=structuredClone(e.audit);delete noResolution.records.find(r=>r.problemId===row.problemId).resolution;assert.equal(p.assessCorpus(noResolution,p.data,fixed).records.find(r=>r.problemId===row.problemId).resolved,false);
  }else{assert.equal(gap.state,'pending');assert.equal(result.resolved,false);}
 }
});
