#!/usr/bin/env python3
"""Extract the visible MDX C++20; exact infinite-walk-language minimum oracle."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[s for s in sys.argv[1:] if s!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/parity-walk-profile-layer-greedy-realization.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one always-visible C++20 fence')
TESTS=r'''
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <set>
#include <string>
using Edge=std::pair<int,int>;using U=std::uint64_t;
U checks=0,checksum=0,small_graphs=0,language_groups=0,relabel_checks=0,random_cases=0;
U maximum_cases=0,batch_calls=0,invalid_calls=0,dp_comparisons=0;
void need(bool ok,const char* why){++checks;if(!ok){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(int x){checksum=checksum*1000003+U(x)+1;}
int call(int n,const std::vector<Edge>& edges,int root=0){int x=minimum_edges_preserving_root_walk_lengths(n,edges,root);need(x>=n-1&&x<=int(edges.size()),"universal bounds");absorb(x);return x;}
std::vector<int> word(int n,const std::vector<Edge>& edges,int root=0){
 std::vector<int> adjacent(n);for(auto [u,v]:edges){adjacent[u]|=1<<v;adjacent[v]|=1<<u;}
 std::map<int,int> seen;std::vector<int> sequence;int mask=1<<root;
 while(!seen.contains(mask)){
  seen[mask]=int(sequence.size());sequence.push_back(mask);int next=0;
  for(int v=0;v<n;++v)if(mask>>v&1)next|=adjacent[v];
  mask=next;
 }
 // Exact states are also outputs, so first recurrence gives the canonical
 // complete preperiod/period representation without a finite cutoff.
 sequence.insert(sequence.begin(),seen[mask]);return sequence;
}
bool connected(int n,const std::vector<Edge>& edges){
 std::vector<int> seen(n);seen[0]=1;
 for(int pass=0;pass<n;++pass)for(auto [u,v]:edges)if(seen[u]||seen[v])seen[u]=seen[v]=1;
 return std::accumulate(seen.begin(),seen.end(),0)==n;
}
// Slower independent optimization: all possible edge-count choices between
// adjacent buckets, with a DP on the pending count. No greedy exchange rule.
int layer_dp(int n,const std::vector<Edge>& edges,int root){
 const int inf=1000000;std::vector<std::vector<int>> adj(n);for(auto [u,v]:edges){adj[u].push_back(v);adj[v].push_back(u);}
 std::vector<std::array<int,2>> d(n,{inf,inf});std::vector<Edge> queue{{root,0}};d[root][0]=0;
 for(std::size_t z=0;z<queue.size();++z){auto [u,p]=queue[z];for(int v:adj[u])if(d[v][1-p]==inf){d[v][1-p]=d[u][p]+1;queue.push_back({v,1-p});}}
 if(d[root][1]==inf)return n-1;
 std::map<Edge,int> f;std::set<int> layers;for(auto p:d){if(p[0]>p[1])std::swap(p[0],p[1]);++f[{p[0],p[1]}];layers.insert(p[0]+p[1]);}
 auto count=[&](int a,int b){auto it=f.find({a,b});return it==f.end()?0:it->second;};int answer=0;
 for(int sum:layers){
  std::vector<int> dp(1,0);
  for(int a=0;2*a<sum;++a){int b=sum-a,z=count(a,b);bool root_bucket=a==0&&z;
   if(b==a+1){int best=inf;
    for(int p=0;p<int(dp.size());++p)if(dp[p]<inf)
     for(int c=0;c<=z;++c){
      if(root_bucket){if(c)best=std::min(best,dp[p]+c);continue;}
      int missing=z-std::min({z,p,2*c});
      if(missing&&!count(a-1,b-1))continue;
      best=std::min(best,dp[p]+c+missing);
     }
    need(best<inf,"DP terminal feasible");answer+=best;break;
   }
   int next=count(a+1,b-1),cap=std::min(z*next,std::max(z,next));std::vector<int> ndp(cap+1,inf);
   for(int p=0;p<int(dp.size());++p)if(dp[p]<inf)for(int k=0;k<=cap;++k){
    if(root_bucket){if(k)ndp[k]=std::min(ndp[k],dp[p]+k);continue;}
    int missing=z-std::min({z,p,k});if(missing&&!count(a-1,b-1))continue;
    ndp[k]=std::min(ndp[k],dp[p]+k+missing);
   }
   dp=std::move(ndp);
  }
 }
 return answer;
}
void exhaustive(std::mt19937& rng){
 for(int n=2;n<=5;++n){
  std::vector<Edge> possible;for(int u=0;u<n;++u)for(int v=u;v<n;++v)possible.push_back({u,v});
  struct Record {std::vector<Edge> edges;std::vector<int> key;int actual;};
  std::vector<Record> records;std::map<std::vector<int>,int> minimum;
  for(unsigned bits=0;bits<(1u<<possible.size());++bits){
   std::vector<Edge> edges;for(unsigned k=0;k<possible.size();++k)if(bits>>k&1)edges.push_back(possible[k]);
   if(!connected(n,edges))continue;
   auto key=word(n,edges);auto it=minimum.find(key);int m=int(edges.size());
   if(it==minimum.end())minimum.emplace(key,m);else it->second=std::min(it->second,m);
   records.push_back({edges,key,call(n,edges)});++small_graphs;
  }
  language_groups+=minimum.size();
  for(auto& record:records){
   int expected=minimum.at(record.key);need(record.actual==expected,"complete infinite-language minimum");
   need(layer_dp(n,record.edges,0)==expected,"DP oracle crosscheck");++dp_comparisons;
   // Renaming maps original root0 to an arbitrary supplied root; reverse edge
   // endpoints and shuffle input so CSR and duplicate normalization are tested.
   std::vector<int> permutation(n);std::iota(permutation.begin(),permutation.end(),0);std::shuffle(permutation.begin(),permutation.end(),rng);
   auto changed=record.edges;for(auto& [u,v]:changed){u=permutation[u];v=permutation[v];if(rng()&1)std::swap(u,v);}std::shuffle(changed.begin(),changed.end(),rng);
   need(call(n,changed,permutation[0])==expected,"root and input order relabeling");++relabel_checks;
  }
 }
 need(small_graphs==23940&&language_groups==932,"exhaustive scope");
 std::vector<Edge> input{{0,1},{0,2},{1,1},{2,2}},triangle{{0,1},{0,2},{1,2}};
 need(word(3,input)==word(3,triangle),"new edge preserves complete language");
 need(call(3,input)==3,"not restricted to original edges");int best=100;
 for(int bits=0;bits<16;++bits){std::vector<Edge> sub;for(int j=0;j<4;++j)if(bits>>j&1)sub.push_back(input[j]);if(word(3,input)==word(3,sub))best=std::min(best,int(sub.size()));}
 need(best==4,"strict subgraph restriction counterexample");
}
void randomized(std::mt19937& rng){
 for(int trial=0;trial<1600;++trial){
  int n=2+int(rng()%79);std::set<Edge> chosen;
  for(int v=1;v<n;++v){int u=int(rng()%v);chosen.insert({u,v});}
  for(int repeat=0;repeat<n*3;++repeat)if(rng()%3){int u=int(rng()%n),v=int(rng()%n);if(u>v)std::swap(u,v);chosen.insert({u,v});}
  std::vector<Edge> edges(chosen.begin(),chosen.end());int root=int(rng()%n);auto copy=edges;
  need(call(n,edges,root)==layer_dp(n,edges,root),"random count-DP oracle");need(copy==edges,"const input");++random_cases;++dp_comparisons;
 }
}
void maximum(std::mt19937& rng){
 const int n=100000;std::vector<Edge> path;for(int i=1;i<n;++i)path.push_back({i-1,i});
 need(call(n,path)==n-1,"max deep bipartite path");++maximum_cases;
 auto root_loop=path;root_loop.push_back({0,0});need(call(n,root_loop)==n,"max path forced root loop");++maximum_cases;
 need(call(n,root_loop,n-1)==n,"max finite parity distance 2N-1");++maximum_cases;
 std::vector<Edge> leaf_loops;for(int v=1;v<n;++v){leaf_loops.push_back({0,v});leaf_loops.push_back({v,v});}
 need(call(n,leaf_loops)==(n-1)+n/2,"max odd terminal bucket without A");++maximum_cases;
 std::vector<Edge> odd_cycle;for(int i=1;i<n-1;++i)odd_cycle.push_back({i-1,i});odd_cycle.push_back({n-2,0});odd_cycle.push_back({0,n-1});
 need(call(n,odd_cycle)==n,"max odd cycle plus pendant");++maximum_cases;
 std::set<Edge> dense(path.begin(),path.end());
 while(dense.size()<200000){int u=int(rng()%n),v=int(rng()%n);if((u^v)&1){if(u>v)std::swap(u,v);dense.insert({u,v});}}
 std::vector<Edge> edges(dense.begin(),dense.end());need(call(n,edges,n-1)==n-1,"max M bipartite redundant edges");++maximum_cases;
 dense.clear();dense.insert({0,0});for(int v=1;v<n;++v)dense.insert({0,v});
 while(dense.size()<200000){int u=1+int(rng()%(n-1)),v=1+int(rng()%(n-1));if(u>v)std::swap(u,v);dense.insert({u,v});}
 edges.assign(dense.begin(),dense.end());need(call(n,edges)==n,"max M same terminal bucket");++maximum_cases;
 // Repeated instances attain original T and total N without sharing state.
 const std::vector<Edge> a{{0,1}},b{{0,1},{0,0}};
 for(int t=0;t<50000;++t){need(call(2,(t&1)?a:b)==((t&1)?1:2),"max original test count");++batch_calls;}
}
void invalid(){
 auto reject=[](int n,const std::vector<Edge>& edges,int root=0){bool caught=false;try{(void)minimum_edges_preserving_root_walk_lengths(n,edges,root);}catch(const std::invalid_argument&){caught=true;}need(caught,"invalid API");++invalid_calls;};
 reject(-1,{});reject(0,{});reject(1,{{0,0}});reject(100001,{});
 reject(2,{{0,1}},-1);reject(2,{{0,1}},2);reject(2,{{-1,1}});reject(2,{{0,2}});
 reject(2,{{0,1},{1,0}});reject(2,{{0,1},{0,0},{0,0}});reject(2,{});
 reject(3,{{0,1},{0,0}});reject(4,{{0,1},{2,3}});
 std::vector<Edge> too_many;for(int u=0;u<1000&&too_many.size()<200001;++u)for(int v=u;v<1000&&too_many.size()<200001;++v)too_many.push_back({u,v});reject(1000,too_many);
 need(call(2,{{0,1}})==1,"state after invalid input");
}
int main(){auto started=std::chrono::steady_clock::now();std::mt19937 rng(2021117);exhaustive(rng);randomized(rng);maximum(rng);invalid();
 std::cout<<"{\"checks\":"<<checks<<",\"allConnectedLoopGraphsN2to5\":"<<small_graphs<<",\"completeInfiniteLanguageGroups\":"<<language_groups<<",\"rootRelabelingCases\":"<<relabel_checks<<",\"independentDpComparisons\":"<<dp_comparisons<<",\"randomCases\":"<<random_cases<<",\"maximumN100000Cases\":"<<maximum_cases<<",\"maximumBatchCalls\":"<<batch_calls<<",\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";
}
'''
code=blocks[0]
with tempfile.TemporaryDirectory(prefix='flowchartcp-minedges-') as temp:
 cpp=Path(temp)/'check.cpp';binary=Path(temp)/'check';cpp.write_text(code+TESTS)
 flags=['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror']
 if '--sanitize' in sys.argv:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
 subprocess.run(flags+[str(cpp),'-o',str(binary)],check=True)
 env=os.environ.copy()
 if '--sanitize' in sys.argv:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
 result=subprocess.run(['/usr/bin/time','-f','max_rss_kib %M',str(binary)],check=True,env=env,capture_output=True,text=True,timeout=300)
 output=json.loads(result.stdout)
 output['peakRSSKiB']=int(re.search(r'max_rss_kib (\d+)',result.stderr)[1])
 output['sanitized']='--sanitize' in sys.argv
 output['cppSha256']=hashlib.sha256(code.encode()).hexdigest()
 print(json.dumps(output,indent=2))
