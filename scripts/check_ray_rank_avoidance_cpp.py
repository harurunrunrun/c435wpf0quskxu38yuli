#!/usr/bin/env python3
"""Check six published ray, rank, avoidance and tree-cost implementations."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SITE = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```cpp\s*\n(.*?)^```\s*$", re.M | re.S)
ARTICLES = (
    "second-maximum-subarray-contribution",
    "frequency-equals-value-offline",
    "grid-ray-direction-prefix",
    "permutation-inversion-window-dp",
    "forward-dag-vertex-avoidance-intervals",
    "tree-root-reversal-costs",
)


def extracted_source():
    """Use the examples readers actually receive, rather than copied code."""
    includes = set()
    examples = []
    for slug in ARTICLES:
        article = SITE / "src/content/docs/techniques" / (slug + ".mdx")
        matches = FENCE.findall(article.read_text(encoding="utf8"))
        if len(matches) != 1:
            raise ValueError(f"{article.name}: expected one complete C++ example")
        source = matches[0]
        includes.update(re.findall(r"^#include[^\n]*$", source, re.M))
        source = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.M)
        examples.append("namespace article_" + slug.replace("-", "_")
                        + " {\n" + source + "\n}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <algorithm>
#include <cassert>
#include <climits>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace std;

using article_second_maximum_subarray_contribution::all_subarray_second_maximum_sum;
using article_frequency_equals_value_offline::offline_frequency_equals_value;
using article_grid_ray_direction_prefix::count_grid_ray_paths;
using article_permutation_inversion_window_dp::count_permutations_with_inversions;
using article_forward_dag_vertex_avoidance_intervals::shortest_paths_avoiding_each_forward_vertex;
using article_tree_root_reversal_costs::RootReversalEdge;
using article_tree_root_reversal_costs::minimum_root_reversal_costs;

constexpr long long MOD = 1000000007;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

long long modular_power(long long value, int exponent) {
    long long result = 1;
    for (; exponent; exponent >>= 1, value = value * value % MOD)
        if (exponent & 1) result = result * value % MOD;
    return result;
}

__int128 literal_second_maximum(const vector<long long>& values) {
    __int128 answer = 0;
    for (int left = 0; left < int(values.size()); ++left)
        for (int right = left + 1; right < int(values.size()); ++right) {
            vector<long long> interval(values.begin() + left, values.begin() + right + 1);
            sort(interval.begin(), interval.end(), greater<long long>());
            answer += interval[1];
        }
    return answer;
}

void check_second_case(const vector<long long>& values) {
    const auto before = values;
    assert(all_subarray_second_maximum_sum(values) == literal_second_maximum(values));
    assert(values == before);
}

void check_second_maximum(mt19937& rng) {
    const vector<long long> alphabet = {LLONG_MIN, -2, 0, LLONG_MAX};
    for (int n = 0; n <= 7; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= int(alphabet.size());
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<long long> values(n);
            for (long long& value : values) {
                value = alphabet[code % alphabet.size()];
                code /= int(alphabet.size());
            }
            check_second_case(values);
        }
    }
    for (int n = 2; n <= 8; ++n) {
        vector<long long> values(n);
        iota(values.begin(), values.end(), 1);
        do { check_second_case(values); } while (next_permutation(values.begin(), values.end()));
    }
    for (int trial = 0; trial < 600; ++trial) {
        vector<long long> values(rng() % 40);
        for (long long& value : values) value = (long long)(rng() % 101) - 50;
        check_second_case(values);
    }
    const int n = 200000;
    const __int128 intervals = (__int128)n * (n - 1) / 2;
    assert(all_subarray_second_maximum_sum(vector<long long>(n, LLONG_MAX)) == intervals * LLONG_MAX);
    assert(all_subarray_second_maximum_sum(vector<long long>(n, LLONG_MIN)) == intervals * LLONG_MIN);
    vector<long long> increasing(n);
    iota(increasing.begin(), increasing.end(), 1);
    const __int128 expected = (__int128)(n - 1) * n * (2 * n - 1) / 6;
    assert(all_subarray_second_maximum_sum(increasing) == expected);
    reverse(increasing.begin(), increasing.end());
    assert(all_subarray_second_maximum_sum(increasing) == expected);
    require_exception<invalid_argument>([] { (void)all_subarray_second_maximum_sum(vector<long long>(200001)); });
    cout << "second-maximum-subarray-contribution PASS: every short duplicate/extreme-value array and permutation against sorted intervals, signed 128-bit totals and 200000-element boundaries\n";
}

vector<int> literal_frequency(const vector<long long>& values,
                              const vector<pair<int, int>>& queries) {
    vector<int> result;
    for (const auto& [left, right] : queries) {
        map<long long, int> frequency;
        for (int i = left; i < right; ++i) ++frequency[values[i]];
        int answer = 0;
        for (const auto& [value, count] : frequency) answer += value == count;
        result.push_back(answer);
    }
    return result;
}

void check_frequency_case(const vector<long long>& values,
                          const vector<pair<int, int>>& queries) {
    const auto before_values = values;
    const auto before_queries = queries;
    assert(offline_frequency_equals_value(values, queries) == literal_frequency(values, queries));
    assert(values == before_values && queries == before_queries);
}

void check_frequency(mt19937& rng) {
    const vector<long long> alphabet = {1, 2, 3, 5, 1000000000};
    for (int n = 0; n <= 6; ++n) {
        vector<pair<int, int>> queries;
        for (int left = 0; left <= n; ++left)
            for (int right = left; right <= n; ++right) queries.emplace_back(left, right);
        reverse(queries.begin(), queries.end());
        if (!queries.empty()) queries.push_back(queries.front());
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= int(alphabet.size());
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<long long> values(n);
            for (long long& value : values) {
                value = alphabet[code % alphabet.size()];
                code /= int(alphabet.size());
            }
            check_frequency_case(values, queries);
        }
    }
    for (int trial = 0; trial < 1000; ++trial) {
        const int n = rng() % 60;
        vector<long long> values(n);
        for (long long& value : values) value = 1 + rng() % 70;
        vector<pair<int, int>> queries;
        for (int i = 0; i < 100; ++i) {
            int left = rng() % (n + 1), right = rng() % (n + 1);
            if (left > right) swap(left, right);
            queries.emplace_back(left, right);
        }
        check_frequency_case(values, queries);
    }
    const int n = 200000;
    vector<pair<int, int>> queries;
    for (int i = 0; i < n; ++i) queries.emplace_back(i, i + 1);
    assert(offline_frequency_equals_value(vector<long long>(n, 1), queries) == vector<int>(n, 1));
    assert(offline_frequency_equals_value(vector<long long>(n, 1000000000), queries) == vector<int>(n, 0));
    vector<pair<int, int>> broad = {{0, n}, {0, 2}, {n - 2, n}, {n, n}, {0, 1}, {0, 3}};
    assert(offline_frequency_equals_value(vector<long long>(n, 2), broad)
           == (vector<int>{0, 1, 1, 0, 0, 0}));
    require_exception<invalid_argument>([] { (void)offline_frequency_equals_value(vector<long long>(200001, 1), {}); });
    require_exception<invalid_argument>([] { (void)offline_frequency_equals_value({}, vector<pair<int, int>>(200001, {0, 0})); });
    for (long long bad : {LLONG_MIN, -1LL, 0LL, 1000000001LL, LLONG_MAX})
        require_exception<invalid_argument>([&] { (void)offline_frequency_equals_value({bad}, {}); });
    for (auto query : vector<pair<int, int>>{{-1, 0}, {0, 2}, {1, 0}, {2, 2}, {0, -1}})
        require_exception<out_of_range>([&] { (void)offline_frequency_equals_value({1}, {query}); });
    cout << "frequency-equals-value-offline PASS: direct maps over every short interval, shuffled/repeated/empty queries, candidate-count boundaries and 200000 values/queries\n";
}

int literal_grid_paths(const vector<string>& grid) {
    const int height = grid.size(), width = height ? grid[0].size() : 0;
    if (!height || !width || grid[0][0] == '#' || grid.back().back() == '#') return 0;
    vector<vector<long long>> ways(height, vector<long long>(width));
    ways[0][0] = 1;
    const vector<pair<int, int>> directions = {{1, 0}, {0, 1}, {1, 1}};
    for (int row = 0; row < height; ++row)
        for (int column = 0; column < width; ++column) if (grid[row][column] == '.')
            for (const auto& [dr, dc] : directions)
                for (int rr = row + dr, cc = column + dc;
                     rr < height && cc < width && grid[rr][cc] == '.'; rr += dr, cc += dc)
                    ways[rr][cc] = (ways[rr][cc] + ways[row][column]) % MOD;
    return int(ways.back().back());
}

void check_grid_case(const vector<string>& grid) {
    const auto before = grid;
    assert(count_grid_ray_paths(grid) == literal_grid_paths(grid));
    assert(grid == before);
}

void check_grid_paths(mt19937& rng) {
    check_grid_case({});
    check_grid_case({""});
    check_grid_case({"", "", ""});
    for (int height = 1; height <= 4; ++height)
        for (int width = 1; width <= 4; ++width)
            for (int mask = 0; mask < (1 << (height * width)); ++mask) {
                vector<string> grid(height, string(width, '.'));
                for (int r = 0; r < height; ++r)
                    for (int c = 0; c < width; ++c)
                        if (mask >> (r * width + c) & 1) grid[r][c] = '#';
                check_grid_case(grid);
            }
    for (int trial = 0; trial < 700; ++trial) {
        const int height = 1 + rng() % 30, width = 1 + rng() % 30;
        vector<string> grid(height, string(width, '.'));
        for (string& row : grid) for (char& cell : row) if (rng() % 5 == 0) cell = '#';
        check_grid_case(grid);
    }
    assert(count_grid_ray_paths(vector<string>{string(2000, '.')}) == modular_power(2, 1998));
    assert(count_grid_ray_paths(vector<string>(2000, ".")) == modular_power(2, 1998));
    vector<string> diagonal(2000, string(2000, '#'));
    for (int i = 0; i < 2000; ++i) diagonal[i][i] = '.';
    assert(count_grid_ray_paths(diagonal) == modular_power(2, 1998));
    vector<string> blocked(2000, string(2000, '#'));
    assert(count_grid_ray_paths(blocked) == 0);
    require_exception<length_error>([] { (void)count_grid_ray_paths(vector<string>(2001)); });
    require_exception<length_error>([] { (void)count_grid_ray_paths({string(2001, '.')}); });
    for (const auto& grid : vector<vector<string>>{{".", ".."}, {"", "."}, {"x"}, {"#x"}, {".", "?"}})
        require_exception<invalid_argument>([&] { (void)count_grid_ray_paths(grid); });
    cout << "grid-ray-direction-prefix PASS: direct cell-by-cell ray moves for every wall pattern through 4x4, obstacle resets and 2000x2000/empty/input boundaries\n";
}

long long independent_inversion_generating_coefficient(int n, int k) {
    if (n == 0) return k == 0;
    // Enumerate the signed numerator product, then multiply by the
    // binomial expansion of (1-z)^(-n), without sliding windows.
    vector<long long> numerator(k + 1);
    numerator[0] = 1;
    for (int factor = 1; factor <= n && factor <= k; ++factor)
        for (int degree = k; degree >= factor; --degree)
            numerator[degree] = (numerator[degree] - numerator[degree - factor] + MOD) % MOD;
    vector<long long> denominator(k + 1, 1);
    for (int degree = 1; degree <= k; ++degree)
        denominator[degree] = denominator[degree - 1] * (n + degree - 1) % MOD
                              * modular_power(degree, MOD - 2) % MOD;
    long long result = 0;
    for (int degree = 0; degree <= k; ++degree)
        result = (result + numerator[degree] * denominator[k - degree]) % MOD;
    return result;
}

void check_inversion_counts() {
    for (int n = 0; n <= 9; ++n) {
        const int maximum = n * (n - 1) / 2;
        vector<int> histogram(maximum + 1);
        vector<int> permutation(n);
        iota(permutation.begin(), permutation.end(), 0);
        do {
            int inversions = 0;
            for (int i = 0; i < n; ++i)
                for (int j = i + 1; j < n; ++j) inversions += permutation[i] > permutation[j];
            ++histogram[inversions];
        } while (next_permutation(permutation.begin(), permutation.end()));
        for (int k = 0; k <= min(1000, maximum + 3); ++k)
            assert(count_permutations_with_inversions(n, k) == (k <= maximum ? histogram[k] : 0));
    }
    for (const auto& [n, k] : vector<pair<int, int>>{
            {1000, 1000}, {1000, 999}, {1000, 500}, {100, 1000}, {45, 990},
            {45, 989}, {44, 946}, {44, 945}, {44, 947}, {2, 1000}, {1, 1000}, {0, 1000}})
        assert(count_permutations_with_inversions(n, k) == independent_inversion_generating_coefficient(n, k));
    assert(count_permutations_with_inversions(1000, 0) == 1);
    assert(count_permutations_with_inversions(1000, 1) == 999);
    assert(count_permutations_with_inversions(1000, 2) == 499499);
    require_exception<invalid_argument>([] { (void)count_permutations_with_inversions(-1, 0); });
    require_exception<invalid_argument>([] { (void)count_permutations_with_inversions(0, -1); });
    require_exception<length_error>([] { (void)count_permutations_with_inversions(1001, 0); });
    require_exception<length_error>([] { (void)count_permutations_with_inversions(0, 1001); });
    cout << "permutation-inversion-window-dp PASS: inversion histograms of all permutations through N=9, independent generating-product coefficients at N/K=1000 and empty/symmetry/range boundaries\n";
}

vector<int> literal_avoiding_distances(int n, const vector<pair<int, int>>& edges) {
    vector<vector<int>> adjacency(n);
    for (auto [from, to] : edges) adjacency[from].push_back(to);
    vector<int> result(n, -1);
    for (int banned = 1; banned < n - 1; ++banned) {
        vector<int> distance(n, -1);
        queue<int> work;
        work.push(0);
        distance[0] = 0;
        while (!work.empty()) {
            const int vertex = work.front(); work.pop();
            for (int next : adjacency[vertex]) if (next != banned && distance[next] == -1) {
                distance[next] = distance[vertex] + 1;
                work.push(next);
            }
        }
        result[banned] = distance[n - 1];
    }
    return result;
}

void check_avoiding_case(int n, const vector<pair<int, int>>& edges) {
    const auto before = edges;
    assert(shortest_paths_avoiding_each_forward_vertex(n, edges) == literal_avoiding_distances(n, edges));
    assert(edges == before);
}

void check_forward_avoidance(mt19937& rng) {
    for (int n = 1; n <= 6; ++n) {
        vector<pair<int, int>> universe;
        for (int from = 0; from < n; ++from)
            for (int to = from + 1; to < n; ++to) universe.emplace_back(from, to);
        for (int mask = 0; mask < (1 << universe.size()); ++mask) {
            vector<pair<int, int>> edges;
            for (int i = 0; i < int(universe.size()); ++i)
                if (mask >> i & 1) edges.push_back(universe[i]);
            check_avoiding_case(n, edges);
        }
    }
    for (int trial = 0; trial < 2000; ++trial) {
        const int n = 1 + rng() % 50;
        vector<pair<int, int>> edges;
        for (int from = 0; from < n; ++from)
            for (int to = from + 1; to < n; ++to) if (rng() % 7 == 0) {
                edges.emplace_back(from, to);
                if (rng() % 3 == 0) edges.emplace_back(from, to);
            }
        shuffle(edges.begin(), edges.end(), rng);
        check_avoiding_case(n, edges);
    }
    const int n = 200000;
    vector<pair<int, int>> chain;
    for (int i = 0; i + 1 < n; ++i) chain.emplace_back(i, i + 1);
    assert(shortest_paths_avoiding_each_forward_vertex(n, chain) == vector<int>(n, -1));
    chain.emplace_back(0, n - 1);
    vector<int> direct(n, 1);
    direct.front() = direct.back() = -1;
    assert(shortest_paths_avoiding_each_forward_vertex(n, chain) == direct);
    assert(shortest_paths_avoiding_each_forward_vertex(3, vector<pair<int, int>>(2000000, {0, 2}))
           == (vector<int>{-1, 1, -1}));
    require_exception<invalid_argument>([] { (void)shortest_paths_avoiding_each_forward_vertex(0, {}); });
    require_exception<invalid_argument>([] { (void)shortest_paths_avoiding_each_forward_vertex(200001, {}); });
    require_exception<length_error>([] { (void)shortest_paths_avoiding_each_forward_vertex(3, vector<pair<int, int>>(2000001, {0, 2})); });
    for (auto edge : vector<pair<int, int>>{{-1, 1}, {0, 3}, {1, 1}, {2, 1}, {3, 4}})
        require_exception<invalid_argument>([&] { (void)shortest_paths_avoiding_each_forward_vertex(3, {edge}); });
    cout << "forward-dag-vertex-avoidance-intervals PASS: delete-each-vertex BFS for every forward graph through N=6, duplicate/unreachable paths and N=200000/M=2000000 boundaries\n";
}

vector<__int128> literal_root_costs(int n, const vector<RootReversalEdge>& edges) {
    vector<vector<int>> adjacency(n);
    for (const auto& edge : edges) {
        adjacency[edge.from].push_back(edge.to);
        adjacency[edge.to].push_back(edge.from);
    }
    vector<__int128> result(n);
    for (int root = 0; root < n; ++root) {
        vector<int> depth(n, -1);
        queue<int> work;
        work.push(root); depth[root] = 0;
        while (!work.empty()) {
            const int vertex = work.front(); work.pop();
            for (int next : adjacency[vertex]) if (depth[next] == -1) {
                depth[next] = depth[vertex] + 1;
                work.push(next);
            }
        }
        for (const auto& edge : edges)
            if (depth[edge.from] > depth[edge.to]) result[root] += edge.cost;
    }
    return result;
}

vector<pair<int, int>> prufer_tree(int n, int code) {
    if (n == 1) return {};
    vector<int> sequence(max(0, n - 2));
    vector<int> degree(n, 1);
    for (int& value : sequence) { value = code % n; code /= n; ++degree[value]; }
    vector<pair<int, int>> edges;
    for (int value : sequence) {
        int leaf = 0;
        while (degree[leaf] != 1) ++leaf;
        edges.emplace_back(leaf, value);
        --degree[leaf]; --degree[value];
    }
    int first = -1;
    for (int vertex = 0; vertex < n; ++vertex) if (degree[vertex] == 1) {
        if (first == -1) first = vertex;
        else edges.emplace_back(first, vertex);
    }
    return edges;
}

void check_root_case(int n, const vector<RootReversalEdge>& edges) {
    const auto expected = literal_root_costs(n, edges);
    const auto actual = minimum_root_reversal_costs(n, edges);
    assert(actual == expected);
}

void check_root_reversal(mt19937& rng) {
    const vector<long long> costs = {0, 1, 7, LLONG_MAX};
    for (int n = 1; n <= 6; ++n) {
        int trees = 1;
        for (int i = 0; i < n - 2; ++i) trees *= n;
        for (int code = 0; code < trees; ++code) {
            const auto tree = prufer_tree(n, code);
            for (int orientation = 0; orientation < (1 << tree.size()); ++orientation) {
                vector<RootReversalEdge> edges;
                for (int i = 0; i < int(tree.size()); ++i) {
                    auto [from, to] = tree[i];
                    if (orientation >> i & 1) swap(from, to);
                    edges.push_back({from, to, costs[(i + orientation + code) % costs.size()]});
                }
                check_root_case(n, edges);
            }
        }
    }
    for (int trial = 0; trial < 1000; ++trial) {
        const int n = 1 + rng() % 70;
        vector<RootReversalEdge> edges;
        for (int vertex = 1; vertex < n; ++vertex) {
            int from = rng() % vertex, to = vertex;
            if (rng() & 1) swap(from, to);
            edges.push_back({from, to, (rng() % 3 == 0) ? LLONG_MAX : (long long)(rng() % 1000000000)});
        }
        shuffle(edges.begin(), edges.end(), rng);
        check_root_case(n, edges);
    }
    const int n = 200000;
    vector<RootReversalEdge> chain;
    for (int i = 0; i + 1 < n; ++i) chain.push_back({i, i + 1, LLONG_MAX});
    auto result = minimum_root_reversal_costs(n, chain);
    assert(result.size() == size_t(n));
    for (int root = 0; root < n; ++root) assert(result[root] == (__int128)root * LLONG_MAX);
    for (auto& edge : chain) swap(edge.from, edge.to);
    result = minimum_root_reversal_costs(n, chain);
    for (int root = 0; root < n; ++root) assert(result[root] == (__int128)(n - 1 - root) * LLONG_MAX);
    vector<RootReversalEdge> star;
    for (int i = 1; i < n; ++i) star.push_back({0, i, 0});
    assert(minimum_root_reversal_costs(n, star) == vector<__int128>(n, 0));
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(0, {}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(200001, {}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(2, {}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(1, {{0, 0, 1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(2, {{0, 0, 1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(2, {{-1, 1, 1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(2, {{0, 2, 1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(2, {{0, 1, -1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(3, {{0, 1, 1}, {1, 0, 1}}); });
    require_exception<invalid_argument>([] { (void)minimum_root_reversal_costs(4, {{0, 1, 1}, {1, 2, 1}, {2, 0, 1}}); });
    cout << "tree-root-reversal-costs PASS: every labelled tree/orientation through N=6 using an independent BFS from every root, zero/64-bit costs and 200000-vertex chains/stars with 128-bit totals\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261025);
    check_second_maximum(rng);
    check_frequency(rng);
    check_grid_paths(rng);
    check_inversion_counts();
    check_forward_avoidance(rng);
    check_root_reversal(rng);
}

'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-ray-rank-avoidance-cpp-") as directory:
        source = Path(directory) / "comparisons.cpp"
        executable = Path(directory) / "comparisons"
        source.write_text(extracted_source() + "\n" + TESTS, encoding="utf8")
        compiled = subprocess.run(
            [args.compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
             str(source), "-o", str(executable)],
            capture_output=True, text=True, timeout=120)
        if compiled.returncode:
            print(compiled.stderr, file=sys.stderr)
            return compiled.returncode
        result = subprocess.run([str(executable)], cwd=directory, timeout=180)
        if result.returncode:
            return result.returncode
        print("All 6 ray, rank and avoidance implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
