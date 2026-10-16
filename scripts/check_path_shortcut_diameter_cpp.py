#!/usr/bin/env python3
"""Compile the actual visible fence; compare station graphs and discrete boxes."""
import argparse,hashlib,json,os,pathlib,re,subprocess,tempfile

HARNESS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <sys/resource.h>
#include <type_traits>
using I64=std::int64_t;using V=std::vector<int>;using Box=std::array<I64,4>;
static_assert(std::is_same_v<decltype(&find_shortcut),long long(*)(int,V,V,int)>);
static_assert(std::is_same_v<decltype(&minimum_path_shortcut_diameter),I64(*)(const V&,const V&,int)>);
struct Injected:std::bad_alloc{};static long fail_after=-1,allocations=0;static std::size_t live_bytes=0,peak_bytes=0;
struct alignas(std::max_align_t) Header{std::size_t bytes;};
__attribute__((noinline))void* operator new(std::size_t n){if(fail_after>=0&&allocations++==fail_after)throw Injected{};auto*p=static_cast<Header*>(std::malloc(sizeof(Header)+n));if(!p)throw std::bad_alloc{};p->bytes=n;live_bytes+=n;peak_bytes=std::max(peak_bytes,live_bytes);return p+1;}
__attribute__((noinline))void operator delete(void*q)noexcept{if(q){auto*p=static_cast<Header*>(q)-1;live_bytes-=p->bytes;std::free(p);}}
void*operator new[](std::size_t n){return::operator new(n);}void operator delete[](void*p)noexcept{::operator delete(p);}void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
struct Data{V l,d;int c;};
static std::uint64_t checks=0,checksum=0,prepared=0,min_calls=0,core_calls=0,adapter_calls=0,predicate_calls=0,small_cases=0,binary_cases=0,random_cases=0,actual_graphs=0,floyd_relaxations=0,boundary_comparisons=0,thresholds=0,boxes=0,box_pairs=0,invalids=0,faults=0,state_cases=0,metamorphic=0;
static std::size_t largest_payload=0;static std::mt19937_64 rng(0x20160814ULL);
void need(bool b,const char*w){++checks;if(!b)throw std::runtime_error(w);}void rec(std::uint64_t x){checksum=checksum*1000003ULL+x;}
std::uint64_t hash(const Data&a){std::uint64_t h=a.c;for(int x:a.l)h=h*100003+x;for(int x:a.d)h=h*100003+x;return h;}
std::vector<I64> positions(const Data&a){std::vector<I64>x(a.d.size());for(std::size_t i=1;i<x.size();++i)x[i]=x[i-1]+a.l[i-1];return x;}
bool decide(const PathShortcut&p,I64 k){++predicate_calls;bool result=p.can_achieve(k);rec(result);return result;}
I64 minimum(const PathShortcut&p){++min_calls;I64 result=p.minimum_diameter();rec(result);return result;}
I64 core(const Data&a){auto before=hash(a);const auto memory=live_bytes;peak_bytes=memory;auto result=minimum_path_shortcut_diameter(a.l,a.d,a.c);++core_calls;largest_payload=std::max(largest_payload,peak_bytes-memory);need(memory==live_bytes&&hash(a)==before,"generic function state/input");rec(result);return result;}
I64 adapter(const Data&a){auto before=hash(a);auto result=find_shortcut(int(a.d.size()),a.l,a.d,a.c);++adapter_calls;need(hash(a)==before,"adapter caller input");rec(result);return result;}
struct Literal{I64 best,original;std::vector<I64>diameters;};
Literal literal(const Data&a){const int n=int(a.d.size()),m=n+int(std::count_if(a.d.begin(),a.d.end(),[](int v){return v>0;}));const I64 inf=I64(1)<<60;std::vector<I64>base(std::size_t(m)*m,inf);
 for(int i=0;i<m;++i)base[i*m+i]=0;
 for(int i=0;i+1<n;++i)base[i*m+i+1]=base[(i+1)*m+i]=a.l[i];
 int next=n;for(int i=0;i<n;++i)if(a.d[i]){base[i*m+next]=base[next*m+i]=a.d[i];++next;}
 auto diameter=[&](std::vector<I64>dist){for(int k=0;k<m;++k)for(int i=0;i<m;++i)for(int j=0;j<m;++j){++floyd_relaxations;dist[i*m+j]=std::min(dist[i*m+j],dist[i*m+k]+dist[k*m+j]);}return*std::max_element(dist.begin(),dist.end());};
 Literal out{inf,diameter(base),{}};
 for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){auto dist=base;dist[u*m+v]=dist[v*m+u]=std::min<I64>(dist[u*m+v],a.c);I64 value=diameter(std::move(dist));++actual_graphs;out.diameters.push_back(value);out.best=std::min(out.best,value);}
 return out;
}
Box explicit_bounds(const Data&a,const std::vector<I64>&x,I64 k,bool relation_checks){Box b{0,2*x.back(),1,x.back()};const int n=int(x.size());
 for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)if(I64(a.d[i])+a.d[j]+x[j]-x[i]>k){
  const I64 ai=x[i]-a.d[i],aj=x[j]-a.d[j],bi=x[i]+a.d[i],bj=x[j]+a.d[j];
  Box pair{bi+bj+a.c-k,ai+aj+k-a.c,bj-ai+a.c-k,aj-bi+k-a.c};
  b[0]=std::max(b[0],pair[0]);b[1]=std::min(b[1],pair[1]);b[2]=std::max(b[2],pair[2]);b[3]=std::min(b[3],pair[3]);
  if(relation_checks)for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){I64 y=x[u],z=x[v];bool direct=I64(a.d[i])+a.d[j]+std::abs(x[i]-y)+std::abs(x[j]-z)+a.c<=k;bool rotated=pair[0]<=y+z&&y+z<=pair[1]&&pair[2]<=z-y&&z-y<=pair[3];need(direct==rotated,"one pair all four boundaries including c");++boundary_comparisons;}
 }
 return b;
}
void threshold(const Data&a,const PathShortcut&p,const Literal&exact,I64 k,bool detailed){++thresholds;need(decide(p,k)==(exact.best<=k),"actual threshold versus all endpoint Floyd");if(!detailed)return;
 auto x=positions(a);const auto bound=explicit_bounds(a,x,k,true);std::size_t pair=0;bool any=false;
 for(int u=0;u<int(x.size());++u)for(int v=u+1;v<int(x.size());++v){I64 sum=x[u]+x[v],diff=x[v]-x[u];bool accepted=bound[0]<=sum&&sum<=bound[1]&&bound[2]<=diff&&diff<=bound[3];need(accepted==(exact.diameters[pair++]<=k),"aggregated bounds versus actual graph diameter");any|=accepted;}
 need(path_shortcut_detail::station_pair(x,bound)==any,"actual discrete pointer versus all station endpoints");
 I64 top_two=0;for(int i=0;i<int(x.size());++i)for(int j=i+1;j<int(x.size());++j)top_two=std::max(top_two,I64(a.d[i])+a.d[j]);
 if(k>=top_two)for(int i=0;i<int(x.size());++i)for(int j=0;j<int(x.size());++j)if(i!=j&&x[i]-a.d[i]<x[j]+a.d[j]-k)need(i<j,"necessary top-two guard makes eligible orientation correct");
}
void run_case(const Data&a,bool dense,bool original){const auto before=hash(a);Literal exact=literal(a);PathShortcut p(a.l,a.d,a.c);++prepared;
 need(p.station_count()==int(a.d.size()),"station count");need(minimum(p)==exact.best,"prepared minimum versus literal graph");need(core(a)==exact.best,"generic minimum versus literal graph");if(original)need(adapter(a)==exact.best,"original minimum versus literal graph");
 if(dense)for(I64 k=0;k<=exact.original+1;++k)threshold(a,p,exact,k,true);
 else{std::set<I64>limits{0,exact.best-1,exact.best,exact.best+1,exact.original,std::numeric_limits<I64>::max()};for(auto k:limits)threshold(a,p,exact,k,k<=exact.original+1);}
 need(hash(a)==before,"all APIs preserve source input");
}
void exhaustive(){
 for(int n=2;n<=5;++n){for(int gaps=0;gaps<(1<<(n-1));++gaps){V l(n-1);for(int i=0;i<n-1;++i)l[i]=1+(gaps>>i&1);int total=1;for(int i=0;i<n;++i)total*=3;
  for(int code=0;code<total;++code){int value=code;V d(n);for(int&v:d){v=value%3;value/=3;}for(int c:{1,3}){++small_cases;run_case({l,d,c},true,true);}}
 }}
 for(int n=2;n<=6;++n)for(int mask=0;mask<(1<<n);++mask){V d(n);for(int i=0;i<n;++i)d[i]=mask>>i&1;for(int c:{1,2,4}){++binary_cases;run_case({V(n-1,1),d,c},true,true);}}
}
void arbitrary_boxes(){
 for(int mask=0;mask<64;++mask)if(std::popcount(unsigned(mask))>=2){std::vector<I64>x;for(int i=0;i<6;++i)if(mask>>i&1)x.push_back(i);
  for(int sl=-1;sl<=11;++sl)for(int sh=sl;sh<=11;++sh)for(int dl=-1;dl<=7;++dl)for(int dh=dl;dh<=7;++dh){Box b{sl,sh,dl,dh};bool expected=false;
   for(int i=0;i<int(x.size());++i)for(int j=i+1;j<int(x.size());++j){++box_pairs;expected|=sl<=x[i]+x[j]&&x[i]+x[j]<=sh&&dl<=x[j]-x[i]&&x[j]-x[i]<=dh;}
   need(path_shortcut_detail::station_pair(x,b)==expected,"all arbitrary four-bound boxes literal station pairs");++boxes;rec(expected);
  }
 }
 need(!path_shortcut_detail::station_pair({0,2},{2,2,1,1}),"continuous half-integer endpoints are not stations");
 need(!path_shortcut_detail::station_pair({0,2},{0,4,0,0}),"same endpoint forbidden even distance zero bound");
}
void random_tests(){
 for(int it=0;it<1120;++it){int n=it<1000?2+int(rng()%9):11+int(rng()%6);Data a{V(n-1),V(n),1};int range=it%3==0?1000000000:30;for(auto&v:a.l)v=1+int(rng()%range);for(auto&v:a.d)v=int(rng()%(range+1ULL));a.c=1+int(rng()%range);++random_cases;run_case(a,false,true);
  if(it<120){auto expected=literal(a).best;auto reverse=a;std::reverse(reverse.l.begin(),reverse.l.end());std::reverse(reverse.d.begin(),reverse.d.end());need(core(reverse)==expected,"line reflection");++metamorphic;
   if(range==30){auto scaled=a;for(auto&v:scaled.l)v*=7;for(auto&v:scaled.d)v*=7;scaled.c*=7;need(core(scaled)==7*expected,"all edge lengths scale");++metamorphic;}
  }
 }
 const std::vector<std::pair<Data,I64>> examples{{{{10,20,20},{0,40,0,30},10},80},{{V(8,10),{20,0,30,0,0,40,0,40,0},30},110},{{{2,2,2},{1,10,10,1},1},21},{{{1,1},{1,1,1},3},4},{{{10,100},{100,0,0},1},110},{{{1},{100,0},1},101}};
 for(const auto&[a,answer]:examples){need(literal(a).best==answer,"official/self-exclusion witness");run_case(a,false,true);}
}
// Independent homogeneous-cycle formula: enumerate every possible shortcut span,
// balance the two tails, and inspect the two integer vertices nearest antipodal.
I64 homogeneous(int n,I64 edge,I64 leaf,I64 c){I64 best=std::numeric_limits<I64>::max();for(int span=1;span<n;++span){int k=int(std::min<I64>(span,(I64(span)*edge+c)/(2*edge)));I64 radius=0;
 for(int j=k;j<=std::min(span,k+1);++j)radius=std::max(radius,std::min(I64(j)*edge,I64(span-j)*edge+c));
 I64 tails=I64(n-1-span)*edge,max_tail=I64((n-span)/2)*edge;I64 value=std::max(tails+std::min(I64(span)*edge,c),max_tail+radius);best=std::min(best,value);}
 return best+2*leaf;}
struct MaxCase{std::string name;I64 answer;double seconds;};static std::vector<MaxCase>maximums;
void maximum_case(std::string name,const Data&a,I64 expected,bool original){need(a.d.size()==1000000,"full source N");auto start=std::chrono::steady_clock::now();auto memory=live_bytes;peak_bytes=memory;PathShortcut p(a.l,a.d,a.c);++prepared;largest_payload=std::max(largest_payload,peak_bytes-memory);
 need(minimum(p)==expected,"maximum source closed-form optimum");need(!decide(p,expected-1)&&decide(p,expected)&&decide(p,INT64_MAX),"maximum decision boundary/INT64_MAX");
 double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();maximums.push_back({std::move(name),expected,seconds});if(original)need(adapter(a)==expected,"maximum original adapter");}
void maximum_tests(){const int n=1000000,M=1000000000;
 for(int edge:{1,M})for(int leaf:{0,M})for(int c:{1,M}){Data a{V(n-1,edge),V(n,leaf),c};maximum_case("homogeneous path/leaf/shortcut",a,homogeneous(n,edge,leaf,c),edge==M&&leaf==M);}
 {Data a{V(n-1,999999937),V(n,123456789),555555557};maximum_case("nonuniform antipodal remainder in homogeneous cycle",a,homogeneous(n,999999937,123456789,555555557),true);}
 {Data a{V(n-1),V(n),M};I64 total=0;for(auto&v:a.l){v=1+int(rng()%100);total+=v;}for(auto&v:a.d)v=int(rng()%(M+1ULL));a.d.front()=a.d.back()=M;maximum_case("random edges/branches, unusably long shortcut",a,total+2*I64(M),true);}
 for(int c:{1,M}){Data a{V(n-1,1),V(n),c};for(int i=0;i<n;++i)a.d[i]=i;maximum_case("all a_i equal; largest branches adjacent",a,2*I64(n-1),false);std::reverse(a.d.begin(),a.d.end());maximum_case("all b_i equal; largest branches adjacent",a,2*I64(n-1),false);}
 need(largest_payload==56000000,"three prepared vector payloads on tested ABI");
}
template<class F>void invalid(F fn){bool caught=false;try{fn();}catch(const std::invalid_argument&){caught=true;}need(caught,"invalid_argument contract");++invalids;}
template<class F>void empty_error(F fn){bool caught=false;try{fn();}catch(const std::logic_error&){caught=true;}need(caught,"moved-empty logic_error");++state_cases;}
void move_assign(PathShortcut& target,PathShortcut& source){target=std::move(source);}
void api_tests(){
 invalid([]{PathShortcut p({}, {},1);});invalid([]{PathShortcut p({}, {0},1);});invalid([]{PathShortcut p({1},{0,0,0},1);});invalid([]{PathShortcut p({1,1},{0,0},1);});
 for(int bad:{INT_MIN,-1,0,1000000001,INT_MAX}){invalid([&]{PathShortcut p({bad},{0,0},1);});invalid([&]{PathShortcut p({1},{0,0},bad);});}
 for(int bad:{INT_MIN,-1,1000000001,INT_MAX})invalid([&]{PathShortcut p({1},{0,bad},1);});
 Data oversized{V(1000000,1),V(1000001),1};invalid([&]{PathShortcut p(oversized.l,oversized.d,1);});
 for(int n:{INT_MIN,-1,0,1,3,1000001,INT_MAX})invalid([&]{(void)find_shortcut(n,{1},{0,0},1);});
 invalid([]{(void)find_shortcut(2,{},{0,0},1);});invalid([]{(void)find_shortcut(2,{1},{0},1);});
 PathShortcut p({10,100},{100,0,0},1);invalid([&]{(void)p.can_achieve(-1);});invalid([&]{(void)p.can_achieve(INT64_MIN);});
 auto copy=p;need(minimum(copy)==110&&minimum(p)==110,"copy independent");auto moved=std::move(copy);need(copy.station_count()==0&&minimum(moved)==110,"move empties source");empty_error([&]{(void)copy.minimum_diameter();});empty_error([&]{(void)copy.can_achieve(200);});
 auto empty_copy=copy;need(empty_copy.station_count()==0,"copy moved-empty");empty_error([&]{(void)empty_copy.minimum_diameter();});copy=p;need(minimum(copy)==110,"reassign moved-empty");move_assign(copy,copy);need(minimum(copy)==110,"self move assignment valid");
 Data input{{1,2,3},{2,3,4,5},2};const auto before=literal(input).best;PathShortcut detached(input.l,input.d,input.c);input.l.clear();input.d.assign(1,INT_MIN);need(minimum(detached)==before,"input lifetime independence");
 PathShortcut queries(V(1999,1),V(2000),1);const auto best=minimum(queries);fail_after=0;allocations=0;
 for(int i=0;i<5000;++i){need(queries.can_achieve(i)==(i>=best),"nonallocating prepared predicate");}for(int i=0;i<20;++i)need(queries.minimum_diameter()==best,"nonallocating repeated minimum");fail_after=-1;need(allocations==0,"query allocates after preparation");state_cases+=5020;
 for(int i=0;i<5000;++i){need(core({{1},{i%2?0:100,0},1})==(i%2?1:101),"independent repeated calls");++state_cases;}
}
template<class F>void allocation_faults(F fn,int wanted){auto memory=live_bytes;fail_after=LONG_MAX;allocations=0;fn();int count=int(allocations);fail_after=-1;need(count==wanted,"observed construction/copy allocation count");need(live_bytes==memory,"successful temporary scratch freed");
 for(int at=0;at<count;++at){fail_after=at;allocations=0;bool caught=false;try{fn();}catch(const Injected&){caught=true;}fail_after=-1;need(caught,"allocation subtype identity propagates");need(live_bytes==memory,"allocation failure unwind bytes");++faults;fn();need(live_bytes==memory,"subsequent successful allocation recovery");}}
void exception_tests(){for(int n:{4,1000000}){V l(n-1,1),d(n);auto lc=l,dc=d;
 allocation_faults([&]{PathShortcut p(l,d,1);need(p.station_count()==n,"fault constructor station count");},3);need(l==lc&&d==dc,"constructor failure const input");
 allocation_faults([&]{(void)find_shortcut(n,l,d,1000000000);},5);need(l==lc&&d==dc,"adapter failure input copies");
 PathShortcut source(l,d,1);allocation_faults([&]{PathShortcut copy(source);need(copy.station_count()==n,"fault copy count");},3);
 V heavy(n,1000000000);PathShortcut target(l,heavy,1000000000);const I64 previous=target.minimum_diameter();const auto memory=live_bytes;
 for(int at=0;at<3;++at){fail_after=at;allocations=0;bool caught=false;try{target=source;}catch(const Injected&){caught=true;}fail_after=-1;
  need(caught&&live_bytes==memory,"strong copy assignment allocation unwind");need(target.can_achieve(previous)&&!target.can_achieve(previous-1),"failed assignment preserves complete target answer");need(source.can_achieve(n),"failed assignment preserves source");++faults;
 }
 target=source;need(target.station_count()==n&&target.can_achieve(n),"copy assignment recovers after errors");
 }}
int main(){try{auto start=std::chrono::steady_clock::now();exhaustive();arbitrary_boxes();random_tests();
 for(int n=2;n<=12;++n)for(int edge=1;edge<=4;++edge)for(int leaf=0;leaf<=2;++leaf)for(int c=1;c<=9;++c){Data a{V(n-1,edge),V(n,leaf),c};need(homogeneous(n,edge,leaf,c)==literal(a).best,"independent max-family formula selfcheck");}
 maximum_tests();api_tests();exception_tests();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"preparedInputs\":"<<prepared<<",\"preparedMinimumCalls\":"<<min_calls<<",\"genericFunctionCalls\":"<<core_calls<<",\"originalAdapterCalls\":"<<adapter_calls<<",\"explicitPredicateCalls\":"<<predicate_calls
 <<",\"allSmallN2to5\":"<<small_cases<<",\"allBinaryBranchPathsN2to6\":"<<binary_cases<<",\"randomAllEndpointFloydCases\":"<<random_cases<<",\"literalAugmentedGraphs\":"<<actual_graphs<<",\"floydRelaxations\":"<<floyd_relaxations
 <<",\"fourBoundaryEquivalences\":"<<boundary_comparisons<<",\"decisionThresholds\":"<<thresholds<<",\"arbitraryDiscreteBoxes\":"<<boxes<<",\"literalStationPairsForBoxes\":"<<box_pairs<<",\"metamorphicChecks\":"<<metamorphic
 <<",\"invalidCases\":"<<invalids<<",\"allocationFailuresInjected\":"<<faults<<",\"stateChecks\":"<<state_cases<<",\"maximumPreparedPayloadBytes\":"<<largest_payload<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
 bool comma=false;for(const auto&r:maximums){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<r.name<<"\",\"n\":1000000,\"answer\":"<<r.answer<<",\"prepareAndMinimumSeconds\":"<<r.seconds<<'}';}std::cout<<"]}\n";
 }catch(const std::exception&e){fail_after=-1;std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output');ap.add_argument('--article',default=str(pathlib.Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/path-shortcut-diameter-rotated-constraints-extrema-sweep.mdx'));args=ap.parse_args()
    raw=pathlib.Path(args.article).read_bytes();article=raw.decode();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.*)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料'];cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-shortcut-cpp-') as td:
        source=pathlib.Path(td)/'check.cpp';binary=pathlib.Path(td)/'check';source.write_text(cpp+'\n'+HARNESS);subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        run=subprocess.run([str(binary)],capture_output=True,text=True,env=env)
        if run.returncode:raise RuntimeError(run.stderr or run.stdout)
        result=json.loads(run.stdout);result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitized':args.sanitize,'articleSha256':hashlib.sha256(raw).hexdigest()})
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:pathlib.Path(args.output).write_text(text)
    print(text,end='')
if __name__=='__main__':main()
