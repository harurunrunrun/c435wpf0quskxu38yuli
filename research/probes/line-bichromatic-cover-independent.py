#!/usr/bin/env python3
"""Actual-fence checks via weighted edge-cover/matching reduction, not coordinate block DP."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile,time
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/line-bipartite-edge-cover-monochromatic-block-prefix-dp.mdx').read_text();cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(cpp)==1;cpp=cpp[0]
harness=r'''
#include <bit>
#include <cstdlib>
#include <iostream>
#include <new>
#include <numeric>
#include <random>
static long long fail_after=-1;static bool counting=false;static std::size_t live=0,peak=0;
struct alignas(std::max_align_t) Header{std::size_t size;bool tracked;};
[[gnu::noinline]] void* operator new(std::size_t n){if(fail_after==0)throw std::bad_alloc();if(fail_after>0)--fail_after;auto*p=static_cast<Header*>(std::malloc(sizeof(Header)+(n?n:1)));if(!p)throw std::bad_alloc();p->size=n;p->tracked=counting;if(counting){live+=n;peak=std::max(peak,live);}return p+1;}
[[gnu::noinline]] void* operator new[](std::size_t n){return ::operator new(n);}
[[gnu::noinline]] void operator delete(void*ptr)noexcept{if(!ptr)return;auto*p=static_cast<Header*>(ptr)-1;if(p->tracked)live-=p->size;std::free(p);}
[[gnu::noinline]] void operator delete[](void*p)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
using ll=std::int64_t;using V=std::vector<int>;long long checks=0,cases=0,subset_matches=0,faults=0;std::uint64_t checksum=0;
void require(bool b){++checks;if(!b)throw std::runtime_error("weighted matching oracle mismatch");}
ll maximum_assignment(const std::vector<std::vector<ll>>&gain){int n=int(gain.size());std::vector<ll>u(n+1),v(n+1);std::vector<int>p(n+1),way(n+1);
 for(int row=1;row<=n;++row){p[0]=row;int at=0;std::vector<ll>distance(n+1,ll{1}<<60);std::vector<bool>used(n+1);
  do{used[at]=true;int owner=p[at],next=0;ll delta=ll{1}<<60;
   for(int j=1;j<=n;++j)if(!used[j]){ll cost=-gain[owner-1][j-1]-u[owner]-v[j];if(cost<distance[j]){distance[j]=cost;way[j]=at;}if(distance[j]<delta){delta=distance[j];next=j;}}
   for(int j=0;j<=n;++j){if(used[j]){u[p[j]]+=delta;v[j]-=delta;}else distance[j]-=delta;}at=next;
  }while(p[at]);
  do{int prev=way[at];p[at]=p[prev];at=prev;}while(at);
 }
 ll result=0;for(int j=1;j<=n;++j)result+=gain[p[j]-1][j-1];return result;
}
ll subset_assignment(const std::vector<std::vector<ll>>&g,int rows,int columns){
 std::vector<ll>d(1U<<columns,-1);d[0]=0;
 for(int i=0;i<rows;++i){auto next=d;for(unsigned mask=0;mask<d.size();++mask)if(d[mask]>=0)for(int j=0;j<columns;++j)if(!(mask>>j&1))next[mask|(1U<<j)]=std::max(next[mask|(1U<<j)],d[mask]+g[i][j]);d.swap(next);}
 return *std::max_element(d.begin(),d.end());
}
ll matching_cover(const V&r,const V&b){
 int R=int(r.size()),B=int(b.size()),n=std::max(R,B);std::vector<ll>mr(R,ll{1}<<60),mb(B,ll{1}<<60);
 for(int i=0;i<R;++i)for(int j=0;j<B;++j){ll c=std::abs(ll(r[i])-b[j]);mr[i]=std::min(mr[i],c);mb[j]=std::min(mb[j],c);}
 ll baseline=std::accumulate(mr.begin(),mr.end(),ll{0})+std::accumulate(mb.begin(),mb.end(),ll{0});std::vector<std::vector<ll>>g(n,std::vector<ll>(n));
 for(int i=0;i<R;++i)for(int j=0;j<B;++j)g[i][j]=std::max(ll{0},mr[i]+mb[j]-std::abs(ll(r[i])-b[j]));
 ll gain=maximum_assignment(g);
 if(B<=10){require(gain==subset_assignment(g,R,B));++subset_matches;}
 else if(R<=10){std::vector<std::vector<ll>>transpose(B,std::vector<ll>(R));for(int i=0;i<R;++i)for(int j=0;j<B;++j)transpose[j][i]=g[i][j];require(gain==subset_assignment(transpose,B,R));++subset_matches;}
 return baseline-gain;
}
void compare(const V&r,const V&b){const auto rr=r,bb=b;ll expected=matching_cover(r,b);require(min_line_bichromatic_edge_cover(r,b)==expected);require(min_total_length(r,b)==expected);require(rr==r&&bb==b);++cases;checksum=checksum*1000003+static_cast<std::uint64_t>(expected);}
int main(){
 for(int n=2;n<=11;++n)for(unsigned mask=1;mask+1<(1U<<n);++mask){V r,b;int position=0;for(int i=0;i<n;++i){position+=1+(i*i*13+int(mask)%31)%97;((mask>>i&1)?r:b).push_back(position);}compare(r,b);}
 std::mt19937_64 rng(201707302017ULL);
 for(int trial=0;trial<1600;++trial){int n=2+int(rng()%119);V x;while(int(x.size())<n){int p=int(rng()%1000000001ULL);if(std::find(x.begin(),x.end(),p)==x.end())x.push_back(p);}std::sort(x.begin(),x.end());V r,b;
  for(int i=0;i<n;++i){bool red=i==0||((i+1<n)&&(rng()%100<static_cast<unsigned>(trial%99+1)));(red?r:b).push_back(x[i]);}compare(r,b);
 }
 // The exact raw requested vector payload for maximum separated blocks.
 V r(100000),b(100000);std::iota(r.begin(),r.end(),0);std::iota(b.begin(),b.end(),999900001);
 counting=true;ll answer=min_line_bichromatic_edge_cover(r,b);counting=false;require(answer==99990000100000LL);require(live==0);require(peak==5000036);
 const V small_r{0,2},small_b{1};
 for(int adapter=0;adapter<2;++adapter){bool reached=false;for(int at=0;at<100;++at){fail_after=at;try{ll value=adapter?min_total_length(small_r,small_b):min_line_bichromatic_edge_cover(small_r,small_b);fail_after=-1;require(value==2);reached=true;break;}catch(const std::bad_alloc&){fail_after=-1;++faults;}
  require(small_r==V({0,2})&&small_b==V({1}));require(min_line_bichromatic_edge_cover(small_r,small_b)==2);
 }require(reached);}
 std::cout<<"{\"checks\":"<<checks<<",\"weightedMatchingEdgeCoverInputs\":"<<cases<<",\"hungarianVersusLiteralSubsetAssignmentSelfChecks\":"<<subset_matches<<",\"allocationFailureExceptions\":"<<faults<<",\"maxApiRequestedVectorBytes\":"<<peak<<",\"maxApiLiveVectorBytesAfterCall\":"<<live<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='flowchartcp-wiring-matching-oracle-')as td:
 src=Path(td)/'probe.cpp';exe=Path(td)/'probe';src.write_text(cpp+'\n'+harness)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete',str(src),'-o',str(exe)],check=True)
 result=json.loads(subprocess.check_output([str(exe)],text=True))
result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'seconds':time.monotonic()-start,'oracle':'Weighted edge cover reduces to sum_v cheapest_incident(v) minus maximum-weight partial bipartite matching with gain(v,w)=max(0,cheapest(v)+cheapest(w)-cost(v,w)). Square padded Hungarian assignment computes maximum gain; an independent subset-assignment DP self-checks every case with a color size<=10. Neither uses coordinate sorting/block decomposition/one-overlap recurrence, nor the author coverage-mask/all-edge-subset/two-dimensional-prefix oracles.','allocationFailureScope':'Every allocation in the public const-reference API and the original value-vector adapter is failed in turn; check input constness and fresh valid call after each exception. Adapter copies account for two extra allocations.','sanitizerForThisAdditionalProbe':False,'sharedOrAuthorArtifactsModified':False})
print(json.dumps(result,ensure_ascii=False,indent=2))
