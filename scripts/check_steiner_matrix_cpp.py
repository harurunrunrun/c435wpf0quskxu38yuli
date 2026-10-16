#!/usr/bin/env python3
"""Verify the published Steiner subset DP and Laplacian-minor examples."""

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
ARTICLES = ("steiner-terminal-subset-shortest", "spanning-tree-laplacian-minor")


def extracted_source():
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
        examples.append("namespace article_" + slug.replace("-", "_") + " {\n" + source + "\n}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <cassert>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <tuple>
#include <vector>
using namespace std;
using article_steiner_terminal_subset_shortest::minimum_steiner_tree_cost;
using article_spanning_tree_laplacian_minor::count_spanning_trees_mod;
constexpr long long MOD = 998244353;

struct DisjointSet {
    vector<int> parent;
    explicit DisjointSet(int n): parent(n) { iota(parent.begin(), parent.end(), 0); }
    int find(int v) { return parent[v] == v ? v : parent[v] = find(parent[v]); }
    bool join(int u, int v) {
        u = find(u); v = find(v);
        if (u == v) return false;
        parent[u] = v;
        return true;
    }
};

template<class Function>
void require_invalid(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const invalid_argument&) { rejected = true; }
    assert(rejected);
}

// Enumerate edge sets directly. No terminal-set DP or shortest paths are used.
vector<long long> brute_all_steiner_costs(int n, const vector<tuple<int,int,long long>>& edges) {
    vector<long long> best(1 << n, 1LL << 60);
    best[0] = 0;
    for (unsigned selected = 0; selected < (1U << edges.size()); ++selected) {
        DisjointSet components(n);
        long long cost = 0;
        for (int e = 0; e < int(edges.size()); ++e) if (selected >> e & 1U) {
            auto [u, v, w] = edges[e];
            components.join(u, v);
            cost += w;
        }
        vector<int> member_masks(n, 0);
        for (int v = 0; v < n; ++v) member_masks[components.find(v)] |= 1 << v;
        for (int component : member_masks) if (component) {
            for (int terminal_set = component; terminal_set; terminal_set = (terminal_set - 1) & component)
                best[terminal_set] = min(best[terminal_set], cost);
        }
    }
    for (long long& value : best) if (value == (1LL << 60)) value = -1;
    return best;
}

vector<int> terminals_from_mask(int n, int mask) {
    vector<int> terminals;
    for (int v = 0; v < n; ++v) if (mask >> v & 1) terminals.push_back(v);
    return terminals;
}

void check_steiner(mt19937& rng) {
    for (int n = 1; n <= 5; ++n) {
        vector<pair<int,int>> possible;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) possible.emplace_back(u, v);
        for (int graph_mask = 0; graph_mask < (1 << possible.size()); ++graph_mask) {
            vector<tuple<int,int,long long>> edges;
            for (int e = 0; e < int(possible.size()); ++e) if (graph_mask >> e & 1) {
                auto [u, v] = possible[e];
                long long weight = (e * 7 + graph_mask) % 4;
                edges.emplace_back(u, v, weight);
            }
            auto expected = brute_all_steiner_costs(n, edges);
            for (int mask = 0; mask < (1 << n); ++mask)
                assert(minimum_steiner_tree_cost(n, edges, terminals_from_mask(n, mask)) == expected[mask]);
        }
    }
    for (int trial = 0; trial < 350; ++trial) {
        int n = 1 + int(rng() % 7), m = int(rng() % 13);
        vector<tuple<int,int,long long>> edges;
        for (int e = 0; e < m; ++e)
            edges.emplace_back(rng() % n, rng() % n, rng() % 6);
        auto expected = brute_all_steiner_costs(n, edges);
        int mask = int(rng() % (1U << n));
        vector<int> terminals = terminals_from_mask(n, mask);
        if (!terminals.empty()) terminals.push_back(terminals.front());
        assert(minimum_steiner_tree_cost(n, edges, terminals) == expected[mask]);
    }
    assert(minimum_steiner_tree_cost(4, {{0,3,1},{1,3,1},{2,3,1}}, {0,1,2}) == 3);
    assert(minimum_steiner_tree_cost(4, {{0,1,0},{1,2,0},{2,3,0},{0,3,5}}, {0,2,3}) == 0);
    assert(minimum_steiner_tree_cost(3, {}, {}) == 0);
    assert(minimum_steiner_tree_cost(3, {}, {2,2,2}) == 0);
    assert(minimum_steiner_tree_cost(3, {{0,1,0}}, {0,2}) == -1);
    vector<tuple<int,int,long long>> maximum_edges;
    for (int v = 1; v < 200; ++v) maximum_edges.emplace_back(v - 1, v, 1000000000LL);
    while (maximum_edges.size() < 20000) {
        int u = int(maximum_edges.size() % 199);
        maximum_edges.emplace_back(u, u + 1, 1000000000LL);
    }
    assert(minimum_steiner_tree_cost(200, maximum_edges, {0,22,44,66,88,110,132,154,176,199}) == 199000000000LL);
    require_invalid([] { minimum_steiner_tree_cost(0, {}, {}); });
    require_invalid([] { minimum_steiner_tree_cost(201, {}, {}); });
    require_invalid([] { minimum_steiner_tree_cost(1, vector<tuple<int,int,long long>>(20001, {0,0,0}), {}); });
    require_invalid([] { minimum_steiner_tree_cost(1, {}, vector<int>(11,0)); });
    for (auto edge : vector<tuple<int,int,long long>>{{-1,0,0},{0,-1,0},{0,1,0},{1,0,0},{0,0,-1},{0,0,1000000001LL}})
        require_invalid([&] { minimum_steiner_tree_cost(1, {edge}, {}); });
    require_invalid([] { minimum_steiner_tree_cost(1, {}, {-1}); });
    require_invalid([] { minimum_steiner_tree_cost(1, {}, {1}); });
    cout << "steiner-terminal-subset-shortest PASS: every simple graph through 5 vertices and every terminal subset versus edge-set enumeration; random loops/parallel edges/duplicates; free edges, shared branch, disconnected cases, 10-terminal/200-vertex/20000-edge/64-bit boundaries and invalid input\n";
}

long long brute_spanning_trees(int n, const vector<pair<int,int>>& edges) {
    long long answer = 0;
    for (unsigned selected = 0; selected < (1U << edges.size()); ++selected) {
        if (__builtin_popcount(selected) != n - 1) continue;
        DisjointSet components(n);
        bool acyclic = true;
        for (int e = 0; e < int(edges.size()); ++e) if (selected >> e & 1U) {
            auto [u, v] = edges[e];
            if (!components.join(u, v)) { acyclic = false; break; }
        }
        if (acyclic) ++answer;
    }
    return answer;
}

// Enumerate edge *types* of multigraphs and multiply their multiplicities.
long long compressed_tree_count(int n, const vector<tuple<int,int,int>>& types) {
    long long answer = 0;
    for (unsigned selected = 0; selected < (1U << types.size()); ++selected) {
        if (__builtin_popcount(selected) != n - 1) continue;
        DisjointSet components(n);
        long long ways = 1;
        bool acyclic = true;
        for (int e = 0; e < int(types.size()); ++e) if (selected >> e & 1U) {
            auto [u, v, count] = types[e];
            if (!components.join(u, v)) { acyclic = false; break; }
            ways = ways * count % MOD;
        }
        if (acyclic) answer = (answer + ways) % MOD;
    }
    return answer;
}

vector<pair<int,int>> expand_types(const vector<tuple<int,int,int>>& types) {
    vector<pair<int,int>> edges;
    for (auto [u, v, count] : types) for (int i = 0; i < count; ++i) edges.emplace_back(u, v);
    return edges;
}

long long modular_power(long long base, int exponent) {
    long long result = 1;
    while (exponent--) result = result * base % MOD;
    return result;
}

void check_matrix_tree(mt19937& rng) {
    for (int n = 1; n <= 6; ++n) {
        vector<pair<int,int>> possible;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) possible.emplace_back(u, v);
        for (int graph_mask = 0; graph_mask < (1 << possible.size()); ++graph_mask) {
            vector<pair<int,int>> edges;
            for (int e = 0; e < int(possible.size()); ++e) if (graph_mask >> e & 1) edges.push_back(possible[e]);
            assert(count_spanning_trees_mod(n, edges) == brute_spanning_trees(n, edges));
        }
    }
    for (int trial = 0; trial < 500; ++trial) {
        int n = 1 + int(rng() % 7), m = int(rng() % 14);
        vector<pair<int,int>> edges;
        for (int e = 0; e < m; ++e) edges.emplace_back(rng() % n, rng() % n);
        assert(count_spanning_trees_mod(n, edges) == brute_spanning_trees(n, edges));
    }
    assert(count_spanning_trees_mod(1, {}) == 1);
    assert(count_spanning_trees_mod(1, {{0,0},{0,0}}) == 1);
    assert(count_spanning_trees_mod(200, {}) == 0);
    assert(count_spanning_trees_mod(2, vector<pair<int,int>>(20000, {0,1})) == 20000);

    // Connected graph with tree count 139 * MOD. A zero residue is not a disconnection test.
    vector<tuple<int,int,int>> zero_types = {{0,1,2124},{1,2,487},{2,0,895},{0,3,10356},{1,3,1142},{2,3,1831}};
    assert(compressed_tree_count(4, zero_types) == 0);
    assert(count_spanning_trees_mod(4, expand_types(zero_types)) == 0);
    // The leading 3x3 minor is zero modulo MOD, but a later row is a usable pivot.
    vector<tuple<int,int,int>> pivot_types = {{0,1,2124},{1,2,487},{2,0,895},{0,3,10356},{1,4,1142},{2,4,1831},{3,4,1}};
    assert(compressed_tree_count(5, pivot_types) == 37926081);
    assert(count_spanning_trees_mod(5, expand_types(pivot_types)) == compressed_tree_count(5, pivot_types));

    // Cayley's formula is independent of Laplacian elimination.
    vector<pair<int,int>> complete;
    for (int u = 0; u < 200; ++u) for (int v = u + 1; v < 200; ++v) complete.emplace_back(u, v);
    assert(complete.size() == 19900);
    assert(count_spanning_trees_mod(200, complete) == modular_power(200,198));
    vector<pair<int,int>> tree;
    for (int v = 1; v < 200; ++v) tree.emplace_back(v - 1, v);
    while (tree.size() < 20000) tree.emplace_back(199,199);
    assert(count_spanning_trees_mod(200, tree) == 1);
    require_invalid([] { count_spanning_trees_mod(0, {}); });
    require_invalid([] { count_spanning_trees_mod(201, {}); });
    require_invalid([] { count_spanning_trees_mod(1, vector<pair<int,int>>(20001, {0,0})); });
    for (auto edge : vector<pair<int,int>>{{-1,0},{0,-1},{1,0},{0,1}})
        require_invalid([&] { count_spanning_trees_mod(1, {edge}); });
    cout << "spanning-tree-laplacian-minor PASS: every simple graph through 6 vertices versus edge-set enumeration; random multigraphs and loops; exact multiplicity enumeration for zero residue and row-pivot exchange; Cayley K200, 20000-edge and invalid-input boundaries\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261015);
    check_steiner(rng);
    check_matrix_tree(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-steiner-matrix-cpp-") as directory:
        source = Path(directory) / "comparisons.cpp"
        executable = Path(directory) / "comparisons"
        source.write_text(extracted_source() + "\n" + TESTS, encoding="utf8")
        compiled = subprocess.run(
            [args.compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)],
            capture_output=True, text=True, timeout=120)
        if compiled.returncode:
            print(compiled.stderr, file=sys.stderr)
            return compiled.returncode
        result = subprocess.run([str(executable)], cwd=directory, timeout=240)
        if result.returncode:
            return result.returncode
        print("All 2 Steiner and Laplacian-minor implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
