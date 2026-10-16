"""Compare the eight published range-pattern snippets against independent models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
HELPERS=r'''
using namespace std;
vector<pair<int,int>> all_ranges(int n){vector<pair<int,int>> out;for(int l=0;l<=n;++l)for(int r=l;r<=n;++r)out.push_back({l,r});return out;}
long long model_singletons(const vector<long long>& a){long long answer=0;for(int l=0;l<int(a.size());++l){map<long long,int> count;for(int r=l;r<int(a.size());++r){++count[a[r]];for(auto [v,c]:count){(void)v;if(c==1)++answer;}}}return answer;}
int model_run(const string& s,int l,int r,char bit){int best=0,current=0;for(int i=l;i<r;++i){current=s[i]==bit?current+1:0;best=max(best,current);}return best;}
long long model_nonadjacent(const vector<long long>& a,int l,int r){int n=r-l;long long best=0;for(unsigned mask=0;mask<(1u<<n);++mask)if((mask&(mask<<1))==0){long long sum=0;for(int i=0;i<n;++i)if(mask>>i&1)sum+=a[l+i];best=max(best,sum);}return best;}
int main(){using namespace tested;mt19937_64 rng(1944751000522);
'''
CASES={
'fixed-window-min-mex-gaps':r'''
    auto check=[](const vector<int>& a){int n=a.size();for(int width=1;width<=n;++width){int expected=n+1;for(int l=0;l+width<=n;++l){set<int> present(a.begin()+l,a.begin()+l+width);int mex=0;while(present.count(mex))++mex;expected=min(expected,mex);}assert(minimum_window_mex(a,width)==expected);}};
    for(int n=1,power=3;n<=8;++n,power*=3)for(int code=0;code<power;++code){int x=code;vector<int>a(n);for(auto&v:a){v=x%3;x/=3;}check(a);}
    for(int trial=0;trial<800;++trial){int n=1+rng()%70;vector<int>a(n);for(auto&x:a)x=rng()%(2*n+1);check(a);}
    bool thrown=false;try{minimum_window_mex({-1},1);}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=1500000;vector<int>a(n);assert(minimum_window_mex(a,n)==1 && minimum_window_mex(a,1)==1);iota(a.begin(),a.end(),0);assert(minimum_window_mex(a,n)==n && minimum_window_mex(a,n-1)==0);
''',
'subarray-fold-value-runs':r'''
    auto check=[](const vector<uint32_t>& a,bool positive){map<uint32_t,long long> gcds,ors;for(int l=0;l<int(a.size());++l){uint32_t g=0,o=0;for(int r=l;r<int(a.size());++r){g=gcd(g,a[r]);o|=a[r];++gcds[g];++ors[o];}}assert(subarray_or_histogram(a)==ors);if(positive)assert(subarray_gcd_histogram(a)==gcds);};
    check({},true);
    for(int n=1,power=4;n<=6;++n,power*=4)for(int code=0;code<power;++code){int x=code;vector<uint32_t>a(n);for(auto&v:a){v=x%4;x/=4;}check(a,false);for(auto&v:a)++v;check(a,true);}
    for(int trial=0;trial<1200;++trial){int n=rng()%70;vector<uint32_t>a(n);for(auto&x:a)x=1+rng()%1000000000;check(a,true);}
    bool thrown=false;try{subarray_gcd_histogram({0});}catch(const invalid_argument&){thrown=true;}assert(thrown);
    check({UINT32_MAX,1,UINT32_MAX,0},false);
    int n=200000;auto g=subarray_gcd_histogram(vector<uint32_t>(n,UINT32_MAX));assert(g.size()==1 && g.begin()->second==1LL*n*(n+1)/2);
    vector<uint32_t>a(n);for(int i=0;i<n;++i)a[i]=uint32_t(1)<<(i%32);auto o=subarray_or_histogram(a);long long total=0;for(auto [value,count]:o){(void)value;total+=count;}assert(total==1LL*n*(n+1)/2 && o.count(UINT32_MAX));
''',
'singleton-subarray-contribution':r'''
    for(int n=0,power=1;n<=8;++n,power*=3)for(int code=0;code<power;++code){int x=code;vector<long long>a(n);for(auto&v:a){v=x%3;x/=3;}assert(total_singleton_occurrences(a)==model_singletons(a));}
    for(int trial=0;trial<900;++trial){int n=rng()%55;vector<long long>a(n);for(auto&v:a)v=int(rng()%19)-9;assert(total_singleton_occurrences(a)==model_singletons(a));}
    assert(total_singleton_occurrences({LLONG_MIN,LLONG_MAX,LLONG_MIN})==8);
    int n=200000;assert(total_singleton_occurrences(vector<long long>(n,7))==n);vector<long long>a(n);iota(a.begin(),a.end(),0LL);assert(total_singleton_occurrences(a)==1LL*n*(n+1)*(n+2)/6);
''',
'offline-range-singleton-witness':r'''
    auto check=[](const vector<long long>& a){auto queries=all_ranges(a.size());reverse(queries.begin(),queries.end());auto answer=range_singleton_values(a,queries);assert(answer.size()==queries.size());for(int q=0;q<int(queries.size());++q){auto [l,r]=queries[q];map<long long,int> count;for(int i=l;i<r;++i)++count[a[i]];bool exists=false;for(auto [v,c]:count){(void)v;exists|=c==1;}assert(bool(answer[q])==exists);if(answer[q])assert(count[*answer[q]]==1);}};
    for(int n=0,power=1;n<=7;++n,power*=3)for(int code=0;code<power;++code){int x=code;vector<long long>a(n);for(auto&v:a){v=x%3;x/=3;}check(a);}
    for(int trial=0;trial<300;++trial){int n=rng()%35;vector<long long>a(n);for(auto&v:a)v=int(rng()%15)-7;check(a);}
    check({LLONG_MIN,0,LLONG_MAX,0});assert(range_singleton_values({0},{{0,1}})[0]==optional<long long>(0));
    int n=500000;vector<long long>a(n);vector<pair<int,int>> queries;for(int i=0;i<n;++i){a[i]=i%1000;queries.push_back({i,i+1});}auto answer=range_singleton_values(a,queries);for(int i=0;i<n;++i)assert(answer[i]==optional<long long>(a[i]));assert(!range_singleton_values(a,{{0,n}})[0]);
''',
'flip-longest-binary-run':r'''
    for(int n=0;n<=8;++n)for(unsigned mask=0;mask<(1u<<n);++mask){string s(n,'0');for(int i=0;i<n;++i)if(mask>>i&1)s[i]='1';BinaryRuns tree(s);for(auto [l,r]:all_ranges(n)){tree.flip(l,r);for(int i=l;i<r;++i)s[i]^=1;for(auto [a,b]:all_ranges(n))for(int bit=0;bit<2;++bit)assert(tree.longest(a,b,bit)==model_run(s,a,b,'0'+bit));tree.flip(l,r);for(int i=l;i<r;++i)s[i]^=1;}}
    for(int trial=0;trial<500;++trial){int n=1+rng()%100;string s(n,'0');for(auto& c:s)c='0'+rng()%2;BinaryRuns tree(s);for(int q=0;q<300;++q){int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);if(rng()%2){tree.flip(l,r);for(int i=l;i<r;++i)s[i]^=1;}else for(int bit=0;bit<2;++bit)assert(tree.longest(l,r,bit)==model_run(s,l,r,'0'+bit));}}
    int n=500000;BinaryRuns tree(string(n,'0'));tree.flip(0,n);assert(tree.longest(0,n)==n);tree.flip(123,456789);assert(tree.longest(0,n)==n-456789);tree.flip(123,456789);assert(tree.longest(0,n)==n);for(int i=0;i<100000;++i){tree.flip(i,i+1);assert(tree.longest(i,i+1)==0);}assert(tree.longest(0,n)==n-100000);
''',
'point-update-nonadjacent-max-sum':r'''
    for(int n=0,power=1;n<=7;++n,power*=3)for(int code=0;code<power;++code){int x=code;vector<long long>a(n);for(auto&v:a){v=x%3-1;x/=3;}NonadjacentSum tree(a);for(auto [l,r]:all_ranges(n))assert(tree.maximum(l,r)==model_nonadjacent(a,l,r));assert(tree.maximum_all()==model_nonadjacent(a,0,n));}
    for(int trial=0;trial<700;++trial){int n=1+rng()%11;vector<long long>a(n);for(auto&v:a)v=int(rng()%31)-15;NonadjacentSum tree(a);for(int q=0;q<100;++q){int pos=rng()%n;long long value=int(rng()%41)-20;a[pos]=value;tree.set(pos,value);int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);assert(tree.maximum(l,r)==model_nonadjacent(a,l,r));assert(tree.maximum_all()==model_nonadjacent(a,0,n));}}
    int n=200000;NonadjacentSum tree(vector<long long>(n,1));assert(tree.maximum_all()==n/2);for(int i=0;i<n;i+=2)tree.set(i,-1000000000);assert(tree.maximum_all()==n/2);NonadjacentSum negative(vector<long long>(n,-1000000000));assert(negative.maximum_all()==0);negative.set(0,1000000000);negative.set(1,1000000000);assert(negative.maximum_all()==1000000000);negative.set(2,1000000000);assert(negative.maximum_all()==2000000000);
''',
'range-modulo-halving':r'''
    for(int n=1,power=4;n<=6;++n,power*=4)for(int code=0;code<power;++code){int x=code;vector<long long>a(n);for(auto&v:a){v=x%4;x/=4;}for(auto [l,r]:all_ranges(n))for(int mod=1;mod<=6;++mod){ModuloSum tree(a);auto expected=a;tree.modulo(l,r,mod);for(int i=l;i<r;++i)expected[i]%=mod;for(auto [ql,qr]:all_ranges(n))assert(tree.sum(ql,qr)==accumulate(expected.begin()+ql,expected.begin()+qr,0LL));}}
    for(int trial=0;trial<400;++trial){int n=1+rng()%100;vector<long long>a(n);for(auto&v:a)v=rng()%1000000001;ModuloSum tree(a);for(int q=0;q<400;++q){int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);switch(rng()%3){case 0:{long long mod=1+rng()%1000000001;tree.modulo(l,r,mod);for(int i=l;i<r;++i)a[i]%=mod;break;}case 1:{int p=rng()%n;long long value=rng()%1000000001;tree.set(p,value);a[p]=value;break;}default:assert(tree.sum(l,r)==accumulate(a.begin()+l,a.begin()+r,0LL));}}}
    bool thrown=false;try{ModuloSum({1}).modulo(0,1,0);}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=200000;ModuloSum tree(vector<long long>(n,1000000000));long long value=1000000000;while(value){long long mod=value/2+1;tree.modulo(0,n,mod);value%=mod;assert(tree.sum(0,n)==n*value);}for(int i=0;i<50000;++i){tree.set(i,1000000000);assert(tree.sum(0,n)==1000000000);tree.modulo(0,n,1);assert(tree.sum(0,n)==0);}
''',
'offline-range-equal-gap':r'''
    auto check=[](const vector<long long>& a){auto queries=all_ranges(a.size());reverse(queries.begin(),queries.end());auto answer=range_equal_minimum_gaps(a,queries);for(int q=0;q<int(queries.size());++q){auto [l,r]=queries[q];int expected=INT_MAX;for(int i=l;i<r;++i)for(int j=i+1;j<r;++j)if(a[i]==a[j])expected=min(expected,j-i);assert(answer[q]==(expected==INT_MAX?-1:expected));}};
    for(int n=0,power=1;n<=7;++n,power*=3)for(int code=0;code<power;++code){int x=code;vector<long long>a(n);for(auto&v:a){v=x%3;x/=3;}check(a);}
    for(int trial=0;trial<300;++trial){int n=rng()%40;vector<long long>a(n);for(auto&v:a)v=int(rng()%19)-9;check(a);}check({LLONG_MAX,LLONG_MIN,LLONG_MAX});
    int n=500000;vector<long long>a(n);iota(a.begin(),a.end(),0LL);vector<pair<int,int>> queries;for(int i=0;i<n;++i)queries.push_back({0,i+1});auto answer=range_equal_minimum_gaps(a,queries);for(int x:answer)assert(x==-1);fill(a.begin(),a.end(),7);answer=range_equal_minimum_gaps(a,queries);for(int i=0;i<n;++i)assert(answer[i]==(i==0?-1:1));
'''
}
def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='range-pattern-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr
if __name__=='__main__':
    rows=json.loads((ROOT/'data/range-pattern-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
