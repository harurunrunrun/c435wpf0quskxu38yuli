#!/usr/bin/env python3
"""Check the published FPS square root by direct coefficient equations and squaring."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SITE = Path(__file__).resolve().parent.parent
TESTS = r'''
constexpr int P=998244353;
int independent_power(int a,int e) {
    long long result=1,base=a;
    while(e) {if(e%2) result=result*base%P; base=base*base%P; e/=2;}
    return int(result);
}
vector<int> square_direct(const vector<int>& a,int n) {
    vector<int> result(n);
    for(int i=0;i<int(a.size()) && i<n;++i)
        for(int j=0;j<int(a.size()) && i+j<n;++j)
            result[i+j]=(result[i+j]+1LL*a[i]*a[j])%P;
    return result;
}
void check_product(const vector<int>& f,int n) {
    auto before=f;
    auto answer=fps_square_root(f,n);
    assert(f==before);
    int first=0;
    while(first<n && (first>=int(f.size()) || f[first]==0)) ++first;
    bool exists=first==n || (!(first%2) && independent_power(f[first],(P-1)/2)==1);
    assert(bool(answer)==exists);
    if(!answer) return;
    assert(int(answer->size())==n);
    auto product=square_direct(*answer,n);
    for(int i=0;i<n;++i) assert(product[i]==(i<int(f.size())?f[i]:0));
}
vector<int> coefficient_oracle(const vector<int>& f,int n,int first,int root) {
    int length=n-first;
    vector<int> q(length),result(n);
    q[0]=min(root,P-root);
    int inverse=independent_power(2LL*q[0]%P,P-2);
    for(int k=1;k<length;++k) {
        long long value=first+k<int(f.size())?f[first+k]:0;
        for(int i=1;i<k;++i) value=(value-1LL*q[i]*q[k-i])%P;
        value=(value%P+P)%P;
        q[k]=value*inverse%P;
    }
    copy(q.begin(),q.end(),result.begin()+first/2);
    return result;
}
template<class F> void rejects(F f) {
    bool caught=false;
    try {f();} catch(const invalid_argument&) {caught=true;}
    assert(caught);
}
int main() {
    for(int b=1;b<=12000;++b) {
        int residue=1LL*b*b%P;
        auto root=scalar_square_root(residue);
        assert(root && *root==b);
        assert(!scalar_square_root(3LL*residue%P));
    }
    assert(scalar_square_root(0)==optional<int>(0));
    assert(scalar_square_root(1)==optional<int>(1));
    for(int n=0;n<=6;++n) {
        int count=1;
        for(int i=0;i<n;++i) count*=5;
        for(int encoded=0;encoded<count;++encoded) {
            int mask=encoded;
            vector<int> f(n);
            for(int& a:f) {a=mask%5;mask/=5;}
            check_product(f,n);
        }
    }
    mt19937 random(10202026);
    for(int trial=0;trial<7000;++trial) {
        int n=1+random()%95,shift=random()%((n+1)/2),first=2*shift;
        int root=1+random()%(P-1);
        vector<int> f(n+random()%4);
        f[first]=1LL*root*root%P;
        for(int i=first+1;i<int(f.size());++i) f[i]=random()%P;
        auto expected=coefficient_oracle(f,n,first,root);
        auto answer=fps_square_root(f,n);
        assert(answer && *answer==expected);
        if(trial<1000) check_product(f,n);
    }
    check_product({},0);
    check_product({},17);
    check_product({0,0,0,0,1},4);
    check_product({0,0,1,2,1},5);
    check_product({0,0,0,1},4);
    check_product({0,0,0,0,3},5);
    check_product({4},29);
    const int maximum=1<<21;
    vector<int> shifted(maximum-1);
    shifted.back()=4;
    auto boundary=fps_square_root(shifted,maximum);
    assert(boundary && int(boundary->size())==maximum);
    for(int i=0;i<maximum;++i) assert((*boundary)[i]==(i==(maximum-2)/2?2:0));
    shifted.push_back(0);
    shifted[maximum-2]=0;shifted.back()=1;
    assert(!fps_square_root(shifted,maximum));
    const int large=500000;
    auto long_answer=fps_square_root({4,12,9},large);
    assert(long_answer && int(long_answer->size())==large);
    for(int i=0;i<large;++i) assert((*long_answer)[i]==(i==0?2:i==1?3:0));
    rejects([]{fps_square_root({},-1);});
    rejects([]{fps_square_root({},(1<<21)+1);});
    rejects([]{fps_square_root(vector<int>((1<<21)+1),0);});
    rejects([]{fps_square_root({-1},0);});
    rejects([]{fps_square_root({P},1);});
    rejects([]{fps_square_root({1,P},1);});
    cout<<"PASS: FPS square root against direct products and coefficient equations; 24000 scalar cases, exhaustive small coefficients, 7000 random series, 500000 terms and API boundaries.\n";
}
'''

def main():
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    article = SITE / 'src/content/docs/techniques/fps-square-root.mdx'
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
    if len(fences) != 1:
        raise ValueError('Expected one complete published C++ implementation')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-fps-square-root-') as directory:
        source = Path(directory) / 'test.cpp'
        binary = Path(directory) / 'test'
        source.write_text(fences[0] + TESTS)
        subprocess.run([compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True, timeout=90)
        subprocess.run([str(binary)], check=True, timeout=180)

if __name__ == '__main__':
    main()
