import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync, readdirSync } from 'node:fs';
import { answerState, enterFlowRoute, backFlowState, evaluateState, getGraph, getNodeOptions, graphs, initialState, parseFlowHash, renderFlowHtml, renderFlowSvg, sanitizeState, serializeFlowHash, validateGraphs, walkFromRoot, type FlowGraph } from '../src/lib/flow.ts';

const questionCount = graphs.reduce((sum, graph) => sum + graph.nodes.filter((node) => node.type === 'question').length, 0);
const walks = JSON.parse(readFileSync('data/problem-walks.json', 'utf8'));
const baselineReferences = readdirSync('data').filter((name) => /^references-.*\.json$/.test(name)).flatMap((name) => JSON.parse(readFileSync(`data/${name}`, 'utf8')));
const techniqueTitles: Record<string, string> = Object.fromEntries(readdirSync('data').filter((name) => /^techniques-.*\.json$/.test(name)).flatMap((name) => JSON.parse(readFileSync(`data/${name}`, 'utf8'))).map((row: { id: string; title: string }) => [row.id, row.title]));

function local(graph: string, answers: string[]) { return evaluateState({ graph, answers }); }
function root(choices: string[], entryGraphId?: string) {
  const graphId = entryGraphId ?? choices[0];
  const answers = entryGraphId ? choices : choices.slice(1);
  assert.ok(graphs.some((graph) => graph.id === graphId), `Unknown test entry: ${graphId}`);
  const result = walkFromRoot(answers, graphId);
  assert.equal(result.consumed, answers.length);
  return result;
}

test('charts contain substantial problem-feature questions, with complete acyclic multi-choice branches', () => {
  assert.ok(graphs.length >= 30);
  assert.ok(questionCount >= 250);
  assert.ok(graphs.filter((graph) => graph.nodes.some((node) => getNodeOptions(node).length >= 4)).length >= 15);
  assert.deepEqual(validateGraphs(), []);
  for (const graph of graphs) for (const node of graph.nodes) {
    assert.ok(node.title.trim());
    if (node.type === 'question') {
      assert.ok(node.explanation);
      assert.ok(getNodeOptions(node).some((option) => option.id === 'unknown'));
      assert.doesNotMatch(node.title, /CHT|Monge|SMAWK|Knuth|Grundy|LARSCH|モノイド/);
    }
    if (node.type === 'result') { assert.ok(node.techniques!.length); assert.ok(node.conditions!.length); }
  }
  const start = local('ranges', []).current;
  assert.equal(start.id, 'updates');
  assert.ok(getNodeOptions(start).some((option) => option.id === 'aggregate-goals'));
  const aggregate = enterFlowRoute(answerState(initialState('ranges'), 'aggregate-goals'));
  assert.equal(aggregate.graph, 'range-aggregate-goals');
  assert.ok(getNodeOptions(evaluateState(aggregate).current).some((option) => option.id === 'change'));
  assert.equal(enterFlowRoute(answerState(aggregate, 'change')).graph, 'range-update');
  assert.ok(!graphs.some((graph) => graph.id === 'overview'));
  assert.ok(graphs.filter((graph) => graph.entry).length >= 14);
});

test('all recorded problem-method mappings are followed from their problem-domain root', () => {
  const covered = new Set<string>();
  for (const fixture of walks) {
    assert.ok(fixture.features.length);
    assert.ok(['verified', 'pending'].includes(fixture.reviewStatus));
    assert.ok(fixture.statementUrl.startsWith('https://'));
    assert.ok(fixture.evidenceUrl.startsWith('https://'));
    assert.ok(['editorial', 'reference-solution', 'independent-analysis', 'official-tag'].includes(fixture.verificationKind));
    const result = root(fixture.choices, fixture.entryGraphId);
    assert.equal(result.current.type, 'result', `${fixture.problemId}: complete path`);
    assert.deepEqual(result.steps.map(({ graph, node, answer }) => ({ graph, node, answer })), fixture.steps);
    for (const technique of fixture.expectedTechniqueIds) {
      assert.ok(result.current.techniques!.includes(technique), `${fixture.problemId}: ${technique}`);
      covered.add(`${fixture.statementUrl}:${technique}`);
    }
  }
  for (const reference of baselineReferences) assert.ok(covered.has(`${reference.url}:${reference.techniqueId}`), `${reference.problemId}/${reference.techniqueId}: root walk missing`);
  assert.ok(walks.filter((fixture: { reviewStatus: string }) => fixture.reviewStatus === 'verified').length >= 70);
  assert.ok(walks.some((fixture: { reviewStatus: string }) => fixture.reviewStatus === 'pending'));
});

test('unknown proceeds to an explicit confirmation question without acting as no', () => {
  const state = answerState(initialState('ranges'), 'unknown');
  const result = evaluateState(state);
  assert.equal(result.current.type, 'question');
  assert.equal(result.current.id, 'check');
  assert.notEqual(result.current.id, local('ranges', ['static']).current.id);
  const weight = local('shortest-path', ['normal', 'distance-only', 'no', 'no', 'no', 'unknown']);
  assert.equal(weight.current.id, 'check');
  assert.ok(!weight.current.techniques?.includes('dijkstra'));
});

test('negative interval sums avoid an unproved two-pointer shortcut; fixed windows still update', () => {
  const negative = local('range-window', ['variable', 'no', 'no', 'no']);
  assert.equal(negative.current.id, 'fallback');
  assert.ok(!negative.current.techniques!.includes('two-pointers'));
  const count = root(['ranges', 'window', 'sum-equal']);
  assert.ok(count.current.techniques!.includes('subarray-prefix-frequency'));
  const fixed = local('range-window', ['fixed', 'aggregate', 'no', 'yes']);
  assert.equal(fixed.current.id, 'sliding');
  assert.ok(fixed.current.conditions!.some((value) => value.includes('負数')));
  const monotone = local('range-window', ['variable', 'yes', 'yes']);
  assert.equal(monotone.current.id, 'pointers');
  assert.match(monotone.current.conditions!.join(' '), /証明/);
});

test('static invertibility, point assignment, affine actions and value caps follow distinct routes', () => {
  assert.equal(local('range-static', ['sum', 'yes']).current.id, 'prefix');
  assert.equal(local('range-static', ['minmax', 'yes']).current.id, 'segment');
  assert.ok(root(['ranges', 'change', 'point-add', 'yes']).current.techniques!.includes('fenwick-tree'));
  assert.ok(root(['ranges', 'change', 'point-set', 'aggregate', 'yes']).current.techniques!.includes('segment-tree'));
  const affine = root(['ranges', 'change', 'affine', 'yes']);
  assert.ok(affine.current.techniques!.includes('affine-lazy-composition'));
  const caps = root(['ranges', 'change', 'cap', 'aggregate', 'yes']);
  assert.ok(caps.current.techniques!.includes('range-chmin-second-maximum'));
  assert.ok(!root(['ranges', 'change', 'cap', 'aggregate', 'no']).current.techniques!.includes('segment-tree-beats'));
});

test('DAGs with negative edges, general nonnegative weights, 0-1 weights and negative cycles are separated', () => {
  assert.ok(root(['graphs', 'distance', 'normal', 'distance-only', 'no', 'yes']).current.techniques!.includes('zero-one-bfs'));
  const dag = root(['graphs', 'distance', 'normal', 'distance-only', 'no', 'no', 'yes']);
  assert.ok(dag.current.techniques!.includes('dag-dp'));
  assert.ok(!dag.current.techniques!.includes('dijkstra'));
  const nonnegative = root(['graphs', 'distance', 'normal', 'distance-only', 'no', 'no', 'no', 'yes']);
  assert.ok(nonnegative.current.techniques!.includes('dijkstra'));
  const negative = root(['graphs', 'distance', 'normal', 'distance-only', 'no', 'no', 'no', 'no', 'yes']);
  assert.ok(negative.current.techniques!.includes('bellman-ford'));
  assert.ok(!negative.current.techniques!.includes('dijkstra'));
  assert.ok(root(['graphs', 'negative-cycle']).current.techniques!.includes('bellman-ford'));
});

test('edge deletions, time intervals and branched versions require different feature paths', () => {
  assert.ok(root(['graphs', 'connectivity', 'delete', 'yes']).current.techniques!.includes('reverse-edge-deletion'));
  assert.ok(root(['graphs', 'connectivity', 'mixed', 'yes', 'no', 'yes']).current.techniques!.includes('connectivity-time-intervals'));
  const online = root(['graphs', 'connectivity', 'mixed', 'no']);
  assert.equal(online.current.id, 'dynamic');
  assert.ok(!online.current.techniques!.includes('union-find'));
  assert.ok(root(['graphs', 'connectivity', 'branched-version', 'yes']).current.techniques!.includes('rollback-dsu'));
});

test('monotone slopes, arbitrary slopes and non-linear single crossings have separate guards', () => {
  const monotone = local('dp-affine', ['yes', 'yes', 'yes', 'yes']);
  assert.ok(monotone.current.techniques!.includes('convex-hull-trick'));
  const general = local('dp-affine', ['yes', 'no', 'yes']);
  assert.ok(general.current.techniques!.includes('li-chao-tree'));
  assert.ok(!general.current.techniques!.includes('convex-hull-trick'));
  const curves = local('dp-affine', ['no', 'yes', 'yes']);
  assert.ok(curves.current.techniques!.includes('li-chao-tree'));
  assert.match(curves.current.conditions!.join(' '), /一般化/);
});

test('Knuth, staged minima, arbitrary entry evaluation and online minima preserve dependencies', () => {
  assert.ok(local('dp-monge', ['yes', 'yes']).current.techniques!.includes('knuth-optimization'));
  assert.ok(!local('dp-monge', ['yes', 'no']).current.techniques!.includes('knuth-optimization'));
  const divide = local('dp-monge', ['no', 'no', 'yes', 'no']);
  assert.ok(divide.current.techniques!.includes('divide-conquer-dp'));
  const independent = local('dp-monge', ['no', 'no', 'yes', 'yes', 'yes']);
  assert.ok(independent.current.techniques!.includes('monge-smawk'));
  const online = local('dp-monge', ['no', 'yes', 'yes', 'sequential']);
  assert.ok(online.current.techniques!.includes('larsch'));
  assert.ok(!online.current.techniques!.includes('monge-smawk'));
  const block = local('dp-monge', ['no', 'yes', 'yes', 'blocks', 'yes']);
  assert.ok(block.current.techniques!.includes('monge-smawk'));
});

test('exact-count penalties require optimal-value differences and tie recovery, independent of Monge', () => {
  const confirmed = local('dp-convex', ['yes', 'yes', 'yes', 'yes']);
  assert.ok(confirmed.current.techniques!.includes('aliens-trick'));
  const unconfirmed = local('dp-convex', ['yes', 'yes', 'unknown']);
  assert.equal(unconfirmed.current.type, 'question');
  assert.ok(!unconfirmed.current.techniques?.includes('aliens-trick'));
  assert.match(confirmed.current.conditions!.join(' '), /個数の単調性だけで適用しない/);
  const arc = walks.find((row: { problemId: string }) => row.problemId === 'arc168_e');
  assert.ok(root(arc.choices, arc.entryGraphId).current.techniques!.includes('aliens-trick'));
});

test('scoring games are distinct from normal-play win/lose games', () => {
  const score = root(['game-probability', 'score', 'yes']);
  assert.equal(score.current.id, 'score-result');
  assert.match(score.current.conditions!.join(' '), /D\[s\]/);
  const grundy = root(['game-probability', 'win', 'no-move', 'other', 'yes', 'yes', 'yes']);
  assert.equal(grundy.current.id, 'grundy');
  assert.match(grundy.current.conditions!.join(' '), /通常ルール/);
});


test('periods with an unfinished repetition and exact repetitions take distinct feature branches', () => {
  const partial = root(['strings', 'prefix', 'border-period', 'partial-period', 'yes']);
  assert.ok(partial.current.techniques!.includes('period-from-border'));
  assert.match(partial.current.conditions!.join(' '), /途中/);
  const exact = root(['strings', 'prefix', 'border-period', 'period', 'no']);
  assert.equal(exact.current.id, 'period-full');
  assert.match(exact.current.conditions!.join(' '), /区別/);
  const nonoverlap = root(['strings', 'substrings', 'repeated', 'no']);
  assert.ok(!nonoverlap.current.techniques!.includes('lcp-repeated-substring'));
});

test('wildcard matching checks exact coefficient recovery, and repeated text preserves wraparound', () => {
  const unproved = root(['strings', 'pattern', 'wildcard', 'yes', 'unknown']);
  assert.equal(unproved.current.type, 'question');
  assert.ok(!unproved.current.techniques?.includes('wildcard-convolution'));
  const recoveryFails = root(['strings', 'pattern', 'wildcard', 'yes', 'no']);
  assert.ok(!recoveryFails.current.techniques!.includes('wildcard-convolution'));
  const periodic = root(['strings', 'pattern', 'periodic-display', 'yes', 'yes', 'yes']);
  assert.ok(periodic.current.techniques!.includes('wildcard-convolution'));
  const repeat = root(['strings', 'subsequence', 'repeated-text', 'yes']);
  assert.match(repeat.current.conditions!.join(' '), /一周/);
  assert.ok(repeat.current.techniques!.includes('substring-subsequence-next'));
});

test('required substrings use a complement and inherited forbidden suffixes are checked', () => {
  const contain = root(['strings', 'pattern', 'many-patterns', 'contain', 'yes', 'yes', 'yes']);
  assert.ok(contain.current.techniques!.includes('automaton-forbidden-dp'));
  assert.ok(contain.steps.some((step) => step.node === 'contain-complement'));
  const missedSuffix = root(['strings', 'pattern', 'many-patterns', 'avoid', 'yes', 'no']);
  assert.ok(!missedSuffix.current.techniques!.includes('automaton-forbidden-dp'));
  const degree = root(['strings', 'palindrome', 'recursive-degree', 'yes', 'degree-one', 'yes']);
  assert.ok(degree.current.techniques!.includes('palindrome-center-contribution'));
  assert.ok(degree.steps.some((step) => step.node === 'recursive-part'));
});

test('recursive palindrome degrees reach the full recurrence as well as the two component improvements', () => {
  const full = root(['strings', 'palindrome', 'recursive-degree', 'yes', 'all-degrees', 'yes']);
  assert.ok(full.current.techniques!.includes('palindrome-recursive-degree'));
  assert.match(full.current.conditions!.join(' '), /非回文は次数 0/);
  assert.match(full.current.conditions!.join(' '), /長さ 1 の次数は 1/);
  assert.match(full.current.conditions!.join(' '), /floor/);
  const unconfirmed = root(['strings', 'palindrome', 'recursive-degree', 'yes', 'all-degrees', 'unknown']);
  assert.equal(unconfirmed.current.type, 'question');
  assert.ok(!unconfirmed.current.techniques?.includes('palindrome-recursive-degree'));
  const component = root(['strings', 'palindrome', 'recursive-degree', 'yes', 'range-test', 'yes']);
  assert.ok(component.current.techniques!.includes('palindrome-radius-range'));
  assert.ok(!component.current.techniques!.includes('palindrome-recursive-degree'));
});

test('single failures reject directed graphs; forbidden-pair and difference constraints require their own domains', () => {
  const directed = root(['graphs', 'failures', 'no']);
  assert.ok(!directed.current.techniques?.includes('bridge-edge-failure'));
  assert.ok(!directed.current.techniques?.includes('block-cut-path'));
  const vertex = root(['graphs', 'failures', 'yes', 'vertex', 'yes', 'yes']);
  assert.ok(vertex.current.techniques!.includes('block-cut-path'));
  const nonbinary = root(['graphs', 'constraints', 'forbidden-pairs', 'no']);
  assert.ok(!nonbinary.current.techniques!.includes('two-sat-forbidden-pairs'));
  const inequalities = root(['graphs', 'constraints', 'difference', 'no']);
  assert.ok(!inequalities.current.techniques!.includes('dsu-potential-differences'));
});

test('statements about two choices, integer differences and set merging enter before a graph model is assumed', () => {
  for (const [id, category] of [['practice2_h', 'dp'], ['abc327_d', 'dp'], ['abc328_f', 'math'], ['abc302_f', 'set-operations']]) {
    const fixture = walks.find((row: { problemId: string }) => row.problemId === id);
    assert.equal(fixture.entryGraphId, category);
    assert.equal(root(fixture.choices, fixture.entryGraphId).current.type, 'result');
  }
  const sets = root(['set-operations', 'merge', 'yes', 'yes', 'shared-set', 'yes', 'yes']);
  assert.ok(sets.current.techniques!.includes('zero-one-bfs-supernodes'));
  assert.ok(sets.steps.some((step) => step.graph === 'set-operations'));
});

test('resource bounds, interval-edge direction and weight reweighting are prerequisites for distance methods', () => {
  assert.ok(!root(['graphs', 'distance', 'resource', 'no']).current.techniques!.includes('dijkstra-expanded-resource'));
  const resource = root(['graphs', 'distance', 'resource', 'yes', 'yes']);
  assert.match(resource.current.conditions!.join(' '), /最適値が変わらない証明/);
  assert.ok(!root(['graphs', 'distance', 'range-edges', 'yes', 'no']).current.techniques!.includes('dijkstra-range-edges'));
  assert.ok(!root(['graphs', 'distance', 'all-pairs', 'no']).current.techniques!.includes('dijkstra-potential-reweight'));
  const reweight = root(['graphs', 'distance', 'all-pairs', 'yes', 'yes']);
  assert.match(reweight.current.conditions!.join(' '), /負閉路がない/);
  assert.match(reweight.current.conditions!.join(' '), /差を戻/);
});

test('using every edge once checks both degree balance and complete edge coverage', () => {
  const tour = root(['graphs', 'all-edges', 'yes', 'yes', 'yes']);
  assert.ok(tour.current.techniques!.includes('euler-degree-connectivity'));
  assert.match(tour.current.conditions!.join(' '), /辺数/);
  assert.ok(tour.steps.some((step) => step.node === 'degree-difference'));
  assert.ok(tour.steps.some((step) => step.node === 'edge-coverage'));
  assert.ok(!root(['graphs', 'all-edges', 'yes', 'yes', 'no']).current.techniques!.includes('euler-degree-connectivity'));
  assert.ok(root(['graphs', 'exact-walk', 'once', 'items', 'yes']).current.techniques!.includes('bitmask-dp'));
});

test('noncoprime modular equations keep impossible cases and avoid an unwarranted modular inverse', () => {
  const impossible = root(['math', 'congruences', 'linear', 'no']);
  assert.ok(impossible.current.techniques!.includes('linear-congruence-gcd'));
  assert.match(impossible.current.conditions!.join(' '), /存在しない/);
  const incompatible = root(['math', 'congruences', 'several', 'no']);
  assert.ok(incompatible.current.techniques!.includes('crt-noncoprime'));
  assert.ok(!root(['math', 'congruences', 'several', 'yes', 'no']).current.techniques!.includes('crt-noncoprime'));
  const sums = root(['math', 'poly', 'yes', 'power-sum', 'yes']);
  assert.ok(sums.current.techniques!.includes('matrix-walk-sum-block'));
  assert.match(sums.current.conditions!.join(' '), /逆元.*要求しない/);
});

test('geometry separates coverage, rectangle splitting, lattice area, and circumference containment', () => {
  const union = root(['geometry', 'rectangle-union', 'yes', 'yes']);
  assert.ok(union.current.techniques!.includes('rectangle-union-sweep'));
  assert.match(union.current.conditions!.join(' '), /物理的な長さ/);
  const split = root(['geometry', 'rectangle-split', 'yes', 'yes']);
  assert.ok(split.current.techniques!.includes('rectangle-split-dp'));
  assert.ok(!split.current.techniques!.includes('rectangle-union-sweep'));
  assert.ok(!root(['geometry', 'lattice-area', 'no']).current.techniques!.includes('lattice-pick-area'));
  const circles = root(['geometry', 'circle-travel', 'yes', 'yes', 'yes']);
  assert.ok(circles.current.techniques!.includes('circle-square-distance'));
  assert.match(circles.current.conditions!.join(' '), /下限/);
});

test('sum feasibility, pairwise coprimality and cyclic boundaries keep necessary information', () => {
  const feasible = root(['dp', 'balanced-groups', 'yes', 'yes']);
  assert.ok(feasible.current.techniques!.includes('knapsack-bitset-shift'));
  assert.ok(!root(['dp', 'capacity', 'total', 'sum-feasibility', 'no']).current.techniques!.includes('knapsack-bitset-shift'));
  const primeSets = root(['math', 'product-exponents', 'yes', 'yes']);
  assert.ok(primeSets.current.techniques!.includes('subset-coprime-small-primes'));
  assert.match(primeSets.current.conditions!.join(' '), /任意の二数が互いに素/);
  assert.ok(!root(['dp', 'cyclic-neighbors', 'yes', 'no']).current.techniques!.includes('cyclic-dp-first-state'));
  const cyclic = root(['dp', 'cyclic-neighbors', 'yes', 'yes', 'yes']);
  assert.ok(cyclic.current.techniques!.includes('cyclic-dp-first-state'));
  assert.match(cyclic.current.conditions!.join(' '), /長さ 1・2/);
});


test('truncated coefficient operations reject missing units, invalid constants and unavailable multiplication lengths', () => {
  const start = ['math', 'poly', 'yes', 'series', 'operation'];
  assert.ok(!root([...start, 'inverse', 'no']).current.techniques!.includes('fps-inverse-newton'));
  assert.ok(!root([...start, 'inverse', 'yes', 'no']).current.techniques!.includes('fps-inverse-newton'));
  assert.ok(!root([...start, 'log', 'no']).current.techniques!.includes('fps-log-derivative'));
  assert.ok(!root([...start, 'log', 'yes', 'no']).current.techniques!.includes('fps-log-derivative'));
  assert.ok(!root([...start, 'exp', 'no']).current.techniques!.includes('fps-exp-newton'));
  assert.ok(!root([...start, 'exp', 'yes', 'yes', 'no']).current.techniques!.includes('fps-exp-newton'));
  const log = root([...start, 'log', 'yes', 'yes', 'yes']);
  assert.match(log.current.conditions!.join(' '), /定数項は 1/);
  const unknown = root([...start, 'inverse', 'unknown']);
  assert.equal(unknown.current.type, 'question');
});

test('coefficient products distinguish XOR divisibility, disjoint sets and invertible factorial weights', () => {
  const prefix = ['math', 'poly', 'yes', 'coefficient-products'];
  assert.ok(!root([...prefix, 'xor', 'no']).current.techniques!.includes('xor-convolution-transform'));
  assert.ok(!root([...prefix, 'disjoint', 'no']).current.techniques!.includes('subset-convolution-ranked'));
  const disjoint = root([...prefix, 'disjoint', 'yes']);
  assert.match(disjoint.current.conditions!.join(' '), /A∩B は空/);
  assert.match(disjoint.current.conditions!.join(' '), /減算/);
  assert.ok(!root([...prefix, 'binomial', 'no']).current.techniques!.includes('binomial-convolution-factorials'));
  const basis = root(['math', 'poly', 'yes', 'values-shift', 'basis', 'yes', 'yes']);
  assert.ok(basis.current.techniques!.includes('binomial-convolution-factorials'));
  const fixture = walks.find((row: { problemId: string }) => row.problemId === 'stirling_number_of_the_second_kind');
  assert.ok(fixture.features.some((feature: string) => feature.includes('x^N') && feature.includes('x(x-1)')));
});

test('polynomial evaluation allows duplicate points while shifts and distant coefficients preserve their guards', () => {
  const points = root(['math', 'poly', 'yes', 'values-shift', 'values', 'yes', 'yes']);
  assert.ok(points.current.techniques!.includes('multipoint-product-tree'));
  assert.match(points.current.conditions!.join(' '), /評価点の重複を許す/);
  assert.ok(!root(['math', 'poly', 'yes', 'values-shift', 'shift', 'no']).current.techniques!.includes('polynomial-taylor-shift'));
  const distant = root(['math', 'poly', 'yes', 'known-recurrence', 'far-term', 'yes', 'yes']);
  assert.ok(distant.current.techniques!.includes('linear-recurrence-bostan-mori'));
  assert.match(distant.current.conditions!.join(' '), /偶奇/);
});

test('modular exponent search permits noncoprime bases; composite binomials require tables and floor sums require a positive divisor', () => {
  const power = root(['math', 'power-exponent', 'yes', 'yes']);
  assert.ok(power.current.techniques!.includes('primitive-root-discrete-log'));
  assert.match(power.current.conditions!.join(' '), /原始根.*要求しない/);
  assert.ok(!root(['math', 'power-exponent', 'yes', 'no']).current.techniques!.includes('primitive-root-discrete-log'));
  assert.ok(!root(['math', 'count', 'composite-binomial', 'no']).current.techniques!.includes('binomial-composite-prime-power'));
  const composite = root(['math', 'count', 'composite-binomial', 'yes', 'yes']);
  assert.match(composite.current.conditions!.join(' '), /素因数指数/);
  assert.ok(!root(['math', 'linear-floor-sum', 'no']).current.techniques!.includes('floor-sum-euclidean'));
  assert.match(root(['math', 'linear-floor-sum', 'yes', 'yes']).current.conditions!.join(' '), /符号付き/);
});

test('static ranks expose both compatible candidates and update ranks retain event time order', () => {
  const staticRank = root(['ranges', 'static', 'kth', 'yes', 'yes', 'yes']);
  assert.ok(staticRank.current.techniques!.includes('persistent-prefix-kth'));
  assert.ok(staticRank.current.techniques!.includes('wavelet-range-kth'));
  const dynamicRank = root(['ranges', 'change', 'order-statistics', 'kth', 'yes', 'yes']);
  assert.ok(dynamicRank.current.techniques!.includes('offline-kth-divide-values'));
  assert.match(dynamicRank.current.conditions!.join(' '), /時刻順/);
  assert.ok(!root(['ranges', 'change', 'order-statistics', 'kth', 'no']).current.techniques!.includes('offline-kth-divide-values'));
  const frequencyMex = root(['ranges', 'change', 'order-statistics', 'frequency-mex', 'yes', 'yes', 'yes']);
  assert.match(frequencyMex.current.conditions!.join(' '), /出現回数の未出現値/);
  assert.ok(!root(['ranges', 'change', 'order-statistics', 'frequency-mex', 'yes', 'no']).current.techniques!.includes('mo-with-updates'));
});

test('offline thresholds require monotone time, domination handles duplicates, and rank search requires nonnegative counts', () => {
  assert.ok(!root(['ranges', 'first-threshold', 'yes', 'no']).current.techniques!.includes('parallel-binary-search-time'));
  const time = root(['ranges', 'first-threshold', 'yes', 'yes', 'yes']);
  assert.match(time.current.conditions!.join(' '), /単調/);
  assert.ok(!root(['geometry', 'dominated', 'yes', 'no']).current.techniques!.includes('cdq-dominance'));
  const dominance = root(['geometry', 'dominated', 'yes', 'yes']);
  assert.match(dominance.current.conditions!.join(' '), /完全な重複/);
  assert.ok(!root(['ranges', 'remove-rank', 'no']).current.techniques!.includes('fenwick-prefix-lower-bound'));
  assert.match(root(['ranges', 'remove-rank', 'yes']).current.conditions!.join(' '), /非負/);
});

test('overlapping set updates require table memory and uniform range additions preserve sorted block order', () => {
  const sets = root(['set-operations', 'sum-updates', 'yes', 'yes', 'yes']);
  assert.ok(sets.current.techniques!.includes('sqrt-heavy-light-sets'));
  assert.match(sets.current.conditions!.join(' '), /H×S.*H×M/);
  assert.ok(!root(['set-operations', 'sum-updates', 'yes', 'yes', 'no']).current.techniques!.includes('sqrt-heavy-light-sets'));
  const count = root(['ranges', 'change', 'range-add-count', 'yes', 'yes']);
  assert.match(count.current.conditions!.join(' '), /順序は全体加算で変わらない/);
  const weighted = root(['ranges', 'change', 'weighted-relative', 'yes']);
  assert.ok(weighted.current.techniques!.includes('alternating-linear-weight-prefix'));
});

test('XOR rank removes equal values, and dynamic XOR walks require revisits and full rollback context', () => {
  assert.ok(!root(['math', 'xor', 'ranked-values', 'no']).current.techniques!.includes('xor-basis-kth'));
  const rank = root(['math', 'xor', 'ranked-values', 'yes', 'yes']);
  assert.match(rank.current.conditions!.join(' '), /重複排除/);
  assert.ok(!root(['graphs', 'distance', 'xor-walk', 'no']).current.techniques!.includes('linear-basis-rollback'));
  assert.ok(!root(['graphs', 'distance', 'xor-walk', 'yes', 'update', 'no']).current.techniques!.includes('linear-basis-rollback'));
  const rollback = root(['graphs', 'distance', 'xor-walk', 'yes', 'update', 'yes', 'yes']);
  assert.match(rollback.current.conditions!.join(' '), /頂点・辺の再訪/);
  assert.match(rollback.current.conditions!.join(' '), /部分技巧.*潜在値/);
});

test('random increment expectation includes the present trial and independently empty places use products', () => {
  const expectation = root(['game-probability', 'repeated-trials', 'gain', 'yes', 'yes']);
  assert.match(expectation.current.conditions!.join(' '), /1\+Σ/);
  assert.match(expectation.current.conditions!.join(' '), /分子の 1/);
  assert.match(expectation.current.conditions!.join(' '), /残り目標は正/);
  const infinite = root(['game-probability', 'repeated-trials', 'gain', 'yes', 'no']);
  assert.equal(infinite.current.id, 'gain-infinite');
  assert.ok(!root(['game-probability', 'repeated-trials', 'vacant', 'no']).current.techniques!.includes('independent-avoidance-product'));
  const vacant = root(['game-probability', 'repeated-trials', 'vacant', 'yes', 'yes']);
  assert.match(vacant.current.conditions!.join(' '), /場所どうし.*独立性は要求しない/);
  assert.ok(!root(['game-probability', 'repeated-trials', 'collect', 'no']).current.techniques!.includes('coupon-collector-state-count'));
});

test('start-time probabilities and order statistics require the distribution stated by their implementations', () => {
  const start = getGraph('probability-processes').nodes.find((node) => node.id === 'start-times')!;
  assert.match(start.title, /固定整数.*独立・等確率/);
  assert.ok(!root(['game-probability', 'repeated-trials', 'active-time', 'no']).current.techniques!.includes('probability-start-time-window'));
  const rankCount = getGraph('probability-processes').nodes.find((node) => node.id === 'rank-count')!;
  assert.match(rankCount.title, /独立.*同じ 1\.\.M の一様分布/);
  assert.ok(!root(['game-probability', 'repeated-trials', 'rank', 'yes', 'no']).current.techniques!.includes('expectation-order-statistic-tail'));
});

test('tree degree bounds, group spans and triggered paths preserve the information sent across their boundary', () => {
  const tree = root(['graphs', 'tree-answer', 'degree-capacity', 'yes', 'yes']);
  assert.ok(tree.current.techniques!.includes('tree-dp-degree-capacity'));
  assert.match(tree.current.conditions!.join(' '), /上限 0.*不可能/);
  assert.match(tree.current.conditions!.join(' '), /追加の大域制約はなく/);
  assert.ok(!root(['graphs', 'tree-answer', 'degree-capacity', 'yes', 'no']).current.techniques!.includes('tree-dp-degree-capacity'));
  const groups = root(['dp', 'group-spread', 'yes', 'yes', 'yes']);
  assert.ok(groups.current.techniques!.includes('dp-open-groups-gap-cost'));
  assert.match(groups.current.conditions!.join(' '), /同じ値.*区別/);
  assert.ok(!root(['graphs', 'forest-trigger', 'no']).current.techniques!.includes('forest-trigger-minimum-continuation'));
  const forest = root(['graphs', 'forest-trigger', 'yes', 'yes', 'yes']);
  assert.match(forest.current.conditions!.join(' '), /非負/);
});

test('permutation construction separates arbitrary swaps, component impossibility and reusable allowed pairs', () => {
  const arbitrary = root(['ranges', 'sort-permutation', 'arbitrary', 'yes']);
  assert.ok(arbitrary.current.techniques!.includes('permutation-cycle-minimum-swaps'));
  const impossible = root(['ranges', 'sort-permutation', 'allowed-pairs', 'no']);
  assert.equal(impossible.current.id, 'swap-impossible');
  const limited = root(['ranges', 'sort-permutation', 'allowed-pairs', 'yes', 'no']);
  assert.ok(!limited.current.techniques!.includes('permutation-tree-leaf-fix'));
  const allowed = root(['ranges', 'sort-permutation', 'allowed-pairs', 'yes', 'yes', 'yes']);
  assert.match(allowed.current.conditions!.join(' '), /何度でも/);
});

test('graph construction retains its distance-count bounds, and appended decimal integers stay as strings', () => {
  const star = root(['thinking', 'graph-build', 'yes', 'yes', 'yes']);
  assert.ok(star.current.techniques!.includes('construct-star-distance-two'));
  assert.match(star.current.conditions!.join(' '), /その組だけ/);
  assert.equal(root(['thinking', 'graph-build', 'yes', 'yes', 'no']).current.id, 'star-impossible');
  assert.ok(!root(['thinking', 'graph-build', 'yes', 'no']).current.techniques!.includes('construct-star-distance-two'));
  const digits = root(['ranges', 'append-digits', 'yes', 'yes']);
  assert.ok(digits.current.techniques!.includes('append-digits-lexicographic'));
  assert.match(digits.current.conditions!.join(' '), /64 bit.*文字列/);
  assert.match(digits.current.conditions!.join(' '), /すべて 9/);
  assert.match(digits.current.conditions!.join(' '), /任意の 0\.\.9/);
});


test('natural purpose entries reach detailed questions directly without a second mode selector', () => {
  assert.equal(root(['interactive-oracles']).current.id, 'response');
  assert.equal(root(['heuristic', 'no']).current.id, 'model');
  assert.equal(root(['game-probability', 'win']).current.id, 'ending');
  assert.equal(root(['geometry', 'far']).current.id, 'diameter-hull');
  assert.equal(root(['geometry', 'sign']).current.id, 'goal');
  assert.equal(root(['geometry', 'manhattan']).current.id, 'goal');
  for (const fixture of walks) for (const answer of fixture.choices) {
    assert.ok(!['oracle', 'local-structure', 'precise-geometric', 'specific-rules'].includes(answer));
  }
  const generic = root(['heuristic', 'no', 'other', 'yes', 'yes', 'no', 'yes', 'yes']);
  assert.ok(generic.current.techniques!.includes('simulated-annealing'));
});

test('legacy orientation routes to the actual use and every diagram is reachable from a domain root', () => {
  const intersection = root(['geometry', 'other-geometric', 'yes', 'segments', 'yes', 'yes']);
  assert.ok(intersection.current.techniques!.includes('segment-intersection-orientation'));
  const orientation = root(['geometry', 'sign', 'orientation', 'yes']);
  assert.match(orientation.current.conditions!.join(' '), /三点の向きの判定部品/);
  const reached = new Set<string>();
  function visit(id: string) {
    if (reached.has(id)) return;
    reached.add(id);
    for (const node of getGraph(id).nodes) if (node.type === 'route') visit(node.graph!);
  }
  for (const entry of graphs.filter((graph) => graph.entry)) visit(entry.id);
  assert.equal(reached.size, graphs.length);
});

test('nearest, furthest and narrowest geometry keep different reductions and exact arithmetic guards', () => {
  const closest = root(['geometry', 'closest', 'yes', 'yes']);
  assert.ok(closest.current.techniques!.includes('geometry-closest-pair'));
  assert.match(closest.current.conditions!.join(' '), /重複点.*0/);
  assert.ok(!root(['geometry', 'closest', 'no']).current.techniques!.includes('geometry-closest-pair'));
  const far = root(['geometry', 'far', 'yes', 'yes']);
  assert.ok(far.current.techniques!.includes('convex-diameter-calipers'));
  assert.ok(far.current.techniques!.includes('rotating-calipers'));
  const width = root(['geometry', 'width', 'yes', 'yes']);
  assert.ok(width.current.techniques!.includes('convex-minimum-width'));
  assert.match(width.current.conditions!.join(' '), /非凸.*凸包/);
  assert.match(width.current.conditions!.join(' '), /全共線.*0/);
});

test('convex membership, winding and segment intersection require the shape and boundary they actually handle', () => {
  const convex = root(['geometry', 'sign', 'convex-point', 'yes', 'yes']);
  assert.ok(convex.current.techniques!.includes('convex-point-membership'));
  assert.ok(!root(['geometry', 'sign', 'convex-point', 'no']).current.techniques!.includes('convex-point-membership'));
  const simple = root(['geometry', 'sign', 'simple-point', 'yes', 'yes']);
  assert.ok(simple.current.techniques!.includes('polygon-winding-integer'));
  assert.match(simple.current.conditions!.join(' '), /半開区間/);
  const segments = root(['geometry', 'sign', 'segments', 'yes', 'yes']);
  assert.ok(segments.current.techniques!.includes('segment-intersection-orientation'));
  assert.match(segments.current.conditions!.join(' '), /端点接触.*共線/);
  const sum = root(['geometry', 'region-sum', 'yes', 'yes']);
  assert.ok(sum.current.techniques!.includes('convex-minkowski-sum'));
  assert.match(sum.current.conditions!.join(' '), /三点以上の狭義凸/);
  assert.match(sum.current.conditions!.join(' '), /連続座標.*格子点や頂点だけに限定しない/);
  assert.ok(!root(['geometry', 'region-sum', 'yes', 'no']).current.techniques!.includes('convex-minkowski-sum'));
});

test('direction counting handles zero vectors, unique collinear starts and nondegenerate triangle angles', () => {
  const collinear = root(['geometry', 'directions', 'collinear', 'yes', 'yes']);
  assert.ok(collinear.current.techniques!.includes('collinear-direction-gcd'));
  assert.match(collinear.current.conditions!.join(' '), /最小添字/);
  assert.match(collinear.current.conditions!.join(' '), /K=1 は無限/);
  const perpendicular = root(['dp', 'perpendicular-subset', 'yes', 'yes']);
  assert.ok(perpendicular.current.techniques!.includes('perpendicular-direction-pairs'));
  assert.match(perpendicular.current.conditions!.join(' '), /ゼロベクトル.*単独/);
  assert.ok(!root(['geometry', 'directions', 'triangles', 'no']).current.techniques!.includes('angle-vector-two-pointers'));
  const triangles = root(['geometry', 'directions', 'triangles', 'yes', 'yes']);
  assert.match(triangles.current.conditions!.join(' '), /180 度未満/);
});

test('Manhattan connectivity uses half-open direction regions and convex area cuts compare both sides of a threshold', () => {
  const connect = root(['geometry', 'manhattan', 'connect', 'yes', 'yes']);
  assert.ok(connect.current.techniques!.includes('manhattan-nearest-octants'));
  assert.match(connect.current.conditions!.join(' '), /半開/);
  assert.match(connect.current.conditions!.join(' '), /重複座標.*0 の辺/);
  const maximum = root(['geometry', 'manhattan', 'maximum', 'yes']);
  assert.ok(maximum.current.techniques!.includes('manhattan-transform'));
  assert.ok(!root(['geometry', 'area-cut', 'no']).current.techniques!.includes('convex-polygon-half-area'));
  const cut = root(['geometry', 'area-cut', 'yes', 'yes', 'yes']);
  assert.ok(cut.current.techniques!.includes('convex-polygon-half-area'));
  assert.match(cut.current.conditions!.join(' '), /直前.*直後/);
});

test('normal game moves require their exact subtraction, transfer, divisor and tree-removal rules', () => {
  const normal = ['game-probability', 'win', 'no-move'];
  const take = root([...normal, 'bounded-take', 'yes']);
  assert.ok(take.current.techniques!.includes('bounded-take-grundy-period'));
  assert.match(take.current.conditions!.join(' '), /最後に取る側が負ける.*使わない/);
  assert.ok(!root([...normal, 'bounded-take', 'no']).current.techniques!.includes('bounded-take-grundy-period'));
  const stairs = root([...normal, 'stairs', 'yes']);
  assert.match(stairs.current.conditions!.join(' '), /段 1/);
  const divisor = root([...normal, 'proper-divisor', 'yes']);
  assert.ok(divisor.current.techniques!.includes('divisor-game-prime-count'));
  assert.match(divisor.current.conditions!.join(' '), /すべて.*真の正の約数/);
  const cut = root([...normal, 'cut-tree', 'yes']);
  assert.match(cut.current.conditions!.join(' '), /根を含まない部分.*すべて/);
});

test('games with increasing state components prove a bound, and pair removal preserves only its residual set', () => {
  const normal = ['game-probability', 'win', 'no-move'];
  const colors = root([...normal, 'two-colors', 'yes', 'yes']);
  assert.ok(colors.current.techniques!.includes('grundy-conserved-state-bound'));
  assert.match(colors.current.conditions!.join(' '), /b\+w\(w\+1\)\/2/);
  assert.ok(!root([...normal, 'two-colors', 'yes', 'no']).current.techniques!.includes('grundy-conserved-state-bound'));
  const pair = root([...normal, 'compatible-pair', 'yes']);
  assert.ok(pair.current.techniques!.includes('pair-removal-mask-game'));
  assert.match(pair.current.conditions!.join(' '), /相性は固定/);
});

test('cyclic word games allow reuse and draws; weighted boards check immediate wins before odd-total scoring', () => {
  const cycle = root(['strings', 'reusable-word-game', 'yes', 'yes']);
  assert.ok(cycle.current.techniques!.includes('retrograde-winning-draw'));
  assert.match(cycle.current.conditions!.join(' '), /何度でも/);
  assert.ok(!root(['strings', 'reusable-word-game', 'no']).current.techniques!.includes('retrograde-winning-draw'));
  const board = root(['game-probability', 'win', 'immediate-board', 'yes', 'yes']);
  assert.ok(board.current.techniques!.includes('weighted-board-terminal-minimax'));
  assert.match(board.current.conditions!.join(' '), /満盤.*より先/);
  assert.match(board.current.conditions!.join(' '), /総和は奇数/);
});

test('distance and unimodal value oracles check structural guarantees and actual query budgets', () => {
  assert.ok(!root(['interactive-oracles', 'tree-distance', 'no']).current.techniques!.includes('interactive-tree-diameter'));
  const tree = root(['interactive-oracles', 'tree-distance', 'yes', 'yes']);
  assert.ok(tree.current.techniques!.includes('interactive-tree-diameter'));
  assert.match(tree.current.conditions!.join(' '), /2\(N−1\)/);
  assert.match(tree.current.conditions!.join(' '), /自己距離.*質問しない/);
  assert.ok(!root(['interactive-oracles', 'unimodal-value', 'no']).current.techniques!.includes('interactive-fibonacci-maximum'));
  assert.ok(!root(['interactive-oracles', 'unimodal-value', 'yes', 'no']).current.techniques!.includes('interactive-fibonacci-maximum'));
  const unimodal = root(['interactive-oracles', 'unimodal-value', 'yes', 'yes']);
  assert.match(unimodal.current.conditions!.join(' '), /非負.*狭義/);
  assert.match(unimodal.current.conditions!.join(' '), /15 回/);
});

test('missing-rook and simultaneous group tests require single-target consistency and retain generic navigation', () => {
  assert.ok(!root(['interactive-oracles', 'rectangle-count', 'no']).current.techniques!.includes('interactive-missing-rook'));
  const rook = root(['interactive-oracles', 'rectangle-count', 'yes', 'yes']);
  assert.ok(rook.current.techniques!.includes('interactive-missing-rook'));
  assert.match(rook.current.conditions!.join(' '), /各行・各列.*高々一個/);
  const batch = root(['interactive-oracles', 'batch-subsets', 'yes', 'yes']);
  assert.ok(batch.current.techniques!.includes('interactive-bit-group-testing'));
  assert.match(batch.current.conditions!.join(' '), /不良は一つ/);
  assert.ok(!root(['interactive-oracles', 'batch-subsets', 'no']).current.techniques!.includes('interactive-bit-group-testing'));
  assert.ok(root(['interactive-oracles', 'navigation', 'yes']).current.techniques!.includes('interactive'));
});

test('rectangle score changes retain legality and one-edge candidate optimality is restricted to the fixed neighborhood', () => {
  const model = ['heuristic', 'no', 'rectangles'];
  const delta = root([...model, 'delta', 'yes', 'yes']);
  assert.ok(delta.current.techniques!.includes('heuristic-rectangle-score-delta'));
  assert.match(delta.current.conditions!.join(' '), /未丸め/);
  assert.ok(!root([...model, 'delta', 'yes', 'no']).current.techniques!.includes('heuristic-rectangle-score-delta'));
  const edge = root([...model, 'one-edge', 'yes', 'yes', 'yes']);
  assert.match(edge.current.conditions!.join(' '), /三辺|一辺以外/);
  assert.match(edge.current.conditions!.join(' '), /希望面積/);
  assert.match(edge.current.conditions!.join(' '), /最適解を保証しない/);
});

test('tile-path changes restore tile IDs and relaxed reachable bounds never underestimate possible continuation', () => {
  const model = ['heuristic', 'no', 'path-tail'];
  const tail = root([...model, 'tail', 'yes', 'yes']);
  assert.ok(tail.current.techniques!.includes('heuristic-path-tail-rollback'));
  assert.match(tail.current.conditions!.join(' '), /マスではなくタイル ID/);
  assert.match(tail.current.conditions!.join(' '), /初期マス/);
  const upper = root([...model, 'upper', 'yes', 'yes']);
  assert.match(upper.current.conditions!.join(' '), /同 ID の別マスへ入れない/);
  assert.match(upper.current.conditions!.join(' '), /過小.*捨てない/);
  assert.match(upper.current.conditions!.join(' '), /最大点が負なら 0/);
  assert.ok(!root([...model, 'upper', 'yes', 'no']).current.techniques!.includes('heuristic-path-reachable-upper-bound'));
});

test('route reversals and paired insertions enforce ordering, symmetric reversal cost and the same-gap case', () => {
  const model = ['heuristic', 'no', 'ordered-route'];
  assert.ok(!root([...model, 'reverse', 'no']).current.techniques!.includes('heuristic-precedence-two-opt'));
  const reverse = root([...model, 'reverse', 'yes', 'yes']);
  assert.match(reverse.current.conditions!.join(' '), /対称/);
  assert.match(reverse.current.conditions!.join(' '), /各一回/);
  assert.match(reverse.current.conditions!.join(' '), /両方.*区間内/);
  const insert = root([...model, 'insert-pair', 'yes', 'yes']);
  assert.ok(insert.current.techniques!.includes('heuristic-paired-insertion-prefix'));
  assert.match(insert.current.conditions!.join(' '), /同じ隙間.*別に比較/);
});

test('exact scheduling queries share gap evaluation, while candidate swaps use sequential reversible changes', () => {
  const exact = root(['ranges', 'schedule-change', 'one-day', 'yes']);
  assert.ok(exact.current.techniques!.includes('heuristic-schedule-gap-delta'));
  assert.match(exact.current.conditions!.join(' '), /固定係数/);
  const swap = root(['heuristic', 'no', 'schedule', 'swap-days', 'yes']);
  assert.ok(swap.current.techniques!.includes('heuristic-schedule-swap-transaction'));
  assert.match(swap.current.conditions!.join(' '), /一つ目を適用した状態/);
  assert.match(swap.current.conditions!.join(' '), /復元/);
});

test('coverage candidates and deltas keep active stations fixed and separate omitted constant costs', () => {
  const model = ['heuristic', 'no', 'circle-cover'];
  const candidates = root([...model, 'candidates', 'yes', 'yes']);
  assert.ok(candidates.current.techniques!.includes('heuristic-radius-threshold-candidates'));
  assert.match(candidates.current.conditions!.join(' '), /最小整数半径/);
  const delta = root([...model, 'delta', 'yes', 'yes']);
  assert.ok(delta.current.techniques!.includes('heuristic-cover-count-delta'));
  assert.match(delta.current.conditions!.join(' '), /0→1.*1→0/);
  assert.match(delta.current.conditions!.join(' '), /ON ケーブル費/);
  assert.ok(!root([...model, 'delta', 'no']).current.techniques!.includes('heuristic-cover-count-delta'));
});

test('URL history round trips domain choices and legacy yes/no/unknown safely', () => {
  const changedRange = { graph: 'range-aggregate-goals', answers: ['change'], trail: [{ graph: 'ranges', answers: ['aggregate-goals'] }] };
  for (const state of [changedRange, { graph: 'dp-affine', answers: ['yes', 'no', 'unknown'] }]) {
    assert.deepEqual(parseFlowHash(serializeFlowHash(state)), state);
  }
  assert.deepEqual(parseFlowHash('#flow=ranges&steps=c:change'), changedRange);
  assert.deepEqual(parseFlowHash(serializeFlowHash({ graph: 'ranges', answers: ['change'] })), changedRange);
  assert.deepEqual(parseFlowHash('#flow=missing&steps=y'), initialState());
  assert.deepEqual(parseFlowHash('#flow=range-update&steps=c:affine,x,c:past'), {
    graph: 'range-uniform-value-effects', answers: ['affine'], trail: [{ graph: 'range-update', answers: ['uniform-value-effects'] }],
  });
  assert.deepEqual(parseFlowHash('#flow=overview&steps=c:exact'), initialState());
  assert.deepEqual(parseFlowHash('#flow=ranges&steps=c:%ZZ'), initialState());
  assert.deepEqual(parseFlowHash('#flow=dp&steps=' + 'y,'.repeat(3000)), initialState());
  assert.deepEqual(sanitizeState({ graph: 'ranges', answers: ['change', '<script>', 'static'], current: 'anything' }), changedRange);
});

test('cross-chart answers keep a domain entry in shared URLs and backtracking restores its question', () => {
  const start = initialState('ranges');
  const domain = { graph: 'ranges', answers: ['aggregate-goals'] };
  const category = enterFlowRoute(answerState(start, 'aggregate-goals'));
  assert.deepEqual(category, { graph: 'range-aggregate-goals', answers: [], trail: [domain] });
  const parent = answerState(category, 'change');
  const entered = enterFlowRoute(parent);
  assert.equal(entered.graph, 'range-update');
  const rangeParent = { graph: 'range-aggregate-goals', answers: ['change'] };
  assert.deepEqual(entered, { graph: 'range-update', answers: [], trail: [domain, rangeParent] });
  const pointCategory = enterFlowRoute(answerState(entered, 'point-value-goals'));
  assert.deepEqual(pointCategory, {
    graph: 'range-point-value-goals', answers: [],
    trail: [domain, rangeParent, { graph: 'range-update', answers: ['point-value-goals'] }],
  });
  const child = enterFlowRoute(answerState(pointCategory, 'order-statistics'));
  assert.equal(child.graph, 'range-changing-statistics');
  assert.deepEqual(child.trail, [
    domain, rangeParent, { graph: 'range-update', answers: ['point-value-goals'] },
    { graph: 'range-point-value-goals', answers: ['order-statistics'] },
  ]);
  assert.deepEqual(parseFlowHash(serializeFlowHash(answerState(child, 'kth'))), answerState(child, 'kth'));
  const back = backFlowState(child);
  assert.deepEqual(back, pointCategory);
  const updateBack = backFlowState(back);
  assert.deepEqual(updateBack, entered);
  const categoryBack = backFlowState(updateBack);
  assert.deepEqual(categoryBack, category);
  assert.deepEqual(backFlowState(categoryBack), start);
  assert.deepEqual(sanitizeState({ graph: 'dp', answers: [], trail: [parent] }), initialState('dp'));
});

test('results and routes reject trailing choices, while domain walking follows its detailed charts', () => {
  const state = { graph: 'range-aggregate-goals', answers: ['change'], trail: [{ graph: 'ranges', answers: ['aggregate-goals'] }] };
  assert.equal(evaluateState(state).current.type, 'route');
  assert.deepEqual(answerState(state, 'affine'), state);
  assert.deepEqual(answerState({ graph: 'ranges', answers: ['change'] }, 'affine'), state);
  const result = sanitizeState({ graph: 'range-update', answers: ['affine', 'yes'] });
  assert.equal(evaluateState(result).current.type, 'result');
  assert.ok(evaluateState(result).current.techniques!.includes('affine-lazy-composition'));
  assert.deepEqual(answerState(result, 'past'), result);
  assert.equal(root(['ranges', 'change']).current.id, 'change-kind');
  assert.throws(() => walkFromRoot(['an-algorithm-name'], 'ranges'), /Invalid root choice/);
  assert.equal(walkFromRoot([]).graph.id, 'ranges');
  assert.ok(root(['fixed-output']).current.techniques!.includes('output-only'));
});

test('SVG and accessible text contain the exact canonical choices and link targets', () => {
  for (const graph of graphs) {
    const svg = renderFlowSvg(graph);
    assert.match(svg, /^<svg /);
    assert.doesNotMatch(svg, />QUESTION<|>DETAIL CHART<|>CANDIDATES/);
    for (const node of graph.nodes) {
      assert.ok(svg.includes(`data-node="${node.id}"`));
      for (const id of node.techniques ?? []) assert.ok(svg.includes(`/flowchartcp/techniques/${id}/`));
      if (node.type === 'question') for (const { id } of getNodeOptions(node)) assert.ok(svg.includes(`data-edge="${node.id}:${id}:${node.answers![id]}"`));
    }
  }
  const html = renderFlowHtml();
  for (const graph of graphs) {
    assert.ok(html.includes(`id="diagram-${graph.id}"`));
    for (const node of graph.nodes) assert.ok(html.includes(`id="flow-text-${graph.id}-${node.id}"`));
  }
  assert.ok(html.includes('適用条件'));
  assert.ok(html.includes('<noscript>'));
});

test('renderers escape untrusted text and support both root and GitHub Pages base paths', () => {
  const original = getGraph('range-static');
  const graph: FlowGraph = { ...original, title: '<script>unsafe</script>', nodes: original.nodes.map((node) => ({ ...node, title: `${node.title} <img onerror="alert(1)">` })) };
  const svg = renderFlowSvg(graph, '/', { 'prefix-sum': '<svg onload="alert(1)">' });
  assert.ok(!svg.includes('<script>unsafe'));
  assert.ok(!svg.includes('<img onerror='));
  assert.ok(svg.includes('&lt;script&gt;'));
  assert.ok(svg.includes('/techniques/prefix-sum/'));
  assert.ok(!svg.includes('//techniques/'));
  const html = renderFlowHtml('/flowchartcp/', { 'prefix-sum': '</script><script>alert(1)</script>' });
  assert.ok(!html.includes('</script><script>alert(1)</script>'));
  assert.ok(html.includes('\\u003c/script\\u003e'));
});

test('validator reports broken choices, missing links, cycles and cross-chart route cycles', () => {
  const bad: FlowGraph = { id: 'bad', title: 'bad', description: 'bad', root: 'a', nodes: [
    { id: 'a', type: 'question', title: 'a', answers: { yes: 'a', no: 'missing', unknown: 'a' } },
    { id: 'orphan', type: 'result', title: 'orphan', techniques: [], conditions: [] },
  ] };
  const errors = validateGraphs([bad]);
  assert.ok(errors.some((error) => error.includes('missing no target')));
  assert.ok(errors.some((error) => error.includes('cycle')));
  assert.ok(errors.some((error) => error.includes('unreachable orphan')));
  const cyclic: FlowGraph = { id: 'route', title: 'route', description: 'route', root: 'go', nodes: [{ id: 'go', type: 'route', title: 'go', graph: 'route' }] };
  assert.ok(validateGraphs([cyclic]).some((error) => error.includes('Graph route cycle')));
});

test('ordinary string, assignment and grid entrances expose distinct problem purposes', () => {
  assert.equal(root(['flow-matching']).current.id, 'purpose');
  assert.equal(root(['graphs', 'assignment']).current.id, 'purpose');
  assert.equal(root(['grid-arrangements']).current.id, 'goal');
  assert.equal(root(['dp', 'capacity']).current.id, 'capacity-purpose');
  assert.equal(root(['dp', 'digits']).current.id, 'goal');
  const unrestricted = root(['strings', 'subsequence', 'yes', 'free', 'yes']);
  const nonadjacent = root(['strings', 'subsequence', 'yes', 'nonadjacent']);
  assert.ok(unrestricted.current.techniques!.includes('dp-last-occurrence'));
  assert.ok(!unrestricted.current.techniques!.includes('subsequence-nonadjacent-last-range'));
  assert.ok(nonadjacent.current.techniques!.includes('subsequence-nonadjacent-last-range'));
  assert.ok(!nonadjacent.current.techniques!.includes('dp-last-occurrence'));
  const dictionary = root(['strings', 'pattern', 'many-patterns', 'occurrences']);
  assert.equal(dictionary.current.id, 'dictionary-changes');
  const ranking = root(['strings', 'substrings', 'no', 'yes']);
  assert.equal(ranking.current.id, 'rank-counting');
});

test('the thirty new technique mappings have original evidence and guarded root paths', () => {
  const files = ['string-extension-problem-features.json', 'dp-extension-problem-features.json', 'flow-matching-problem-features.json'];
  const rows = files.flatMap((file) => JSON.parse(readFileSync(`data/${file}`, 'utf8')));
  assert.equal(rows.length, 30);
  for (const row of rows) {
    const fixture = walks.find((walk: { statementUrl: string; expectedTechniqueIds: string[] }) => walk.statementUrl === row.url && row.techniqueIds.every((id: string) => walk.expectedTechniqueIds.includes(id)));
    assert.ok(fixture, `${row.problemId}: new root fixture`);
    assert.equal(fixture.reviewStatus, 'verified');
    assert.ok(fixture.statementEvidenceUrl.startsWith('https://'));
    const finished = root(fixture.choices, fixture.entryGraphId);
    assert.equal(finished.current.type, 'result');
    for (const id of row.techniqueIds) assert.ok(finished.current.techniques!.includes(id));
    const last = fixture.choices.at(-1);
    if (last !== 'yes') continue; // The nonadjacent position rule itself is a feature choice.
    const prefix = fixture.choices.slice(0, -1);
    const unsure = root([...prefix, 'unknown'], fixture.entryGraphId);
    assert.equal(unsure.current.type, 'question', `${row.problemId}: confirm unknown`);
    assert.ok(!unsure.current.techniques?.includes(row.techniqueIds[0]));
    const rejected = root([...prefix, 'no'], fixture.entryGraphId);
    if (row.techniqueIds[0] === 'matrix-margin-lower-offset') {
      assert.equal(rejected.current.id, 'matrix-impossible');
      assert.match(rejected.current.conditions!.join(' '), /残量.*不一致/);
    } else {
      assert.ok(!rejected.current.techniques?.includes(row.techniqueIds[0]), `${row.problemId}: prerequisite not met`);
    }
  }
});

test('subsequence buckets freeze one position and shortest absent strings prioritize length', () => {
  const batch = root(['strings', 'subsequence', 'many-queries', 'together', 'yes']);
  assert.ok(batch.current.techniques!.includes('subsequence-waiting-buckets'));
  assert.match(batch.current.conditions!.join(' '), /高々一回/);
  const online = root(['strings', 'subsequence', 'many-queries', 'online', 'yes']);
  assert.ok(online.current.techniques!.includes('substring-subsequence-next'));
  assert.ok(!online.current.techniques!.includes('subsequence-waiting-buckets'));
  const absent = root(['strings', 'subsequence', 'absent', 'yes', 'yes']);
  assert.match(absent.current.conditions!.join(' '), /最短長.*最小/);
  assert.ok(!root(['strings', 'subsequence', 'absent', 'no']).current.techniques!.includes('shortest-absent-subsequence'));
  const missingTarget = root(['strings', 'subsequence', 'delete-gap', 'no']);
  assert.ok(!missingTarget.current.techniques!.includes('subsequence-delete-gap'));
});

test('substring ranks separate output string identity from occurrence multiplicity', () => {
  const prefix = ['strings', 'substrings', 'no', 'yes'];
  const distinct = root([...prefix, 'distinct', 'yes']);
  const multiplicity = root([...prefix, 'occurrences', 'yes']);
  assert.ok(distinct.current.techniques!.includes('sam-kth-distinct-substring'));
  assert.ok(!distinct.current.techniques!.includes('sam-kth-occurrence-substring'));
  assert.ok(multiplicity.current.techniques!.includes('sam-kth-occurrence-substring'));
  assert.ok(!multiplicity.current.techniques!.includes('sam-kth-distinct-substring'));
  assert.match(distinct.current.conditions!.join(' '), /一回ずつ/);
  assert.match(multiplicity.current.conditions!.join(' '), /出現位置ごと/);
  const lengths = root(['strings', 'substrings', 'length-distribution', 'yes']);
  assert.ok(lengths.current.techniques!.includes('sam-length-distribution'));
  assert.match(lengths.current.conditions!.join(' '), /最大長\+1/);
});

test('live dictionary changes, unit abc edits and dynamic hashes retain essential conditions', () => {
  const live = root(['strings', 'pattern', 'many-patterns', 'occurrences', 'yes', 'yes']);
  assert.match(live.current.conditions!.join(' '), /内容は途中で増減しない/);
  assert.match(live.current.conditions!.join(' '), /有効化・無効化/);
  const fixed = root(['strings', 'pattern', 'many-patterns', 'occurrences', 'no', 'yes']);
  assert.ok(fixed.current.techniques!.includes('aho-failure-aggregation'));
  assert.ok(!fixed.current.techniques!.includes('aho-active-failure-subtree'));
  const edits = root(['strings', 'subsequence', 'avoid-updates', 'yes', 'yes']);
  assert.match(edits.current.conditions!.join(' '), /a・b・c.*abc/);
  assert.match(edits.current.conditions!.join(' '), /最少削除数と最少置換数が等しい/);
  const hash = root(['strings', 'palindrome', 'point-updates', 'yes', 'yes']);
  assert.match(hash.current.conditions!.join(' '), /衝突.*許容/);
  const order = root(['strings', 'palindrome', 'point-updates', 'yes']).current;
  assert.equal(order.id, 'update-point-check');
  assert.equal(order.type, 'question');
  assert.match(order.explanation!, /正順では右区間の長さで左区間/);
  const exact = root(['strings', 'palindrome', 'point-updates', 'no']);
  assert.equal(exact.current.id, 'exact-updates-budget');
  const costly = root(['strings', 'palindrome', 'point-updates', 'no', 'no']);
  assert.ok(!costly.current.techniques!.includes('rolling-hash'));
  assert.ok(!costly.current.techniques!.includes('suffix-array'));
  const ordinary = root(['strings', 'palindrome', 'no', 'no', 'yes', 'yes', 'yes', 'yes']);
  assert.ok(ordinary.current.techniques!.includes('palindrome-update-hash-monoid'));
});

test('mandatory pairing is feasibility, while additive unit-resource profits retain every size', () => {
  const compulsory = root(['grid-arrangements', 'neighbor-pairs', 'mandatory', 'yes', 'yes']);
  assert.ok(compulsory.current.techniques!.includes('mandatory-matching-lower-bounds'));
  assert.match(compulsory.current.conditions!.join(' '), /存在.*最大の組数ではない/);
  const size = root(['grid-arrangements', 'neighbor-pairs', 'maximize']);
  assert.ok(size.current.techniques!.includes('matching'));
  assert.ok(!size.current.techniques!.includes('mandatory-matching-lower-bounds'));
  const profit = root(['flow-matching', 'profit', 'each', 'yes', 'yes']);
  assert.ok(profit.current.techniques!.includes('matching-profit-each-cardinality'));
  const additive = root(['flow-matching', 'profit', 'each', 'yes']).current;
  assert.equal(additive.id, 'profit-quantity');
  assert.equal(additive.type, 'question');
  assert.match(additive.title, /利益の和.*追加の利益・費用/);
  assert.ok(!root(['flow-matching', 'profit', 'each', 'no']).current.techniques!.includes('matching-profit-each-cardinality'));
  assert.match(profit.current.conditions!.join(' '), /整数 k ごとの値/);
  assert.match(profit.current.conditions!.join(' '), /Ck から.*最小費用を引いて/);
});

test('assignment models reject non-product placement, duplicate coordinate collapse and absent perfect correspondence', () => {
  assert.ok(!root(['grid-arrangements', 'rectangle-rooks', 'no']).current.techniques!.includes('rectangle-rook-flow'));
  const rook = root(['grid-arrangements', 'rectangle-rooks', 'yes', 'yes']);
  assert.match(rook.current.conditions!.join(' '), /直積/);
  const points = root(['flow-matching', 'positions', 'translated', 'yes', 'yes']);
  assert.match(points.current.conditions!.join(' '), /正の固定時間/);
  assert.match(points.current.conditions!.join(' '), /出発点・到着点は同数/);
  assert.match(points.current.conditions!.join(' '), /重複せず/);
  const incomplete = root(['flow-matching', 'forced', 'no']);
  assert.ok(!incomplete.current.techniques!.includes('perfect-matching-forced-scc'));
  const forced = root(['flow-matching', 'forced', 'yes', 'yes']);
  assert.match(forced.current.conditions!.join(' '), /全ての合法な完全対応/);
  assert.match(forced.current.conditions!.join(' '), /平行辺/);
});

test('pivot paths, timed covers, dependency selection and corridors preserve their graph domains', () => {
  assert.ok(!root(['graphs', 'through-pivot', 'no']).current.techniques!.includes('vertex-disjoint-through-pivot'));
  const pivot = root(['graphs', 'through-pivot', 'yes', 'yes']);
  assert.match(pivot.current.conditions!.join(' '), /A・B・C は相異なる/);
  assert.match(pivot.current.conditions!.join(' '), /片側へ二本/);
  const schedule = root(['flow-matching', 'schedule', 'yes', 'yes']);
  assert.match(schedule.current.conditions!.join(' '), /循環しない/);
  assert.match(schedule.current.conditions!.join(' '), /初期位置は自由/);
  const closure = root(['dp', 'dependency-selection', 'yes', 'yes']);
  assert.match(closure.current.conditions!.join(' '), /u→v.*u を選んで v を選ばない/);
  assert.match(closure.current.conditions!.join(' '), /個数指定や資源総量.*追加制限はない/);
  assert.match(closure.current.conditions!.join(' '), /空集合.*実現可能な損失の上界/);
  assert.ok(!root(['dp', 'dependency-selection', 'no']).current.techniques!.includes('maximum-profit-closure'));
  const upper = getGraph('selection-closure').nodes.find((node) => node.id === 'capacity-bound')!;
  assert.match(upper.explanation!, /空集合.*正の利益の総和 W/);
  assert.doesNotMatch(upper.title, /全ての有限な損失/);
  const corridors = root(['grid-arrangements', 'corridor-cover', 'yes', 'yes']);
  assert.match(corridors.current.conditions!.join(' '), /費用は一律一/);
  assert.match(corridors.current.conditions!.join(' '), /同じマスへの複数台の配置も許される/);
  assert.ok(!root(['grid-arrangements', 'corridor-cover', 'no']).current.techniques!.includes('grid-corridor-cover-matching'));
});

test('adjacent merge sums, identical boxes and narrow domino boards require their exact models', () => {
  const merge = root(['dp', 'adjacent-merges', 'yes', 'yes']);
  assert.match(merge.current.conditions!.join(' '), /非負.*四点/);
  assert.ok(!root(['dp', 'adjacent-merges', 'yes', 'no']).current.techniques!.includes('knuth-optimization'));
  const bins = root(['dp', 'capacity', 'bins', 'yes', 'yes']);
  assert.match(bins.current.conditions!.join(' '), /同容量/);
  assert.match(bins.current.conditions!.join(' '), /同居禁止はない/);
  assert.ok(!root(['dp', 'capacity', 'bins', 'yes', 'no']).current.techniques!.includes('subset-bin-lexicographic'));
  const domino = root(['grid-arrangements', 'domino-tilings', 'domino', 'yes', 'yes']);
  assert.match(domino.current.conditions!.join(' '), /障害物のない/);
  assert.match(domino.current.conditions!.join(' '), /はみ出すマスが残らない/);
});

test('pair removals count operation order and grid XOR corrects one shared central cell', () => {
  const removal = root(['dp', 'adjacent-pair-removal', 'yes', 'yes']);
  assert.match(removal.current.conditions!.join(' '), /操作の順番.*ペア集合の数とは異なる/);
  assert.ok(!root(['dp', 'adjacent-pair-removal', 'yes', 'no']).current.techniques!.includes('interval-pair-removal-interleavings'));
  const xor = root(['grid-arrangements', 'right-down', 'xor', 'yes', 'yes']);
  assert.match(xor.current.conditions!.join(' '), /同じ中央マス/);
  assert.match(xor.current.conditions!.join(' '), /もう一度.*一回分/);
});

test('digit totals, strict LIS counts and tree cuts retain the minimal sufficient history', () => {
  const digit = root(['math', 'digits', 'required-sum', 'yes', 'yes']);
  assert.ok(digit.current.techniques!.includes('digit-required-count-sum'));
  assert.equal(digit.steps.filter((step) => step.answer === 'required-sum').length, 1);
  assert.match(digit.current.conditions!.join(' '), /先頭へ補ったゼロ.*出現に含めず/);
  assert.match(digit.current.conditions!.join(' '), /sum′=10×sum\+d×count/);
  const dpDigits = root(['dp', 'digits', 'required-sum', 'yes', 'yes']);
  assert.ok(dpDigits.current.techniques!.includes('digit-required-count-sum'));
  const lis = root(['dp', 'generated-lis', 'yes', 'yes']);
  assert.match(lis.current.conditions!.join(' '), /狭義増加/);
  assert.match(lis.current.conditions!.join(' '), /等しい値.*長さを増やさない/);
  const marked = root(['graphs', 'connectivity', 'one-mark-cuts', 'yes', 'yes']);
  assert.match(marked.current.conditions!.join(' '), /子辺を切る場合.*印が一つ/);
  const rooted = root(['graphs', 'tree-answer', 'one-mark-components', 'yes', 'yes']);
  assert.ok(rooted.current.techniques!.includes('tree-one-mark-components'));
});

test('sparse grid paths classify the first obstacle and first arrival uses the opponent one turn earlier', () => {
  const grid = root(['grid-arrangements', 'right-down', 'blocked', 'yes', 'yes']);
  const geometric = root(['geometry', 'grid-paths', 'yes', 'yes']);
  assert.ok(grid.current.techniques!.includes('sparse-grid-blocked-points'));
  assert.ok(geometric.current.techniques!.includes('sparse-grid-blocked-points'));
  assert.match(grid.current.conditions!.join(' '), /最初に通る障害点.*一度だけ/);
  assert.match(grid.current.conditions!.join(' '), /階乗が法の下で可逆/);
  const race = root(['game-probability', 'repeated-trials', 'race', 'yes', 'yes']);
  assert.match(race.current.conditions!.join(' '), /独立.*一様分布/);
  assert.match(race.current.conditions!.join(' '), /t−1 回後に未到着/);
  assert.ok(!root(['game-probability', 'repeated-trials', 'race', 'yes', 'no']).current.techniques!.includes('independent-race-first-hit'));
});


test('batch path sums distinguish edges from inclusive vertices and reject intermediate queries', () => {
  const start = ['graphs', 'tree-range', 'batch-paths'];
  const edges = root([...start, 'edge', 'yes']);
  const vertices = root([...start, 'vertex', 'yes']);
  assert.ok(edges.current.techniques!.includes('tree-path-edge-difference'));
  assert.ok(!edges.current.techniques!.includes('tree-path-vertex-difference'));
  assert.ok(vertices.current.techniques!.includes('tree-path-vertex-difference'));
  assert.match(vertices.current.conditions!.join(' '), /根.*親/);
  assert.ok(!root([...start, 'edge', 'no']).current.techniques!.includes('tree-path-edge-difference'));
  assert.equal(root([...start, 'vertex', 'unknown']).current.type, 'question');
});

test('tree path ranks reject changing values, and ordered functions keep the direction of the path', () => {
  const rank = ['graphs', 'tree-range', 'path-static', 'kth'];
  assert.ok(root([...rank, 'yes', 'yes']).current.techniques!.includes('tree-path-kth-persistent'));
  assert.ok(!root([...rank, 'no']).current.techniques!.includes('tree-path-kth-persistent'));
  assert.ok(!root([...rank, 'yes', 'no']).current.techniques!.includes('tree-path-kth-persistent'));
  const ordered = root(['graphs', 'tree-range', 'path-change', 'directed-compose', 'yes', 'yes']);
  assert.ok(ordered.current.techniques!.includes('tree-path-directed-composition'));
  assert.match(ordered.current.conditions!.join(' '), /交換則は仮定しない/);
  assert.match(ordered.current.conditions!.join(' '), /共通祖先.*二回/);
});

test('nearest marks require addition only and nonnegative tree lengths', () => {
  const start = ['graphs', 'tree-range', 'nearest-marked'];
  assert.ok(root([...start, 'add', 'yes']).current.techniques!.includes('centroid-nearest-marked'));
  assert.ok(!root([...start, 'remove']).current.techniques!.includes('centroid-nearest-marked'));
  assert.ok(!root([...start, 'add', 'no']).current.techniques!.includes('centroid-nearest-marked'));
  assert.equal(root([...start, 'unknown']).current.type, 'question');
});

test('subtree modes are static and root changes preserve the fixed edges', () => {
  const modes = ['graphs', 'tree-range', 'colors', 'mode'];
  assert.ok(root([...modes, 'yes', 'yes']).current.techniques!.includes('subtree-mode-sack'));
  assert.ok(!root([...modes, 'no']).current.techniques!.includes('subtree-mode-sack'));
  const changed = ['graphs', 'tree-range', 'subtree', 'root-change'];
  const result = root([...changed, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('reroot-subtree-complement'));
  assert.match(result.current.conditions!.join(' '), /LCA/);
  assert.ok(!root([...changed, 'no']).current.techniques!.includes('reroot-subtree-complement'));
});

test('last-write subtree and root-path operations require assignments and point reads', () => {
  const start = ['graphs', 'tree-range', 'subtree', 'last-write'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('subtree-path-last-write'));
  assert.match(result.current.conditions!.join(' '), /操作の終点.*部分木/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('subtree-path-last-write'));
  assert.equal(root([...start, 'yes', 'unknown']).current.type, 'question');
});

test('shortest-route statistics require strictly positive weights, while a single discount allows zero', () => {
  const statistics = ['graphs', 'distance', 'normal', 'route-statistics'];
  assert.ok(root([...statistics, 'yes', 'yes']).current.techniques!.includes('shortest-tight-dag-statistics'));
  assert.ok(!root([...statistics, 'no']).current.techniques!.includes('shortest-tight-dag-statistics'));
  assert.equal(root([...statistics, 'unknown']).current.type, 'question');
  const discount = ['graphs', 'distance', 'single-discount'];
  assert.ok(root([...discount, 'yes', 'yes']).current.techniques!.includes('shortest-one-edge-discount'));
  assert.ok(!root([...discount, 'yes', 'no']).current.techniques!.includes('shortest-one-edge-discount'));
});

test('exact tree-length counts and minimum edge counts use different retained values', () => {
  const start = ['graphs', 'tree-range', 'distance'];
  const count = root([...start, 'exact-count', 'yes', 'yes']);
  const minimum = root([...start, 'min-edges', 'yes', 'yes']);
  assert.ok(count.current.techniques!.includes('centroid-count-cross-subtrees'));
  assert.ok(!count.current.techniques!.includes('weighted-tree-exact-length-min-edges'));
  assert.ok(minimum.current.techniques!.includes('weighted-tree-exact-length-min-edges'));
  assert.ok(!minimum.current.techniques!.includes('centroid-count-cross-subtrees'));
  assert.match(minimum.current.conditions!.join(' '), /同じ枝.*組み合わせない/);
  assert.ok(!root([...start, 'min-edges', 'no']).current.techniques!.includes('weighted-tree-exact-length-min-edges'));
  assert.ok(!root([...start, 'min-edges', 'yes', 'no']).current.techniques!.includes('weighted-tree-exact-length-min-edges'));
  assert.equal(root([...start, 'min-edges', 'unknown']).current.type, 'question');
});

test('rotation-only colorings and reflected colorings have separate arithmetic and symmetry guards', () => {
  const start = ['math', 'count', 'symmetry'];
  const rotation = root([...start, 'rotation', 'yes', 'yes']);
  const reflection = root([...start, 'reflection', 'yes', 'yes', 'yes']);
  assert.ok(rotation.current.techniques!.includes('burnside-necklace-divisors'));
  assert.ok(!rotation.current.techniques!.includes('burnside-bracelet-reflections'));
  assert.ok(reflection.current.techniques!.includes('burnside-bracelet-reflections'));
  assert.ok(!root([...start, 'rotation', 'yes', 'no']).current.techniques!.includes('burnside-necklace-divisors'));
  assert.equal(root([...start, 'reflection', 'unknown']).current.type, 'question');
});

test('invalid bracket prefixes end at zero rather than an unrestricted Catalan shortcut', () => {
  const start = ['strings', 'bracket-prefix', 'yes'];
  const invalid = root([...start, 'negative']);
  const valid = root([...start, 'valid', 'yes', 'yes']);
  assert.equal(invalid.current.id, 'zero-result');
  assert.match(invalid.current.conditions!.join(' '), /既に負/);
  assert.equal(root([...start, 'valid', 'no']).current.id, 'zero-result');
  assert.ok(valid.current.techniques!.includes('ballot-prefix-reflection'));
  assert.ok(!root(['strings', 'bracket-prefix', 'no']).current.techniques!.includes('ballot-prefix-reflection'));
});

test('fixed-point permutations and injective pairs require distinct objects and different sharing rules', () => {
  const start = ['math', 'count', 'forbidden'];
  assert.ok(root([...start, 'permutation-fixed', 'yes', 'none']).current.techniques!.includes('derangement-fixed-count'));
  assert.ok(root([...start, 'permutation-fixed', 'yes', 'exact']).current.techniques!.includes('derangement-fixed-count'));
  assert.ok(!root([...start, 'permutation-fixed', 'no']).current.techniques!.includes('derangement-fixed-count'));
  const injective = root([...start, 'coordinate-match', 'yes', 'yes']);
  assert.ok(injective.current.techniques!.includes('injective-coordinate-avoidance'));
  assert.match(injective.current.conditions!.join(' '), /異なる位置.*共有.*許す/);
  assert.ok(!root([...start, 'coordinate-match', 'yes', 'no']).current.techniques!.includes('injective-coordinate-avoidance'));
});

test('subset extrema count equal values by distinct indices', () => {
  const start = ['math', 'count', 'contribution', 'extrema'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('subset-extrema-rank'));
  assert.match(result.current.conditions!.join(' '), /同じ値.*添字/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('subset-extrema-rank'));
});

test('exact redistribution requires boundary and padding checks beyond the minimum transfer count', () => {
  const start = ['math', 'count', 'identical', 'moves', 'yes', 'yes'];
  const atMost = root([...start, 'at-most']);
  const exact = root([...start, 'exact', 'yes']);
  assert.ok(atMost.current.techniques!.includes('redistribution-zero-count'));
  assert.ok(exact.current.techniques!.includes('redistribution-zero-count'));
  assert.notEqual(atMost.current.id, exact.current.id);
  assert.match(exact.current.conditions!.join(' '), /ちょうど k 回.*断定しない/);
  assert.ok(!root([...start, 'exact', 'no']).current.techniques!.includes('redistribution-zero-count'));
  assert.equal(root([...start, 'exact', 'unknown']).current.type, 'question');
});

test('grid color separation requires every declared row and column to be used', () => {
  const start = ['grid-arrangements', 'color-separation'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('grid-active-rows-cols'));
  assert.match(result.current.conditions!.join(' '), /個数 0.*零行.*零列/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('grid-active-rows-cols'));
});

test('bounding rectangles sample a nonempty uniform subset and require invertible selection counts', () => {
  const start = ['grid-arrangements', 'bounding-area'];
  assert.ok(root([...start, 'yes', 'yes']).current.techniques!.includes('subset-bounding-box-expectation'));
  assert.ok(!root([...start, 'no']).current.techniques!.includes('subset-bounding-box-expectation'));
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('subset-bounding-box-expectation'));
});

test('equal-adjacency coloring rejects a circular boundary', () => {
  const start = ['math', 'count', 'equal-neighbors'];
  assert.ok(root([...start, 'yes', 'yes', 'at-most']).current.techniques!.includes('coloring-equal-adjacencies'));
  assert.ok(root([...start, 'yes', 'yes', 'exact']).current.techniques!.includes('coloring-equal-adjacencies'));
  assert.ok(!root([...start, 'no']).current.techniques!.includes('coloring-equal-adjacencies'));
});

test('final clamp values and intermediate aggregate queries select different methods', () => {
  const start = ['ranges', 'change', 'cap'];
  const final = root([...start, 'final-values', 'yes', 'yes']);
  const aggregate = root([...start, 'aggregate', 'yes']);
  assert.ok(final.current.techniques!.includes('range-clamp-composition'));
  assert.ok(!final.current.techniques!.includes('segment-tree-beats'));
  assert.ok(aggregate.current.techniques!.includes('range-chmin-second-maximum'));
  assert.ok(!aggregate.current.techniques!.includes('range-clamp-composition'));
  assert.ok(!root([...start, 'final-values', 'yes', 'no']).current.techniques!.includes('range-clamp-composition'));
});

test('median budgets require equal weights and a free common destination', () => {
  const start = ['ranges', 'window', 'median-budget'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('median-window-budget'));
  assert.match(result.current.conditions!.join(' '), /重複位置/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('median-window-budget'));
  assert.equal(root([...start, 'yes', 'unknown']).current.type, 'question');
});

test('top-k visiting values are an evaluation kernel and do not finish the interval search', () => {
  const start = ['ranges', 'window', 'travel-visits', 'yes'];
  const evaluate = root([...start, 'evaluate', 'yes']);
  const search = root([...start, 'whole-search']);
  assert.ok(evaluate.current.techniques!.includes('active-top-k-count-sum'));
  assert.match(evaluate.current.conditions!.join(' '), /訪問範囲.*別に設計/);
  assert.ok(!search.current.techniques!.includes('active-top-k-count-sum'));
  assert.match(search.current.conditions!.join(' '), /最適化は完了しない/);
});

test('gift balancing introduces candidate bounds rather than assuming they were in the input', () => {
  const result = root(['flow-matching', 'receive-balance', 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('lower-bound-flow'));
  assert.match(result.current.conditions!.join(' '), /候補区間探索.*別に/);
  const gift = walks.find((row: { problemId: string }) => row.problemId === '1615');
  assert.equal(gift.reviewStatus, 'verified');
  assert.equal(gift.entryGraphId, 'flow-matching');
  assert.ok(gift.features.some((value: string) => value.includes('差を最小')));
  const cuts = walks.find((row: { problemId: string }) => row.problemId === 'BRKSTRNG');
  assert.equal(cuts.reviewStatus, 'verified');
});

test('color-balance tree walks identify frequency preprocessing from the actual color-count objective', () => {
  const start = ['graphs', 'tree-answer', 'colored-walk-balance'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('tree-path-edge-difference'));
  assert.match(result.current.conditions!.join(' '), /個数計算.*別に/);
  assert.match(result.current.conditions!.join(' '), /可否だけ.*色分け数/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('tree-path-edge-difference'));
  const fixture = walks.find((row: { problemId: string; expectedTechniqueIds: string[] }) => row.problemId === 'abc222_e' && row.expectedTechniqueIds.includes('tree-path-edge-difference'));
  assert.ok(fixture.steps.some((step: { node: string; answer: string }) => step.node === 'shortest' && step.answer === 'tree-answer'));
  assert.ok(fixture.features.some((value: string) => value.includes('色分け')));
});

test('static rank problems add value-divided offline queries only when all questions are known', () => {
  const start = ['ranges', 'static', 'kth', 'yes', 'yes'];
  const offline = root([...start, 'yes']);
  const online = root([...start, 'no']);
  assert.ok(offline.current.techniques!.includes('persistent-prefix-kth'));
  assert.ok(offline.current.techniques!.includes('wavelet-range-kth'));
  assert.ok(offline.current.techniques!.includes('offline-kth-divide-values'));
  assert.ok(!online.current.techniques!.includes('offline-kth-divide-values'));
  assert.equal(root([...start, 'unknown']).current.type, 'question');
});

test('upper and lower edge thresholds use opposite orders without deleting components', () => {
  const start = ['graphs', 'connectivity', 'threshold'];
  const low = root([...start, 'low', 'yes']);
  const high = root([...start, 'high', 'yes']);
  assert.ok(low.current.techniques!.includes('dsu-threshold-queries'));
  assert.ok(high.current.techniques!.includes('dsu-threshold-queries'));
  assert.match(high.current.conditions!.join(' '), /降順/);
  assert.match(high.current.conditions!.join(' '), /同重み.*先に/);
  assert.match(high.current.conditions!.join(' '), /大きさから 1/);
  assert.ok(!root([...start, 'high', 'no']).current.techniques!.includes('dsu-threshold-queries'));
});

test('bounded subarray sums allow negative values and expose the moving prefix range', () => {
  const start = ['ranges', 'window', 'bounded-length-sum'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('dp-sliding-min'));
  assert.match(result.current.conditions!.join(' '), /負数/);
  assert.match(result.current.conditions!.join(' '), /r−b≤l≤r−a/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('dp-sliding-min'));
});

test('set ranks guard duplicate changes, offline values and out-of-range positions', () => {
  const start = ['set-operations', 'ordered-values'];
  const result = root([...start, 'yes', 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('fenwick-prefix-lower-bound'));
  assert.match(result.current.conditions!.join(' '), /順位が範囲外.*探索を呼ばず/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('fenwick-prefix-lower-bound'));
  assert.ok(!root([...start, 'yes', 'yes', 'no']).current.techniques!.includes('fenwick-prefix-lower-bound'));
  assert.equal(root([...start, 'yes', 'yes', 'unknown']).current.type, 'question');
});

test('all twenty-four graph, state and selection additions have matching root traces and explicit unknown guards', () => {
  const files = ['graph-extension-problem-features.json', 'dp-structure-problem-features.json', 'selection-pattern-problem-features.json'];
  const additions = files.flatMap((file) => JSON.parse(readFileSync(`data/${file}`, 'utf8')));
  assert.equal(additions.length, 24);
  for (const row of additions) {
    const fixture = walks.find((walk: { statementUrl: string; expectedTechniqueIds: string[] }) => walk.statementUrl === row.url && row.techniqueIds.every((id: string) => walk.expectedTechniqueIds.includes(id)));
    assert.ok(fixture, `${row.problemId}: feature path missing`);
    assert.equal(fixture.reviewStatus, 'verified');
    assert.ok(fixture.features.length >= 2);
    assert.equal(root(fixture.choices, fixture.entryGraphId).current.type, 'result');
    assert.equal(fixture.choices.at(-1), 'yes');
    const prefix = fixture.choices.slice(0, -1);
    const unknown = root([...prefix, 'unknown'], fixture.entryGraphId);
    assert.equal(unknown.current.type, 'question');
    assert.ok(!unknown.current.techniques?.includes(row.techniqueIds[0]));
  }
  assert.equal(walks.filter((walk: { reviewStatus: string }) => walk.reviewStatus === 'pending').length, 4);
});

test('one-way connectivity distinguishes mutual components, DAG reachability and reach from one capital', () => {
  const start = ['graphs', 'connectivity', 'directed'];
  assert.ok(root([...start, 'mutual']).current.techniques!.includes('scc'));
  const dag = root([...start, 'reachable-counts', 'yes', 'yes']);
  assert.ok(dag.current.techniques!.includes('dag-reachable-bitsets'));
  assert.match(dag.current.conditions!.join(' '), /自分自身/);
  assert.match(dag.current.conditions!.join(' '), /重複.*足し算/);
  assert.ok(!root([...start, 'reachable-counts', 'no']).current.techniques!.includes('dag-reachable-bitsets'));
  assert.ok(!root([...start, 'reachable-counts', 'yes', 'no']).current.techniques!.includes('dag-reachable-bitsets'));
  const capital = root([...start, 'capital-additions', 'yes', 'yes']);
  assert.ok(capital.current.techniques!.includes('capital-reachability-scc-sources'));
  assert.match(capital.current.conditions!.join(' '), /未到達成分だけ/);
  assert.ok(!root([...start, 'capital-additions', 'yes', 'no']).current.techniques!.includes('capital-reachability-scc-sources'));
});

test('one-time rewards require revisits, nonnegative rewards and unrestricted endpoints', () => {
  const start = ['graphs', 'collect-once-reward'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('scc-collect-once-reward'));
  assert.match(result.current.conditions!.join(' '), /時間に制限がない/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('scc-collect-once-reward'));
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('scc-collect-once-reward'));
});

test('independent directed-edge shortest failures require unit edges and an affordable rerun count', () => {
  const start = ['graphs', 'failures', 'no', 'one-edge-distance'];
  const result = root([...start, 'yes', 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('unweighted-edge-removal-shortest'));
  assert.match(result.current.conditions!.join(' '), /独立に適用/);
  assert.match(result.current.conditions!.join(' '), /N−1/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('unweighted-edge-removal-shortest'));
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('unweighted-edge-removal-shortest'));
  assert.ok(!root([...start, 'yes', 'yes', 'no']).current.techniques!.includes('unweighted-edge-removal-shortest'));
});

test('multiple cheap routes count equal-cost edge sequences and reject simple-path-only constraints', () => {
  const start = ['graphs', 'distance', 'normal', 'k-walks'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('k-shortest-walk-prefix-cap'));
  assert.match(result.current.conditions!.join(' '), /同じ費用.*捨てない/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('k-shortest-walk-prefix-cap'));
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('k-shortest-walk-prefix-cap'));
});

test('lexicographic edge labels are minimized after edge count and retain all same-prefix frontier points', () => {
  const start = ['graphs', 'distance', 'normal', 'label-sequence'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('shortest-lexicographic-label-frontier'));
  assert.match(result.current.conditions!.join(' '), /全行き先/);
  assert.match(result.current.conditions!.join(' '), /平行辺・自己ループ/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('shortest-lexicographic-label-frontier'));
});

test('orienting fixed undirected edges diagnoses both a bridge and a disconnected input as impossible', () => {
  const start = ['graphs', 'connectivity', 'orient-all', 'strong'];
  const valid = root([...start, 'yes', 'yes']);
  const invalid = root([...start, 'yes', 'no']);
  assert.ok(valid.current.techniques!.includes('bridgeless-strong-orientation'));
  assert.equal(invalid.current.id, 'impossible-result');
  assert.match(invalid.current.conditions!.join(' '), /一辺だけの接続/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('bridgeless-strong-orientation'));
});

test('restoring distance tables requires positive off-diagonal distances and separates an inconsistent table', () => {
  const start = ['graphs', 'distance-table'];
  const valid = root([...start, 'yes', 'yes']);
  const invalid = root([...start, 'yes', 'no']);
  assert.ok(valid.current.techniques!.includes('distance-matrix-essential-edges'));
  assert.match(valid.current.conditions!.join(' '), /異なる第三点/);
  assert.match(valid.current.conditions!.join(' '), /零距離.*そのまま使わない/);
  assert.equal(invalid.current.id, 'invalid-result');
  assert.ok(!root([...start, 'no']).current.techniques!.includes('distance-matrix-essential-edges'));
});

test('subset sums bounded by a selected maximum require nonnegative added weights and unique equal maxima', () => {
  const start = ['dp', 'sum-selected-maximum'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('subset-sum-max-threshold'));
  assert.match(result.current.conditions!.join(' '), /A が等しい.*一意/);
  assert.match(result.current.conditions!.join(' '), /使用前の表/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('subset-sum-max-threshold'));
});

test('adjacent swaps and value edits enter through the actual reorder operations and need uniform nonnegative costs', () => {
  const start = ['ranges', 'reorder-cost', 'swap-and-adjust'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('assignment-adjacent-swap-mask'));
  assert.match(result.current.conditions!.join(' '), /共通単価.*非負/);
  assert.match(result.current.conditions!.join(' '), /同じ値.*入力位置/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('assignment-adjacent-swap-mask'));
  const previous = walks.find((row: { problemId: string }) => row.problemId === 'abc201_f');
  const previousWalk = root(previous.choices, previous.entryGraphId);
  assert.equal(previousWalk.steps.find((step) => step.node === 'reorder-operation')?.answer, 'move-position');
  assert.ok(previousWalk.current.techniques!.includes('dp-prefix-min'));
  assert.ok(!previousWalk.current.techniques!.includes('assignment-adjacent-swap-mask'));
});

test('rectangle tilings distinguish two-cell pieces from unrestricted-height rectangular blocks', () => {
  const start = ['grid-arrangements', 'domino-tilings'];
  const rectangular = root([...start, 'any-rectangles', 'yes', 'yes']);
  assert.ok(rectangular.current.techniques!.includes('two-column-rectangle-tiles'));
  assert.match(rectangular.current.conditions!.join(' '), /高さに上限がない/);
  assert.ok(!root([...start, 'any-rectangles', 'yes', 'no']).current.techniques!.includes('two-column-rectangle-tiles'));
  const old = walks.find((row: { problemId: string }) => row.problemId === '2181');
  const pieceChoice = old.steps.find((step: { node: string }) => step.node === 'tile-shape');
  assert.ok(pieceChoice);
  assert.equal(pieceChoice.answer, 'domino');
  assert.ok(root(old.choices, old.entryGraphId).current.techniques!.includes('domino-column-transition'));
});

test('fixed tournaments permit nonmonotone final-win rewards but reject opponent-dependent rewards', () => {
  const start = ['game-probability', 'fixed-tournament'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('tournament-opponent-maximum'));
  assert.match(result.current.conditions!.join(' '), /単調性は不要/);
  assert.match(result.current.conditions!.join(' '), /重複して足さない/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('tournament-opponent-maximum'));
});

test('connected tree subsets use value-and-position ownership to distinguish equal minima', () => {
  const start = ['graphs', 'tree-answer', 'connected-value-range'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('connected-set-minimum-root'));
  assert.match(result.current.conditions!.join(' '), /同値の入力位置/);
  assert.match(result.current.conditions!.join(' '), /O\(N²\)/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('connected-set-minimum-root'));
});

test('waypoint compression allows incidental collections and passing the goal, while keeping the maze static', () => {
  const start = ['grid-arrangements', 'collect-and-finish'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('grid-waypoint-subset'));
  assert.match(result.current.conditions!.join(' '), /途中の終点通過を許す/);
  assert.match(result.current.conditions!.join(' '), /通行条件が変わらない/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('grid-waypoint-subset'));
});

test('earning-rate dominance requires right-down moves, positive earnings and a bounded residual', () => {
  const start = ['grid-arrangements', 'right-down', 'earn-before-move'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('grid-earning-rate-dominance'));
  assert.match(result.current.conditions!.join(' '), /残金が最高収入未満/);
  assert.match(result.current.conditions!.join(' '), /行動数が同じなら残金最大/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('grid-earning-rate-dominance'));
});

test('ratio weight caps preserve real transformed weights and reject additional constraints above the lower bound', () => {
  const start = ['dp', 'capacity', 'ratio'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('ratio-knapsack-weight-cap'));
  assert.match(result.current.conditions!.join(' '), /実際の重量/);
  assert.match(result.current.conditions!.join(' '), /1≤W/);
  assert.ok(!root([...start, 'yes', 'no']).current.techniques!.includes('ratio-knapsack-weight-cap'));
});

test('maximum-count jobs branch by common start, unit release windows and fixed intervals', () => {
  const start = ['dp', 'time-jobs'];
  const deadlines = root([...start, 'deadline-duration', 'yes', 'yes']);
  const release = root([...start, 'unit-release-expiry', 'yes', 'yes']);
  const intervals = root([...start, 'fixed-intervals', 'yes', 'yes']);
  assert.ok(deadlines.current.techniques!.includes('deadline-duration-remove-longest'));
  assert.ok(release.current.techniques!.includes('unit-release-expiry-earliest'));
  assert.ok(intervals.current.techniques!.includes('interval-k-resources-predecessor'));
  assert.match(release.current.conditions!.join(' '), /時刻 R にも/);
  assert.match(intervals.current.conditions!.join(' '), /終了時刻＝次の開始時刻/);
  assert.ok(!root([...start, 'deadline-duration', 'yes', 'no']).current.techniques!.includes('deadline-duration-remove-longest'));
  assert.ok(!root([...start, 'unit-release-expiry', 'no']).current.techniques!.includes('unit-release-expiry-earliest'));
});

test('coupon selection requires nested price eligibility, fixed discounts and single use', () => {
  const start = ['flow-matching', 'price-coupons'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('threshold-coupon-max-discount'));
  assert.match(result.current.conditions!.join(' '), /入れ子/);
  assert.match(result.current.conditions!.join(' '), /割合割引.*使わない/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('threshold-coupon-max-discount'));
});

test('length-specified free splits are separated from fixed-position interval cuts', () => {
  const start = ['dp', 'split', 'cut-cost'];
  const free = root([...start, 'free-lengths', 'yes', 'yes']);
  assert.ok(free.current.techniques!.includes('unordered-split-residual-huffman'));
  assert.match(free.current.conditions!.join(' '), /零の余りは加えない/);
  assert.ok(!root([...start, 'free-lengths', 'no']).current.techniques!.includes('unordered-split-residual-huffman'));
  const old = walks.find((row: { problemId: string }) => row.problemId === 'BRKSTRNG');
  assert.ok(old.steps.some((step: { node: string; answer: string }) => step.node === 'cut-layout' && step.answer === 'fixed-cuts'));
  assert.ok(root(old.choices, old.entryGraphId).current.techniques!.includes('knuth-optimization'));
});

test('fixed-size diversity needs a nondecreasing type bonus, while maximum products use true integer order', () => {
  const start = ['dp', 'fixed-count-selection'];
  const diversity = root([...start, 'diversity', 'yes', 'yes']);
  assert.ok(diversity.current.techniques!.includes('fixed-size-diversity-exchange'));
  assert.match(diversity.current.conditions!.join(' '), /非減少/);
  assert.ok(!root([...start, 'diversity', 'no']).current.techniques!.includes('fixed-size-diversity-exchange'));
  const product = root([...start, 'product', 'yes', 'yes']);
  assert.ok(product.current.techniques!.includes('maximum-product-sign-exchange'));
  assert.match(product.current.conditions!.join(' '), /剰余を比較して選ばない/);
  assert.ok(!root([...start, 'product', 'yes', 'no']).current.techniques!.includes('maximum-product-sign-exchange'));
});

test('cyclic inversion deltas require a zero-based permutation before using the value as a rank', () => {
  const start = ['ranges', 'cyclic-inversions'];
  const result = root([...start, 'yes', 'yes']);
  assert.ok(result.current.techniques!.includes('cyclic-inversion-delta'));
  assert.match(result.current.conditions!.join(' '), /N−1−2x/);
  assert.ok(!root([...start, 'no']).current.techniques!.includes('cyclic-inversion-delta'));
});

test('all problem examples start at a selected domain, and every diagram is available from those domains', () => {
  const domains = graphs.filter((graph) => graph.entry);
  assert.equal(domains.length, 15);
  assert.equal(graphs[0].id, 'ranges');
  assert.ok(!graphs.some((graph) => graph.id === 'overview'));
  const visited = new Set<string>();
  function visit(id: string) {
    if (visited.has(id)) return;
    visited.add(id);
    for (const node of getGraph(id).nodes) if (node.type === 'route') visit(node.graph!);
  }
  for (const domain of domains) {
    visit(domain.id);
    const start = initialState(domain.id);
    assert.equal(evaluateState(start).current.id, domain.root);
    assert.deepEqual(parseFlowHash(serializeFlowHash(start)), start);
    const svg = renderFlowSvg(domain, '/flowchartcp/', techniqueTitles);
    assert.ok(svg.includes(`data-node="${domain.root}"`));
  }
  assert.equal(visited.size, graphs.length);
  for (const fixture of walks) {
    const domain = getGraph(fixture.entryGraphId);
    assert.equal(domain.entry, true, `${fixture.problemId}: selected domain`);
    assert.ok(fixture.steps.every((step: { graph: string }) => step.graph !== 'overview'));
    if (fixture.steps.length) assert.deepEqual(fixture.steps[0], { graph: domain.id, node: domain.root, answer: fixture.choices[0] });
    else assert.equal(domain.id, 'fixed-output');
  }
});

test('twenty-eight range, operation and integer techniques have thirty-two primary problem walks with unknown confirmation', () => {
  const files = ['range-pattern-problem-features.json', 'operation-pattern-problem-features.json', 'integer-pattern-problem-features.json'];
  const additions = files.flatMap((file) => JSON.parse(readFileSync(`data/${file}`, 'utf8')));
  assert.equal(additions.length, 32);
  const ids = new Set(additions.flatMap((row) => row.techniqueIds));
  assert.equal(ids.size, 28);
  for (const row of additions) {
    const fixture = walks.find((walk: { statementUrl: string; expectedTechniqueIds: string[] }) => walk.statementUrl === row.url && row.techniqueIds.every((id: string) => walk.expectedTechniqueIds.includes(id)));
    assert.ok(fixture, `${row.problemId}: domain trace`);
    assert.equal(fixture.reviewStatus, 'verified');
    const result = root(fixture.choices, fixture.entryGraphId);
    assert.equal(result.current.type, 'result');
    for (const id of row.techniqueIds) assert.ok(result.current.techniques!.includes(id));
    const prefix = fixture.choices.slice(0, -1);
    const unknown = root([...prefix, 'unknown'], fixture.entryGraphId);
    assert.equal(unknown.current.type, 'question', `${row.problemId}: confirm an unknown property`);
    assert.ok(!unknown.current.techniques?.some((id) => row.techniqueIds.includes(id)));
    if (fixture.choices.at(-1) === 'yes') {
      const rejected = root([...prefix, 'no'], fixture.entryGraphId);
      if (row.techniqueIds.includes('half-multiple-two-adic')) {
        assert.equal(rejected.current.id, 'zero-result');
        assert.match(rejected.current.conditions!.join(' '), /異なる二の指数/);
      } else assert.ok(!rejected.current.techniques?.some((id) => row.techniqueIds.includes(id)), `${row.problemId}: unmet prerequisite`);
    }
  }
  assert.equal(walks.filter((walk: { reviewStatus: string }) => walk.reviewStatus === 'pending').length, 4);
});

test('fixed-window minimum mex is separate from window aggregates and frequency mex', () => {
  const prefix = ['ranges', 'window', 'fixed'];
  const mex = root([...prefix, 'min-mex', 'yes', 'yes']);
  assert.ok(mex.current.techniques!.includes('fixed-window-min-mex-gaps'));
  assert.match(mex.current.conditions!.join(' '), /最小|一つ/);
  assert.ok(!root([...prefix, 'min-mex', 'no']).current.techniques!.includes('fixed-window-min-mex-gaps'));
  const aggregate = root([...prefix, 'aggregate', 'no', 'yes']);
  assert.ok(aggregate.current.techniques!.includes('sliding-window'));
  assert.ok(!aggregate.current.techniques!.includes('fixed-window-min-mex-gaps'));
  const intervalMex = root(['ranges', 'change', 'order-statistics', 'frequency-mex', 'yes', 'yes', 'yes']);
  assert.ok(!intervalMex.current.techniques!.includes('fixed-window-min-mex-gaps'));
});

test('subarray gcd counts and bitwise-or distinct values share compression after their own value-bound guards', () => {
  const prefix = ['ranges', 'window', 'fold-results'];
  const gcd = root([...prefix, 'gcd', 'yes']);
  const or = root([...prefix, 'or', 'yes']);
  assert.ok(gcd.current.techniques!.includes('subarray-fold-value-runs'));
  assert.ok(or.current.techniques!.includes('subarray-fold-value-runs'));
  assert.notEqual(gcd.current.id, or.current.id);
  assert.match(gcd.current.conditions!.join(' '), /頻度|個数/);
  assert.match(gcd.current.conditions!.join(' '), /正整数.*0 を受け付けない/);
  assert.match(or.current.conditions!.join(' '), /種類|集合/);
  assert.ok(!root([...prefix, 'gcd', 'no']).current.techniques!.includes('subarray-fold-value-runs'));
  assert.ok(!root([...prefix, 'or', 'no']).current.techniques!.includes('subarray-fold-value-runs'));
  assert.equal(root([...prefix, 'or', 'unknown']).current.type, 'question');
});

test('exactly-once contribution, witness and closest equal pair keep different outputs and static-query guards', () => {
  const total = root(['strings', 'substrings', 'singleton-total', 'yes', 'yes']);
  assert.ok(total.current.techniques!.includes('singleton-subarray-contribution'));
  assert.match(total.current.conditions!.join(' '), /前|直前/);
  const prefix = ['ranges', 'static', 'distinct'];
  const types = root([...prefix, 'types', 'yes']);
  const witness = root([...prefix, 'singleton', 'yes', 'yes']);
  const gap = root([...prefix, 'equal-gap', 'yes', 'yes']);
  assert.ok(!types.current.techniques!.includes('offline-range-singleton-witness'));
  assert.ok(witness.current.techniques!.includes('offline-range-singleton-witness'));
  assert.ok(gap.current.techniques!.includes('offline-range-equal-gap'));
  assert.ok(!root([...prefix, 'singleton', 'no']).current.techniques!.includes('offline-range-singleton-witness'));
  assert.ok(!root([...prefix, 'equal-gap', 'no']).current.techniques!.includes('offline-range-equal-gap'));
  assert.match(witness.current.conditions!.join(' '), /最新|直前/);
  assert.match(witness.current.conditions!.join(' '), /任意の一例/);
  assert.match(gap.current.conditions!.join(' '), /連続|隣/);
});

test('binary complementation keeps both symbols and nonadjacent maximum keeps order and true integer maxima', () => {
  const binary = root(['strings', 'binary-flip', 'yes', 'yes']);
  assert.ok(binary.current.techniques!.includes('flip-longest-binary-run'));
  assert.match(binary.current.conditions!.join(' '), /接頭|接尾/);
  const fromArray = root(['ranges', 'change', 'binary-flip', 'yes', 'yes']);
  assert.deepEqual(fromArray.current.techniques, binary.current.techniques);
  assert.ok(!root(['strings', 'binary-flip', 'no']).current.techniques!.includes('flip-longest-binary-run'));
  const prefix = ['ranges', 'change', 'point-set', 'nonadjacent'];
  const selected = root([...prefix, 'yes', 'yes']);
  assert.ok(selected.current.techniques!.includes('point-update-nonadjacent-max-sum'));
  assert.match(selected.current.conditions!.join(' '), /順序|左.*右/);
  assert.match(selected.current.conditions!.join(' '), /剰余|整数/);
  assert.ok(!root([...prefix, 'yes', 'no']).current.techniques!.includes('point-update-nonadjacent-max-sum'));
});

test('modulo updates require nonnegative values and account for values restored by point assignments', () => {
  const prefix = ['ranges', 'change', 'range-modulo'];
  const modulo = root([...prefix, 'yes', 'yes']);
  assert.ok(modulo.current.techniques!.includes('range-modulo-halving'));
  assert.match(modulo.current.conditions!.join(' '), /a%m<a\/2/);
  assert.match(modulo.current.conditions!.join(' '), /代入/);
  assert.ok(!root([...prefix, 'no']).current.techniques!.includes('range-modulo-halving'));
  assert.ok(!root([...prefix, 'yes', 'no']).current.techniques!.includes('range-modulo-halving'));
});

test('decimal substring divisibility distinguishes coprime shifts, last digits and unsupported noncoprime moduli', () => {
  const prefix = ['strings', 'substrings', 'decimal-divisibility', 'yes'];
  for (const modulus of ['prime', 'coprime', 'two-five']) assert.ok(root([...prefix, modulus]).current.techniques!.includes('decimal-substring-divisibility'));
  const composite = root([...prefix, 'other']);
  assert.ok(!composite.current.techniques!.includes('decimal-substring-divisibility'));
  const prime = root([...prefix, 'prime']);
  assert.match(prime.current.conditions!.join(' '), /2・5/);
  const coprime = root([...prefix, 'coprime']);
  assert.match(coprime.current.conditions!.join(' '), /gcd\(P,10\)=1/);
  const numeric = root(['math', 'digits', 'substring-divisible', 'yes', 'prime']);
  assert.deepEqual(numeric.current.techniques, prime.current.techniques);
});

test('divisibility purposes preserve old gcd counting and separate exact deletion, square products and interval pairs', () => {
  const prefix = ['math', 'gcd', 'yes'];
  const old = walks.find((walk: { problemId: string }) => walk.problemId === 'abc162_e');
  assert.ok(old.choices.includes('gcd-count'));
  assert.equal(root(old.choices, old.entryGraphId).current.type, 'result');
  const lcm = root([...prefix, 'lcm-removal', 'yes', 'yes']);
  const square = root([...prefix, 'square-product', 'yes', 'yes']);
  const interval = root([...prefix, 'nondividing-pairs', 'yes', 'yes']);
  assert.ok(lcm.current.techniques!.includes('lcm-removal-unique-maximum'));
  assert.match(lcm.current.conditions!.join(' '), /唯一/);
  assert.ok(square.current.techniques!.includes('squarefree-product-pairs'));
  assert.match(square.current.conditions!.join(' '), /零/);
  assert.ok(interval.current.techniques!.includes('gcd-pairs-exclude-divides'));
  assert.match(interval.current.conditions!.join(' '), /二倍/);
  for (const kind of ['lcm-removal', 'square-product', 'nondividing-pairs']) assert.equal(root([...prefix, kind, 'unknown']).current.type, 'question');
});

test('half odd multiples have a proved impossible branch and factorial divisibility requires feasible factorization', () => {
  const prefix = ['math', 'gcd', 'yes'];
  const half = root([...prefix, 'half-odd-multiples', 'yes', 'yes']);
  const impossible = root([...prefix, 'half-odd-multiples', 'yes', 'no']);
  assert.ok(half.current.techniques!.includes('half-multiple-two-adic'));
  assert.equal(impossible.current.id, 'zero-result');
  assert.match(impossible.current.conditions!.join(' '), /異なる二の指数/);
  assert.ok(!root([...prefix, 'half-odd-multiples', 'no']).current.techniques!.includes('half-multiple-two-adic'));
  const factorial = root([...prefix, 'factorial-threshold', 'yes', 'yes']);
  assert.ok(factorial.current.techniques!.includes('factorial-divisibility-threshold'));
  assert.match(factorial.current.conditions!.join(' '), /K=1.*1/);
  assert.ok(!root([...prefix, 'factorial-threshold', 'yes', 'no']).current.techniques!.includes('factorial-divisibility-threshold'));
});

test('nested powers separate actual zero exponents from residue zero, and decimal rank sums use integer division', () => {
  const tower = root(['math', 'power-tower', 'yes', 'yes']);
  assert.ok(tower.current.techniques!.includes('prime-mod-power-tower'));
  assert.match(tower.current.conditions!.join(' '), /剰余 0.*実際の指数 0/);
  assert.match(tower.current.conditions!.join(' '), /998244353/);
  assert.ok(!root(['math', 'power-tower', 'yes', 'no']).current.techniques!.includes('prime-mod-power-tower'));
  const rank = root(['math', 'digits', 'digit-rank-sum', 'yes', 'yes']);
  assert.ok(rank.current.techniques!.includes('decimal-length-rank-sum'));
  assert.match(rank.current.conditions!.join(' '), /偶数の法.*逆元は不要/);
  assert.ok(!root(['math', 'digits', 'digit-rank-sum', 'no']).current.techniques!.includes('decimal-length-rank-sum'));
});

test('two-sequence equality and inequality use their actual allowed operations, with a shared question in two domains', () => {
  const prefix = ['ranges', 'sequence-operations'];
  const equal = root([...prefix, 'equal-pair', 'yes', 'yes']);
  const unequal = root([...prefix, 'unequal-pair', 'yes', 'yes']);
  assert.ok(equal.current.techniques!.includes('simultaneous-swap-parity'));
  assert.match(equal.current.conditions!.join(' '), /N≥3/);
  assert.match(equal.current.conditions!.join(' '), /共有添字/);
  assert.match(equal.current.conditions!.join(' '), /重複/);
  assert.ok(unequal.current.techniques!.includes('unequal-multiset-cyclic-shift'));
  assert.match(unequal.current.conditions!.join(' '), /freq_A\(v\)\+freq_B\(v\)≤N/);
  assert.ok(!root([...prefix, 'equal-pair', 'no']).current.techniques!.includes('simultaneous-swap-parity'));
  assert.ok(!root([...prefix, 'unequal-pair', 'no']).current.techniques!.includes('unequal-multiset-cyclic-shift'));
  const otherDomain = root(['thinking', 'sequence-operations', 'equal-pair', 'yes', 'yes']);
  assert.deepEqual(otherDomain.current.techniques, equal.current.techniques);
  const category = enterFlowRoute(answerState(initialState('thinking'), 'operation-goals'));
  assert.equal(category.graph, 'thinking-operation-goals');
  const parent = answerState(category, 'sequence-operations');
  const child = enterFlowRoute(parent);
  assert.equal(child.graph, 'sequence-operation-goals');
  assert.deepEqual(backFlowState(child), category);
  assert.deepEqual(backFlowState(category), initialState('thinking'));
  assert.deepEqual(parseFlowHash(serializeFlowHash(child)), child);
});

test('addition ordering, reserved occurrences and circular removal keep their operation bounds and endpoint requirements', () => {
  const prefix = ['ranges', 'sequence-operations'];
  const add = root([...prefix, 'add-to-sorted', 'yes', 'yes']);
  assert.ok(add.current.techniques!.includes('additive-sign-sweep'));
  assert.match(add.current.conditions!.join(' '), /2N/);
  assert.match(add.current.conditions!.join(' '), /全零/);
  const reserved = root([...prefix, 'occurrence-position', 'yes', 'yes']);
  assert.ok(reserved.current.techniques!.includes('reserved-occurrence-deadlines'));
  assert.match(reserved.current.conditions!.join(' '), /i−1/);
  assert.match(reserved.current.conditions!.join(' '), /N−i/);
  const ramp = root([...prefix, 'circular-zero', 'yes', 'yes']);
  assert.ok(ramp.current.techniques!.includes('circular-ramp-removal-counts'));
  assert.match(ramp.current.conditions!.join(' '), /非負整数/);
  assert.match(ramp.current.conditions!.join(' '), /どの順/);
  for (const kind of ['add-to-sorted', 'occurrence-position', 'circular-zero']) assert.equal(root([...prefix, kind, 'unknown']).current.type, 'question');
});

test('uncertain ball identities retain only one-special-item possibility and modulo grids allow choosing the common remainder', () => {
  const ball = root(['thinking', 'hidden-item', 'yes', 'yes']);
  assert.ok(ball.current.techniques!.includes('special-ball-possibility'));
  assert.match(ball.current.conditions!.join(' '), /0.*候補を消す/);
  assert.ok(!root(['thinking', 'hidden-item', 'no']).current.techniques!.includes('special-ball-possibility'));
  const grid = root(['grid-arrangements', 'neighbor-modulo', 'yes', 'yes']);
  assert.ok(grid.current.techniques!.includes('adjacent-modulo-prime-grid'));
  assert.match(grid.current.conditions!.join(' '), /10\^15/);
  assert.match(grid.current.conditions!.join(' '), /相異性/);
  assert.ok(!root(['grid-arrangements', 'neighbor-modulo', 'yes', 'no']).current.techniques!.includes('adjacent-modulo-prime-grid'));
});

test('orientation distinguishes mutual reachability from even outdegree in each connected component', () => {
  const prefix = ['graphs', 'connectivity', 'orient-all'];
  const strong = root([...prefix, 'strong', 'yes', 'yes']);
  const even = root([...prefix, 'even-outdegree', 'yes', 'yes']);
  assert.ok(strong.current.techniques!.includes('bridgeless-strong-orientation'));
  assert.ok(!strong.current.techniques!.includes('even-outdegree-orientation'));
  assert.ok(even.current.techniques!.includes('even-outdegree-orientation'));
  assert.ok(!even.current.techniques!.includes('bridgeless-strong-orientation'));
  assert.match(even.current.conditions!.join(' '), /全ての連結成分の辺数が偶数/);
  assert.ok(!root([...prefix, 'even-outdegree', 'no']).current.techniques!.includes('even-outdegree-orientation'));
});

const currentPatternGraphIds = [
  'prefix-piece-cover', 'suffix-lcp-pair-sums', 'sorted-word-neighbor-lcp',
  'fixed-length-lex-subsequence', 'small-edit-distance-band',
  'periodic-consecutive-word-chain', 'reverse-deletion-half-match', 'slash-balanced-subsequence',
  'weighted-distance-all-roots', 'tree-farthest-all-vertices',
  'tree-target-bonus-all-vertices', 'tree-all-pair-xor-sum',
  'rooted-tree-leaf-labels', 'specified-unique-mst-count',
  'tree-path-black-constraints', 'marked-vertex-separation',
  'subset-sum-dynamic-count', 'all-segment-subset-count', 'knapsack-color-first-bonus',
  'interval-hit-selection-score', 'partition-distinct-values', 'partition-equal-value-pairs',
  'palindrome-erasure-sequence', 'optional-booster-point-tour',
];

test('new detailed cases are reachable from the same 15 domain roots and preserve pending evidence', () => {
  const entries = graphs.filter((graph) => graph.entry);
  assert.equal(entries.length, 15);
  assert.ok(!graphs.some((graph) => graph.id === 'overview'));
  const reached = new Set(entries.map((graph) => graph.id));
  const queue = [...reached];
  for (let i = 0; i < queue.length; ++i) {
    for (const node of getGraph(queue[i]!).nodes) {
      if (node.type === 'route' && node.graph && !reached.has(node.graph)) {
        reached.add(node.graph); queue.push(node.graph);
      }
    }
  }
  assert.equal(reached.size, graphs.length);
  for (const id of currentPatternGraphIds) {
    assert.ok(reached.has(id), id);
    assert.ok(!getGraph(id).entry, id);
    assert.equal(getNodeOptions(local(id, []).current).length, 4, id);
  }
  assert.equal(walks.filter((walk: { reviewStatus: string }) => walk.reviewStatus === 'pending').length, 4);
  for (const file of ['dp-pattern-problem-features', 'string-pattern-problem-features', 'tree-pattern-problem-features']) {
    const features = JSON.parse(readFileSync(`data/${file}.json`, 'utf8'));
    assert.equal(features.length, 8, file);
    for (const feature of features) {
      const walk = walks.find((row: { statementUrl: string; expectedTechniqueIds: string[] }) => row.statementUrl === feature.url && feature.techniqueIds.every((id: string) => row.expectedTechniqueIds.includes(id)));
      assert.ok(walk, feature.problemId);
      assert.ok(entries.some((entry) => entry.id === walk.entryGraphId));
      assert.equal(walk.reviewStatus, feature.reviewStatus);
      const end = root(walk.choices, walk.entryGraphId);
      assert.equal(end.current.type, 'result');
      assert.equal(end.graph.entry, undefined);
    }
  }
});

test('new detail charts ask for confirmation on unknown and reject a changed operation model', () => {
  for (const id of currentPatternGraphIds) {
    const graph = getGraph(id);
    const model = local(id, []).current;
    const expected = graph.nodes.find((node) => node.id === 'result')!.techniques!;
    assert.equal(local(id, ['unknown']).current.id, 'check', id);
    for (const option of getNodeOptions(model).slice(1).filter((option) => option.id !== 'unknown')) {
      const result = local(id, [option.id]).current;
      assert.equal(result.type, 'result', id);
      for (const technique of expected) assert.ok(!result.techniques!.includes(technique), `${id}/${option.id}/${technique}`);
    }
    const first = getNodeOptions(model)[0]!.id;
    const denied = local(id, [first, 'no']).current;
    for (const technique of expected) assert.ok(!denied.techniques!.includes(technique), `${id}/no/${technique}`);
    assert.equal(local(id, [first, 'unknown']).current.id, 'check', id);
  }
});

test('prefix-piece covers require all shorter prefixes, and suffix LCP sums keep the self contribution', () => {
  const pieces = root(['strings', 'prefix', 'prefix-pieces', 'all-prefixes', 'yes', 'yes']);
  assert.ok(pieces.current.techniques!.includes('prefix-piece-farthest-reach'));
  assert.match(pieces.current.conditions!.join(' '), /1\.\.最長一致長/);
  assert.ok(!root(['strings', 'prefix', 'prefix-pieces', 'listed-words']).current.techniques!.includes('prefix-piece-farthest-reach'));
  const sum = root(['strings', 'substrings', 'suffix-lcp-sum', 'sum-each', 'yes', 'yes']);
  const maximum = root(['strings', 'prefix', 'sorted-word-lcp', 'longest-other', 'yes', 'yes']);
  assert.ok(sum.current.techniques!.includes('suffix-lcp-pair-sum'));
  assert.ok(maximum.current.techniques!.includes('sorted-adjacent-max-lcp'));
  assert.match(sum.current.conditions!.join(' '), /自分自身.*残りの長さ/);
  assert.match(maximum.current.conditions!.join(' '), /重複した語を削除しない/);
  assert.ok(!sum.current.techniques!.includes('sorted-adjacent-max-lcp'));
});

test('fixed-length and slash subsequences distinguish position freedom, length feasibility and crossing endpoints', () => {
  const lex = root(['strings', 'subsequence', 'fixed-lex-length', 'exact-k', 'yes', 'yes']);
  assert.ok(lex.current.techniques!.includes('fixed-length-lexicographic-subsequence'));
  assert.match(lex.current.conditions!.join(' '), /0≤K≤本文長/);
  const lengthGuard = local('fixed-length-lex-subsequence', ['exact-k', 'yes']).current;
  assert.match(lengthGuard.explanation!, /K が本文長.*全ての文字/);
  const slash = root(['strings', 'subsequence', 'slash-balanced', 'balanced-slash', 'yes', 'yes']);
  assert.ok(slash.current.techniques!.includes('slash-subsequence-crossing'));
  assert.match(slash.current.conditions!.join(' '), /スラッシュがなければ 0/);
  assert.match(slash.current.conditions!.join(' '), /交差が区間内にない.*最初または最後/);
  assert.ok(!root(['strings', 'subsequence', 'slash-balanced', 'contiguous']).current.techniques!.includes('slash-subsequence-crossing'));
});

test('small edit thresholds require unit costs and a feasible band, while periodic word chains detect infinite cycles', () => {
  const edit = root(['strings', 'edit-threshold', 'unit-three', 'yes', 'yes']);
  assert.ok(edit.current.techniques!.includes('edit-distance-diagonal-band'));
  assert.match(edit.current.conditions!.join(' '), /長さの差が K.*不可能/);
  assert.ok(!root(['strings', 'edit-threshold', 'weighted']).current.techniques!.includes('edit-distance-diagonal-band'));
  assert.ok(!root(['strings', 'edit-threshold', 'unit-three', 'yes', 'no']).current.techniques!.includes('edit-distance-diagonal-band'));
  const periodic = root(['strings', 'prefix', 'periodic-consecutive', 'consecutive-word', 'yes', 'yes']);
  assert.ok(periodic.current.techniques!.includes('periodic-match-residue-chains'));
  assert.match(periodic.current.conditions!.join(' '), /成功位置だけの循環.*有限の最大回数が存在しない/);
  assert.ok(!root(['strings', 'prefix', 'periodic-consecutive', 'subsequence']).current.techniques!.includes('periodic-match-residue-chains'));
  const deletion = root(['strings', 'reverse-delete-half', 'reverse-deleted', 'yes', 'yes']);
  assert.ok(deletion.current.techniques!.includes('reverse-deletion-two-z'));
  assert.match(deletion.current.conditions!.join(' '), /削除開始位置 0 と N/);
});

test('tree distance totals, eccentricities and target bonuses follow separate outputs and exclusion rules', () => {
  const prefix = ['graphs', 'tree-answer', 'all-distances'];
  const sum = root([...prefix, 'weighted-sum', 'demand-sum', 'yes', 'yes']);
  const farthest = root([...prefix, 'farthest', 'farthest-all', 'yes', 'yes']);
  const bonus = root([...prefix, 'target-bonus', 'exclude-self', 'yes', 'yes']);
  assert.ok(sum.current.techniques!.includes('weighted-tree-distance-reroot'));
  assert.match(sum.current.conditions!.join(' '), /全需要−2子側需要/);
  assert.ok(farthest.current.techniques!.includes('tree-eccentricity-diameter-endpoints'));
  assert.match(farthest.current.conditions!.join(' '), /非負/);
  assert.ok(bonus.current.techniques!.includes('tree-target-bonus-excluding-self'));
  assert.match(bonus.current.conditions!.join(' '), /同点.*−INF.*候補なし/);
  assert.ok(!root([...prefix, 'farthest', 'farthest-all', 'no']).current.techniques!.includes('tree-eccentricity-diameter-endpoints'));
  assert.ok(!root([...prefix, 'target-bonus', 'include-self']).current.techniques!.includes('tree-target-bonus-excluding-self'));
});

test('marked vertex separation checks original adjacency and rejects weighted deletion or edge deletion', () => {
  const prefix = ['graphs', 'tree-range', 'marked-separation'];
  const possible = root([...prefix, 'unmarked-vertices', 'yes', 'no', 'yes']);
  const impossible = root([...prefix, 'unmarked-vertices', 'yes', 'yes']);
  assert.ok(possible.current.techniques!.includes('virtual-tree-marked-vertex-separation'));
  assert.equal(impossible.current.id, 'impossible');
  assert.match(impossible.current.conditions!.join(' '), /元の木.*直接隣り合う/);
  assert.match(impossible.current.conditions!.join(' '), /圧縮木.*区別/);
  assert.ok(!root([...prefix, 'weighted-vertices']).current.techniques!.includes('virtual-tree-marked-vertex-separation'));
  assert.ok(!root([...prefix, 'edges']).current.techniques!.includes('virtual-tree-marked-vertex-separation'));
  assert.equal(root([...prefix, 'unmarked-vertices', 'yes', 'unknown']).current.id, 'check');
});

test('unique spanning-tree counts use strict inequalities and an absent-edge choice', () => {
  const prefix = ['graphs', 'specified-mst-count'];
  const unique = root([...prefix, 'unique', 'yes', 'yes']);
  assert.ok(unique.current.techniques!.includes('unique-mst-completion-count'));
  assert.match(unique.current.conditions!.join(' '), /厳密に大きく/);
  assert.match(unique.current.conditions!.join(' '), /追加辺なし/);
  assert.match(unique.current.conditions!.join(' '), /S−w\+1.*ab−1/);
  assert.ok(!root([...prefix, 'one-of']).current.techniques!.includes('unique-mst-completion-count'));
  const path = root(['graphs', 'tree-path-black-constraints', 'at-least-black', 'yes', 'yes']);
  assert.ok(path.current.techniques!.includes('tree-path-hitting-inclusion-exclusion'));
  assert.match(path.current.conditions!.join(' '), /少数の制約経路.*指数化/);
  assert.match(path.current.conditions!.join(' '), /零長経路.*満たせない/);
});

test('tree XOR contributions and leaf labels retain pair order and the number-of-leaves lower bound', () => {
  const xor = root(['graphs', 'tree-answer', 'all-pair-xor', 'xor-sum', 'yes', 'yes']);
  assert.ok(xor.current.techniques!.includes('tree-xor-pair-bit-contribution'));
  assert.match(xor.current.conditions!.join(' '), /順序なし.*順序付き/);
  const leaves = root(['graphs', 'tree-range', 'subtree', 'leaf-labels', 'nested-subtrees', 'yes', 'yes']);
  assert.ok(leaves.current.techniques!.includes('rooted-tree-leaf-interval-labels'));
  assert.match(leaves.current.conditions!.join(' '), /最大整数.*葉数/);
  assert.match(leaves.current.conditions!.join(' '), /\[1,1\]/);
});

test('dynamic subset counts, all-segment aggregates and first-color bonuses keep different count/value states', () => {
  const inverse = root(['dp', 'capacity', 'dynamic-count', 'count', 'yes', 'yes']);
  assert.ok(inverse.current.techniques!.includes('subset-sum-inverse-update'));
  assert.match(inverse.current.conditions!.join(' '), /追加.*降順.*削除.*昇順/);
  assert.match(inverse.current.conditions!.join(' '), /重さ 0・負数.*最大値/);
  assert.ok(!root(['dp', 'capacity', 'dynamic-count', 'max-value']).current.techniques!.includes('subset-sum-inverse-update'));
  const all = root(['dp', 'all-segment-sums', 'segment-and-subset', 'yes', 'yes']);
  assert.ok(all.current.techniques!.includes('all-segment-subset-sum'));
  assert.match(all.current.conditions!.join(' '), /区間の位置.*添字部分集合/);
  const color = root(['dp', 'capacity', 'color-bonus', 'once-per-color', 'yes', 'yes']);
  assert.ok(color.current.techniques!.includes('knapsack-first-color-bonus'));
  assert.match(color.current.conditions!.join(' '), /初回遷移だけ/);
  assert.ok(!root(['dp', 'capacity', 'color-bonus', 'per-item']).current.techniques!.includes('knapsack-first-color-bonus'));
});

test('partition distinctness and equal-pair costs require their own update formulas and a proof for narrowed optima', () => {
  const distinct = root(['dp', 'split', 'distinct-score', 'distinct-count', 'yes', 'yes']);
  const pairs = root(['dp', 'split', 'equal-pair-cost', 'equal-pair-count', 'yes', 'yes']);
  assert.ok(distinct.current.techniques!.includes('partition-distinct-range-add'));
  assert.ok(pairs.current.techniques!.includes('partition-equal-pairs-moving-window'));
  assert.match(distinct.current.conditions!.join(' '), /前回出現.*開始位置/);
  assert.match(pairs.current.conditions!.join(' '), /四点不等式.*単調性.*一般の区間費用.*無条件で適用しない/);
  assert.ok(!root(['dp', 'split', 'equal-pair-cost', 'arbitrary']).current.techniques!.includes('partition-equal-pairs-moving-window'));
  assert.ok(!root(['dp', 'split', 'equal-pair-cost', 'equal-pair-count', 'yes', 'no']).current.techniques!.includes('partition-equal-pairs-moving-window'));
});

test('interval-hit rewards, palindrome erasure and optional boosters keep operation timing and empty-state boundaries', () => {
  const hit = root(['dp', 'interval-hit-score', 'hit-once', 'yes', 'yes']);
  assert.ok(hit.current.techniques!.includes('interval-hit-last-selected'));
  assert.match(hit.current.conditions!.join(' '), /符号付き報酬.*一度/);
  assert.match(hit.current.conditions!.join(' '), /新状態を作ってから.*報酬/);
  const erase = root(['dp', 'palindrome-erasure', 'any-palindrome', 'yes', 'yes']);
  assert.ok(erase.current.techniques!.includes('palindrome-erasure-boundary'));
  assert.match(erase.current.conditions!.join(' '), /内側が空.*0 にはならない/);
  assert.deepEqual(root(['strings', 'palindrome', 'erase-contiguous', 'any-palindrome', 'yes', 'yes']).current.techniques, erase.current.techniques);
  const booster = root(['dp', 'booster-tour', 'mandatory-optional', 'yes', 'yes']);
  assert.ok(booster.current.techniques!.includes('optional-booster-subset-speed'));
  assert.match(booster.current.conditions!.join(' '), /移動前の集合.*原点への帰還時間/);
  assert.ok(!root(['dp', 'booster-tour', 'graph-roads']).current.techniques!.includes('optional-booster-subset-speed'));
});

test('bit constraints distinguish AND forcing, independent OR bits, carry-free sums and shared bounded XOR', () => {
  const base = ['math', 'bit-constraints'];
  const and = root([...base, 'range-and', 'and-equalities', 'yes', 'yes']);
  assert.ok(and.current.techniques!.includes('range-and-forced-bits'));
  assert.match(and.current.conditions!.join(' '), /再検査.*0 指定/);
  assert.ok(!root([...base, 'range-and', 'different']).current.techniques!.includes('range-and-forced-bits'));
  const or = root([...base, 'or-count', 'triplet-or', 'yes', 'yes']);
  assert.ok(or.current.techniques!.includes('bitwise-or-constraint-count'));
  assert.match(or.current.conditions!.join(' '), /2\^N.*要素数 N.*桁を結ぶ/);
  const sum = root([...base, 'sum-xor-bound', 'sum-bound', 'yes', 'yes']);
  assert.ok(sum.current.techniques!.includes('carryfree-sum-xor-bound'));
  assert.match(sum.current.conditions!.join(' '), /順序付き.*a\+b≤L/);
  const bounded = root([...base, 'bounded-xor', 'shared-x', 'yes', 'yes']);
  assert.ok(bounded.current.techniques!.includes('bounded-xor-sum-maximum'));
  assert.match(bounded.current.conditions!.join(' '), /共通の一つ.*既に小さい.*無条件に選ばない/);
});

test('bit constructions check shared-one capacity and nonnegative remainders; generator costs require all target values', () => {
  const base = ['math', 'bit-constraints'];
  const pop = root([...base, 'popcounts', 'fixed-width', 'yes', 'yes']);
  assert.ok(pop.current.techniques!.includes('xor-popcount-construction'));
  assert.match(pop.current.conditions!.join(' '), /0≤t≤B−c.*a−t,b−t/);
  const pair = root([...base, 'and-sum', 'nonnegative-pair', 'yes', 'yes']);
  assert.ok(pair.current.techniques!.includes('and-sum-disjoint-remainder'));
  assert.match(pair.current.conditions!.join(' '), /s≥2a.*先.*d=s−2a.*AND a/);
  const buy = root([...base, 'buy-generators', 'all-masks', 'yes', 'yes']);
  assert.ok(buy.current.techniques!.includes('minimum-cost-xor-generators'));
  assert.match(buy.current.conditions!.join(' '), /全ての B ビット.*費用は非負.*一つの目標/);
  assert.ok(!root([...base, 'buy-generators', 'different']).current.techniques!.includes('minimum-cost-xor-generators'));
  const window = root(['ranges', 'window', 'carryfree-sum-xor', 'sum-equals-xor', 'yes', 'yes']);
  assert.ok(window.current.techniques!.includes('carryfree-subarray-window'));
  assert.match(window.current.conditions!.join(' '), /非負.*高々一つ.*0 を含む.*負数/);
});

test('plane pair groups distinguish diagonals from bisectors and explicitly exclude zero-area choices', () => {
  const base = ['geometry', 'point-set-shapes'];
  const parallelogram = root([...base, 'parallelograms', 'positive-area', 'yes', 'yes']);
  assert.ok(parallelogram.current.techniques!.includes('parallelogram-diagonal-midpoints'));
  assert.match(parallelogram.current.conditions!.join(' '), /座標和.*三点共線.*退化/);
  const trapezoid = root([...base, 'weighted-trapezoid', 'weighted-four', 'yes', 'yes']);
  assert.ok(trapezoid.current.techniques!.includes('isosceles-trapezoid-bisector-groups'));
  assert.match(trapezoid.current.conditions!.join(' '), /長方形.*垂直二等分線.*中点が異なる.*退化/);
  assert.ok(!root([...base, 'weighted-trapezoid', 'different']).current.techniques!.includes('isosceles-trapezoid-bisector-groups'));
});

test('circle counts, free-center covering and translated convex intersections keep their boundary and transformation guards', () => {
  const base = ['geometry', 'point-set-shapes'];
  const lattice = root([...base, 'circle-lattice', 'finite-decimal', 'yes', 'yes']);
  assert.ok(lattice.current.techniques!.includes('scaled-circle-lattice-scan'));
  assert.match(lattice.current.conditions!.join(' '), /10\^d.*境界.*負座標.*桁あふれ/);
  const cover = root([...base, 'cover-circle', 'free-center', 'yes', 'yes']);
  assert.ok(cover.current.techniques!.includes('disk-cover-center-intersections'));
  assert.match(cover.current.conditions!.join(' '), /任意の実数.*二点.*一点だけ.*単調/);
  const convex = root([...base, 'translated-polygons', 'same-convex', 'yes', 'yes']);
  assert.ok(convex.current.techniques!.includes('translated-convex-halfplane-max'));
  assert.match(convex.current.conditions!.join(' '), /凸.*平行移動.*共通部分.*和集合.*境界/);
  assert.ok(!root([...base, 'cover-circle', 'different']).current.techniques!.includes('disk-cover-center-intersections'));
  assert.ok(!root([...base, 'translated-polygons', 'same-convex', 'no']).current.techniques!.includes('translated-convex-halfplane-max'));
});

test('point congruence retains signed orientation while repeated walks and wall areas retain displacement and real cell sizes', () => {
  const base = ['geometry', 'point-set-shapes'];
  const same = root([...base, 'same-points', 'rigid-motion', 'yes', 'yes']);
  assert.ok(same.current.techniques!.includes('point-congruence-cyclic-signature'));
  assert.match(same.current.conditions!.join(' '), /零ベクトル.*符号付き外積.*反転/);
  const repeat = root([...base, 'repeat-moves', 'same-walk', 'yes', 'yes']);
  assert.ok(repeat.current.techniques!.includes('repeated-grid-walk-orbits'));
  assert.match(repeat.current.conditions!.join(' '), /和集合.*変位が 0.*軌道.*区間/);
  const area = root([...base, 'wall-area', 'axis-walls', 'yes', 'yes']);
  assert.ok(area.current.techniques!.includes('plane-wall-compressed-cells'));
  assert.match(area.current.conditions!.join(' '), /端点を通り抜ける.*無限.*元の幅×高さ.*縦×横/);
});

test('stateful random processes distinguish resetting, empty-plate selection and strict record stopping', () => {
  const base = ['game-probability', 'stateful-process'];
  const restart = root([...base, 'restart', 'common-start', 'yes', 'yes']);
  assert.ok(restart.current.techniques!.includes('restart-board-trial-expectation'));
  assert.match(restart.current.conditions!.join(' '), /共通.*履歴.*p>0.*p=0.*丸めない/);
  assert.ok(!root([...base, 'restart', 'different']).current.techniques!.includes('restart-board-trial-expectation'));
  const sushi = root([...base, 'sushi', 'uniform-plates', 'yes', 'yes']);
  assert.ok(sushi.current.techniques!.includes('sushi-count-state-rolling'));
  assert.match(sushi.current.conditions!.join(' '), /空皿も含む.*高々 3.*二層.*順序/);
  const record = root([...base, 'increasing', 'strictly-increasing', 'yes', 'yes']);
  assert.ok(record.current.techniques!.includes('increasing-record-reward-probability'));
  assert.match(record.current.conditions!.join(' '), /初期番号は 0.*小さいか同じなら停止.*高々一度.*引き直し/);
});

test('random swaps keep replacement and initial symmetry; exact dice products exclude other prime factors and oversteps', () => {
  const base = ['game-probability', 'stateful-process'];
  const swap = root([...base, 'random-swap', 'with-replacement', 'yes', 'yes']);
  assert.ok(swap.current.techniques!.includes('random-swap-symmetry-two-state'));
  assert.match(swap.current.conditions!.join(' '), /復元抽出.*元の位置.*確率は全て等しく.*N=1/);
  assert.ok(!root([...base, 'random-swap', 'different']).current.techniques!.includes('random-swap-symmetry-two-state'));
  const product = root([...base, 'dice-product', 'exact-product', 'yes', 'yes']);
  assert.ok(product.current.techniques!.includes('dice-product-prime-exponents'));
  assert.match(product.current.conditions!.join(' '), /ちょうど.*他の素因数.*目標 1.*自己遷移.*失敗/);
});

test('one-edge DAG changes, adaptive roulette choices and subtree deletions keep their different conditioning', () => {
  const base = ['game-probability', 'stateful-process'];
  const edge = root([...base, 'remove-edge', 'uniform-dag', 'yes', 'yes']);
  assert.ok(edge.current.techniques!.includes('dag-edge-removal-expectation'));
  assert.match(edge.current.conditions!.join(' '), /非巡回.*高々一辺.*出次数 1.*到達確率×.*複数辺/);
  const roulette = root([...base, 'choose-roulette', 'adaptive-choice', 'yes', 'yes']);
  assert.ok(roulette.current.techniques!.includes('roulette-choice-zero-outcomes'));
  assert.match(roulette.current.conditions!.join(' '), /正の費用.*非負整数.*回数制限.*自己遷移.*全出目 0/);
  const subtree = root([...base, 'subtree-delete', 'uniform-remaining', 'yes', 'yes']);
  assert.ok(subtree.current.techniques!.includes('random-subtree-removal-ancestor-priority'));
  assert.match(subtree.current.conditions!.join(' '), /残り頂点.*選択.*depth\(v\)\+1.*独立性を仮定せず/);
});

test('all twenty-four new detailed models withhold their technique when conditions are unknown or fail', () => {
  const details = ['bit', 'planar', 'probability'].flatMap(group => JSON.parse(readFileSync(`data/${group}-pattern-problem-features.json`, 'utf8'))).flatMap((row: { techniqueIds: string[] }) => row.techniqueIds);
  assert.equal(new Set(details).size, 24);
  for (const id of details) {
    const graph = getGraph(id), first = getNodeOptions(graph.nodes.find(node => node.id === graph.root)!)[0]!.id;
    for (const node of graph.nodes.filter(node => node.type === 'question')) assert.doesNotMatch(node.title, /二層|自己遷移|接頭辞.*状態|巡回列|整数平方根|費用順|累積和|到達確率|優先順位|軌道|圧縮/);
    for (const answers of [['different'], [first, 'no'], [first, 'yes', 'no']]) {
      const result = local(id, answers).current;
      assert.equal(result.type, 'result'); assert.ok(!result.techniques!.includes(id), `${id}: failed assumptions`);
    }
    for (const answers of [['unknown'], [first, 'unknown'], [first, 'yes', 'unknown']]) {
      const result = local(id, answers).current;
      assert.equal(result.type, 'question'); assert.equal(result.id, 'check');
      assert.ok(!result.techniques?.includes(id), `${id}: unknown assumptions`);
    }
  }
  assert.equal(walks.filter((row: { reviewStatus: string }) => row.reviewStatus === 'pending').length, 4);
  assert.equal(graphs.filter(graph => graph.entry).length, 15);
});
