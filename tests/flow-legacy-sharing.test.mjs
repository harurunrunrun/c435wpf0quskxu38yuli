import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const frozen=JSON.parse(await readFile(path.join(site,'tests/fixtures/flow-legacy-sharing.json'),'utf8'));
let temporary;
const implementation=(async()=>{
  temporary=await mkdtemp(path.join(tmpdir(),'flowchartcp-legacy-sharing-'));
  await compileLocalModules(site,temporary);
  return import(pathToFileURL(path.join(temporary,'flow.js')).href);
})();
after(async()=>{await implementation;await rm(temporary,{recursive:true,force:true});});

// This is the pre-split URL format, deliberately independent of the new
// serializer and of legacyEntryChoices. Fixtures came from the old graph data.
function oldHash(state) {
  const short={yes:'y',no:'n',unknown:'u'};
  const steps=state.answers.map(answer=>short[answer]??`c:${encodeURIComponent(answer)}`).join(',');
  return `#flow=${encodeURIComponent(state.graph)}&steps=${steps}${state.trail?.length?`&trail=${encodeURIComponent(JSON.stringify(state.trail))}`:''}`;
}
function key(state) {return `${state.graph}:${JSON.stringify(state.answers)}`;}
function describe(record) {return record.problemId?`${record.case}/${record.problemId}`:key(record.state);}
function assertCurrent(flow,state,record) {
  const node=flow.evaluateState(state).current,label=describe(record);
  assert.equal(node.id,record.expected.id,`${label}: current node`);
  assert.equal(node.type,record.expected.type,`${label}: node type`);
  assert.deepEqual(node.techniques??[],record.expected.techniques,`${label}: candidate techniques`);
  if(record.expected.routeGraph) assert.equal(node.graph,record.expected.routeGraph,`${label}: route destination`);
  assert.equal(flow.getFlowDomainId(state),record.domain,`${label}: originating domain`);
}
function assertCanonicalTrail(flow,state,label) {
  const known=new Set(flow.graphs.map(graph=>graph.id));
  const contexts=[...(state.trail??[]),{graph:state.graph,answers:state.answers}];
  for(let i=0;i<contexts.length;++i) {
    const context=contexts[i];
    assert(known.has(context.graph),`${label}: history graph exists`);
    const graph=flow.getGraph(context.graph);
    let node=graph.nodes.find(node=>node.id===graph.root);
    for(const answer of context.answers) {
      assert.equal(node.type,'question',`${label}: history continues only through questions`);
      assert(flow.getNodeOptions(node).some(option=>option.id===answer),`${label}: canonical history answer ${context.graph}/${node.id}/${answer}`);
      node=graph.nodes.find(candidate=>candidate.id===node.answers[answer]);
      assert(node,`${label}: canonical history target`);
    }
    if(i<contexts.length-1) {
      assert.equal(node.type,'route',`${label}: history ends at a route`);
      assert.equal(node.graph,contexts[i+1].graph,`${label}: contiguous graph history`);
    }
  }
}
function assertReload(flow,state,record) {
  assertCanonicalTrail(flow,state,describe(record));
  assert.deepEqual(flow.sanitizeState(state),state,`${describe(record)}: canonical normalization is idempotent`);
  const hash=flow.serializeFlowHash(state);
  assert.deepEqual(flow.parseFlowHash(hash),state,`${describe(record)}: canonical URL reload`);
  assertCurrent(flow,flow.parseFlowHash(hash),record);
}

test('frozen history fixtures include every old local prefix and all 404 completed problem walks',()=>{
  assert.equal(frozen.version,1);
  assert.equal(frozen.originalGraphCount,230);
  assert.equal(frozen.originalWalkCount,404);
  assert.equal(frozen.localPrefixes.length,593);
  assert.equal(frozen.completedWalks.length,404);
  const prefixes=new Map(frozen.localPrefixes.map(record=>[key(record.state),record]));
  assert.equal(prefixes.size,frozen.localPrefixes.length);
  assert.deepEqual(Object.fromEntries(frozen.splitGraphIds.map(id=>[id,frozen.localPrefixes.filter(record=>record.domain===id).length])),{geometry:179,dp:94,graphs:90,math:230});
  for(const id of frozen.splitGraphIds) assert(prefixes.has(key({graph:id,answers:[]})),`${id}: old empty answer prefix`);
  for(const record of frozen.localPrefixes) {
    assert.equal(oldHash(record.state),record.hash);
    for(const answer of record.expected.answers??[]) assert(prefixes.has(key({...record.state,answers:[...record.state.answers,answer]})),`${key(record.state)}: complete old branch ${answer}`);
  }
  for(const record of frozen.completedWalks) {
    assert.equal(oldHash(record.state),record.hash);
    assert.equal(new URL(record.url).hash,record.hash);
    assert.equal(record.expected.type,'result');
    for(const technique of record.expectedTechniqueIds) assert(record.expected.techniques.includes(technique));
  }
});

test('all 593 old local URL prefixes retain their current question, route or result after the split',async()=>{
  const flow=await implementation;
  for(const record of frozen.localPrefixes) {
    const state=flow.parseFlowHash(record.hash);
    assertCurrent(flow,state,record);
    assert.deepEqual(flow.sanitizeState(record.state),state,`${describe(record)}: object and URL migration agree`);
    assertReload(flow,state,record);
  }
});

test('all 404 completed shared URLs retain candidates, canonical history, domain and usable backtracking',async()=>{
  const flow=await implementation;
  for(const record of frozen.completedWalks) {
    let state=flow.parseFlowHash(new URL(record.url).hash);
    assertCurrent(flow,state,record);
    assert.deepEqual(flow.sanitizeState(record.state),state,`${describe(record)}: complete state migration`);
    assertReload(flow,state,record);
    const oldChoices=[...(record.state.trail??[]),record.state].flatMap(context=>context.answers);
    const walked=flow.walkFromRoot(oldChoices,record.domain);
    assert.equal(walked.consumed,oldChoices.length,`${describe(record)}: all old choices consumed`);
    assert.equal(walked.current.id,record.expected.id,`${describe(record)}: old walk current node`);
    assert.equal(walked.current.type,record.expected.type,`${describe(record)}: old walk node type`);
    assert.deepEqual(walked.current.techniques??[],record.expected.techniques,`${describe(record)}: old walk candidates`);
    const canonicalSteps=[...(state.trail??[]),state].flatMap(context=>{
      const graph=flow.getGraph(context.graph),steps=[];
      let node=graph.nodes.find(node=>node.id===graph.root);
      for(const answer of context.answers) {
        const target=node.answers[answer];steps.push({graph:graph.id,node:node.id,answer,target});
        node=graph.nodes.find(node=>node.id===target);
      }
      return steps;
    });
    assert.deepEqual(walked.steps,canonicalSteps,`${describe(record)}: object/URL/walk migration agree`);
    const weight=value=>value.answers.length+(value.trail??[]).reduce((sum,item)=>sum+item.answers.length+1,0);
    for(let remaining=weight(state)+1;weight(state)>0;--remaining) {
      assert(remaining>0,`${describe(record)}: finite backtracking`);
      const previous=flow.backFlowState(state);
      assert(weight(previous)<weight(state),`${describe(record)}: backtracking removes a history step`);
      assertCanonicalTrail(flow,previous,describe(record));
      assert.equal(flow.getFlowDomainId(previous),record.domain,`${describe(record)}: backtracking preserves domain`);
      assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(previous)),previous,`${describe(record)}: backtracked state can be shared`);
      state=previous;
    }
    assert.deepEqual(state,flow.initialState(record.domain),`${describe(record)}: backtracking reaches its field root`);
  }
});

test('split entry metadata targets canonical category routes without changing the 15 fields',async()=>{
  const flow=await implementation;
  assert.equal(flow.entryGraphs.length,15);
  for(const id of frozen.splitGraphIds) {
    const graph=flow.getGraph(id),root=graph.nodes.find(node=>node.id===graph.root);
    assert(graph.legacyEntryChoices&&Object.keys(graph.legacyEntryChoices).length>0,`${id}: migration metadata`);
    for(const [oldAnswer,target] of Object.entries(graph.legacyEntryChoices)) {
      assert(frozen.localPrefixes.some(record=>record.state.graph===id&&record.state.answers.length===1&&record.state.answers[0]===oldAnswer),`${id}: migration starts from an actual old answer`);
      assert(flow.getNodeOptions(root).some(option=>option.id===target.answer),`${id}/${oldAnswer}: canonical category choice`);
      const route=graph.nodes.find(node=>node.id===root.answers[target.answer]);
      assert.equal(route.type,'route',`${id}/${oldAnswer}: category route`);
      assert.equal(route.graph,target.graph,`${id}/${oldAnswer}: metadata matches route`);
      assert(flow.graphs.some(graph=>graph.id===target.graph),`${id}/${oldAnswer}: category graph exists`);
    }
  }
});

test('invalid trailing answers and malformed old histories remain safely truncated',async()=>{
  const flow=await implementation;
  for(const record of frozen.localPrefixes) {
    const expected=flow.parseFlowHash(record.hash);
    const corrupt={...record.state,answers:[...record.state.answers,'__invalid_old_answer__','yes']};
    assert.deepEqual(flow.parseFlowHash(oldHash(corrupt)),expected,`${describe(record)}: invalid old answer suffix`);
    assert.deepEqual(flow.sanitizeState({...record.state,answers:[...record.state.answers,null,'yes']}),expected,`${describe(record)}: nonstring suffix`);
  }
  assert.deepEqual(flow.parseFlowHash('#flow=not-a-real-field&steps=y'),flow.initialState());
  assert.deepEqual(flow.parseFlowHash('#flow=graphs&steps='+('x'.repeat(5000))),flow.initialState());
  const malformed=['#flow=graphs&steps=c:%ZZ','#flow=dp&steps=c:%E0%A4%A','#flow=math&steps=y&trail=%7Bbad-json'];
  for(const hash of malformed) {
    const state=flow.parseFlowHash(hash);
    assertCanonicalTrail(flow,state,hash);
    assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)),state);
  }
  const injected={graph:'ranges',answers:[],trail:[{graph:'graphs',answers:['distance']}]};
  const state=flow.parseFlowHash(oldHash(injected));
  assert.equal(state.graph,'ranges');assert.deepEqual(state.answers,[]);
  assertCanonicalTrail(flow,state,'unrelated injected history');
  assert.equal(flow.getFlowDomainId(state),'ranges');
});
