#!/usr/bin/env python3
"""Extract the published C++20 fence; compare literal edges and cover-mask DP."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else (Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/line-bipartite-edge-cover-monochromatic-block-prefix-dp.mdx')
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('one complete always-visible C++20 fence required')
TESTS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <type_traits>
using ll=std::int64_t;using U=std::uint64_t;
U checks=0,calls=0,adapter_calls=0,small_cases=0,literal_subsets=0,exponential_calls=0,quadratic_cells=0,prefixes=0,random_small=0,random_medium=0,maximum_cases=0,batch_cases=0,invalid_cases=0,checksum=0;
void require(bool ok,const char* message){++checks;if(!ok){std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}}
ll call(const std::vector<int>& red,const std::vector<int>& blue,bool adapter=true){
 const auto r=red,b=blue;ll got=min_line_bichromatic_edge_cover(red,blue);++calls;
 require(red==r&&blue==b,"all const coordinates unchanged");
 require(got>0&&got<=ll(red.size()+blue.size()-1)*1000000000LL,"positive finite cost and universal two-star upper bound");
 if(adapter){require(min_total_length(red,blue)==got,"exact value-vector original adapter equals const-reference API");++adapter_calls;}
 checksum=checksum*1000003+U(got);return got;
}
ll exponential(const std::vector<int>& red,const std::vector<int>& blue){
 // Weighted set cover on labeled vertices. No sorted blocks, prefix indices,
 // uncrossing, C(k,j), or production recurrence participates in this oracle.
 const int r=int(red.size()),n=r+int(blue.size());require(n<=20&&r>0&&r<n,"small independent exponential oracle domain");
 std::vector<ll> memo(1U<<n,-1);memo[0]=0;
 std::function<ll(unsigned)> solve=[&](unsigned need)->ll{
  auto& result=memo[need];if(result>=0)return result;result=ll{1}<<60;const int v=std::countr_zero(need);
  if(v<r){for(int j=0;j<int(blue.size());++j)result=std::min(result,std::abs(ll(red[v])-blue[j])+solve(need&~(1U<<v)&~(1U<<(r+j))));}
  else{for(int i=0;i<r;++i)result=std::min(result,std::abs(ll(blue[v-r])-red[i])+solve(need&~(1U<<v)&~(1U<<i)));}
  return result;
 };++exponential_calls;return solve((1U<<n)-1);
}
ll literal(const std::vector<int>& red,const std::vector<int>& blue){
 struct Edge{int u,v;ll cost;};std::vector<Edge> edges;const int r=int(red.size()),n=r+int(blue.size());
 for(int i=0;i<r;++i)for(int j=0;j<int(blue.size());++j)edges.push_back({i,r+j,std::abs(ll(red[i])-blue[j])});
 require(edges.size()<=16,"all-edge-subset literal oracle bound");
 std::vector<int> degree(n);int covered=0;ll cost=0,best=ll{1}<<60;unsigned previous=0;
 for(unsigned index=0;index<(1U<<edges.size());++index){
  const unsigned mask=index^(index>>1);if(index){const unsigned change=mask^previous;const auto& e=edges[std::countr_zero(change)];
   if(mask&change){if(degree[e.u]++==0)++covered;if(degree[e.v]++==0)++covered;cost+=e.cost;}
   else{if(--degree[e.u]==0)--covered;if(--degree[e.v]==0)--covered;cost-=e.cost;}
  }
  previous=mask;++literal_subsets;if(covered==n)best=std::min(best,cost);
 }
 return best;
}
ll quadratic(const std::vector<int>& red,const std::vector<int>& blue){
 std::vector<ll> previous(blue.size()+1,ll{1}<<60),current(blue.size()+1,ll{1}<<60);previous[0]=0;
 for(int r:red){current[0]=ll{1}<<60;for(std::size_t j=1;j<=blue.size();++j){
  current[j]=std::min({previous[j],current[j-1],previous[j-1]})+std::abs(ll(r)-blue[j-1]);++quadratic_cells;
 }previous.swap(current);}return previous.back();
}
void small(){
 for(int n=2;n<=12;++n)for(unsigned color=1;color+1<(1U<<n);++color)for(int profile=0;profile<4;++profile){
  std::vector<int> x(n),red,blue;for(int i=0,position=0;i<n;++i){
   if(profile==0)x[i]=i;
   if(profile==1){position+=1+(i*i+3*i)%5;x[i]=position;}
   if(profile==2)x[i]=1000000000-1000+7*i;
   if(profile==3)x[i]=int(1000000000LL*i/(n-1));
   ((color>>i&1)?red:blue).push_back(x[i]);
  }
  ll expected=exponential(red,blue);require(quadratic(red,blue)==expected,"quadratic auxiliary oracle independently agrees with cover-mask DP on all small cases");
  if(n<=8)require(literal(red,blue)==expected,"ALL bipartite edge subsets independently minimize degree>=1 cost");
  require(call(red,blue)==expected,"actual published linear API matches independent exponential optimum");++small_cases;
  require(call(blue,red,false)==expected,"exchange two color names");
  std::vector<int> rr,bb;for(auto i=red.rbegin();i!=red.rend();++i)rr.push_back(1000000000-*i);
  for(auto i=blue.rbegin();i!=blue.rend();++i)bb.push_back(1000000000-*i);
  require(call(rr,bb,false)==expected,"reflection preserves every wire length and reverses all block boundaries");
  if(n<=9){
   // Test every completed production prefix through the public API. The last
   // partial block and all first-block-infinite cases are independently reset.
   std::vector<int> r,b;
   for(int end=0;end<n;++end){((color>>end&1)?r:b).push_back(x[end]);if(r.empty()||b.empty())continue;
    require(call(r,b,false)==exponential(r,b),"every prefix including middle of final block");++prefixes;
   }
  }
 }
}
void boundaries(){
 static_assert(std::is_same_v<decltype(&min_total_length),long long(*)(std::vector<int>,std::vector<int>)>);
 static_assert(std::is_same_v<decltype(&min_line_bichromatic_edge_cover),std::int64_t(*)(const std::vector<int>&,const std::vector<int>&)>);
 require(call({1,2,3,7},{0,4,5,9,10})==10,"official nine-point sample with degree2 point");
 require(call({0,2},{1})==2,"R-B-R NEEDS overlap D[q-k+1], middle point reused");
 require(call({0},{1,2,3,4})==10,"last block longer than left, all j>A rows");
 require(call({0,1,2,3},{4})==10,"first single-color block infinity except D0");
 require(call({0},{1000000000})==1000000000,"largest single-edge length");
 require(call({0,100},{1,2})==99,"a fixed aggregate flow quantity may leave one point uncovered");
 for(const auto& red:std::vector<std::vector<int>>{{0,1,2,1000000000},{0,2,5,9},{1,3,4,8,10}}){
  std::vector<int> blue=red.size()==4&&red.back()==1000000000?std::vector<int>{3,999999997,999999998,999999999}:red[0]==0?std::vector<int>{1,3,4,6,7,8,10}:std::vector<int>{0,2,5,6,7,9,11};
  require(call(red,blue)==exponential(red,blue),"multi-block overlaps and unequal ending runs");
 }
 auto bad=[](const std::vector<int>& red,const std::vector<int>& blue){
  auto r=red,b=blue;bool caught=false;try{(void)min_line_bichromatic_edge_cover(red,blue);}catch(const std::invalid_argument&){caught=true;}
  require(caught&&r==red&&b==blue,"invalid API rejects and preserves caller arrays");
  caught=false;try{(void)min_total_length(red,blue);}catch(const std::invalid_argument&){caught=true;}
  require(caught&&r==red&&b==blue,"original adapter delegates all validation");++invalid_cases;
 };
 bad({},{});bad({},{1});bad({0},{});bad({-1},{1});bad({INT_MIN},{1});bad({0},{INT_MAX});bad({0},{1000000001});
 bad({2,1},{3});bad({0},{2,1});bad({0,0},{1});bad({0},{1,1});bad({0},{0});bad({0,2},{1,2});bad({1,2},{0,1,3});
 std::vector<int> too_long(100001);std::iota(too_long.begin(),too_long.end(),0);bad(too_long,{1000000000});bad({1000000000},too_long);
 const std::vector<int> alias{0,2,4};bad(alias,alias);
 require(call({0,2},{1})==2,"fresh call following all invalid operations");
}
void randoms(){
 std::mt19937_64 rng(2017073002);
 for(int iteration=0;iteration<1800;++iteration){int n=9+int(rng()%10);std::vector<int> red,blue;int position=0;
  for(int i=0;i<n;++i){position+=1+int(rng()%1000000);bool c=i==0?false:i==n-1?true:rng()%2;(c?red:blue).push_back(position);}
  const ll exact=exponential(red,blue);require(call(red,blue)==exact,"random exact weighted-cover mask DP with arbitrary coordinate gaps");
  require(quadratic(red,blue)==exact,"random second oracle cross-check");++random_small;
 }
 for(int iteration=0;iteration<3500;++iteration){int n=2+int(rng()%599);std::vector<int> red,blue;int position=0;
  for(int i=0;i<n;++i){position+=1+int(rng()%10000);bool c=i==0?false:i==n-1?true:rng()%2;(c?red:blue).push_back(position);}
  require(call(red,blue)==quadratic(red,blue),"larger random unsplit quadratic DP, independent of block minima");++random_medium;
 }
 for(int iteration=0;iteration<20000;++iteration){
  if(iteration%3==0)require(call({0,2},{1},false)==2,"reentrant one-point overlap after prior scratch histories");
  if(iteration%3==1)require(call({0},{1,2,3,4},false)==10,"reentrant large last run after shorter call");
  if(iteration%3==2)require(call({1,2,3,7},{0,4,5,9,10},false)==10,"reentrant original sample");
  ++batch_cases;
 }
}
void maximum(){
 const int n=100000;std::vector<int> a(n),b(n);std::iota(a.begin(),a.end(),0);std::iota(b.begin(),b.end(),n);
 auto verify=[&](const std::vector<int>& r,const std::vector<int>& bl,ll expected){require(call(r,bl)==expected,"original maximum point counts and coordinates versus independent closed form");++maximum_cases;};
 verify(a,b,10000000000LL);verify(b,a,10000000000LL);
 for(int i=0;i<n;++i){a[i]=2*i;b[i]=2*i+1;}verify(a,b,n);
 std::iota(a.begin(),a.end(),0);std::iota(b.begin(),b.end(),999900001);verify(a,b,99990000100000LL);
 std::iota(b.begin(),b.end(),1);verify({0},b,5000050000LL);
 std::iota(a.begin(),a.end(),0);verify(a,{1000000000},99995000050000LL);
 verify({0,1000000000},b,5999850000LL);
 // Each original pair contains opposite colors at distance1. Every valid
 // solution uses at least N/2 positive integer-length wires, and these pairs
 // attain the lower bound regardless of how the colors alternate between pairs.
 std::mt19937_64 rng(20170730);a.clear();b.clear();for(int i=0;i<n;++i){bool flip=rng()%2;a.push_back(2*i+int(flip));b.push_back(2*i+int(!flip));}
 verify(a,b,n);verify(b,a,n);
 // The same exact N/2 lower bound survives a translation near coordinate1e9.
 for(int& x:a){x+=999800000;}
 for(int& x:b){x+=999800000;}
 verify(a,b,n);
 require(call({0,2},{1})==2,"fresh tiny prefix after all maximum allocations");
}
int main(){auto begin=std::chrono::steady_clock::now();boundaries();small();randoms();maximum();
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<calls<<",\"originalAdapterCalls\":"<<adapter_calls<<",\"allTwoColorOrdersN2to12FourCoordinateProfiles\":"<<small_cases<<",\"literalAllEdgeSubsetsN2to8\":"<<literal_subsets<<",\"independentExponentialOracleCalls\":"<<exponential_calls<<",\"independentQuadraticCells\":"<<quadratic_cells<<",\"everySmallCompletedPrefix\":"<<prefixes<<",\"randomExactCoverCases\":"<<random_small<<",\"randomQuadraticCases\":"<<random_medium<<",\"maximumCases\":"<<maximum_cases<<",\"reentrantBatchCalls\":"<<batch_cases<<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-wiring-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(src),'-o',str(binary)],check=True,timeout=120)
    process=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if process.returncode:print(process.stdout,end='',file=sys.stderr);print(process.stderr,end='',file=sys.stderr);process.check_returncode()
    result=json.loads(process.stdout);result['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',process.stderr)[1]);result['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();result['sanitized']='--sanitize' in sys.argv
    print(json.dumps(result,ensure_ascii=False,indent=2))
