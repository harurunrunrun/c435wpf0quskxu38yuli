"""Compare the ten published combinatorial snippets with complete small models."""
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
long long model_power(long long x,long long e,long long p){long long r=1;for(;e;e>>=1,x=x*x%p)if(e&1)r=r*x%p;return r;}
long long model_choose(int n,int k){if(k<0 || k>n)return 0;long long r=1;for(int i=1;i<=k;++i)r=r*(n-i+1)/i;return r;}
long long normalized(__int128 x,long long p){x%=p;if(x<0)x+=p;return static_cast<long long>(x);}
string necklace_canonical(string value,bool reflection){string best=value;for(int turn=0;turn<int(value.size());++turn){rotate(value.begin(),value.begin()+1,value.end());best=min(best,value);}if(reflection){reverse(value.begin(),value.end());for(int turn=0;turn<int(value.size());++turn){rotate(value.begin(),value.begin()+1,value.end());best=min(best,value);}}return best;}
long long orbit_model(int n,int colors,bool reflection){set<string> unique;string value(n,'a');function<void(int)> visit=[&](int at){if(at==n){unique.insert(necklace_canonical(value,reflection));return;}for(int color=0;color<colors;++color){value[at]=char('a'+color);visit(at+1);}};visit(0);return unique.size();}
int main(){using namespace tested;mt19937_64 rng(102941567);
'''
CASES={
'burnside-necklace-divisors':r'''
    for(int n=1;n<=8;++n)for(int colors=0;colors<=4;++colors)
        assert(count_rotation_necklaces(n,colors)==orbit_model(n,colors,false));
    for(int n:{1,2,3,4,8,9,12,30,60,997,1000000}){
        assert(count_rotation_necklaces(n,1)==1);
        assert(count_rotation_necklaces(n,0)==0);
    }
    constexpr long long p=1000000007;
    assert(count_rotation_necklaces(1,LLONG_MAX)==LLONG_MAX%p);
    assert(count_rotation_necklaces(4,3)==24);
    for(int n=1;n<=1000;++n){long long sum=0;for(int r=0;r<n;++r)sum=(sum+model_power(13,gcd(n,r),p))%p;assert(count_rotation_necklaces(n,13)==sum*model_power(n,p-2,p)%p);}
    for(int n:{0,-1,1000000007}){bool thrown=false;try{count_rotation_necklaces(n,2);}catch(const invalid_argument&){thrown=true;}assert(thrown);}
''',
'burnside-bracelet-reflections':r'''
    for(int n=1;n<=8;++n)for(int colors=0;colors<=4;++colors){auto result=count_necklaces_and_bracelets(n,colors);assert(result.first==orbit_model(n,colors,false));assert(result.second==orbit_model(n,colors,true));}
    assert(count_necklaces_and_bracelets(5,2)==make_pair(cpp_int(8),cpp_int(8)));
    assert(count_necklaces_and_bracelets(5,5)==make_pair(cpp_int(629),cpp_int(377)));
    auto huge=count_necklaces_and_bracelets(50,10);assert(huge.first>cpp_int(LLONG_MAX) && huge.second>cpp_int(LLONG_MAX));
    auto ten=count_necklaces_and_bracelets(50,1);assert(ten.first==1 && ten.second==1);
    bool thrown=false;try{count_necklaces_and_bracelets(51,2);}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'ballot-prefix-reflection':r'''
    for(int n=0;n<=12;++n){map<string,long long> prefixes;for(unsigned mask=0;mask<(1u<<n);++mask){string s;int h=0;bool valid=true;for(int i=0;i<n;++i){char ch=(mask>>i&1)?'(':')';s+=ch;h+=(ch=='(')?1:-1;if(h<0)valid=false;}if(valid && h==0)for(int k=0;k<=n;++k)++prefixes[s.substr(0,k)];}
        for(int k=0;k<=n;++k)for(unsigned mask=0;mask<(1u<<k);++mask){string s;for(int i=0;i<k;++i)s+=(mask>>i&1)?'(':')';assert(complete_bracket_prefix(n,s)==prefixes[s]);}
    }
    BinomialTable<BALLOT_MOD> table(16);
    for(int l=0;l<=12;++l)for(int h=0;h<=12;++h){long long expected=0;for(unsigned mask=0;mask<(1u<<l);++mask){int height=h;bool valid=true;for(int i=0;i<l;++i){height+=(mask>>i&1)?1:-1;if(height<0)valid=false;}if(valid && height==0)++expected;}assert(ballot_completions(l,h,table)==expected);}
    assert(complete_bracket_prefix(6,"(()")==2);
    assert(complete_bracket_prefix(2,")")==0 && complete_bracket_prefix(2,"(((")==0);
    assert(complete_bracket_prefix(1000000,string(500000,'('))==1);
    bool thrown=false;try{complete_bracket_prefix(2,"x");}catch(const invalid_argument&){thrown=true;}assert(thrown);
    for(int n:{-2,1000000007}){bool rejected=false;try{BinomialTable<BALLOT_MOD> invalid(n);}catch(const invalid_argument&){rejected=true;}assert(rejected);}
''',
'derangement-fixed-count':r'''
    for(int n=0;n<=9;++n){vector<int> order(n);iota(order.begin(),order.end(),0);vector<long long> count(n+1);do{int fixed=0;for(int i=0;i<n;++i)fixed+=(order[i]==i);++count[fixed];}while(next_permutation(order.begin(),order.end()));FixedPointCounts result(n);for(int k=0;k<=n;++k)assert(result.count(k)==count[k]);assert(result.count(-1)==0 && result.count(n+1)==0);}
    FixedPointCounts large(1000000);assert(large.count(1000000)==1 && large.count(999999)==0 && large.count(999998)==999496507);
    assert(FixedPointCounts(4).count(0)==9);
''',
'subset-extrema-rank':r'''
    for(int trial=0;trial<600;++trial){int n=1+rng()%11,k=1+rng()%n;vector<long long> v(n);for(auto& x:v)x=int(rng()%9)-4;__int128 maxima=0,minima=0;for(unsigned mask=0;mask<(1u<<n);++mask)if(popcount(mask)==k){long long lo=LLONG_MAX,hi=LLONG_MIN;for(int i=0;i<n;++i)if(mask>>i&1){lo=min(lo,v[i]);hi=max(hi,v[i]);}maxima+=hi;minima+=lo;}auto actual=subset_extrema_sums(v,k);assert(actual.first==normalized(maxima,EXTREMA_MOD) && actual.second==normalized(minima,EXTREMA_MOD));}
    for(int k=1;k<=3;++k){vector<long long> v{LLONG_MIN,0,LLONG_MAX};__int128 hi=0,lo=0;for(unsigned mask=0;mask<8;++mask)if(popcount(mask)==k){long long a=LLONG_MAX,b=LLONG_MIN;for(int i=0;i<3;++i)if(mask>>i&1){a=min(a,v[i]);b=max(b,v[i]);}hi+=b;lo+=a;}auto actual=subset_extrema_sums(v,k);assert(actual.first==normalized(hi,EXTREMA_MOD) && actual.second==normalized(lo,EXTREMA_MOD));}
    auto sample=subset_extrema_sums({1,1,3,4},2);assert((sample.first-sample.second+EXTREMA_MOD)%EXTREMA_MOD==11);
    auto equal=subset_extrema_sums(vector<long long>(100000,-13),50000);assert(equal.first==equal.second);
''',
'redistribution-zero-count':r'''
    for(int n=3;n<=6;++n){set<vector<int>> exact{vector<int>(n,1)},at_most=exact;for(int k=0;k<=9;++k){assert(redistribution_states(n,k,true)==static_cast<long long>(exact.size()));assert(redistribution_states(n,k,false)==static_cast<long long>(at_most.size()));set<vector<int>> next;for(auto state:exact)for(int i=0;i<n;++i)if(state[i])for(int j=0;j<n;++j)if(i!=j){auto moved=state;--moved[i];++moved[j];next.insert(moved);}exact=move(next);at_most.insert(exact.begin(),exact.end());}
        assert(redistribution_states(n,1000000000LL,true)==model_choose(2*n-1,n-1));
    }
    assert(redistribution_states(3,0,true)==1 && redistribution_states(3,1,true)==6 && redistribution_states(3,1,false)==7);
    assert(redistribution_states(15,6,true)==22583772 && redistribution_states(200000,1000000000LL,true)==607923868);
    bool thrown=false;try{redistribution_states(2,3,true);}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'injective-coordinate-avoidance':r'''
    for(int m=0;m<=6;++m)for(int n=0;n<=m;++n){vector<vector<int>> all;vector<int> values(m);iota(values.begin(),values.end(),0);do{vector<int> prefix(values.begin(),values.begin()+n);all.push_back(prefix);}while(next_permutation(values.begin(),values.end()));sort(all.begin(),all.end());all.erase(unique(all.begin(),all.end()),all.end());long long pairs=0,fixed=0;vector<int> base(n);iota(base.begin(),base.end(),0);for(const auto& a:all){bool good=true;for(int i=0;i<n;++i)if(a[i]==base[i])good=false;if(good)++fixed;for(const auto& b:all){bool unequal=true;for(int i=0;i<n;++i)if(a[i]==b[i])unequal=false;if(unequal)++pairs;}}BinomialTable<INJECTION_MOD> table(m);assert(avoid_fixed_injection(n,m,table)==fixed);assert(count_unequal_injection_pairs(n,m)==pairs);}
    assert(count_unequal_injection_pairs(2,2)==2 && count_unequal_injection_pairs(2,3)==18);
    assert(count_unequal_injection_pairs(141421,356237)==881613484);
    assert(count_unequal_injection_pairs(5,4)==0 && count_unequal_injection_pairs(-1,4)==0);
''',
'grid-active-rows-cols':r'''
    for(int n=1;n<=3;++n)for(int m=1;m<=3;++m){int cells=n*m;vector<vector<long long>> count(cells+1,vector<long long>(cells+1));int states=1;for(int i=0;i<cells;++i)states*=3;for(int encoded=0;encoded<states;++encoded){int rem=encoded,black=0,white=0;vector<vector<int>> grid(n,vector<int>(m));for(int r=0;r<n;++r)for(int c=0;c<m;++c){grid[r][c]=rem%3;rem/=3;black+=grid[r][c]==1;white+=grid[r][c]==2;}bool valid=true;for(int r=0;r<n;++r){int last=0;for(int c=0;c<m;++c)if(grid[r][c]){if(last && last!=grid[r][c])valid=false;last=grid[r][c];}}for(int c=0;c<m;++c){int last=0;for(int r=0;r<n;++r)if(grid[r][c]){if(last && last!=grid[r][c])valid=false;last=grid[r][c];}}if(valid)++count[black][white];}
        for(int b=0;b<=cells;++b)for(int w=0;b+w<=cells;++w)assert(count_separated_two_colors(n,m,b,w)==count[b][w]);
    }
    BinomialTable<GRID_COUNT_MOD> table(9);
    for(int stones=0;stones<=9;++stones){auto actual=active_row_column_counts(3,3,stones,table);for(int n=0;n<=3;++n)for(int m=0;m<=3;++m){long long expected=0;for(unsigned mask=0;mask<(1u<<(n*m));++mask)if(popcount(mask)==stones){unsigned rows=0,cols=0;for(int i=0;i<n*m;++i)if(mask>>i&1){rows|=1u<<(i/m);cols|=1u<<(i%m);}if(rows==(1u<<n)-1 && cols==(1u<<m)-1)++expected;}assert(actual[n][m]==expected);}}
    assert(count_separated_two_colors(2,2,1,1)==4 && count_separated_two_colors(1,2,1,1)==0);
    assert(count_separated_two_colors(40,40,30,30)==467620384);
    bool thrown=false;try{count_separated_two_colors(1,1,INT_MAX,INT_MAX);}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'subset-bounding-box-expectation':r'''
    for(int h=1;h<=4;++h)for(int w=1;w<=4;++w)if(h*w<=12)for(int k=1;k<=h*w;++k){long long sum=0,count=0;for(unsigned mask=0;mask<(1u<<(h*w));++mask)if(popcount(mask)==k){int lo_r=h,hi_r=-1,lo_c=w,hi_c=-1;for(int i=0;i<h*w;++i)if(mask>>i&1){lo_r=min(lo_r,i/w);hi_r=max(hi_r,i/w);lo_c=min(lo_c,i%w);hi_c=max(hi_c,i%w);}sum+=(hi_r-lo_r+1)*(hi_c-lo_c+1);++count;}assert(expected_subset_bounding_box(h,w,k)==sum*model_power(count,BOX_MOD-2,BOX_MOD)%BOX_MOD);}
    assert(expected_subset_bounding_box(2,2,2)==665496238 && expected_subset_bounding_box(10,10,1)==1);
    assert(expected_subset_bounding_box(314,159,2653)==639716353);
    assert(expected_subset_bounding_box(1000,1000,1)==1 && expected_subset_bounding_box(1000,1000,1000000)==1000000);
    bool thrown=false;try{expected_subset_bounding_box(2,2,0);}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'coloring-equal-adjacencies':r'''
    for(int n=1;n<=8;++n)for(int colors=0;colors<=4;++colors){vector<long long> expected(n);vector<int> values(n);function<void(int)> visit=[&](int at){if(at==n){int same=0;for(int i=1;i<n;++i)same+=values[i]==values[i-1];++expected[same];return;}for(int color=0;color<colors;++color){values[at]=color;visit(at+1);}};visit(0);assert(equal_adjacency_counts(n,colors)==expected);}
    auto sample=equal_adjacency_counts(3,2);assert(sample[0]+sample[1]==6);
    assert(equal_adjacency_counts(100,100)[0]==73074801);
    auto large=equal_adjacency_counts(60522,114575);long long sum=0;for(int k=0;k<=7559;++k)sum=(sum+large[k])%COLORING_MOD;assert(sum==479519525);
    auto one=equal_adjacency_counts(200000,1);assert(one.back()==1 && accumulate(one.begin(),one.end(),0LL)==1);
    assert(equal_adjacency_counts(1,LLONG_MAX)[0]==LLONG_MAX%COLORING_MOD);
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
    with tempfile.TemporaryDirectory(prefix='combinatorics-coverage-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=70)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    rows=json.loads((ROOT/'data/combinatorics-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
