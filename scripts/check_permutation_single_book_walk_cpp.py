#!/usr/bin/env python3
"""Actual MDX fence versus physical one-held-item0-1 BFS and cycle-subset DP."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/permutation-cycle-interval-closure-two-sided-walk-greedy.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('one complete always-visible C++20 fence required')
TESTS=r'''
#include <array>
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <deque>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <type_traits>
using ll=std::int64_t;using U=std::uint64_t;
U checks=0,calls=0,adapters=0,literal_inputs=0,literal_states=0,small_inputs=0,subset_calls=0,subset_transitions=0,interval_calls=0,random_subset=0,random_interval=0,metamorphic=0,maximum_cases=0,batch_cases=0,invalid_cases=0,checksum=0;
void require(bool b,const char* message){++checks;if(!b){std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}}
ll base_cost(const std::vector<int>& p){ll sum=0;for(int i=0;i<int(p.size());++i)sum+=std::abs(ll(i)-p[i]);return sum;}
ll call(const std::vector<int>& p,int s,bool adapter=true){
 const auto original=p;const ll answer=minimum_single_book_sort_walk(p,s);++calls;const ll base=base_cost(p);
 require(p==original,"const permutation unchanged");require(base<=answer&&answer<=base+2*ll(p.size()-1),"book transport lower bound and whole-line-tour upper bound");
 require((answer-base)%2==0,"nonessential walk balanced across cuts is even");
 if(adapter){require(minimum_walk(p,s)==answer,"current two-argument value-vector adapter exactly matches core");++adapters;}
 checksum=checksum*1000003+U(answer);return answer;
}
struct Cycles{
 std::vector<std::vector<int>> vertices;std::vector<int> id,low,high;ll base=0;int target_l,target_r;
 Cycles(const std::vector<int>& p,int s):id(p.size(),-1),target_l(s),target_r(s){
  base=base_cost(p);for(int v=0;v<int(p.size());++v)if(p[v]!=v){target_l=std::min(target_l,v);target_r=std::max(target_r,v);}
  std::vector<bool> visited(p.size());for(int v=0;v<int(p.size());++v){if(visited[v])continue;std::vector<int> group;int u=v;
   do{visited[u]=true;group.push_back(u);u=p[u];}while(u!=v);
   if(group.size()==1)continue;
   int c=int(vertices.size());for(int x:group)id[x]=c;low.push_back(*std::min_element(group.begin(),group.end()));high.push_back(*std::max_element(group.begin(),group.end()));vertices.push_back(group);
  }
 }
};
ll subsets(const std::vector<int>& p,int start){
 // Independent exponential DP over activated nontrivial CYCLES. A transition
 // selects any next cycle and directly pays to reach an actual member. Close
 // by explicitly checking actual members in the current visited interval.
 // No left/right first bridge, frontier scan, or greedy decision is used.
 Cycles c(p,start);const int k=int(c.vertices.size());require(k<=15,"independent subset-DP oracle size");const unsigned count=1U<<k;
 auto bounds=[&](unsigned mask){int l=start,r=start;for(int i=0;i<k;++i)if(mask>>i&1){l=std::min(l,c.low[i]);r=std::max(r,c.high[i]);}return std::pair{l,r};};
 auto close=[&](unsigned mask){for(;;){auto [l,r]=bounds(mask);unsigned next=mask;for(int i=0;i<k;++i)if(!(mask>>i&1))
    for(int v:c.vertices[i])if(l<=v&&v<=r){next|=1U<<i;break;}
   if(next==mask)return mask;
   mask=next;
  }};
 std::vector<ll> dp(count,ll{1}<<60);dp[close(0)]=0;
 for(unsigned mask=0;mask<count;++mask){if(dp[mask]==(ll{1}<<60))continue;require(close(mask)==mask,"canonical activated subset");auto [l,r]=bounds(mask);
  for(int i=0;i<k;++i)if(!(mask>>i&1)){int distance=INT_MAX;
   for(int v:c.vertices[i])distance=std::min(distance,v<l?l-v:v>r?v-r:0);
   unsigned next=close(mask|(1U<<i));dp[next]=std::min(dp[next],dp[mask]+2*ll(distance));++subset_transitions;
  }
 }++subset_calls;return c.base+dp.back();
}
ll interval_dp(const std::vector<int>& p,int start){
 // Exhaustive two-dimensional interval DP. Closure rescans ALL interior
 // positions and follows cycle members literally. It deliberately does not
 // use the production boundary-only scan or first-cross exchange proof.
 Cycles c(p,start);const int n=int(p.size());std::vector<ll> memo(n*n,-1);
 auto close=[&](int l,int r){for(;;){int a=l,b=r;for(int v=l;v<=r;++v){int id=c.id[v];if(id>=0){a=std::min(a,c.low[id]);b=std::max(b,c.high[id]);}}
   if(a==l&&b==r)return std::pair{l,r};
   l=a;r=b;
  }};
 std::function<ll(int,int)> solve=[&](int l,int r)->ll{
  auto [a,b]=close(l,r);auto& result=memo[a*n+b];if(result>=0)return result;
  if(a<=c.target_l&&b>=c.target_r)return result=0;
  result=ll{1}<<60;
  if(a>c.target_l)result=std::min(result,2+solve(a-1,b));
  if(b<c.target_r)result=std::min(result,2+solve(a,b+1));
  return result;
 };++interval_calls;return c.base+solve(start,start);
}
const std::array<int,9> factorial{1,1,2,6,24,120,720,5040,40320};
int rank_items(const std::array<int,8>& a,int m){int rank=0;unsigned used=0;for(int i=0;i<m;++i){rank+=int(std::popcount(((1U<<a[i])-1)&~used))*factorial[m-i-1];used|=1U<<a[i];}return rank;}
std::array<int,8> unrank_items(int rank,int m){std::array<int,8> a{},available{};std::iota(available.begin(),available.end(),0);int left=m;
 for(int i=0;i<m;++i){const int unit=factorial[m-i-1],pick=rank/unit;rank%=unit;a[i]=available[pick];for(int j=pick;j+1<left;++j)available[j]=available[j+1];--left;}return a;
}
std::vector<int> physical(int n,int start){
 // State holds the EXACT shelf permutation, one held item (blank=n), and
 // current position. Swap held/current is cost0 (pickup/putdown/swap); walk
 // one adjacent edge is cost1. Reversible graph allows BFS from sorted shelf.
 std::vector<int> distance(factorial[n+1]*n,INT_MAX);std::deque<int> queue;distance[start]=0;queue.push_back(start);
 auto improve=[&](int state,int value,bool zero){if(value<distance[state]){distance[state]=value;if(zero)queue.push_front(state);else queue.push_back(state);}};
 while(!queue.empty()){int state=queue.front();queue.pop_front();int rank=state/n,pos=state%n,value=distance[state];auto items=unrank_items(rank,n+1);
  std::swap(items[pos],items[n]);improve(rank_items(items,n+1)*n+pos,value,true);
  if(pos>0)improve(rank*n+pos-1,value+1,false);
  if(pos+1<n)improve(rank*n+pos+1,value+1,false);
 }
 for(int d:distance)require(d!=INT_MAX,"every literal shelf/held/position state reached");
 literal_states+=distance.size();return distance;
}
void all_small(){
 for(int n=1;n<=8;++n)for(int start=0;start<n;++start){const auto literal=n<=7?physical(n,start):std::vector<int>{};std::vector<int> p(n);std::iota(p.begin(),p.end(),0);U local=0;
  do{ll exact=subsets(p,start);if(n<=7){std::array<int,8> items{};std::copy(p.begin(),p.end(),items.begin());items[n]=n;require(exact==literal[rank_items(items,n+1)*n+start],"independent cycle-subset oracle equals FULL physical held-book0-1 BFS");++literal_inputs;}
   require(call(p,start)==exact,"published linear frontier API matches exact activated-subset optimum");++small_inputs;
   if(n<=6||local%31==0){std::vector<int> reflected(n),inverse(n);for(int i=0;i<n;++i){reflected[n-1-i]=n-1-p[i];inverse[p[i]]=i;}
    require(call(reflected,n-1-start,false)==exact,"reflection of shelf and start");require(call(inverse,start,false)==exact,"inverse permutation through reversing the complete physical sorting walk");metamorphic+=2;
   }++local;
  }while(std::next_permutation(p.begin(),p.end()));
 }
}
void boundaries(){
 static_assert(std::is_same_v<decltype(&minimum_walk),long long(*)(std::vector<int>,int)>);
 static_assert(std::is_same_v<decltype(&minimum_single_book_sort_walk),std::int64_t(*)(const std::vector<int>&,int)>);
 require(call({0},0)==0,"N1 valid with no walk");require(call({0,2,3,1},0)==6,"final official sample6");
 require(call({2,1,0},1)==6,"actual cycle vertex required; hull-overlap gives WRONG4");
 require(call({3,2,1,0},1)==10,"two nested bridge cycles, first left/right costs tied");
 require(call({0,1,2,3,4},3)==0,"identity with arbitrary start returns0 after validation");
 auto bad=[](const std::vector<int>& p,int s){const auto original=p;bool caught=false;try{(void)minimum_single_book_sort_walk(p,s);}catch(const std::invalid_argument&){caught=true;}
  require(caught&&p==original,"invalid core rejects and preserves permutation");caught=false;try{(void)minimum_walk(p,s);}catch(const std::invalid_argument&){caught=true;}require(caught&&p==original,"final adapter preserves invalid-input contract");++invalid_cases;};
 bad({},0);bad({},-1);bad({0},-1);bad({0},1);bad({0},INT_MIN);bad({0},INT_MAX);bad({0,1},2);
 bad({-1},0);bad({INT_MIN},0);bad({INT_MAX},0);bad({1},0);bad({0,0},0);bad({1,1},1);bad({0,2,0},1);bad({0,1,3},1);
 std::vector<int> oversized(1000001);std::iota(oversized.begin(),oversized.end(),0);bad(oversized,0);
 require(call({2,1,0},1)==6,"fresh state following all invalid inputs");
}
void randoms(){std::mt19937 rng(20170801);
 for(int it=0;it<6000;++it){int n=1+int(rng()%30),s=int(rng()%n);std::vector<int> p(n);std::iota(p.begin(),p.end(),0);
  if(it%3==0)std::shuffle(p.begin(),p.end(),rng);
  if(it%3==1)for(int j=0;j<n/2;++j)if(rng()%2)std::swap(p[j],p[n-1-j]);
  if(it%3==2)for(int j=0;j+1<n;j+=2)if(rng()%3)std::swap(p[j],p[j+1]);
  require(call(p,s)==subsets(p,s),"random exact activated-cycle subset DP");require(call(p,s,false)==interval_dp(p,s),"two independent closure representations agree on random inputs");++random_subset;
 }
 for(int it=0;it<2500;++it){int n=1+int(rng()%120),s=int(rng()%n);std::vector<int> p(n);std::iota(p.begin(),p.end(),0);
  if(it%3==0)std::shuffle(p.begin(),p.end(),rng);
  if(it%3==1)for(int j=0;j<n/2;++j)if(rng()%2)std::swap(p[j],p[n-1-j]);
  if(it%3==2)for(int j=0;j+1<n;j+=2)std::swap(p[j],p[j+1]);
  require(call(p,s)==interval_dp(p,s),"larger random ALL interval choices, no greedy assumption");++random_interval;
 }
 for(int it=0;it<20000;++it){require(call(it%2?std::vector<int>{2,1,0}:std::vector<int>{0,2,3,1},it%2?1:0,false)==6,"independent repeated calls with changing permutation/start");++batch_cases;}
}
void maximum(){const int n=1000000;std::vector<int> p(n);std::iota(p.begin(),p.end(),0);
 auto verify=[&](int s,ll expected){require(call(p,s)==expected,"original maximum N1million versus exact independent structural formula");++maximum_cases;};
 verify(0,0);verify(n-1,0);
 for(int i=0;i<n;++i)p[i]=(i+1)%n;
 verify(n/2,2LL*(n-1));
 for(int i=0;i<n;++i)p[i]=n-1-i;
 verify(0,500000000000LL);verify(n/2,500000000000LL+n-2);verify(n/4,500000000000LL+n/2);
 std::iota(p.begin(),p.end(),0);std::swap(p[0],p[n-1]);verify(n/2,3LL*n-4);verify(0,2LL*(n-1));
 for(int i=0;i<n;++i)p[i]=i^1;
 verify(n/3,2LL*(n-1));
 std::iota(p.begin(),p.end(),0);std::swap(p[n-2],p[n-1]);verify(0,2LL*(n-1));verify(n-1,2);
 std::iota(p.begin(),p.end(),0);for(int i=0;i<n;i+=5){p[i]=i+1;p[i+1]=i+2;p[i+2]=i;}verify(0,1999994);verify(n-1,1999998);
 // All vertices lie in one random directed cycle. Its transport sum is an
 // exact lower bound attained from every start without any connection cost.
 std::vector<int> order(n);std::iota(order.begin(),order.end(),0);std::mt19937 rng(2017080102);std::shuffle(order.begin(),order.end(),rng);
 for(int i=0;i<n;++i)p[order[i]]=order[(i+1)%n];
 verify(n/7,base_cost(p));
 require(call({2,1,0},1)==6,"tiny call after all maximum buffers");
}
int main(){auto begin=std::chrono::steady_clock::now();boundaries();all_small();randoms();maximum();
 require(literal_inputs==40319&&literal_states==2177282&&small_inputs==362879,"exact physical/exponential enumeration scopes");
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<calls<<",\"originalAdapterCalls\":"<<adapters<<",\"allPermutationsAndStartsN1to8\":"<<small_inputs<<",\"physicalInputsN1to7\":"<<literal_inputs<<",\"physicalShelfHeldPositionStates\":"<<literal_states<<",\"cycleSubsetOracleCalls\":"<<subset_calls<<",\"cycleSubsetTransitions\":"<<subset_transitions<<",\"exhaustiveIntervalOracleCalls\":"<<interval_calls<<",\"randomSubsetCases\":"<<random_subset<<",\"randomIntervalCases\":"<<random_interval<<",\"reflectionInverseChecks\":"<<metamorphic<<",\"maximumN1millionCases\":"<<maximum_cases<<",\"reentrantBatchCalls\":"<<batch_cases<<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-books-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(src),'-o',str(binary)],check=True,timeout=120)
    process=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if process.returncode:print(process.stdout,end='',file=sys.stderr);print(process.stderr,end='',file=sys.stderr);process.check_returncode()
    result=json.loads(process.stdout);result['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',process.stderr)[1]);result['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();result['sanitized']='--sanitize' in sys.argv
    print(json.dumps(result,ensure_ascii=False,indent=2))
