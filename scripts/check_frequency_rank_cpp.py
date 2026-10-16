#!/usr/bin/env python3
"""Check the six published substring, rank and frequency implementations."""

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
    "eertree-palindrome-length-frequency",
    "shortest-common-unique-substring",
    "top-k-bounded-subarray-sums",
    "kth-signed-pair-product",
    "digit-sum-divides-value",
    "pair-floor-ratio-frequency",
)


def extracted_source():
    """Compile the article fences, rather than a copied implementation."""
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
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace std;

using article_eertree_palindrome_length_frequency::maximum_palindrome_length_frequency;
using article_shortest_common_unique_substring::shortest_common_unique_substring_length;
using article_top_k_bounded_subarray_sums::top_k_bounded_subarray_sums;
using article_kth_signed_pair_product::kth_signed_pair_product;
using article_digit_sum_divides_value::count_digit_sum_divisible;
using article_pair_floor_ratio_frequency::sum_floor_pair_ratios;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

vector<string> words(int alphabet, int maximum_length) {
    vector<string> all(1);
    size_t begin = 0, end = 1;
    for (int length = 1; length <= maximum_length; ++length) {
        const size_t old_end = end;
        for (size_t i = begin; i < end; ++i) {
            const string prefix = all[i];
            for (int c = 0; c < alphabet; ++c)
                all.push_back(prefix + char('a' + c));
        }
        begin = old_end;
        end = all.size();
    }
    return all;
}

map<string, int> literal_substrings(const string& text) {
    map<string, int> occurrences;
    for (size_t left = 0; left < text.size(); ++left)
        for (size_t length = 1; left + length <= text.size(); ++length)
            ++occurrences[text.substr(left, length)];
    return occurrences;
}

long long literal_palindrome_score(const string& text) {
    long long answer = 0;
    for (const auto& [part, count] : literal_substrings(text)) {
        string reversed = part;
        reverse(reversed.begin(), reversed.end());
        if (part == reversed)
            answer = max(answer, (long long)part.size() * count);
    }
    return answer;
}

void check_palindrome_score(mt19937& rng) {
    for (const string& text : words(2, 11))
        assert(maximum_palindrome_length_frequency(text) == literal_palindrome_score(text));
    for (int trial = 0; trial < 700; ++trial) {
        string text(rng() % 55, 'a');
        for (char& c : text) c += rng() % 5;
        assert(maximum_palindrome_length_frequency(text) == literal_palindrome_score(text));
    }
    assert(maximum_palindrome_length_frequency("aaaa") == 6);
    const int n = 1000000;
    const long long repeated = (long long)(n + 1) * (n + 1) / 4;
    assert(maximum_palindrome_length_frequency(string(n, 'a')) == repeated);
    string alternating(n, 'a');
    for (int i = 1; i < n; i += 2) alternating[i] = 'b';
    long long alternating_expected = 0;
    // Every odd-length interval is a palindrome, and its starting parity
    // determines which of the two distinct words it spells.
    for (int length = 1; length <= n; length += 2)
        alternating_expected = max(alternating_expected,
            (long long)length * ((n - length + 2) / 2));
    assert(maximum_palindrome_length_frequency(alternating) == alternating_expected);
    require_exception<invalid_argument>([] { (void)maximum_palindrome_length_frequency("Aa"); });
    require_exception<invalid_argument>([] { (void)maximum_palindrome_length_frequency("a{"); });
    require_exception<invalid_argument>([] {
        (void)maximum_palindrome_length_frequency(string(1, char(255)));
    });
    require_exception<length_error>([] {
        (void)maximum_palindrome_length_frequency(string(1000001, 'a'));
    });
    cout << "eertree-palindrome-length-frequency PASS: literal substring maps, overlapping occurrences, all binary strings and million-character repeated/alternating boundaries\n";
}

int literal_common_unique(const map<string, int>& first,
                          const map<string, int>& second) {
    int answer = INT_MAX;
    for (const auto& [part, count] : first) if (count == 1) {
        auto found = second.find(part);
        if (found != second.end() && found->second == 1)
            answer = min(answer, (int)part.size());
    }
    return answer == INT_MAX ? -1 : answer;
}

void check_common_unique(mt19937& rng) {
    const auto all = words(2, 6);
    vector<map<string, int>> occurrences;
    for (const auto& text : all) occurrences.push_back(literal_substrings(text));
    for (size_t i = 0; i < all.size(); ++i)
        for (size_t j = 0; j < all.size(); ++j)
            assert(shortest_common_unique_substring_length(all[i], all[j])
                   == literal_common_unique(occurrences[i], occurrences[j]));
    for (int trial = 0; trial < 1200; ++trial) {
        string first(rng() % 35, 'a'), second(rng() % 35, 'a');
        for (char& c : first) c += rng() % 4;
        for (char& c : second) c += rng() % 4;
        assert(shortest_common_unique_substring_length(first, second)
               == literal_common_unique(literal_substrings(first), literal_substrings(second)));
    }
    assert(shortest_common_unique_substring_length("aaaa", "aaaa") == 4);
    assert(shortest_common_unique_substring_length("aaaa", "aaa") == -1);
    assert(shortest_common_unique_substring_length("ab", "ba") == 1);
    const string repeated(100000, 'a');
    assert(shortest_common_unique_substring_length(repeated, repeated) == 100000);
    string changed = repeated;
    changed.back() = 'b';
    assert(shortest_common_unique_substring_length(repeated, changed) == -1);
    assert(shortest_common_unique_substring_length(repeated, string(100000, 'b')) == -1);
    // Contract validation precedes the empty-string no-solution shortcut.
    require_exception<invalid_argument>([] { (void)shortest_common_unique_substring_length("", "A"); });
    require_exception<invalid_argument>([] { (void)shortest_common_unique_substring_length("A", ""); });
    require_exception<invalid_argument>([] {
        (void)shortest_common_unique_substring_length("a", string(1, char(255)));
    });
    require_exception<length_error>([] {
        (void)shortest_common_unique_substring_length(string(100001, 'a'), string(100000, 'a'));
    });
    require_exception<length_error>([] {
        (void)shortest_common_unique_substring_length("", string(200001, 'a'));
    });
    cout << "shortest-common-unique-substring PASS: literal maps for every pair of small binary strings, exact uniqueness, no-solution cases and full combined-length boundaries\n";
}

vector<__int128> literal_subarray_sums(const vector<long long>& values, int low, int high) {
    vector<__int128> sums;
    for (int left = 0; left < (int)values.size(); ++left) {
        __int128 sum = 0;
        for (int right = left; right < (int)values.size(); ++right) {
            sum += values[right];
            const int length = right - left + 1;
            if (low <= length && length <= high) sums.push_back(sum);
        }
    }
    sort(sums.begin(), sums.end(), greater<__int128>());
    return sums;
}

void check_top_k_case(const vector<long long>& values, int low, int high, bool all_k,
                      mt19937& rng) {
    const auto expected = literal_subarray_sums(values, low, high);
    const auto before = values;
    vector<int> ranks;
    if (all_k) {
        for (int k = 0; k <= (int)expected.size(); ++k) ranks.push_back(k);
    } else {
        ranks = {0, (int)expected.size(), (int)(rng() % (expected.size() + 1))};
    }
    for (int k : ranks) {
        const auto actual = top_k_bounded_subarray_sums(values, low, high, k);
        const vector<__int128> expected_prefix(expected.begin(), expected.begin() + k);
        const __int128 expected_sum = accumulate(expected_prefix.begin(), expected_prefix.end(), (__int128)0);
        assert(actual.sums == expected_prefix);
        assert(actual.total == expected_sum);
        assert(values == before);
    }
}

void check_top_k(mt19937& rng) {
    const vector<long long> alphabet = {-2, 0, 3};
    for (int n = 1; n <= 6; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= int(alphabet.size());
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<long long> values(n);
            for (auto& value : values) { value = alphabet[code % 3]; code /= 3; }
            for (int low = 1; low <= n; ++low)
                for (int high = low; high <= n; ++high)
                    check_top_k_case(values, low, high, true, rng);
        }
    }
    const vector<long long> extreme = {LLONG_MIN, LLONG_MAX, LLONG_MIN, -1, 0, 1, LLONG_MAX};
    for (int low = 1; low <= (int)extreme.size(); ++low)
        for (int high = low; high <= (int)extreme.size(); ++high)
            check_top_k_case(extreme, low, high, true, rng);
    for (int trial = 0; trial < 500; ++trial) {
        int n = 1 + rng() % 13;
        vector<long long> values(n);
        for (auto& value : values) value = int(rng() % 101) - 50;
        int low = 1 + rng() % n, high = low + rng() % (n - low + 1);
        check_top_k_case(values, low, high, true, rng);
    }
    const int n = 500000;
    vector<long long> large(n, LLONG_MAX);
    auto actual = top_k_bounded_subarray_sums(large, 1, 1, n);
    assert(actual.sums.size() == (size_t)n);
    assert(all_of(actual.sums.begin(), actual.sums.end(), [](__int128 x) { return x == LLONG_MAX; }));
    assert(actual.total == (__int128)n * LLONG_MAX);
    actual = top_k_bounded_subarray_sums(large, n, n, 1);
    assert(actual.sums == vector<__int128>{(__int128)n * LLONG_MAX});
    assert(actual.total == (__int128)n * LLONG_MAX);
    fill(large.begin(), large.end(), LLONG_MIN);
    actual = top_k_bounded_subarray_sums(large, n, n, 1);
    assert(actual.sums == vector<__int128>{(__int128)n * LLONG_MIN});
    assert(actual.total == (__int128)n * LLONG_MIN);
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({}, 1, 1, 0); });
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({1}, 0, 1, 0); });
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({1}, 1, 2, 0); });
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({1, 2}, 2, 1, 0); });
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({1}, 1, 1, -1); });
    require_exception<invalid_argument>([] { (void)top_k_bounded_subarray_sums({1}, 1, 1, 2); });
    require_exception<invalid_argument>([] {
        (void)top_k_bounded_subarray_sums(vector<long long>(2000), 1, 2000, 500001);
    });
    require_exception<length_error>([] {
        (void)top_k_bounded_subarray_sums(vector<long long>(500001), 1, 1, 0);
    });
    cout << "top-k-bounded-subarray-sums PASS: all intervals sorted directly, every small rank, duplicate sums, signed 64-bit inputs and half-million-item output with 128-bit totals\n";
}

void check_product_case(const vector<long long>& values) {
    vector<__int128> expected;
    for (size_t i = 0; i < values.size(); ++i)
        for (size_t j = i + 1; j < values.size(); ++j)
            expected.push_back((__int128)values[i] * values[j]);
    sort(expected.begin(), expected.end());
    for (size_t rank = 0; rank < expected.size(); ++rank)
        assert(kth_signed_pair_product(values, (long long)rank + 1) == expected[rank]);
}

void product_arrays(const vector<long long>& alphabet, int maximum_length) {
    for (int n = 2; n <= maximum_length; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= int(alphabet.size());
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<long long> values(n);
            for (auto& value : values) {
                value = alphabet[code % alphabet.size()];
                code /= int(alphabet.size());
            }
            check_product_case(values);
        }
    }
}

void check_products(mt19937& rng) {
    product_arrays({-2, -1, 0, 1, 2}, 5);
    product_arrays({LLONG_MIN, LLONG_MIN + 1, -1000000000, -1, 0, 1,
                    1000000000, LLONG_MAX - 1, LLONG_MAX}, 4);
    for (int trial = 0; trial < 1000; ++trial) {
        vector<long long> values(2 + rng() % 12);
        for (auto& value : values) value = int(rng() % 101) - 50;
        check_product_case(values);
    }
    const int n = 200000, half = n / 2;
    const long long pairs = (long long)n * (n - 1) / 2;
    vector<long long> large(n, LLONG_MIN);
    const __int128 highest = (__int128)LLONG_MIN * LLONG_MIN;
    assert(kth_signed_pair_product(large, 1) == highest);
    assert(kth_signed_pair_product(large, pairs) == highest);
    fill(large.begin() + half, large.end(), LLONG_MAX);
    const long long negative_count = (long long)half * half;
    const long long low_positive_count = (long long)half * (half - 1) / 2;
    const __int128 lowest = (__int128)LLONG_MIN * LLONG_MAX;
    const __int128 low_positive = (__int128)LLONG_MAX * LLONG_MAX;
    for (long long rank : {1LL, negative_count})
        assert(kth_signed_pair_product(large, rank) == lowest);
    for (long long rank : {negative_count + 1, negative_count + low_positive_count})
        assert(kth_signed_pair_product(large, rank) == low_positive);
    assert(kth_signed_pair_product(large, negative_count + low_positive_count + 1) == highest);
    assert(kth_signed_pair_product(large, pairs) == highest);
    assert(kth_signed_pair_product(vector<long long>(n), pairs) == 0);
    require_exception<invalid_argument>([] { (void)kth_signed_pair_product({}, 1); });
    require_exception<invalid_argument>([] { (void)kth_signed_pair_product({1}, 1); });
    require_exception<invalid_argument>([] { (void)kth_signed_pair_product({1, 2}, 0); });
    require_exception<invalid_argument>([] { (void)kth_signed_pair_product({1, 2}, 2); });
    require_exception<length_error>([] {
        (void)kth_signed_pair_product(vector<long long>(200001), 1);
    });
    cout << "kth-signed-pair-product PASS: all unordered indexed pairs sorted directly, all small ranks, zeros/equalities, signed 64-bit extremes and ranks beyond 32 bits\n";
}

int decimal_digit_sum(long long value) {
    int sum = 0;
    while (value) { sum += int(value % 10); value /= 10; }
    return sum;
}

void check_digit_sum(mt19937& rng) {
    const int maximum = 1000000;
    vector<int> prefix(maximum + 1);
    for (int value = 1; value <= maximum; ++value)
        prefix[value] = prefix[value - 1] + (value % decimal_digit_sum(value) == 0);
    for (int upper = 0; upper <= 500; ++upper)
        assert(count_digit_sum_divisible(upper) == prefix[upper]);
    for (int trial = 0; trial < 150; ++trial) {
        int upper = rng() % (maximum + 1);
        assert(count_digit_sum_divisible(upper) == prefix[upper]);
    }
    for (int power = 1; power <= maximum; power *= 10) {
        assert(count_digit_sum_divisible(power) == prefix[power]);
        assert(count_digit_sum_divisible(power - 1) == prefix[power - 1]);
    }
    assert(count_digit_sum_divisible(9876543210LL) == 547452239);
    // Check the exact jump by testing the newly admitted integer directly,
    // including the full 15-digit boundary and a nontrivial 14-digit value.
    for (long long upper : {100000000000000LL, 99999999999999LL, 12345678901234LL}) {
        const auto current = count_digit_sum_divisible(upper);
        const auto previous = count_digit_sum_divisible(upper - 1);
        assert(current - previous == (upper % decimal_digit_sum(upper) == 0));
        assert(0 <= previous && previous <= current && current <= upper);
    }
    require_exception<invalid_argument>([] { (void)count_digit_sum_divisible(-1); });
    require_exception<invalid_argument>([] { (void)count_digit_sum_divisible(100000000000001LL); });
    require_exception<invalid_argument>([] { (void)count_digit_sum_divisible(LLONG_MAX); });
    cout << "digit-sum-divides-value PASS: independent direct integer divisibility counts, decimal boundaries, original large sample and exact single-integer jumps at 10^14\n";
}

long long literal_floor_ratios(const vector<int>& values) {
    long long answer = 0;
    for (size_t i = 0; i < values.size(); ++i)
        for (size_t j = i + 1; j < values.size(); ++j)
            answer += max(values[i], values[j]) / min(values[i], values[j]);
    return answer;
}

void check_floor_ratios(mt19937& rng) {
    for (int n = 0; n <= 6; ++n) {
        int patterns = 1;
        for (int i = 0; i < n; ++i) patterns *= 5;
        for (int pattern = 0; pattern < patterns; ++pattern) {
            int code = pattern;
            vector<int> values(n);
            for (int& value : values) { value = 1 + code % 5; code /= 5; }
            const auto before = values;
            assert(sum_floor_pair_ratios(values) == literal_floor_ratios(values));
            assert(values == before);
        }
    }
    for (int trial = 0; trial < 600; ++trial) {
        vector<int> values(rng() % 35);
        for (int& value : values) value = 1 + rng() % 10000;
        assert(sum_floor_pair_ratios(values) == literal_floor_ratios(values));
    }
    for (const auto& values : vector<vector<int>>{
            {1, 1000000}, {999999, 1000000}, {1, 1, 1000000, 1000000},
            {2, 3, 4, 5, 6, 7, 8, 9, 10, 999999, 1000000}})
        assert(sum_floor_pair_ratios(values) == literal_floor_ratios(values));
    const int n = 200000, half = n / 2;
    const long long pairs = (long long)n * (n - 1) / 2;
    assert(sum_floor_pair_ratios(vector<int>(n, 1)) == pairs);
    assert(sum_floor_pair_ratios(vector<int>(n, 1000000)) == pairs);
    vector<int> large(n, 1);
    fill(large.begin() + half, large.end(), 1000000);
    const long long expected = (long long)half * (half - 1)
                            + (long long)half * half * 1000000;
    assert(sum_floor_pair_ratios(large) == expected);
    require_exception<invalid_argument>([] { (void)sum_floor_pair_ratios({0}); });
    require_exception<invalid_argument>([] { (void)sum_floor_pair_ratios({-1}); });
    require_exception<invalid_argument>([] { (void)sum_floor_pair_ratios({1000001}); });
    require_exception<length_error>([] { (void)sum_floor_pair_ratios(vector<int>(200001, 1)); });
    cout << "pair-floor-ratio-frequency PASS: direct division for every indexed pair, exhaustive small arrays, equal-value corrections and maximum value/count boundaries\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261023);
    check_palindrome_score(rng);
    check_common_unique(rng);
    check_top_k(rng);
    check_products(rng);
    check_digit_sum(rng);
    check_floor_ratios(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-frequency-rank-cpp-") as directory:
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
        print("All 6 frequency and rank implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
