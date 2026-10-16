import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { validateSite } from '../scripts/validate.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const question = (id, answers) => ({ id, type: 'question', title: `質問 ${id}`, answers, options: Object.keys(answers).map(id => ({ id, label: id })) });
const result = id => ({ id, type: 'result', title: `候補 ${id}`, techniques: ['example'], conditions: ['入力条件を確認する'] });
const route = (id, graph, continuation = false) => ({ id, type: 'route', title: '続きの質問へ', graph, ...(continuation ? { continuation: true } : {}) });
const graph = (id, root, nodes, extra = {}) => ({ id, title: id, description: `${id} の条件`, root, nodes, ...extra });

// Independent of authored chart data: two successive root regroupings followed
// by two same-question continuations must preserve one former answer sequence.
const fixture = [
  graph('field', 'root', [question('root', { 'group-a': 'to-a', unknown: 'uncertain' }), route('to-a', 'category'), result('uncertain')],
    { entry: true, legacyEntryChoices: { former: { answer: 'group-a', graph: 'category' } } }),
  graph('category', 'root', [question('root', { 'group-b': 'to-b', unknown: 'uncertain' }), route('to-b', 'sub-category'), result('uncertain')],
    { legacyEntryChoices: { former: { answer: 'group-b', graph: 'sub-category' } } }),
  graph('sub-category', 'root', [question('root', { former: 'step-one', unknown: 'uncertain' }),
    question('step-one', { yes: 'step-two', no: 'uncertain', unknown: 'uncertain' }), route('step-two', 'detail-a', true), result('uncertain')]),
  graph('detail-a', 'step-two', [question('step-two', { yes: 'step-three', no: 'uncertain', unknown: 'uncertain' }), route('step-three', 'detail-b', true), result('uncertain')]),
  graph('detail-b', 'step-three', [question('step-three', { yes: 'success', no: 'uncertain', unknown: 'uncertain' }), result('success'), result('uncertain')]),
];
const expected = {
  graph: 'detail-b', answers: ['yes'], trail: [
    { graph: 'field', answers: ['group-a'] }, { graph: 'category', answers: ['group-b'] },
    { graph: 'sub-category', answers: ['former', 'yes'] }, { graph: 'detail-a', answers: ['yes'] },
  ],
};
// The old encoding is intentionally independent of the current serializer.
function oldHash(state) {
  const short = { yes: 'y', no: 'n', unknown: 'u' };
  return `#flow=${state.graph}&steps=${state.answers.map(answer => short[answer] ?? `c:${encodeURIComponent(answer)}`).join(',')}${state.trail?.length ? `&trail=${encodeURIComponent(JSON.stringify(state.trail))}` : ''}`;
}

let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-nested-migrations-'));
  const modules = path.join(temporary, 'modules');
  await compileLocalModules(site, modules);
  const modulePath = path.join(modules, 'flow.js');
  const source = await readFile(modulePath, 'utf8');
  const isolated = source.replace(/^const rawGraphs = .+;$/m, `const rawGraphs = ${JSON.stringify(fixture)};`);
  assert.notEqual(isolated, source, 'the fixture replaces only compiled chart data');
  await writeFile(modulePath, isolated);
  const [flow, viewer] = await Promise.all([
    import(pathToFileURL(modulePath).href), import(pathToFileURL(path.join(modules, 'diagram-viewer.js')).href),
  ]);
  const root = path.join(temporary, 'site');
  await mkdir(path.join(root, 'data'), { recursive: true });
  await mkdir(path.join(root, 'src/content/docs/techniques'), { recursive: true });
  await mkdir(path.join(root, 'vendor/ac-library'), { recursive: true });
  const json = (relative, value) => writeFile(path.join(root, relative), `${JSON.stringify(value)}\n`);
  await json('data/techniques-fixture.json', [{ id: 'example', title: '条件の確認', summary: '条件に合う候補を調べる。', family: '確認', level: 'basic', status: 'reviewed', aliases: ['Example'], entryPoints: ['advanced'], prerequisites: [], sources: ['https://example.org/guide'] }]);
  await json('data/references-fixture.json', [{ techniqueId: 'example', problemId: 'sample', title: '例題', source: 'fixture', evidence: '公開解説で確認', verification: 'editorial', url: 'https://example.org/problem', editorialUrl: 'https://example.org/guide', difficulty: null }]);
  await json('data/sources.json', [{ id: 'fixture', name: 'fixture', language: 'ja', method: 'manual', enumerability: 'manual', access: 'public', status: 'partial', notes: '検証用', homepage: 'https://example.org/', archive: 'https://example.org/archive' }]);
  await json('data/research-ledger.json', { cutoff: '2026-10-14', coveragePolicy: '全件調査は未完了。', verifiedMappings: 1, reviewedProblems: 1, formatVerifiedProblems: 0, sources: [{ source: 'fixture', discovered: 1, fetched: 1, metadataCollected: 1, bootstrapProblems: 1, solutionReviewed: 1, techniquesExtracted: 1, totalKnown: null, status: 'partial', scope: '検証用', notes: '検証用' }] });
  await json('vendor/ac-library/manifest.json', { repository: 'https://github.com/atcoder/ac-library', revision: '0'.repeat(40), license: 'CC0-1.0', files: [] });
  await writeFile(path.join(root, 'src/content/docs/techniques/example.mdx'), `---\ntitle: 条件の確認\ndescription: 条件に合う候補を調べる。\ntechniqueId: example\n---\n${['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'].map(heading => `\n## ${heading}\n\n条件を確認する。\n`).join('')}\n\`\`\`cpp\nbool applicable(bool condition) { return condition; }\n\`\`\`\n\nhttps://example.org/guide\n\n<TechniqueReferences techniqueId="example" />\n`);
  await json('data/flows.json', fixture);
  return { flow, viewer, root, json };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

function assertStable(flow, state) {
  assert.deepEqual(flow.sanitizeState(state), state, 'canonical history is not expanded twice');
  assert.deepEqual(flow.parseFlowHash(flow.serializeFlowHash(state)), state, 'canonical shared URL reloads');
  const contexts = [...(state.trail ?? []), { graph: state.graph, answers: state.answers }];
  for (let index = 0; index < contexts.length; index++) {
    const context = contexts[index], graph = flow.getGraph(context.graph);
    let node = graph.nodes.find(node => node.id === graph.root);
    for (const answer of context.answers) {
      assert.equal(node.type, 'question');
      assert(flow.getNodeOptions(node).some(option => option.id === answer));
      node = graph.nodes.find(candidate => candidate.id === node.answers[answer]);
      assert(node);
    }
    if (index + 1 < contexts.length) {
      assert.equal(node.type, 'route');
      assert.equal(node.graph, contexts[index + 1].graph, 'route boundaries are contiguous');
    }
  }
}

test('both validators accept root migrations that forward the same old answer through another migration', async () => {
  const { flow, root } = await implementation;
  assert.deepEqual(flow.validateGraphs(fixture), []);
  assert.deepEqual((await validateSite(root)).errors, []);
});

test('old local prefixes preserve their questions and candidates across four chart boundaries', async () => {
  const { flow, viewer } = await implementation;
  const cases = [
    [[], 'field', 'root'], [['unknown'], 'field', 'uncertain'],
    [['former'], 'sub-category', 'step-one'], [['former', 'no'], 'sub-category', 'uncertain'], [['former', 'unknown'], 'sub-category', 'uncertain'],
    [['former', 'yes'], 'detail-a', 'step-two'], [['former', 'yes', 'no'], 'detail-a', 'uncertain'], [['former', 'yes', 'unknown'], 'detail-a', 'uncertain'],
    [['former', 'yes', 'yes'], 'detail-b', 'step-three'], [['former', 'yes', 'yes', 'no'], 'detail-b', 'uncertain'], [['former', 'yes', 'yes', 'unknown'], 'detail-b', 'uncertain'],
    [['former', 'yes', 'yes', 'yes'], 'detail-b', 'success'],
  ];
  for (const [answers, graph, node] of cases) {
    const raw = { graph: 'field', answers }, hash = oldHash(raw), state = flow.parseFlowHash(hash);
    assert.equal(state.graph, graph);
    assert.equal(flow.evaluateState(state).current.id, node);
    assert.deepEqual(flow.sanitizeState(raw), state);
    assert.deepEqual(viewer.diagramState('field', hash), state);
    assert.equal(flow.getFlowDomainId(state), 'field');
    assertStable(flow, state);
    assert.deepEqual(flow.sanitizeState({ ...raw, answers: [...answers, '__invalid__', 'yes'] }), state, 'invalid suffix is truncated');
  }
});

test('histories from each split generation remain flat, shareable and reversible', async () => {
  const { flow, viewer } = await implementation;
  const states = [
    { graph: 'field', answers: ['former', 'yes', 'yes', 'yes'] },
    { graph: 'category', answers: ['former', 'yes', 'yes', 'yes'], trail: [{ graph: 'field', answers: ['group-a'] }] },
    { graph: 'detail-b', answers: ['yes'], trail: [{ graph: 'field', answers: ['former', 'yes'] }, { graph: 'detail-a', answers: ['yes'] }] },
    { graph: 'detail-b', answers: ['yes'], trail: [{ graph: 'field', answers: ['group-a'] }, { graph: 'category', answers: ['former', 'yes'] }, { graph: 'detail-a', answers: ['yes'] }] },
    { graph: 'detail-a', answers: ['yes', 'yes'], trail: [{ graph: 'field', answers: ['former', 'yes'] }] },
    expected,
  ];
  const weight = state => state.answers.length + (state.trail ?? []).reduce((sum, item) => sum + item.answers.length + 1, 0);
  for (const raw of states) {
    let state = flow.sanitizeState(raw);
    assert.deepEqual(state, expected);
    assert.deepEqual(flow.parseFlowHash(oldHash(raw)), expected);
    assertStable(flow, state);
    if (raw.graph !== state.graph) assert.deepEqual(flow.migratedFlowHash(raw.graph, oldHash(raw)), expected);
    assert.deepEqual(viewer.diagramState(raw.graph, oldHash(raw)), expected);
    for (let remaining = weight(state) + 1; weight(state) > 0; remaining--) {
      assert(remaining > 0);
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state), 'back removes an answer or route boundary');
      assert.equal(flow.getFlowDomainId(previous), 'field');
      assertStable(flow, previous);
      state = previous;
    }
    assert.deepEqual(state, flow.initialState('field'));
  }
  for (const id of ['field', 'category', 'sub-category']) {
    const walked = flow.walkFromRoot(['former', 'yes', 'yes', 'yes'], id);
    assert.equal(walked.current.id, 'success');
    assert.equal(walked.consumed, 4, 'root regroupings do not consume the old answer twice');
  }
});

test('nested viewer migration still rejects another chart hash and stops at ordinary routes', async () => {
  const { flow, viewer } = await implementation;
  for (const hash of [flow.serializeFlowHash(expected), '#flow=category&steps=c:former,y,y,y', '#flow=field&steps=c:group-a,c:former,y,y,y']) {
    assert.equal(flow.migratedFlowHash('field', hash), undefined);
    assert.deepEqual(viewer.diagramState('field', hash), hash.startsWith('#flow=field&') ? { graph: 'field', answers: ['group-a'] } : flow.initialState('field'));
  }
  const malformed = flow.sanitizeState({ graph: 'field', answers: ['former', 'yes', 'yes', 'yes'], trail: [{ graph: 'detail-b', answers: ['yes'] }] });
  assert.deepEqual(malformed, expected, 'bad external history cannot suppress a valid local migration');
});

test('both validators continue to reject broken nested links, missing answers, mismatched routes and cycles', async () => {
  const { flow, root, json } = await implementation;
  const cases = [
    ['broken chain', graphs => { graphs[1].legacyEntryChoices.former.answer = 'missing'; }, /invalid legacy entry/, /旧回答/],
    ['missing former answer', graphs => { delete graphs[2].nodes[0].answers.former; graphs[2].nodes[0].answers.other = 'step-one'; graphs[2].nodes[0].options.find(option => option.id === 'former').id = 'other'; }, /invalid legacy entry/, /旧回答/],
    ['mismatched route', graphs => { graphs[0].legacyEntryChoices.former.graph = 'sub-category'; }, /invalid legacy entry/, /旧回答/],
    ['same-answer forwarding cycle', graphs => { graphs[1].legacyEntryChoices.former.graph = 'field'; graphs[1].nodes.find(node => node.id === 'to-b').graph = 'field'; }, /Graph route cycle/, /循環/],
  ];
  try {
    for (const [description, mutate, coreError, siteError] of cases) {
      const graphs = structuredClone(fixture);
      mutate(graphs);
      assert(flow.validateGraphs(graphs).some(error => coreError.test(error)), `${description}: core validator rejects the fixture`);
      await json('data/flows.json', graphs);
      const result = await validateSite(root);
      assert(result.errors.some(error => siteError.test(error)), `${description}: content validator rejects the fixture`);
    }
  } finally { await json('data/flows.json', fixture); }
});
