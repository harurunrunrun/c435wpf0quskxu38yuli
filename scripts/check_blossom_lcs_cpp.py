#!/usr/bin/env python3
"""Compare the published general matching and bit-parallel LCS implementations."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SITE = Path(__file__).resolve().parent.parent
ARTICLES = ("general-matching-blossom-contraction", "lcs-bit-parallel-length")
FENCE = re.compile(r"^```cpp\s*\n(.*?)^```\s*$", re.M | re.S)


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
        examples.append("namespace article_" + slug.replace("-", "_")
                        + " {\n" + source + "\n}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <vector>
using namespace std;
using article_general_matching_blossom_contraction::maximum_general_matching;
using article_lcs_bit_parallel_length::bit_parallel_lcs_length;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

int subset_matching(int n, const vector<pair<int,int>>& edges) {
    vector<int> neighbors(n), memo(1 << n, -1);
    for (auto [u,v] : edges) if (u != v) {
        neighbors[u] |= 1 << v;
        neighbors[v] |= 1 << u;
    }
    function<int(int)> best = [&](int available) -> int {
        if (!available) return 0;
        int& result = memo[available];
        if (result != -1) return result;
        int u = countr_zero(static_cast<unsigned int>(available));
        int rest = available ^ (1 << u);
        result = best(rest);
        for (int choices = neighbors[u] & rest; choices; choices &= choices - 1) {
            int v = countr_zero(static_cast<unsigned int>(choices));
            result = max(result, 1 + best(rest ^ (1 << v)));
        }
        return result;
    };
    return best((1 << n) - 1);
}

void check_matching_case(int n, const vector<pair<int,int>>& edges, int expected = -1) {
    const auto before = edges;
    auto answer = maximum_general_matching(n, edges);
    if (expected == -1) expected = subset_matching(n, edges);
    assert(int(answer.size()) == expected);
    vector<int> used(n);
    set<pair<int,int>> allowed;
    for (auto [u,v] : edges) allowed.emplace(min(u,v),max(u,v));
    for (auto [u,v] : answer) {
        assert(0 <= u && u < v && v < n);
        assert(!used[u]++ && !used[v]++);
        assert(allowed.count({u,v}));
    }
    assert(edges == before);
}

void check_matching(mt19937& rng) {
    for (int n = 0; n <= 6; ++n) {
        vector<pair<int,int>> possible;
        for (int u = 0; u < n; ++u)
            for (int v = u + 1; v < n; ++v) possible.emplace_back(u,v);
        for (int mask = 0; mask < (1 << possible.size()); ++mask) {
            vector<pair<int,int>> edges;
            for (size_t i = 0; i < possible.size(); ++i)
                if (mask >> i & 1) edges.push_back(possible[i]);
            check_matching_case(n, edges);
        }
    }
    for (int repeat = 0; repeat < 1200; ++repeat) {
        int n = 7 + rng() % 12;
        vector<pair<int,int>> edges;
        unsigned int density = 10 + rng() % 81;
        for (int u = 0; u < n; ++u) {
            if (rng() % 2) edges.emplace_back(u,u);
            for (int v = u + 1; v < n; ++v) if (rng() % 100 < density) {
                edges.emplace_back(u,v);
                if (rng() % 4 == 0) edges.emplace_back(v,u);
            }
        }
        shuffle(edges.begin(), edges.end(), rng);
        check_matching_case(n, edges);
    }
    // This vertex order triggers a contraction containing an earlier contraction.
    check_matching_case(10, {
        {0,4},{1,2},{1,3},{1,5},{1,6},{2,8},{3,4},
        {3,6},{3,7},{4,6},{4,9},{5,6},{7,8}
    });
    // An odd cycle with two overlapping odd cycles, a stem and outside leaves.
    vector<pair<int,int>> flower = {
        {0,1},{1,2},{2,3},{3,4},{4,0},
        {2,5},{5,6},{6,2},{4,7},{7,8},{8,4},
        {0,9},{9,10},{6,11},{8,12},{11,13},{12,14},{13,14}
    };
    vector<int> label(15);
    iota(label.begin(), label.end(), 0);
    for (int repeat = 0; repeat < 300; ++repeat) {
        shuffle(label.begin(), label.end(), rng);
        vector<pair<int,int>> edges;
        for (auto [u,v] : flower) edges.emplace_back(label[u],label[v]);
        check_matching_case(15, edges);
    }
    vector<pair<int,int>> complete;
    for (int u = 0; u < 500; ++u)
        for (int v = u + 1; v < 500; ++v) complete.emplace_back(u,v);
    check_matching_case(500, complete, 250);
    check_matching_case(500, {}, 0);
    check_matching_case(500, vector<pair<int,int>>(200000, {0,499}), 1);
    vector<pair<int,int>> cycle;
    for (int i = 0; i < 499; ++i) cycle.emplace_back(i,(i+1)%499);
    check_matching_case(500, cycle, 249);
    require_exception<invalid_argument>([] { maximum_general_matching(-1, {}); });
    require_exception<invalid_argument>([] { maximum_general_matching(501, {}); });
    require_exception<invalid_argument>([] { maximum_general_matching(0, {{0,0}}); });
    require_exception<invalid_argument>([] { maximum_general_matching(2, {{-1,1}}); });
    require_exception<invalid_argument>([] { maximum_general_matching(2, {{0,2}}); });
    require_exception<invalid_argument>([] { maximum_general_matching(2, vector<pair<int,int>>(200001,{0,1})); });
    cout << "general-matching-blossom-contraction PASS: every simple graph through 6 vertices, independent subset DP through 18 vertices, nested/overlapping odd-cycle fixtures, loops, parallel edges and 500-vertex boundaries\n";
}

int table_lcs(const string& a, const string& b) {
    vector<vector<int>> dp(a.size()+1, vector<int>(b.size()+1));
    for (size_t i = 0; i < a.size(); ++i)
        for (size_t j = 0; j < b.size(); ++j)
            dp[i+1][j+1] = a[i] == b[j] ? dp[i][j]+1 : max(dp[i][j+1],dp[i+1][j]);
    return dp.back().back();
}

void check_lcs_case(const string& a, const string& b, int expected = -1) {
    const auto before_a = a, before_b = b;
    if (expected == -1) expected = table_lcs(a,b);
    assert(bit_parallel_lcs_length(a,b) == expected);
    assert(bit_parallel_lcs_length(b,a) == expected);
    assert(a == before_a && b == before_b);
}

void check_lcs(mt19937& rng) {
    vector<string> binary;
    for (int length = 0; length <= 8; ++length)
        for (int mask = 0; mask < (1 << length); ++mask) {
            string value;
            for (int i = 0; i < length; ++i) value.push_back('a' + (mask >> i & 1));
            binary.push_back(value);
        }
    for (size_t i = 0; i < binary.size(); ++i)
        for (size_t j = i; j < binary.size(); ++j) check_lcs_case(binary[i],binary[j]);
    vector<int> boundaries{0,1,2,62,63,64,65,66,126,127,128,129,130,191,192,193,255,256,257};
    for (int n : boundaries) for (int m : boundaries) {
        check_lcs_case(string(n,'a'),string(m,'a'),min(n,m));
        check_lcs_case(string(n,'a'),string(m,'b'),0);
        string a(n,'a'), b(m,'a');
        for (int i = 0; i < n; ++i) if (i % 7 == 0) a[i] = 'b';
        for (int j = 0; j < m; ++j) if (j % 11 == 0) b[j] = 'b';
        check_lcs_case(a,b);
    }
    string all_bytes;
    for (int c = 0; c < 256; ++c) all_bytes.push_back(static_cast<char>(c));
    check_lcs_case(all_bytes,all_bytes,256);
    string reverse_bytes = all_bytes;
    reverse(reverse_bytes.begin(),reverse_bytes.end());
    check_lcs_case(all_bytes,reverse_bytes,1);
    for (int repeat = 0; repeat < 800; ++repeat) {
        int n = rng() % 300, m = rng() % 300;
        string a(n,'\0'), b(m,'\0');
        int alphabet = repeat % 2 ? 256 : 3;
        for (char& c : a) c = static_cast<char>(rng() % alphabet);
        for (char& c : b) c = static_cast<char>(rng() % alphabet);
        check_lcs_case(a,b);
    }
    check_lcs_case(string(200000,'\0'),string(129,'\0'),129);
    // Full supported lengths exercise the complete multiword loop.
    assert(bit_parallel_lcs_length(string(200000,'x'),string(200000,'x')) == 200000);
    assert(bit_parallel_lcs_length(string(200000,'x'),{}) == 0);
    require_exception<invalid_argument>([] { bit_parallel_lcs_length(string(200001,'a'),{}); });
    require_exception<invalid_argument>([] { bit_parallel_lcs_length({},string(200001,'a')); });
    cout << "lcs-bit-parallel-length PASS: every binary-string pair through length 8 against full DP, 63/64/65 and 127/128/129-bit carry/borrow boundaries, all byte values and length 200000\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261026);
    check_matching(rng);
    check_lcs(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-blossom-lcs-cpp-") as directory:
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
        print("All 2 blossom and LCS implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
