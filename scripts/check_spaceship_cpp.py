#!/usr/bin/env python3
"""Check the published hierarchical reset walk counter against direct mask DP."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SITE = Path(__file__).resolve().parent.parent
ARTICLE = SITE / 'src/content/docs/techniques/hierarchical-reset-walk-count.mdx'

TESTS = r'''
#include <algorithm>
#include <cassert>
#include <bit>
#include <iostream>
#include <limits>
#include <random>
#include <utility>

using namespace std;
constexpr int TEST_MOD = 1000000007;

void add_mod(int& target, int value) {
    target += value;
    if (target >= TEST_MOD) target -= TEST_MOD;
}

size_t query_index(int n, int k, const ResetWalkQuery& query) {
    return static_cast<size_t>(
        ((query.start_vertex * k + query.first_label - 1) * n
         + query.end_vertex) * k + query.last_label - 1);
}

// Directly count every legal extension of each (start room, first label).
// A mask bit means that label has been used since the last larger label.
// No maximum-label split, endpoint pseudostate or matrix product is used.
vector<int> literal_mask_table(const vector<string>& graph, int k) {
    const int n = static_cast<int>(graph.size());
    const int mask_count = 1 << k;
    vector<int> answers(n * k * n * k);
    for (int start = 0; start < n; ++start) {
        for (int first = 1; first <= k; ++first) {
            vector<vector<int>> ways(mask_count, vector<int>(n));
            ways[1 << (first - 1)][start] = 1;
            for (int mask = 1; mask < mask_count; ++mask) {
                // The most recent label is the least set bit: lower bits
                // were cleared when it was pressed.
                const int last = countr_zero(static_cast<unsigned>(mask)) + 1;
                for (int room = 0; room < n; ++room) {
                    const int count = ways[mask][room];
                    add_mod(answers[query_index(n, k, {start, first, room, last})], count);
                    if (count == 0) continue;
                    for (int next_room = 0; next_room < n; ++next_room) {
                        if (graph[room][next_room] != '1') continue;
                        for (int label = 0; label < k; ++label) {
                            if (mask & (1 << label)) continue;
                            const int next_mask =
                                (mask & ~((1 << (label + 1)) - 1)) | (1 << label);
                            assert(next_mask > mask);
                            add_mod(ways[next_mask][next_room], count);
                        }
                    }
                }
            }
        }
    }
    return answers;
}

vector<ResetWalkQuery> every_query(int n, int k) {
    vector<ResetWalkQuery> queries;
    for (int start = 0; start < n; ++start)
        for (int first = 1; first <= k; ++first)
            for (int end = 0; end < n; ++end)
                for (int last = 1; last <= k; ++last)
                    queries.push_back({start, first, end, last});
    return queries;
}

void check_graph(const vector<string>& graph, int k, mt19937& random) {
    const int n = static_cast<int>(graph.size());
    const auto before = graph;
    const auto expected = literal_mask_table(graph, k);
    auto queries = every_query(n, k);
    shuffle(queries.begin(), queries.end(), random);
    // API batches respect Q <= 60, including the final short batch.
    for (size_t offset = 0; offset < queries.size(); offset += 60) {
        const size_t end = min(queries.size(), offset + 60);
        const vector<ResetWalkQuery> batch(queries.begin() + offset, queries.begin() + end);
        const auto actual = count_hierarchical_reset_walks(graph, k, batch);
        assert(actual.size() == batch.size());
        for (size_t j = 0; j < batch.size(); ++j) {
            if (actual[j] != expected[query_index(n, k, batch[j])]) {
                const auto& query = batch[j];
                cerr << "mask mismatch: N=" << n << " K=" << k
                     << " query=" << query.start_vertex << ',' << query.first_label
                     << ',' << query.end_vertex << ',' << query.last_label << '\n';
                abort();
            }
        }
    }
    const vector<ResetWalkQuery> repeated(60, queries.front());
    assert(count_hierarchical_reset_walks(graph, k, repeated)
           == vector<int>(60, expected[query_index(n, k, queries.front())]));
    assert(count_hierarchical_reset_walks(graph, k, {}).empty());
    assert(graph == before);
}

void check_samples() {
    const vector<string> first_graph = {
        "010000", "001000", "000100", "000010", "000000", "000001"};
    const vector<ResetWalkQuery> first_queries = {
        {0, 1, 0, 1}, {2, 3, 0, 1}, {0, 1, 2, 3}, {0, 1, 4, 1},
        {0, 2, 4, 1}, {0, 1, 4, 2}, {0, 3, 4, 3}, {5, 2, 5, 2}};
    assert(count_hierarchical_reset_walks(first_graph, 3, first_queries)
           == (vector<int>{1, 0, 1, 3, 2, 2, 0, 5}));
    const vector<string> second_graph = {
        "001100", "001110", "101101", "010111", "110111", "000111"};
    const vector<ResetWalkQuery> second_queries = {
        {1, 3, 2, 4}, {0, 3, 3, 4}, {3, 3, 0, 4},
        {2, 3, 2, 4}, {5, 3, 2, 4}, {0, 3, 1, 4}};
    assert(count_hierarchical_reset_walks(second_graph, 4, second_queries)
           == (vector<int>{26, 49, 29, 27, 18, 22}));
    const vector<string> third_graph = {
        "110101", "011001", "001111", "101111", "111010", "000001"};
    const vector<ResetWalkQuery> third_queries = {
        {4, 2, 4, 2}, {0, 6, 1, 5}, {3, 3, 2, 8}, {2, 9, 4, 3}, {0, 5, 3, 3}};
    const vector<int> third_expected = {
        713313311, 716721076, 782223918, 335511486, 539247783};
    assert(count_hierarchical_reset_walks(third_graph, 10, third_queries) == third_expected);
    const auto mask_answers = literal_mask_table(third_graph, 10);
    for (size_t j = 0; j < third_queries.size(); ++j)
        assert(mask_answers[query_index(6, 10, third_queries[j])] == third_expected[j]);
    cout << "spaceship-samples PASS: all three official samples, including direct 10-label mask counting and modulo totals\n";
}

// These graphs have three layers and no edges within/backwards, so all
// possible walks contain at most three pressed vertices. Enumerate those
// walks and their middle label directly, even when N=K=Q=60.
int literal_three_layer_answer(const vector<string>& graph, int k,
                              const ResetWalkQuery& query) {
    const int n = static_cast<int>(graph.size());
    int answer = query.start_vertex == query.end_vertex && query.first_label == query.last_label;
    if (graph[query.start_vertex][query.end_vertex] == '1'
        && query.first_label != query.last_label) ++answer;
    for (int middle = 0; middle < n; ++middle) {
        if (graph[query.start_vertex][middle] != '1'
            || graph[middle][query.end_vertex] != '1') continue;
        for (int label = 1; label <= k; ++label) {
            if (label == query.first_label || label == query.last_label) continue;
            if (query.first_label == query.last_label && label < query.first_label) continue;
            ++answer;
        }
    }
    return answer;
}

void check_maximum_cases() {
    constexpr int n = 60, k = 60;
    vector<string> graph(n, string(n, '0'));
    for (int from = 0; from < n; ++from) {
        for (int to = 0; to < n; ++to) {
            if (from / 20 < to / 20 && (from * 7 + to * 11) % 5 != 0)
                graph[from][to] = '1';
        }
    }
    vector<ResetWalkQuery> queries;
    for (int i = 0; i < 60; ++i) {
        const int start = i < 40 ? i % 20 : i;
        const int end = i % 5 == 0 ? start : 40 + (i * 7) % 20;
        queries.push_back({start, 1 + i, end, i % 3 == 0 ? 1 + i : 60 - i});
    }
    vector<int> expected;
    for (const auto& query : queries)
        expected.push_back(literal_three_layer_answer(graph, k, query));
    assert(count_hierarchical_reset_walks(graph, k, queries) == expected);
    assert(*max_element(expected.begin(), expected.end()) > 500);

    // With no edge, the sole possible sequence is the initial press.
    graph.assign(n, string(n, '0'));
    for (size_t j = 0; j < queries.size(); ++j) {
        const auto& query = queries[j];
        expected[j] = query.start_vertex == query.end_vertex
                      && query.first_label == query.last_label;
    }
    assert(count_hierarchical_reset_walks(graph, k, queries) == expected);

    // In a complete cyclic graph even the top label cannot be reused.
    // Other endpoint cells contain huge counts, while these 60 exact
    // constraints have the independently known identity answer.
    graph.assign(n, string(n, '1'));
    for (int j = 0; j < 60; ++j) {
        queries[j] = {j, k, j % 2 == 0 ? j : (j + 1) % n, k};
        expected[j] = j % 2 == 0 ? 1 : 0;
    }
    assert(count_hierarchical_reset_walks(graph, k, queries) == expected);
    cout << "spaceship-boundaries PASS: N=K=Q=60, direct three-layer walk enumeration, no edges and dense cyclic graph with self loops\n";
}

template<class Function>
void require_invalid(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const invalid_argument&) { rejected = true; }
    assert(rejected);
}

void check_contracts() {
    assert(count_hierarchical_reset_walks({"0"}, 1, {{0, 1, 0, 1}}) == vector<int>{1});
    assert(count_hierarchical_reset_walks({"1"}, 2, {{0, 1, 0, 1}, {0, 2, 0, 2}})
           == (vector<int>{2, 1}));
    for (int k : {0, -1, 61, numeric_limits<int>::max()})
        require_invalid([&] { (void)count_hierarchical_reset_walks({"0"}, k, {}); });
    for (const auto& graph : vector<vector<string>>{
        {}, {""}, {"00"}, {"00", "0"}, {"00", "000"}, {"2"}, {"x"},
        vector<string>(61, string(61, '0'))}) {
        require_invalid([&] { (void)count_hierarchical_reset_walks(graph, 1, {}); });
    }
    require_invalid([] {
        (void)count_hierarchical_reset_walks({"1"}, 1, vector<ResetWalkQuery>(61, {0, 1, 0, 1}));
    });
    for (auto query : vector<ResetWalkQuery>{
        {-1, 1, 0, 1}, {1, 1, 0, 1}, {0, 1, -1, 1}, {0, 1, 1, 1},
        {0, 0, 0, 1}, {0, 2, 0, 1}, {0, 1, 0, 0}, {0, 1, 0, 2},
        {numeric_limits<int>::min(), 1, 0, 1}, {0, 1, numeric_limits<int>::max(), 1}}) {
        require_invalid([&] { (void)count_hierarchical_reset_walks({"1"}, 1, {query}); });
    }
    cout << "spaceship-contracts PASS: zero-move versus empty sequences, equal first/last labels, query batches, empty queries and every invalid-input class\n";
}

int main() {
    mt19937 random(10692020);
    check_samples();
    int graphs_checked = 0;
    for (int n = 1; n <= 3; ++n) {
        const int maximum_k = n == 1 ? 6 : n == 2 ? 5 : 4;
        for (int bits = 0; bits < (1 << (n * n)); ++bits) {
            vector<string> graph(n, string(n, '0'));
            for (int i = 0; i < n; ++i)
                for (int j = 0; j < n; ++j)
                    if (bits >> (i * n + j) & 1) graph[i][j] = '1';
            for (int k = 1; k <= maximum_k; ++k) {
                check_graph(graph, k, random);
                ++graphs_checked;
            }
        }
    }
    for (int trial = 0; trial < 240; ++trial) {
        const int n = 1 + random() % 4, k = 1 + random() % 6;
        vector<string> graph(n, string(n, '0'));
        for (auto& row : graph)
            for (char& value : row) value = random() % 3 == 0 ? '1' : '0';
        check_graph(graph, k, random);
        ++graphs_checked;
    }
    cout << "spaceship-mask-oracle PASS: " << graphs_checked
         << " exhaustive and random graph/label cases, every endpoint/first/last query, shuffled batches, repeated queries and reset-mask DP\n";
    check_maximum_cases();
    check_contracts();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default=os.environ.get('CXX', 'g++'))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f'C++20 compiler not found: {args.compiler}')
    article = ARTICLE.read_text(encoding='utf8')
    if len(re.findall(r'^## ', article, re.M)) != 8:
        parser.error('expected exactly eight article sections')
    matches = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article, re.M | re.S)
    if len(matches) != 1:
        parser.error('expected exactly one complete C++ fence')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-spaceship-') as directory:
        source = Path(directory) / 'compare.cpp'
        executable = Path(directory) / 'compare'
        source.write_text(matches[0] + '\n' + TESTS, encoding='utf8')
        compiled = subprocess.run(
            [args.compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
             str(source), '-o', str(executable)],
            capture_output=True, text=True, timeout=120)
        if compiled.returncode:
            print(compiled.stderr, file=sys.stderr)
            return compiled.returncode
        result = subprocess.run([str(executable)], timeout=180)
        if result.returncode:
            return result.returncode
        print('Published hierarchical reset walk implementation passed independent mask-DP and maximum-boundary comparisons.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
