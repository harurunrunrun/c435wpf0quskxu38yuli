#!/usr/bin/env python3
"""Read-only independent review: directed arborescence oracle and allocation faults."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <new>
#include <numeric>
#include <random>
#include <sys/resource.h>
long allocation_countdown=-1;
[[gnu::noinline]] void* operator new(std::size_t n){if(allocation_countdown==0)throw std::bad_alloc();if(allocation_countdown>0)--allocation_countdown;void*p=std::malloc(n?n:1);if(!p)throw std::bad_alloc();return p;}
[[gnu::noinline]] void* operator new[](std::size_t n){return ::operator new(n);}
[[gnu::noinline]] void operator delete(void*p)noexcept{std::free(p);}[[gnu::noinline]] void operator delete[](void*p)noexcept{std::free(p);}
[[gnu::noinline]] void operator delete(void*p,std::size_t)noexcept{std::free(p);}[[gnu::noinline]] void operator delete[](void*p,std::size_t)noexcept{std::free(p);}
using V=std::vector<int>;using ll=std::int64_t;using U=std::uint64_t;
U checks=0,checksum=0,small=0,brute_cases=0,brute_assignments=0,randoms=0,metamorphic=0,max_cases=0,allocation_failures=0,instrumented_calls=0;
U scan_steps=0,paid_steps=0,endpoint_checks=0,max_scans_plus_paid=0;
void require(bool ok,const char*m){++checks;if(!ok)throw std::runtime_error(m);}void record(U x){checksum=checksum*1000003+x;}
struct Arc{int from,to,cost;};
// Chu--Liu/Edmonds: choose cheapest incoming arcs, contract all directed cycles,
// subtract the selected incoming cost at each old target, and continue.
int directed_tree(int n,int root,std::vector<Arc> edges){int total=0;for(;;){V cost(n,1000000),parent(n,-1);for(auto e:edges)if(e.from!=e.to&&e.cost<cost[e.to]){cost[e.to]=e.cost;parent[e.to]=e.from;}cost[root]=0;
 for(int v=0;v<n;++v){require(cost[v]<1000000,"arborescence reachable");total+=cost[v];}V id(n,-1),seen(n,-1);int cycles=0;
 for(int v=0;v<n;++v){int w=v;while(seen[w]!=v&&id[w]<0&&w!=root){seen[w]=v;w=parent[w];}if(w!=root&&id[w]<0){for(int u=parent[w];u!=w;u=parent[u])id[u]=cycles;id[w]=cycles++;}}
 if(cycles==0){return total;}for(int v=0;v<n;++v)if(id[v]<0)id[v]=cycles++;std::vector<Arc> next;for(auto e:edges){const int u=id[e.from],v=id[e.to];if(u!=v)next.push_back({u,v,e.cost-cost[e.to]});}root=id[root];n=cycles;edges=std::move(next);}}
int incoming_brute(int n,int root,const std::vector<Arc>&edges){++brute_cases;std::vector<std::vector<Arc>> incoming(n);for(auto e:edges)if(e.to!=root&&e.from!=e.to)incoming[e.to].push_back(e);V parent(n,-1);int best=INT_MAX;parent[root]=root;
 auto enumerate=[&](auto&&self,int v,int cost)->void{if(v==n){++brute_assignments;for(int start=0;start<n;++start){int w=start,steps=0;while(w!=root&&steps<=n){w=parent[w];++steps;}if(w!=root)return;}best=std::min(best,cost);return;}if(v==root){self(self,v+1,cost);return;}for(auto e:incoming[v]){parent[v]=e.from;self(self,v+1,cost+e.cost);}};enumerate(enumerate,0,0);return best;}
struct Model{ll base;int n,root;std::vector<Arc> edges;};
Model model(const V&p,int s){const int n=int(p.size());ll base=0;int lo=s,hi=s;V cycle(n,-1);std::vector<V> groups;
 for(int v=0;v<n;++v){base+=std::abs(ll(v)-p[v]);if(p[v]!=v){lo=std::min(lo,v);hi=std::max(hi,v);}if(cycle[v]<0){V group;int w=v;do{cycle[w]=int(groups.size());group.push_back(w);w=p[w];}while(w!=v);groups.push_back(std::move(group));}}
 const int count=hi-lo+1;std::vector<V> cost(count,V(count,INT_MAX));for(int v=0;v+1<count;++v)cost[v][v+1]=cost[v+1][v]=2;
 for(const auto&group:groups){if(group.size()==1)continue;const int left=*std::min_element(group.begin(),group.end()),right=*std::max_element(group.begin(),group.end());for(int actual:group)for(int point=left;point<=right;++point)if(point!=actual)cost[actual-lo][point-lo]=0;}
 std::vector<Arc> edges;for(int u=0;u<count;++u)for(int v=0;v<count;++v)if(u!=v&&cost[u][v]!=INT_MAX)edges.push_back({u,v,cost[u][v]});return {base,count,s-lo,edges};}
ll oracle(const V&p,int s,bool brute){const auto x=model(p,s);const int extra=directed_tree(x.n,x.root,x.edges);if(brute)require(extra==incoming_brute(x.n,x.root,x.edges),"Edmonds equals every incoming-parent assignment");return x.base+extra;}
ll instrumented_book_sort_walk(const V&,int);
ll tested(const V&p,int s,ll expected,bool instrument=true){const auto old=p;const ll actual=minimum_single_book_sort_walk(p,s);require(actual==expected&&p==old,"actual fence versus independent arborescence");require(minimum_walk(p,s)==actual,"adapter equals independently verified core");record(actual);
 if(instrument){scan_steps=paid_steps=endpoint_checks=0;const auto measured=instrumented_book_sort_walk(p,s);++instrumented_calls;require(measured==actual,"instrumented copy equals original fence");require(scan_steps+paid_steps<=2*(p.size()-1),"trial union pays/scans each new vertex at most twice");require(endpoint_checks<=4*p.size()-2,"constant endpoint rechecks bounded by paid steps");max_scans_plus_paid=std::max(max_scans_plus_paid,scan_steps+paid_steps);}return actual;}
void exhaustive(){for(int n=1;n<=7;++n){V p(n);std::iota(p.begin(),p.end(),0);do{for(int s=0;s<n;++s){tested(p,s,oracle(p,s,n<=5));++small;}}while(std::next_permutation(p.begin(),p.end()));}}
V stretch(const V&p,int factor,int padding=0){V result(factor*(int(p.size())-1)+1+2*padding);std::iota(result.begin(),result.end(),0);for(int i=0;i<int(p.size());++i)result[padding+factor*i]=padding+factor*p[i];return result;}
void random_cases(){std::mt19937 rng(2017080107);for(int it=0;it<1500;++it){const int n=2+int(rng()%79),s=rng()%n;V p(n);std::iota(p.begin(),p.end(),0);
 if(it%4==0)std::shuffle(p.begin(),p.end(),rng);else if(it%4==1){for(int i=0;i<n/2;++i)if(rng()%3)std::swap(p[i],p[n-1-i]);}else if(it%4==2){for(int i=0;i+2<n;i+=3){p[i]=i+1;p[i+1]=i+2;p[i+2]=i;}}else{for(int t=0;t<2*n;++t){int u=rng()%n,v=rng()%n;if(rng()%5==0)std::swap(p[u],p[v]);}}
 const ll answer=oracle(p,s,false);tested(p,s,answer);++randoms;
 const int factor=1+int(rng()%8),padding=1+int(rng()%8);auto scaled=stretch(p,factor);tested(scaled,factor*s,factor*answer);++metamorphic;
 auto padded=stretch(p,1,padding);tested(padded,padding+s,answer);++metamorphic;
 // Invert independently selected permutation cycles, rather than globally.
 V seen(n,0),changed=p;for(int v=0;v<n;++v)if(!seen[v]){V group;int w=v;do{seen[w]=1;group.push_back(w);w=p[w];}while(w!=v);if(rng()&1)for(int point:group)changed[p[point]]=point;}tested(changed,s,answer);++metamorphic;
 }}
void largest(){std::mt19937 rng(2017080108);const int n=1000000;V reverse(n);for(int i=0;i<n;++i)reverse[i]=n-1-i;tested(reverse,n/2,500000000000LL+n-2);++max_cases;
 for(int it=0;it<18;++it){const int original=11+int(rng()%11),s=rng()%original;V p(original);std::iota(p.begin(),p.end(),0);
  if(it%3==0)std::shuffle(p.begin(),p.end(),rng);else if(it%3==1)for(int i=0;i+1<original;i+=2)std::swap(p[i],p[i+1]);else for(int i=0;i<original/2;++i)if(rng()%3)std::swap(p[i],p[original-1-i]);
  const int factor=(n-1)/(original-1);const auto scaled=stretch(p,factor);tested(scaled,factor*s,factor*oracle(p,s,false));++max_cases;
 }}
void allocations(){for(V p:std::vector<V>{{0},{2,1,0},{0,2,3,1},V(1000000)}){if(p.size()>4)for(int i=0;i<int(p.size());++i)p[i]=int(p.size())-1-i;const int s=int(p.size())/2;const auto original=p;const ll expected=minimum_single_book_sort_walk(p,s);
 for(int adapter=0;adapter<=1;++adapter){int failed=0;for(int index=0;index<20;++index){bool caught=false;ll answer=-1;allocation_countdown=index;try{answer=adapter?minimum_walk(p,s):minimum_single_book_sort_walk(p,s);}catch(const std::bad_alloc&){caught=true;}allocation_countdown=-1;
  require(p==original,"allocation failure leaves caller input unchanged");if(caught){++allocation_failures;++failed;require(minimum_single_book_sort_walk(p,s)==expected,"fresh call after each allocation failure");}else{require(answer==expected,"first nonfailing allocation count has correct result");break;}}
  require(failed==(p.size()==1?1:3)+adapter,"all public allocations fault-injected,including adapter copy");}}}
int main(){try{const auto start=std::chrono::steady_clock::now();exhaustive();random_cases();largest();allocations();require(small==40319&&brute_cases==719,"independent exhaustive scopes");rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"smallPermutationStarts\":"<<small<<",\"bruteIncomingTreeCases\":"<<brute_cases<<",\"bruteIncomingAssignments\":"<<brute_assignments<<",\"randomArborescenceCases\":"<<randoms<<",\"metamorphicChecks\":"<<metamorphic<<",\"millionScaleCases\":"<<max_cases<<",\"allocationFailuresInjected\":"<<allocation_failures<<",\"instrumentedCalls\":"<<instrumented_calls<<",\"maxScannedPlusPaid\":"<<max_scans_plus_paid<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
 }catch(const std::exception&e){allocation_countdown=-1;std::cerr<<e.what()<<'\n';return 1;}}
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/permutation-cycle-interval-closure-two-sided-walk-greedy.mdx').read_text()
    cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)[0]
    assert hashlib.sha256(cpp.encode()).hexdigest()=='320921a0131689953b2ebd74a0bc81a6abe9073fd506576a4c18cb1909af7bd6'
    instrument=cpp.replace('minimum_single_book_sort_walk','instrumented_book_sort_walk').replace('minimum_walk','instrumented_minimum_walk')
    instrument=instrument.replace('const auto extend = [&](int& l, int& r) {','const auto extend = [&](int& l, int& r) {\n        endpoint_checks += 2;')
    instrument=instrument.replace('const int next = wanted_left < l ? --l : ++r;','++scan_steps;\n            const int next = wanted_left < l ? --l : ++r;')
    instrument=instrument.replace('left_cost += 2;','++paid_steps; left_cost += 2;').replace('right_cost += 2;','++paid_steps; right_cost += 2;')
    assert instrument.count('++scan_steps')==1 and instrument.count('++paid_steps')==2
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-books-independent-cpp-') as directory:
        source=Path(directory)/'probe.cpp';binary=Path(directory)/'probe'
        source.write_text(cpp+'\n'+HARNESS+'\n'+instrument)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    print(json.dumps({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitized':args.sanitize,**json.loads(run.stdout)},indent=2))


if __name__=='__main__':
    main()
