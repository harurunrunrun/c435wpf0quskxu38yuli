import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);
const metadata = JSON.parse(readFileSync(path.join(site, 'data/techniques-reasoning.json'), 'utf8'));
function snippet(id, language) {
  const body = readFileSync(path.join(site, 'src/content/docs/techniques', `${id}.mdx`), 'utf8');
  const code = body.match(new RegExp('```' + language + '\\n([\\s\\S]*?)\\n```'))?.[1];
  assert(code, `${id}: missing ${language} snippet`);
  return code;
}

test('reasoning snippets compile and agree with small exhaustive models', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-reasoning-'));
  const source = path.join(directory, 'test.cpp');
  const executable = path.join(directory, 'test');
  const cpp = metadata.filter(m => !['counterexample', 'output-only'].includes(m.id)).map(m => snippet(m.id, 'cpp')).join('\n\n');
  try {
    await writeFile(source, '#include <cassert>\n#include <functional>\n#include <string>\n#include <iostream>\n' + cpp + String.raw`
int main() {
    std::mt19937 rng(314159);
    for (int n = 0; n <= 8; ++n) for (int run = 0; run < 60; ++run) {
        std::vector<long long> a(n);
        for (auto& x : a) x = int(rng()%7)-3;
        __int128 expected = 0;
        for (int l = 0; l < n; ++l) for (int r = l+1; r <= n; ++r)
            for (int i = l; i < r; ++i) expected += a[i];
        assert(sum_of_all_subarray_sums(a) == expected);
        auto histogram = subset_sum_histogram(a);
        long long ways = 0;
        for (auto [sum, count] : histogram) ways += count;
        assert(ways == (1LL << n));
        long long total = 0;
        for (long long x : a) total += x;
        assert(sum_mod(a, 7) == (total%7+7)%7);
    }
    for (int n = 1; n <= 8; ++n) for (int run = 0; run < 60; ++run) {
        std::vector<std::vector<int>> g(n);
        for (int v = 0; v < n; ++v) for (int u = 0; u < v; ++u)
            if (rng()%2) { g[v].push_back(u); g[u].push_back(v); }
        std::vector<int> order(n), active(n);
        std::iota(order.begin(), order.end(), 0);
        std::shuffle(order.begin(), order.end(), rng);
        auto actual = components_after_additions(g, order);
        for (int step = 0; step < n; ++step) {
            active[order[step]] = 1;
            std::vector<int> seen(n);
            int count = 0;
            for (int v = 0; v < n; ++v) if (active[v] && !seen[v]) {
                ++count;
                std::vector<int> stack{v}; seen[v] = 1;
                while (!stack.empty()) {
                    int now = stack.back(); stack.pop_back();
                    for (int next : g[now]) if (active[next] && !seen[next]) {
                        seen[next] = 1; stack.push_back(next);
                    }
                }
            }
            assert(actual[step] == count);
        }
        std::vector<bool> marked(n);
        for (int v = 0; v < n; ++v) marked[v] = rng()%2;
        const int INF = 1000000;
        std::vector<std::vector<int>> d(2*n, std::vector<int>(2*n, INF));
        for (int i = 0; i < 2*n; ++i) d[i][i] = 0;
        for (int v = 0; v < n; ++v) for (int u : g[v]) for (int p = 0; p < 2; ++p)
            d[2*v+p][2*u+(p^int(marked[u]))] = 1;
        for (int k = 0; k < 2*n; ++k) for (int i = 0; i < 2*n; ++i) for (int j = 0; j < 2*n; ++j)
            d[i][j] = std::min(d[i][j], d[i][k]+d[k][j]);
        for (int parity = 0; parity < 2; ++parity) {
            auto result = parity_bfs(g, marked, 0, parity);
            for (int v = 0; v < n; ++v) for (int p = 0; p < 2; ++p)
                assert(result[v][p] == (d[parity][2*v+p] == INF ? -1 : d[parity][2*v+p]));
        }
    }
    for (int n = 0; n <= 8; ++n) for (int run = 0; run < 50; ++run) {
        std::vector<std::pair<long long,long long>> intervals(n);
        for (auto& [l,r] : intervals) { l = rng()%10; r = l+1+rng()%5; }
        int optimum = 0;
        for (int mask = 0; mask < (1<<n); ++mask) {
            std::vector<std::pair<long long,long long>> chosen;
            for (int i = 0; i < n; ++i) if ((mask>>i)&1) chosen.push_back(intervals[i]);
            std::sort(chosen.begin(), chosen.end());
            bool valid = true;
            for (int i = 1; i < int(chosen.size()); ++i)
                if (chosen[i].first < chosen[i-1].second) valid = false;
            if (valid) optimum = std::max(optimum, int(chosen.size()));
        }
        assert(maximum_nonoverlapping(intervals) == optimum);
    }
    for (std::string s : {"", "a", "ab", "abca", "aabab", "abbbba"}) {
        auto expected = canonical_dihedral(s);
        assert(canonical_dihedral(expected) == expected);
        for (int i = 0; i < int(s.size()); ++i) {
            assert(canonical_dihedral(s.substr(i)+s.substr(0,i)) == expected);
        }
        std::reverse(s.begin(), s.end());
        assert(canonical_dihedral(s) == expected);
    }
    for (int n = 0; n <= 5; ++n) for (int k = 1; k <= 4; ++k) {
        long long count = 0, possibilities = 1;
        for (int i = 0; i < n; ++i) possibilities *= k;
        for (int mask = 0; mask < possibilities; ++mask) {
            int value = mask; bool contains = false;
            for (int i = 0; i < n; ++i) { contains |= value%k == 0; value /= k; }
            count += contains;
        }
        assert(contains_designated_symbol(n,k,1000000007) == count);
    }
    for (int run = 0; run < 100; ++run) {
        int n = 8;
        std::vector<std::vector<int>> moves(n);
        for (int i = 0; i < n; ++i) for (int j = 0; j < i; ++j)
            if (rng()%2) moves[i].push_back(j);
        auto grundy = grundy_dag(moves);
        std::vector<std::vector<bool>> win(n,std::vector<bool>(n));
        for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j) {
            for (int x : moves[i]) if (!win[x][j]) win[i][j] = true;
            for (int y : moves[j]) if (!win[i][y]) win[i][j] = true;
            assert(win[i][j] == bool(grundy[i]^grundy[j]));
        }
    }
    for (int run = 0; run < 100; ++run) {
        int n = 6, group_count = 4, INF = 1000000;
        std::vector<std::vector<int>> groups(group_count);
        std::vector<std::vector<int>> original(n,std::vector<int>(n,INF));
        for (int i = 0; i < n; ++i) original[i][i] = 0;
        for (auto& group : groups) {
            for (int i = 0; i < n; ++i) if (rng()%2) group.push_back(i);
            for (int a : group) for (int b : group) if (a != b) original[a][b] = 1;
        }
        auto hubs = group_hubs(n, groups);
        int total = hubs.size();
        std::vector<std::vector<int>> compressed(total,std::vector<int>(total,INF));
        for (int i = 0; i < total; ++i) compressed[i][i] = 0;
        for (int v = 0; v < total; ++v) for (auto [u,w] : hubs[v]) compressed[v][u] = std::min(compressed[v][u], w);
        for (int k = 0; k < n; ++k) for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j)
            original[i][j] = std::min(original[i][j],original[i][k]+original[k][j]);
        for (int k = 0; k < total; ++k) for (int i = 0; i < total; ++i) for (int j = 0; j < total; ++j)
            compressed[i][j] = std::min(compressed[i][j],compressed[i][k]+compressed[k][j]);
        for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j) assert(original[i][j] == compressed[i][j]);
    }
    auto hashes = random_value_hashes(5, 42);
    auto p = hash_prefix({0,1,1,3}, hashes), q = hash_prefix({3,1,0,1}, hashes);
    assert(hash_range(p,0,4) == hash_range(q,0,4));
    assert(hash_range(p,0,0) == HashPair({0,0}));
    assert(std::abs(expectation_with_self_loop(1,0.5L,{{0.5L,3}})-5) < 1e-12L);
    auto score = [](int value) { return -double(value)*value; };
    auto neighbor = [](int& value, auto& rng) { value += int(rng()%3)-1; };
    assert(hill_climb(10,5000,42,score,neighbor) == 0);
    assert(anneal(10,5000,10,0.001,42,score,neighbor) == 0);
    auto expand = [](int value) { return std::vector<int>{value*2,value*2+1}; };
    auto evaluate = [](int value) { return double(value); };
    auto all = beam_search(0,5,32,expand,evaluate);
    assert(all.size() == 32 && all.front() == 31);
    auto narrow = beam_search(0,5,1,expand,evaluate);
    assert(narrow.size() == 1 && narrow.front() == 31);
    assert(beam_search(0,5,0,expand,evaluate).empty());
}
`);
    await execute('g++', ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', source, '-o', executable], { timeout: 60000 });
    await execute(executable, [], { timeout: 30000 });
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('Python counterexample and output-only snippets preserve verified best artifacts', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-output-only-'));
  const script = path.join(directory, 'test.py');
  try {
    await writeFile(script, snippet('counterexample', 'python') + '\n' + snippet('output-only', 'python') + String.raw`
import sys
output = Path(sys.argv[1]) / 'best.txt'
validate = lambda text: text.isdigit()
score = lambda text: int(text)
assert save_if_better(output, '5', validate, score)
assert not save_if_better(output, '4', validate, score)
assert not save_if_better(output, 'invalid', validate, score)
assert output.read_text() == '5'
assert save_if_better(output, '8', validate, score)
assert output.read_text() == '8'
assert first_coin_counterexample([1, 5, 10], 100) is None
`);
    await execute('python3', [script, directory], { timeout: 30000 });
  } finally { await rm(directory, { recursive: true, force: true }); }
});
