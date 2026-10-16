#!/usr/bin/env python3
"""Compare six published DP implementations with independent small enumerations."""

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
    "lis-through-each-position",
    "lis-length-count-monoid",
    "partition-extrema-weighted-sum",
    "partition-minimum-pivot-max-score",
    "interval-removal-carried-group",
    "permutation-inequality-last-rank",
)


def extracted_source():
    """Use the actual complete article examples, not copies of their code."""
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
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
using article_lis_through_each_position::classify_lis_positions;
using article_lis_length_count_monoid::count_lis_mod;
using article_partition_extrema_weighted_sum::partition_extrema_product_sum;
using article_partition_minimum_pivot_max_score::partition_minimum_pivot_max_score;
using article_interval_removal_carried_group::max_equal_run_square_score;
using article_permutation_inequality_last_rank::count_inequality_permutations;

struct EnumeratedLis {
    int length = 0;
    long long count = 0;
    vector<int> kind, left, right;
};

EnumeratedLis subsequence_lis(const vector<long long>& values) {
    const int n = values.size();
    assert(n <= 20);
    EnumeratedLis answer;
    answer.kind.assign(n, 0);
    answer.left.assign(n, 0);
    answer.right.assign(n, 0);
    vector<unsigned> maximum_masks;
    // Enumerate actual selected index sets; no rank compression, patience
    // sorting, Fenwick tree, or LIS DP is used by this oracle.
    for (unsigned mask = 0; mask < (1U << n); ++mask) {
        bool increasing = true;
        int previous = -1, first = -1, last = -1, length = 0;
        for (int i = 0; i < n; ++i) if ((mask >> i) & 1U) {
            if (previous >= 0 && values[previous] >= values[i]) {
                increasing = false;
                break;
            }
            if (first < 0) first = i;
            last = previous = i;
            ++length;
        }
        if (!increasing) continue;
        if (length) {
            answer.left[last] = max(answer.left[last], length);
            answer.right[first] = max(answer.right[first], length);
        }
        if (length > answer.length) {
            answer.length = length;
            maximum_masks.clear();
        }
        if (length == answer.length) maximum_masks.push_back(mask);
    }
    answer.count = maximum_masks.size();
    for (int i = 0; i < n; ++i) {
        size_t uses = 0;
        for (unsigned mask : maximum_masks) uses += (mask >> i) & 1U;
        answer.kind[i] = uses == 0 ? 0 : uses == maximum_masks.size() ? 2 : 1;
    }
    return answer;
}

void check_lis_case(const vector<long long>& values, const vector<long long>& moduli) {
    const auto before = values;
    const auto expected = subsequence_lis(values);
    const auto classified = classify_lis_positions(values);
    assert(classified.length == expected.length);
    assert(classified.left == expected.left && classified.right == expected.right);
    assert(classified.kind == expected.kind);
    for (long long modulus : moduli) {
        auto counted = count_lis_mod(values, modulus);
        assert(counted.length == expected.length);
        assert(counted.count == expected.count % modulus);
    }
    assert(values == before);
}

void check_lis(mt19937& rng) {
    const vector<long long> moduli{1, 2, 3, 97, 998244353, 1LL << 32,
        numeric_limits<long long>::max()};
    for (int n = 0, power = 1; n <= 8; ++n, power *= 3) {
        for (int encoding = 0; encoding < power; ++encoding) {
            vector<long long> values(n);
            int digits = encoding;
            for (auto& value : values) { value = digits % 3 - 1; digits /= 3; }
            check_lis_case(values, moduli);
        }
    }
    const long long lo = numeric_limits<long long>::min();
    const long long hi = numeric_limits<long long>::max();
    for (const auto& values : vector<vector<long long>>{
            {}, {lo}, {hi}, {lo,hi}, {hi,lo}, {lo,lo,hi,hi},
            {1,1,2,2}, {1,3,2,4}, {4,3,2,1}, {2,2,2,2},
            {lo,0,hi,-1,lo,hi,0,hi},
            {3,1,4,1,5,9,2,6,5,3,5}}) check_lis_case(values, moduli);
    for (int trial = 0; trial < 450; ++trial) {
        vector<long long> values(rng() % 15);
        for (auto& value : values) {
            switch (rng() % 11) {
                case 0: value = lo; break;
                case 1: value = hi; break;
                default: value = int(rng() % 13) - 6;
            }
        }
        check_lis_case(values, moduli);
    }
    // Each equal-value block offers independent choices. Counts quickly exceed
    // 64 bits; the expected residue is computed separately with 128-bit products.
    vector<long long> blocked;
    constexpr int blocks = 120, choices = 7;
    for (int value = 0; value < blocks; ++value)
        blocked.insert(blocked.end(), choices, value);
    const auto classified = classify_lis_positions(blocked);
    assert(classified.length == blocks);
    for (int status : classified.kind) assert(status == 1);
    for (long long modulus : moduli) {
        long long expected = 1 % modulus;
        for (int i = 0; i < blocks; ++i)
            expected = static_cast<long long>((__int128)expected * choices % modulus);
        const auto counted = count_lis_mod(blocked, modulus);
        assert(counted.length == blocks && counted.count == expected);
    }
    vector<long long> monotone(100000);
    iota(monotone.begin(), monotone.end(), -50000LL);
    auto increasing = classify_lis_positions(monotone);
    assert(increasing.length == int(monotone.size()));
    for (int status : increasing.kind) assert(status == 2);
    auto count = count_lis_mod(monotone, 998244353);
    assert(count.length == int(monotone.size()) && count.count == 1);
    reverse(monotone.begin(), monotone.end());
    auto decreasing = classify_lis_positions(monotone);
    assert(decreasing.length == 1);
    for (int status : decreasing.kind) assert(status == 1);
    count = count_lis_mod(monotone, 998244353);
    assert(count.length == 1 && count.count == int(monotone.size()));
    cout << "lis-through-each-position PASS: every small subsequence, exact left/right lengths, membership, duplicates and signed endpoints\n";
    cout << "lis-length-count-monoid PASS: index-distinct subsequence counts, modulus one, zero residues and counts exceeding 64 bits\n";
}

int all_partition_extrema(const vector<long long>& values) {
    constexpr long long modulus = 998244353;
    const int n = values.size();
    if (!n) return 1;
    long long result = 0;
    // A bit after each position chooses an actual partition boundary. Compute
    // each segment's extrema directly, rather than maintaining stack groups.
    for (unsigned cuts = 0; cuts < (1U << (n - 1)); ++cuts) {
        long long product = 1;
        int left = 0;
        for (int right = 0; right < n; ++right) {
            if (right != n - 1 && !((cuts >> right) & 1U)) continue;
            auto bounds = minmax_element(values.begin() + left, values.begin() + right + 1);
            long long difference = static_cast<long long>(((__int128)*bounds.second - *bounds.first) % modulus);
            product = product * difference % modulus;
            left = right + 1;
        }
        result = (result + product) % modulus;
    }
    return int(result);
}

__int128 all_partition_pivots(const vector<long long>& height, const vector<long long>& score) {
    const int n = height.size();
    if (!n) return 0;
    optional<__int128> best;
    for (unsigned cuts = 0; cuts < (1U << (n - 1)); ++cuts) {
        __int128 result = 0;
        int left = 0;
        for (int right = 0; right < n; ++right) {
            if (right != n - 1 && !((cuts >> right) & 1U)) continue;
            int pivot = left;
            for (int i = left + 1; i <= right; ++i)
                if (height[i] <= height[pivot]) pivot = i; // Rightmost minimum.
            result += score[pivot];
            left = right + 1;
        }
        if (!best || result > *best) best = result;
    }
    return *best;
}

void check_extrema_case(const vector<long long>& values) {
    const auto before = values;
    assert(partition_extrema_product_sum(values) == all_partition_extrema(values));
    assert(values == before);
}

void check_pivot_case(const vector<long long>& height, const vector<long long>& score) {
    const auto old_height = height, old_score = score;
    assert(partition_minimum_pivot_max_score(height, score) == all_partition_pivots(height, score));
    assert(height == old_height && score == old_score);
}

void check_partition_dp(mt19937& rng) {
    for (int n = 0, power = 1; n <= 8; ++n, power *= 3) {
        for (int encoding = 0; encoding < power; ++encoding) {
            vector<long long> values(n), score(n);
            int digits = encoding;
            for (int i = 0; i < n; ++i) {
                values[i] = digits % 3 - 1;
                score[i] = (i * 5 + encoding) % 9 - 6;
                digits /= 3;
            }
            check_extrema_case(values);
            check_pivot_case(values, score);
        }
    }
    // Original CF1482E has distinct heights. Exhaust all their orders as well
    // as separately exercising the article's declared rightmost tie extension.
    for (int n = 0; n <= 7; ++n) {
        vector<long long> height(n), score(n);
        iota(height.begin(), height.end(), 0);
        do {
            for (int i = 0; i < n; ++i) score[i] = (height[i] * 7 + i * 3) % 13 - 8;
            check_pivot_case(height, score);
        } while (next_permutation(height.begin(), height.end()));
    }
    const long long lo = numeric_limits<long long>::min();
    const long long hi = numeric_limits<long long>::max();
    const vector<long long> pool{lo,lo+1,-998244353,-1,0,1,998244353,hi-1,hi};
    for (const auto& values : vector<vector<long long>>{
            {}, {lo}, {hi}, {lo,hi}, {hi,lo}, {lo,0,hi}, {hi,lo,hi,lo},
            {2,2,2,2}, {-3,-2,-1,0,1,2}, {2,1,0,-1,-2,-3},
            {998244353,0,-998244353}, {lo,lo+1,hi-1,hi}}) check_extrema_case(values);
    check_pivot_case({0,1,2}, {lo,lo,lo});
    check_pivot_case({2,1,0}, {lo,lo,lo});
    check_pivot_case({0,0,0}, {hi,hi,hi});
    check_pivot_case({1,1}, {hi,lo});
    check_pivot_case({1,1}, {lo,hi});
    check_pivot_case({0,1,0,1,0}, {lo,hi,lo,hi,lo});
    for (int trial = 0; trial < 1200; ++trial) {
        int n = rng() % 13;
        vector<long long> values(n), score(n);
        for (int i = 0; i < n; ++i) {
            values[i] = trial % 5 ? int(rng() % 13) - 6 : pool[rng() % pool.size()];
            score[i] = trial % 4 ? int(rng() % 31) - 20 : pool[rng() % pool.size()];
        }
        check_extrema_case(values);
        check_pivot_case(values, score);
    }
    // Every length>=2 constant segment has range zero. For pivot scores of -1,
    // the single segment is the best partition even on a long monotone input.
    vector<long long> many(100000, hi), scores(many.size(), -1);
    assert(partition_extrema_product_sum(many) == 0);
    iota(many.begin(), many.end(), -50000LL);
    assert(partition_minimum_pivot_max_score(many, scores) == -1);
    reverse(many.begin(), many.end());
    assert(partition_minimum_pivot_max_score(many, scores) == -1);
    bool rejected = false;
    try { (void)partition_minimum_pivot_max_score({0}, {}); }
    catch (const invalid_argument&) { rejected = true; }
    assert(rejected);
    cout << "partition-extrema-weighted-sum PASS: all small partitions, repeated extrema, signed endpoints and modular differences\n";
    cout << "partition-minimum-pivot-max-score PASS: all small partitions, distinct height permutations, rightmost ties and 128-bit negative scores\n";
}

map<vector<int>, long long> removal_cache;

long long all_removal_orders(const vector<int>& colors) {
    if (colors.empty()) return 0;
    if (auto found = removal_cache.find(colors); found != removal_cache.end()) return found->second;
    long long best = 0;
    // Try every currently contiguous equal-color interval, including proper
    // subintervals of a run. No carried group, interval split, or compressed
    // three-dimensional state is used by this oracle.
    for (int left = 0; left < int(colors.size()); ++left) {
        for (int right = left; right < int(colors.size()) && colors[right] == colors[left]; ++right) {
            vector<int> remaining;
            remaining.insert(remaining.end(), colors.begin(), colors.begin() + left);
            remaining.insert(remaining.end(), colors.begin() + right + 1, colors.end());
            long long length = right - left + 1;
            best = max(best, length * length + all_removal_orders(remaining));
        }
    }
    return removal_cache[colors] = best;
}

void check_removal_case(const vector<int>& colors) {
    const auto before = colors;
    assert(max_equal_run_square_score(colors) == all_removal_orders(colors));
    assert(colors == before);
}

void check_carried_group(mt19937& rng) {
    for (int n = 0, power = 1; n <= 7; ++n, power *= 3) {
        for (int encoding = 0; encoding < power; ++encoding) {
            vector<int> colors(n);
            int digits = encoding;
            for (auto& value : colors) { value = digits % 3; digits /= 3; }
            check_removal_case(colors);
        }
    }
    for (const auto& colors : vector<vector<int>>{
            {1,3,2,2,2,3,4,3,1}, {0,1,0}, {1,1,2,2,1,1},
            {INT_MIN,INT_MAX,INT_MIN,INT_MAX,INT_MIN}, {0,-1,0,1,0,-1,0}})
        check_removal_case(colors);
    assert(max_equal_run_square_score({1,3,2,2,2,3,4,3,1}) == 23);
    for (int trial = 0; trial < 260; ++trial) {
        vector<int> colors(rng() % 11);
        for (auto& value : colors) value = int(rng() % 4) - 2;
        check_removal_case(colors);
    }
    vector<int> same(100, INT_MIN), distinct(100);
    iota(distinct.begin(), distinct.end(), 10000);
    assert(max_equal_run_square_score(same) == 10000);
    assert(max_equal_run_square_score(distinct) == 100);
    bool rejected = false;
    try { (void)max_equal_run_square_score(vector<int>(101, 0)); }
    catch (const length_error&) { rejected = true; }
    assert(rejected);
    cout << "interval-removal-carried-group PASS: every removable same-color interval and order, delayed merges, arbitrary colors and length boundaries\n";
}

void check_permutation_rank() {
    const vector<int> moduli{1, 2, 97, 998244353, INT_MAX};
    for (int n = 1; n <= 8; ++n) {
        const int m = n - 1;
        vector<long long> counts(1 << m);
        vector<int> permutation(n);
        iota(permutation.begin(), permutation.end(), 0);
        // Classify actual permutations by their adjacent comparison pattern.
        // This does not use a last rank, row prefix sums, or a recurrence.
        do {
            unsigned signs = 0;
            for (int i = 0; i < m; ++i)
                if (permutation[i] > permutation[i + 1]) signs |= 1U << i;
            ++counts[signs];
        } while (next_permutation(permutation.begin(), permutation.end()));
        int patterns = 1;
        for (int i = 0; i < m; ++i) patterns *= 3;
        for (int encoding = 0; encoding < patterns; ++encoding) {
            int digits = encoding;
            string comparisons;
            for (int i = 0; i < m; ++i) {
                comparisons += "<>?"[digits % 3];
                digits /= 3;
            }
            long long expected = 0;
            for (unsigned signs = 0; signs < counts.size(); ++signs) {
                bool matches = true;
                for (int i = 0; i < m; ++i) {
                    if (comparisons[i] != '?' && (comparisons[i] == '>') != bool((signs >> i) & 1U)) {
                        matches = false;
                        break;
                    }
                }
                if (matches) expected += counts[signs];
            }
            for (int modulus : moduli)
                assert(count_inequality_permutations(comparisons, modulus) == expected % modulus);
        }
    }
    for (int modulus : moduli) {
        assert(count_inequality_permutations(string(300, '<'), modulus) == 1 % modulus);
        assert(count_inequality_permutations(string(300, '>'), modulus) == 1 % modulus);
        long long factorial = 1 % modulus;
        for (int i = 1; i <= 301; ++i) factorial = factorial * i % modulus;
        assert(count_inequality_permutations(string(300, '?'), modulus) == factorial);
    }
    for (const string invalid : {"=", "<x>", "D", "? ?"}) {
        bool rejected = false;
        try { (void)count_inequality_permutations(invalid); }
        catch (const invalid_argument&) { rejected = true; }
        assert(rejected);
    }
    for (int invalid_modulus : {0, -1, INT_MIN}) {
        bool rejected = false;
        try { (void)count_inequality_permutations("<>", invalid_modulus); }
        catch (const invalid_argument&) { rejected = true; }
        assert(rejected);
    }
    assert(count_inequality_permutations(string(4999, '<'), INT_MAX) == 1);
    bool rejected = false;
    try { (void)count_inequality_permutations(string(5000, '<')); }
    catch (const length_error&) { rejected = true; }
    assert(rejected);
    cout << "permutation-inequality-last-rank PASS: all permutations through eight elements, every wildcard pattern, small/composite moduli and factorial boundaries\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261020);
    check_lis(rng);
    check_partition_dp(rng);
    check_carried_group(rng);
    check_permutation_rank();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-dp-expansion-cpp-") as directory:
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
        result = subprocess.run([str(executable)], cwd=directory, timeout=120)
        if result.returncode:
            return result.returncode
        print("All 6 DP expansion implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
