#!/usr/bin/env python3
"""Extract visible C++20; compare to first-visit game trees and all fixed policies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS = r'''
#include <array>
#include <chrono>
#include <climits>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <sys/resource.h>
#include <type_traits>
using Arc=repeated_target::Arc;using Solution=repeated_target::Solution;using V=std::vector<int>;using Arcs=std::vector<Arc>;using Graph=std::vector<V>;
std::uint64_t checks=0,api_calls=0,checksum=0,small_graphs=0,small_cases=0,first_starts=0,first_nodes=0,fixed_pairs=0,functional_starts=0;
std::uint64_t random_small=0,random_large=0,certificate_calls=0,metamorphic=0,invalid_cases=0;
void require(bool ok,const char*message){++checks;if(!ok)throw std::runtime_error(message);}
void record(std::uint64_t v){checksum=checksum*1000003ULL+v;}
Graph graph(int n,const Arcs&arcs){Graph g(n);for(auto[u,v]:arcs)g[u].push_back(v);return g;}
Solution api(const V&a,const V&r,const Arcs&edges){++api_calls;auto answer=repeated_target::solve_repeated_target_game(a,r,edges);
 require(answer.winning.size()==a.size()&&answer.move.size()==a.size(),"return sizes");require(answer.deletion_rounds>=0&&answer.deletion_rounds<=int(a.size()),"round range");
 for(int x:answer.winning){require(x==0||x==1,"binary winners");record(x);}record(answer.deletion_rounds);return answer;}
// Literal first-visit permanent-switch rules. No reachability-attractor recurrence.
bool first_visit(int start,const V&a,const V&r,const Graph&g){++first_starts;V path,position(a.size(),-1);
 auto search=[&](auto&&self,int v)->bool{++first_nodes;if(position[v]>=0){for(int i=position[v];i<int(path.size());++i)if(r[path[i]])return true;return false;}
  position[v]=int(path.size());path.push_back(v);bool result=a[v]==0;
  for(int w:g[v]){const bool child=self(self,w);if(a[v])result=result||child;else result=result&&child;}
  path.pop_back();position[v]=-1;return result;};return search(search,start);}
bool fixed_outcome(int start,const V&r,const V&next){++functional_starts;V position(r.size(),-1),path;int v=start;
 while(position[v]<0){position[v]=int(path.size());path.push_back(v);v=next[v];}for(int i=position[v];i<int(path.size());++i)if(r[path[i]])return true;return false;}
std::vector<V> policies(int player,const V&a,const Graph&g){V choices(a.size());for(int v=0;v<int(a.size());++v)choices[v]=g[v][0];std::vector<V> result;
 auto enumerate=[&](auto&&self,int v)->void{if(v==int(a.size())){result.push_back(choices);return;}if(a[v]!=player){self(self,v+1);return;}
  for(int w:g[v]){choices[v]=w;self(self,v+1);}};enumerate(enumerate,0);return result;}
void all_policies(const V&a,const V&r,const Graph&g,const Solution&answer,const V&literal){const int n=int(a.size());const auto pa=policies(1,a,g),pb=policies(0,a,g);
 std::vector<V> all_a(pa.size(),V(n,1)),all_b(pb.size(),V(n,1));int actual_a=-1,actual_b=-1;
 for(int i=0;i<int(pa.size());++i){bool same=true;for(int v=0;v<n;++v)if(a[v]&&pa[i][v]!=answer.move[v])same=false;if(same)actual_a=i;}
 for(int j=0;j<int(pb.size());++j){bool same=true;for(int v=0;v<n;++v)if(!a[v]&&pb[j][v]!=answer.move[v])same=false;if(same)actual_b=j;}
 require(actual_a>=0&&actual_b>=0,"returned choices form legal complete policies");V next(n);
 for(int i=0;i<int(pa.size());++i)for(int j=0;j<int(pb.size());++j){++fixed_pairs;for(int v=0;v<n;++v)next[v]=a[v]?pa[i][v]:pb[j][v];
  for(int s=0;s<n;++s){const bool win=fixed_outcome(s,r,next);all_a[i][s]&=win;all_b[j][s]&=!win;
   if(i==actual_a&&answer.winning[s])require(win,"returned A policy loses against some fixed B policy");
   if(j==actual_b&&!answer.winning[s])require(!win,"returned B policy loses against some fixed A policy");}}
 for(int s=0;s<n;++s){bool aw=false,bw=false;for(const auto&p:all_a)aw|=p[s];for(const auto&p:all_b)bw|=p[s];
  require(aw!=bw,"fixed-policy quantifiers do not determine a side");require(aw==bool(literal[s])&&bw==!bool(literal[s]),"first-visit minimax versus all complete fixed policies");}}
// SCC is used ONLY as an independent certificate checker for the returned fixed
// policies; it never computes a winning region or an attractor.
void certify(const V&a,const V&r,const Arcs&edges,const Solution&answer){++certificate_calls;const int n=int(a.size());const auto g=graph(n,edges);
 for(int v=0;v<n;++v)require(std::find(g[v].begin(),g[v].end(),answer.move[v])!=g[v].end(),"strategy uses an original outgoing arc");
 for(int side=0;side<=1;++side){Graph h(n),rev(n);V active(n,0);
  for(int v=0;v<n;++v)if(answer.winning[v]==side){active[v]=side==0||!r[v];
   for(int w:g[v])if(a[v]!=side||w==answer.move[v]){require(answer.winning[w]==side,"strategy region is not closed");
    if((side==0||!r[v])&&(side==0||!r[w])){h[v].push_back(w);rev[w].push_back(v);}}}
  V seen(n,0),order;for(int root=0;root<n;++root)if(active[root]&&!seen[root]){std::vector<std::pair<int,std::size_t>> stack{{root,0}};seen[root]=1;
   while(!stack.empty()){auto&[v,i]=stack.back();if(i==h[v].size()){order.push_back(v);stack.pop_back();}else{const int w=h[v][i++];if(!seen[w]){seen[w]=1;stack.emplace_back(w,0);}}}}
  V component(n,-1),sizes,charged;for(auto it=order.rbegin();it!=order.rend();++it)if(component[*it]<0){const int id=int(sizes.size());sizes.push_back(0);charged.push_back(0);V stack{*it};component[*it]=id;
   while(!stack.empty()){const int v=stack.back();stack.pop_back();++sizes[id];charged[id]|=r[v];for(int w:rev[v])if(component[w]<0){component[w]=id;stack.push_back(w);}}}
  for(int v=0;v<n;++v)if(active[v])for(int w:h[v])if(component[v]==component[w]&&(v==w||sizes[component[v]]>1)){
   require(side==0&&!charged[component[v]],side==1?"A fixed strategy permits a target-free cycle":"B fixed strategy permits a target-bearing cycle");}
 }}
void literal_case(const V&a,const V&r,const Arcs&edges,bool exhaustive_assignment=false){const auto g=graph(int(a.size()),edges);const auto before_a=a,before_r=r;const auto before_edges=edges;auto answer=api(a,r,edges);V expected(a.size());
 for(int s=0;s<int(a.size());++s){expected[s]=first_visit(s,a,r,g);require(answer.winning[s]==expected[s],"literal first-visit minimax");}all_policies(a,r,g,answer,expected);
 require(a==before_a&&r==before_r&&edges==before_edges,"input mutation");if(exhaustive_assignment)++small_cases;}
void graph_assignments(int n,const Arcs&edges){++small_graphs;for(int am=0;am<(1<<n);++am)for(int rm=1;rm<(1<<n);++rm){V a(n),r(n);for(int v=0;v<n;++v){a[v]=(am>>v)&1;r[v]=(rm>>v)&1;}literal_case(a,r,edges,true);}}
void exhaustive(){for(int n=1;n<=3;++n){Arcs edges;auto rows=[&](auto&&self,int u)->void{if(u==n){graph_assignments(n,edges);return;}
  for(int mask=1;mask<(1<<n);++mask){const auto size=edges.size();for(int v=0;v<n;++v)if(mask>>v&1)edges.emplace_back(u,v);self(self,u+1);edges.resize(size);}};rows(rows,0);}
 // Every N=4 total graph with at most one branching vertex and degree<=2.
 const int n=4;for(int branch=-1;branch<n;++branch){Arcs edges;auto rows=[&](auto&&self,int u)->void{if(u==n){graph_assignments(n,edges);return;}
  if(u==branch){for(int x=0;x<n;++x)for(int y=x+1;y<n;++y){edges.emplace_back(u,x);edges.emplace_back(u,y);self(self,u+1);edges.pop_back();edges.pop_back();}}
  else for(int v=0;v<n;++v){edges.emplace_back(u,v);self(self,u+1);edges.pop_back();}};rows(rows,0);}}
Arcs random_edges(int n,int maximum_degree,std::mt19937&rng){Arcs result;for(int u=0;u<n;++u){V destinations(n);std::iota(destinations.begin(),destinations.end(),0);std::shuffle(destinations.begin(),destinations.end(),rng);
 const int degree=1+int(rng()%std::min(n,maximum_degree));for(int i=0;i<degree;++i)result.emplace_back(u,destinations[i]);}return result;}
void random_tests(){std::mt19937 rng(20170730);for(int test=0;test<500;++test){const int n=4+int(rng()%5);V a(n),r(n);for(int&x:a)x=rng()&1;for(int&x:r)x=rng()&1;r[rng()%n]=1;
  literal_case(a,r,random_edges(n,3,rng),false);++random_small;}
 for(int test=0;test<1000;++test){const int n=2+int(rng()%69);V a(n),r(n);for(int&x:a)x=rng()&1;for(int&x:r)x=rng()%5==0;r[rng()%n]=1;auto edges=random_edges(n,15,rng);const auto answer=api(a,r,edges);certify(a,r,edges,answer);++random_large;
  std::shuffle(edges.begin(),edges.end(),rng);const auto shuffled=api(a,r,edges);require(answer.winning==shuffled.winning&&answer.move==shuffled.move&&answer.deletion_rounds==shuffled.deletion_rounds,"arc-order invariance");++metamorphic;
  V permutation(n);std::iota(permutation.begin(),permutation.end(),0);std::shuffle(permutation.begin(),permutation.end(),rng);V changed_a(n),changed_r(n);for(int v=0;v<n;++v){changed_a[permutation[v]]=a[v];changed_r[permutation[v]]=r[v];}
  Arcs changed_edges;for(auto[u,v]:edges)changed_edges.emplace_back(permutation[u],permutation[v]);auto relabeled=api(changed_a,changed_r,changed_edges);for(int v=0;v<n;++v)require(relabeled.winning[permutation[v]]==answer.winning[v],"vertex relabeling");certify(changed_a,changed_r,changed_edges,relabeled);++metamorphic;
  V extra=r;for(int&x:extra)if(rng()%3==0)x=1;const auto more=api(a,extra,edges);for(int v=0;v<n;++v)require(!answer.winning[v]||more.winning[v],"adding targets cannot hurt A");certify(a,extra,edges,more);++metamorphic;
 }}
void reject(const V&a,const V&r,const Arcs&edges){++api_calls;bool caught=false;try{(void)repeated_target::solve_repeated_target_game(a,r,edges);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid generic input accepted");++invalid_cases;}
void reject_adapter(const V&a,const V&r,const V&u,const V&v){++api_calls;bool caught=false;try{(void)who_wins(a,r,u,v);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid callback input accepted");++invalid_cases;}
void api_cases(){using Callback=V(*)(V,V,V,V);static_assert(std::is_same_v<decltype(&who_wins),Callback>);
 ++api_calls;require(who_wins({0,1},{1,0},{0,0,1,1},{0,1,0,1})==V({1,1}),"official example");
 for(int owner=0;owner<=1;++owner){literal_case({owner},{1},{{0,0}});literal_case({owner},{0},{{0,0}},false);}
 reject({}, {}, {});reject(V(5001,0),V(5001,1),{});reject({0},{},{{0,0}});reject({-1},{1},{{0,0}});reject({2},{1},{{0,0}});reject({INT_MAX},{1},{{0,0}});reject({0},{-1},{{0,0}});reject({0},{2},{{0,0}});
 reject({0},{1},{});reject({0},{1},{{0,0},{0,0}});reject({0,1},{1,0},Arcs(20001,{0,0}));reject({0,1},{1,0},{{0,0},{0,0}});reject({0,1},{1,0},{{0,0},{0,1}});
 for(int bad:std::array<int,4>{INT_MIN,-1,2,INT_MAX}){reject({0,1},{1,0},{{bad,0},{1,1}});reject({0,1},{1,0},{{0,bad},{1,1}});}
 reject_adapter({}, {}, {}, {});reject_adapter(V(5001,0),V(5001,1),{},{});reject_adapter({0},{},{0},{0});reject_adapter({0},{1},{0},{});reject_adapter({0},{0},{0},{0});reject_adapter({0},{2},{0},{0});reject_adapter({2},{1},{0},{0});reject_adapter({0,1},{1,0},{0,0},{0,0});reject_adapter({0},{1},{-1},{0});
 const V a{0,1,0,1},r{1,0,0,1};const Arcs edges{{0,0},{0,1},{1,2},{2,1},{2,3},{3,3}};const auto expected=api(a,r,edges);
 for(int call=0;call<100;++call){auto copy=expected;auto moved=std::move(copy);require(moved.winning==expected.winning&&moved.move==expected.move,"result copy/move");moved.winning.assign(100,7);moved.move.clear();auto alternate=api({0,0},{0,0},{{0,1},{1,0}});require(alternate.winning==V({0,0}),"empty target extension");const auto again=api(a,r,edges);require(again.winning==expected.winning&&again.move==expected.move&&again.deletion_rounds==expected.deletion_rounds,"call isolation and owned return values");}
}
struct Maximum{std::string name;int n,m,rounds,winning;};std::vector<Maximum> max_records;
void maximum_case(const std::string&name,const V&a,const V&r,const Arcs&edges,const V&expected,int rounds=-1){const auto answer=api(a,r,edges);require(answer.winning==expected,"maximum closed-form winners");if(rounds>=0)require(answer.deletion_rounds==rounds,"maximum exact deletion rounds");certify(a,r,edges,answer);
 V u,v;for(auto[x,y]:edges){u.push_back(x);v.push_back(y);}if(std::find(r.begin(),r.end(),1)!=r.end()){++api_calls;require(who_wins(a,r,u,v)==expected,"maximum source adapter");}
 max_records.push_back({name,int(a.size()),int(edges.size()),answer.deletion_rounds,std::accumulate(answer.winning.begin(),answer.winning.end(),0)});}
Arcs filled(int n,Arcs edges,int maximum,bool keep_last_sink=false){std::set<Arc> present(edges.begin(),edges.end());
 for(int u=0;u<n&&int(edges.size())<maximum;++u){if(keep_last_sink&&u==n-1)continue;for(int v=0;v<n&&int(edges.size())<maximum;++v)if(present.emplace(u,v).second)edges.emplace_back(u,v);}return edges;}
void rounds_case(int k,bool maximum){const int n=2*k+1+(maximum?1:0);V a(n,1),r(n,0);Arcs edges{{0,0}};if(maximum)edges.emplace_back(n-1,n-1);
 for(int i=1;i<=k;++i){const int c=2*i-1,x=2*i;r[c]=1;edges.emplace_back(c,i==1?0:2*(i-1));edges.emplace_back(x,x);edges.emplace_back(x,c);}
 if(maximum){for(int i=1;i<=k&&edges.size()<20000;++i)for(int j=1;j<i&&edges.size()<20000;++j)edges.emplace_back(2*i,2*j);
  maximum_case("5000 vertices,20000 arcs,2500 elimination rounds",a,r,edges,V(n,0),k+1);}
 else{literal_case(a,r,edges);const auto answer=api(a,r,edges);require(answer.deletion_rounds==k+1,"small linear-round family");}}
void maximum_tests(){for(int k=1;k<=3;++k)rounds_case(k,false);const int n=5000;V a(n),r(n,1);for(int v=0;v<n;++v)a[v]=(v*17+v/3)&1;Arcs loops;for(int v=0;v<n;++v)loops.emplace_back(v,v);
 maximum_case("5000 vertices,20000 arcs,all targets",a,r,filled(n,loops,20000),V(n,1),0);
 Arcs cycle;for(int v=0;v<n;++v)cycle.emplace_back(v,(v+1)%n);r.assign(n,0);r[n-1]=1;maximum_case("5000-cycle,exact charging gap5000",a,r,cycle,V(n,1),0);
 Arcs chain;for(int v=0;v<n;++v)chain.emplace_back(v,std::min(v+1,n-1));a.assign(n,1);maximum_case("5000-chain to charging sink,20000 arcs",a,r,filled(n,chain,20000),V(n,1),0);
 a.assign(n,0);V only_last(n,0);only_last[n-1]=1;maximum_case("all B,noncharging selfloops,20000 arcs",a,r,filled(n,loops,20000,true),only_last);
 r.assign(n,0);r[0]=1;maximum_case("long chain,transient charge then noncharging sink",a,r,chain,V(n,0));
 r.assign(n,0);maximum_case("5000 vertices,empty-target generic extension",a,r,filled(n,loops,20000),V(n,0),1);
 r.assign(n,0);for(int i=0;i<n/2;++i)r[i]=1;maximum_case("disconnected selfloops,mixed winners",a,r,loops,r,1);
 rounds_case(2499,true);
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_cases();exhaustive();random_tests();maximum_tests();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"exhaustiveGraphs\":"<<small_graphs<<",\"exhaustiveAssignments\":"<<small_cases<<",\"firstVisitInitialPositions\":"<<first_starts<<",\"firstVisitSearchNodes\":"<<first_nodes
 <<",\"fixedPolicyPairs\":"<<fixed_pairs<<",\"fixedPolicyInitialPositions\":"<<functional_starts<<",\"randomSmallGraphs\":"<<random_small<<",\"randomLargeGraphs\":"<<random_large<<",\"strategyCertificates\":"<<certificate_calls<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCases\":"<<invalid_cases
 <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";bool comma=false;
 for(const auto&x:max_records){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<x.name<<"\",\"n\":"<<x.n<<",\"m\":"<<x.m<<",\"deletionRounds\":"<<x.rounds<<",\"AWinningVertices\":"<<x.winning<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/buchi-owned-graph-repeated-target-attractor-elimination.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-train-cpp-') as directory:
        source=Path(directory)/'check.cpp'
        binary=Path(directory)/'check'
        source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS']='halt_on_error=1'
        result=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),
                     'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),
                     'sanitize':args.sanitize,'compilerFlags':flags,**json.loads(result.stdout)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
