#!/usr/bin/env python3
"""Check the actual LCS and polynomial reconstruction examples against independent models."""

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
    "lcs-hirschberg-reconstruction",
    "polynomial-interpolation-product-tree",
    "lagrange-consecutive-values",
)


def extracted_source():
    """Keep each published implementation intact, isolated from other helper names."""
    includes = set()
    examples = []
    for slug in ARTICLES:
        article = SITE / "src/content/docs/techniques" / (slug + ".mdx")
        matches = FENCE.findall(article.read_text(encoding="utf8"))
        if len(matches) != 1:
            raise ValueError(f"{article.name}: expected exactly one complete C++ example")
        source = matches[0]
        for include in re.findall(r"^#include[^\n]*$", source, re.M):
            includes.add(include)
        source = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.M)
        namespace = "article_" + slug.replace("-", "_")
        examples.append(f"namespace {namespace} {{\n{source}\n}}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <cassert>
#include <iostream>
#include <limits>
#include <random>
#include <set>
using namespace std;
using article_lcs_hirschberg_reconstruction::lcs_hirschberg;
using article_polynomial_interpolation_product_tree::polynomial_interpolate;
using article_lagrange_consecutive_values::ConsecutiveLagrange;

template<class Sequence>
int full_table_lcs_length(const Sequence& a,const Sequence& b) {
    vector<vector<int>> table(a.size()+1,vector<int>(b.size()+1));
    for(size_t i=0;i<a.size();++i) for(size_t j=0;j<b.size();++j)
        table[i+1][j+1]=a[i]==b[j]?table[i][j]+1:max(table[i][j+1],table[i+1][j]);
    return table.back().back();
}

template<class Sequence>
bool is_subsequence(const Sequence& subsequence,const Sequence& sequence) {
    size_t matched=0;
    for(const auto& value:sequence)
        if(matched<subsequence.size() && value==subsequence[matched]) ++matched;
    return matched==subsequence.size();
}

template<class Sequence>
void check_lcs(const Sequence& a,const Sequence& b) {
    const auto a_before=a,b_before=b;
    auto result=lcs_hirschberg(a,b);
    assert(a==a_before && b==b_before);
    assert(is_subsequence(result,a) && is_subsequence(result,b));
    assert(int(result.size())==full_table_lcs_length(a,b));
}

int oracle_power(int value,int exponent,int modulus) {
    long long answer=1,base=value;
    while(exponent) {
        if(exponent&1) answer=answer*base%modulus;
        base=base*base%modulus;
        exponent>>=1;
    }
    return int(answer);
}

int horner(const vector<int>& coefficients,long long point,int modulus) {
    point%=modulus;
    if(point<0) point+=modulus;
    long long answer=0;
    for(auto it=coefficients.rbegin();it!=coefficients.rend();++it)
        answer=(answer*point+*it)%modulus;
    return int(answer);
}

// Newton divided differences are independent of the product tree, polynomial
// division, NTT, and the prefix/suffix products used in the articles.
vector<int> quadratic_interpolant(const vector<int>& points,const vector<int>& values,int modulus) {
    const int n=points.size();
    vector<int> divided=values,result(n),basis{1};
    for(int width=1;width<n;++width) for(int i=n-1;i>=width;--i) {
        int numerator=(divided[i]-divided[i-1]+modulus)%modulus;
        int denominator=(points[i]-points[i-width]+modulus)%modulus;
        divided[i]=1LL*numerator*oracle_power(denominator,modulus-2,modulus)%modulus;
    }
    for(int i=0;i<n;++i) {
        for(int k=0;k<=i;++k) result[k]=(result[k]+1LL*basis[k]*divided[i])%modulus;
        vector<int> next(basis.size()+1);
        for(size_t k=0;k<basis.size();++k) {
            next[k]=(next[k]+1LL*basis[k]*(modulus-points[i]))%modulus;
            next[k+1]=(next[k+1]+basis[k])%modulus;
        }
        basis=move(next);
    }
    return result;
}

int main(int argc,char** argv) {
    // Contracts fail before any undefined inverse or unrelated out-of-bounds access.
    if(argc>1) {
        string mode=argv[1];
        if(mode=="duplicate-points") { (void)polynomial_interpolate({7,7},{1,2});return 0; }
        if(mode=="mismatched-sizes") { (void)polynomial_interpolate({7},{});return 0; }
        if(mode=="empty-consecutive") { ConsecutiveLagrange interpolation({});return 0; }
        if(mode=="degree-at-least-modulus") { ConsecutiveLagrange interpolation({0,1,2,3,4,0},5);return 0; }
        return 2;
    }

    mt19937 rng(20261015);
    auto random=[&](int limit){return int(rng()%unsigned(limit));};

    vector<string> binary_strings;
    for(int n=0;n<=5;++n) for(int mask=0;mask<(1<<n);++mask) {
        string value;
        for(int i=0;i<n;++i) value+=char('a'+((mask>>i)&1));
        binary_strings.push_back(value);
    }
    for(const auto& a:binary_strings) for(const auto& b:binary_strings) check_lcs(a,b);
    for(int trial=0;trial<1200;++trial) {
        string a(random(29),'a'),b(random(29),'a');
        for(auto& value:a) value=char('a'+random(5));
        for(auto& value:b) value=char('a'+random(5));
        check_lcs(a,b);
        vector<int> x(random(25)),y(random(25));
        for(auto& value:x) value=random(11)-5;
        for(auto& value:y) value=random(11)-5;
        check_lcs(x,y);
    }
    check_lcs(string(100,'a'),string(70,'a'));
    check_lcs(string("abc"),string("xyz"));
    check_lcs(string("cabcaacb"),string("cabcaacb"));
    // Extreme aspect ratios exercise the choice of the short DP dimension and
    // both input orientations without allocating a giant reference DP table.
    string long_text(300000,'x');
    long_text[0]='a';long_text[150000]='b';long_text.back()='c';
    for(const auto& short_text:{string(),string("abc"),string("cba"),string("zzz")}) {
        for(bool reverse_inputs:{false,true}) {
            auto answer=reverse_inputs?lcs_hirschberg(short_text,long_text):lcs_hirschberg(long_text,short_text);
            assert(is_subsequence(answer,long_text) && is_subsequence(answer,short_text));
            const size_t expected=short_text=="abc"?3:short_text=="cba"?1:0;
            assert(answer.size()==expected);
        }
    }
    cout<<"lcs-hirschberg-reconstruction PASS: exhaustive and randomized optimal subsequences\n";

    constexpr int MOD=998244353;
    assert(polynomial_interpolate({},{}).empty());
    assert(polynomial_interpolate({0},{123})==vector<int>{123});
    assert(polynomial_interpolate({MOD-1},{0})==vector<int>{0});
    auto check_product_tree=[&](int n,bool compare_quadratic) {
        vector<int> coefficients(n),points,values;
        for(auto& value:coefficients) value=random(MOD);
        if(n && random(3)==0) coefficients.back()=0;
        if(random(7)==0) fill(coefficients.begin(),coefficients.end(),0);
        set<int> used;
        while(int(points.size())<n) {
            int point=points.empty()?0:random(MOD);
            if(used.insert(point).second) points.push_back(point);
        }
        shuffle(points.begin(),points.end(),rng);
        for(int point:points) values.push_back(horner(coefficients,point,MOD));
        const auto points_before=points,values_before=values;
        auto answer=polynomial_interpolate(points,values);
        assert(points==points_before && values==values_before);
        assert(answer==coefficients);
        if(compare_quadratic) assert(answer==quadratic_interpolant(points,values,MOD));
        for(int sample=0;sample<8;++sample) {
            int point=random(MOD);
            assert(horner(answer,point,MOD)==horner(coefficients,point,MOD));
        }
    };
    for(int trial=0;trial<350;++trial) check_product_tree(random(19),true);
    for(int n:{31,32,33,63,64,65,127,128,129,257,513})
        for(int trial=0;trial<3;++trial) check_product_tree(n,false);
    // Non-polynomial-looking values still determine the unique degree < n interpolant.
    for(int trial=0;trial<120;++trial) {
        int n=1+random(15);
        vector<int> points(n),values(n);
        for(int i=0;i<n;++i) {points[i]=MOD-1-i;values[i]=random(MOD);}
        auto expected=quadratic_interpolant(points,values,MOD);
        assert(polynomial_interpolate(points,values)==expected);
    }
    cout<<"polynomial-interpolation-product-tree PASS: direct interpolation and NTT-sized recovery\n";

    for(int modulus:{5,7,101,998244353,1000000007}) for(int trial=0;trial<180;++trial) {
        int n=1+random(min(modulus,60));
        vector<int> coefficients(n),values(n),points(n);
        for(auto& value:coefficients) value=random(modulus);
        if(trial%5==0) fill(coefficients.begin(),coefficients.end(),0);
        if(trial%7==0) for(int i=1;i<n;++i) coefficients[i]=0;
        for(int i=0;i<n;++i) {points[i]=i;values[i]=horner(coefficients,i,modulus);}
        const auto before=values;
        ConsecutiveLagrange interpolation(values,modulus);
        assert(values==before);
        for(int i=0;i<n;++i) {
            assert(interpolation.evaluate(i)==values[i]);
            assert(interpolation.evaluate(1LL*modulus+i)==values[i]);
            assert(interpolation.evaluate(-1LL*modulus+i)==values[i]);
        }
        const vector<long long> samples={
            -1,-2,-1000000000000000000LL,1000000000000000000LL,
            numeric_limits<long long>::min(),numeric_limits<long long>::max(),
            n,n+1,2LL*n,1LL*modulus-1,1LL*modulus,1LL*modulus+1
        };
        for(long long point:samples)
            assert(interpolation.evaluate(point)==horner(coefficients,point,modulus));
        for(int sample=0;sample<12;++sample) {
            long long point=1LL*random(modulus)*random(1000)-random(modulus);
            assert(interpolation.evaluate(point)==horner(coefficients,point,modulus));
        }
        if(n<=12) {
            auto direct=quadratic_interpolant(points,values,modulus);
            assert(direct==coefficients);
            for(long long point:samples)
                assert(interpolation.evaluate(point)==horner(direct,point,modulus));
        }
    }
    ConsecutiveLagrange default_modulus({2,5,10});
    assert(default_modulus.evaluate(3)==17);

    // Codeforces 622F: S(N) = sum_{i=1}^N i^k has degree at most k+1.
    // Generate the initial samples and all expected answers from the original
    // sum, rather than choosing polynomial coefficients as in the tests above.
    for(int modulus:{101,1000000007}) for(int k=0;k<=8;++k) {
        vector<int> sums(71);
        for(int n=1;n<=70;++n)
            sums[n]=(sums[n-1]+oracle_power(n,k,modulus))%modulus;
        const int degree=k+1;
        vector<int> samples(sums.begin(),sums.begin()+degree+1);
        ConsecutiveLagrange interpolation(samples,modulus);
        for(int n=0;n<=70;++n) assert(interpolation.evaluate(n)==sums[n]);
    }

    // ABC208F: begin with f_0(N)=N^k and take a prefix sum M times.
    // All k+M here are below p, so each summation has a nonzero leading
    // denominator in the field and increases the degree bound by one.
    for(int modulus:{101,1000000007}) for(int k=1;k<=5;++k) {
        vector<int> sequence(51);
        for(int n=1;n<=50;++n) sequence[n]=oracle_power(n,k,modulus);
        for(int repetitions=0;repetitions<=4;++repetitions) {
            if(repetitions) for(int n=1;n<=50;++n)
                sequence[n]=(sequence[n]+sequence[n-1])%modulus;
            const int degree=k+repetitions;
            vector<int> samples(sequence.begin(),sequence.begin()+degree+1);
            ConsecutiveLagrange interpolation(samples,modulus);
            for(int n=0;n<=50;++n) assert(interpolation.evaluate(n)==sequence[n]);
        }
    }
    cout<<"lagrange-consecutive-values PASS: finite-field and signed-64 inputs, power sums, repeated prefix sums\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-reconstruction-cpp-") as directory:
        source = Path(directory) / "comparisons.cpp"
        executable = Path(directory) / "comparisons"
        source.write_text(extracted_source() + "\n" + TESTS, encoding="utf8")
        compiled = subprocess.run(
            [args.compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(SITE / "vendor/ac-library"), str(source), "-o", str(executable)],
            capture_output=True, text=True, timeout=120)
        if compiled.returncode:
            print(compiled.stderr, file=sys.stderr)
            return compiled.returncode
        result = subprocess.run([str(executable)], cwd=directory, timeout=90)
        if result.returncode:
            return result.returncode
        for mode in (
            "duplicate-points", "mismatched-sizes", "empty-consecutive", "degree-at-least-modulus",
        ):
            rejected = subprocess.run([str(executable), mode], cwd=directory, capture_output=True, text=True, timeout=10)
            if rejected.returncode == 0 or "assert" not in rejected.stderr.lower():
                print(f"Expected an assertion failure for {mode}; got {rejected.returncode}: {rejected.stderr}", file=sys.stderr)
                return 1
        print("All 3 reconstruction implementations passed independent comparisons and contract checks.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
