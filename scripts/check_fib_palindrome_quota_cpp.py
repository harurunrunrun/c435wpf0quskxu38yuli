#!/usr/bin/env python3
"""Compare six published mask, quota, automaton, Fibonacci and palindrome examples."""

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
    "square-product-subsets-parity-mask",
    "xor-minimax-bit-partition",
    "grid-row-pick-reset",
    "wildcard-pattern-overlap-automaton",
    "fibonacci-range-sequence-lazy",
    "palindrome-adjacent-pair-inversions",
)


def extracted_source():
    """Compile the complete C++ fences that are actually published."""
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
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
using namespace std;

using article_square_product_subsets_parity_mask::count_square_product_subsets;
using article_xor_minimax_bit_partition::minimum_maximum_xor;
using article_grid_row_pick_reset::maximum_grid_value_row_quota;
using article_wildcard_pattern_overlap_automaton::maximum_wildcard_pattern_occurrences;
using article_fibonacci_range_sequence_lazy::FibonacciRangeAddSum;
using article_palindrome_adjacent_pair_inversions::minimum_adjacent_swaps_to_palindrome;

constexpr long long MOD = 1000000007;
constexpr long long FIB_MOD = 1000000009;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

long long power_mod(long long value, int exponent, long long modulus = MOD) {
    long long result = 1;
    for (; exponent; exponent >>= 1, value = value * value % modulus)
        if (exponent & 1) result = result * value % modulus;
    return result;
}

// Factoring is deliberately independent of the article's value-frequency DP.
unsigned square_kernel(int value) {
    unsigned result = 0;
    int prime_index = 0;
    for (int candidate = 2; candidate <= 70; ++candidate) {
        bool prime = true;
        for (int divisor = 2; divisor * divisor <= candidate; ++divisor)
            if (candidate % divisor == 0) prime = false;
        if (!prime) continue;
        while (value % candidate == 0) {
            result ^= 1U << prime_index;
            value /= candidate;
        }
        ++prime_index;
    }
    return result;
}

int literal_square_subsets(const vector<int>& values) {
    const int subsets = 1 << values.size();
    vector<unsigned> kernels(subsets);
    vector<unsigned> singles;
    for (int value : values) singles.push_back(square_kernel(value));
    int answer = 0;
    for (int subset = 1; subset < subsets; ++subset) {
        const int bit = __builtin_ctz(unsigned(subset));
        kernels[subset] = kernels[subset & (subset - 1)] ^ singles[bit];
        answer += kernels[subset] == 0;
    }
    return answer;
}

int independent_square_nullity(const vector<int>& values) {
    array<unsigned, 19> basis{};
    int rank = 0;
    for (int value : values) {
        unsigned kernel = square_kernel(value);
        for (int bit = 18; bit >= 0; --bit) if (kernel >> bit & 1U) {
            if (basis[bit]) kernel ^= basis[bit];
            else { basis[bit] = kernel; ++rank; break; }
        }
    }
    return int((power_mod(2, int(values.size()) - rank) + MOD - 1) % MOD);
}

void check_square_subsets(mt19937& rng) {
    assert(count_square_product_subsets({}) == 0);
    for (int value = 1; value <= 70; ++value)
        assert(count_square_product_subsets({value}) == literal_square_subsets({value}));
    for (int twos = 0; twos <= 4; ++twos)
        for (int threes = 0; threes <= 4; ++threes) {
            vector<int> values(twos, 2);
            values.insert(values.end(), threes, 3);
            values.push_back(6);
            values.push_back(1);
            values.push_back(4);
            assert(count_square_product_subsets(values) == literal_square_subsets(values));
        }
    for (int trial = 0; trial < 35; ++trial) {
        vector<int> values(1 + rng() % 18);
        for (int& value : values) value = 1 + rng() % 70;
        const auto before = values;
        assert(count_square_product_subsets(values) == literal_square_subsets(values));
        assert(values == before);
    }
    vector<int> many(100000, 1);
    assert(count_square_product_subsets(many) == int((power_mod(2, 100000) + MOD - 1) % MOD));
    fill(many.begin(), many.end(), 70);
    assert(count_square_product_subsets(many) == int((power_mod(2, 99999) + MOD - 1) % MOD));
    for (int i = 0; i < int(many.size()); ++i) many[i] = 1 + i % 70;
    assert(count_square_product_subsets(many) == independent_square_nullity(many));
    require_exception<invalid_argument>([] { (void)count_square_product_subsets(vector<int>(100001, 1)); });
    for (int bad : {INT_MIN, -1, 0, 71, INT_MAX})
        require_exception<invalid_argument>([&] { (void)count_square_product_subsets({1, bad}); });
    cout << "square-product-subsets-parity-mask PASS: all singleton values, duplicate multisets and literal subsets, independent linear nullity at 100000 elements and invalid inputs\n";
}

int literal_minimax_xor(const vector<int>& values, int limit) {
    int answer = INT_MAX;
    for (int x = 0; x < limit; ++x) {
        int worst = 0;
        for (int value : values) worst = max(worst, value ^ x);
        answer = min(answer, worst);
    }
    return answer;
}

void check_xor_minimax(mt19937& rng) {
    for (int n = 0; n <= 7; ++n) {
        vector<int> values(n);
        function<void(int, int)> enumerate = [&](int index, int least) {
            if (index == n) {
                assert(minimum_maximum_xor(values) == literal_minimax_xor(values, 8));
                return;
            }
            for (int value = least; value < 8; ++value) {
                values[index] = value;
                enumerate(index + 1, value);
            }
        };
        enumerate(0, 0);
    }
    for (int trial = 0; trial < 1000; ++trial) {
        vector<int> values(rng() % 25);
        for (int& value : values) value = rng() % 256;
        const int expected = literal_minimax_xor(values, 256);
        assert(minimum_maximum_xor(values) == expected);
        const int common_xor = int(rng() & ((1U << 30) - 1));
        for (int& value : values) value ^= common_xor;
        const auto before = values;
        assert(minimum_maximum_xor(values) == expected);
        assert(values == before);
    }
    vector<int> large(200000, (1 << 30) - 1);
    assert(minimum_maximum_xor(large) == 0);
    for (int i = 0; i < int(large.size()); i += 2) large[i] = 0;
    assert(minimum_maximum_xor(large) == (1 << 29));
    for (int& value : large) if (value) value = 1 << 29;
    assert(minimum_maximum_xor(large) == (1 << 29));
    require_exception<invalid_argument>([] { (void)minimum_maximum_xor(vector<int>(200001)); });
    for (int bad : {INT_MIN, -1, 1 << 30, INT_MAX})
        require_exception<invalid_argument>([&] { (void)minimum_maximum_xor({0, bad}); });
    cout << "xor-minimax-bit-partition PASS: every short multiset of 3-bit values and all candidate XORs, random common-XOR invariance, 30-bit/200000-element and invalid boundaries\n";
}

long long literal_grid_quota(const vector<vector<long long>>& values, int quota) {
    const int height = values.size(), width = height ? values[0].size() : 0;
    if (!height || !width) return 0;
    long long answer = 0;
    function<void(int, int, int, long long)> visit = [&](int row, int column, int used, long long sum) {
        for (int pick = 0; pick <= 1; ++pick) if (used + pick <= quota) {
            const long long next_sum = sum + pick * values[row][column];
            if (row + 1 == height && column + 1 == width) answer = max(answer, next_sum);
            if (column + 1 < width) visit(row, column + 1, used + pick, next_sum);
            if (row + 1 < height) visit(row + 1, column, 0, next_sum);
        }
    };
    visit(0, 0, 0, 0);
    return answer;
}

void check_grid_quota(mt19937& rng) {
    assert(maximum_grid_value_row_quota({}) == 0);
    assert(maximum_grid_value_row_quota({{}, {}, {}}) == 0);
    for (int height = 1; height <= 3; ++height)
        for (int width = 1; width <= 3; ++width)
            for (int mask = 0; mask < (1 << (height * width)); ++mask) {
                vector<vector<long long>> values(height, vector<long long>(width));
                for (int r = 0; r < height; ++r)
                    for (int c = 0; c < width; ++c) values[r][c] = mask >> (r * width + c) & 1;
                for (int quota = 0; quota <= 3; ++quota)
                    assert(maximum_grid_value_row_quota(values, quota) == literal_grid_quota(values, quota));
            }
    for (int trial = 0; trial < 300; ++trial) {
        const int height = 1 + rng() % 4, width = 1 + rng() % 4;
        vector<vector<long long>> values(height, vector<long long>(width));
        for (auto& row : values) for (long long& value : row) value = rng() % 100;
        const auto before = values;
        for (int quota = 0; quota <= 3; ++quota)
            assert(maximum_grid_value_row_quota(values, quota) == literal_grid_quota(values, quota));
        assert(values == before);
    }
    assert(maximum_grid_value_row_quota({vector<long long>(3000, 1000000000)}) == 3000000000LL);
    assert(maximum_grid_value_row_quota(vector<vector<long long>>(3000, {1000000000})) == 3000000000000LL);
    {
        const vector<vector<long long>> large(3000, vector<long long>(3000, 1000000000));
        assert(maximum_grid_value_row_quota(large) == 5999000000000LL);
    }
    for (int bad_quota : {-1, 4, INT_MAX})
        require_exception<invalid_argument>([&] { (void)maximum_grid_value_row_quota({}, bad_quota); });
    require_exception<invalid_argument>([] { (void)maximum_grid_value_row_quota(vector<vector<long long>>(3001)); });
    require_exception<invalid_argument>([] { (void)maximum_grid_value_row_quota({vector<long long>(3001)}); });
    for (const auto& values : vector<vector<vector<long long>>>{{{}, {1}}, {{1}, {}}, {{-1}}, {{1000000001}}, {{LLONG_MAX}}})
        require_exception<invalid_argument>([&] { (void)maximum_grid_value_row_quota(values, 0); });
    cout << "grid-row-pick-reset PASS: every binary grid through 3x3 and random path/pick enumerations for all quotas, row resets, 64-bit totals and a 3000x3000 boundary\n";
}

int literal_wildcard_occurrences(string text, const string& pattern) {
    string alphabet = pattern;
    sort(alphabet.begin(), alphabet.end());
    alphabet.erase(unique(alphabet.begin(), alphabet.end()), alphabet.end());
    for (char other = 'a'; other <= 'z'; ++other) if (alphabet.find(other) == string::npos) {
        alphabet += other;
        break;
    }
    vector<int> unknown;
    for (int i = 0; i < int(text.size()); ++i) if (text[i] == '?') unknown.push_back(i);
    int answer = 0;
    function<void(int)> enumerate = [&](int index) {
        if (index < int(unknown.size())) {
            for (char letter : alphabet) {
                text[unknown[index]] = letter;
                enumerate(index + 1);
            }
            return;
        }
        int count = 0;
        for (int start = 0; start + int(pattern.size()) <= int(text.size()); ++start)
            count += text.compare(start, pattern.size(), pattern) == 0;
        answer = max(answer, count);
    };
    enumerate(0);
    return answer;
}

void check_wildcard_automaton(mt19937& rng) {
    for (int length = 1; length <= 3; ++length)
        for (int bits = 0; bits < (1 << length); ++bits) {
            string pattern(length, 'a');
            for (int i = 0; i < length; ++i) pattern[i] += bits >> i & 1;
            for (int text_length = 0; text_length <= 5; ++text_length) {
                int possibilities = 1;
                for (int i = 0; i < text_length; ++i) possibilities *= 3;
                for (int code = 0; code < possibilities; ++code) {
                    int remaining = code;
                    string text(text_length, 'a');
                    for (char& letter : text) { letter = string("ab?")[remaining % 3]; remaining /= 3; }
                    assert(maximum_wildcard_pattern_occurrences(text, pattern) == literal_wildcard_occurrences(text, pattern));
                }
            }
        }
    for (int trial = 0; trial < 300; ++trial) {
        string text(rng() % 10, 'a'), pattern(1 + rng() % 6, 'a');
        int unknowns = 0;
        for (char& letter : text) {
            letter = string("abc?")[rng() % 4];
            if (letter == '?' && ++unknowns > 6) letter = 'c';
        }
        for (char& letter : pattern) letter = char('a' + rng() % 3);
        assert(maximum_wildcard_pattern_occurrences(text, pattern) == literal_wildcard_occurrences(text, pattern));
    }
    assert(maximum_wildcard_pattern_occurrences(string(100000, '?'), "a") == 100000);
    assert(maximum_wildcard_pattern_occurrences(string(100000, '?'), "ab") == 50000);
    assert(maximum_wildcard_pattern_occurrences(string(100000, 'a'), string(100, 'a')) == 99901);
    assert(maximum_wildcard_pattern_occurrences(string(100, '?'), string(100000, 'a')) == 0);
    assert(maximum_wildcard_pattern_occurrences("", string(100000, 'a')) == 0);
    for (const auto& [text, pattern] : vector<pair<string, string>>{
            {"", ""}, {"?", "?"}, {"A", "a"}, {"a!", "a"}, {"", "A"},
            {"", string(100001, 'a')}, {string(100001, 'a'), "a"},
            {string(1001, '?'), string(10000, 'a')}})
        require_exception<invalid_argument>([&] { (void)maximum_wildcard_pattern_occurrences(text, pattern); });
    cout << "wildcard-pattern-overlap-automaton PASS: complete short replacements and literal overlapping matches, unequal borders, 100000-character inputs and the 10000000 product boundary\n";
}

long long normalize_fib(long long value) {
    value %= FIB_MOD;
    if (value < 0) value += FIB_MOD;
    return value;
}

pair<long long, long long> independent_fibonacci_pair(int index) {
    if (index == 0) return {0, 1};
    const auto [a, b] = independent_fibonacci_pair(index / 2);
    const long long even = a * ((2 * b % FIB_MOD - a + FIB_MOD) % FIB_MOD) % FIB_MOD;
    const long long odd = (a * a + b * b) % FIB_MOD;
    return (index & 1) ? make_pair(odd, (even + odd) % FIB_MOD) : make_pair(even, odd);
}

long long fib_sum(int left, int right) {
    return (independent_fibonacci_pair(right + 2).first
            - independent_fibonacci_pair(left + 2).first + FIB_MOD) % FIB_MOD;
}

void check_fibonacci_ranges(mt19937& rng) {
    static_assert(FibonacciRangeAddSum::MOD == FIB_MOD);
    FibonacciRangeAddSum empty({});
    empty.add_fibonacci(0, 0);
    assert(empty.range_sum(0, 0) == 0);
    for (int trial = 0; trial < 200; ++trial) {
        const int n = rng() % 71;
        vector<long long> values(n);
        for (long long& value : values) {
            const int choice = rng() % 5;
            value = choice == 0 ? LLONG_MIN : choice == 1 ? LLONG_MAX
                    : (long long)(rng() % 2000000001) - 1000000000;
        }
        const auto before = values;
        FibonacciRangeAddSum structure(values);
        assert(values == before);
        for (long long& value : values) value = normalize_fib(value);
        for (int step = 0; step < 500; ++step) {
            int left = rng() % (n + 1), right = rng() % (n + 1);
            if (left > right) swap(left, right);
            if (rng() % 3) {
                structure.add_fibonacci(left, right);
                long long previous = 0, current = 1;
                for (int index = left; index < right; ++index) {
                    values[index] = (values[index] + current) % FIB_MOD;
                    const long long next = (previous + current) % FIB_MOD;
                    previous = current; current = next;
                }
            } else {
                long long expected = 0;
                for (int index = left; index < right; ++index) expected = (expected + values[index]) % FIB_MOD;
                assert(structure.range_sum(left, right) == expected);
            }
        }
        for (int left = 0; left <= n; ++left)
            for (int right = left; right <= n; ++right) {
                long long expected = 0;
                for (int index = left; index < right; ++index) expected = (expected + values[index]) % FIB_MOD;
                assert(structure.range_sum(left, right) == expected);
            }
    }
    const int n = 300000;
    FibonacciRangeAddSum large(vector<long long>(n, LLONG_MIN));
    for (int repeat = 0; repeat < 1000; ++repeat) large.add_fibonacci(0, n);
    vector<pair<int, int>> updates;
    for (int step = 0; step < 500; ++step) {
        int left = rng() % (n + 1), right = rng() % (n + 1);
        if (left > right) swap(left, right);
        large.add_fibonacci(left, right);
        updates.emplace_back(left, right);
    }
    vector<pair<int, int>> queries = {{0, n}, {0, 1}, {n - 1, n}, {n, n}, {12345, 287654}};
    for (int i = 0; i < 200; ++i) {
        const int left = rng() % n;
        queries.emplace_back(left, left + 1);
    }
    for (const auto& [left, right] : queries) {
        long long expected = (normalize_fib(LLONG_MIN) * (right - left) + 1000 * fib_sum(left, right)) % FIB_MOD;
        for (const auto& [start, finish] : updates) {
            const int lo = max(left, start), hi = min(right, finish);
            if (lo < hi) expected = (expected + fib_sum(lo - start, hi - start)) % FIB_MOD;
        }
        assert(large.range_sum(left, right) == expected);
    }
    require_exception<invalid_argument>([] { FibonacciRangeAddSum oversized(vector<long long>(300001)); });
    FibonacciRangeAddSum small({LLONG_MIN, LLONG_MAX});
    for (const auto& [left, right] : vector<pair<int, int>>{{-1, 0}, {0, 3}, {2, 1}, {3, 3}, {0, -1}}) {
        require_exception<out_of_range>([&] { small.add_fibonacci(left, right); });
        require_exception<out_of_range>([&] { (void)small.range_sum(left, right); });
    }
    require_exception<out_of_range>([&] { empty.add_fibonacci(0, 1); });
    require_exception<out_of_range>([&] { (void)empty.range_sum(-1, 0); });
    cout << "fibonacci-range-sequence-lazy PASS: literal overlapping updates and all short ranges, independent fast-doubling sums at 300000 elements, lazy composition, signed normalization and invalid ranges\n";
}

bool is_palindrome(const string& text) {
    return equal(text.begin(), text.begin() + text.size() / 2, text.rbegin());
}

long long independent_target_palindromes(const string& text) {
    array<int, 26> frequency{};
    for (char letter : text) ++frequency[letter - 'a'];
    string half, middle;
    for (int letter = 0; letter < 26; ++letter) {
        half.append(frequency[letter] / 2, char('a' + letter));
        if (frequency[letter] & 1) middle += char('a' + letter);
    }
    if (middle.size() > 1) return -1;
    long long answer = LLONG_MAX;
    do {
        string target = half + middle + string(half.rbegin(), half.rend());
        array<vector<int>, 26> original;
        for (int i = 0; i < int(text.size()); ++i) original[text[i] - 'a'].push_back(i);
        array<int, 26> used{};
        vector<int> order;
        for (char letter : target) order.push_back(original[letter - 'a'][used[letter - 'a']++]);
        long long inversions = 0;
        for (int i = 0; i < int(order.size()); ++i)
            for (int j = i + 1; j < int(order.size()); ++j) inversions += order[i] > order[j];
        answer = min(answer, inversions);
    } while (next_permutation(half.begin(), half.end()));
    return answer;
}

void check_palindrome_swaps(mt19937& rng) {
    for (int n = 0; n <= 8; ++n) {
        map<string, vector<string>> groups;
        int possibilities = 1;
        for (int i = 0; i < n; ++i) possibilities *= 3;
        for (int code = 0; code < possibilities; ++code) {
            int remaining = code;
            string text(n, 'a');
            for (char& letter : text) { letter += remaining % 3; remaining /= 3; }
            string key = text;
            sort(key.begin(), key.end());
            groups[key].push_back(text);
        }
        for (const auto& [key, texts] : groups) {
            (void)key;
            unordered_map<string, int> distance;
            queue<string> work;
            for (const string& text : texts) if (is_palindrome(text)) {
                distance.emplace(text, 0);
                work.push(text);
            }
            while (!work.empty()) {
                const string text = work.front(); work.pop();
                const int next_distance = distance.at(text) + 1;
                for (int i = 0; i + 1 < n; ++i) if (text[i] != text[i + 1]) {
                    string next = text;
                    swap(next[i], next[i + 1]);
                    if (distance.emplace(next, next_distance).second) work.push(next);
                }
            }
            for (const string& text : texts) {
                const long long expected = distance.empty() ? -1 : distance.at(text);
                assert(minimum_adjacent_swaps_to_palindrome(text) == expected);
                if (n <= 6) assert(independent_target_palindromes(text) == expected);
            }
        }
    }
    for (int trial = 0; trial < 250; ++trial) {
        string half(rng() % 8, 'a');
        for (char& letter : half) letter += rng() % 4;
        string text = half + string(half.rbegin(), half.rend());
        if (rng() & 1) text += char('a' + rng() % 4);
        shuffle(text.begin(), text.end(), rng);
        assert(minimum_adjacent_swaps_to_palindrome(text) == independent_target_palindromes(text));
    }
    assert(minimum_adjacent_swaps_to_palindrome(string(200000, 'z')) == 0);
    assert(minimum_adjacent_swaps_to_palindrome(string(100000, 'a') + string(100000, 'b')) == 5000000000LL);
    assert(minimum_adjacent_swaps_to_palindrome(string(199999, 'a') + "b") == -1);
    string half(100000, 'a');
    for (char& letter : half) letter += rng() % 26;
    assert(minimum_adjacent_swaps_to_palindrome(half + string(half.rbegin(), half.rend())) == 0);
    require_exception<invalid_argument>([] { (void)minimum_adjacent_swaps_to_palindrome(string(200001, 'a')); });
    for (const string& bad : vector<string>{"A", "a?", "a0", "a b", string("a\0b", 3)})
        require_exception<invalid_argument>([&] { (void)minimum_adjacent_swaps_to_palindrome(bad); });
    cout << "palindrome-adjacent-pair-inversions PASS: multisource adjacent-swap BFS for every ternary string through length 8, independent target-palindrome inversions, impossible parity and 200000-character/64-bit boundaries\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261026);
    check_square_subsets(rng);
    check_xor_minimax(rng);
    check_grid_quota(rng);
    check_wildcard_automaton(rng);
    check_fibonacci_ranges(rng);
    check_palindrome_swaps(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-fib-palindrome-quota-cpp-") as directory:
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
        result = subprocess.run([str(executable)], cwd=directory, timeout=240)
        if result.returncode:
            return result.returncode
        print("All 6 mask, quota, automaton, Fibonacci and palindrome implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
