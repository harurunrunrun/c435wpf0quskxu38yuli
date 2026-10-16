#!/usr/bin/env python3
"""Visible-fence reconstruction versus literal spanning-tree overlap oracles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HEADER = '''#pragma once
#include <vector>
#ifdef TEST_MUTABLE_REF
int count_common_roads(std::vector<int>&);
#else
int count_common_roads(const std::vector<int>&);
#endif
std::vector<int> find_roads(int,std::vector<int>,std::vector<int>);
'''
HARNESS = r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdint>
#include <iostream>
#include <random>
#include <set>
#include <string>
#include <sys/resource.h>
#include <type_traits>
using Edge=tree_overlap::Edge;using Edges=std::vector<Edge>;using V=std::vector<int>;using Result=tree_overlap::Result;
std::uint64_t checks=0,api_calls=0,checksum=0,oracle_queries=0,oracle_entries=0,small_graphs=0,small_trees=0,prufer_cases=0,transcript_filters=0,random_cases=0,metamorphic=0,invalid_cases=0,adapter_calls=0;
void require(bool ok,const char*message){++checks;if(!ok)throw std::runtime_error(message);}
void record(std::uint64_t x){checksum=checksum*1000003ULL+x;}
// Connectivity by literal undirected BFS, independent of the published DSU.
bool literal_tree(int n,const Edges&edges,std::span<const int> ids){if(ids.size()!=static_cast<std::size_t>(n-1))return false;V head(n,-1),to(2*(n-1)),next(2*(n-1));int used=0;
 for(int e:ids){if(e<0||e>=int(edges.size()))return false;auto[u,v]=edges[e];to[used]=v;next[used]=head[u];head[u]=used++;to[used]=u;next[used]=head[v];head[v]=used++;}
 V seen(n,0),queue{0};seen[0]=1;for(std::size_t i=0;i<queue.size();++i)for(int e=head[queue[i]];e>=0;e=next[e]){const int v=to[e];if(!seen[v]){seen[v]=1;queue.push_back(v);}}return int(queue.size())==n;}
struct Context{int n;const Edges&edges;V hidden;std::vector<std::uint64_t> candidates;int calls=0,entries=0;
 int ask(std::span<const int> ids){require(literal_tree(n,edges,ids),"oracle received an illegal spanning tree");int answer=0;std::uint64_t mask=0;
  for(int e:ids){answer+=hidden[e];if(!candidates.empty())mask|=1ULL<<e;}++calls;entries+=n-1;++oracle_queries;oracle_entries+=n-1;
  if(!candidates.empty()){std::vector<std::uint64_t> survivors;for(auto tree:candidates){++transcript_filters;if(std::popcount(tree&mask)==answer)survivors.push_back(tree);}candidates=std::move(survivors);require(!candidates.empty(),"true hidden tree removed from transcript completions");}
  return answer;}};
Context* current_context=nullptr;
#ifdef TEST_MUTABLE_REF
int count_common_roads(std::vector<int>& query){return current_context->ask(query);}
#else
int count_common_roads(const std::vector<int>& query){return current_context->ask(query);}
#endif
V sorted(V x){std::sort(x.begin(),x.end());return x;}
V indicator(const Edges&edges,const V&ids){V h(edges.size(),0);for(int e:ids)h[e]=1;return h;}
Result run(int n,const Edges&edges,const V&ids,const std::vector<std::uint64_t>&candidates={}){require(literal_tree(n,edges,ids),"oracle hidden input must be a tree");Context context{n,edges,indicator(edges,ids),candidates};const auto before=edges;
 ++api_calls;auto result=tree_overlap::recover_hidden_tree(n,edges,[&](std::span<const int> query){return context.ask(query);});
 require(sorted(result.roads)==sorted(ids),"recovered hidden edges");require(literal_tree(n,edges,result.roads),"returned answer is a tree");require(edges==before,"input changed");
 require(result.queries==context.calls&&result.query_entries==context.entries,"query accounting");require(result.queries==result.reference_queries+result.degree_queries+result.search_queries,"stage accounting");
 require(result.reference_queries<=1+2*(n-1)&&result.degree_queries==n,"reference and degree query budgets");const int logarithm=std::bit_width(static_cast<unsigned>(n-2));
 require(result.search_queries<=(n-1)*logarithm&&result.queries<=tree_overlap::query_upper_bound(n),"leaf query upper bound");
 require(result.query_entries==result.queries*(n-1)&&result.query_entries<=2989010,"total query array length");
 require(result.reference.size()==result.reference_membership.size(),"reference labels size");for(int i=0;i<n-1;++i)require(result.reference_membership[i]==context.hidden[result.reference[i]],"every learned reference label is exact");
 if(!candidates.empty()){require(context.candidates.size()==1,"full legal transcript leaves a different hidden tree possible");std::uint64_t answer=0;for(int e:result.roads)answer|=1ULL<<e;require(context.candidates[0]==answer,"unique literal transcript completion");}
 for(int e:sorted(result.roads)){record(e);}record(result.queries);record(result.reference_queries);return result;}
void adapter(int n,const Edges&edges,const V&ids){Context context{n,edges,indicator(edges,ids),{}};auto* previous=current_context;current_context=&context;V u,v;for(auto[x,y]:edges){u.push_back(x);v.push_back(y);}const auto old_u=u,old_v=v;
 ++api_calls;++adapter_calls;const auto answer=find_roads(n,u,v);current_context=previous;require(sorted(answer)==sorted(ids)&&u==old_u&&v==old_v,"original adapter signature and answer");require(context.calls<=tree_overlap::query_upper_bound(n),"original adapter fullscore budget");}
std::vector<V> all_trees(int n,const Edges&edges){std::vector<V> result;V chosen;auto enumerate=[&](auto&&self,int next)->void{if(chosen.size()==static_cast<std::size_t>(n-1)){if(literal_tree(n,edges,chosen))result.push_back(chosen);return;}
 const int needed=n-1-int(chosen.size());for(int e=next;e+needed<=int(edges.size());++e){chosen.push_back(e);self(self,e+1);chosen.pop_back();}};enumerate(enumerate,0);return result;}
void exhaustive(){for(int n=2;n<=5;++n){Edges possible;for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)possible.emplace_back(u,v);
 for(int mask=0;mask<(1<<possible.size());++mask){if(std::popcount(static_cast<unsigned>(mask))<n-1)continue;Edges edges;for(int e=0;e<int(possible.size());++e)if(mask>>e&1)edges.push_back(possible[e]);const auto trees=all_trees(n,edges);if(trees.empty())continue;++small_graphs;
  std::vector<std::uint64_t> completions;for(const auto&t:trees){std::uint64_t bits=0;for(int e:t)bits|=1ULL<<e;completions.push_back(bits);}
  for(const auto&hidden:trees){run(n,edges,hidden,completions);++small_trees;if(small_trees%113==0)adapter(n,edges,hidden);}}}}
Edges complete(int n,bool path_first=false){Edges edges;if(path_first)for(int v=1;v<n;++v)edges.emplace_back(v-1,v);for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)if(!path_first||v!=u+1)edges.emplace_back(u,v);return edges;}
V edge_ids(const Edges&edges,const Edges&tree){int n=0;for(auto[u,v]:edges)n=std::max(n,std::max(u,v)+1);std::vector<V> index(n,V(n,-1));for(int e=0;e<int(edges.size());++e){auto[u,v]=edges[e];index[u][v]=index[v][u]=e;}V result;for(auto[u,v]:tree){require(index[u][v]>=0,"constructed hidden edge exists");result.push_back(index[u][v]);}return result;}
Edges prufer_tree(const V&word){const int n=int(word.size())+2;V degree(n,1);for(int v:word)++degree[v];Edges result;
 for(int v:word){int leaf=0;while(degree[leaf]!=1)++leaf;result.emplace_back(leaf,v);--degree[leaf];--degree[v];}V leaves;for(int v=0;v<n;++v)if(degree[v]==1)leaves.push_back(v);result.emplace_back(leaves[0],leaves[1]);return result;}
void prufer(){const int n=6;const auto edges=complete(n);V word(n-2,0);auto enumerate=[&](auto&&self,int i)->void{if(i==int(word.size())){run(n,edges,edge_ids(edges,prufer_tree(word)));++prufer_cases;return;}for(int v=0;v<n;++v){word[i]=v;self(self,i+1);}};enumerate(enumerate,0);}
void random_tests(){std::mt19937 rng(20170801);for(int test=0;test<400;++test){const int n=2+int(rng()%49);Edges hidden;for(int v=1;v<n;++v)hidden.emplace_back(v,int(rng()%v));std::set<Edge> present;for(auto[u,v]:hidden)present.emplace(std::min(u,v),std::max(u,v));
 for(int i=0;i<3*n;++i){int u=rng()%n,v=rng()%n;if(u!=v)present.emplace(std::min(u,v),std::max(u,v));}Edges edges(present.begin(),present.end());std::shuffle(edges.begin(),edges.end(),rng);auto ids=edge_ids(edges,hidden);run(n,edges,ids);++random_cases;
  Edges flipped=edges;for(auto&[u,v]:flipped)if(rng()&1)std::swap(u,v);run(n,flipped,ids);++metamorphic;
  V perm(n);std::iota(perm.begin(),perm.end(),0);std::shuffle(perm.begin(),perm.end(),rng);for(auto&[u,v]:flipped){u=perm[u];v=perm[v];}run(n,flipped,ids);++metamorphic;
  V order(edges.size());std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);Edges changed;V new_ids;const V h=indicator(edges,ids);for(int e=0;e<int(edges.size());++e){changed.push_back(edges[order[e]]);if(h[order[e]])new_ids.push_back(e);}run(n,changed,new_ids);++metamorphic;if(test<30)adapter(n,edges,ids);
 }}
void invalids(){int calls=0;tree_overlap::Oracle safe=[&](std::span<const int>){++calls;return 0;};auto reject=[&](int n,const Edges&edges,int budget=8000,bool empty=false){bool caught=false;const int old=calls;++api_calls;try{(void)tree_overlap::recover_hidden_tree(n,edges,empty?tree_overlap::Oracle{}:safe,budget);}catch(const std::invalid_argument&){caught=true;}require(caught&&calls==old,"invalid graph/budget/callback must fail before asking");++invalid_cases;};
 reject(0,{});reject(1,{});reject(501,{});reject(INT_MIN,{});reject(INT_MAX,{});reject(2,{});reject(2,{{0,1},{0,1}});reject(3,{{0,1},{1,0}});reject(3,{{0,0},{1,2}});reject(4,{{0,1},{1,2},{0,2}});reject(2,{{0,2}});reject(2,{{-1,1}});reject(2,{{INT_MIN,1}});reject(2,{{0,INT_MAX}});reject(2,{{0,1}},-1);reject(2,{{0,1}},8001);reject(2,{{0,1}},8000,true);
 auto bad_reply=[&](int n,const Edges&edges,V replies){int at=0;bool caught=false;++api_calls;try{(void)tree_overlap::recover_hidden_tree(n,edges,[&](std::span<const int>){return replies[std::min(at++,int(replies.size())-1)];});}catch(const std::runtime_error&){caught=true;}require(caught,"invalid/inconsistent reply accepted");++invalid_cases;};
 for(int bad:{INT_MIN,-1,2,INT_MAX}){bad_reply(2,{{0,1}},{bad});}bad_reply(3,complete(3),{0});bad_reply(3,complete(3),{2});bad_reply(3,complete(3),{1,2,0});bad_reply(3,{{0,1},{1,2}},{2,0});bad_reply(3,{{0,1},{1,2}},{2,2,1,2});
 auto reject_adapter=[&](int n,V u,V v){bool caught=false;++api_calls;try{(void)find_roads(n,u,v);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid original adapter accepted");++invalid_cases;};reject_adapter(1,{},{});reject_adapter(2,{0},{});reject_adapter(2,{},{});reject_adapter(501,{},{});reject_adapter(2,{0,0},{1,1});
 struct Marker{};bool propagated=false;++api_calls;try{(void)tree_overlap::recover_hidden_tree(2,Edges{{0,1}},[](std::span<const int>)->int{throw Marker{};});}catch(const Marker&){propagated=true;}require(propagated,"callback exception identity not preserved");
}
void api_tests(){using Signature=V(*)(int,V,V);static_assert(std::is_same_v<decltype(&find_roads),Signature>);require(tree_overlap::query_upper_bound(500)==5990,"exact maximum query formula");
 for(int n=2;n<=500;++n){const int expected=1+2*(n-1)+n+(n-1)*std::bit_width(static_cast<unsigned>(n-2));require(tree_overlap::query_upper_bound(n)==expected&&expected<=5990,"every source N bound");}
 for(int bad:{INT_MIN,0,1,501,INT_MAX}){bool caught=false;try{(void)tree_overlap::query_upper_bound(bad);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid bound helper");++invalid_cases;}
 const auto edges=complete(4);const V hidden{0,1,5};const auto result=run(4,edges,hidden);adapter(4,edges,hidden);const int needed=result.queries;
 for(int budget:{0,needed-1,needed}){Context context{4,edges,indicator(edges,hidden),{}};bool caught=false;++api_calls;try{const auto actual=tree_overlap::recover_hidden_tree(4,edges,[&](std::span<const int>q){return context.ask(q);},budget);require(sorted(actual.roads)==hidden,"exact query budget success");}catch(const std::runtime_error&){caught=true;}
  require(caught==(budget<needed)&&context.calls==budget,"budget checked before extra oracle call");}
 for(int call=0;call<30;++call){auto copy=result;auto moved=std::move(copy);require(moved.roads==result.roads&&moved.reference_membership==result.reference_membership,"returned arrays copy/move");moved.roads.clear();moved.reference_membership.assign(500,8);
  bool nested=false;Context context{4,edges,indicator(edges,hidden),{}};++api_calls;const auto answer=tree_overlap::recover_hidden_tree(4,edges,[&](std::span<const int>question){if(!nested){nested=true;run(2,Edges{{1,0}},V{0});adapter(2,Edges{{0,1}},V{0});}return context.ask(question);});require(answer.roads==result.roads&&answer.reference_membership==result.reference_membership,"nested calls and mutated old results are isolated");}
 invalids();}
struct Maximum{std::string name;int n,m,q,reference,entries;double seconds;};std::vector<Maximum> maximum_records;
void maximum_case(const std::string&name,const Edges&edges,const Edges&hidden){const auto start=std::chrono::steady_clock::now();const auto ids=edge_ids(edges,hidden);const auto answer=run(500,edges,ids);adapter(500,edges,ids);
 maximum_records.push_back({name,500,int(edges.size()),answer.queries,answer.reference_queries,answer.query_entries,std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()});}
void maximum(){const int n=500;Edges path,star;for(int v=1;v<n;++v){path.emplace_back(v-1,v);star.emplace_back(0,v);}maximum_case("path graph unique hidden tree",path,path);maximum_case("star graph unique hidden tree",star,star);
 auto dense=complete(n);maximum_case("complete lexicographic reference,hidden star",dense,star);maximum_case("complete lexicographic reference,hidden path",dense,path);std::mt19937 rng(20170801);V word(n-2);for(int&v:word)v=rng()%n;auto random=prufer_tree(word);maximum_case("complete lexicographic reference,hidden Prufer tree",dense,random);
 dense=complete(n,true);maximum_case("complete path reference,hidden star",dense,star);maximum_case("complete path reference,hidden reference path",dense,path);std::shuffle(dense.begin(),dense.end(),rng);maximum_case("complete permuted reference,hidden Prufer tree",dense,random);
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_tests();
#ifndef ADAPTER_SMOKE_ONLY
 exhaustive();prufer();random_tests();maximum();
#endif
 rusage usage{};getrusage(RUSAGE_SELF,&usage);std::cout<<"{\"checks\":"<<checks<<",\"recoverCalls\":"<<api_calls<<",\"literalValidTreeQuestions\":"<<oracle_queries<<",\"literalQuestionEntries\":"<<oracle_entries<<",\"exhaustiveConnectedGraphs\":"<<small_graphs<<",\"everyHiddenTreeForEverySmallGraph\":"<<small_trees
 <<",\"transcriptCompletionComparisons\":"<<transcript_filters<<",\"completeN6PruferHiddenTrees\":"<<prufer_cases<<",\"randomGraphs\":"<<random_cases<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCases\":"<<invalid_cases<<",\"originalAdapterCalls\":"<<adapter_calls
 <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";bool comma=false;
 for(const auto&x:maximum_records){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<x.name<<"\",\"n\":"<<x.n<<",\"m\":"<<x.m<<",\"queries\":"<<x.q<<",\"referenceQueries\":"<<x.reference<<",\"queryEntries\":"<<x.entries<<",\"twoApiCallsSeconds\":"<<x.seconds<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/spanning-tree-overlap-oracle-reference-labeling-leaf-peeling.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-simurgh-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
        (Path(directory)/'simurgh.h').write_text(HEADER)
        generic=Path(directory)/'generic.cpp';generic.write_text(cpp)
        subprocess.run(['g++',*flags,'-fsyntax-only',str(generic)],check=True)
        source.write_text(cpp+'\n'+HARNESS)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS']='halt_on_error=1'
        results=[]
        for extra in [[],['-DTEST_MUTABLE_REF','-DADAPTER_SMOKE_ONLY']]:
            subprocess.run(['g++',*flags,'-DSIMURGH_ORIGINAL_GRADER',*extra,str(source),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
            results.append(json.loads(result.stdout))
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),
                     'sanitize':args.sanitize,'compilerFlags':flags,'genericWithoutHeaderCompiled':True,
                     'stubContract':'Synthetic test headers cover const vector<int>& and vector<int>& oracle parameters;no claim of obtaining official header bytes.',
                     'constReferenceHeaderFull':results[0],'mutableReferenceHeaderApiSmoke':results[1]},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
