#!/usr/bin/env python3
"""Test the published maximal threshold matching DP against matching enumeration."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SITE = Path(__file__).resolve().parent.parent
ARTICLE = SITE / 'src/content/docs/techniques/maximal-threshold-matching-sweep-dp.mdx'

TESTS = r'''
long long brute(const vector<long long>& a, const vector<long long>& b) {
    vector<int> used(b.size(), 0), unmatched;
    function<long long(int)> visit = [&](int i) -> long long {
        if (i == int(a.size())) {
            for (int x : unmatched)
                for (int j = 0; j < int(b.size()); ++j)
                    if (!used[j] && a[x] <= b[j]) return 0;
            return 1;
        }
        unmatched.push_back(i);
        long long answer = visit(i + 1);
        unmatched.pop_back();
        for (int j = 0; j < int(b.size()); ++j) {
            if (used[j] || a[i] > b[j]) continue;
            used[j] = 1;
            answer += visit(i + 1);
            used[j] = 0;
        }
        return answer;
    };
    return visit(0);
}
vector<long long> decode(int code, int n) {
    vector<long long> result(n);
    for (auto& x : result) { x = 1 + code % 3; code /= 3; }
    return result;
}
template<class Function> void rejects(Function f) {
    bool caught = false;
    try { f(); } catch (const invalid_argument&) { caught = true; }
    assert(caught);
}
int main() {
    for (int l = 0; l <= 3; ++l) for (int r = 0; r <= 3; ++r) {
        int left_cases = 1, right_cases = 1;
        for (int i = 0; i < l; ++i) left_cases *= 3;
        for (int i = 0; i < r; ++i) right_cases *= 3;
        for (int x = 0; x < left_cases; ++x)
            for (int y = 0; y < right_cases; ++y) {
                auto a = decode(x, l), b = decode(y, r);
                assert(count_maximal_threshold_matchings(a, b) == brute(a, b));
            }
    }
    mt19937 random(20261015);
    for (int trial = 0; trial < 1800; ++trial) {
        vector<long long> a(random() % 7), b(random() % 7);
        for (auto& x : a) x = 1 + random() % 5;
        for (auto& x : b) x = 1 + random() % 5;
        auto before_a = a, before_b = b;
        assert(count_maximal_threshold_matchings(a, b) == brute(a, b));
        assert(a == before_a && b == before_b);
    }
    assert(count_maximal_threshold_matchings({1,2,3,4}, {1,2,2,3}) == 9);
    constexpr long long MOD = 1000000007;
    long long factorial = 1;
    for (int i = 1; i <= 3000; ++i) factorial = factorial * i % MOD;
    assert(count_maximal_threshold_matchings(vector<long long>(3000,1),
        vector<long long>(3000,1)) == factorial);
    assert(count_maximal_threshold_matchings(vector<long long>(3000,1000000000),
        vector<long long>(3000,1)) == 1);
    assert(count_maximal_threshold_matchings(vector<long long>(3000,1), {1,1})
        == 3000LL * 2999 % MOD);
    assert(count_maximal_threshold_matchings({}, vector<long long>(3000,1)) == 1);
    assert(count_maximal_threshold_matchings(vector<long long>(3000,1), {}) == 1);
    rejects([]{ count_maximal_threshold_matchings({0}, {1}); });
    rejects([]{ count_maximal_threshold_matchings({1}, {-1}); });
    rejects([]{ count_maximal_threshold_matchings({}, {1000000001LL}); });
    rejects([]{ count_maximal_threshold_matchings(vector<long long>(3001,1), {}); });
    rejects([]{ count_maximal_threshold_matchings({}, vector<long long>(3001,1)); });
    cout << "PASS: maximal threshold matching against all small arrays, direct matchings, ties, empty sides and N=3000 boundaries.\n";
}
'''


def main():
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', ARTICLE.read_text(), re.M | re.S)
    if len(fences) != 1:
        raise ValueError('Expected one complete published C++ implementation')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-threshold-matching-') as directory:
        source = Path(directory) / 'test.cpp'
        binary = Path(directory) / 'test'
        source.write_text(fences[0] + TESTS)
        subprocess.run([compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(source), '-o', str(binary)], check=True, timeout=90)
        subprocess.run([str(binary)], check=True, timeout=90)


if __name__ == '__main__':
    main()
