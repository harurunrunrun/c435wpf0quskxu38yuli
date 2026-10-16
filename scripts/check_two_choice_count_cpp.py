#!/usr/bin/env python3
"""Compare compressed two-choice count DP with complete choice enumeration."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
SITE=Path(__file__).resolve().parent.parent
ARTICLE=Path(sys.argv[1]) if len(sys.argv)>1 else SITE/'src/content/docs/techniques/two-choice-nondecreasing-count-interval-reconstruction.mdx'
TESTS=r'''
vector<bool> brute_counts(const vector<long long>& a,const vector<long long>& b) {
    int n=a.size();vector<bool> possible(n+1);
    for(int mask=0;mask<(1<<n);++mask) {
        bool legal=true;
        for(int i=1;i<n;++i) {
            long long before=(mask>>(i-1)&1)?a[i-1]:b[i-1];
            long long after=(mask>>i&1)?a[i]:b[i];
            if(before>after) {legal=false;break;}
        }
        if(legal) possible[popcount(unsigned(mask))]=true;
    }
    return possible;
}
void validate_answer(const vector<long long>& a,const vector<long long>& b,int k,const string& answer) {
    assert(answer.size()==a.size());
    assert(count(answer.begin(),answer.end(),'A')==k);
    for(int i=0;i<int(a.size());++i) {
        assert(answer[i]=='A' || answer[i]=='B');
        if(i) {
            long long before=answer[i-1]=='A'?a[i-1]:b[i-1];
            long long after=answer[i]=='A'?a[i]:b[i];
            assert(before<=after);
        }
    }
}
void check(const vector<long long>& a,const vector<long long>& b) {
    auto expected=brute_counts(a,b);
    auto old_a=a,old_b=b;
    for(int k=0;k<=int(a.size());++k) {
        auto answer=choose_nondecreasing_two_sources(a,b,k);
        assert(bool(answer)==expected[k]);
        if(answer) validate_answer(a,b,k,*answer);
        assert(a==old_a && b==old_b);
    }
}
template<class F> void rejects(F f) {
    bool caught=false;
    try {f();} catch(const invalid_argument&) {caught=true;}
    assert(caught);
}
int main() {
    long long complete=0;
    for(int n=0;n<=6;++n) {
        int count=1;for(int i=0;i<n;++i) count*=9;
        for(int encoded=0;encoded<count;++encoded) {
            int code=encoded;vector<long long> a(n),b(n);
            for(int i=0;i<n;++i) {a[i]=code%3;b[i]=code/3%3;code/=9;}
            check(a,b);++complete;
        }
    }
    mt19937 random(10202026);
    for(int trial=0;trial<12000;++trial) {
        int n=random()%11;vector<long long>a(n),b(n);
        auto value=[&]() -> long long {
            if(trial%3==0) return random()%2?LLONG_MIN+random()%4:LLONG_MAX-random()%4;
            return int(random()%15)-7;
        };
        for(auto& x:a)x=value();
        for(auto& x:b)x=value();
        check(a,b);
    }
    check({2,5,4,9,15,11},{6,7,6,8,12,14});
    check({1,4,10,20},{3,5,8,13});
    check({3,4,5,6},{10,9,8,7});
    check({25,18,40,37,29,95,41,53,39,69,61,90},{14,18,22,28,18,30,32,32,63,58,71,78});
    check({LLONG_MIN,LLONG_MAX},{LLONG_MAX,LLONG_MIN});
    const int n=1000000;
    vector<long long>a(n),b(n);iota(a.begin(),a.end(),0LL);b=a;
    auto answer=choose_nondecreasing_two_sources(a,b,n/2);
    assert(answer);validate_answer(a,b,n/2,*answer);
    fill(a.begin(),a.end(),LLONG_MIN);fill(b.begin(),b.end(),LLONG_MIN);
    for(int k:{0,n/2,n}) {
        auto tied=choose_nondecreasing_two_sources(a,b,k);
        assert(tied);validate_answer(a,b,k,*tied);
    }
    a[0]=b[0]=LLONG_MAX;
    assert(!choose_nondecreasing_two_sources(a,b,n/2));
    rejects([]{choose_nondecreasing_two_sources({1},{},0);});
    rejects([]{choose_nondecreasing_two_sources({},{},-1);});
    rejects([]{choose_nondecreasing_two_sources({},{},1);});
    rejects([]{choose_nondecreasing_two_sources(vector<long long>(1000001),vector<long long>(1000001),0);});
    cout<<"PASS: two-choice nondecreasing count reconstruction; "<<complete
        <<" exhaustive ternary sequence pairs, 12000 random cases, all counts, 1000000 positions and signed 64-bit boundaries.\n";
}
'''
def main():
    compiler=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:raise RuntimeError('A C++20 compiler is required')
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',ARTICLE.read_text(),re.M|re.S)
    if len(fences)!=1:raise ValueError('Expected one published complete C++ fence')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-building-count-') as directory:
        source=Path(directory)/'test.cpp';binary=Path(directory)/'test';source.write_text(fences[0]+TESTS)
        subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=180)
if __name__=='__main__':main()
