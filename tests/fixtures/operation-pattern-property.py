"""Validate eight published operation patterns against exhaustive legal state models."""
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
int main(){mt19937_64 rng(29617881008);
'''
CASES={
'simultaneous-swap-parity':r'''
    auto check_all=[](int n,int colors){int states=1;for(int i=0;i<n;++i)states*=colors;vector<vector<long long>>a(states,vector<long long>(n));vector<vector<int>>swapped(states,vector<int>(n*n));for(int code=0;code<states;++code){int rem=code;for(int i=0;i<n;++i){a[code][i]=rem%colors;rem/=colors;}for(int i=0;i<n;++i)for(int j=0;j<n;++j){auto v=a[code];swap(v[i],v[j]);int next=0,multiplier=1;for(auto x:v){next+=int(x)*multiplier;multiplier*=colors;}swapped[code][i*n+j]=next;}}
        vector<bool>possible(states*states);vector<int>queue;for(int code=0;code<states;++code){int state=code*states+code;possible[state]=true;queue.push_back(state);}for(size_t at=0;at<queue.size();++at){int ca=queue[at]/states,cb=queue[at]%states;for(int i=0;i<n;++i)for(int j=0;j<n;++j)if(i!=j)for(int k=0;k<n;++k)if(k!=i&&k!=j){int next=swapped[ca][i*n+j]*states+swapped[cb][i*n+k];if(!possible[next]){possible[next]=true;queue.push_back(next);}}}for(int ca=0;ca<states;++ca)for(int cb=0;cb<states;++cb)assert(can_match_by_shared_index_swaps(a[ca],a[cb])==possible[ca*states+cb]);};
    check_all(3,3);check_all(4,4);check_all(5,3);
    assert(!can_match_by_shared_index_swaps({0,1,2},{1,0,2}));assert(can_match_by_shared_index_swaps({0,0,1},{0,1,0}));assert(!can_match_by_shared_index_swaps({0,0,1},{0,1,1}));
    vector<long long>a(200000);iota(a.begin(),a.end(),0);auto b=a;swap(b[0],b[1]);assert(!can_match_by_shared_index_swaps(a,b));swap(b[1],b[2]);assert(can_match_by_shared_index_swaps(a,b));
    bool rejected=false;try{can_match_by_shared_index_swaps({0,1},{1,0});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'unequal-multiset-cyclic-shift':r'''
    auto check=[](const vector<long long>&a,vector<long long>b){auto sorted=b;sort(sorted.begin(),sorted.end());bool possible=false;do{bool valid=true;for(int i=0;i<int(a.size());++i)if(a[i]==sorted[i])valid=false;if(valid){possible=true;break;}}while(next_permutation(sorted.begin(),sorted.end()));auto actual=rearrange_to_unequal_values(a,b);assert(bool(actual)==possible);if(actual){sort(b.begin(),b.end());auto result=*actual;sort(result.begin(),result.end());assert(result==b);for(int i=0;i<int(a.size());++i)assert(a[i]!=(*actual)[i]);}};
    for(int n=0;n<=5;++n){vector<vector<long long>>values;vector<long long>v(n);function<void(int,int)>visit=[&](int at,int lower){if(at==n){values.push_back(v);return;}for(int x=lower;x<3;++x){v[at]=x;visit(at+1,x);}};visit(0,0);for(const auto&a:values)for(const auto&b:values)check(a,b);}
    for(int trial=0;trial<700;++trial){int n=rng()%9;vector<long long>a(n),b(n);for(auto&x:a)x=int(rng()%7)-3;for(auto&x:b)x=int(rng()%7)-3;check(a,b);}
    vector<long long>a(200000),b(200000,LLONG_MAX);iota(a.begin(),a.end(),0);auto actual=rearrange_to_unequal_values(a,b);assert(actual && *actual==b);
    a.assign(200000,8);b.assign(200000,9);for(int i=0;i<100000;++i)a[i]=b[i]=7;actual=rearrange_to_unequal_values(a,b);assert(actual);for(int i=0;i<200000;++i)assert(a[i]!=(*actual)[i]);
    assert(!rearrange_to_unequal_values({1,1,2},{1,1,3}));
''',
'additive-sign-sweep':r'''
    auto verify=[](vector<long long>a){auto moves=additive_nondecreasing_operations(a);int n=a.size();assert(moves.size()<=size_t(2*n));vector<__int128>state(a.begin(),a.end());for(auto[from,to]:moves){assert(from>=0&&from<n&&to>=0&&to<n);state[to]+=state[from];}assert(is_sorted(state.begin(),state.end()));long long maximum=0;for(auto v:a)maximum=max(maximum,llabs(v));for(auto v:state)assert(v>=-(__int128)n*maximum&&v<=(__int128)n*maximum);};
    for(int n=0;n<=6;++n){vector<long long>a(n);function<void(int)>visit=[&](int at){if(at==n){verify(a);return;}for(int v=-2;v<=2;++v){a[at]=v;visit(at+1);}};visit(0);}
    auto reachable=[](vector<long long>initial){int n=initial.size();set<vector<long long>>seen{initial};vector<vector<long long>>queue{initial};vector<int>steps{0};for(size_t at=0;at<queue.size();++at){auto state=queue[at];if(is_sorted(state.begin(),state.end()))return true;if(steps[at]==2*n)continue;for(int from=0;from<n;++from)for(int to=0;to<n;++to){auto next=state;next[to]+=next[from];if(llabs(next[to])>n)continue;if(seen.insert(next).second){queue.push_back(next);steps.push_back(steps[at]+1);}}}return false;};
    for(int n=1;n<=3;++n){vector<long long>a(n);function<void(int)>visit=[&](int at){if(at==n){assert(reachable(a));return;}for(int v=-1;v<=1;++v){a[at]=v;visit(at+1);}};visit(0);}
    verify({-1000000000,1000000000,0,-1000000000});verify({1000000000LL,-999999999,0});vector<long long>large(200000);for(int i=0;i<200000;++i)large[i]=(i%2)?-1000000000:1000000000;verify(large);
''',
'special-ball-possibility':r'''
    for(int trial=0;trial<900;++trial){int n=1+rng()%5;vector<int>initial(n,1),count=initial;vector<vector<int>>all{vector<int>(n)};iota(all[0].begin(),all[0].end(),0);vector<pair<int,int>>moves;for(int step=0;step<12;++step){vector<bool>expected(n);for(const auto&location:all)expected[location[0]]=true;assert(possible_special_ball_boxes(initial,0,moves)==expected);vector<int>nonempty;for(int i=0;i<n;++i)if(count[i])nonempty.push_back(i);int from=nonempty[rng()%nonempty.size()],to=rng()%n;moves.push_back({from,to});set<vector<int>>next;for(const auto&state:all)for(int ball=0;ball<n;++ball)if(state[ball]==from){auto location=state;location[ball]=to;next.insert(location);}all.assign(next.begin(),next.end());--count[from];++count[to];}}
    assert(possible_special_ball_boxes({1,1,1},0,{{0,1},{1,2}})==vector<bool>({false,true,true}));
    assert(possible_special_ball_boxes({2,0},0,{{0,1}})==vector<bool>({true,true}));
    assert(possible_special_ball_boxes({1},0,{{0,0}})==vector<bool>({true}));
    int n=200000;vector<pair<int,int>>moves;for(int i=0;i+1<n;++i)moves.push_back({i,i+1});auto result=possible_special_ball_boxes(vector<int>(n,1),0,moves);assert(!result[0]);for(int i=1;i<n;++i)assert(result[i]);
''',
'reserved-occurrence-deadlines':r'''
    auto positions=[](const vector<int>&a,int n){vector<int>count(n),position(n,-1);for(int i=0;i<int(a.size());++i){int value=a[i]-1;assert(value>=0&&value<n);++count[value];if(count[value]==value+1)position[value]=i;}for(int c:count)assert(c==n);return position;};
    for(int n=1;n<=3;++n){vector<int>a;for(int value=1;value<=n;++value)for(int copies=0;copies<n;++copies)a.push_back(value);set<vector<int>>possible;do{possible.insert(positions(a,n));}while(next_permutation(a.begin(),a.end()));vector<int>x(n);vector<bool>used(n*n);function<void(int)>visit=[&](int at){if(at==n){auto result=construct_ranked_occurrences(x);assert(bool(result)==bool(possible.count(x)));if(result)assert(positions(*result,n)==x);return;}for(int p=0;p<n*n;++p)if(!used[p]){used[p]=true;x[at]=p;visit(at+1);used[p]=false;}};visit(0);}
    for(int trial=0;trial<600;++trial){int n=1+rng()%14;vector<int>a;for(int value=1;value<=n;++value)for(int copies=0;copies<n;++copies)a.push_back(value);shuffle(a.begin(),a.end(),rng);auto x=positions(a,n);auto result=construct_ranked_occurrences(x);assert(result&&positions(*result,n)==x);}
    assert(!construct_ranked_occurrences({3,0}));assert(!construct_ranked_occurrences({0,0}));
    int n=500;vector<int>x(n);for(int i=0;i<n;++i)x[i]=i*n+i;auto result=construct_ranked_occurrences(x);assert(result&&positions(*result,n)==x);
''',
'circular-ramp-removal-counts':r'''
    for(int n=1;n<=5;++n){int states=1;for(int i=0;i<n;++i)states*=8;vector<vector<int>>amount(n,vector<int>(n));for(int start=0;start<n;++start)for(int j=0;j<n;++j)amount[start][j]=(j-start-1+n)%n+1;vector<bool>reachable(states);vector<int>queue{0};reachable[0]=true;for(size_t at=0;at<queue.size();++at){int code=queue[at],rem=code;vector<int>a(n);for(auto&v:a){v=rem%8;rem/=8;}for(int start=0;start<n;++start){int next=0,multiplier=1;bool valid=true;for(int j=0;j<n;++j){if(a[j]+amount[start][j]>=8)valid=false;next+=(a[j]+amount[start][j])*multiplier;multiplier*=8;}if(valid&&!reachable[next]){reachable[next]=true;queue.push_back(next);}}}
        for(int code=0;code<states;++code){int rem=code;vector<long long>a(n);for(auto&v:a){v=rem%8;rem/=8;}auto result=circular_ramp_removal_counts(a);assert(bool(result)==reachable[code]);if(result){vector<long long>reconstructed(n);for(int start=0;start<n;++start){assert((*result)[start]>=0);for(int j=0;j<n;++j)reconstructed[j]+=(*result)[start]*amount[start][j];}assert(reconstructed==a);for(int start=0;start<n;++start)for(int times=0;times<(*result)[start];++times)for(int j=0;j<n;++j){a[j]-=amount[start][j];assert(a[j]>=0);}for(auto v:a)assert(v==0);}}
    }
    assert(circular_ramp_removal_counts({4,5,1,2,3}));assert(circular_ramp_removal_counts({6,9,12,10,8}));assert(!circular_ramp_removal_counts({1,2,3,1}));
    int n=200000;vector<long long>a(n,1LL*n*(n+1)/2);auto result=circular_ramp_removal_counts(a);assert(result);for(auto v:*result)assert(v==1);
    assert(circular_ramp_removal_counts({1000000000000LL})==optional<vector<long long>>({1000000000000LL}));
''',
'adjacent-modulo-prime-grid':r'''
    auto verify=[](int n){auto a=adjacent_modulo_one_grid(n);assert(int(a.size())==n);unordered_set<long long>distinct;for(int r=0;r<n;++r){assert(int(a[r].size())==n);for(int c=0;c<n;++c){long long v=a[r][c];assert(1<=v&&v<=1000000000000000LL);assert(distinct.insert(v).second);if(r+1<n){long long u=a[r+1][c];assert(max(u,v)%min(u,v)==1);}if(c+1<n){long long u=a[r][c+1];assert(max(u,v)%min(u,v)==1);}}}};
    for(int n=2;n<=35;++n){verify(n);}
    verify(499);verify(500);
    bool small_possible=false;vector<int>a{2,3,4,5};do{int remainder=max(a[0],a[1])%min(a[0],a[1]);if(remainder>0&&max(a[0],a[2])%min(a[0],a[2])==remainder&&max(a[1],a[3])%min(a[1],a[3])==remainder&&max(a[2],a[3])%min(a[2],a[3])==remainder)small_possible=true;}while(next_permutation(a.begin(),a.end()));assert(small_possible);
    bool rejected=false;try{adjacent_modulo_one_grid(501);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'even-outdegree-orientation':r'''
    auto verify=[](int n,const vector<pair<int,int>>&edges,const vector<pair<int,int>>&direction){assert(direction.size()==edges.size());vector<int>out(n);for(int i=0;i<int(edges.size());++i){auto[u,v]=direction[i];assert((direction[i]==edges[i]||direction[i]==pair<int,int>{edges[i].second,edges[i].first}));++out[u];(void)v;}for(int d:out)assert(d%2==0);};
    auto brute=[](int n,const vector<pair<int,int>>&edges){for(unsigned direction=0;direction<(1u<<edges.size());++direction){vector<int>out(n);for(int i=0;i<int(edges.size());++i){auto[u,v]=edges[i];if(direction>>i&1u)swap(u,v);++out[u];}bool valid=true;for(int d:out)if(d%2)valid=false;if(valid)return true;}return false;};
    for(unsigned mask=0;mask<(1u<<10);++mask){vector<pair<int,int>>edges;int bit=0;for(int u=0;u<5;++u)for(int v=u+1;v<5;++v){if(mask>>bit&1u)edges.push_back({u,v});++bit;}auto result=orient_with_even_outdegrees(5,edges);assert(bool(result)==brute(5,edges));if(result)verify(5,edges,*result);}
    for(int trial=0;trial<1100;++trial){int n=1+rng()%8,m=rng()%12;vector<pair<int,int>>edges;for(int i=0;i<m;++i)edges.push_back({int(rng()%n),int(rng()%n)});auto result=orient_with_even_outdegrees(n,edges);assert(bool(result)==brute(n,edges));if(result)verify(n,edges,*result);}
    assert(!orient_with_even_outdegrees(4,{{0,1},{2,3}}));assert(!orient_with_even_outdegrees(1,{{0,0}}));assert(orient_with_even_outdegrees(1,{{0,0},{0,0}}));
    int n=200000;vector<pair<int,int>>edges;for(int i=0;i+1<n;++i)edges.push_back({i,i+1});assert(!orient_with_even_outdegrees(n,edges));edges.push_back({n-1,0});auto result=orient_with_even_outdegrees(n,edges);assert(result);verify(n,edges,*result);
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    source='#include <bits/stdc++.h>\n'+snippets[0]+'\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='operation-pattern-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=70)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    rows=json.loads((ROOT/'data/operation-pattern-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
