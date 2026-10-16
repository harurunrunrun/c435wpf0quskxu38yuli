#!/usr/bin/env python3
"""Extract the published C++20 fence and compare against simultaneous updates.

Relocation: python3 check.py --article /path/to/the/article.mdx
The script and article need not share a directory or belong to a checkout.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


TESTS = r'''
#include <boost/multiprecision/cpp_int.hpp>
using boost::multiprecision::cpp_int;

constexpr long long MOD = 1000000007;

unsigned literal_simulation(const vector<int>& initial) {
    const int n = int(initial.size()) / 2;
    vector<int> heights = initial;
    vector<int> last(n + 1);
    for (int earthquake = 0; earthquake < n; ++earthquake) {
        fill(last.begin(), last.end(), -1);
        // Snapshot every protected position before changing any height.
        for (int i = 0; i < 2 * n; ++i)
            if (heights[i] > 0) last[heights[i]] = i;
        for (int i = 0; i < 2 * n; ++i)
            if (heights[i] > 0 && last[heights[i]] != i) --heights[i];
    }
    unsigned mask = 0;
    vector<int> count(n + 1);
    for (int i = 0; i < 2 * n; ++i)
        if (heights[i] > 0) {
            mask |= 1U << i;
            ++count[heights[i]];
        }
    for (int h = 1; h <= n; ++h) assert(count[h] == 1);
    return mask;
}

unsigned parking_mask(const vector<int>& initial) {
    vector<bool> used(initial.size() / 2 + 1);
    unsigned mask = 0;
    for (int i = int(initial.size()) - 1; i >= 0; --i) {
        int height = initial[i];
        while (height > 0 && used[height]) --height;
        if (height > 0) {
            used[height] = true;
            mask |= 1U << i;
        }
    }
    return mask;
}

unsigned frequency_mask(const vector<int>& initial, bool discard_survivors) {
    int n = int(initial.size()) / 2;
    vector<int> counts(n + 1);
    unsigned mask = 0;
    for (int i = 0; i < 2 * n; ++i) {
        int prefix = 0, minimum = 0, first = 0;
        for (int h = 1; h <= n; ++h) {
            prefix += counts[h] - 1;
            if (prefix < minimum) { minimum = prefix; first = h; }
        }
        bool survives_here = initial[i] > first;
        if (survives_here) mask |= 1U << i;
        if (!discard_survivors || !survives_here) ++counts[initial[i]];
        if (discard_survivors) {
            prefix = 0; minimum = 0;
            for (int h = 1; h <= n; ++h) {
                prefix += counts[h] - 1;
                minimum = min(minimum, prefix);
            }
            assert(prefix == minimum);
        }
    }
    return mask;
}

vector<int> positions(int n, unsigned mask) {
    vector<int> result;
    for (int i = 0; i < 2 * n; ++i)
        if (mask & (1U << i)) result.push_back(i + 1);
    return result;
}

void exhaustive_simulations() {
    unsigned long long total_permutations = 0, total_sets = 0;
    for (int n = 1; n <= 6; ++n) {
        vector<int> heights;
        for (int h = 1; h <= n; ++h) {
            heights.push_back(h); heights.push_back(h);
        }
        vector<unsigned long long> counts(1U << (2 * n));
        unsigned long long permutations = 0;
        do {
            unsigned expected = literal_simulation(heights);
            ++counts[expected];
            ++permutations;
            if (n <= 5 || permutations % 997 == 0) {
                assert(parking_mask(heights) == expected);
                assert(frequency_mask(heights, false) == expected);
                assert(frequency_mask(heights, true) == expected);
            }
        } while (next_permutation(heights.begin(), heights.end()));
        unsigned long long sum = 0, sets = 0;
        for (unsigned mask = 0; mask < counts.size(); ++mask) {
            if (popcount(mask) != n) continue;
            vector<int> input = positions(n, mask), before = input;
            long long actual = count_paired_height_survivors(n, input);
            assert(input == before);
            assert(actual == static_cast<long long>(counts[mask] % MOD));
            bool prefix_feasible = true;
            for (int i = 0; i < n; ++i) prefix_feasible &= input[i] >= 2 * (i + 1);
            assert((actual > 0) == prefix_feasible);
            sum += actual;
            ++sets;
        }
        unsigned long long expected_total = 1;
        for (int i = 1; i <= 2 * n; ++i) expected_total *= i;
        expected_total >>= n;
        assert(permutations == expected_total && sum == expected_total);
        total_permutations += permutations; total_sets += sets;
        cout << "exhaustive N=" << n << ": " << permutations
             << " multiset permutations, " << sets << " survivor sets\n";
    }
    assert(total_permutations == 7600417 && total_sets == 1274);
}

// Exponential exact count with the FULL frequency vector: no deferred values,
// no Dyck weights, no labelled copies, and no modular arithmetic.
cpp_int full_frequency_exact(int n, const vector<int>& target) {
    vector<bool> survivor(2 * n + 1);
    for (int p : target) survivor[p] = true;
    vector<int> power(n + 1, 1);
    for (int h = 0; h < n; ++h) power[h + 1] = power[h] * 3;
    vector<cpp_int> ways(power[n]);
    ways[0] = 1;
    for (int code = 0; code < power[n] - 1; ++code) {
        if (ways[code] == 0) continue;
        vector<int> frequency(n);
        int value = code, used = 0, prefix = 0, minimum = 0, first = 0;
        for (int h = 0; h < n; ++h) {
            frequency[h] = value % 3; value /= 3;
            used += frequency[h];
            prefix += frequency[h] - 1;
            if (prefix < minimum) { minimum = prefix; first = h + 1; }
        }
        for (int h = 0; h < n; ++h)
            if (frequency[h] < 2 && ((h + 1 > first) == survivor[used + 1]))
                ways[code + power[h]] += ways[code];
    }
    return ways.back();
}

long long mod_power(long long base, int exponent) {
    long long answer = 1;
    for (; exponent; exponent >>= 1, base = base * base % MOD)
        if (exponent & 1) answer = answer * base % MOD;
    return answer;
}

long long late_survivors_formula(int n) {
    vector<long long> factorial(2 * n + 1, 1);
    for (int i = 1; i <= 2 * n; ++i) factorial[i] = factorial[i - 1] * i % MOD;
    auto choose = [&](int k) -> long long {
        if (k < 0) return 0;
        return factorial[2 * n] * mod_power(factorial[k], MOD - 2) % MOD
            * mod_power(factorial[2 * n - k], MOD - 2) % MOD;
    };
    // Reflection of the first bad step: horizontal steps have two colors.
    long long weighted_walks = (choose(n) - choose(n - 2) + MOD) % MOD;
    return weighted_walks * factorial[n] % MOD * factorial[n] % MOD
        * mod_power(500000004, n) % MOD;
}

void exact_and_modular_checks() {
    assert(count_paired_height_survivors(3, {3, 4, 6}) == 5);
    assert(count_paired_height_survivors(1, {1}) == 0);
    assert(count_paired_height_survivors(1, {2}) == 1);
    vector<int> sample = {5, 8, 9, 13, 15, 16, 17, 18, 19, 20};
    cpp_int raw = full_frequency_exact(10, sample);
    assert(raw == cpp_int(111147004440LL));
    assert(count_paired_height_survivors(10, sample) == (raw % MOD).convert_to<long long>());
    assert(count_paired_height_survivors(10, sample) == 147003663);
    mt19937 rng(20200321);
    int above_modulus = 0;
    for (int trial = 0; trial < 16; ++trial) {
        int n = 7 + trial % 5;
        vector<int> target(2 * n);
        iota(target.begin(), target.end(), 1);
        shuffle(target.begin(), target.end(), rng);
        target.resize(n); sort(target.begin(), target.end());
        if (trial % 3 == 0) iota(target.begin(), target.end(), n + 1);
        cpp_int exact = full_frequency_exact(n, target);
        above_modulus += exact > MOD;
        assert(count_paired_height_survivors(n, target) == (exact % MOD).convert_to<long long>());
    }
    assert(above_modulus > 0);
    for (int n : {7, 10, 31, 600}) {
        vector<int> late(n), alternating(n);
        iota(late.begin(), late.end(), n + 1);
        for (int i = 0; i < n; ++i) alternating[i] = 2 * (i + 1);
        assert(count_paired_height_survivors(n, late) == late_survivors_formula(n));
        assert(count_paired_height_survivors(n, alternating) == 1);
    }
    vector<int> impossible(600);
    iota(impossible.begin(), impossible.end(), 600); // Rightmost position absent.
    assert(count_paired_height_survivors(600, impossible) == 0);
    iota(impossible.begin(), impossible.end(), 601);
    impossible[0] = 1;
    assert(count_paired_height_survivors(600, impossible) == 0);
    cout << "exact full-frequency counts: sample + 16 cases N=7..11; modular wrap checked\n";
    cout << "N=600: late survivors/reflection formula, alternating=1, two impossible sets\n";
}

template<class Function> void rejects(Function action) {
    bool caught = false;
    try { action(); } catch (const invalid_argument&) { caught = true; }
    assert(caught);
}

void contract_checks() {
    rejects([] { count_paired_height_survivors(0, {}); });
    rejects([] { count_paired_height_survivors(-1, {}); });
    rejects([] { count_paired_height_survivors(601, vector<int>(601)); });
    rejects([] { count_paired_height_survivors(2, {4}); });
    rejects([] { count_paired_height_survivors(2, {1, 2, 4}); });
    rejects([] { count_paired_height_survivors(2, {2, 2}); });
    rejects([] { count_paired_height_survivors(2, {4, 2}); });
    rejects([] { count_paired_height_survivors(2, {0, 4}); });
    rejects([] { count_paired_height_survivors(2, {-1, 4}); });
    rejects([] { count_paired_height_survivors(2, {2, 5}); });
    cout << "API contract: 10 rejection cases, no mutation, repeated calls\n";
}

int main() {
    exhaustive_simulations();
    exact_and_modular_checks();
    contract_checks();
    cout << "paired-height survivor checks passed\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", type=Path, default=Path(__file__).resolve().parent.parent / "src/content/docs/techniques/paired-height-survivors-weighted-dyck-dp.mdx")
    parser.add_argument("--cxx", default=shutil.which("g++") or shutil.which("clang++") or "g++")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    compiler = shutil.which(args.cxx)
    if compiler is None:
        parser.error(f"C++ compiler unavailable: {args.cxx}")
    article = args.article.resolve()
    text = article.read_text(encoding="utf-8")
    fences = re.findall(r"^```cpp\s*\n(.*?)^```\s*$", text, re.M | re.S)
    if len(fences) != 1:
        parser.error(f"{article}: expected one complete C++ fence, got {len(fences)}")
    expected_sections = ["使う場面", "考え方", "適用条件", "なぜ正しいか", "計算量", "実装", "関連する手法", "参考資料"]
    if re.findall(r"^## (.+)$", text, re.M) != expected_sections:
        parser.error("article must have the eight required sections in order")
    if "<details" in text or "<summary" in text:
        parser.error("technique and implementation must remain visible")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-ruins-build-") as directory:
        directory = Path(directory)
        source, executable = directory / "check.cpp", directory / "check"
        source.write_text(fences[0] + "\n" + TESTS, encoding="utf-8")
        flags = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"]
        if args.sanitize:
            flags += ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
        subprocess.run([compiler, *flags, str(source), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
