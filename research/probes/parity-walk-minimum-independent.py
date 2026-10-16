#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,subprocess,tempfile
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/parity-walk-profile-layer-greedy-realization.mdx'
cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)[0]
test=r'''
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <unordered_map>
using Edge=std::pair<int,int>;using U=std::uint64_t;
U checks=0,graphs=0,root_cases=0,checksum=0,language_states=0;int max_prefix_cycle_states=0;
void require(bool b,const char* why){++checks;if(!b){std::cerr<<why<<'\n';std::exit(1);}}
std::pair<std::string,bool> word(const std::array<unsigned,6>& adjacent,int root){
 // Exact reachable-set sequence. The set is BOTH state and output; its first
 // repeat is the canonical complete infinite word, with no guessed horizon.
 std::array<int,64> seen;seen.fill(-1);std::string sequence;unsigned state=1U<<root,ever=0;
 while(seen[state]<0){seen[state]=int(sequence.size());sequence.push_back(char(state));ever|=state;unsigned next=0;
  for(int v=0;v<6;++v)if(state>>v&1)next|=adjacent[v];
  state=next;
 }
 language_states+=sequence.size();max_prefix_cycle_states=std::max(max_prefix_cycle_states,int(sequence.size()));
 sequence.insert(sequence.begin(),char(seen[state]));return {sequence,ever==63};
}
std::array<unsigned,6> build(unsigned mask,const std::vector<Edge>& possible){
 std::array<unsigned,6> a{};for(unsigned j=0;j<possible.size();++j)if(mask>>j&1){auto [u,v]=possible[j];a[u]|=1U<<v;a[v]|=1U<<u;}return a;
}
int main(){
 const auto begin=std::chrono::steady_clock::now();std::vector<Edge> possible;
 for(int u=0;u<6;++u)for(int v=u;v<6;++v)possible.push_back({u,v});
 std::unordered_map<std::string,int> minimum;minimum.reserve(100000);
 for(unsigned mask=0;mask<(1U<<21);++mask){const auto [key,connected]=word(build(mask,possible),0);if(!connected)continue;
  const int count=std::popcount(mask);auto [it,inserted]=minimum.emplace(key,count);if(!inserted)it->second=std::min(it->second,count);++graphs;
 }
 require(graphs==1709056,"ALL connected labeled six-vertex graphs, all optional loops, no multiedges");
 for(unsigned mask=0;mask<(1U<<21);++mask){const auto [key,connected]=word(build(mask,possible),0);if(!connected)continue;
  std::vector<Edge> edges;for(unsigned j=0;j<possible.size();++j)if(mask>>j&1)edges.push_back(possible[j]);
  const int want=minimum.at(key),got=minimum_edges_preserving_root_walk_lengths(6,edges);
  require(got==want,"actual fence vs TRUE minimum over EVERY graph with exact same complete infinite language, N6");checksum=checksum*1000003+U(got+1);
  if(mask%2027==0){for(int root=1;root<6;++root){
   std::array<unsigned,6> renamed{};
   auto map=[&](int v){return v==0?root:v==root?0:v;};
   for(auto [u,v]:edges){u=map(u);v=map(v);renamed[u]|=1U<<v;renamed[v]|=1U<<u;}
   const auto [renamedkey,stillconnected]=word(renamed,0);require(stillconnected,"renaming preserves connectivity");
   const int expected=minimum.at(renamedkey);auto changed=edges;std::reverse(changed.begin(),changed.end());for(auto& e:changed)std::swap(e.first,e.second);
   const int answer=minimum_edges_preserving_root_walk_lengths(6,changed,root);
   require(answer==expected,"nonzero original root against independently renamed full-graph optimum; reverse endpoints/order");checksum=checksum*1000003+U(answer+1);++root_cases;
  }}
 }
 std::cout<<"{\"checks\":"<<checks<<",\"allConnectedLoopGraphsN6\":"<<graphs<<",\"completeInfiniteLanguageGroups\":"<<minimum.size()<<",\"extraNonzeroRootCases\":"<<root_cases<<",\"reachableSetStatesProcessed\":"<<language_states<<",\"maximumObservedPrefixCycleStates\":"<<max_prefix_cycle_states<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-minedges-independent-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(cpp+'\n'+test)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(p/'test')],capture_output=True,text=True,check=True,timeout=300)
 output=json.loads(result.stdout);output['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]);output['cppSha256']=hashlib.sha256(cpp.encode()).hexdigest()
 print(json.dumps(output,indent=2))
