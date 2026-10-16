#!/usr/bin/env python3
"""Compare six published tree, ordering and construction snippets independently."""

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
    "tree-root-path-lis-rollback",
    "tree-increasing-label-reroot-ratio",
    "mex-sort-fix-positions",
    "permutation-square-root-cycle-pairing",
    "functional-cycle-minimum-order-cost",
    "bipartite-component-edge-addition-count",
)


def extracted_source():
    """Use the actual complete article fences, with separate C++ namespaces."""
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
#include <algorithm>
#include <cassert>
#include <climits>
#include <functional>
#include <iostream>
#include <limits>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>
using namespace std;

using article_tree_root_path_lis_rollback::root_path_lis;
using article_tree_increasing_label_reroot_ratio::increasing_tree_label_counts;
using article_mex_sort_fix_positions::mex_sort_operations;
using article_permutation_square_root_cycle_pairing::permutation_square_root;
using article_functional_cycle_minimum_order_cost::minimize_functional_order_cost;
using article_bipartite_component_edge_addition_count::count_bipartite_edge_additions;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

vector<pair<int, int>> prufer_tree(int n, long long code) {
    if (n == 1) return {};
    vector<int> word(max(0, n - 2)), degree(n, 1);
    for (int& value : word) {
        value = int(code % n);
        code /= n;
        ++degree[value];
    }
    vector<pair<int, int>> edges;
    for (int value : word) {
        int leaf = 0;
        while (degree[leaf] != 1) ++leaf;
        edges.emplace_back(leaf, value);
        --degree[leaf];
        --degree[value];
    }
    int first = -1, second = -1;
    for (int v = 0; v < n; ++v) if (degree[v] == 1) {
        if (first == -1) first = v;
        else second = v;
    }
    edges.emplace_back(first, second);
    return edges;
}

vector<int> rooted_parents(int n, const vector<pair<int, int>>& edges, int root) {
    vector<vector<int>> adjacency(n);
    for (auto [u, v] : edges) {
        adjacency[u].push_back(v);
        adjacency[v].push_back(u);
    }
    vector<int> parent(n, -2);
    queue<int> pending;
    parent[root] = -1;
    pending.push(root);
    while (!pending.empty()) {
        int v = pending.front();
        pending.pop();
        for (int to : adjacency[v]) if (parent[to] == -2) {
            parent[to] = v;
            pending.push(to);
        }
    }
    return parent;
}

void check_path_lis_case(const vector<long long>& values,
                         const vector<pair<int, int>>& edges, int root) {
    const int n = int(values.size());
    const auto parent = rooted_parents(n, edges, root);
    vector<int> expected(n);
    for (int vertex = 0; vertex < n; ++vertex) {
        vector<long long> path;
        for (int v = vertex; v != -1; v = parent[v]) path.push_back(values[v]);
        reverse(path.begin(), path.end());
        // Enumerate subsets of the actual path; there is no tails array or
        // tree rollback in this oracle.
        for (unsigned mask = 0; mask < (1U << path.size()); ++mask) {
            bool increasing = true, seen = false;
            long long last = 0;
            int length = 0;
            for (size_t i = 0; i < path.size(); ++i) if ((mask >> i) & 1U) {
                if (seen && last >= path[i]) increasing = false;
                last = path[i];
                seen = true;
                ++length;
            }
            if (increasing) expected[vertex] = max(expected[vertex], length);
        }
    }
    assert(root_path_lis(values, edges, root) == expected);
}

void check_path_lis(mt19937& rng) {
    for (int n = 1; n <= 5; ++n) {
        long long trees = 1;
        for (int i = 0; i < n - 2; ++i) trees *= n;
        int patterns = 1;
        const int alphabet = n <= 4 ? 3 : 2;
        for (int i = 0; i < n; ++i) patterns *= alphabet;
        for (long long tree = 0; tree < trees; ++tree) {
            const auto edges = prufer_tree(n, tree);
            for (int pattern = 0; pattern < patterns; ++pattern) {
                int code = pattern;
                vector<long long> values(n);
                for (auto& value : values) {
                    value = code % alphabet - 1;
                    code /= alphabet;
                }
                for (int root = 0; root < n; ++root)
                    check_path_lis_case(values, edges, root);
            }
        }
    }
    for (int trial = 0; trial < 500; ++trial) {
        int n = 1 + rng() % 12;
        vector<pair<int, int>> edges;
        vector<int> relabel(n);
        iota(relabel.begin(), relabel.end(), 0);
        shuffle(relabel.begin(), relabel.end(), rng);
        for (int v = 1; v < n; ++v) edges.emplace_back(relabel[v], relabel[rng() % v]);
        shuffle(edges.begin(), edges.end(), rng);
        vector<long long> values(n);
        for (auto& value : values) value = int(rng() % 11) - 5;
        if (trial % 7 == 0) values[rng() % n] = numeric_limits<long long>::min();
        if (trial % 11 == 0) values[rng() % n] = numeric_limits<long long>::max();
        check_path_lis_case(values, edges, rng() % n);
    }
    const int n = 200000;
    vector<long long> ascending(n);
    vector<pair<int, int>> chain, star;
    for (int v = 0; v < n; ++v) {
        ascending[v] = v;
        if (v) {
            chain.emplace_back(v - 1, v);
            star.emplace_back(0, v);
        }
    }
    auto lengths = root_path_lis(ascending, chain);
    for (int v = 0; v < n; ++v) assert(lengths[v] == v + 1);
    lengths = root_path_lis(ascending, chain, n - 1);
    for (int length : lengths) assert(length == 1);
    lengths = root_path_lis(vector<long long>(n, LLONG_MIN), star);
    for (int length : lengths) assert(length == 1);
    require_exception<invalid_argument>([] { (void)root_path_lis({}, {}); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1}, {}, -1); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1}, {}, 1); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1, 2}, {}); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1, 2}, {{0, 0}}); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1, 2}, {{0, 2}}); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1, 2, 3}, {{0, 1}, {1, 0}}); });
    require_exception<invalid_argument>([] { (void)root_path_lis({1, 2, 3, 4}, {{0, 1}, {1, 2}, {2, 0}}); });
    cout << "tree-root-path-lis-rollback PASS: all small labelled trees and value assignments, path-subset enumeration, duplicates, extreme values and 200000-vertex paths\n";
}

vector<long long> brute_label_counts(int n, const vector<pair<int, int>>& edges) {
    vector<vector<int>> parents;
    for (int root = 0; root < n; ++root) parents.push_back(rooted_parents(n, edges, root));
    vector<long long> result(n);
    vector<int> labels(n);
    iota(labels.begin(), labels.end(), 0);
    do {
        for (int root = 0; root < n; ++root) {
            bool valid = true;
            for (int v = 0; v < n; ++v)
                if (parents[root][v] != -1 && labels[parents[root][v]] >= labels[v]) valid = false;
            result[root] += valid;
        }
    } while (next_permutation(labels.begin(), labels.end()));
    return result;
}

long long mod_power(long long value, int exponent) {
    constexpr long long mod = 1000000007;
    long long result = 1;
    for (; exponent; exponent >>= 1, value = value * value % mod)
        if (exponent & 1) result = result * value % mod;
    return result;
}

void check_tree_labels(mt19937& rng) {
    for (int n = 1; n <= 5; ++n) {
        long long trees = 1;
        for (int i = 0; i < n - 2; ++i) trees *= n;
        for (long long tree = 0; tree < trees; ++tree) {
            const auto edges = prufer_tree(n, tree);
            assert(increasing_tree_label_counts(n, edges) == brute_label_counts(n, edges));
        }
    }
    for (int trial = 0; trial < 60; ++trial) {
        int n = 6 + int(rng() % 3);
        vector<pair<int, int>> edges;
        for (int v = 1; v < n; ++v) edges.emplace_back(v, rng() % v);
        shuffle(edges.begin(), edges.end(), rng);
        assert(increasing_tree_label_counts(n, edges) == brute_label_counts(n, edges));
    }
    constexpr long long mod = 1000000007;
    const int n = 200000;
    vector<pair<int, int>> chain, star;
    for (int v = 1; v < n; ++v) {
        chain.emplace_back(v - 1, v);
        star.emplace_back(0, v);
    }
    vector<long long> factorial(n, 1), inverse_factorial(n, 1);
    for (int i = 1; i < n; ++i) factorial[i] = factorial[i - 1] * i % mod;
    inverse_factorial[n - 1] = mod_power(factorial[n - 1], mod - 2);
    for (int i = n - 1; i > 0; --i) inverse_factorial[i - 1] = inverse_factorial[i] * i % mod;
    // On a path, a root fixes two chains. A valid labelling is exactly an
    // interleaving of these chains, hence a binomial coefficient.
    auto counts = increasing_tree_label_counts(n, chain);
    for (int root = 0; root < n; ++root) {
        long long expected = factorial[n - 1] * inverse_factorial[root] % mod
                             * inverse_factorial[n - 1 - root] % mod;
        assert(counts[root] == expected);
    }
    counts = increasing_tree_label_counts(n, star);
    assert(counts[0] == factorial[n - 1]);
    for (int root = 1; root < n; ++root) assert(counts[root] == factorial[n - 2]);
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(0, {}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(-1, {}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(1000000007, {}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(2, {}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(2, {{0, 2}}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(2, {{0, 0}}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(3, {{0, 1}, {1, 0}}); });
    require_exception<invalid_argument>([] { (void)increasing_tree_label_counts(4, {{0, 1}, {1, 2}, {2, 0}}); });
    cout << "tree-increasing-label-reroot-ratio PASS: explicit permutations for every root, all small labelled trees, and binomial/factorial checks on 200000-vertex trees\n";
}

void check_mex_case(const vector<int>& initial, bool large = false) {
    const auto before = initial;
    auto operations = mex_sort_operations(initial);
    assert(initial == before);
    const int n = int(initial.size());
    assert(operations.size() <= 2ULL * n);
    vector<int> values = initial;
    if (!large) {
        for (int index : operations) {
            assert(0 <= index && index < n);
            vector<bool> present(n + 1);
            for (int value : values) present[value] = true;
            int mex = 0;
            while (present[mex]) ++mex;
            values[index] = mex;
        }
    } else {
        vector<int> frequency(n + 1);
        for (int value : values) ++frequency[value];
        set<int> missing;
        for (int value = 0; value <= n; ++value) if (!frequency[value]) missing.insert(value);
        for (int index : operations) {
            assert(0 <= index && index < n && !missing.empty());
            int replacement = *missing.begin();
            if (--frequency[values[index]] == 0) missing.insert(values[index]);
            values[index] = replacement;
            if (++frequency[replacement] == 1) missing.erase(replacement);
        }
    }
    for (int i = 0; i < n; ++i) assert(values[i] == i);
}

void check_mex(mt19937& rng) {
    for (int n = 0; n <= 6; ++n) {
        int arrays = 1;
        for (int i = 0; i < n; ++i) arrays *= n + 1;
        for (int code = 0; code < arrays; ++code) {
            int encoded = code;
            vector<int> values(n);
            for (int& value : values) {
                value = encoded % (n + 1);
                encoded /= n + 1;
            }
            check_mex_case(values);
        }
    }
    for (int trial = 0; trial < 1000; ++trial) {
        int n = rng() % 70;
        vector<int> values(n);
        for (int& value : values) value = rng() % (n + 1);
        check_mex_case(values);
    }
    const int n = 200000;
    check_mex_case(vector<int>(n, n), true);
    vector<int> reversed(n), rotated(n);
    for (int i = 0; i < n; ++i) {
        reversed[i] = n - 1 - i;
        rotated[i] = (i + 1) % n;
    }
    check_mex_case(reversed, true);
    check_mex_case(rotated, true);
    reverse(reversed.begin(), reversed.end());
    assert(mex_sort_operations(reversed).empty());
    require_exception<invalid_argument>([] { (void)mex_sort_operations({-1}); });
    require_exception<invalid_argument>([] { (void)mex_sort_operations({2}); });
    require_exception<invalid_argument>([] { (void)mex_sort_operations({0, 3}); });
    cout << "mex-sort-fix-positions PASS: every array through length six, naive mex replay, operation bound, and 200000-element constructions\n";
}

void check_square_witness(const vector<int>& permutation,
                          const optional<vector<int>>& square_root) {
    assert(square_root);
    const int n = int(permutation.size());
    assert(square_root->size() == permutation.size());
    vector<int> frequency(n);
    for (int value : *square_root) {
        assert(0 <= value && value < n);
        ++frequency[value];
    }
    for (int count : frequency) assert(count == 1);
    for (int i = 0; i < n; ++i) assert((*square_root)[(*square_root)[i]] == permutation[i]);
}

void check_square_roots(mt19937& rng) {
    for (int n = 0; n <= 8; ++n) {
        vector<int> permutation(n);
        iota(permutation.begin(), permutation.end(), 0);
        set<vector<int>> all_squares;
        // Enumerating q and recording q composed with q gives an independent
        // existence oracle. It makes no odd/even cycle classification.
        do {
            vector<int> square(n);
            for (int i = 0; i < n; ++i) square[i] = permutation[permutation[i]];
            all_squares.insert(move(square));
        } while (next_permutation(permutation.begin(), permutation.end()));
        do {
            const auto before = permutation;
            auto actual = permutation_square_root(permutation);
            assert(permutation == before);
            assert(bool(actual) == bool(all_squares.count(permutation)));
            if (actual) check_square_witness(permutation, actual);
        } while (next_permutation(permutation.begin(), permutation.end()));
    }
    for (int trial = 0; trial < 700; ++trial) {
        int n = 1 + rng() % 500;
        vector<int> root(n), square(n);
        iota(root.begin(), root.end(), 0);
        shuffle(root.begin(), root.end(), rng);
        for (int i = 0; i < n; ++i) square[i] = root[root[i]];
        check_square_witness(square, permutation_square_root(square));
    }
    const int n = 200000;
    vector<int> single_even(n), paired_even(n), single_odd(n - 1);
    for (int i = 0; i < n; ++i) single_even[i] = (i + 1) % n;
    assert(!permutation_square_root(single_even));
    for (int i = 0; i < n; ++i)
        paired_even[i] = i < n / 2 ? (i + 1) % (n / 2) : n / 2 + (i + 1 - n / 2) % (n / 2);
    check_square_witness(paired_even, permutation_square_root(paired_even));
    for (int i = 0; i < n - 1; ++i) single_odd[i] = (i + 1) % (n - 1);
    check_square_witness(single_odd, permutation_square_root(single_odd));
    require_exception<invalid_argument>([] { (void)permutation_square_root({1}); });
    require_exception<invalid_argument>([] { (void)permutation_square_root({-1}); });
    require_exception<invalid_argument>([] { (void)permutation_square_root({0, 0}); });
    require_exception<invalid_argument>([] { (void)permutation_square_root({1, 2}); });
    cout << "permutation-square-root-cycle-pairing PASS: exhaustive existence by composing every permutation through size eight, witness replay and long cycles\n";
}

__int128 order_cost(const vector<int>& successor, const vector<long long>& penalty,
                    const vector<int>& order) {
    const int n = int(successor.size());
    assert(order.size() == successor.size());
    vector<int> position(n, -1);
    for (int i = 0; i < n; ++i) {
        assert(0 <= order[i] && order[i] < n && position[order[i]] == -1);
        position[order[i]] = i;
    }
    __int128 cost = 0;
    for (int v = 0; v < n; ++v)
        if (position[successor[v]] < position[v]) cost += penalty[v];
    return cost;
}

void check_functional_case(const vector<int>& successor, const vector<long long>& penalty) {
    const auto before_successor = successor;
    const auto before_penalty = penalty;
    vector<int> order(successor.size());
    iota(order.begin(), order.end(), 0);
    optional<__int128> minimum;
    // Directly enumerate the invitation orders, including self-loops under
    // the API's strict-earlier contract. No functional-cycle decomposition
    // or choice of one edge per cycle is used in the oracle.
    do {
        __int128 cost = order_cost(successor, penalty, order);
        if (!minimum || cost < *minimum) minimum = cost;
    } while (next_permutation(order.begin(), order.end()));
    auto actual = minimize_functional_order_cost(successor, penalty);
    assert(actual.minimum_cost == *minimum);
    assert(order_cost(successor, penalty, actual.order) == *minimum);
    assert(successor == before_successor && penalty == before_penalty);
}

void check_functional(mt19937& rng) {
    check_functional_case({}, {});
    for (int n = 1; n <= 5; ++n) {
        int graphs = 1;
        for (int i = 0; i < n; ++i) graphs *= n;
        for (int graph = 0; graph < graphs; ++graph) {
            int encoded = graph;
            vector<int> successor(n);
            for (int& next : successor) {
                next = encoded % n;
                encoded /= n;
            }
            int cost_patterns = n <= 4 ? 1 << n : 1;
            for (int pattern = 0; pattern < cost_patterns; ++pattern) {
                vector<long long> penalty(n);
                for (int v = 0; v < n; ++v)
                    penalty[v] = n <= 4 ? (pattern >> v) & 1 : rng() % 11;
                check_functional_case(successor, penalty);
            }
        }
    }
    for (int trial = 0; trial < 100; ++trial) {
        int n = 6 + rng() % 3;
        vector<int> successor(n);
        vector<long long> penalty(n);
        for (int v = 0; v < n; ++v) {
            successor[v] = rng() % n;
            penalty[v] = trial % 13 == 0 ? LLONG_MAX : rng() % 101;
        }
        check_functional_case(successor, penalty);
    }
    const int n = 200000;
    vector<int> successor(n);
    vector<long long> penalty(n, LLONG_MAX);
    for (int v = 0; v < n; ++v) successor[v] = v ^ 1;
    auto actual = minimize_functional_order_cost(successor, penalty);
    const __int128 paired_cost = (__int128)(n / 2) * LLONG_MAX;
    assert(actual.minimum_cost == paired_cost);
    assert(order_cost(successor, penalty, actual.order) == paired_cost);
    for (int v = 0; v < n; ++v) successor[v] = min(v + 1, n - 1);
    actual = minimize_functional_order_cost(successor, penalty);
    assert(actual.minimum_cost == 0 && order_cost(successor, penalty, actual.order) == 0);
    for (int v = 0; v < n; ++v) successor[v] = (v + 1) % n;
    penalty[n / 3] = 7;
    actual = minimize_functional_order_cost(successor, penalty);
    assert(actual.minimum_cost == 7 && order_cost(successor, penalty, actual.order) == 7);
    iota(successor.begin(), successor.end(), 0);
    actual = minimize_functional_order_cost(successor, penalty);
    assert(actual.minimum_cost == 0 && order_cost(successor, penalty, actual.order) == 0);
    require_exception<invalid_argument>([] { (void)minimize_functional_order_cost({0}, {}); });
    require_exception<invalid_argument>([] { (void)minimize_functional_order_cost({0}, {-1}); });
    require_exception<out_of_range>([] { (void)minimize_functional_order_cost({-1}, {1}); });
    require_exception<out_of_range>([] { (void)minimize_functional_order_cost({1}, {1}); });
    cout << "functional-cycle-minimum-order-cost PASS: all small functional graphs, every ordering, strict self-loop handling, reconstructed witnesses and costs beyond signed 64 bits\n";
}

bool explicitly_bipartite(int n, const vector<pair<int, int>>& edges) {
    vector<vector<int>> adjacency(n);
    for (auto [u, v] : edges) {
        adjacency[u].push_back(v);
        adjacency[v].push_back(u);
    }
    vector<int> color(n, -1);
    for (int root = 0; root < n; ++root) if (color[root] == -1) {
        queue<int> pending;
        color[root] = 0;
        pending.push(root);
        while (!pending.empty()) {
            int v = pending.front();
            pending.pop();
            for (int to : adjacency[v]) {
                if (color[to] == color[v]) return false;
                if (color[to] == -1) {
                    color[to] = color[v] ^ 1;
                    pending.push(to);
                }
            }
        }
    }
    return true;
}

void check_bipartite_case(int n, const vector<pair<int, int>>& edges) {
    const auto before = edges;
    vector<vector<bool>> present(n, vector<bool>(n));
    for (auto [u, v] : edges) present[u][v] = present[v][u] = true;
    long long expected = 0;
    auto augmented = edges;
    // Try every missing edge and recolor the augmented graph from scratch.
    // In particular, distinct components choose their colors independently.
    for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) if (!present[u][v]) {
        augmented.emplace_back(u, v);
        expected += explicitly_bipartite(n, augmented);
        augmented.pop_back();
    }
    assert(count_bipartite_edge_additions(n, edges) == expected);
    assert(edges == before);
}

void check_bipartite(mt19937& rng) {
    for (int n = 0; n <= 6; ++n) {
        vector<pair<int, int>> possible;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) possible.emplace_back(u, v);
        for (unsigned mask = 0; mask < (1U << possible.size()); ++mask) {
            vector<pair<int, int>> edges;
            for (size_t i = 0; i < possible.size(); ++i)
                if ((mask >> i) & 1U) edges.push_back(possible[i]);
            check_bipartite_case(n, edges);
        }
    }
    for (int trial = 0; trial < 400; ++trial) {
        int n = rng() % 25;
        vector<pair<int, int>> edges;
        bool force_bipartite = trial % 2 == 0;
        vector<int> color(n);
        for (int& value : color) value = rng() & 1U;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v)
            if (rng() % 7 == 0 && (!force_bipartite || color[u] != color[v])) edges.emplace_back(u, v);
        shuffle(edges.begin(), edges.end(), rng);
        check_bipartite_case(n, edges);
    }
    const int n = 200000;
    assert(count_bipartite_edge_additions(n, {}) == (long long)n * (n - 1) / 2);
    vector<pair<int, int>> chain, star, matching;
    for (int v = 1; v < n; ++v) {
        chain.emplace_back(v - 1, v);
        star.emplace_back(0, v);
        if (v & 1) matching.emplace_back(v - 1, v);
    }
    assert(count_bipartite_edge_additions(n, chain) == (long long)(n / 2) * (n / 2) - (n - 1));
    assert(count_bipartite_edge_additions(n, star) == 0);
    assert(count_bipartite_edge_additions(n, matching) == (long long)n * (n - 1) / 2 - n / 2);
    assert(count_bipartite_edge_additions(n, {{0, 1}, {1, 2}, {2, 0}}) == 0);
    require_exception<invalid_argument>([] { (void)count_bipartite_edge_additions(-1, {}); });
    require_exception<invalid_argument>([] { (void)count_bipartite_edge_additions(200001, {}); });
    require_exception<invalid_argument>([] { (void)count_bipartite_edge_additions(2, {{0, 0}}); });
    require_exception<out_of_range>([] { (void)count_bipartite_edge_additions(2, {{0, 2}}); });
    require_exception<out_of_range>([] { (void)count_bipartite_edge_additions(0, {{0, 0}}); });
    require_exception<out_of_range>([] { (void)count_bipartite_edge_additions(2, {{-1, 1}}); });
    cout << "bipartite-component-edge-addition-count PASS: every simple graph through six vertices, explicit recoloring after each missing edge and disconnected large cases\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261022);
    check_path_lis(rng);
    check_tree_labels(rng);
    check_mex(rng);
    check_square_roots(rng);
    check_functional(rng);
    check_bipartite(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-tree-construction-cpp-") as directory:
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
        print("All 6 tree and construction implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
