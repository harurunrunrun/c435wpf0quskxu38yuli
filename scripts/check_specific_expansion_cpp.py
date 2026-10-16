#!/usr/bin/env python3
"""Compare the six published expansion examples with independent small models."""

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
    "mst-equal-weight-edge-classification",
    "strict-second-mst-two-maxima",
    "sequence-cut-reverse-split-merge",
    "dynamic-sequence-affine-sum",
    "range-stabilizing-successor",
    "global-replace-reverse-map",
)


def extracted_source():
    """Exercise article fences directly instead of copying their implementations."""
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
#include <random>
#include <limits>
using namespace std;

// Test bodies are below. Each expected result is computed with a direct model
// that does not use the decomposition, lazy flags, or offline order in an article.
using TestEdge = tuple<int, int, long long>;
using article_mst_equal_weight_edge_classification::MstEdgeUse;
using article_mst_equal_weight_edge_classification::classify_msf_edges;
using article_strict_second_mst_two_maxima::strict_second_mst;

struct TinyDsu {
    vector<int> parent;
    explicit TinyDsu(int n) : parent(n) { iota(parent.begin(), parent.end(), 0); }
    int find(int u) { return parent[u] == u ? u : parent[u] = find(parent[u]); }
    bool merge(int u, int v) {
        u = find(u); v = find(v);
        if (u == v) return false;
        parent[u] = v;
        return true;
    }
};

void check_spanning_forests(int n, const vector<TestEdge>& edges) {
    const auto before = edges;
    const int m = edges.size();
    assert(m < 20);
    TinyDsu all(n);
    int components = n;
    for (auto [u, v, weight] : edges) { (void)weight; components -= all.merge(u, v); }
    bool found = false;
    __int128 minimum = 0;
    optional<__int128> second;
    vector<unsigned> minimum_masks;
    // An acyclic subset with n-C edges must span every original component.
    // Enumerating such subsets also checks disconnected minimum forests; no
    // Kruskal order, weight-group contraction, bridge finding or path maxima
    // appears in this oracle.
    for (unsigned mask = 0; mask < (1U << m); ++mask) {
        if (__builtin_popcount(mask) != n - components) continue;
        TinyDsu selected(n);
        __int128 cost = 0;
        bool forest = true;
        for (int e = 0; e < m; ++e) if ((mask >> e) & 1U) {
            auto [u, v, weight] = edges[e];
            if (!selected.merge(u, v)) { forest = false; break; }
            cost += weight;
        }
        if (!forest) continue;
        if (!found || cost < minimum) {
            if (found) second = minimum;
            found = true;
            minimum = cost;
            minimum_masks.assign(1, mask);
        } else if (cost == minimum) {
            minimum_masks.push_back(mask);
        } else if (!second || cost < *second) {
            second = cost;
        }
    }
    assert(found && !minimum_masks.empty());
    const auto result = classify_msf_edges(n, edges);
    assert(result.components == components && result.use.size() == edges.size());
    for (int e = 0; e < m; ++e) {
        size_t count = 0;
        for (unsigned mask : minimum_masks) count += (mask >> e) & 1U;
        auto expected = count == 0 ? MstEdgeUse::None
                      : count == minimum_masks.size() ? MstEdgeUse::Every : MstEdgeUse::Some;
        assert(result.use[e] == expected);
    }
    const auto next = strict_second_mst(n, edges);
    assert(next.connected == (components == 1));
    if (components == 1) {
        assert(next.minimum == minimum);
        assert(next.second == second);
    } else assert(!next.second);
    assert(edges == before);
}

void check_mst(mt19937& rng) {
    // Every simple graph on four vertices with each potential edge absent or
    // assigned one of three repeated weights, including negative and zero.
    vector<pair<int, int>> possible;
    for (int u = 0; u < 4; ++u) for (int v = u + 1; v < 4; ++v) possible.emplace_back(u, v);
    for (int encoding = 0; encoding < 4096; ++encoding) {
        int digits = encoding;
        vector<TestEdge> edges;
        for (auto [u, v] : possible) {
            int choice = digits % 4;
            digits /= 4;
            if (choice) edges.emplace_back(u, v, choice - 2);
        }
        check_spanning_forests(4, edges);
    }
    const long long lo = numeric_limits<long long>::min();
    const long long hi = numeric_limits<long long>::max();
    for (const auto& edges : vector<vector<TestEdge>>{
            {}, {{0,0,lo}}, {{0,0,hi}, {1,1,lo}},
            {{0,1,4}, {0,1,4}, {0,1,5}},
            {{0,1,hi}, {1,2,hi}, {0,2,hi-1}},
            {{0,1,lo}, {1,2,lo}, {0,2,lo+1}},
            {{0,1,lo}, {1,2,0}, {0,2,hi}, {0,1,hi}, {2,2,lo}},
            // Replacing one of the two equal maximum edges leaves the cost
            // unchanged; the strictly heavier answer needs the second distinct
            // maximum, rather than a second edge with the same weight.
            {{0,1,1}, {1,2,3}, {2,3,3}, {0,3,3}, {0,2,5}},
            {{0,1,-2}, {0,1,-2}, {2,3,-1}, {2,3,4}, {3,3,-9}}}) {
        int n = 1;
        for (auto [u,v,w] : edges) { (void)w; n=max(n, max(u,v)+1); }
        check_spanning_forests(n, edges);
    }
    for (int trial = 0; trial < 1400; ++trial) {
        int n = 1 + int(rng() % 7), m = int(rng() % 13);
        vector<TestEdge> edges;
        for (int e = 0; e < m; ++e) {
            int u = rng() % n, v = rng() % n;
            long long weight = int(rng() % 9) - 4;
            if (e && trial % 5 == 0) {
                tie(u, v, weight) = edges[rng() % edges.size()];
                if (trial % 10) ++weight;
            }
            edges.emplace_back(u, v, weight);
        }
        check_spanning_forests(n, edges);
    }
    cout << "mst-equal-weight-edge-classification PASS: all small weighted graphs and randomized multigraph minimum forests\n";
    cout << "strict-second-mst-two-maxima PASS: exhaustive distinct tree costs, equal maxima, disconnected graphs and full signed weights\n";
}

using article_sequence_cut_reverse_split_merge::CutReverseSequence;
using article_dynamic_sequence_affine_sum::DynamicAffineSequence;

long long normalized(long long value) {
    constexpr long long mod = 998244353;
    long long result = value % mod;
    return result < 0 ? result + mod : result;
}

long long random_signed_value(mt19937& rng) {
    switch (rng() % 10) {
        case 0: return numeric_limits<long long>::min();
        case 1: return numeric_limits<long long>::max();
        case 2: return 0;
        case 3: return 998244353;
        case 4: return -998244353;
        default: return (long long)(rng() % 2000000001U) - 1000000000;
    }
}

void check_cut_reverse(mt19937& rng) {
    for (int trial = 0; trial < 100; ++trial) {
        vector<long long> expected(rng() % 30);
        for (auto& value : expected) value = random_signed_value(rng);
        CutReverseSequence sequence(expected, 2026101700ULL + trial);
        assert(sequence.values() == expected);
        for (int step = 0; step < 650; ++step) {
            int n = expected.size();
            int l = rng() % (n + 1), r = rng() % (n + 1);
            if (l > r) swap(l, r);
            if (step % 17 == 0) { l = 0; r = n; }
            if (step % 19 == 0) r = l;
            int operation = n > 65 ? 1 : rng() % 5;
            if (operation == 0) {
                int pos = rng() % (n + 1);
                long long value = random_signed_value(rng);
                sequence.insert(pos, value);
                expected.insert(expected.begin() + pos, value);
            } else if (operation == 1) {
                if (n) {
                    int pos = rng() % n;
                    sequence.erase(pos);
                    expected.erase(expected.begin() + pos);
                }
            } else if (operation == 2) {
                sequence.reverse(l, r);
                reverse(expected.begin() + l, expected.begin() + r);
            } else {
                int pos = rng() % (n - (r - l) + 1);
                vector<long long> cut(expected.begin() + l, expected.begin() + r);
                expected.erase(expected.begin() + l, expected.begin() + r);
                expected.insert(expected.begin() + pos, cut.begin(), cut.end());
                sequence.cut_paste(l, r, pos);
            }
            assert(sequence.size() == int(expected.size()));
            // Preserve pending reversal flags across several later splits and
            // merges instead of forcing a complete traversal after every edit.
            if (step % 13 == 0) assert(sequence.values() == expected);
        }
        assert(sequence.values() == expected);
    }
    CutReverseSequence empty;
    empty.reverse(0, 0);
    empty.cut_paste(0, 0, 0);
    assert(empty.values().empty());
    // A cut is positioned after its old interval has been removed, so moving
    // a segment right must not adjust this index a second time.
    CutReverseSequence explicit_move({0,1,2,3,4,5}, 17);
    explicit_move.cut_paste(1,3,4);
    assert(explicit_move.values() == vector<long long>({0,3,4,5,1,2}));
    explicit_move.reverse(0,6);
    explicit_move.cut_paste(0,6,0);
    assert(explicit_move.values() == vector<long long>({2,1,5,4,3,0}));
    cout << "sequence-cut-reverse-split-merge PASS: randomized vector edits, repeated reversals, empty ranges and cut positions after removal\n";
}

void check_dynamic_affine(mt19937& rng) {
    constexpr long long mod = 998244353;
    auto apply = [&](vector<long long>& values, int l, int r, long long a, long long b) {
        a = normalized(a); b = normalized(b);
        for (int i = l; i < r; ++i) values[i] = (a * values[i] + b) % mod;
    };
    for (int trial = 0; trial < 90; ++trial) {
        vector<long long> initial(rng() % 30);
        for (auto& value : initial) value = random_signed_value(rng);
        vector<long long> expected = initial;
        for (auto& value : expected) value = normalized(value);
        DynamicAffineSequence sequence(initial, 2026101800ULL + trial);
        assert(sequence.values() == expected);
        for (int step = 0; step < 750; ++step) {
            int n = expected.size();
            int l = rng() % (n + 1), r = rng() % (n + 1);
            if (l > r) swap(l, r);
            if (step % 17 == 0) { l = 0; r = n; }
            if (step % 19 == 0) r = l;
            int operation = n > 65 ? 1 : rng() % 6;
            if (operation == 0) {
                int pos = rng() % (n + 1);
                long long value = random_signed_value(rng);
                sequence.insert(pos, value);
                expected.insert(expected.begin() + pos, normalized(value));
            } else if (operation == 1) {
                if (n) {
                    int pos = rng() % n;
                    sequence.erase(pos);
                    expected.erase(expected.begin() + pos);
                }
            } else if (operation == 2) {
                sequence.reverse(l, r);
                reverse(expected.begin() + l, expected.begin() + r);
            } else if (operation == 3 || operation == 4) {
                long long a = random_signed_value(rng), b = random_signed_value(rng);
                sequence.apply_affine(l, r, a, b);
                apply(expected, l, r, a, b);
                // Stack a second pending map before materializing the tree;
                // affine composition is deliberately noncommutative.
                if (operation == 4) {
                    sequence.apply_affine(l, r, 5, 7);
                    apply(expected, l, r, 5, 7);
                }
            }
            // Edits may change n, so query separately chosen valid boundaries.
            int query_l = rng() % (expected.size() + 1), query_r = rng() % (expected.size() + 1);
            if (query_l > query_r) swap(query_l, query_r);
            long long expected_sum = 0;
            for (int i = query_l; i < query_r; ++i) expected_sum = (expected_sum + expected[i]) % mod;
            assert(sequence.range_sum(query_l, query_r) == expected_sum);
            assert(sequence.range_sum(query_l, query_l) == 0);
            assert(sequence.size() == int(expected.size()));
            if (step % 13 == 0) assert(sequence.values() == expected);
        }
        assert(sequence.values() == expected);
    }
    DynamicAffineSequence composition({1,2,3,4,5}, 19);
    composition.apply_affine(0,5,2,3);
    composition.apply_affine(0,5,5,7);
    composition.reverse(0,5);
    composition.apply_affine(1,4,0,-3);
    assert(composition.values() == vector<long long>({72,mod-3,mod-3,mod-3,32}));
    assert(composition.range_sum(0,5) == 95);
    DynamicAffineSequence empty;
    empty.reverse(0,0);
    empty.apply_affine(0,0,numeric_limits<long long>::min(),numeric_limits<long long>::max());
    assert(empty.range_sum(0,0) == 0 && empty.values().empty());
    cout << "dynamic-sequence-affine-sum PASS: vector insertions/deletions, reversals, signed normalization, noncommuting lazy maps and empty sums\n";
}

using article_range_stabilizing_successor::StabilizingRangeMap;
using article_range_stabilizing_successor::integer_sqrt;
using article_range_stabilizing_successor::divisor_counts;
using article_global_replace_reverse_map::GlobalReplaceOp;
using article_global_replace_reverse_map::final_sequence_after_replacements;

long long exact_floor_sqrt(long long value) {
    // An estimate plus exact wide-integer corrections is independent of the
    // published division-based binary search, even close to a large square.
    long long root = static_cast<long long>(sqrtl(static_cast<long double>(value)));
    while ((__int128)(root + 1) * (root + 1) <= value) ++root;
    while ((__int128)root * root > value) --root;
    return root;
}

long long trial_divisors(long long value) {
    assert(value > 0);
    long long answer = 0;
    for (long long d = 1; d <= value / d; ++d) if (value % d == 0)
        answer += d == value / d ? 1 : 2;
    return answer;
}

void check_stabilizing(mt19937& rng) {
    auto run = [&](vector<long long> expected, auto transform, auto oracle_transform, auto fixed) {
        const int n = expected.size();
        long long calls = 0;
        StabilizingRangeMap ranges(expected,
            [&](long long value) { ++calls; return transform(value); }, fixed);
        for (int step = 0; step < 260; ++step) {
            int l = rng() % (n + 1), r = rng() % (n + 1);
            if (l > r) swap(l, r);
            if (step % 17 == 0) { l = 0; r = n; }
            if (step % 19 == 0) r = l;
            long long needed = 0;
            for (int i = l; i < r; ++i) {
                needed += !fixed(expected[i]);
                expected[i] = oracle_transform(expected[i]);
            }
            const auto before_calls = calls;
            ranges.apply(l, r);
            // Each nonfixed element must be transformed once during one
            // update. Previously fixed elements must never be revisited.
            assert(calls - before_calls == needed);
            for (int i = 0; i < n; ++i) assert(ranges.get(i) == expected[i]);
            int a = rng() % (n + 1), b = rng() % (n + 1);
            if (a > b) swap(a, b);
            assert(ranges.sum(a, b) == accumulate(expected.begin() + a, expected.begin() + b, 0LL));
            assert(ranges.sum(0, n) == accumulate(expected.begin(), expected.end(), 0LL));
            assert(ranges.sum(a, a) == 0);
        }
    };
    auto sqrt_fixed = [](long long value) { return value <= 1; };
    auto divisor_fixed = [](long long value) { return value <= 2; };
    const auto divisor_table = divisor_counts(1000000);
    auto table_divisors = [&](long long value) { return divisor_table.at(value); };
    for (int x = 1; x <= 3000; ++x) assert(divisor_table[x] == trial_divisors(x));
    for (int trial = 0; trial < 2500; ++trial) {
        int x = 1 + rng() % 1000000;
        assert(divisor_table[x] == trial_divisors(x));
    }
    vector<long long> square_boundaries = {0,1,2,3,4,8,9,15,16,17,numeric_limits<long long>::max()};
    for (long long root : {2LL,3LL,999999LL,1000000LL,3037000498LL,3037000499LL})
        for (long long delta : {-1LL,0LL,1LL}) square_boundaries.push_back(root*root+delta);
    for (long long value : square_boundaries) assert(integer_sqrt(value) == exact_floor_sqrt(value));
    for (int trial = 0; trial < 2500; ++trial) {
        long long value = (long long)((uint64_t(rng()) << 32 | rng()) >> 1);
        assert(integer_sqrt(value) == exact_floor_sqrt(value));
    }
    run({}, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
    run({0,0,1,1,0,1}, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
    run({1,2,1,2,2,1}, table_divisors, trial_divisors, divisor_fixed);
    run({0,1,2,3,4,8,9,15,16,17,1000000000000LL}, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
    run({1,2,3,4,6,12,36,49,97,999983,1000000}, table_divisors, trial_divisors, divisor_fixed);
    run({numeric_limits<long long>::max()}, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
    run({numeric_limits<long long>::max()-2,1,1}, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
    for (int trial = 0; trial < 80; ++trial) {
        vector<long long> square_values(rng() % 60), divisor_values(rng() % 60);
        for (auto& value : square_values)
            value = trial % 5 ? (long long)(rng() % 1000001U) * (rng() % 1000001U) : rng() % 3;
        for (auto& value : divisor_values) value = trial % 5 ? 1 + rng() % 1000000 : 1 + rng() % 2;
        run(square_values, integer_sqrt, exact_floor_sqrt, sqrt_fixed);
        run(divisor_values, table_divisors, trial_divisors, divisor_fixed);
    }
    cout << "range-stabilizing-successor PASS: exact square roots and divisor updates, elementwise/sum comparisons, permanent skips and full signed-sum boundary\n";
}

vector<long long> forward_replacements(const vector<GlobalReplaceOp>& operations) {
    vector<long long> sequence;
    for (const auto& operation : operations) {
        if (operation.kind == GlobalReplaceOp::Append) sequence.push_back(operation.from);
        else for (auto& value : sequence)
            if (value == operation.from) value = operation.to;
    }
    return sequence;
}

void check_replacements(mt19937& rng) {
    auto verify = [](const vector<GlobalReplaceOp>& operations) {
        vector<tuple<int, long long, long long>> snapshot;
        for (const auto& operation : operations)
            snapshot.emplace_back(int(operation.kind), operation.from, operation.to);
        auto expected = forward_replacements(operations);
        assert(final_sequence_after_replacements(operations) == expected);
        for (size_t i = 0; i < operations.size(); ++i) {
            const auto& operation = operations[i];
            assert(snapshot[i] == make_tuple(int(operation.kind), operation.from, operation.to));
        }
    };
    using Op = GlobalReplaceOp;
    verify({});
    verify({{Op::Replace,1,2},{Op::Replace,2,3},{Op::Replace,3,1}});
    verify({{Op::Append,1,0},{Op::Replace,1,2},{Op::Replace,2,3},{Op::Append,1,0}});
    verify({{Op::Append,1,0},{Op::Append,2,0},{Op::Replace,1,2},{Op::Replace,2,1}});
    verify({{Op::Append,1,0},{Op::Replace,2,3},{Op::Append,2,0},{Op::Replace,1,1}});
    verify({{Op::Append,1,0},{Op::Replace,1,2},{Op::Append,1,0},
            {Op::Replace,2,3},{Op::Append,2,0},{Op::Replace,1,4},{Op::Append,1,0}});
    const vector<long long> pool = {
        numeric_limits<long long>::min(), numeric_limits<long long>::max(),
        -1000000000000000000LL, 1000000000000000000LL, -998244353, -1, 0, 1, 2, 998244353
    };
    for (int trial = 0; trial < 1100; ++trial) {
        vector<Op> operations;
        for (int step = 0, count = rng() % 120; step < count; ++step) {
            long long from = pool[rng() % pool.size()], to = pool[rng() % pool.size()];
            if (step % 9 == 0) to = from;
            operations.push_back({rng() % 5 < 2 ? Op::Append : Op::Replace, from, to});
            // Prefix answers detect the distinction between a snapshot of a
            // replacement target and a reference to that target's future map.
            if (step % 23 == 0) verify(operations);
        }
        verify(operations);
    }
    vector<Op> long_chain;
    for (int i = 0; i < 1000; ++i) long_chain.push_back({Op::Append, -1000000000000000000LL+i, 0});
    for (int i = 0; i < 999; ++i)
        long_chain.push_back({Op::Replace, -1000000000000000000LL+i, -1000000000000000000LL+i+1});
    verify(long_chain);
    cout << "global-replace-reverse-map PASS: forward append/replace traces, target snapshots, absent values, cycles, compressed signed values and long chains\n";
}

int main() {
    mt19937 rng(20261018);
    check_mst(rng);
    check_cut_reverse(rng);
    check_dynamic_affine(rng);
    check_stabilizing(rng);
    check_replacements(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-specific-expansion-cpp-") as directory:
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
        print("All 6 expansion implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
