import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-dp-expansion-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

// These are problem features followed by applicability checks, independently
// specified here rather than copied from the registered example walks.
const paths = [
  {
    domain: 'ranges',
    prefix: ['selected-elements', 'lis-results', 'membership'],
    guards: 2,
    id: 'lis-through-each-position',
    requiredTerms: [/増加/, /位置|添字/, /候補|段/],
  },
  {
    domain: 'ranges',
    prefix: ['selected-elements', 'lis-results', 'count'],
    guards: 2,
    id: 'lis-length-count-monoid',
    requiredTerms: [/増加/, /位置|添字/, /個数/, /法|剰余/],
  },
  {
    domain: 'dp',
    prefix: ['sequence-removals', 'same-color-square'],
    guards: 2,
    id: 'interval-removal-carried-group',
    requiredTerms: [/同色|同じ色/, /二乗|平方/, /外|持ち越/],
  },
  {
    domain: 'dp',
    prefix: ['generation-history', 'permutation-signs'],
    guards: 3,
    id: 'permutation-inequality-last-rank',
    requiredTerms: [/異な|重複/, /隣接|隣り/, /順位/, /O\(N\^2\)|O\(N²\)/],
  },
  {
    domain: 'dp',
    prefix: ['sequence-removals', 'extrema-partition', 'product-ranges'],
    guards: 2,
    id: 'partition-extrema-weighted-sum',
    requiredTerms: [/最大|max/, /最小|min/, /係数|線形/],
  },
  {
    domain: 'dp',
    prefix: ['sequence-removals', 'extrema-partition', 'minimum-owner'],
    guards: 3,
    id: 'partition-minimum-pivot-max-score',
    requiredTerms: [/最小/, /個数|区間数/, /同値|同じ|等し/],
  },
];
const ids = paths.map(item => item.id);
function walk(flow, domain, choices) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, `${domain}/${choices.join('/')}: all answers are consumed`);
  return value;
}
function candidates(value) { return value.current.techniques ?? []; }
function replay(flow, domain, choices) {
  let state = flow.initialState(domain);
  for (const answer of choices) {
    while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
    state = flow.answerState(state, answer);
  }
  while (flow.evaluateState(state).current.type === 'route') state = flow.enterFlowRoute(state);
  return state;
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}

test('six fine-grained DP techniques are reached from problem features after all of their guards', async () => {
  const { flow } = await implementation;
  for (const item of paths) {
    const choices = [...item.prefix, ...Array(item.guards).fill('yes')];
    const value = walk(flow, item.domain, choices);
    assert(candidates(value).includes(item.id), `${item.id}: full conditions select the technique`);
    const graphText = JSON.stringify(value.graph);
    for (const term of item.requiredTerms) assert.match(graphText, term, `${item.id}: applicability is explained`);
    assert(flow.renderFlowSvg(value.graph).includes(`/flowchartcp/techniques/${item.id}/`));
  }
  assert.equal(flow.entryGraphs.length, 15, 'the new charts remain within the existing fields');
});

test('missing properties and unknown answers never assert the six new techniques', async () => {
  const { flow } = await implementation;
  for (const item of paths) {
    for (let guard = 0; guard < item.guards; ++guard) for (const answer of ['no', 'unknown']) {
      const choices = [...item.prefix, ...Array(guard).fill('yes'), answer];
      const value = walk(flow, item.domain, choices);
      assert(!candidates(value).includes(item.id), `${item.id} guard ${guard}/${answer}: missing premise cannot select the technique`);
      if (answer === 'unknown') assert.equal(value.current.type, 'question', `${item.id}: uncertainty gives a next question`);
    }
  }
  for (const [domain, prefix] of [
    ['ranges', ['selected-elements', 'lis-results']],
    ['dp', ['sequence-removals', 'extrema-partition']],
  ]) {
    const value = walk(flow, domain, [...prefix, 'unknown']);
    assert.equal(value.current.type, 'question', `${prefix.join('/')}: unknown goal offers further consideration`);
    assert(ids.every(id => !candidates(value).includes(id)));
  }
});

test('question and diagram URLs retain the same answers and support finite Back to the original field', async () => {
  const { flow, viewer } = await implementation;
  for (const item of paths) {
    const choices = [...item.prefix, ...Array(item.guards).fill('yes')];
    let state = replay(flow, item.domain, choices);
    assert.deepEqual(flow.evaluateState(state).current, walk(flow, item.domain, choices).current);
    for (let remaining = weight(state) + 1; ; --remaining) {
      assert(remaining > 0, `${item.id}: Back terminates`);
      assert.equal(flow.getFlowDomainId(state), item.domain);
      assert.deepEqual(flow.sanitizeState(state), state);
      const hash = flow.serializeFlowHash(state);
      assert.deepEqual(flow.parseFlowHash(hash), state, `${item.id}: question URL reloads`);
      assert.deepEqual(viewer.diagramState(state.graph, hash), state, `${item.id}: diagram-only URL reloads`);
      if (!weight(state)) break;
      const previous = flow.backFlowState(state);
      assert(weight(previous) < weight(state));
      state = previous;
    }
    assert.deepEqual(state, flow.initialState(item.domain));
    assert.deepEqual(flow.backFlowState(state), state);
  }
});

test('new articles have complete explanations and confirmed original examples with root walks', async () => {
  const { flow } = await implementation;
  const files = await readdir(path.join(site, 'data'));
  const load = async expression => (await Promise.all(files.filter(name => expression.test(name)).map(async name =>
    JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))))).flat();
  const [metadata, references] = await Promise.all([load(/^techniques-.*\.json$/), load(/^references-.*\.json$/)]);
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  for (const id of ids) {
    const item = metadata.find(row => row.id === id);
    assert(item, `${id}: registered metadata`);
    assert.equal(item.kind, 'technique');
    assert.equal(item.status, 'reviewed');
    assert(item.aliases.some(alias => /[A-Za-z]/.test(alias)), `${id}: English searchable name`);
    const article = await readFile(path.join(site, 'src/content/docs/techniques', id + '.mdx'), 'utf8');
    for (const heading of ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'])
      assert.equal(article.split(`## ${heading}\n`).length - 1, 1, `${id}: one ${heading} section`);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1, `${id}: one standalone C++ implementation`);
    for (const source of item.sources) assert(article.includes(source), `${id}: registered primary source appears in article`);
    const examples = references.filter(row => row.techniqueId === id);
    assert(examples.length, `${id}: at least one confirmed example`);
    for (const row of examples) {
      assert(['editorial', 'reference-solution', 'independent-analysis'].includes(row.verification));
      const record = walks.find(candidate => candidate.statementUrl === row.url && candidate.expectedTechniqueIds.includes(id));
      assert(record, `${id}/${row.source}/${row.problemId}: example has a root walk`);
      assert.equal(record.reviewStatus, 'verified');
      assert.equal(record.verificationKind, row.verification);
      assert(record.features.length >= 2);
      assert(candidates(walk(flow, record.entryGraphId, record.choices)).includes(id));
    }
  }
});

test('all eight original problems retain their feature evidence and explicit cutoff status', async () => {
  const features = JSON.parse(await readFile(path.join(site, 'data/dp-expansion-problem-features.json'), 'utf8'));
  const files = await readdir(path.join(site, 'data'));
  const references = (await Promise.all(files.filter(name => /^references-.*\.json$/.test(name)).map(async name =>
    JSON.parse(await readFile(path.join(site, 'data', name), 'utf8'))))).flat().filter(row => ids.includes(row.techniqueId));
  const walks = JSON.parse(await readFile(path.join(site, 'data/problem-walks.json'), 'utf8'));
  const expectedPairs = references.map(row => `${row.source}/${row.problemId}/${row.techniqueId}`).sort();
  const actualPairs = [];
  assert.equal(features.length, 8);
  for (const feature of features) {
    assert.equal(feature.reviewStatus, 'verified');
    assert(feature.features.length >= 2);
    assert.equal(feature.cutoff, '2026-10-14');
    assert(feature.evidenceUrl.startsWith('https://'));
    for (const id of feature.techniqueIds) {
      actualPairs.push(`${feature.source}/${feature.problemId}/${id}`);
      const reference = references.find(row => row.source === feature.source && row.problemId === feature.problemId && row.techniqueId === id);
      assert(reference, `${id}: feature evidence corresponds to a registered example`);
      assert.equal(reference.url, feature.url);
      assert.equal(reference.verification, feature.verification);
      const record = walks.find(row => row.source === feature.source && row.problemId === feature.problemId && row.expectedTechniqueIds.includes(id));
      assert(record);
      assert.deepEqual(record.features, feature.features);
      if (feature.publicationDateStatus === 'undated-archive') {
        assert.equal(reference.cutoffVerification, 'undated-archive');
        assert.equal(record.cutoffVerification, 'undated-archive');
      } else {
        assert.equal(feature.publicationDateStatus, 'contest-before-cutoff');
        assert.match(feature.publicationDate, /^\d{4}-\d{2}-\d{2}$/);
        assert(feature.publicationDate <= feature.cutoff);
      }
    }
  }
  assert.deepEqual(actualPairs.sort(), expectedPairs, 'no unverified candidate is promoted or confirmed example omitted');
});
