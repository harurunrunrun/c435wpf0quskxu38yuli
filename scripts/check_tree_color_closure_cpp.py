#!/usr/bin/env python3
"""Compile the article's C++20 and compare it with induced-set connectivity.

Run independently:
  python3 /tmp/flowchartcp-capital-closure-checker.py
  python3 /tmp/flowchartcp-capital-closure-checker.py --sanitize
An optional positional argument selects a relocated article.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

TESTS = r'''
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <string>

using std::pair;
using std::vector;
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}

// No paths, hulls, SCCs or dependency graph: test each original-color subset.
bool connected_union(int k, const vector<int>& colors,
                     const vector<pair<int,int>>& edges, const vector<int>& selected) {
    const int n = static_cast<int>(colors.size());
    vector<char> wanted(k), seen(n);
    for (int c : selected) {
        require(c >= 0 && c < k && !wanted[c], "invalid witness color");
        wanted[c] = true;
    }
    vector<vector<int>> adjacency(n);
    for (auto [u,v] : edges) { adjacency[u].push_back(v); adjacency[v].push_back(u); }
    int start = -1, total = 0;
    for (int v = 0; v < n; ++v) if (wanted[colors[v]]) { start = v; ++total; }
    if (start == -1) return false;
    vector<int> queue{start}; seen[start] = true;
    for (std::size_t i = 0; i < queue.size(); ++i)
        for (int u : adjacency[queue[i]]) if (wanted[colors[u]] && !seen[u]) {
            seen[u] = true; queue.push_back(u);
        }
    return static_cast<int>(queue.size()) == total;
}
int oracle(int k, const vector<int>& colors, const vector<pair<int,int>>& edges) {
    int best = k - 1;
    for (unsigned int mask = 1; mask < (1U << k); ++mask) {
        int cost = std::popcount(mask) - 1;
        vector<int> selected;
        for (int c = 0; c < k; ++c) if ((mask >> c) & 1U) selected.push_back(c);
        if (connected_union(k, colors, edges, selected)) best = std::min(best, cost);
    }
    return best;
}
void compare(int k, const vector<int>& colors, const vector<pair<int,int>>& edges,
             int expected = -1) {
    const auto original_colors = colors;
    const auto original_edges = edges;
    auto actual = minimum_connected_color_merges(k, colors, edges);
    if (expected < 0) expected = oracle(k, colors, edges);
    require(actual.operations == expected, "minimum merge count differs from oracle");
    require(static_cast<int>(actual.colors.size()) == actual.operations + 1, "wrong witness size");
    require(connected_union(k, colors, edges, actual.colors), "witness union is disconnected");
    require(colors == original_colors && edges == original_edges, "input was modified");
}
int power(int a, int exponent) {
    int value = 1;
    while (exponent-- > 0) value *= a;
    return value;
}
vector<pair<int,int>> prufer_tree(int n, int encoded) {
    if (n == 1) return {};
    vector<int> sequence(n - 2), degree(n, 1);
    for (int& v : sequence) { v = encoded % n; encoded /= n; ++degree[v]; }
    vector<pair<int,int>> edges;
    for (int v : sequence) {
        int leaf = 0;
        while (degree[leaf] != 1) ++leaf;
        edges.emplace_back(leaf, v); --degree[leaf]; --degree[v];
    }
    int a = -1, b = -1;
    for (int v = 0; v < n; ++v) if (degree[v] == 1) { if (a == -1) a = v; else b = v; }
    edges.emplace_back(a, b);
    return edges;
}
template<class F> void rejects(F operation) {
    bool rejected = false;
    try { operation(); } catch (const std::invalid_argument&) { rejected = true; }
    require(rejected, "invalid input was accepted");
}
int main(int argc, char**) {
    const bool quick = argc > 1;
    std::uint64_t exhaustive = 0;
    for (int n = 1; n <= (quick ? 4 : 5); ++n) {
        int tree_count = n <= 2 ? 1 : power(n, n - 2);
        for (int encoded_tree = 0; encoded_tree < tree_count; ++encoded_tree) {
            auto edges = prufer_tree(n, encoded_tree);
            for (int k = 1; k <= n; ++k)
                for (int encoded_colors = 0; encoded_colors < power(k, n); ++encoded_colors) {
                    int value = encoded_colors;
                    vector<int> colors(n), frequency(k);
                    for (int& c : colors) { c = value % k; value /= k; ++frequency[c]; }
                    if (std::find(frequency.begin(), frequency.end(), 0) != frequency.end()) continue;
                    compare(k, colors, edges); ++exhaustive;
                }
        }
    }
    // Also enumerate every six-vertex labeled tree and every set partition.
    // Restricted-growth labels represent all color assignments up to renaming.
    std::uint64_t canonical = 0;
    if (!quick) {
        const int n = 6;
        for (int code = 0; code < power(n, n - 2); ++code) {
            auto edges = prufer_tree(n, code);
            vector<int> colors(n, 0);
            auto enumerate = [&](auto&& self, int position, int maximum) -> void {
                if (position == n) {
                    compare(maximum + 1, colors, edges); ++canonical; return;
                }
                for (int c = 0; c <= maximum + 1; ++c) {
                    colors[position] = c;
                    self(self, position + 1, std::max(maximum, c));
                }
            };
            enumerate(enumerate, 1, 0);
        }
    }
    std::mt19937 random(20201023);
    const int trials = quick ? 400 : 6000;
    for (int trial = 0; trial < trials; ++trial) {
        int n = 1 + static_cast<int>(random() % 11U);
        int k = 1 + static_cast<int>(random() % static_cast<unsigned int>(std::min(n, 7)));
        vector<int> colors(n), permutation(n);
        std::iota(permutation.begin(), permutation.end(), 0);
        std::shuffle(permutation.begin(), permutation.end(), random);
        for (int i = 0; i < n; ++i) colors[i] = i < k ? i : static_cast<int>(random() % static_cast<unsigned int>(k));
        std::shuffle(colors.begin(), colors.end(), random);
        vector<pair<int,int>> edges;
        for (int i = 1; i < n; ++i)
            edges.emplace_back(permutation[i], permutation[random() % static_cast<unsigned int>(i)]);
        std::shuffle(edges.begin(), edges.end(), random);
        compare(k, colors, edges);
    }
    // A→B with B already connected, mutual forcing, and two unrelated sinks.
    compare(2, {0,1,0}, {{0,1},{1,2}}, 0);
    compare(2, {0,1,0,1}, {{0,1},{1,2},{2,3}}, 1);
    compare(3, {0,1,0,2,2}, {{0,1},{1,2},{2,3},{3,4}}, 0);
    compare(3, {0,1,2,0,1,2}, {{0,1},{1,2},{2,3},{3,4},{4,5}}, 2);
    // Three examples from the official source, converted to zero-based IDs.
    compare(3, {0,2,0,1,2,1}, {{1,0},{2,4},{5,1},{2,3},{1,2}}, 1);
    compare(4, {1,3,2,0,0,1,2,3}, {{3,0},{0,2},{2,5},{5,6},{6,1},{1,4},{4,7}}, 1);
    compare(4, {2,0,0,1,3,2,2,1,1,2,3,3},
            {{6,8},{0,2},{3,5},{1,3},{9,11},{0,1},{1,9},{10,0},{1,7},{4,2},{5,6}}, 2);
    rejects([] { minimum_connected_color_merges(1, {}, {}); });
    rejects([] { minimum_connected_color_merges(1, vector<int>(200001, 0), {}); });
    rejects([] { minimum_connected_color_merges(0, {0}, {}); });
    rejects([] { minimum_connected_color_merges(2, {0}, {}); });
    rejects([] { minimum_connected_color_merges(1, {-1}, {}); });
    rejects([] { minimum_connected_color_merges(1, {1}, {}); });
    rejects([] { minimum_connected_color_merges(2, {0,0}, {{0,1}}); });
    rejects([] { minimum_connected_color_merges(1, {0,0}, {}); });
    rejects([] { minimum_connected_color_merges(1, {0,0}, {{-1,1}}); });
    rejects([] { minimum_connected_color_merges(1, {0,0}, {{0,2}}); });
    rejects([] { minimum_connected_color_merges(1, {0,0}, {{0,0}}); });
    rejects([] { minimum_connected_color_merges(1, {0,0,0}, {{0,1},{0,1}}); });
    rejects([] { minimum_connected_color_merges(1, {0,0,0,0}, {{0,1},{1,2},{2,0}}); });

    const int n = quick ? 2000 : 200000;
    auto large = [&](const char* label, int k, const vector<int>& colors,
                     const vector<pair<int,int>>& edges, int expected) {
        auto started = std::chrono::steady_clock::now();
        compare(k, colors, edges, expected);
        auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        std::cout << "LARGE " << label << " n=" << n << " seconds=" << elapsed << '\n';
    };
    vector<pair<int,int>> edges;
    for (int i = 1; i < n; ++i) edges.emplace_back(i - 1, i);
    vector<int> colors(n, 0);
    large("deep-one-color", 1, colors, edges, 0);
    std::iota(colors.begin(), colors.end(), 0);
    large("deep-all-distinct", n, colors, edges, 0);
    for (int i = 0; i < n; ++i) colors[i] = i % 2;
    large("deep-alternating", 2, colors, edges, 1);
    for (int i = 0; i < n; ++i) colors[i] = i % (n / 2);
    large("deep-interleaved-pairs", n / 2, colors, edges, n / 2 - 1);
    edges.clear();
    for (int i = 1; i < n; ++i) edges.emplace_back(0, i);
    std::fill(colors.begin(), colors.end(), 1); colors[0] = 0;
    large("star-singleton-center", 2, colors, edges, 0);
    edges.clear();
    vector<int> depth(n);
    int depth_colors = quick ? 4 : 8;
    for (int i = 1; i < n; ++i) {
        int p = (i - 1) / 2; edges.emplace_back(p, i); depth[i] = depth[p] + 1;
    }
    for (int i = 0; i < n; ++i) colors[i] = depth[i] % depth_colors;
    large("balanced-repeated-depths", depth_colors, colors, edges, depth_colors - 1);
    colors[0] = 0;
    for (int i = 1; i < n; ++i) colors[i] = 1 + (i - 1) % (n / 2 - 1);
    std::shuffle(colors.begin() + 1, colors.end(), random);
    large("balanced-random-pairs-singleton-root", n / 2, colors, edges, 0);
    edges.clear();
    for (int i = 1; i < n; ++i) edges.emplace_back(i < n / 2 ? i - 1 : n / 2 - 1, i);
    for (int i = 0; i < n; ++i) colors[i] = i % 3;
    large("broom", 3, colors, edges, 2);
    std::cout << "PASS: tree-color-closure-sink-scc; " << exhaustive
              << " exhaustive labeled-tree/surjective-color cases, " << canonical
              << " six-vertex tree/partition cases, " << trials
              << " random cases, 3 official examples, 13 invalid inputs, 8 large cases.\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article', nargs='?', type=Path,
                        default=Path(__file__).resolve().parent.parent / 'src/content/docs/techniques/tree-color-closure-sink-scc.mdx')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--measure', action='store_true', help='Measure C++ execution peak RSS with /usr/bin/time')
    args = parser.parse_args()
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', args.article.read_text(), re.M | re.S)
    if len(fences) != 1:
        raise ValueError('Expected one complete published C++ implementation')
    headings = re.findall(r'^## (.+)$', args.article.read_text(), re.M)
    if headings != ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']:
        raise ValueError('The article must have the established eight sections')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-capital-closure-') as directory:
        source = Path(directory) / 'test.cpp'
        binary = Path(directory) / 'test'
        source.write_text(fences[0] + TESTS)
        flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic-errors']
        if args.sanitize:
            flags += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run([compiler, *flags, str(source), '-o', str(binary)], check=True, timeout=90)
        started = time.monotonic()
        command = [str(binary), 'quick'] if args.sanitize else [str(binary)]
        if args.measure:
            command = ['/usr/bin/time', '-f', 'PEAK_RSS_KIB=%M', *command]
        environment = os.environ.copy()
        if args.sanitize:
            # LeakSanitizer cannot inspect threads under this sandbox's ptrace.
            environment['ASAN_OPTIONS'] = environment.get('ASAN_OPTIONS', '') + ':detect_leaks=0'
        subprocess.run(command, check=True, timeout=180, env=environment)
        print(f'CHECKER seconds={time.monotonic()-started:.3f} sanitizer={args.sanitize}', flush=True)


if __name__ == '__main__':
    main()
