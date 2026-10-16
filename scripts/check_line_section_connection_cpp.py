#!/usr/bin/env python3
"""Extract the visible C++20 and compare against physical permutations/Held-Karp."""
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
#include <string>
#include <sys/resource.h>
#include <type_traits>
using Sections=std::vector<std::pair<int,int>>;
using I64=std::int64_t;
static_assert(std::is_same_v<decltype(&minimum_section_connection_length),I64(*)(const Sections&)>);
static_assert(std::is_same_v<decltype(&plan_roller_coaster),long long(*)(std::vector<int>,std::vector<int>)>);
struct Injected : std::bad_alloc {};
static long fault_after=-1,allocation_count=0;
static std::size_t live_bytes=0,peak_bytes=0;
struct alignas(std::max_align_t) AllocationHeader { std::size_t size; };
__attribute__((noinline)) void* operator new(std::size_t n){
 if(fault_after>=0&&allocation_count++==fault_after)throw Injected{};
 auto* p=static_cast<AllocationHeader*>(std::malloc(sizeof(AllocationHeader)+n));if(!p)throw std::bad_alloc{};
 p->size=n;live_bytes+=n;peak_bytes=std::max(peak_bytes,live_bytes);return p+1;
}
__attribute__((noinline)) void operator delete(void* q)noexcept{if(q){auto* p=static_cast<AllocationHeader*>(q)-1;live_bytes-=p->size;std::free(p);}}
void* operator new[](std::size_t n){return ::operator new(n);}void operator delete[](void* p)noexcept{::operator delete(p);}
void operator delete(void* p,std::size_t)noexcept{::operator delete(p);}void operator delete[](void* p,std::size_t)noexcept{::operator delete(p);}
static std::uint64_t checks=0,checksum=0,core_calls=0,adapter_calls=0,small_a=0,small_b=0,permutations=0,held_calls=0,held_relaxations=0,random_cases=0,metamorphic=0,max_cases=0,invalid_cases=0,faults=0,reentrant_calls=0;
static std::size_t max_core_payload=0,max_adapter_payload=0;
static std::mt19937_64 rng(0x16082016ULL);
void need(bool x,const char* why){++checks;if(!x)throw std::runtime_error(why);}
void rec(std::uint64_t x){checksum=checksum*1000003ULL+x;}
std::uint64_t fingerprint(const Sections& a){std::uint64_t h=a.size();for(auto [s,t]:a){h=h*100003+s;h=h*100003+t;}return h;}
I64 core(const Sections& a){const auto before=fingerprint(a),memory=live_bytes;peak_bytes=memory;const auto x=minimum_section_connection_length(a);++core_calls;
 max_core_payload=std::max(max_core_payload,peak_bytes-memory);need(live_bytes==memory,"core scratch survives return");need(before==fingerprint(a),"core modified const input");need(x>=0,"negative answer");rec(x);return x;}
I64 adapter(const Sections& a){std::vector<int>s,t;s.reserve(a.size());t.reserve(a.size());for(auto [x,y]:a){s.push_back(x);t.push_back(y);}const auto sb=s,tb=t;const auto memory=live_bytes;peak_bytes=memory;
 const auto x=plan_roller_coaster(s,t);++adapter_calls;max_adapter_payload=std::max(max_adapter_payload,peak_bytes-memory);need(live_bytes==memory,"adapter scratch survives return");need(s==sb&&t==tb,"adapter changed caller arrays");rec(x);return x;}
I64 literal(const Sections& a){std::vector<int>p(a.size());std::iota(p.begin(),p.end(),0);I64 best=std::numeric_limits<I64>::max();
 do{++permutations;int speed=1;I64 cost=0;for(int id:p){const auto [entry,exit]=a[id];int length=std::max(0,speed-entry);cost+=length;speed-=length;need(speed>0&&speed<=entry,"physical order invalid entry/positive speed");speed=exit;}best=std::min(best,cost);}while(std::next_permutation(p.begin(),p.end()));return best;}
I64 held_karp(const Sections& a){++held_calls;const int n=int(a.size()),full=(1<<n)-1;const I64 inf=std::numeric_limits<I64>::max()/4;std::vector<I64>dp(std::size_t(1<<n)*n,inf);
 for(int i=0;i<n;++i)dp[(1<<i)*n+i]=0;
 for(int mask=1;mask<=full;++mask)for(int last=0;last<n;++last)if(mask>>last&1){const auto value=dp[mask*n+last];if(value==inf)continue;for(int next=0;next<n;++next)if(!(mask>>next&1)){++held_relaxations;auto& target=dp[(mask|(1<<next))*n+next];target=std::min(target,value+std::max(0,a[last].second-a[next].first));}}
 return *std::min_element(dp.begin()+std::size_t(full)*n,dp.end());}
void compare(const Sections& a,I64 expected,bool original){need(core(a)==expected,"core disagrees with independent optimum");if(original)need(adapter(a)==expected,"original adapter disagrees with optimum");}
void exhaustive(){
 for(int maximum=2;maximum<=3;++maximum){const int last=maximum==2?6:5,alphabet=maximum*maximum;
  for(int n=2;n<=last;++n){std::uint64_t total=1;for(int i=0;i<n;++i)total*=alphabet;
   for(std::uint64_t code=0;code<total;++code){auto x=code;Sections a(n);for(auto& [s,t]:a){int digit=int(x%alphabet);x/=alphabet;s=digit/maximum+1;t=digit%maximum+1;}
    const auto exact=literal(a);if(maximum==2){++small_b;need(held_karp(a)==exact,"Held-Karp/literal crosscheck");}else ++small_a;
    compare(a,exact,true);
   }
  }
 }
}
void random_and_metamorphic(){
 for(int it=0;it<360;++it){const int n=it<320?2+int(rng()%11):16;Sections a(n);
  for(auto& [s,t]:a){const int range=it%3==0?7:1000000000;s=1+int(rng()%range);t=1+int(rng()%range);if(rng()%7==0)t=s;}
  const auto expected=held_karp(a);++random_cases;compare(a,expected,true);
  if(n<=8)need(literal(a)==expected,"random physical permutations/Held-Karp");
  auto shuffled=a;std::shuffle(shuffled.begin(),shuffled.end(),rng);need(core(shuffled)==expected,"section-label permutation");++metamorphic;
  auto dual=a;for(auto& [s,t]:dual){const int previous=s;s=1000000001-t;t=1000000001-previous;}need(core(dual)==expected,"reflection plus orientation reversal");++metamorphic;
  int maximum=0,minimum=1000000000;for(auto [s,t]:a){maximum=std::max({maximum,s,t});minimum=std::min({minimum,s,t});}
  const int shift=it%2==0?1-minimum:1000000000-maximum;auto translated=a;for(auto& [s,t]:translated){s+=shift;t+=shift;}need(core(translated)==expected,"translation invariance");++metamorphic;
  if(maximum<=10000000){const int scale=7;auto scaled=a;for(auto& [s,t]:scaled){s=s*scale+3;t=t*scale+3;}need(core(scaled)==expected*scale,"positive affine scaling");++metamorphic;}
 }
 Sections official{{1,7},{4,3},{5,8},{6,6}};compare(official,3,true);
 Sections disconnected{{1,10},{3,3},{7,7}};compare(disconnected,5,true);
 Sections high_exit{{1,1000000000},{2,1}};compare(high_exit,0,true);
}
void maximum_case(const Sections& a,I64 expected,bool original){need(a.size()==200000,"full source N");++max_cases;compare(a,expected,original);}
void maximum_tests(){const int n=200000,M=1000000000;Sections a(n);
 std::fill(a.begin(),a.end(),std::pair{1,M});maximum_case(a,I64(n-1)*(M-1),true);
 std::fill(a.begin(),a.end(),std::pair{M,1});maximum_case(a,0,true);
 std::fill(a.begin(),a.end(),std::pair{M,M});maximum_case(a,0,true);
 std::fill(a.begin(),a.end(),std::pair{1,1});maximum_case(a,0,true);
 for(int i=0;i<n;++i){a[i]={i+1,i+2};}a.back()={n,1};maximum_case(a,0,true);
 a[0]={1,M};for(int i=1;i<n;++i)a[i]={i+1,i+1};maximum_case(a,n-1,true);
 a[0]={1,5*n+1};for(int i=1;i<n;++i)a[i]={5*i+1,5*i+1};maximum_case(a,I64(5)*(n-1),true);
 for(int i=0;i<n/2;++i){a[i]={1,M};}for(int i=n/2;i<n;++i){a[i]={i*4000+1,i*4000+1};}maximum_case(a,I64(n/2-1)*(M-1),true);
 for(int i=0;i<n;++i){a[i]={2*i+2,2*i+3};}maximum_case(a,0,true);need(max_core_payload==8000012,"maximum four core-vector payloads");need(max_adapter_payload==11200012,"maximum by-value adapter payloads");
 for(int i=0;i<n;++i){a[i]={M-2*i-1,M-2*i};}maximum_case(a,0,true);
 a[0]={1,M};for(int i=1;i<n;++i)a[i]={M/2,M/2};maximum_case(a,M/2-1,true);
 for(int i=0;i<n;++i){a[i]=i<n/2?std::pair{1,M}:std::pair{1,1};}maximum_case(a,I64(n/2-1)*(M-1),true);
 std::vector<int> vertices(n);for(int i=0;i<n;++i)vertices[i]=i%2==0?i/2+1:M-i/2;
 for(int i=0;i<n;++i){a[i]={vertices[i],vertices[(i+1)%n]};}maximum_case(a,0,true);
 // Each maximum family also survives an arbitrary input ordering and the exact
 // path-reversal/coordinate-reflection bijection, with no computed source answer.
 for(int repeat=0;repeat<4;++repeat){
  a[0]={1,M};for(int i=1;i<n;++i)a[i]={i+1,i+1};std::shuffle(a.begin(),a.end(),rng);maximum_case(a,n-1,false);++metamorphic;
  for(auto& [s,t]:a){int old=s;s=M+1-t;t=M+1-old;}maximum_case(a,n-1,false);++metamorphic;
 }
}
template<class F>void invalid(F fn){bool caught=false;try{fn();}catch(const std::invalid_argument&){caught=true;}need(caught,"invalid input contract");++invalid_cases;}
void api_tests(){
 invalid([]{(void)minimum_section_connection_length({});});invalid([]{(void)minimum_section_connection_length({{1,1}});});
 Sections too_many(200001,{1,1});invalid([&]{(void)minimum_section_connection_length(too_many);});
 for(int bad:{INT_MIN,-1,0,1000000001,INT_MAX}){
  invalid([&]{(void)minimum_section_connection_length({{bad,1},{1,1}});});invalid([&]{(void)minimum_section_connection_length({{1,1},{1,bad}});});
  invalid([&]{(void)plan_roller_coaster({1,bad},{1,1});});invalid([&]{(void)plan_roller_coaster({1,1},{bad,1});});
 }
 invalid([]{(void)plan_roller_coaster({},{});});invalid([]{(void)plan_roller_coaster({1},{1});});invalid([]{(void)plan_roller_coaster({1,1},{1});});invalid([]{(void)plan_roller_coaster({1},{1,1});});
 std::vector<int> oversized(200001,1);invalid([&]{(void)plan_roller_coaster(oversized,oversized);});
 Sections at_end(200000,{1,1});at_end.back().second=INT_MAX;invalid([&]{(void)minimum_section_connection_length(at_end);});
 auto s=std::vector<int>(200000,1),t=s;t.back()=0;invalid([&]{(void)plan_roller_coaster(s,t);});
 for(int i=0;i<20000;++i){Sections a=i%2?Sections{{1,10},{3,3},{7,7}}:Sections{{1,1000000000},{1,1000000000}};const I64 expected=i%2?5:999999999;
  compare(a,expected,i%5==0);++reentrant_calls;}
}
template<class F>void allocation_faults(F fn){
 const auto memory=live_bytes;fault_after=LONG_MAX;allocation_count=0;fn();const long total=allocation_count;fault_after=-1;need(live_bytes==memory,"normal no persistent allocation");need(total>0&&total<=7,"observed core/adapter allocation count");
 for(long i=0;i<total;++i){fault_after=i;allocation_count=0;bool caught=false;try{fn();}catch(const Injected&){caught=true;}fault_after=-1;
  need(caught,"allocation exception identity");need(live_bytes==memory,"allocation unwind leak");++faults;fn();need(live_bytes==memory,"subsequent successful call leak");}
}
void exception_tests(){
 for(int n:{4,200000}){Sections a(n);for(int i=0;i<n;++i)a[i]={2*i+2,2*i+3};auto original=a;
  allocation_faults([&]{need(minimum_section_connection_length(a)==0,"fault test core value");});need(a==original,"fault core preserves input");
  std::vector<int>s,t;for(auto [x,y]:a){s.push_back(x);t.push_back(y);}const auto sb=s,tb=t;
  allocation_faults([&]{need(plan_roller_coaster(s,t)==0,"fault test adapter value");});need(s==sb&&t==tb,"fault adapter preserves input");
 }
}
int main(){try{const auto start=std::chrono::steady_clock::now();exhaustive();random_and_metamorphic();maximum_tests();api_tests();exception_tests();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<core_calls<<",\"originalAdapterCalls\":"<<adapter_calls<<",\"allArraysN2to5Speeds1to3\":"<<small_a
 <<",\"allArraysN2to6Speeds1to2\":"<<small_b<<",\"literalPhysicalPermutations\":"<<permutations<<",\"heldKarpCases\":"<<held_calls<<",\"heldKarpRelaxations\":"<<held_relaxations
 <<",\"randomHeldKarpCases\":"<<random_cases<<",\"metamorphicCases\":"<<metamorphic<<",\"maximumN200000Cases\":"<<max_cases<<",\"invalidCases\":"<<invalid_cases
 <<",\"allocationFailuresInjected\":"<<faults<<",\"reentrantBatchCalls\":"<<reentrant_calls<<",\"maximumCoreVectorPayloadBytes\":"<<max_core_payload<<",\"maximumAdapterAdditionalPayloadBytes\":"<<max_adapter_payload
 <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
 }catch(const std::exception& e){fault_after=-1;std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output');ap.add_argument('--article',default=str(pathlib.Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/directed-line-balance-euler-augmentation-mst.mdx'));args=ap.parse_args()
    raw=pathlib.Path(args.article).read_bytes();article=raw.decode();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.*)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-railroad-cpp-') as td:
        source=pathlib.Path(td)/'check.cpp';binary=pathlib.Path(td)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        run=subprocess.run([str(binary)],capture_output=True,text=True,env=env)
        if run.returncode:raise RuntimeError(run.stderr or run.stdout)
        result=json.loads(run.stdout);result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitized':args.sanitize,'articleSha256':hashlib.sha256(raw).hexdigest()})
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:pathlib.Path(args.output).write_text(text)
    print(text,end='')
if __name__=='__main__':main()
