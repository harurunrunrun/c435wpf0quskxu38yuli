#!/usr/bin/env python3
"""Read-only independent zero-support oracle and allocation/callback fault checks."""
import argparse, hashlib, json, os, pathlib, re, subprocess, tempfile

HARNESS = r'''
#include <array>
#include <chrono>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <random>
#include <set>
#include <sys/resource.h>
using P=std::vector<int>;
using M=std::array<std::uint64_t,2>;
static std::uint64_t checks=0,api_calls=0,checksum=0,all_perms=0,affines=0,transpositions=0,randoms=0,allocation_faults=0,callback_faults=0,callback_types=0,oracle_selfchecks=0;
static long fault=-1,allocations=0;
static std::size_t live_bytes=0;
struct Injected:std::bad_alloc{};
struct alignas(std::max_align_t) Header{std::size_t size;};
__attribute__((noinline)) void* operator new(std::size_t n){
 if(fault>=0&&allocations++==fault)throw Injected{};
 auto*p=static_cast<Header*>(std::malloc(sizeof(Header)+n));if(!p)throw std::bad_alloc{};
 p->size=n;live_bytes+=n;return p+1;
}
__attribute__((noinline)) void operator delete(void*q)noexcept{if(q){auto*p=static_cast<Header*>(q)-1;live_bytes-=p->size;std::free(p);}}
void*operator new[](std::size_t n){return::operator new(n);}
void operator delete[](void*p)noexcept{::operator delete(p);}
void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}
void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
void need(bool good,const char*message){++checks;if(!good)throw std::runtime_error(message);}
void record(std::uint64_t x){checksum=checksum*1000003ULL+x;}
M first(int k){return {k>=64?~std::uint64_t(0):(std::uint64_t(1)<<k)-1,k<=64?0:k==128?~std::uint64_t(0):(std::uint64_t(1)<<(k-64))-1};}
M interval(int l,int r){auto a=first(l),b=first(r);return {a[0]^b[0],a[1]^b[1]};}
void set(M&m,int i){m[i/64]|=std::uint64_t(1)<<(i%64);}
bool get(M m,int i){return m[i/64]>>(i%64)&1;}
M parse(const std::string&x){M m{};for(int i=0;i<int(x.size());++i){need(x[i]=='0'||x[i]=='1',"binary callback text");if(x[i]=='1')set(m,i);}return m;}
// This does not consult inserted strings, recurse, classify a candidate, or move bits forward.
// A legal word has exactly m-1 zeros in a single aligned dyadic block of size m,
// and its unique one inside that block is in the left half.
bool signature(M word,int n){auto valid=first(n);M zero{~word[0]&valid[0],~word[1]&valid[1]};
 int count=std::popcount(zero[0])+std::popcount(zero[1]);int m=count+1;
 if(!count||!std::has_single_bit(unsigned(m)))return false;
 int lo=zero[0]?std::countr_zero(zero[0]):64+std::countr_zero(zero[1]);
 int hi=zero[1]?127-std::countl_zero(zero[1]):63-std::countl_zero(zero[0]);
 int l=lo/m*m;if(hi>=l+m||l+m>n)return false;
 auto left=interval(l,l+m/2);return bool((word[0]&left[0])|(word[1]&left[1]));
}
P identity(int n){P p(n);std::iota(p.begin(),p.end(),0);return p;}
void oracle_selfcheck(){std::mt19937_64 rng(0xabcdef);
 for(int n:{1,2,4,8,16,32,64,128}){std::vector<M> literal;
  for(int m=2;m<=n;m*=2)for(int l=0;l<n;l+=m)for(int marker=l;marker<l+m/2;++marker){auto all=first(n),block=interval(l,l+m);M w{all[0]&~block[0],all[1]&~block[1]};set(w,marker);literal.push_back(w);}
  std::sort(literal.begin(),literal.end());auto compare=[&](M word){need(signature(word,n)==std::binary_search(literal.begin(),literal.end(),word),"zero-support oracle selfcheck against explicit complete source word set");++oracle_selfchecks;};
  if(n<=16){for(unsigned word=0;word<(1U<<n);++word)compare({word,0});}
  else{for(auto word:literal){compare(word);for(int i=0;i<n;++i){auto changed=word;changed[i/64]^=std::uint64_t(1)<<(i%64);compare(changed);}}auto mask=first(n);for(int trial=0;trial<10000;++trial)compare({rng()&mask[0],rng()&mask[1]});}
 }
}
struct Session{
 const P&p;int n,written=0,read=0,compiled=0;std::array<M,448> inserted{};
 explicit Session(const P&x):p(x),n(int(x.size())){}
 void add(const std::string&x){need(!compiled&&int(x.size())==n,"write before compile/length");auto m=parse(x);need(signature(m,n),"zero-support characterization of every write");inserted[written++]=m;}
 void compile(){need(!compiled,"exact single compile");auto need_budget=partition_membership::required_budget(n);need(written==need_budget.writes,"all writes complete before compile");
  std::sort(inserted.begin(),inserted.begin()+written);for(int i=1;i<written;++i)need(inserted[i-1]!=inserted[i],"all legal signatures exactly once");compiled=1;}
 bool check(const std::string&x){need(compiled&&int(x.size())==n,"read after compile/length");++read;
  M old{};for(int out=0;out<n;++out){need(x[out]=='0'||x[out]=='1',"binary read");if(x[out]=='1')set(old,p[out]);}
  return signature(old,n);
 }
};
P recover(Session&o){++api_calls;auto b=partition_membership::required_budget(o.n);
 auto answer=partition_membership::restore(o.n,b.writes,b.reads,[&](const std::string&x){o.add(x);},[&]{o.compile();},[&](const std::string&x){return o.check(x);});
 need(answer==o.p,"inverse pullback zero-support oracle restores p");need(o.written==b.writes&&o.read==b.reads&&o.compiled==1,"fixed nonadaptive phase counts");
 for(int x:answer)record(x);
 return answer;
}
void run(const P&p){Session s(p);recover(s);}
void group_tests(){
 for(int n:{1,2,4,8}){auto p=identity(n);std::set<std::array<unsigned char,12>> orbit;
  do{run(p);++all_perms;if(n==8){std::array<unsigned char,12> codes{};int at=0;
    for(unsigned original=0;original<256;++original)if(signature({original,0},8)){unsigned output=0;for(int i=0;i<8;++i)if(original>>p[i]&1U)output|=1U<<i;codes[at++]=static_cast<unsigned char>(output);}
    need(at==12,"independently characterize all 8-bit source signatures");std::sort(codes.begin(),codes.end());need(orbit.insert(codes).second,"all compiled signature sets in the permutation orbit differ");
   }}while(std::next_permutation(p.begin(),p.end()));
  if(n==8)need(orbit.size()==40320,"trivial automorphism group of the registered set");
 }
 for(int n:{1,2,4,8,16,32,64})for(int a=1;a<n||n==1;a+=2){for(int b=0;b<n;++b){P p(n);for(int i=0;i<n;++i)p[i]=(a*i+b)%n;run(p);++affines;}if(n==1)break;}
 for(int a=1;a<128;a+=2)for(int b:{0,127}){P p(128);for(int i=0;i<128;++i)p[i]=(a*i+b)%128;run(p);++affines;}
 for(int n:{16,32,64,128})for(int i=0;i<n;++i)for(int j=i+1;j<n;++j){auto p=identity(n);std::swap(p[i],p[j]);run(p);++transpositions;}
 std::mt19937_64 rng(0x2016beefULL);for(int trial=0;trial<256;++trial){auto p=identity(128);std::shuffle(p.begin(),p.end(),rng);run(p);++randoms;}
}
void allocation_tests(){
 P p=identity(128);std::rotate(p.begin(),p.begin()+37,p.end());int failures=0;
 for(long at=0;;++at){Session s(p);std::size_t memory=live_bytes;bool caught=false;fault=at;allocations=0;
  try{recover(s);}catch(const Injected&){caught=true;}fault=-1;
  need(live_bytes==memory,"every product allocation-failure unwind is leak free");
  if(!caught){need(at==allocations,"first nonfailing allocation budget");record(at);break;}
  ++allocation_faults;++failures;need(failures<=1024,"finite allocation-failure sweep");
  Session fresh(p);recover(fresh);need(p[0]==37,"source permutation preserved after allocation failure");
 }
 need(failures==510,"observed full-N128 allocation sites; not a portable API bound");
}
struct CallbackFailure{int index;};
void exception_tests(){
 P p{5,8,3,13,9,6,10,1,15,4,11,0,14,7,2,12};auto budget=partition_membership::required_budget(16);int total=budget.writes+1+budget.reads;
 for(int at=0;at<total;++at)for(bool after:{false,true}){Session s(p);int event=0;bool caught=false;++api_calls;
  auto before=[&]{if(event==at&&!after)throw CallbackFailure{at};};auto done=[&]{if(event++==at&&after)throw CallbackFailure{at};};
  try{partition_membership::restore(16,budget.writes,budget.reads,[&](const std::string&x){before();s.add(x);done();},[&]{before();s.compile();done();},[&](const std::string&x){before();bool v=s.check(x);done();return v;});}
  catch(const CallbackFailure&e){caught=e.index==at;}
  need(caught&&event==at+int(after),"all callback exceptions before/after side effects propagate unchanged");++callback_faults;Session fresh(p);recover(fresh);
 }
}
struct Add{std::unique_ptr<int>calls=std::make_unique<int>(0);Session*s;explicit Add(Session&o):s(&o){};void operator()(const std::string&x)&{++*calls;s->add(x);}void operator()(const std::string&)&&=delete;};
struct Compile{std::unique_ptr<int>calls=std::make_unique<int>(0);Session*s;explicit Compile(Session&o):s(&o){};void operator()()&{++*calls;s->compile();}void operator()()&&=delete;};
struct Check{std::unique_ptr<int>calls=std::make_unique<int>(0);Session*s;explicit Check(Session&o):s(&o){};bool operator()(const std::string&x)&{++*calls;return s->check(x);}bool operator()(const std::string&)&&=delete;};
void callable_tests(){auto p=identity(16);std::reverse(p.begin(),p.end());auto b=partition_membership::required_budget(16);
 for(bool wrappers:{false,true}){Session s(p);Add a(s);Compile c(s);Check q(s);++api_calls;
  auto answer=wrappers?partition_membership::restore(16,b.writes,b.reads,std::ref(a),std::ref(c),std::ref(q)):partition_membership::restore(16,b.writes,b.reads,std::move(a),std::move(c),std::move(q));
  need(answer==p&&*a.calls==b.writes&&*c.calls==1&&*q.calls==b.reads,"all three move-only &-qualified callback types preserve objects");++callback_types;
 }
 Session s(p);const auto a=[&](const std::string&x){s.add(x);};const auto c=[&]{s.compile();};const auto q=[&](const std::string&x){return s.check(x);};++api_calls;
 need(partition_membership::restore(16,INT_MAX,INT_MAX,a,c,q)==p,"const lvalue callbacks and INT_MAX budgets");++callback_types;
}
int main(){try{auto start=std::chrono::steady_clock::now();oracle_selfcheck();group_tests();allocation_tests();exception_tests();callable_tests();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"allSmallPermutations\":"<<all_perms<<",\"affinePermutations\":"<<affines<<",\"allTranspositions\":"<<transpositions<<",\"randomFull128\":"<<randoms<<",\"allocationFailures\":"<<allocation_faults<<",\"callbackExceptionsBeforeAfter\":"<<callback_faults<<",\"callbackTypeCases\":"<<callback_types<<",\"oracleSelfchecks\":"<<oracle_selfchecks<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
 }catch(const std::exception&e){fault=-1;std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output');args=ap.parse_args()
    article=(pathlib.Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/precompiled-permutation-partition-signature-membership.mdx').read_bytes();cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.decode(),re.M|re.S)[0]
    assert hashlib.sha256(cpp.encode()).hexdigest()=='b4497f26102e1d3ba262a63f98943aebe81c72b5b7ef6b18b283c2c11edbc609'
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-messy-independent-') as d:
        source=pathlib.Path(d)/'check.cpp';binary=pathlib.Path(d)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        r=subprocess.run([str(binary)],capture_output=True,text=True,env=env)
        if r.returncode:raise RuntimeError(r.stderr or r.stdout)
        result=json.loads(r.stdout);result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'articleSha256':hashlib.sha256(article).hexdigest(),'sanitize':args.sanitize})
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:pathlib.Path(args.output).write_text(text)
    print(text,end='')
if __name__=='__main__':main()
