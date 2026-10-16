#!/usr/bin/env python3
"""Compare the published silhouette and independent letter rewrite C++ examples."""

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
    "row-column-maxima-height-matching",
    "independent-letter-rewrite-reachability",
)


def extracted_source():
    """Extract the exact complete fences; do not maintain a second implementation."""
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
#include <cassert>
#include <functional>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <unordered_set>
using namespace std;

using article_row_column_maxima_height_matching::minimize_height_with_fixed_silhouettes;
using article_independent_letter_rewrite_reachability::IndependentLetterRewrite;

template<class Function> void rejects(Function function) {
    bool caught = false;
    try { function(); } catch (const invalid_argument&) { caught = true; }
    assert(caught);
}

long long enumerate_legal_height_tables(const vector<vector<long long>>& input) {
    const int h = static_cast<int>(input.size());
    const int w = h == 0 ? 0 : static_cast<int>(input[0].size());
    vector<long long> expected_rows(h), expected_cols(w);
    vector<pair<int, int>> positive;
    for (int i = 0; i < h; ++i) for (int j = 0; j < w; ++j) {
        expected_rows[i] = max(expected_rows[i], input[i][j]);
        expected_cols[j] = max(expected_cols[j], input[i][j]);
        if (input[i][j] > 0) positive.emplace_back(i, j);
    }
    vector<vector<long long>> candidate(h, vector<long long>(w));
    long long best = numeric_limits<long long>::max();
    // Enumerate positive heights, including values above the original cell.
    // No matching, shared-witness formula or edge-cover theorem is used here.
    function<void(size_t)> visit = [&](size_t at) {
        if (at == positive.size()) {
            vector<long long> rows(h), cols(w);
            long long sum = 0;
            for (int i = 0; i < h; ++i) for (int j = 0; j < w; ++j) {
                assert((candidate[i][j] == 0) == (input[i][j] == 0));
                rows[i] = max(rows[i], candidate[i][j]);
                cols[j] = max(cols[j], candidate[i][j]);
                sum += candidate[i][j];
            }
            if (rows == expected_rows && cols == expected_cols) best = min(best, sum);
            return;
        }
        auto [i, j] = positive[at];
        for (long long height = 1; height <= min(expected_rows[i], expected_cols[j]); ++height) {
            candidate[i][j] = height;
            visit(at + 1);
        }
    };
    visit(0);
    assert(best != numeric_limits<long long>::max());
    return best;
}

void check_height_table(const vector<vector<long long>>& input) {
    const auto before = input;
    auto answer = minimize_height_with_fixed_silhouettes(input);
    const long long expected = enumerate_legal_height_tables(input);
    long long total = 0;
    for (const auto& row : input) total = accumulate(row.begin(), row.end(), total);
    assert(answer.minimum_remaining == expected);
    assert(answer.maximum_removed == total - expected);
    assert(answer.maximum_removed >= 0);
    assert(input == before);
}

void check_silhouettes() {
    for (int h = 1; h <= 3; ++h) for (int w = 1; w <= 3; ++w) {
        if (h * w > 6) continue;
        int cases = 1;
        for (int cell = 0; cell < h * w; ++cell) cases *= 4;
        for (int code = 0; code < cases; ++code) {
            int rest = code;
            vector<vector<long long>> input(h, vector<long long>(w));
            for (auto& row : input) for (auto& height : row) {
                height = rest % 4;
                rest /= 4;
            }
            check_height_table(input);
        }
    }
    mt19937 random(20170317);
    for (int trial = 0; trial < 300; ++trial) {
        vector<vector<long long>> input(3, vector<long long>(3));
        for (auto& row : input) for (auto& height : row) height = random() % 4;
        check_height_table(input);
    }
    check_height_table({{2,1,1},{2,0,0},{1,2,2}});
    assert(minimize_height_with_fixed_silhouettes({{2,1,1},{2,0,0},{1,2,2}})
        .minimum_remaining == 10);
    // Sparse support prevents matching all equal-height row and column demands.
    check_height_table({{3,0,0},{3,0,0},{0,3,3}});
    check_height_table({{1,0,1},{0,0,0},{1,1,0}});
    check_height_table({{3,2,1},{1,2,0}});
    auto sample = minimize_height_with_fixed_silhouettes({
        {1,4,0,5,2},{2,1,2,0,1},{0,2,3,4,4},{0,3,0,3,1},{1,2,2,1,1}});
    assert(sample.maximum_removed == 9);
    assert(minimize_height_with_fixed_silhouettes({{50,20,3},{20,10,3}})
        .maximum_removed == 30);
    check_height_table({});
    check_height_table({{}, {}, {}});
    check_height_table(vector<vector<long long>>(100));
    auto zero = minimize_height_with_fixed_silhouettes(vector<vector<long long>>(100, vector<long long>(100)));
    assert(zero.minimum_remaining == 0 && zero.maximum_removed == 0);
    auto ones = minimize_height_with_fixed_silhouettes(vector<vector<long long>>(100, vector<long long>(100, 1)));
    assert(ones.minimum_remaining == 10000 && ones.maximum_removed == 0);
    auto large = minimize_height_with_fixed_silhouettes(
        vector<vector<long long>>(100, vector<long long>(100, 1000000000LL)));
    const long long minimum = 10000LL + 100LL * (1000000000LL - 1);
    assert(large.minimum_remaining == minimum);
    assert(large.maximum_removed == 10000000000000LL - minimum);
    vector<vector<long long>> diagonal(100, vector<long long>(100));
    for (int i = 0; i < 100; ++i) diagonal[i][i] = 1000000000LL;
    auto sparse = minimize_height_with_fixed_silhouettes(diagonal);
    assert(sparse.minimum_remaining == 100000000000LL && sparse.maximum_removed == 0);
    rejects([] { minimize_height_with_fixed_silhouettes({{1},{1,2}}); });
    rejects([] { minimize_height_with_fixed_silhouettes({{}, {1}}); });
    rejects([] { minimize_height_with_fixed_silhouettes({{-1}}); });
    rejects([] { minimize_height_with_fixed_silhouettes({{1000000001LL}}); });
    rejects([] { minimize_height_with_fixed_silhouettes(vector<vector<long long>>(101)); });
    rejects([] { minimize_height_with_fixed_silhouettes({vector<long long>(101)}); });
    cout << "row-column-maxima-height-matching PASS: all 0..3 input tables with dimensions at most 3 and six cells, direct enumeration of every legal final height table, sparse support, raised cells, empty grids and 64-bit boundaries\n";
}

vector<string> words_of_length(int length) {
    vector<string> words{""};
    for (int i = 0; i < length; ++i) {
        vector<string> next;
        for (const auto& word : words) for (char c = 'a'; c <= 'c'; ++c)
            next.push_back(word + c);
        words.swap(next);
    }
    return words;
}

unordered_set<string> enumerate_rewrite_words(
    const string& start, const vector<pair<char,char>>& rules) {
    // Whole words are states. One edge rewrites exactly one chosen position.
    // This deliberately avoids a letter-graph reachability computation.
    unordered_set<string> seen{start};
    queue<string> pending;
    pending.push(start);
    while (!pending.empty()) {
        string word = pending.front();
        pending.pop();
        for (size_t i = 0; i < word.size(); ++i) for (auto [from,to] : rules) {
            if (word[i] != from) continue;
            string next = word;
            next[i] = to;
            if (seen.insert(next).second) pending.push(next);
        }
    }
    return seen;
}

void check_letter_rewrites() {
    for (int mask = 0; mask < (1 << 9); ++mask) {
        vector<pair<char,char>> rules;
        for (int a = 0; a < 3; ++a) for (int b = 0; b < 3; ++b)
            if (mask & (1 << (3 * a + b))) rules.emplace_back('a' + a, 'a' + b);
        const auto before = rules;
        const IndependentLetterRewrite solver(rules);
        for (int length = 0; length <= 3; ++length) {
            auto words = words_of_length(length);
            for (const string& from : words) {
                const auto seen = enumerate_rewrite_words(from, rules);
                for (const string& to : words)
                    assert(solver.can_transform(from, to) == seen.contains(to));
                assert(!solver.can_transform(from, from + 'a'));
            }
        }
        assert(rules == before);
    }
    const IndependentLetterRewrite no_rules({});
    assert(no_rules.can_transform("", ""));
    assert(no_rules.can_transform("abcdefghijklmnopqrstuvwxyz", "abcdefghijklmnopqrstuvwxyz"));
    assert(!no_rules.can_transform("a", "b"));
    assert(!no_rules.can_transform("", "a"));
    const IndependentLetterRewrite independent({{'a','b'}});
    assert(independent.can_transform("aa", "ab"));
    assert(!independent.can_transform("ab", "aa"));
    const IndependentLetterRewrite cycle({{'a','b'},{'b','a'},{'b','c'},{'a','b'},{'c','c'}});
    assert(cycle.can_transform("aab", "bac"));
    assert(!cycle.can_transform("c", "a"));
    const IndependentLetterRewrite sample({
        {'c','t'},{'i','r'},{'k','p'},{'o','c'},{'r','o'},
        {'t','e'},{'t','f'},{'u','h'},{'w','p'}});
    assert(sample.can_transform("we", "we"));
    assert(!sample.can_transform("can", "the"));
    assert(!sample.can_transform("work", "people"));
    assert(sample.can_transform("it", "of"));
    assert(sample.can_transform("out", "the"));
    vector<pair<char,char>> all_rules;
    for (char a = 'a'; a <= 'z'; ++a) for (char b = 'a'; b <= 'z'; ++b)
        all_rules.emplace_back(a, b);
    const IndependentLetterRewrite complete(all_rules);
    assert(complete.can_transform(string(200000, 'a'), string(200000, 'z')));
    vector<pair<char,char>> chain;
    for (char c = 'z'; c > 'a'; --c) chain.emplace_back(c - 1, c);
    const IndependentLetterRewrite directed_chain(chain);
    assert(directed_chain.can_transform(string(200000, 'a'), string(200000, 'z')));
    assert(!directed_chain.can_transform("z", "a"));
    const IndependentLetterRewrite repeated(vector<pair<char,char>>(676, {'a','a'}));
    assert(repeated.can_transform("a", "a"));
    rejects([] { IndependentLetterRewrite invalid(vector<pair<char,char>>(677, {'a','b'})); });
    rejects([] { IndependentLetterRewrite invalid({{'A','b'}}); });
    rejects([] { IndependentLetterRewrite invalid({{'a','?'}}); });
    for (const string& invalid : vector<string>{"A", "a0", "a b", string("a\0b", 3), string(1, char(255))}) {
        rejects([&] { no_rules.can_transform(invalid, "a"); });
        rejects([&] { no_rules.can_transform("", invalid); });
    }
    rejects([&] { no_rules.can_transform(string(200001, 'a'), ""); });
    rejects([&] { no_rules.can_transform("", string(200001, 'a')); });
    cout << "independent-letter-rewrite-reachability PASS: every directed rule subset on three letters, whole-word state BFS through length 3, independent positions, zero steps, cycles, reused queries, empty words and invalid contracts\n";
}

int main() {
    cout << unitbuf;
    check_silhouettes();
    check_letter_rewrites();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-silhouette-translation-") as directory:
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
        print("All 2 silhouette and translation implementations passed independent comparisons and contract checks.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
