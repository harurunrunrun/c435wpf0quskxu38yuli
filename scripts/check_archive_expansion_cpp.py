#!/usr/bin/env python3
"""Compare six published implementations with independent small enumerations."""

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
    "residue-shortest-representable-count",
    "summatory-totient-quotient-memo",
    "sam-common-all-strings",
    "palindrome-two-disjoint-product",
    "shortest-edge-mandatory-tight-bridges",
    "complement-graph-unvisited-bfs",
)


def extracted_source():
    """Compile actual article fences, rather than copies of their examples."""
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
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
using namespace std;

using article_residue_shortest_representable_count::count_representable_sums;
using article_summatory_totient_quotient_memo::summatory_totient;
using article_sam_common_all_strings::longest_common_substring_all;
using article_palindrome_two_disjoint_product::maximum_disjoint_odd_palindrome_product;
using article_shortest_edge_mandatory_tight_bridges::DirectedPositiveEdge;
using article_shortest_edge_mandatory_tight_bridges::ShortestEdgeAction;
using article_shortest_edge_mandatory_tight_bridges::analyze_shortest_edges;
using article_complement_graph_unvisited_bfs::complement_components;

template<class Exception, class Function>
void require_exception(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const Exception&) { rejected = true; }
    assert(rejected);
}

void check_coins_case(const vector<long long>& coins, int bound, mt19937& rng) {
    const auto before = coins;
    // Ordinary boolean unbounded knapsack is indexed by the represented sum,
    // and makes no residue graph or minimum-distance assumption.
    vector<int> reachable(bound + 1);
    reachable[0] = 1;
    for (int value = 1; value <= bound; ++value)
        for (long long coin : coins)
            if (coin > 0 && coin <= value && reachable[value - coin]) {
                reachable[value] = 1;
                break;
            }
    vector<int> prefix(bound + 2);
    for (int value = 0; value <= bound; ++value)
        prefix[value + 1] = prefix[value] + reachable[value];
    const auto expected = [&](int left, int right) {
        if (right < 0) return 0;
        return prefix[right + 1] - prefix[max(left, 0)];
    };
    for (int right = 0; right <= bound; right += 7)
        assert(count_representable_sums(coins, -17, right) == expected(-17, right));
    for (int query = 0; query < 20; ++query) {
        int left = int(rng() % (bound + 31)) - 30;
        int right = int(rng() % (bound + 31)) - 30;
        if (left > right) swap(left, right);
        assert(count_representable_sums(coins, left, right) == expected(left, right));
    }
    assert(coins == before);
}

void check_coins(mt19937& rng) {
    for (unsigned mask = 0; mask < 256; ++mask) {
        vector<long long> coins;
        for (int value = 1; value <= 8; ++value)
            if ((mask >> (value - 1)) & 1U) coins.push_back(value);
        check_coins_case(coins, 250, rng);
    }
    for (int trial = 0; trial < 300; ++trial) {
        vector<long long> coins(rng() % 8);
        for (auto& coin : coins) coin = rng() % 40;
        check_coins_case(coins, 400, rng);
    }
    const auto lo = numeric_limits<long long>::min();
    const auto hi = numeric_limits<long long>::max();
    assert(count_representable_sums({}, lo, hi) == 1);
    assert(count_representable_sums({0, 0}, lo, -1) == 0);
    assert(count_representable_sums({0, 1, hi}, 0, hi) == (__int128(1) << 63));
    assert(count_representable_sums({2, hi}, 0, hi) == (__int128(1) << 62) + 1);
    assert(count_representable_sums({6, 10, 10, 0}, hi - 1, hi) == 1);
    assert(count_representable_sums({500000}, 0, 1000000) == 3);
    assert(count_representable_sums({500000, 500000, hi}, hi, hi) == 1);
    require_exception<invalid_argument>([] { (void)count_representable_sums({-1, 2}, 0, 5); });
    require_exception<invalid_argument>([] { (void)count_representable_sums({1}, 3, 2); });
    require_exception<length_error>([] { (void)count_representable_sums({500001}, 0, 4); });
    cout << "residue-shortest-representable-count PASS: boolean sum DP, unreachable residues, duplicate/zero coins and full signed query bounds\n";
}

int mobius_totient_prefix_mod(long long n) {
    constexpr int limit = 1000000;
    vector<int> least(limit + 1), mu(limit + 1), prefix(limit + 1);
    for (int prime = 2; prime <= limit; ++prime) if (least[prime] == 0)
        for (int multiple = prime; multiple <= limit; multiple += prime)
            if (least[multiple] == 0) least[multiple] = prime;
    mu[1] = 1;
    for (int value = 1; value <= limit; ++value) {
        if (value > 1) {
            int prime = least[value], rest = value / prime;
            mu[value] = rest % prime == 0 ? 0 : -mu[rest];
        }
        prefix[value] = prefix[value - 1] + mu[value];
    }
    unordered_map<long long, long long> memo;
    function<long long(long long)> mertens = [&](long long x) -> long long {
        if (x <= limit) return prefix[x];
        if (auto it = memo.find(x); it != memo.end()) return it->second;
        __int128 result = 1;
        for (long long left = 2; left <= x; ) {
            long long quotient = x / left, right = x / quotient;
            result -= (__int128)(right - left + 1) * mertens(quotient);
            left = right + 1;
        }
        assert(-(__int128)x <= result && result <= x);
        return memo[x] = static_cast<long long>(result);
    };
    // Möbius inversion counts ordered coprime lattice points. Its exact
    // (unreduced) total is 2*sum(phi(1..n))-1; it never evaluates the article's
    // modular totient recurrence and uses a different arithmetic function.
    __int128 coprime_pairs = 0;
    for (long long left = 1; left <= n; ) {
        long long quotient = n / left, right = n / quotient;
        coprime_pairs += (__int128)(mertens(right) - mertens(left - 1))
                         * quotient * quotient;
        left = right + 1;
    }
    assert(coprime_pairs > 0 && coprime_pairs % 2 == 1);
    return int(((coprime_pairs + 1) / 2) % 998244353);
}

void check_totient(mt19937& rng) {
    constexpr long long modulus = 998244353;
    // Sieve prime factors directly, independently of quotient grouping or
    // memoized summatory recurrences.
    constexpr int limit = 2000000;
    vector<int> phi(limit + 1);
    iota(phi.begin(), phi.end(), 0);
    for (int prime = 2; prime <= limit; ++prime) if (phi[prime] == prime)
        for (int multiple = prime; multiple <= limit; multiple += prime)
            phi[multiple] -= phi[multiple] / prime;
    vector<long long> prefix(limit + 1);
    for (int value = 1; value <= limit; ++value)
        prefix[value] = (prefix[value - 1] + phi[value]) % modulus;
    long long direct_prefix = 0;
    for (int n = 0; n <= 400; ++n) {
        int count = 0;
        for (int x = 1; x <= n; ++x) count += gcd(x, n) == 1;
        direct_prefix = (direct_prefix + count) % modulus;
        assert(prefix[n] == direct_prefix);
        assert(summatory_totient(n) == direct_prefix);
    }
    for (int trial = 0; trial < 180; ++trial) {
        int n = rng() % 100001;
        assert(summatory_totient(n) == prefix[n]);
    }
    for (int n : {998244, 1000000, 1000001, 1999999, 2000000})
        assert(summatory_totient(n) == prefix[n]);
    // The convolution phi * 1 = id, checked with exact small phi values,
    // independently validates the result's normalization under the modulus.
    for (int n : {1, 2, 100, 997, 10000, 100000}) {
        long long convolution = 0;
        for (int d = 1; d <= n; ++d)
            convolution = (convolution + (long long)phi[d] * (n / d)) % modulus;
        assert(convolution == (long long)n * (n + 1) / 2 % modulus);
    }
    // This reaches the largest supported input and a triangle larger than
    // signed 64 bits. The independent factorization 10^10 = 2^10 * 5^10
    // yields phi(10^10) = 4*10^9, so consecutive sums must differ by that.
    const long long large = 10000000000LL;
    const int at_large = summatory_totient(large);
    const int before_large = summatory_totient(large - 1);
    assert(0 <= at_large && at_large < modulus);
    assert(0 <= before_large && before_large < modulus);
    assert(at_large == mobius_totient_prefix_mod(large));
    assert((at_large - (long long)before_large + modulus) % modulus == 4000000000LL % modulus);
    require_exception<invalid_argument>([] { (void)summatory_totient(-1); });
    require_exception<invalid_argument>([] { (void)summatory_totient(10000000001LL); });
    cout << "summatory-totient-quotient-memo PASS: gcd counts, prime sieve, independent Mobius coprime-pair sum and the 10^10 boundary difference\n";
}

int literal_common_length(const vector<string>& texts) {
    if (texts.empty()) return 0;
    const auto shortest = min_element(texts.begin(), texts.end(),
        [](const string& a, const string& b) { return a.size() < b.size(); });
    int best = 0;
    // Enumerate literal contiguous substrings and use ordinary byte searching.
    // This oracle has no suffix automaton, suffix links, or length propagation.
    for (size_t start = 0; start < shortest->size(); ++start)
        for (size_t length = best + 1; start + length <= shortest->size(); ++length) {
            const auto candidate = shortest->substr(start, length);
            bool common = true;
            for (const auto& text : texts)
                if (text.find(candidate) == string::npos) { common = false; break; }
            if (common) best = length;
        }
    return best;
}

void check_common_case(const vector<string>& texts) {
    const auto before = texts;
    const auto result = longest_common_substring_all(texts);
    assert(int(result.size()) == literal_common_length(texts));
    for (const auto& text : texts) assert(text.find(result) != string::npos);
    assert(texts == before);
}

vector<string> binary_strings(int maximum_length) {
    vector<string> result;
    for (int length = 0; length <= maximum_length; ++length)
        for (unsigned mask = 0; mask < (1U << length); ++mask) {
            string text(length, 'a');
            for (int i = 0; i < length; ++i) if ((mask >> i) & 1U) text[i] = 'b';
            result.push_back(text);
        }
    return result;
}

void check_common(mt19937& rng) {
    check_common_case({});
    const auto pairs = binary_strings(5);
    for (const auto& a : pairs) for (const auto& b : pairs) check_common_case({a, b});
    const auto triples = binary_strings(3);
    for (const auto& a : triples) for (const auto& b : triples) for (const auto& c : triples)
        check_common_case({a, b, c});
    for (const vector<string>& texts : vector<vector<string>>{
            {"abababca", "bababcb", "zzababcyy"},
            {"mississippi", "sippimiss", "ppissi"},
            {"abcdef", "fabcde", "defabc"},
            {"aaaaaaaaab", "baaaaaaaac", "caaaaaaaad"},
            {"abbabaabbab", "baabbabba", "bbaabbababb"},
            {"", "anything"}, {"single"}, {"ab", "ba", "aa", "bb"},
            {string("\0\xff\x80\0z", 5), string("q\xff\x80\0", 4), string("\xff\x80\0", 3)}})
        check_common_case(texts);
    for (int trial = 0; trial < 700; ++trial) {
        vector<string> texts(rng() % 7);
        for (auto& text : texts) {
            text.resize(rng() % 25);
            for (auto& c : text) c = char(trial % 3 ? rng() % 4 : rng() % 256);
        }
        check_common_case(texts);
    }
    vector<string> many(500, string(120, '\0'));
    many[217] = string(37, '\0');
    assert(longest_common_substring_all(many) == string(37, '\0'));
    const string large(100000, 'x');
    assert(longest_common_substring_all({large, "q" + large + "z"}) == large);
    cout << "sam-common-all-strings PASS: literal substring witnesses, all binary pairs/triples, suffix-link adversaries and arbitrary bytes\n";
}

long long all_odd_palindrome_pairs(const string& text) {
    vector<tuple<int, int, int>> intervals;
    for (int left = 0; left < int(text.size()); ++left)
        for (int right = left; right < int(text.size()); right += 2) {
            bool palindrome = true;
            for (int a = left, b = right; a < b; ++a, --b)
                if (text[a] != text[b]) { palindrome = false; break; }
            if (palindrome) intervals.emplace_back(left, right, right - left + 1);
        }
    long long best = 0;
    // Check actual disjoint substring intervals, with no Manacher radii or
    // prefix/suffix endpoint shrinking in the expected result.
    for (auto [a, b, first] : intervals) for (auto [c, d, second] : intervals)
        if (b < c || d < a) best = max(best, (long long)first * second);
    return best;
}

void check_palindrome_case(const string& text) {
    assert(maximum_disjoint_odd_palindrome_product(text) == all_odd_palindrome_pairs(text));
}

void check_palindromes(mt19937& rng) {
    for (const auto& text : binary_strings(12)) check_palindrome_case(text);
    for (const string text : {"abacdcaba", "abbaabba", "abacabadabacaba", "aaaaabaaaaa", "abcbaaaabcba", "abaaba"})
        check_palindrome_case(text);
    for (int trial = 0; trial < 650; ++trial) {
        string text(rng() % 41, '\0');
        for (auto& c : text) c = char(trial % 5 ? rng() % 4 : rng() % 256);
        check_palindrome_case(text);
    }
    for (int n : {99999, 100000, 100001}) {
        long long expected = 0;
        for (long long first = 1; first < n; first += 2) {
            long long second = n - first;
            if (second % 2 == 0) --second;
            expected = max(expected, first * second);
        }
        assert(expected > INT_MAX);
        assert(maximum_disjoint_odd_palindrome_product(string(n, 'a')) == expected);
    }
    cout << "palindrome-two-disjoint-product PASS: every odd palindrome pair, binary exhaustive cases, byte equality and products exceeding 32 bits\n";
}

struct EnumeratedPath {
    __int128 length;
    unsigned edges;
};

vector<EnumeratedPath> all_simple_paths(int n, int source, int target,
                                      const vector<DirectedPositiveEdge>& edges) {
    assert(edges.size() < 31);
    vector<vector<int>> outgoing(n);
    for (int e = 0; e < int(edges.size()); ++e) outgoing[edges[e].from].push_back(e);
    vector<EnumeratedPath> result;
    function<void(int, unsigned, unsigned, __int128)> visit =
        [&](int at, unsigned visited, unsigned used, __int128 length) {
            if (at == target) { result.push_back({length, used}); return; }
            for (int e : outgoing[at]) {
                const auto& edge = edges[e];
                if ((visited >> edge.to) & 1U) continue;
                visit(edge.to, visited | (1U << edge.to), used | (1U << e), length + edge.weight);
            }
        };
    visit(source, 1U << source, 0, 0);
    return result;
}

void check_shortest_case(int n, int source, int target, const vector<DirectedPositiveEdge>& edges) {
    // Enumerate complete positive paths, including their original edge IDs.
    // Neither a shortest-path DAG nor bridges or Dijkstra are used here.
    const auto paths = all_simple_paths(n, source, target, edges);
    const auto result = analyze_shortest_edges(n, source, target, edges);
    assert(result.reachable == !paths.empty());
    assert(result.decisions.size() == edges.size());
    optional<__int128> shortest;
    for (const auto& path : paths)
        if (!shortest || path.length < *shortest) shortest = path.length;
    assert(result.distance == shortest.value_or(0));
    for (int e = 0; e < int(edges.size()); ++e) {
        optional<__int128> with_edge, without_edge;
        bool mandatory = !paths.empty();
        for (const auto& path : paths) {
            const bool uses = (path.edges >> e) & 1U;
            if (shortest && path.length == *shortest && !uses) mandatory = false;
            auto& choice = uses ? with_edge : without_edge;
            if (!choice || path.length < *choice) choice = path.length;
        }
        const auto actual = result.decisions[e];
        if (mandatory) {
            assert(actual.action == ShortestEdgeAction::Mandatory);
            assert(actual.reduction == 0);
            continue;
        }
        optional<long long> reduction;
        if (with_edge && without_edge) {
            // After decreasing this one edge, all best paths must use it iff
            // the best complete path using it becomes strictly cheaper than
            // every complete path avoiding it.
            const __int128 needed = max(__int128(1), *with_edge - *without_edge + 1);
            if (needed < edges[e].weight) reduction = static_cast<long long>(needed);
        }
        if (reduction) {
            assert(actual.action == ShortestEdgeAction::Reduce);
            assert(actual.reduction == *reduction);
            assert(edges[e].weight - *reduction >= 1);
            // Directly change small weights and enumerate the changed graph:
            // no smaller legal positive reduction may already be sufficient.
            if (edges[e].weight <= 10) {
                for (long long decrease = 1; decrease <= *reduction; ++decrease) {
                    auto changed = edges;
                    changed[e].weight -= decrease;
                    const auto after = all_simple_paths(n, source, target, changed);
                    optional<__int128> best;
                    for (const auto& path : after) if (!best || path.length < *best) best = path.length;
                    bool every = bool(best);
                    for (const auto& path : after)
                        if (path.length == best && !((path.edges >> e) & 1U)) every = false;
                    assert(every == (decrease == *reduction));
                }
            }
        } else {
            assert(actual.action == ShortestEdgeAction::Impossible);
            assert(actual.reduction == 0);
        }
    }
}

void check_shortest(mt19937& rng) {
    vector<pair<int, int>> arcs;
    for (int u = 0; u < 3; ++u) for (int v = 0; v < 3; ++v) if (u != v) arcs.emplace_back(u, v);
    for (int encoding = 0; encoding < 4096; ++encoding) {
        int digits = encoding;
        vector<DirectedPositiveEdge> edges;
        for (auto [u, v] : arcs) {
            int choice = digits % 4;
            digits /= 4;
            if (choice) edges.push_back({u, v, choice == 3 ? 4 : choice});
        }
        check_shortest_case(3, 0, 2, edges);
    }
    const long long hi = numeric_limits<long long>::max();
    const vector<vector<DirectedPositiveEdge>> boundary{
        {}, {{0, 1, 1}}, {{0, 1, 1}, {0, 1, 1}}, {{0, 1, 2}, {0, 1, 3}},
        {{0, 1, hi}, {1, 2, hi}, {0, 2, hi}},
        {{0, 1, hi}, {1, 2, hi}},
        {{0, 0, hi}, {0, 1, 2}, {1, 1, 1}, {1, 2, 2}, {2, 2, hi}},
        {{0, 1, 2}, {1, 3, 2}, {0, 2, 2}, {2, 3, 2}, {1, 2, 1}, {2, 1, 1}},
        {{0, 1, 5}, {1, 2, 3}, {0, 2, 8}, {0, 2, 9}, {2, 0, 1}}};
    for (const auto& edges : boundary) {
        int n = 1;
        for (const auto& edge : edges) n = max(n, max(edge.from, edge.to) + 1);
        for (int source = 0; source < n; ++source) for (int target = 0; target < n; ++target)
            check_shortest_case(n, source, target, edges);
    }
    for (int trial = 0; trial < 1400; ++trial) {
        const int n = 1 + rng() % 7, m = rng() % 13;
        vector<DirectedPositiveEdge> edges;
        for (int e = 0; e < m; ++e) {
            int u = rng() % n, v = rng() % n;
            long long weight = 1 + rng() % 9;
            if (e && trial % 5 == 0) {
                const auto& previous = edges[rng() % edges.size()];
                u = previous.from; v = previous.to;
                if (trial % 10) weight = previous.weight;
            }
            edges.push_back({u, v, weight});
        }
        check_shortest_case(n, rng() % n, rng() % n, edges);
    }
    // Iterative bridge traversal and non-overflowing 128-bit distances are
    // also checked at a depth that would exhaust a recursive DFS stack.
    const int n = 100000;
    vector<DirectedPositiveEdge> chain;
    for (int u = 0; u + 1 < n; ++u) chain.push_back({u, u + 1, hi});
    const auto result = analyze_shortest_edges(n, 0, n - 1, chain);
    assert(result.reachable && result.distance == (__int128)(n - 1) * hi);
    for (const auto& decision : result.decisions) assert(decision.action == ShortestEdgeAction::Mandatory);
    require_exception<invalid_argument>([] { (void)analyze_shortest_edges(0, 0, 0, {}); });
    require_exception<invalid_argument>([] { (void)analyze_shortest_edges(2, 0, 1, {{0, 1, 0}}); });
    require_exception<invalid_argument>([] { (void)analyze_shortest_edges(2, 0, 1, {{0, 1, -1}}); });
    require_exception<out_of_range>([] { (void)analyze_shortest_edges(2, 0, 1, {{0, 2, 1}}); });
    cout << "shortest-edge-mandatory-tight-bridges PASS: all positive simple paths, parallel edges, minimum legal reductions and 128-bit chain distances\n";
}

vector<vector<int>> canonical_components(vector<vector<int>> result) {
    for (auto& component : result) sort(component.begin(), component.end());
    sort(result.begin(), result.end());
    return result;
}

void check_complement_case(int n, const vector<pair<int, int>>& forbidden) {
    vector<vector<bool>> adjacent(n, vector<bool>(n, true));
    for (int u = 0; u < n; ++u) adjacent[u][u] = false;
    for (auto [u, v] : forbidden) adjacent[u][v] = adjacent[v][u] = false;
    vector<int> visited(n);
    vector<vector<int>> expected;
    // Materialize all edges of the complement and use ordinary BFS, unlike
    // the linked unvisited list and neighbor stamps in the implementation.
    for (int root = 0; root < n; ++root) if (!visited[root]) {
        expected.push_back({root});
        visited[root] = 1;
        for (size_t head = 0; head < expected.back().size(); ++head) {
            int u = expected.back()[head];
            for (int v = 0; v < n; ++v) if (adjacent[u][v] && !visited[v]) {
                visited[v] = 1;
                expected.back().push_back(v);
            }
        }
    }
    const auto actual = complement_components(n, forbidden);
    assert(canonical_components(actual) == canonical_components(expected));
}

void check_complement(mt19937& rng) {
    for (int n = 0; n <= 6; ++n) {
        vector<pair<int, int>> pairs;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) pairs.emplace_back(u, v);
        for (unsigned mask = 0; mask < (1U << pairs.size()); ++mask) {
            vector<pair<int, int>> forbidden;
            for (size_t e = 0; e < pairs.size(); ++e) if ((mask >> e) & 1U) forbidden.push_back(pairs[e]);
            check_complement_case(n, forbidden);
        }
    }
    for (int trial = 0; trial < 650; ++trial) {
        int n = rng() % 35;
        vector<pair<int, int>> forbidden;
        if (n) for (unsigned e = 0, count = rng() % 160; e < count; ++e) {
            int u = rng() % n, v = rng() % n;
            forbidden.emplace_back(u, v);
            if (e % 5 == 0) forbidden.emplace_back(v, u);
        }
        check_complement_case(n, forbidden);
    }
    const int n = 100000;
    auto empty = complement_components(n, {});
    assert(empty.size() == 1 && empty.front().size() == size_t(n));
    vector<pair<int, int>> star;
    for (int v = 1; v < n; ++v) star.emplace_back(0, v);
    auto star_result = canonical_components(complement_components(n, star));
    assert(star_result.size() == 2 && star_result[0] == vector<int>{0});
    assert(star_result[1].size() == size_t(n - 1));
    vector<pair<int, int>> complete;
    for (int u = 0; u < 200; ++u) for (int v = u + 1; v < 200; ++v) complete.emplace_back(u, v);
    auto singletons = complement_components(200, complete);
    assert(singletons.size() == 200);
    for (const auto& component : singletons) assert(component.size() == 1);
    require_exception<invalid_argument>([] { (void)complement_components(-1, {}); });
    require_exception<out_of_range>([] { (void)complement_components(2, {{0, 2}}); });
    require_exception<out_of_range>([] { (void)complement_components(0, {{0, 0}}); });
    cout << "complement-graph-unvisited-bfs PASS: every graph through six vertices, explicit complement BFS, duplicates and sparse large cases\n";
}

int main() {
    cout << unitbuf;
    mt19937 rng(20261021);
    check_coins(rng);
    check_totient(rng);
    check_common(rng);
    check_palindromes(rng);
    check_shortest(rng);
    check_complement(rng);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-archive-expansion-cpp-") as directory:
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
        print("All 6 archive expansion implementations passed independent comparisons and boundary cases.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
