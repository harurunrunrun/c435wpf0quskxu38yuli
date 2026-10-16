#!/usr/bin/env python3
"""Extract the actual visible C++20 and validate fixed/adaptive rank-count contracts."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
HEADER='#pragma once\n#include <vector>\nstd::vector<int> ask(int);\nint find_best(int);\n'
HARNESS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdint>
#include <iostream>
#include <map>
#include <numeric>
#include <type_traits>
#include <random>
#include <set>
#include <string>
#include <sys/resource.h>
using V=std::vector<int>;using Reply=ranked_prizes::Reply;using Result=ranked_prizes::Result;
std::uint64_t checks=0,checksum=0,api_calls=0,asks=0,small_arrays=0,adaptive_runs=0,adaptive_comparisons=0,adaptive_tree_nodes=0,adaptive_tree_leaves=0,adaptive_tree_branches=0,large_adaptive_runs=0,large_adaptive_comparisons=0,maximum_calls=0,invalids=0,abstract_patterns=0,count_chains=0,adapter_calls=0;int max_queries=0,max_rare=0,max_noncheap_reply=0;std::vector<V> feasible_chains;
void require(bool b,const char*why){++checks;if(!b)throw std::runtime_error(why);}void record(std::uint64_t x){checksum=checksum*1000003ULL+x;}
Reply literal(const V&a,int i){Reply r{0,0};for(int j=0;j<int(a.size());++j)if(a[j]<a[i])++r[j>i];return r;}
bool legal(const V&a){if(a.size()<3||a.size()>200000)return false;V c(7);for(int x:a){if(x<1||x>6)return false;++c[x];}if(c[1]!=1)return false;int types=*std::max_element(a.begin(),a.end());for(int t=2;t<=types;++t)if(c[t]<=1LL*c[t-1]*c[t-1])return false;return true;}
struct Fixed{const V&array;V used;std::vector<Reply>answers;bool direct;int calls=0;
 explicit Fixed(const V&a,bool literal_scan):array(a),used(a.size()),answers(a.size()),direct(literal_scan){int levels=*std::max_element(a.begin(),a.end());V total(levels+1),before(levels+1);for(int x:a)++total[x];for(int i=0;i<int(a.size());++i){int left=0,right=0;for(int t=1;t<a[i];++t){left+=before[t];right+=total[t]-before[t];}answers[i]={left,right};++before[a[i]];}}
 Reply operator()(int i){require(i>=0&&i<int(array.size()),"invalid asked index");require(!used[i]++,"same original index asked twice");++calls;++asks;require(calls<=5000,"full-score hard query bound exceeded");return direct?literal(array,i):answers[i];}};
Fixed*original_context=nullptr;int original_bad_size=-1;
#ifdef PRIZE_ORIGINAL_GRADER
std::vector<int> ask(int i){if(original_bad_size>=0)return V(original_bad_size,0);auto r=(*original_context)(i);return {r[0],r[1]};}
#endif
Result run(const V&a,bool direct=true){require(legal(a),"generated source array not legal");Fixed context(a,direct);const auto before=a;++api_calls;auto result=ranked_prizes::find_unique_best(int(a.size()),[&](int i){return context(i);});
 require(a[result.index]==1,"wrong unique best position");require(result.queries==context.calls&&result.queries==result.fast_queries+result.prefix_queries+result.search_queries,"stage/callback accounting");require(result.queries<=ranked_prizes::query_upper_bound(int(a.size())),"proved global query limit");require(result.maximum_pending<=18,"interval stack exceeds binary height");require(a==before,"input/state mutated");if(result.reference_total>=0){int least=*std::max_element(a.begin(),a.end());require(result.reference_total==int(std::count_if(a.begin(),a.end(),[&](int t){return t<least;})),"reference was not certainly cheapest");}
 max_queries=std::max(max_queries,result.queries);record(result.index);record(result.queries);record(result.prefix_queries);return result;}
void adapter(const V&a){
#ifdef PRIZE_ORIGINAL_GRADER
 Fixed context(a,false);auto*previous=original_context;original_context=&context;++adapter_calls;++api_calls;int got=find_best(int(a.size()));original_context=previous;require(a[got]==1&&context.calls<=5000,"synthetic original adapter failed");record(got);
#else
 (void)a;
#endif
}
std::vector<V> legal_arrays(int n){std::vector<V>result;for(int best=0;best<n;++best){V a(n,2);a[best]=1;result.push_back(a);for(int second=2;second+1+(second*second+1)<=n;++second){V available;for(int i=0;i<n;++i)if(i!=best)available.push_back(i);V chosen;
 auto choose=[&](auto&&self,int at)->void{if(int(chosen.size())==second){V b(n,3);b[best]=1;for(int p:chosen)b[p]=2;result.push_back(std::move(b));return;}for(int i=at;i+second-int(chosen.size())<=int(available.size());++i){chosen.push_back(available[i]);self(self,i+1);chosen.pop_back();}};choose(choose,0);}}
 return result;}
void exhaustive(){for(int n=3;n<=16;++n){auto arrays=legal_arrays(n);for(const auto&a:arrays){run(a);++small_arrays;if(small_arrays%137==0)adapter(a);}}}
void adaptive(){for(int n=8;n<=16;++n){const auto arrays=legal_arrays(n);for(int mode=0;mode<4;++mode){std::vector<int>possible(arrays.size());std::iota(possible.begin(),possible.end(),0);V used(n);int calls=0;++api_calls;
 auto r=ranked_prizes::find_unique_best(n,[&](int i){require(i>=0&&i<n&&!used[i]++,"adaptive query invalid/repeated");std::map<Reply,V> buckets;for(int id:possible){++adaptive_comparisons;buckets[literal(arrays[id],i)].push_back(id);}auto chosen=buckets.begin();for(auto it=buckets.begin();it!=buckets.end();++it){if(mode==0&&it->second.size()>chosen->second.size())chosen=it;if(mode==1&&it->first[0]+it->first[1]>chosen->first[0]+chosen->first[1])chosen=it;if(mode==2&&it->first>chosen->first)chosen=it;if(mode==3&&it->first[0]+it->first[1]==0&&buckets.size()>1)continue;if(mode==3&&chosen->first[0]+chosen->first[1]==0)chosen=it;}Reply answer=chosen->first;possible=chosen->second;require(!possible.empty(),"no adaptive legal completion");++calls;return answer;});
 require(!possible.empty()&&calls<=5000&&calls==r.queries,"adaptive result/accounting");for(int id:possible)require(arrays[id][r.index]==1,"not best in every surviving completion");++adaptive_runs;record(r.index);record(calls);}}}
void all_adaptive_answers(){for(int n=3;n<=12;++n){const auto arrays=legal_arrays(n);V possible(arrays.size());std::iota(possible.begin(),possible.end(),0);std::vector<std::pair<int,Reply>>history;
 struct Pause{int index;};auto explore=[&](auto&&self,const V&candidates)->void{++adaptive_tree_nodes;int at=0,next=-1;bool done=false;Result result;++api_calls;
  try{result=ranked_prizes::find_unique_best(n,[&](int i)->Reply{if(at==int(history.size()))throw Pause{i};require(i==history[at].first,"adaptive replay requested different cached prefix");return history[at++].second;});done=true;}catch(const Pause&p){next=p.index;}
  if(done){require(at==int(history.size())&&result.queries==int(history.size()),"all-answer adaptive leaf query accounting");for(int id:candidates)require(arrays[id][result.index]==1,"adaptive leaf is not best in every completion");++adaptive_tree_leaves;return;}
  require(next>=0&&next<n&&int(history.size())<n,"invalid/nonterminating adaptive branch");std::map<Reply,V>buckets;for(int id:candidates)buckets[literal(arrays[id],next)].push_back(id);
  for(auto&[reply,remaining]:buckets){++adaptive_tree_branches;history.emplace_back(next,reply);self(self,remaining);history.pop_back();}
 };explore(explore,possible);}}
int potential(int h,int k){int answer=0;for(int d=0;d<h;++d)answer+=std::min(1<<d,k);return answer;}
int abstract_scan(unsigned pattern,int left,int right,int count,unsigned&seen){if(!count)return 0;int mid=left+(right-left)/2,at=mid,q=0,cost=0;while(at<=right&&q<count){require(!(seen>>at&1U),"abstract marked interval revisits a point");seen|=1U<<at;++cost;if(!(pattern>>at&1U))break;++q;++at;}
 if(q==count)return cost;
 if(at>right)return cost+abstract_scan(pattern,left,mid-1,count-q,seen);
 unsigned lower=(1U<<mid)-1U,cut=(1U<<left)-1U;int lc=std::popcount(pattern&(lower^cut));return cost+abstract_scan(pattern,left,mid-1,lc,seen)+abstract_scan(pattern,at+1,right,count-q-lc,seen);}
void potential_tests(){require(potential(18,472)==4759&&potential(18,26)==369,"exact global potential constants");for(int n=1;n<=18;++n)for(unsigned mask=0;mask<(1U<<n);++mask){unsigned visited=0;int k=std::popcount(mask),cost=abstract_scan(mask,0,n-1,k,visited);require(cost<=potential(std::bit_width(static_cast<unsigned>(n)),k)&&std::popcount(visited)==cost,"all marked patterns violate potential bound");++abstract_patterns;record(cost);}
 for(int h=1;h<=18;++h)for(int k=1;k<=std::min(472,(1<<(h-1))-1);++k)for(int q=0;q<k;++q){int rest=k-q,a=rest/2,b=rest-a;require(q+1+potential(h-1,a)+potential(h-1,b)<=potential(h,k),"potential scan/split inequality");}}
void counts(){V prefix{1};auto extend=[&](auto&&self)->void{int sum=std::accumulate(prefix.begin(),prefix.end(),0),last=prefix.back();long long cheap=1LL*last*last+1;if(sum+cheap>200000)return;++count_chains;max_rare=std::max(max_rare,sum);max_noncheap_reply=std::max(max_noncheap_reply,sum-last);feasible_chains.push_back(prefix);for(int next=last*last+1;1LL*sum+next+1LL*next*next+1<=200000;++next){prefix.push_back(next);self(self);prefix.pop_back();}};extend(extend);require(max_rare==472&&max_noncheap_reply==26,"exact feasible count chain bounds");}
struct Maximum{std::string name;int n,total,queries,fast,prefix,search;};std::vector<Maximum>maximums;
V arrangement(int n,const V&chain,int placement){int total=std::accumulate(chain.begin(),chain.end(),0),levels=int(chain.size())+1;V a(n,levels),positions;for(int i=0;i<total;++i){int p=0;if(placement==0)p=(int64_t(i)*n)/total;else if(placement==1)p=n-total+i;else if(placement==2)p=i==total-1?n-1:i;else p=(int64_t(2*i+1)*n)/(2*total);positions.push_back(p);}std::sort(positions.begin(),positions.end());int at=0;for(int t=int(chain.size());t>=1;--t)for(int j=0;j<chain[t-1];++j)a[positions[at++]]=t;return a;}
void maximum_case(const std::string&name,const V&a,bool original=false){auto r=run(a,false);int level=*std::max_element(a.begin(),a.end());int rare=int(std::count_if(a.begin(),a.end(),[&](int v){return v<level;}));maximums.push_back({name,int(a.size()),rare,r.queries,r.fast_queries,r.prefix_queries,r.search_queries});++maximum_calls;if(original)adapter(a);}
void maximum_tests(){const int n=200000;for(int p:{0,1,n/2,n-1}){V a(n,2);a[p]=1;maximum_case("two levels,best"+std::to_string(p),a,true);require(maximums.back().queries<=19,"two-level fast path bound");}
 for(const V&chain:std::vector<V>{{1,2},{1,3,21},{1,4,21},{1,4,22},{1,21,446},{1,4,21,446},{1,2,5,26}})for(int placement=0;placement<4;++placement)maximum_case("source counts/placement"+std::to_string(placement),arrangement(n,chain,placement),placement==0);
 for(int size:{472,473,474,475,511,512,513,1023,1024,1025})maximum_case("prefix/binary boundary",arrangement(size,{1,2},3),true);
 std::mt19937 rng(201708015000U);for(int trial=0;trial<64;++trial){V chain=feasible_chains[rng()%feasible_chains.size()];int sum=std::accumulate(chain.begin(),chain.end(),0),min_n=sum+chain.back()*chain.back()+1;int size=min_n+int(rng()%unsigned(200001-min_n));V a=arrangement(size,chain,trial%4);std::shuffle(a.begin(),a.end(),rng);maximum_case("random full legal count chain",a,trial<4);}
}
void large_adaptive(){struct Candidate{int cheapest;std::vector<std::pair<int,int>>special;};const int n=200000;std::vector<Candidate>family;std::mt19937 rng(201708015026U);
 for(const V&chain:std::vector<V>{{1,4,21},{1,4,22},{1,4,21,446}})for(int sample=0;sample<24;++sample){V a=arrangement(n,chain,sample%4);if(sample>=4)std::shuffle(a.begin(),a.end(),rng);Candidate c{int(chain.size())+1,{}};for(int i=0;i<n;++i)if(a[i]<c.cheapest)c.special.emplace_back(i,a[i]);family.push_back(std::move(c));}
 auto answer=[&](const Candidate&c,int i){int type=c.cheapest;for(auto[pos,t]:c.special)if(pos==i){type=t;break;}Reply r{0,0};for(auto[pos,t]:c.special)if(t<type)++r[pos>i];return r;};
 for(int mode=0;mode<3;++mode){V possible(family.size());std::iota(possible.begin(),possible.end(),0);V used(n);int calls=0;++api_calls;auto r=ranked_prizes::find_unique_best(n,[&](int i){require(i>=0&&i<n&&!used[i]++,"large adaptive invalid/cached index");std::map<Reply,V>buckets;for(int id:possible){++large_adaptive_comparisons;buckets[answer(family[id],i)].push_back(id);}auto chosen=buckets.begin();for(auto it=buckets.begin();it!=buckets.end();++it){if(mode==0&&it->second.size()>chosen->second.size())chosen=it;if(mode==1&&it->first[0]+it->first[1]<chosen->first[0]+chosen->first[1])chosen=it;if(mode==2&&it->first[0]+it->first[1]>chosen->first[0]+chosen->first[1])chosen=it;}Reply result=chosen->first;possible=chosen->second;++calls;return result;});
  for(int id:possible)require(answer(family[id],r.index)==Reply{0,0},"large adaptive output not diamond in every completion");
  require(r.queries==calls&&calls<=4779&&r.maximum_pending<=18,"large adaptive full-bound failure");++large_adaptive_runs;record(r.index);record(r.queries);
 }}
void api_tests(){
#ifdef PRIZE_ORIGINAL_GRADER
 static_assert(std::is_same_v<decltype(&find_best),int(*)(int)>);
 for(int n:{2,200001}){++api_calls;bool caught=false;try{(void)find_best(n);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid original N accepted");++invalids;}
 for(int size:{0,1,3}){++api_calls;original_bad_size=size;bool caught=false;try{(void)find_best(3);}catch(const std::runtime_error&){caught=true;}original_bad_size=-1;require(caught,"original ask vector size unchecked");++invalids;}
#endif
 int calls=0;ranked_prizes::Oracle safe=[&](int)->Reply{++calls;return {0,0};};auto reject=[&](int n,int budget=5000,bool empty=false){bool caught=false;int before=calls;++api_calls;try{(void)ranked_prizes::find_unique_best(n,empty?ranked_prizes::Oracle{}:safe,budget);}catch(const std::invalid_argument&){caught=true;}require(caught&&calls==before,"invalid input asks oracle");++invalids;};for(int n:{INT_MIN,-1,0,1,2,200001,INT_MAX})reject(n);reject(3,-1);reject(3,10001);reject(3,5000,true);
 for(Reply bad:std::vector<Reply>{{-1,0},{1,0},{0,-1},{0,INT_MAX},{0,473},{INT_MAX,INT_MAX}}){bool caught=false;++api_calls;try{(void)ranked_prizes::find_unique_best(200000,[&](int){return bad;});}catch(const std::runtime_error&){caught=true;}require(caught,"invalid reply accepted");++invalids;}
 for(int n=3;n<=200000;++n)require(ranked_prizes::query_upper_bound(n)<=4779&&ranked_prizes::query_upper_bound(n)<=n,"bound helper source domain");
 const V a{3,2,3,1,3,3,2,3};auto answer=run(a);adapter(a);for(int budget=0;budget<=answer.queries+1;++budget){Fixed f(a,true);bool thrown=false;++api_calls;try{auto r=ranked_prizes::find_unique_best(int(a.size()),[&](int i){return f(i);},budget);require(r.index==3,"exact budget result");}catch(const std::runtime_error&){thrown=true;}require(thrown==(budget<answer.queries)&&f.calls==std::min(budget,answer.queries),"budget not enforced before callback");}
 struct Marker{int x;};for(int fail=0;fail<answer.queries;++fail){int at=0;bool same=false;++api_calls;try{(void)ranked_prizes::find_unique_best(int(a.size()),[&](int i)->Reply{if(at++==fail)throw Marker{fail};return literal(a,i);});}catch(const Marker&e){same=e.x==fail;}require(same&&at==fail+1,"callback exception identity");}
 {const V main_array=arrangement(1000,{1,4,22},3);const auto full=run(main_array,false);
 for(int budget=0;budget<=full.queries+1;++budget){Fixed f(main_array,false);bool thrown=false;++api_calls;try{auto r=ranked_prizes::find_unique_best(1000,[&](int i){return f(i);},budget);require(r.index==full.index,"main search exact budget result");}catch(const std::runtime_error&){thrown=true;}require(thrown==(budget<full.queries)&&f.calls==std::min(budget,full.queries),"main search sent callback past budget");}
 for(int fail=0;fail<full.queries;++fail){int at=0;bool same=false;Fixed f(main_array,false);++api_calls;try{(void)ranked_prizes::find_unique_best(1000,[&](int i)->Reply{if(at++==fail)throw Marker{fail};return f(i);});}catch(const Marker&e){same=e.x==fail;}require(same&&at==fail+1,"main search callback exception identity");}
 bool nested=false;Fixed f(main_array,false);++api_calls;auto again=ranked_prizes::find_unique_best(1000,[&](int i){if(i>=473&&!nested){nested=true;run({2,1,2});}return f(i);});require(nested&&again.index==full.index,"nested main search callback/state isolation");}
 for(int call=0;call<30;++call){auto copy=answer,moved=std::move(copy);moved.index=-7;bool nested=false;Fixed f(a,true);++api_calls;auto r=ranked_prizes::find_unique_best(int(a.size()),[&](int i){if(!nested){nested=true;run({2,1,2});}return f(i);});require(r.index==answer.index&&r.queries==answer.queries&&moved.index==-7,"reentry/result mutation");}
}
int main(){try{auto start=std::chrono::steady_clock::now();api_tests();
#ifndef ADAPTER_SMOKE_ONLY
 counts();exhaustive();adaptive();all_adaptive_answers();potential_tests();maximum_tests();large_adaptive();
#else
 maximum_case("original maximum S472 full source",arrangement(200000,{1,4,21,446},3),true);maximum_case("original maximum S26 fallback",arrangement(200000,{1,4,21},3),true);maximum_case("original maximum two-level",arrangement(200000,{1},1),true);
#endif
 rusage usage{};getrusage(RUSAGE_SELF,&usage);std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"fixedArrayOracleCalls\":"<<asks<<",\"allLegalArraysN3to16\":"<<small_arrays<<",\"adaptiveCompletionRuns\":"<<adaptive_runs<<",\"adaptiveCandidateReplyComparisons\":"<<adaptive_comparisons<<",\"allAdaptiveTreeNodesN3to12\":"<<adaptive_tree_nodes<<",\"allAdaptiveTreeLeavesN3to12\":"<<adaptive_tree_leaves<<",\"allFeasibleAdaptiveResponseBranchesN3to12\":"<<adaptive_tree_branches<<",\"largeAdaptiveCompletionRuns\":"<<large_adaptive_runs<<",\"largeAdaptiveCandidateReplyComparisons\":"<<large_adaptive_comparisons<<",\"allMarkedPatternsN1to18\":"<<abstract_patterns<<",\"legalCountChains\":"<<count_chains<<",\"maximumNonCheapest\":"<<max_rare<<",\"maximumNonCheapestReplySum\":"<<max_noncheap_reply<<",\"invalidCases\":"<<invalids<<",\"originalAdapterCalls\":"<<adapter_calls<<",\"maximumQueriesObserved\":"<<max_queries<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";bool sep=false;for(const auto&m:maximums){if(sep)std::cout<<',';sep=true;std::cout<<"{\"name\":\""<<m.name<<"\",\"n\":"<<m.n<<",\"nonCheapest\":"<<m.total<<",\"queries\":"<<m.queries<<",\"fast\":"<<m.fast<<",\"prefix\":"<<m.prefix<<",\"search\":"<<m.search<<'}';}std::cout<<"]}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sanitize',action='store_true');parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/rank-count-oracle-equal-level-interval-pruning.mdx'));a=parser.parse_args()
 article=Path(a.article).read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1 and '<details' not in article;assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料'];cpp=fences[0]
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
 if a.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
 with tempfile.TemporaryDirectory(prefix='flowchartcp-prize-cpp-')as td:
  source=Path(td)/'check.cpp';exe=Path(td)/'check';source.write_text(cpp+'\n'+HARNESS);(Path(td)/'prize.h').write_text(HEADER);env=os.environ.copy()
  if a.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
  results=[]
  for more in [[],['-DPRIZE_ORIGINAL_GRADER','-DADAPTER_SMOKE_ONLY']]:
   subprocess.run(['g++',*flags,*more,str(source),'-o',str(exe)],check=True)
   result=subprocess.run([str(exe)],check=True,text=True,capture_output=True,env=env);results.append(json.loads(result.stdout))
 print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':a.sanitize,'compilerFlags':flags,'genericStandaloneFull':results[0],'syntheticHeaderOriginalAdapterSmoke':results[1],'officialHeaderBytesRetrieved':False},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
