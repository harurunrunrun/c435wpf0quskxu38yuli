#!/usr/bin/env python3
"""Compile the exact article's C++20 fences and compare against the original color rule."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PUBLISHED = Path(__file__).resolve().parent.parent / 'src/content/docs/techniques/interactive-hidden-bipartite-edge-color-pair-recovery.mdx'
ARTICLE = Path(sys.argv[1]) if len(sys.argv) > 1 else (PUBLISHED if PUBLISHED.is_file() else Path('/tmp/flowchartcp-chameleon-interactive-hidden-bipartite-edge-color-pair-recovery.mdx'))
TESTS = r'''
struct DirectOracle {
    int n, calls = 0, answers = 0;
    long long query_elements = 0;
    vector<int> sex, color, like, answered;
    DirectOracle(vector<int> s, vector<int> c, vector<int> l)
        : n(int(s.size()) / 2), sex(move(s)), color(move(c)), like(move(l)), answered(2*n, 0) {
        assert(int(color.size()) == 2*n && int(like.size()) == 2*n);
        vector<int> incoming(2*n, 0);
        vector<vector<int>> occurrences(2, vector<int>(n, 0));
        for (int i = 0; i < 2*n; ++i) {
            assert(sex[i] == 0 || sex[i] == 1);
            assert(0 <= color[i] && color[i] < n);
            ++occurrences[sex[i]][color[i]];
            assert(0 <= like[i] && like[i] < 2*n);
            assert(sex[i] != sex[like[i]] && color[i] != color[like[i]]);
            ++incoming[like[i]];
        }
        for (int count : incoming) assert(count == 1);
        for (auto row : occurrences) for (int count : row) assert(count == 1);
    }
    // No hidden graph, degree rule, or matching formula is used by this oracle.
    int count_colors(const vector<int>& ids) const {
        vector<char> attending(2*n, false), visible(n, false);
        for (int id : ids) {
            if (id < 0 || id >= 2*n || attending[id]) throw invalid_argument("invalid query IDs");
            attending[id] = true;
        }
        for (int id : ids) {
            int shown = attending[like[id]] ? color[like[id]] : color[id];
            visible[shown] = true;
        }
        return accumulate(visible.begin(), visible.end(), 0);
    }
    int query(const vector<int>& ids) {
        if (++calls > 20000) throw runtime_error("official query limit exceeded");
        query_elements += ids.size();
        return count_colors(ids);
    }
    void answer(int a, int b) {
        if (a < 0 || a >= 2*n || b < 0 || b >= 2*n || a == b)
            throw invalid_argument("invalid answer IDs");
        if (answered[a] || answered[b]) throw invalid_argument("repeated answer ID");
        if (color[a] != color[b]) throw invalid_argument("different original colors");
        answered[a] = answered[b] = true;
        ++answers;
    }
    void finish() const {
        if (answers != n || accumulate(answered.begin(), answered.end(), 0) != 2*n)
            throw invalid_argument("incomplete answer");
    }
};

DirectOracle* active_oracle = nullptr;
int Query(const vector<int>& one_based) {
    vector<int> ids;
    for (int x : one_based) {
        if (x < 1 || x > 2*active_oracle->n) throw invalid_argument("official ID range");
        ids.push_back(x - 1);
    }
    return active_oracle->query(ids);
}
void Answer(int a, int b) { active_oracle->answer(a - 1, b - 1); }

long long exhaustive_cases = 0, random_cases = 0, lemma_checks = 0, graph_checks = 0;
long long total_queries = 0, max_elements = 0;
int max_queries = 0, adapter_cases = 0, max_query_set = 0;
array<long long, 5> exhaustive_by_n{};

void check_instance(DirectOracle oracle, bool small, bool check_lemma = false, bool adapter = false) {
    const int n = oracle.n, m = 2*n;
    if (adapter) {
        active_oracle = &oracle;
        Solve(n);
        ++adapter_cases;
    } else {
        auto result = recover_hidden_color_pairs(n, [&](const vector<int>& ids) {
            max_query_set = max(max_query_set, int(ids.size()));
            return oracle.query(ids);
        }, hidden_color_pair_query_bound(n));
        assert(result.query_count == oracle.calls);
        assert(int(result.pairs.size()) == n);
        for (auto [a,b] : result.pairs) oracle.answer(a,b);
        vector<vector<char>> expected(m, vector<char>(m, false));
        if (small) {
            for (int a = 0; a < m; ++a) for (int b = a+1; b < m; ++b) {
                expected[a][b] = expected[b][a] = (oracle.count_colors({a,b}) == 1);
                ++graph_checks;
            }
        } else {
            // For large inputs construct the expected graph from the raw pair oracle
            // on each possible structural edge; assert no unexpected recovered edge.
            for (int a = 0; a < m; ++a) for (int b : result.graph[a])
                assert(oracle.count_colors({a,b}) == 1);
            for (int a = 0; a < m; ++a) for (int b = 0; b < m; ++b)
                if (a != b && (oracle.color[a] == oracle.color[b] || oracle.like[a] == b || oracle.like[b] == a))
                    expected[a][b] = (oracle.count_colors({a,b}) == 1);
        }
        vector<vector<char>> actual(m, vector<char>(m, false));
        for (int a = 0; a < m; ++a) for (int b : result.graph[a]) {
            assert(0 <= b && b < m && a != b && !actual[a][b]);
            actual[a][b] = true;
        }
        assert(actual == expected);
        if (check_lemma) {
            for (int mask = 0; mask < (1 << m); ++mask) {
                vector<int> independent;
                bool okay = true;
                for (int a = 0; a < m; ++a) if ((mask >> a) & 1) {
                    for (int b : independent) if (expected[a][b]) okay = false;
                    independent.push_back(a);
                }
                if (!okay) continue;
                assert(int(independent.size()) <= n);
                assert(oracle.count_colors(independent) == int(independent.size()));
                for (int v = 0; v < m; ++v) if (!((mask >> v) & 1)) {
                    bool edge = false;
                    for (int a : independent) edge = edge || expected[v][a];
                    auto ids = independent;
                    ids.push_back(v);
                    assert((oracle.count_colors(ids) < int(ids.size())) == edge);
                    ++lemma_checks;
                }
            }
        }
    }
    oracle.finish();
    assert(oracle.calls <= hidden_color_pair_query_bound(n));
    assert(oracle.calls <= 19000 && oracle.calls <= 20000);
    max_queries = max(max_queries, oracle.calls);
    max_elements = max(max_elements, oracle.query_elements);
    total_queries += oracle.calls;
}

vector<vector<int>> permutations(int n, bool derangement = false) {
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);
    vector<vector<int>> result;
    do {
        bool okay = true;
        if (derangement) for (int i = 0; i < n; ++i) if (p[i] == i) okay = false;
        if (okay) result.push_back(p);
    } while (next_permutation(p.begin(), p.end()));
    return result;
}

void exhaustive(int n) {
    const int m = 2*n;
    auto all = permutations(n), derangements = permutations(n, true);
    // N<=3 also enumerates all actual color labels. N=4 quotients out only
    // simultaneous color renaming: every gender split, color matching, and both
    // independent preference permutations are still enumerated without sampling.
    auto x_labels = all;
    if (n == 4) x_labels.resize(1);
    for (int mask = 0; mask < (1 << m); ++mask) if (__builtin_popcount(unsigned(mask)) == n) {
        vector<int> sex(m), x, y;
        for (int i = 0; i < m; ++i) {
            sex[i] = (mask >> i) & 1;
            (sex[i] ? y : x).push_back(i);
        }
        for (const auto& xp : x_labels) for (const auto& yp : all) {
            vector<int> color(m), by_x(n), by_y(n);
            for (int i = 0; i < n; ++i) {
                color[x[i]] = xp[i]; by_x[xp[i]] = x[i];
                color[y[i]] = yp[i]; by_y[yp[i]] = y[i];
            }
            for (const auto& p : derangements) for (const auto& q : derangements) {
                vector<int> like(m);
                for (int c = 0; c < n; ++c) {
                    like[by_x[c]] = by_y[p[c]];
                    like[by_y[c]] = by_x[q[c]];
                }
                check_instance(DirectOracle(sex, color, like), true, n <= 3);
                ++exhaustive_cases;
                ++exhaustive_by_n[n];
            }
        }
    }
}

vector<int> random_derangement(int n, mt19937& rng) {
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);
    for (;;) {
        shuffle(p.begin(), p.end(), rng);
        bool okay = true;
        for (int i = 0; i < n; ++i) if (p[i] == i) okay = false;
        if (okay) return p;
    }
}

DirectOracle generated(int n, mt19937& rng, int mode) {
    vector<int> order(2*n), sex(2*n), color(2*n), like(2*n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    vector<int> x(n), y(n);
    for (int c = 0; c < n; ++c) {
        x[c] = order[c]; y[c] = order[n+c];
        sex[x[c]] = 0; sex[y[c]] = 1;
        color[x[c]] = color[y[c]] = c;
    }
    auto p = random_derangement(n, rng), q = random_derangement(n, rng);
    if (mode == 1) { // all preferences are mutual
        for (int c = 0; c < n; ++c) q[p[c]] = c;
    } else if (mode == 2) { // degree three everywhere (unless N=2)
        for (int c = 0; c < n; ++c) p[c] = q[c] = (c+1)%n;
    } else if (mode == 3) { // many small components, with both degree types
        for (int begin = 0; begin < n;) {
            int block = (n-begin == 2 || n-begin == 4) ? 2 : 3;
            for (int k = 0; k < block; ++k)
                p[begin+k] = q[begin+k] = begin + (k+1)%block;
            begin += block;
        }
    }
    for (int c = 0; c < n; ++c) {
        like[x[c]] = y[p[c]];
        like[y[c]] = x[q[c]];
    }
    return DirectOracle(sex, color, like);
}

template<class Exception, class F> void rejects(F action) {
    bool caught = false;
    try { action(); } catch (const Exception&) { caught = true; }
    assert(caught);
}

int main() {
    assert(hidden_color_pair_query_bound(500) == 19000);
    int previous_bound = 0;
    for (int n = 2; n <= 500; ++n) {
        int lg = 0, power = 1;
        while (power < n) { power *= 2; ++lg; }
        int independent_bound = 3*n*(1+lg) + 8*n;
        assert(hidden_color_pair_query_bound(n) == independent_bound);
        assert(independent_bound >= previous_bound && independent_bound <= 19000);
        previous_bound = independent_bound;
    }
    for (int n : {-1, 0, 1, 501}) {
        rejects<invalid_argument>([&] { hidden_color_pair_query_bound(n); });
        rejects<invalid_argument>([&] {
            recover_hidden_color_pairs(n, [](const vector<int>&) -> int { assert(false); return 0; });
        });
    }
    for (int n : {2, 3, 4, 499, 500}) rejects<invalid_argument>([&] {
        recover_hidden_color_pairs(n, [](const vector<int>&) -> int { assert(false); return 0; },
                                   hidden_color_pair_query_bound(n)-1);
    });
    for (int wrong : {-1, 0, 3}) rejects<runtime_error>([&] {
        recover_hidden_color_pairs(2, [&](const vector<int>&) { return wrong; });
    });
    exhaustive(2);
    exhaustive(3);
    exhaustive(4);
    assert(exhaustive_by_n[2] == 24 && exhaustive_by_n[3] == 2880 && exhaustive_by_n[4] == 136080);
    mt19937 rng(20201015);
    for (int trial = 0; trial < 1200; ++trial) {
        int n = 2 + rng()%79;
        check_instance(generated(n, rng, trial%4), false, false, trial < 100);
        ++random_cases;
    }
    for (int n : {127,128,129,255,256,257,499,500}) for (int trial = 0; trial < 12; ++trial) {
        check_instance(generated(n, rng, trial%4), false, false, trial == 0);
        ++random_cases;
    }
    for (int trial = 0; trial < 48; ++trial) {
        check_instance(generated(500, rng, trial%4), false, false, trial < 4);
        ++random_cases;
    }
    auto oracle = generated(3, rng, 2);
    assert(oracle.count_colors({}) == 0);
    rejects<invalid_argument>([&] { oracle.count_colors({-1}); });
    rejects<invalid_argument>([&] { oracle.count_colors({6}); });
    rejects<invalid_argument>([&] { oracle.count_colors({0,0}); });
    rejects<invalid_argument>([&] { oracle.answer(0,0); });
    rejects<invalid_argument>([&] { oracle.answer(-1,0); });
    rejects<invalid_argument>([&] { oracle.finish(); });
    int other = 1;
    while (oracle.color[other] == oracle.color[0]) ++other;
    rejects<invalid_argument>([&] { oracle.answer(0,other); });
    int mate = 1;
    while (oracle.color[mate] != oracle.color[0]) ++mate;
    oracle.answer(0,mate);
    rejects<invalid_argument>([&] { oracle.answer(0,mate); });
    oracle.calls = 20000;
    rejects<runtime_error>([&] { oracle.query({0}); });
    cout << "{\"status\":\"passed\",\"exhaustiveCases\":" << exhaustive_cases
         << ",\"exhaustiveByN\":{\"2\":" << exhaustive_by_n[2]
         << ",\"3\":" << exhaustive_by_n[3] << ",\"4\":" << exhaustive_by_n[4]
         << "},\"randomCases\":" << random_cases << ",\"officialAdapterCases\":" << adapter_cases
         << ",\"independentSetLemmaChecks\":" << lemma_checks << ",\"rawPairGraphChecks\":" << graph_checks
         << ",\"totalQueries\":" << total_queries << ",\"maximumObservedQueries\":" << max_queries
         << ",\"provedMaximumQueries\":19000,\"officialLimit\":20000,\"maximumQuerySetSize\":" << max_query_set
         << ",\"maximumQueryElementsPerInstance\":" << max_elements
         << ",\"invalidArgumentChecks\":\"passed\"}\n";
}
'''


def main():
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', ARTICLE.read_text(), re.M | re.S)
    if len(fences) != 2:
        raise ValueError('Expected a core implementation and an official adapter')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-chameleon-build-') as directory:
        directory = Path(directory)
        (directory / 'chameleon.h').write_text('#include <vector>\nint Query(const std::vector<int>&);\nvoid Answer(int,int);\n')
        source, binary = directory / 'test.cpp', directory / 'test'
        source.write_text('\n'.join(fences) + TESTS)
        subprocess.run([compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True, timeout=90)
        completed = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=180)
        result = json.loads(completed.stdout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        Path('/tmp/flowchartcp-chameleon-test-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
