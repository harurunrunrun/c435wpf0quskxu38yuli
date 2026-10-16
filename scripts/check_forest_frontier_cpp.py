#!/usr/bin/env python3
"""Compare the published dynamic-forest and frontier examples with independent models."""

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
ARTICLES = ("dynamic-forest-path-aggregate", "frontier-single-cycle")


def extracted_source():
    """Compile the actual article code, without maintaining a second implementation."""
    includes = set()
    examples = []
    for slug in ARTICLES:
        article = SITE / "src/content/docs/techniques" / (slug + ".mdx")
        matches = FENCE.findall(article.read_text(encoding="utf8"))
        if len(matches) != 1:
            raise ValueError(f"{article.name}: expected exactly one complete C++ example")
        source = matches[0]
        includes.update(re.findall(r"^#include[^\n]*$", source, re.M))
        source = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.M)
        namespace = "article_" + slug.replace("-", "_")
        examples.append(f"namespace {namespace} {{\n{source}\n}}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <cassert>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <set>
using namespace std;
using article_dynamic_forest_path_aggregate::LinkCutPath;
using article_dynamic_forest_path_aggregate::SumMonoid;
using article_dynamic_forest_path_aggregate::Affine;
using article_dynamic_forest_path_aggregate::AffineMonoid;
using article_frontier_single_cycle::count_grid_hamiltonian_cycles;
using boost::multiprecision::cpp_int;

// The oracle stores ordinary undirected edges. It never uses preferred paths,
// rotations, auxiliary roots, lazy reversal, or the article's combine function.
struct ForestOracle {
    vector<set<int>> adjacency;
    vector<long long> values;
    vector<Affine> functions;

    explicit ForestOracle(int n) : adjacency(n), values(n), functions(n, {1, 0}) {}

    vector<int> path(int source, int target) const {
        vector<int> parent(adjacency.size(), -1);
        queue<int> pending;
        parent[source] = source;
        pending.push(source);
        while (!pending.empty()) {
            int u = pending.front();
            pending.pop();
            for (int v : adjacency[u]) if (parent[v] == -1) {
                parent[v] = u;
                pending.push(v);
            }
        }
        if (parent[target] == -1) return {};
        vector<int> result;
        for (int v = target;; v = parent[v]) {
            result.push_back(v);
            if (v == source) break;
        }
        reverse(result.begin(), result.end());
        return result;
    }

    bool link(int u, int v) {
        if (!path(u, v).empty()) return false;
        adjacency[u].insert(v);
        adjacency[v].insert(u);
        return true;
    }

    bool cut(int u, int v) {
        if (!adjacency[u].count(v)) return false;
        adjacency[u].erase(v);
        adjacency[v].erase(u);
        return true;
    }
};

void check_forest_path(ForestOracle& oracle, LinkCutPath<SumMonoid>& sums,
                       LinkCutPath<AffineMonoid>& functions, int u, int v) {
    auto path = oracle.path(u, v);
    auto sum = sums.query_path(u, v);
    auto composition = functions.query_path(u, v);
    assert(sums.connected(u, v) == !path.empty());
    assert(functions.connected(u, v) == !path.empty());
    assert(sum.has_value() == !path.empty());
    assert(composition.has_value() == !path.empty());
    if (path.empty()) return;

    long long expected_sum = 0;
    constexpr long long mod = 998244353;
    long long coefficient = 1, constant = 0;
    // Apply each vertex function in the BFS path's explicit order.
    for (int vertex : path) {
        expected_sum += oracle.values[vertex];
        auto [a, b] = oracle.functions[vertex];
        coefficient = a * coefficient % mod;
        constant = (a * constant + b) % mod;
        assert(sums.get_value(vertex) == oracle.values[vertex]);
        assert(functions.get_value(vertex) == oracle.functions[vertex]);
    }
    assert(*sum == expected_sum);
    assert(composition->a == coefficient && composition->b == constant);
    for (long long x : {0LL, 1LL, 19260817LL, mod - 1}) {
        long long expected = x;
        for (int vertex : path) {
            auto [a, b] = oracle.functions[vertex];
            expected = (a * expected + b) % mod;
        }
        assert((composition->a * x + composition->b) % mod == expected);
    }
}

void check_forest(mt19937& rng) {
    auto random = [&](int bound) { return int(rng() % unsigned(bound)); };
    // Empty construction is valid, although no vertex operation is available.
    LinkCutPath<SumMonoid> empty_sums(vector<long long>{});
    LinkCutPath<AffineMonoid> empty_functions(vector<Affine>{});

    for (int trial = 0; trial < 90; ++trial) {
        const int n = 1 + random(35);
        ForestOracle oracle(n);
        for (int u = 0; u < n; ++u) {
            oracle.values[u] = random(2001) - 1000;
            oracle.functions[u] = {random(998244353), random(998244353)};
        }
        LinkCutPath<SumMonoid> sums(oracle.values);
        LinkCutPath<AffineMonoid> functions(oracle.functions);
        auto link = [&](int u, int v) {
            bool expected = oracle.link(u, v);
            assert(sums.link(u, v) == expected);
            assert(functions.link(u, v) == expected);
        };
        auto cut = [&](int u, int v) {
            bool expected = oracle.cut(u, v);
            assert(sums.cut(u, v) == expected);
            assert(functions.cut(u, v) == expected);
        };
        // Begin with varying trees and isolated vertices, then repeatedly
        // replace edges. Failed operations must preserve every later answer.
        for (int u = 1; u < n; ++u) if (random(4)) link(u, random(u));
        for (int step = 0; step < 900; ++step) {
            int u = random(n), v = random(n);
            switch (random(8)) {
                case 0: case 1: link(u, v); break;
                case 2: case 3: {
                    if (random(2) && !oracle.adjacency[u].empty())
                        v = *next(oracle.adjacency[u].begin(), random(oracle.adjacency[u].size()));
                    cut(u, v);
                    break;
                }
                case 4:
                    oracle.values[u] = random(2000001) - 1000000;
                    oracle.functions[u] = {random(998244353), random(998244353)};
                    // Include identity and constant functions: reversal cannot
                    // depend on invertibility of a vertex function.
                    if (step % 7 == 0) oracle.functions[u] = {0, random(998244353)};
                    if (step % 11 == 0) oracle.functions[u] = {1, 0};
                    sums.set_value(u, oracle.values[u]);
                    functions.set_value(u, oracle.functions[u]);
                    break;
                case 5:
                    for (int repeat = 0; repeat < 3; ++repeat) {
                        sums.make_root(u);
                        functions.make_root(u);
                    }
                    break;
                case 6: cut(u, u); link(u, u); break;
                case 7: check_forest_path(oracle, sums, functions, u, u); break;
            }
            check_forest_path(oracle, sums, functions, u, v);
            check_forest_path(oracle, sums, functions, v, u);
            if (step % 150 == 0) for (int a = 0; a < n; ++a) for (int b = 0; b < n; ++b)
                check_forest_path(oracle, sums, functions, a, b);
        }
    }

    // A long path exposes reversal flags over many rotations. Cut each direct
    // edge in alternating directions, query the split, then reconnect reversed.
    const int n = 97;
    ForestOracle oracle(n);
    for (int u = 0; u < n; ++u) {
        oracle.values[u] = u - 48;
        oracle.functions[u] = {u + 2, u * u + 3};
    }
    LinkCutPath<SumMonoid> sums(oracle.values);
    LinkCutPath<AffineMonoid> functions(oracle.functions);
    for (int u = 1; u < n; ++u) {
        assert(oracle.link(u - 1, u));
        assert(sums.link(u - 1, u));
        assert(functions.link(u - 1, u));
    }
    assert(!sums.cut(0, n - 1));
    assert(!functions.cut(n - 1, 0));
    assert(!sums.link(n - 1, 0));
    assert(!functions.link(0, n - 1));
    for (int step = 0; step < 300; ++step) {
        int root = random(n), edge = random(n - 1);
        sums.make_root(root);
        functions.make_root(root);
        int u = edge, v = edge + 1;
        if (step & 1) swap(u, v);
        assert(oracle.cut(u, v));
        assert(sums.cut(u, v));
        assert(functions.cut(u, v));
        check_forest_path(oracle, sums, functions, 0, n - 1);
        check_forest_path(oracle, sums, functions, edge, edge);
        assert(!sums.cut(v, u));
        assert(!functions.cut(v, u));
        oracle.values[root] += step - 150;
        oracle.functions[root] = {step % 5, step * step + 7};
        sums.set_value(root, oracle.values[root]);
        functions.set_value(root, oracle.functions[root]);
        assert(oracle.link(v, u));
        assert(sums.link(v, u));
        assert(functions.link(v, u));
        check_forest_path(oracle, sums, functions, 0, n - 1);
        check_forest_path(oracle, sums, functions, n - 1, 0);
    }
    cout << "dynamic-forest-path-aggregate PASS: randomized BFS paths, directed affine composition, failed operations, cuts and rerooting\n";
}

struct TinyGrid {
    vector<vector<int>> adjacency;
    vector<pair<int, int>> edges;
};

TinyGrid tiny_grid(const vector<string>& grid) {
    int height = grid.size(), width = grid.empty() ? 0 : grid.front().size();
    vector<vector<int>> index(height, vector<int>(width, -1));
    int n = 0;
    for (int r = 0; r < height; ++r) for (int c = 0; c < width; ++c)
        if (grid[r][c] == '.') index[r][c] = n++;
    TinyGrid result;
    result.adjacency.resize(n);
    for (int r = 0; r < height; ++r) for (int c = 0; c < width; ++c) {
        int u = index[r][c];
        if (u == -1) continue;
        for (auto [dr, dc] : {pair{0, 1}, pair{1, 0}}) {
            int rr = r + dr, cc = c + dc;
            if (rr >= height || cc >= width || index[rr][cc] == -1) continue;
            int v = index[rr][cc];
            result.adjacency[u].push_back(v);
            result.adjacency[v].push_back(u);
            result.edges.emplace_back(u, v);
        }
    }
    return result;
}

// Entire edge sets are enumerated, rather than sweeping cells or maintaining
// frontier labels. Every selected vertex must have degree two AND be connected.
long long edge_subset_cycles(const vector<string>& grid) {
    auto [adjacency, edges] = tiny_grid(grid);
    int n = adjacency.size(), m = edges.size();
    assert(n <= 9 && m <= 12);
    if (n < 4) return 0;
    long long count = 0;
    for (unsigned mask = 0; mask < (1U << m); ++mask) {
        if (__builtin_popcount(mask) != n) continue;
        vector<int> degrees(n), parent(n);
        iota(parent.begin(), parent.end(), 0);
        auto find = [&](auto&& self, int u) -> int {
            return parent[u] == u ? u : parent[u] = self(self, parent[u]);
        };
        for (int edge = 0; edge < m; ++edge) if ((mask >> edge) & 1U) {
            auto [u, v] = edges[edge];
            ++degrees[u];
            ++degrees[v];
            parent[find(find, u)] = find(find, v);
        }
        if (any_of(degrees.begin(), degrees.end(), [](int degree) { return degree != 2; })) continue;
        bool connected = true;
        for (int u = 0; u < n; ++u) connected &= find(find, u) == find(find, 0);
        count += connected;
    }
    return count;
}

// A second oracle enumerates vertex orders starting at a fixed vertex. Each
// undirected cycle is seen twice, once in each orientation. There is no state
// packing, normalization, row shift, or plug merging shared with the article.
long long vertex_order_cycles(const vector<string>& grid) {
    auto tiny = tiny_grid(grid);
    auto& adjacency = tiny.adjacency;
    int n = adjacency.size();
    assert(n <= 20);
    if (n < 4 || n % 2) return 0;
    for (const auto& neighbors : adjacency) if (neighbors.size() < 2) return 0;
    auto dfs = [&](auto&& self, int u, unsigned visited) -> long long {
        if (__builtin_popcount(visited) == n)
            return find(adjacency[u].begin(), adjacency[u].end(), 0) != adjacency[u].end();
        long long count = 0;
        for (int v : adjacency[u]) if (!((visited >> v) & 1U))
            count += self(self, v, visited | (1U << v));
        return count;
    };
    long long directed = dfs(dfs, 0, 1);
    assert(directed % 2 == 0);
    return directed / 2;
}

vector<string> transpose(const vector<string>& grid) {
    if (grid.empty()) return {};
    vector<string> result(grid.front().size(), string(grid.size(), '*'));
    for (size_t r = 0; r < grid.size(); ++r) for (size_t c = 0; c < grid[r].size(); ++c)
        result[c][r] = grid[r][c];
    return result;
}

void check_frontier(mt19937& rng) {
    auto check = [&](const vector<string>& grid, long long expected) {
        auto before = grid;
        assert(count_grid_hamiltonian_cycles(grid) == expected);
        assert(grid == before);
        assert(count_grid_hamiltonian_cycles(transpose(grid)) == expected);
    };
    check({}, 0);
    check({"", ""}, 0);
    check({"*"}, 0);
    check({"."}, 0);
    check({".."}, 0);
    check({"...."}, 0);
    check({"..", ".."}, 1);
    check({"...", "..."}, 1);
    check({"....", "...."}, 1);
    check({"...", "...", "..."}, 0);
    check({"....", "....", "....", "...."}, 6);
    // These contain disjoint cycles or a bridge between cycle-bearing pieces.
    // Counting degree-two covers or accepting the first closed plug gives a
    // false positive; all usable vertices must be on a single cycle.
    check({"..*..", "..*.."}, 0);
    check({"..**..", "......"}, 0);
    check({"..***", "..***", "*****"}, 1);
    check({"****", "*..*", "*..*", "****"}, 1);
    check({"....", ".**.", ".**.", "...."}, 1);

    // Exhaust every obstacle pattern for every grid through 3x3 and compare
    // two independent brute-force definitions with the published plug DP.
    for (int height = 1; height <= 3; ++height) for (int width = 1; width <= 3; ++width) {
        int cells = height * width;
        for (unsigned mask = 0; mask < (1U << cells); ++mask) {
            vector<string> grid(height, string(width, '*'));
            for (int cell = 0; cell < cells; ++cell) if ((mask >> cell) & 1U)
                grid[cell / width][cell % width] = '.';
            long long expected = edge_subset_cycles(grid);
            assert(vertex_order_cycles(grid) == expected);
            check(grid, expected);
        }
    }
    for (auto [height, width] : {pair{3, 4}, pair{4, 4}, pair{3, 5}, pair{4, 5}}) {
        for (int trial = 0; trial < 180; ++trial) {
            vector<string> grid(height, string(width, '.'));
            int blocked_percent = trial % 3 == 0 ? 10 : trial % 3 == 1 ? 25 : 45;
            for (auto& row : grid) for (char& cell : row)
                if (int(rng() % 100) < blocked_percent) cell = '*';
            check(grid, vertex_order_cycles(grid));
        }
    }

    // At the supported width boundary, plugs reach the high packed positions.
    // The last usable cell need not be the last cell of the enclosing grid.
    for (auto [height, width] : {pair{12, 12}, pair{12, 13}, pair{13, 12}}) {
        for (bool far_corner : {false, true}) {
            vector<string> grid(height, string(width, '*'));
            int r = far_corner ? height - 3 : 0;
            int c = width - 2;
            for (int dr = 0; dr < 2; ++dr) for (int dc = 0; dc < 2; ++dc) grid[r + dr][c + dc] = '.';
            check(grid, 1);
        }
        vector<string> ring(height, string(width, '*'));
        for (int r = 0; r < height; ++r) for (int c = 0; c < width; ++c)
            if (r == 0 || c == 0 || r + 1 == height || c + 1 == width) ring[r][c] = '.';
        check(ring, 1);
    }

    // Each 4x4 board has six cycles, all containing its top-left horizontal
    // edge and bottom-left horizontal edge. Stack thirty boards and join their
    // cycles by replacing each neighboring pair of those edges with two
    // vertical edges. This injects 6^30 distinct cycles into the 120x4 grid,
    // proving that its count exceeds 64 bits without reimplementing a DP.
    cpp_int lower_bound = 1;
    for (int block = 0; block < 30; ++block) lower_bound *= 6;
    vector<string> tall(120, string(4, '.'));
    auto large = count_grid_hamiltonian_cycles(tall);
    assert(lower_bound > (cpp_int(1) << 64));
    assert(large >= lower_bound);
    assert(count_grid_hamiltonian_cycles(transpose(tall)) == large);

    for (const vector<string>& invalid : {
            vector<string>{"..", "."}, vector<string>{"", "."},
            vector<string>{".?"}, vector<string>(13, string(13, '*'))}) {
        bool rejected = false;
        try { (void)count_grid_hamiltonian_cycles(invalid); }
        catch (const invalid_argument&) { rejected = true; }
        assert(rejected);
    }
    cout << "frontier-single-cycle PASS: exhaustive edge subsets, vertex-order cycles, premature closures, packing limits and exact counts beyond 64 bits\n";
}

int main() {
    mt19937 rng(20261016);
    check_forest(rng);
    check_frontier(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-forest-frontier-cpp-") as directory:
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
        result = subprocess.run([str(executable)], cwd=directory, timeout=90)
        if result.returncode:
            return result.returncode
        print("All 2 forest and frontier implementations passed independent comparisons and contract checks.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
