#!/usr/bin/env python3
"""Actual-fence review via coherent transcript adversary and leaf-stripping legality."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile,time
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/spanning-tree-overlap-oracle-reference-labeling-leaf-peeling.mdx').read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1;cpp=fences[0]
assert hashlib.sha256(cpp.encode()).hexdigest()=='890af3ba0d61b726576a464272e51ac2816e3ca2bf59facee194b58a5f0972bd'
harness=r'''
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <queue>
#include <random>
static long long fail_after=-1;static bool counting=false;static std::size_t live=0,peak=0;
struct alignas(std::max_align_t) Header{std::size_t size;bool tracked;};
[[gnu::noinline]] void* operator new(std::size_t n){if(fail_after==0)throw std::bad_alloc();if(fail_after>0)--fail_after;auto*p=static_cast<Header*>(std::malloc(sizeof(Header)+(n?n:1)));if(!p)throw std::bad_alloc();p->size=n;p->tracked=counting;if(counting){live+=n;peak=std::max(peak,live);}return p+1;}
[[gnu::noinline]] void* operator new[](std::size_t n){return ::operator new(n);}
[[gnu::noinline]] void operator delete(void*ptr)noexcept{if(!ptr)return;auto*p=static_cast<Header*>(ptr)-1;if(p->tracked)live-=p->size;std::free(p);}
[[gnu::noinline]] void operator delete[](void*p)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
using V=std::vector<int>;using Edges=std::vector<tree_overlap::Edge>;using U=std::uint64_t;
U checks=0,checksum=0,transcripts=0,candidate_inspections=0,oracle_calls=0,oracle_entries=0,legal_leaf_checks=0,budget_tests=0,callback_exceptions=0,allocation_failures=0,complete_tree_count=0;int worst_queries=0,callbacks_before_alloc_failure=0,measured_maximum_queries=0;
void require(bool b,const char*what){++checks;if(!b)throw std::runtime_error(what);}void record(U x){checksum=checksum*1000003ULL+x;}
// N-1 distinct selected edges are a tree iff repeatedly stripping degree-one
// vertices removes all edges. This uses no DSU and no BFS connectivity check.
bool leaf_tree(int n,const Edges&edges,std::span<const int>ids){++legal_leaf_checks;if(int(ids.size())!=n-1)return false;V degree(n),last(n),seen(edges.size()),queue;for(int e:ids){if(e<0||e>=int(edges.size())||seen[e]++)return false;auto[u,v]=edges[e];++degree[u];++degree[v];last[u]^=e;last[v]^=e;}
 for(int v=0;v<n;++v)if(degree[v]==1)queue.push_back(v);int removed=0;for(std::size_t head=0;head<queue.size();++head){int v=queue[head];if(degree[v]!=1)continue;int e=last[v];auto[a,b]=edges[e];int w=a==v?b:a;degree[v]=0;--degree[w];last[w]^=e;++removed;if(degree[w]==1)queue.push_back(w);}return removed==n-1;}
Edges complete(int n){Edges g;for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)g.emplace_back(u,v);return g;}
std::vector<U> all_cayley(int n){Edges all=complete(n);std::vector<V>id(n,V(n,-1));for(int e=0;e<int(all.size());++e){auto[u,v]=all[e];id[u][v]=id[v][u]=e;}V word(n-2);std::vector<U>result;
 auto enumerate=[&](auto&&self,int at)->void{if(at<int(word.size())){for(int v=0;v<n;++v){word[at]=v;self(self,at+1);}return;}V degree(n,1);for(int v:word)++degree[v];std::priority_queue<int,V,std::greater<int>>leaves;for(int v=0;v<n;++v)if(degree[v]==1)leaves.push(v);U mask=0;
  for(int v:word){int leaf=leaves.top();leaves.pop();mask|=U{1}<<id[leaf][v];--degree[leaf];if(--degree[v]==1)leaves.push(v);}int x=leaves.top();leaves.pop();int y=leaves.top();mask|=U{1}<<id[x][y];result.push_back(mask);
 };enumerate(enumerate,0);U count=1;for(int i=0;i<n-2;++i)count*=n;require(result.size()==count,"Cayley enumeration count");auto sorted=result;std::sort(sorted.begin(),sorted.end());require(std::adjacent_find(sorted.begin(),sorted.end())==sorted.end(),"duplicate Cayley tree");complete_tree_count+=result.size();return result;}
void adversarial_case(int n,const Edges&edges,const std::vector<U>&universe,int mode){Edges canonical=complete(n);std::vector<V>index(n,V(n,-1));for(int e=0;e<int(canonical.size());++e){auto[u,v]=canonical[e];index[u][v]=index[v][u]=e;}
 U present=0;V mapping;for(auto[u,v]:edges){int i=index[u][v];mapping.push_back(i);present|=U{1}<<i;}std::vector<U>possible;for(U tree:universe)if((tree&present)==tree)possible.push_back(tree);require(!possible.empty(),"connected subgraph has hidden completion");
 std::vector<std::pair<U,int>>history;const auto before=edges;int calls=0;
 auto answer=tree_overlap::recover_hidden_tree(n,edges,[&](std::span<const int>question){require(leaf_tree(n,edges,question),"transcript query not a legal spanning tree");U mask=0;for(int e:question)mask|=U{1}<<mapping[e];V buckets(n);for(U tree:possible){++candidate_inspections;++buckets[std::popcount(tree&mask)];}int chosen=-1;
  for(int k=0;k<n;++k)if(buckets[k]){if(chosen<0)chosen=k;else if(mode==0&&(buckets[k]>buckets[chosen]||(buckets[k]==buckets[chosen]&&k>chosen)))chosen=k;else if(mode==2)chosen=k;}
  require(chosen>=0,"no coherent answer bucket");std::vector<U>next;for(U tree:possible)if(std::popcount(tree&mask)==chosen)next.push_back(tree);possible.swap(next);history.emplace_back(mask,chosen);++calls;++oracle_calls;oracle_entries+=n-1;return chosen;
 });
 require(possible.size()==1,"coherent transcript does not identify one fixed hidden tree");U actual=0;for(int e:answer.roads)actual|=U{1}<<mapping[e];require(actual==possible[0]&&leaf_tree(n,edges,answer.roads),"returned tree differs from unique completion");
 for(auto[question,reply]:history)require(std::popcount(actual&question)==reply,"final fixed hidden tree contradicts earlier response");
 for(int i=0;i<n-1;++i)require(answer.reference_membership[i]==int(actual>>mapping[answer.reference[i]]&1),"coherent transcript reference labels");
 require(answer.queries==calls&&calls<=tree_overlap::query_upper_bound(n),"coherent transcript exceeds proved budget");require(answer.reference_queries<=1+2*(n-1)&&answer.degree_queries==n,"classification/degree budget");
 require(answer.search_queries<=(n-1)*std::bit_width(static_cast<unsigned>(n-2)),"leaf binary-search budget");require(answer.query_entries==calls*(n-1),"query element accounting");require(edges==before,"caller graph mutation");worst_queries=std::max(worst_queries,calls);++transcripts;record(actual);record(calls);
}
void transcripts_test(){std::mt19937 rng(201708015990U);for(int n=2;n<=7;++n){auto all=all_cayley(n);auto edges=complete(n);for(int trial=0;trial<12;++trial){std::shuffle(edges.begin(),edges.end(),rng);for(auto&[u,v]:edges)if(rng()&1)std::swap(u,v);for(int mode=0;mode<3;++mode)adversarial_case(n,edges,all,mode);}}
 const int n=7;auto all=all_cayley(n);auto dense=complete(n);for(int trial=0;trial<60;++trial){U retained=all[rng()%all.size()];Edges edges;for(int e=0;e<int(dense.size());++e)if((retained>>e&1)||(rng()%100<unsigned(trial%90)))edges.push_back(dense[e]);std::shuffle(edges.begin(),edges.end(),rng);for(auto&[u,v]:edges)if(rng()&1)std::swap(u,v);for(int mode=0;mode<3;++mode)adversarial_case(n,edges,all,mode);}}
int true_answer(const V&hidden,std::span<const int>q){int answer=0;for(int e:q)answer+=hidden[e];return answer;}
void zero_and_bridge(){Edges edges{{0,1},{1,2},{0,2},{3,0},{3,1},{3,2}};V hidden{0,0,0,1,1,1},replies;auto result=tree_overlap::recover_hidden_tree(4,edges,[&](std::span<const int>q){require(leaf_tree(4,edges,q),"zero-cycle query legality");int a=true_answer(hidden,q);replies.push_back(a);return a;});
 require(replies.size()>=3&&replies[0]==1&&replies[1]==1&&replies[2]==1,"explicit all-unknown cycle has only zero exchange deltas");require(result.reference==V({0,1,3})&&result.reference_membership==V({0,0,1}),"zero-delta cycle must be all0,not all1");
 edges={{0,1},{1,2},{2,3},{3,4},{4,5},{0,2},{3,5}};hidden={1,0,1,1,0,1,1};result=tree_overlap::recover_hidden_tree(6,edges,[&](std::span<const int>q){require(leaf_tree(6,edges,q),"bridge query legality");return true_answer(hidden,q);});require(result.reference_membership==V({1,0,1,1,0}),"unexchanged bridge label must be1");}
void exceptions_and_budgets(){int n=7;auto edges=complete(n);V hidden(edges.size());for(int e=0;e<int(edges.size());++e)hidden[e]=edges[e].first==n-1||edges[e].second==n-1;int calls=0;
 tree_overlap::Oracle oracle=[&](std::span<const int>q){++calls;return true_answer(hidden,q);};auto success=tree_overlap::recover_hidden_tree(n,edges,oracle);int needed=success.queries;const auto original=edges;
 for(int limit=0;limit<=needed+2;++limit){calls=0;bool thrown=false;try{auto result=tree_overlap::recover_hidden_tree(n,edges,oracle,limit);require(result.roads==success.roads,"budget changes final tree");}catch(const std::runtime_error&){thrown=true;}require(thrown==(limit<needed)&&calls==std::min(limit,needed),"budget sends one excessive callback or misses success");++budget_tests;}
 struct Marker{int index;};for(int at=0;at<needed;++at){calls=0;bool same=false;try{(void)tree_overlap::recover_hidden_tree(n,edges,[&](std::span<const int>q){if(calls++==at)throw Marker{at};return true_answer(hidden,q);});}catch(const Marker&failure){same=failure.index==at;}require(same&&calls==at+1,"callback exception identity/count");calls=0;require(tree_overlap::recover_hidden_tree(n,edges,oracle).roads==success.roads,"fresh call after callback exception");++callback_exceptions;}
 bool done=false;for(int at=0;at<4000;++at){fail_after=at;counting=true;calls=0;try{{auto result=tree_overlap::recover_hidden_tree(n,edges,oracle);fail_after=-1;require(result.roads==success.roads,"successful body after allocation fault enumeration");}counting=false;require(live==0,"successful API retains payload");done=true;break;}catch(const std::bad_alloc&){fail_after=-1;counting=false;++allocation_failures;callbacks_before_alloc_failure=std::max(callbacks_before_alloc_failure,calls);}
  require(live==0&&edges==original,"allocation exception mutates inputs or leaks API state");require(tree_overlap::recover_hidden_tree(n,edges,oracle).roads==success.roads,"fresh recovery after allocation exception");}require(done,"allocation failure enumeration failed to reach completion");}
std::size_t maximum_payload(){const int n=500;Edges edges;for(int v=1;v<n;++v)edges.emplace_back(v-1,v);for(int u=0;u<n;++u)for(int v=u+2;v<n;++v)edges.emplace_back(u,v);V hidden(edges.size());for(int e=0;e<int(edges.size());++e)hidden[e]=edges[e].first==0||edges[e].second==0;
 tree_overlap::Oracle oracle=[&](std::span<const int>q){bool before=counting;counting=false;require(leaf_tree(n,edges,q),"maximum independent leaf-strip query legality");int a=true_answer(hidden,q);counting=before;return a;};require(live==0,"max initial tracked live bytes");peak=0;counting=true;
 {auto result=tree_overlap::recover_hidden_tree(n,edges,oracle);require(result.queries<=5990&&result.query_entries<=2989010,"maximum theoretical budget");require(result.roads.size()==499,"max output length");for(int e:result.roads)require(hidden[e]==1,"max output membership");measured_maximum_queries=result.queries;}
 counting=false;require(live==0,"maximum API retains vector state");return peak;}
int main(){transcripts_test();zero_and_bridge();exceptions_and_budgets();auto payload=maximum_payload();
 std::cout<<"{\"checks\":"<<checks<<",\"consistentAdversarialTranscripts\":"<<transcripts<<",\"completeCayleyTreesEnumerated\":"<<complete_tree_count<<",\"candidateIntersectionInspections\":"<<candidate_inspections<<",\"transcriptOracleCalls\":"<<oracle_calls<<",\"transcriptOracleEntries\":"<<oracle_entries<<",\"independentLeafStrippingTreeChecks\":"<<legal_leaf_checks<<",\"maximumSmallTranscriptQueries\":"<<worst_queries<<",\"allPerCallBudgetsChecked\":"<<budget_tests<<",\"everyCallbackExceptionPosition\":"<<callback_exceptions<<",\"allocationFailureExceptions\":"<<allocation_failures<<",\"maxPriorCallbackEffectsOnAllocationFailure\":"<<callbacks_before_alloc_failure<<",\"maximumDenseN500ApiRequestedPayloadBytes\":"<<payload<<",\"maximumDenseN500Queries\":"<<measured_maximum_queries<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='flowchartcp-simurgh-coherent-adversary-')as td:
 src=Path(td)/'probe.cpp';exe=Path(td)/'probe';src.write_text(cpp+'\n'+harness)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-mismatched-new-delete',str(src),'-o',str(exe)],check=True)
 result=json.loads(subprocess.check_output([str(exe)],text=True))
result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'secondsIncludingCompilation':time.monotonic()-start,'oracle':'At each query partition every compatible labeled spanning tree by its exact intersection count and keep a nonempty bucket. Try largest bucket, smallest feasible response and largest feasible response on complete N2..7 graphs with12edge/endpoint permutations and60connected N7 subgraphs. No hidden tree is selected beforehand, but the final single candidate is explicitly checked against every prior response, so each entire transcript is consistent with one fixed hidden tree; this is a stress oracle,not a claim that the original grader is adaptive. Queries and final outputs are checked by degree-one leaf stripping,not production DSU or author BFS.','extraTargetedCases':'An explicit unknown triangle disjoint from the hidden star gives two zero exchange deltas and must label the entire cycle0. Two cyclic blocks joined by a bridge check the unexchanged reference bridge is1. Every budget0..needed+2 and every callback-throw position is exercised on a dense N7 hidden star. Every API allocation is failed in turn,with prior external callback effects allowed to persist and a clean fresh call afterward.','memoryScope':'Requested live allocation payload for the actual generic N500 complete graph,path reference,hidden star only. Caller inputs/function object,oracle allocations,allocator headers,compiler and ASan overhead are excluded. No universal maximum-byte claim; source adapter storage is separately covered by supplied-checker reproduction.','additionalProbeSanitized':False,'sharedOrAuthorArtifactsModified':False})
print(json.dumps(result,ensure_ascii=False,indent=2))
