#!/usr/bin/env python3
"""Check six published mask, boundary-DP and path implementations."""

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
    "disjoint-mask-subset-witness",
    "subset-and-zero-superset-inclusion",
    "color-exclusion-two-best-dp",
    "bracket-pair-color-boundaries",
    "exact-k-edge-minplus",
    "disk-passage-wall-bottleneck",
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
#include <array>
#include <cassert>
#include <climits>
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

using article_disjoint_mask_subset_witness::disjoint_mask_witness;
using article_subset_and_zero_superset_inclusion::count_nonempty_and_zero;
using article_color_exclusion_two_best_dp::maximum_colorful_subsequence_value;
using article_bracket_pair_color_boundaries::count_boundary_bracket_colorings;
using article_exact_k_edge_minplus::ExactStepEdge;
using article_exact_k_edge_minplus::minimum_cost_exact_edges;
using article_disk_passage_wall_bottleneck::maximum_disk_passage_radius;

constexpr long long MOD = 1000000007;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

long long modular_power(long long value, int power) {
    long long result = 1;
    for (; power; power >>= 1, value = value * value % MOD)
        if (power & 1) result = result * value % MOD;
    return result;
}

void literal_witness_case(const vector<int>& values, int bits) {
    const auto before = values;
    const auto actual = disjoint_mask_witness(values, bits);
    assert(values == before && actual.size() == values.size());
    set<int> present(values.begin(), values.end());
    for (size_t i = 0; i < values.size(); ++i) {
        bool possible = false;
        for (int value : values) possible |= ((values[i] & value) == 0);
        assert((actual[i] != -1) == possible);
        if (actual[i] != -1)
            assert(present.count(actual[i]) && (values[i] & actual[i]) == 0);
    }
}

void check_disjoint_witness(mt19937& rng) {
    for (int bits = 0; bits <= 3; ++bits) {
        const int alphabet = 1 << bits;
        const int max_length = bits == 3 ? 5 : 7;
        for (int n = 0; n <= max_length; ++n) {
            int patterns = 1;
            for (int i = 0; i < n; ++i) patterns *= alphabet;
            for (int pattern = 0; pattern < patterns; ++pattern) {
                int code = pattern;
                vector<int> values(n);
                for (int& value : values) { value = code % alphabet; code /= alphabet; }
                literal_witness_case(values, bits);
            }
        }
    }
    for (int trial = 0; trial < 700; ++trial) {
        const int bits = 1 + rng() % 12;
        vector<int> values(rng() % 40);
        for (int& value : values) value = rng() % (1 << bits);
        literal_witness_case(values, bits);
    }
    assert(disjoint_mask_witness({0}, 0) == vector<int>{0});
    assert(disjoint_mask_witness({7}, 3) == vector<int>{-1});
    assert(disjoint_mask_witness({7, 7}, 3) == (vector<int>{-1, -1}));
    const int all = (1 << 22) - 1;
    vector<int> large(1000000, all);
    large.front() = 0;
    for (int bit = 0; bit < 22; ++bit) large[bit + 1] = 1 << bit;
    const auto result = disjoint_mask_witness(large, 22);
    set<int> present(large.begin(), large.end());
    assert(result.size() == large.size());
    for (size_t i = 0; i < large.size(); ++i)
        assert(present.count(result[i]) && (result[i] & large[i]) == 0);
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness({}, -1); });
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness({}, 23); });
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness({-1}, 3); });
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness({8}, 3); });
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness({1}, 0); });
    require_exception<invalid_argument>([] { (void)disjoint_mask_witness(vector<int>(1000001), 0); });
    cout << "disjoint-mask-subset-witness PASS: direct witness scans for all small arrays, duplicate/index semantics, zero-bit universe and maximum mask/input boundaries\n";
}

int literal_and_subsets(const vector<int>& values, int bits) {
    int answer = 0;
    for (int subset = 1; subset < (1 << values.size()); ++subset) {
        int value = (1 << bits) - 1;
        for (int i = 0; i < (int)values.size(); ++i)
            if (subset >> i & 1) value &= values[i];
        answer += value == 0;
    }
    return answer;
}

void check_and_zero(mt19937& rng) {
    for (int bits = 0; bits <= 3; ++bits) {
        const int alphabet = 1 << bits;
        const int max_length = bits == 3 ? 5 : 7;
        for (int n = 0; n <= max_length; ++n) {
            int patterns = 1;
            for (int i = 0; i < n; ++i) patterns *= alphabet;
            for (int pattern = 0; pattern < patterns; ++pattern) {
                int code = pattern;
                vector<int> values(n);
                for (int& value : values) { value = code % alphabet; code /= alphabet; }
                const auto before = values;
                assert(count_nonempty_and_zero(values, bits) == literal_and_subsets(values, bits));
                assert(values == before);
            }
        }
    }
    for (int trial = 0; trial < 300; ++trial) {
        const int bits = 1 + rng() % 12;
        vector<int> values(rng() % 15);
        for (int& value : values) value = rng() % (1 << bits);
        assert(count_nonempty_and_zero(values, bits) == literal_and_subsets(values, bits));
    }
    assert(count_nonempty_and_zero({1, 1}, 1) == 0);
    assert(count_nonempty_and_zero({0, 0}, 1) == 3);
    assert(count_nonempty_and_zero({1, 2, 3}, 2) == 2);
    assert(count_nonempty_and_zero(vector<int>(1000000, 0), 20)
           == (modular_power(2, 1000000) + MOD - 1) % MOD);
    assert(count_nonempty_and_zero(vector<int>(1000000, (1 << 20) - 1), 20) == 0);
    // A disjoint pair of nonzero masks must contribute at least one copy
    // of each value, with indexed duplicates chosen independently.
    vector<int> split(1000000, (1 << 10) - 1);
    fill(split.begin() + 500000, split.end(), ((1 << 20) - 1) ^ ((1 << 10) - 1));
    const long long nonempty_half = (modular_power(2, 500000) + MOD - 1) % MOD;
    assert(count_nonempty_and_zero(split, 20) == nonempty_half * nonempty_half % MOD);
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero({}, -1); });
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero({}, 21); });
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero({-1}, 3); });
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero({8}, 3); });
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero({1}, 0); });
    require_exception<invalid_argument>([] { (void)count_nonempty_and_zero(vector<int>(1000001), 0); });
    cout << "subset-and-zero-superset-inclusion PASS: every nonempty indexed subset of small arrays, zero-bit/empty correction and independent large duplicate-group counts\n";
}

vector<optional<long long>> literal_colorful_choices(const vector<int>& colors,
                                                   const vector<long long>& values) {
    const int n = colors.size();
    vector<optional<long long>> answer(n + 1);
    for (int subset = 0; subset < (1 << n); ++subset) {
        long long value = 0;
        int kept = 0, last = -1;
        bool valid = true;
        for (int i = 0; i < n; ++i) if (subset >> i & 1) {
            if (last == colors[i]) valid = false;
            last = colors[i];
            value += values[i];
            ++kept;
        }
        if (valid && (!answer[n - kept] || value > *answer[n - kept]))
            answer[n - kept] = value;
    }
    return answer;
}

void check_colorful_case(const vector<int>& colors, const vector<long long>& values) {
    const auto expected = literal_colorful_choices(colors, values);
    const auto before_colors = colors;
    const auto before_values = values;
    for (int deletions = 0; deletions <= (int)colors.size(); ++deletions)
        assert(maximum_colorful_subsequence_value(colors, values, deletions)
               == expected[deletions]);
    assert(colors == before_colors && values == before_values);
}

void check_colorful_dp(mt19937& rng) {
    constexpr array<long long, 3> weight = {-3, 0, 5};
    for (int n = 0; n <= 5; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= 9;
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<int> colors(n);
            vector<long long> values(n);
            for (int i = 0; i < n; ++i) {
                colors[i] = code % 3;
                code /= 3;
                values[i] = weight[code % 3];
                code /= 3;
            }
            check_colorful_case(colors, values);
        }
    }
    for (int trial = 0; trial < 500; ++trial) {
        const int n = rng() % 14;
        vector<int> colors(n);
        vector<long long> values(n);
        for (int i = 0; i < n; ++i) {
            colors[i] = rng() % 5 == 0 ? INT_MAX : int(rng() % 4);
            values[i] = (long long)(rng() % 2000000001U) - 1000000000LL;
        }
        check_colorful_case(colors, values);
    }
    check_colorful_case({1, 1, 2, 1, 2}, {100, 99, -5, 2, 3});
    check_colorful_case({0, 0, INT_MAX, 0}, {-1000000000LL, 1000000000LL, -1, -2});
    const int n = 200000;
    vector<int> colors(n);
    vector<long long> values(n, 1000000000LL);
    for (int i = 0; i < n; ++i) colors[i] = i % 2;
    assert(maximum_colorful_subsequence_value(colors, values, 0)
           == optional<long long>((long long)n * 1000000000LL));
    assert(maximum_colorful_subsequence_value(colors, values, 500)
           == optional<long long>((long long)(n - 500) * 1000000000LL));
    fill(colors.begin(), colors.end(), INT_MAX);
    assert(!maximum_colorful_subsequence_value(colors, values, 500));
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({0}, {}, 0); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({}, {}, -1); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({}, {}, 1); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({-1}, {0}, 0); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({0}, {1000000001LL}, 0); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value({0}, {-1000000001LL}, 0); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value(vector<int>(501), vector<long long>(501), 501); });
    require_exception<invalid_argument>([] { (void)maximum_colorful_subsequence_value(vector<int>(200001), vector<long long>(200001), 0); });
    cout << "color-exclusion-two-best-dp PASS: independent deletion subsets including negative values, exact deletion counts, color ties, no-solution cases and maximum N/K\n";
}

vector<pair<int, int>> matching_pairs(const string& brackets) {
    vector<int> stack;
    vector<pair<int, int>> pairs;
    for (int i = 0; i < (int)brackets.size(); ++i) {
        if (brackets[i] == '(') stack.push_back(i);
        else { pairs.emplace_back(stack.back(), i); stack.pop_back(); }
    }
    assert(stack.empty());
    return pairs;
}

long long literal_ternary_bracket_colors(const string& brackets) {
    const auto pairs = matching_pairs(brackets);
    long long answer = 0;
    int patterns = 1;
    for (size_t i = 0; i < brackets.size(); ++i) patterns *= 3;
    for (int pattern = 0; pattern < patterns; ++pattern) {
        int code = pattern;
        vector<int> color(brackets.size());
        for (int& c : color) { c = code % 3; code /= 3; }
        bool valid = true;
        for (const auto& [left, right] : pairs)
            if ((color[left] == 0) == (color[right] == 0)) { valid = false; break; }
        for (int i = 1; valid && i < (int)color.size(); ++i)
            if (color[i] && color[i] == color[i - 1]) valid = false;
        answer += valid;
    }
    return answer;
}

long long literal_pair_bracket_colors(const string& brackets) {
    const auto pairs = matching_pairs(brackets);
    long long answer = 0;
    vector<int> color(brackets.size());
    function<void(int)> visit = [&](int at) {
        if (at == (int)pairs.size()) {
            for (int i = 1; i < (int)color.size(); ++i)
                if (color[i] && color[i] == color[i - 1]) return;
            ++answer;
            return;
        }
        const auto [left, right] = pairs[at];
        for (int side = 0; side < 2; ++side) for (int c = 1; c <= 2; ++c) {
            color[left] = side == 0 ? c : 0;
            color[right] = side == 1 ? c : 0;
            visit(at + 1);
        }
    };
    visit(0);
    return answer;
}

vector<string> balanced_words(int pairs) {
    vector<string> result;
    function<void(string, int, int)> visit = [&](string word, int opens, int closes) {
        if (opens == pairs && closes == pairs) { result.push_back(word); return; }
        if (opens < pairs) visit(word + '(', opens + 1, closes);
        if (closes < opens) visit(word + ')', opens, closes + 1);
    };
    visit("", 0, 0);
    return result;
}

void check_bracket_colors(mt19937& rng) {
    for (int pairs = 0; pairs <= 5; ++pairs)
        for (const string& word : balanced_words(pairs)) {
            const auto expected = literal_ternary_bracket_colors(word);
            assert(literal_pair_bracket_colors(word) == expected);
            assert(count_boundary_bracket_colorings(word) == expected);
        }
    for (int pairs = 6; pairs <= 8; ++pairs) {
        auto words = balanced_words(pairs);
        shuffle(words.begin(), words.end(), rng);
        for (int trial = 0; trial < 25; ++trial)
            assert(count_boundary_bracket_colorings(words[trial])
                   == literal_pair_bracket_colors(words[trial]));
    }
    assert(count_boundary_bracket_colorings("()") == 4);
    assert(count_boundary_bracket_colorings("(())") == 12);
    assert(count_boundary_bracket_colorings("()()") == 14);
    const int pairs = 100000;
    assert(count_boundary_bracket_colorings(string(pairs, '(') + string(pairs, ')'))
           == 4 * modular_power(3, pairs - 1) % MOD);
    string flat;
    flat.reserve(2 * pairs);
    for (int i = 0; i < pairs; ++i) flat += "()";
    // For the special flat family, independently count which end of the
    // previous pair is red/blue; only right-to-left equal colors conflict.
    long long left_color = 1, right_color = 1;
    for (int i = 1; i < pairs; ++i) {
        const long long next_left = (2 * left_color + right_color) % MOD;
        const long long next_right = (2 * left_color + 2 * right_color) % MOD;
        left_color = next_left;
        right_color = next_right;
    }
    assert(count_boundary_bracket_colorings(flat) == 2 * (left_color + right_color) % MOD);
    for (const string bad : {"(", ")", ")(", "(()", "())(", "(a)", "[]"})
        require_exception<invalid_argument>([&] { (void)count_boundary_bracket_colorings(bad); });
    require_exception<invalid_argument>([] { (void)count_boundary_bracket_colorings(string(100001, '(') + string(100001, ')')); });
    cout << "bracket-pair-color-boundaries PASS: direct 3^N colors for every small balanced word, explicit pair choices, adjacency constraints and 200000-character deep/flat cases\n";
}

optional<__int128> literal_exact_edge_cost(int n, const vector<ExactStepEdge>& edges,
                                        int edge_count, int source, int target) {
    vector<optional<__int128>> layer(n);
    layer[source] = 0;
    for (int step = 0; step < edge_count; ++step) {
        vector<optional<__int128>> next(n);
        for (const auto& edge : edges) if (layer[edge.from]) {
            const __int128 candidate = *layer[edge.from] + edge.cost;
            if (!next[edge.to] || candidate < *next[edge.to])
                next[edge.to] = candidate;
        }
        layer = move(next);
    }
    return layer[target];
}

void check_exact_case(int n, const vector<ExactStepEdge>& edges, int limit) {
    for (int source = 0; source < n; ++source)
        for (int target = 0; target < n; ++target)
            for (int count = 0; count <= limit; ++count)
                assert(minimum_cost_exact_edges(n, edges, count, source, target)
                       == literal_exact_edge_cost(n, edges, count, source, target));
}

void check_exact_edges(mt19937& rng) {
    // Every directed two-vertex graph over absent/-2/0/3 edges, including
    // actual self-loops, is compared with a fresh DP layer for every step.
    constexpr array<long long, 3> costs = {-2, 0, 3};
    for (int n = 1; n <= 2; ++n) {
        int patterns = 1;
        for (int i = 0; i < n * n; ++i) patterns *= 4;
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<ExactStepEdge> edges;
            for (int from = 0; from < n; ++from)
                for (int to = 0; to < n; ++to) {
                    int state = code % 4;
                    code /= 4;
                    if (state) edges.push_back({from, to, costs[state - 1]});
                }
            check_exact_case(n, edges, 7);
        }
    }
    // All directed three-vertex edge sets, with mixed signs determined by
    // endpoints, exercise parity, unreachable vertices and negative cycles.
    for (int mask = 0; mask < (1 << 9); ++mask) {
        vector<ExactStepEdge> edges;
        for (int from = 0; from < 3; ++from)
            for (int to = 0; to < 3; ++to)
                if (mask >> (3 * from + to) & 1)
                    edges.push_back({from, to, costs[(from + 2 * to) % 3]});
        check_exact_case(3, edges, 6);
    }
    for (int trial = 0; trial < 700; ++trial) {
        const int n = 1 + rng() % 7;
        vector<ExactStepEdge> edges(rng() % (3 * n * n + 1));
        for (auto& edge : edges) {
            edge.from = rng() % n;
            edge.to = rng() % n;
            edge.cost = (long long)(rng() % 2001) - 1000;
        }
        const int source = rng() % n, target = rng() % n, count = rng() % 15;
        assert(minimum_cost_exact_edges(n, edges, count, source, target)
               == literal_exact_edge_cost(n, edges, count, source, target));
    }
    assert(minimum_cost_exact_edges(2, {{0, 1, 4}}, 1, 0, 1) == optional<__int128>(4));
    assert(!minimum_cost_exact_edges(2, {{0, 1, 4}}, 2, 0, 1));
    assert(minimum_cost_exact_edges(1, {}, 0, 0, 0) == optional<__int128>(0));
    assert(!minimum_cost_exact_edges(1, {}, 1, 0, 0));
    assert(!minimum_cost_exact_edges(2, {{0, 1, 0}}, 0, 0, 1));
    check_exact_case(3, {{0, 1, LLONG_MIN}, {1, 2, LLONG_MIN},
                         {2, 0, LLONG_MAX}, {0, 1, LLONG_MAX}, {2, 2, LLONG_MAX}}, 8);
    constexpr unsigned long long k = 1000000000000000000ULL;
    assert(minimum_cost_exact_edges(1, {{0, 0, LLONG_MAX}}, k, 0, 0)
           == optional<__int128>((__int128)k * LLONG_MAX));
    vector<ExactStepEdge> parallel(100000, {0, 0, LLONG_MAX});
    parallel.back().cost = LLONG_MIN;
    assert(minimum_cost_exact_edges(1, parallel, k, 0, 0)
           == optional<__int128>((__int128)k * LLONG_MIN));
    vector<ExactStepEdge> cycle;
    for (int vertex = 0; vertex < 100; ++vertex)
        cycle.push_back({vertex, (vertex + 1) % 100, vertex == 0 ? LLONG_MAX : 0});
    assert(minimum_cost_exact_edges(100, cycle, k, 0, 0)
           == optional<__int128>((__int128)(k / 100) * LLONG_MAX));
    assert(!minimum_cost_exact_edges(100, cycle, k - 1, 0, 0));
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(0, {}, 0, 0, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(101, {}, 0, 0, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {}, 1000000000000000001ULL, 0, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {}, ULLONG_MAX, 0, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {}, 0, -1, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {}, 0, 0, 1); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {{-1, 0, 0}}, 0, 0, 0); });
    require_exception<invalid_argument>([] { (void)minimum_cost_exact_edges(1, {{0, 1, 0}}, 0, 0, 0); });
    require_exception<length_error>([] { (void)minimum_cost_exact_edges(1, vector<ExactStepEdge>(100001, {0, 0, 0}), 0, 0, 0); });
    cout << "exact-k-edge-minplus PASS: independent step-layer DP on all small directed graphs, forbidden implicit waiting, real loops/multiple edges, signed-64-bit costs and 10^18-edge boundaries\n";
}

long double literal_wall_bottleneck(const vector<pair<long long, long long>>& points,
                                   long long half_width) {
    const int n = points.size(), upper = n, lower = n + 1;
    vector<vector<long double>> distance(n + 2,
        vector<long double>(n + 2, numeric_limits<long double>::infinity()));
    for (int i = 0; i < n + 2; ++i) distance[i][i] = 0;
    distance[upper][lower] = distance[lower][upper] = 2.0L * half_width;
    for (int i = 0; i < n; ++i) {
        distance[i][upper] = distance[upper][i] = (long double)half_width - points[i].second;
        distance[i][lower] = distance[lower][i] = (long double)half_width + points[i].second;
        for (int j = 0; j < i; ++j) {
            const long double dx = (long double)points[i].first - points[j].first;
            const long double dy = (long double)points[i].second - points[j].second;
            distance[i][j] = distance[j][i] = hypotl(dx, dy);
        }
    }
    // Independent min/max Floyd relaxation: no sorting, squared distances,
    // or disjoint-set implementation is shared with the published example.
    for (int middle = 0; middle < n + 2; ++middle)
        for (int from = 0; from < n + 2; ++from)
            for (int to = 0; to < n + 2; ++to)
                distance[from][to] = min(distance[from][to],
                    max(distance[from][middle], distance[middle][to]));
    return distance[upper][lower] / 2;
}

void require_close(long double actual, long double expected) {
    assert(isfinite(actual));
    assert(fabsl(actual - expected) <= 1e-13L * max(1.0L, fabsl(expected)));
}

void check_passage_case(const vector<pair<long long, long long>>& points, long long half_width) {
    const auto before = points;
    const long double result = maximum_disk_passage_radius(points, half_width);
    require_close(result, literal_wall_bottleneck(points, half_width));
    assert(points == before);
    assert(0 <= result && result <= half_width);
    auto shifted = points;
    for (auto& [x, y] : shifted) { x += 100; y = -y; }
    require_close(maximum_disk_passage_radius(shifted, half_width), result);
}

void check_disk_passage(mt19937& rng) {
    const vector<pair<long long, long long>> grid = {
        {-2, -2}, {-2, 0}, {-2, 2}, {0, -2}, {0, 0}, {0, 2}, {2, -2}, {2, 0}, {2, 2}};
    for (int n = 0; n <= 4; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= int(grid.size());
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<pair<long long, long long>> points(n);
            for (auto& point : points) { point = grid[code % grid.size()]; code /= grid.size(); }
            check_passage_case(points, 3);
        }
    }
    for (int trial = 0; trial < 700; ++trial) {
        const int n = rng() % 13;
        const long long half_width = 1 + rng() % 100;
        vector<pair<long long, long long>> points(n);
        for (auto& [x, y] : points) {
            x = (long long)(rng() % 10001) - 5000;
            y = (long long)(rng() % (2 * half_width - 1)) - half_width + 1;
        }
        check_passage_case(points, half_width);
    }
    require_close(maximum_disk_passage_radius({}), 100);
    require_close(maximum_disk_passage_radius({}, 1000000000), 1000000000);
    for (long long half_width : {1LL, 2LL, 100LL, 1000000000LL})
        for (long long y : {0LL, 1 - half_width, half_width - 1})
            require_close(maximum_disk_passage_radius({{1000000000, y}}, half_width),
                          ((long double)half_width + llabs(y)) / 2);
    const vector<pair<long long, long long>> extremes = {
        {-1000000000, -999999999}, {1000000000, 999999999}, {0, 0}, {0, 0}};
    require_close(maximum_disk_passage_radius(extremes, 1000000000),
                  literal_wall_bottleneck(extremes, 1000000000));
    // Points on one vertical line cut the strip into explicit gaps. Their
    // largest consecutive gap (including the walls) is the usable diameter.
    vector<pair<long long, long long>> chain;
    for (int y = -1000; y <= 999; ++y) chain.emplace_back(123, y);
    require_close(maximum_disk_passage_radius(chain, 1001), 1);
    require_close(maximum_disk_passage_radius(vector<pair<long long, long long>>(2000, {0, 0})), 50);
    require_exception<length_error>([] { (void)maximum_disk_passage_radius(vector<pair<long long, long long>>(2001)); });
    require_exception<invalid_argument>([] { (void)maximum_disk_passage_radius({}, 0); });
    require_exception<invalid_argument>([] { (void)maximum_disk_passage_radius({}, -1); });
    require_exception<invalid_argument>([] { (void)maximum_disk_passage_radius({}, 1000000001); });
    for (const auto& point : vector<pair<long long, long long>>{
            {1000000001, 0}, {-1000000001, 0}, {LLONG_MIN, 0}, {LLONG_MAX, 0},
            {0, 100}, {0, -100}, {0, LLONG_MIN}, {0, LLONG_MAX}})
        require_exception<invalid_argument>([&] { (void)maximum_disk_passage_radius({point}); });
    cout << "disk-passage-wall-bottleneck PASS: independent min/max Floyd thresholds for all small point lists, duplicates/symmetries, exact vertical gaps, full coordinates and 2000-point boundaries\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261024);
    check_disjoint_witness(rng);
    check_and_zero(rng);
    check_colorful_dp(rng);
    check_bracket_colors(rng);
    check_exact_edges(rng);
    check_disk_passage(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-mask-bracket-path-cpp-") as directory:
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
        print("All 6 mask, bracket and path implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
