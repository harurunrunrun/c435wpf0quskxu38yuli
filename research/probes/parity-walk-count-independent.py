#!/usr/bin/env python3
"""Complete reachable-set words -> positive edge clauses -> Shannon counting."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile

HARNESS=r'''
#include <bit>
#include <chrono>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
using U=std::uint64_t;
using Edge=std::pair<int,int>;
U checks=0,checksum=0,instances=0,recursion_calls=0,memo_hits=0;
U language_states=0,clause_count=0,allowed_count=0,api_calls=0,maximum_exact=0;
U oracle_crosschecks=0,oracle_graph_assignments=0;
void require(bool b,const char*why){++checks;if(!b)throw std::runtime_error(why);}
void record(int x){checksum=checksum*1000003ULL+U(x+1);++api_calls;}

// Direct Boolean edge-assignment count for a monotone CNF. All arithmetic is
// exact; n<=10 gives <=55 possible edges, so even 2^55 fits uint64_t.
struct Counter {
 std::unordered_map<std::string,U> memo;
 U solve(U available,std::vector<U> clauses) {
  ++recursion_calls;
  for(;;) {
   if(std::any_of(clauses.begin(),clauses.end(),[](U c){return c==0;}))return 0;
   std::sort(clauses.begin(),clauses.end(),[](U a,U b){const int pa=std::popcount(a),pb=std::popcount(b);return pa!=pb?pa<pb:a<b;});
   std::vector<U> minimal;
   for(U clause:clauses)if(std::none_of(minimal.begin(),minimal.end(),[&](U smaller){return (smaller&clause)==smaller;}))minimal.push_back(clause);
   clauses=std::move(minimal);
   U units=0;for(U c:clauses)if(std::has_single_bit(c))units|=c;
   if(!units)break;
   available&=~units;
   std::erase_if(clauses,[&](U c){return bool(c&units);});
  }
  U used=0;for(U c:clauses)used|=c;
  const U free_factor=U(1)<<std::popcount(available&~used);
  if(clauses.empty())return free_factor;
  std::sort(clauses.begin(),clauses.end());
  std::string key;for(U c:clauses)for(int byte=0;byte<8;++byte)key.push_back(char(c>>(8*byte)));
  if(auto it=memo.find(key);it!=memo.end()){++memo_hits;return free_factor*it->second;}
  int best=-1,score=-1;
  for(int bit=0;bit<55;++bit)if(used>>bit&1) {
   int count=0;for(U c:clauses)count+=bool(c>>bit&1);
   if(count>score){score=count;best=bit;}
  }
  const U bit=U(1)<<best;
  auto absent=clauses,present=clauses;
  for(U&c:absent)c&=~bit;
  std::erase_if(present,[&](U c){return bool(c&bit);});
  const U result=solve(used&~bit,std::move(absent))+solve(used&~bit,std::move(present));
  memo.emplace(std::move(key),result);return free_factor*result;
 }
};

U direct_count(int n,const std::vector<Edge>&edges,int root) {
 std::vector<unsigned> adjacency(n);
 for(auto[u,v]:edges){adjacency[u]|=1U<<v;adjacency[v]|=1U<<u;}
 std::vector<unsigned> word;std::vector<int> seen(1U<<n,-1);unsigned state=1U<<root;
 while(seen[state]<0) {
  seen[state]=int(word.size());word.push_back(state);unsigned next=0;
  for(int u=0;u<n;++u)if(state>>u&1)next|=adjacency[u];
  state=next;
 }
 const int cycle=seen[state];language_states+=word.size();
 std::vector<unsigned> next(word.size());
 for(std::size_t t=0;t<word.size();++t)next[t]=word[t+1<word.size()?t+1:std::size_t(cycle)];
 std::vector<Edge> possible;
 for(int u=0;u<n;++u)for(int v=u;v<n;++v) {
  bool allowed=true;
  for(std::size_t t=0;t<word.size();++t)
   if(((word[t]>>u&1)&&!(next[t]>>v&1))||((word[t]>>v&1)&&!(next[t]>>u&1))){allowed=false;break;}
  if(allowed)possible.push_back({u,v});
 }
 allowed_count+=possible.size();
 std::vector<U> clauses;
 for(std::size_t t=0;t<word.size();++t)for(int v=0;v<n;++v)if(next[t]>>v&1) {
  U clause=0;
  for(std::size_t e=0;e<possible.size();++e){auto[a,b]=possible[e];
   if((a==v&&(word[t]>>b&1))||(b==v&&(word[t]>>a&1)))clause|=U(1)<<e;
  }
  clauses.push_back(clause);
 }
 clause_count+=clauses.size();Counter counter;
 const U result=counter.solve((U(1)<<possible.size())-1,std::move(clauses));
 require(result>=1,"original graph is one realization");maximum_exact=std::max(maximum_exact,result);
 return result;
}
std::vector<unsigned> literal_word(int n,const std::vector<Edge>&edges,int root) {
 std::vector<unsigned> adjacency(n);
 for(auto[u,v]:edges){adjacency[u]|=1U<<v;adjacency[v]|=1U<<u;}
 std::vector<int> seen(1U<<n,-1);std::vector<unsigned> result;unsigned at=1U<<root;
 while(seen[at]<0) {
  seen[at]=int(result.size());result.push_back(at);unsigned next=0;
  for(int i=0;i<n;++i)if(at>>i&1)next|=adjacency[i];
  at=next;
 }
 result.insert(result.begin(),unsigned(seen[at]));return result;
}
void crosscheck_oracle() {
 std::mt19937 rng(270113U);
 for(int trial=0;trial<12;++trial) {
  const int n=trial<4?4:5,root=trial%n;
  std::vector<Edge> possible,target;
  for(int i=0;i<n;++i)for(int j=i;j<n;++j)possible.push_back({i,j});
  for(int i=1;i<n;++i)target.push_back({i-1,i});
  if(trial%3==0)target.push_back({trial%n,trial%n});
  if(trial%3==1)target.push_back({0,n-1});
  if(trial%3==2)target.push_back({0,2});
  if(rng()%2)target.push_back({(trial+1)%n,(trial+1)%n});
  std::sort(target.begin(),target.end());target.erase(std::unique(target.begin(),target.end()),target.end());
  const auto want=literal_word(n,target,root);U expected=0;
  for(U mask=0;mask<(U(1)<<possible.size());++mask) {
   std::vector<Edge> candidate;for(std::size_t i=0;i<possible.size();++i)if(mask>>i&1)candidate.push_back(possible[i]);
   expected+=literal_word(n,candidate,root)==want;++oracle_graph_assignments;
  }
  require(direct_count(n,target,root)==expected,"Shannon oracle checked against all labeled edge assignments");++oracle_crosschecks;
 }
}
void verify(int n,const std::vector<Edge>&edges,int root) {
 ++instances;const U expected=direct_count(n,edges,root);
 for(int modulus:{1,4,6,8,9,16,25,49,97,999999937,1000000007,2147483647}) {
  int got=count_graphs_preserving_root_walk_lengths(n,edges,root,modulus);record(got);
  require(got==int(expected%U(modulus)),"reachable-set clauses exact edge-assignment count");
 }
 // Two different composite factorizations exercise arithmetic independently
 // of the exact oracle's graph constraints.
 for(auto [a,b]:{std::pair{4,9},std::pair{25,49}}) {
  int combined=count_graphs_preserving_root_walk_lengths(n,edges,root,a*b);record(combined);
  require(combined%a==int(expected%U(a))&&combined%b==int(expected%U(b)),"composite CRT projections");
 }
}
int main(){auto begin=std::chrono::steady_clock::now();std::mt19937 rng(721913U);
 crosscheck_oracle();
 // Fixed long odd-return paths and two interacting branching regions.
 for(int n=7;n<=10;++n)for(int loop=0;loop<n;++loop) {
  std::vector<Edge> e;for(int v=1;v<n;++v)e.push_back({v-1,v});e.push_back({loop,loop});verify(n,e,0);
  verify(n,e,n-1);
 }
 // Every labeled tree on seven vertices; no loop and one rotating loop/root.
 // This provides all distinct branching shapes without re-enumerating N6.
 for(int code=0;code<16807;++code) {
  int value=code;std::vector<int> prufer(5),degree(7,1);
  for(int&i:prufer){i=value%7;value/=7;++degree[i];}
  std::vector<Edge> edges;
  for(int v:prufer){int leaf=0;while(degree[leaf]!=1)++leaf;edges.push_back({leaf,v});--degree[leaf];--degree[v];}
  int a=0;while(degree[a]!=1)++a;int b=a+1;while(degree[b]!=1)++b;edges.push_back({a,b});
  verify(7,edges,code%7);
  edges.push_back({(code/7)%7,(code/7)%7});verify(7,edges,code%7);
 }
 // General non-tree profiles with multiple cycles/loops and arbitrary root.
 for(int trial=0;trial<1500;++trial) {
  int n=7+int(rng()%4);std::vector<Edge> edges;
  std::vector<std::vector<bool>> have(n,std::vector<bool>(n));
  auto add=[&](int u,int v){if(!have[u][v]){have[u][v]=have[v][u]=true;edges.push_back({u,v});}};
  for(int v=1;v<n;++v)add(v,int(rng()%unsigned(v)));
  const unsigned threshold=unsigned(trial%7)*10;
  for(int u=0;u<n;++u)for(int v=u;v<n;++v)if(rng()%100<threshold)add(u,v);
  verify(n,edges,int(rng()%unsigned(n)));
 }
 std::cout<<"{\"checks\":"<<checks<<",\"instances\":"<<instances<<",\"apiCalls\":"<<api_calls
  <<",\"completeWordStates\":"<<language_states<<",\"candidateEdges\":"<<allowed_count<<",\"rawPositiveClauses\":"<<clause_count
  <<",\"shannonCalls\":"<<recursion_calls<<",\"memoHits\":"<<memo_hits<<",\"oracleCrosschecks\":"<<oracle_crosschecks
  <<",\"oracleGraphAssignments\":"<<oracle_graph_assignments<<",\"maximumExactRealizations\":\""<<maximum_exact
  <<"\",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''

article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/parity-walk-profile-layer-inclusion-exclusion-count.mdx').read_text()
fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
assert len(fences)==1
with tempfile.TemporaryDirectory(prefix='flowchartcp-countgraphs-independent-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(fences[0]+'\n'+HARNESS)
    subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True)
    result=json.loads(subprocess.check_output([str(binary)],text=True))
result['cppSha256']=hashlib.sha256(fences[0].encode()).hexdigest()
result['oracle']='Complete reachable-set word -> per-time positive edge clauses -> exact Shannon variable recursion; no parity profiles/layers/PIE.'
print(json.dumps(result,ensure_ascii=False))
