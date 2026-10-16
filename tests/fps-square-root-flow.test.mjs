import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
test('square-root features require an odd field, one-or-none output and supported precision', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'flowchartcp-square-root-flow-'));
  try {
    await compileLocalModules(site, directory);
    const flow = await import(pathToFileURL(path.join(directory, 'flow.js')));
    const viewer = await import(pathToFileURL(path.join(directory, 'diagram-viewer.js')));
    assert.deepEqual(flow.validateGraphs(), []);
    const guards = ['odd-field', 'one-or-none', 'supported-length'];
    for (let i = 0; i < guards.length; ++i) {
      const prefix = ['series-square', ...Array(i).fill('yes')];
      const current = flow.walkFromRoot(prefix, 'math');
      assert.equal(current.current.id, guards[i]);
      for (const answer of ['no', 'unknown']) {
        const value = flow.walkFromRoot([...prefix, answer], 'math');
        assert.equal(value.consumed, prefix.length + 1);
        assert.equal(value.graph.id, 'condition-check');
        assert.equal(value.current.type, 'question');
      }
    }
    const value = flow.walkFromRoot(['series-square', 'yes', 'yes', 'yes'], 'math');
    assert.equal(value.consumed, 4);
    assert.deepEqual(value.current.techniques, ['fps-square-root']);
    const diagram = flow.renderFlowSvg(value.graph);
    assert(diagram.includes('/flowchartcp/techniques/fps-square-root/'));
    for (const node of value.graph.nodes) if (node.type === 'question')
      for (const option of flow.getNodeOptions(node))
        assert(diagram.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
    const secondEntry = flow.walkFromRoot(['square-root', 'yes', 'yes', 'yes'], 'series-coefficients');
    assert.deepEqual(secondEntry.current, value.current);
    let state = flow.initialState('math');
    for (const answer of ['series-square', 'yes', 'yes', 'yes']) {
      while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
      state = flow.answerState(state, answer);
    }
    assert.deepEqual(flow.evaluateState(state).current, value.current);
    const hash = flow.serializeFlowHash(state);
    assert.deepEqual(flow.parseFlowHash(hash), state);
    assert.deepEqual(viewer.diagramState(state.graph, hash), state);
    const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
    const record = walks.find(row => row.source === 'Library Checker'
      && row.problemId === 'sqrt_of_formal_power_series' && row.expectedTechniqueIds.includes('fps-square-root'));
    assert(record);
    assert.equal(record.reviewStatus, 'verified');
    assert.equal(record.verificationKind, 'reference-solution');
    assert.deepEqual(record.steps, value.steps.map(({ graph, node, answer }) => ({ graph, node, answer })));
    const [feature] = JSON.parse(await readFile(path.join(site, 'data/fps-square-root-problem-features.json'), 'utf8'));
    assert.deepEqual(feature.features, record.features);
    assert.equal(feature.publicationDateStatus, 'source-before-cutoff');
    assert.equal(feature.sourceDate, '2019-09-20');
    assert.equal(feature.publicationDate, undefined, 'a proposal date is not the judge release date');
    assert.equal(feature.cutoffEvidenceUrl, 'https://github.com/yosupo06/library-checker-problems/issues/73');
  } finally { await rm(directory, { recursive: true, force: true }); }
});
