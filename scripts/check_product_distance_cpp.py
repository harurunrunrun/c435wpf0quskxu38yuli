#!/usr/bin/env python3
"""Compare the published synchronized product-distance implementation with literal product graphs."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SITE = Path(__file__).resolve().parent.parent
ARTICLE = SITE / 'src/content/docs/techniques/synchronous-product-parity-distance-sum.mdx'

TESTS = r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <random>
using namespace std;
constexpr long long TEST_MOD = 1000000007;

int literal_product_sum(const vector<SynchronousFactorGraph>& factors) {
    int product = 1;
    vector<int> stride;
    vector<vector<vector<int>>> adjacent;
    for (const auto& factor : factors) {
        stride.push_back(product);
        product *= factor.vertex_count;
        adjacent.emplace_back(factor.vertex_count);
        for (const auto& [u, v] : factor.edges) {
            adjacent.back()[u].push_back(v);
            adjacent.back()[v].push_back(u);
        }
    }
    vector<int> distance(product, -1), queue{0};
    distance[0] = 0;
    long long result = 0;
    for (size_t head = 0; head < queue.size(); ++head) {
        const int state = queue[head];
        vector<int> position(factors.size());
        for (size_t i = 0; i < factors.size(); ++i)
            position[i] = state / stride[i] % factors[i].vertex_count;
        auto walk_one_step = [&](auto&& self, size_t i, int next_state) -> void {
            if (i == factors.size()) {
                if (distance[next_state] < 0) {
                    distance[next_state] = distance[state] + 1;
                    result += distance[next_state];
                    queue.push_back(next_state);
                }
                return;
            }
            for (int to : adjacent[i][position[i]])
                self(self, i + 1, next_state + stride[i] * to);
        };
        walk_one_step(walk_one_step, 0, 0);
    }
    return int(result % TEST_MOD);
}

void check(const vector<SynchronousFactorGraph>& factors) {
    const int expected = literal_product_sum(factors);
    const int actual = synchronous_product_distance_sum(factors);
    if (expected != actual) {
        cerr << "mismatch expected=" << expected << " actual=" << actual << '\n';
        for (const auto& f : factors) {
            cerr << "n=" << f.vertex_count << " edges:";
            for (const auto& [u, v] : f.edges) cerr << ' ' << u << ',' << v;
            cerr << '\n';
        }
        abort();
    }
}

vector<SynchronousFactorGraph> all_graphs(int max_n) {
    vector<SynchronousFactorGraph> result;
    for (int n = 1; n <= max_n; ++n) {
        vector<pair<int, int>> possible;
        for (int u = 0; u < n; ++u)
            for (int v = u; v < n; ++v) possible.emplace_back(u, v);
        for (int mask = 0; mask < (1 << possible.size()); ++mask) {
            SynchronousFactorGraph factor{n, {}};
            for (size_t i = 0; i < possible.size(); ++i)
                if (mask >> i & 1) factor.edges.push_back(possible[i]);
            result.push_back(factor);
        }
    }
    return result;
}

template<class Exception, class Function>
void require_exception(Function function) {
    bool thrown = false;
    try { function(); }
    catch (const Exception&) { thrown = true; }
    assert(thrown);
}

long long power(long long a, int b) {
    long long answer = 1;
    for (; b; b >>= 1, a = a * a % TEST_MOD)
        if (b & 1) answer = answer * a % TEST_MOD;
    return answer;
}

int main() {
    check({});
    const auto short_graphs = all_graphs(3);
    for (const auto& a : short_graphs)
        for (const auto& b : short_graphs) check({a, b});
    const auto tiny_graphs = all_graphs(2);
    for (const auto& a : tiny_graphs)
        for (const auto& b : tiny_graphs)
            for (const auto& c : tiny_graphs) check({a, b, c});
    const auto solo_graphs = all_graphs(5);
    for (const auto& a : solo_graphs) check({a});
    mt19937 random(20261015);
    for (int trial = 0; trial < 2000; ++trial) {
        vector<SynchronousFactorGraph> factors;
        const int k = 1 + random() % 5;
        for (int i = 0; i < k; ++i) {
            const int n = 1 + random() % 4;
            SynchronousFactorGraph factor{n, {}};
            for (int u = 0; u < n; ++u)
                for (int v = u; v < n; ++v) if (random() % 3 == 0) {
                    factor.edges.emplace_back(u, v);
                    if (random() % 5 == 0) factor.edges.emplace_back(v, u);
                }
            shuffle(factor.edges.begin(), factor.edges.end(), random);
            factors.push_back(factor);
        }
        check(factors);
    }
    const SynchronousFactorGraph two_vertex_edge{2, {{0, 1}}};
    assert(synchronous_product_distance_sum({two_vertex_edge, two_vertex_edge}) == 1);
    const SynchronousFactorGraph triangle{3, {{0, 1}, {1, 2}, {2, 0}}};
    check({triangle, triangle});
    check({two_vertex_edge, triangle});
    check({{1, {{0, 0}}}, triangle});
    check({{3, {{1, 2}}}, triangle});
    check({{5, {{0, 1}, {1, 2}, {2, 0}, {3, 4}}}, triangle});
    cout << "product-distance-literal PASS: all loop-allowing graph pairs through 3 vertices, triples through 2, single graphs through 5, and 2000 random products against explicit product-state BFS\n";

    SynchronousFactorGraph chain{100000, {}};
    for (int i = 1; i < chain.vertex_count; ++i) chain.edges.emplace_back(i - 1, i);
    assert(synchronous_product_distance_sum({chain}) == (99999LL * 100000 / 2) % TEST_MOD);
    SynchronousFactorGraph odd_cycle{99999, {}};
    for (int i = 0; i < odd_cycle.vertex_count; ++i)
        odd_cycle.edges.emplace_back(i, (i + 1) % odd_cycle.vertex_count);
    assert(synchronous_product_distance_sum({odd_cycle}) == (99999LL * 99999 / 4) % TEST_MOD);
    vector<SynchronousFactorGraph> many_pairs(50000, two_vertex_edge);
    assert(synchronous_product_distance_sum(many_pairs) == 1);
    const SynchronousFactorGraph complete_with_loops{2, {{0, 0}, {0, 1}, {1, 1}}};
    vector<SynchronousFactorGraph> many_complete(30000, complete_with_loops);
    assert(synchronous_product_distance_sum(many_complete) == (power(2, 30000) - 1 + TEST_MOD) % TEST_MOD);
    SynchronousFactorGraph repeated{2, vector<pair<int, int>>(200000, {0, 1})};
    assert(synchronous_product_distance_sum({repeated}) == 1);
    SynchronousFactorGraph long_other{99998, {}};
    for (int i = 1; i < long_other.vertex_count; ++i) long_other.edges.emplace_back(i - 1, i);
    assert(synchronous_product_distance_sum({two_vertex_edge, long_other}) == (99997LL * 99998 / 2) % TEST_MOD);
    assert(synchronous_product_distance_sum({{1, {}}, long_other}) == 0);
    cout << "product-distance-boundaries PASS: 100000 vertices, 200000 edges, 50000 factors, long odd cycle, huge destination products and unequal distance bounds\n";

    require_exception<invalid_argument>([] { (void)synchronous_product_distance_sum({{0, {}}}); });
    require_exception<invalid_argument>([] { (void)synchronous_product_distance_sum({{-1, {}}}); });
    require_exception<invalid_argument>([] { (void)synchronous_product_distance_sum({{2, {{-1, 1}}}}); });
    require_exception<invalid_argument>([] { (void)synchronous_product_distance_sum({{2, {{0, 2}}}}); });
    require_exception<invalid_argument>([] { (void)synchronous_product_distance_sum({{1, {}}, {2, {{0, -1}}}}); });
    require_exception<length_error>([] { (void)synchronous_product_distance_sum({{100001, {}}}); });
    require_exception<length_error>([] { (void)synchronous_product_distance_sum(vector<SynchronousFactorGraph>(50001, {1, {{0, 0}}})); });
    require_exception<length_error>([] { (void)synchronous_product_distance_sum({{50001, {}}, {50000, {}}}); });
    require_exception<length_error>([] { (void)synchronous_product_distance_sum({{2, vector<pair<int, int>>(200001, {0, 1})}}); });
    cout << "product-distance-contracts PASS: empty products, isolated starts, disconnected factors, self loops, parallel edges and invalid input limits\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default=os.environ.get('CXX', 'g++'))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f'C++20 compiler not found: {args.compiler}')
    matches = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', ARTICLE.read_text(), re.M | re.S)
    if len(matches) != 1:
        parser.error('expected exactly one complete C++ fence')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-product-distance-') as directory:
        source = Path(directory) / 'compare.cpp'
        executable = Path(directory) / 'compare'
        source.write_text(matches[0] + '\n' + TESTS)
        compiled = subprocess.run([args.compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], capture_output=True, text=True, timeout=120)
        if compiled.returncode:
            print(compiled.stderr, file=sys.stderr)
            return compiled.returncode
        result = subprocess.run([str(executable)], timeout=120)
        if result.returncode:
            return result.returncode
        print('Published synchronized product-distance implementation passed independent product-graph BFS and boundary comparisons.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
