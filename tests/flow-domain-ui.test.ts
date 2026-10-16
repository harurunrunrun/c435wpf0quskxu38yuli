import test from 'node:test';
import assert from 'node:assert/strict';
import { entryGraphs, flowGroups, getFlowDomainId, graphs, initialState, renderFlowHtml, sanitizeState, evaluateState, enterFlowRoute, answerState } from '../src/lib/flow.ts';

test('field entries replace the overview and every diagram occurs in one field index', () => {
  assert(!graphs.some(graph => graph.id === 'overview'));
  assert(entryGraphs.length >= 10);
  assert(entryGraphs.some(graph => graph.id === initialState().graph));
  assert.equal(initialState().graph, 'ranges');
  assert.equal(new Set(flowGroups.flatMap(group => group.graphs.map(graph => graph.id))).size, graphs.length);
  assert.equal(flowGroups.reduce((count, group) => count + group.graphs.length, 0), graphs.length);
  for(const group of flowGroups) {
    assert(group.graphs.includes(group.entry));
    assert.equal(getFlowDomainId(initialState(group.entry.id)), group.entry.id);
  }
});

test('static readers get field links and grouped detailed diagrams without an overall chart', () => {
  const html=renderFlowHtml();
  assert.doesNotMatch(html, /diagram-overview|value="overview"|data-flow-svg="overview"/);
  assert.equal((html.match(/data-domain-graph="/g) ?? []).length,entryGraphs.length);
  assert.equal((html.match(/<optgroup /g) ?? []).length,entryGraphs.length);
  assert.equal((html.match(/<option value=/g) ?? []).length,graphs.length);
  for(const entry of entryGraphs) assert(html.includes(`href="#diagram-${entry.id}" data-domain-graph="${entry.id}"`));
  for(const graph of graphs) assert(html.includes(`id="diagram-${graph.id}"`));
});

test('the originating field survives entering detailed charts and sanitizing shared history', () => {
  let state=initialState('ranges');
  const root=graphs.find(graph=>graph.id==='ranges')!.nodes.find(node=>node.id===graphs.find(graph=>graph.id==='ranges')!.root)!;
  const option=Object.entries(root.answers!).find(([,id])=>graphs.find(graph=>graph.id==='ranges')!.nodes.find(node=>node.id===id)!.type==='route')!;
  assert(option);
  state=answerState(state,option[0]);state=enterFlowRoute(state);
  assert.notEqual(state.graph,'ranges');
  assert.equal(getFlowDomainId(state),'ranges');
  assert.equal(getFlowDomainId(sanitizeState(state)),'ranges');
  assert(evaluateState(state).current);
});
