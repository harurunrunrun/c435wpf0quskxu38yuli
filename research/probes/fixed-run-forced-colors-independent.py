#!/usr/bin/env python3
"""Enumerate block start positions directly, not binary rows or F/B tables."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args()
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/fixed-run-row-prefix-suffix-feasibility-forced-colors.mdx';cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S);assert len(cpp)==1
cppsha=hashlib.sha256(cpp[0].encode()).hexdigest();assert cppsha=='ec94273cd1ffaf3f0b71d23c9a58eadb00f964a42a62e86d2a9c7d375d08c29c'
test=r'''
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>
#include <random>
using U=std::uint64_t;using C=std::vector<int>;using A=std::optional<std::string>;
U checks=0,api=0,base_cases=0,clue_slack_profiles=0,placements=0,accepted=0,framed=0,pinned=0,adapter_calls=0,contradictions=0,faults=0,checksum=0;
struct Marker:std::bad_alloc{};
long countdown=-1;std::size_t live_bytes=0;
struct alignas(std::max_align_t) Header{std::size_t size;};
[[gnu::noinline]]void* operator new(std::size_t n){
 if(countdown==0)throw Marker{};
 if(countdown>0)--countdown;
 auto p=static_cast<Header*>(std::malloc(sizeof(Header)+(n?n:1)));if(!p)throw std::bad_alloc{};
 p->size=n;live_bytes+=n;return p+1;
}
[[gnu::noinline]]void operator delete(void* p)noexcept{if(p){auto h=static_cast<Header*>(p)-1;live_bytes-=h->size;std::free(h);}}
void* operator new[](std::size_t n){return ::operator new(n);}void operator delete[](void*p)noexcept{::operator delete(p);}
void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
void need(bool ok,const char* why){++checks;if(!ok){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void mix(U x){checksum=checksum*1000003+x;}
A call(const std::string& row,const C& clues){++api;return run_colors::forced_colors(row,std::span<const int>(clues));}
A oracle(const std::string& row,const C& clues){
 const int n=int(row.size()),k=int(clues.size());need(n<=63,"placement mask size bound");
 U black=0,white=0;for(int i=0;i<n;++i){if(row[i]=='X')black|=U{1}<<i;if(row[i]=='_')white|=U{1}<<i;}
 std::array<int,10> remaining{};for(int t=k-1;t>=0;--t)remaining[t]=remaining[t+1]+clues[t]+(t+1<k);
 bool any=false;U common=~U{},possible=0;
 auto place=[&](auto&& self,int t,int earliest,U mask)->void{
  if(t==k){++placements;if((mask&black)==black&&!(mask&white)){++accepted;any=true;common&=mask;possible|=mask;}return;}
  for(int start=earliest;start+remaining[t]<=n;++start){U block=((U{1}<<clues[t])-1)<<start;self(self,t+1,start+clues[t]+1,mask|block);}
 };
 place(place,0,0,0);if(!any)return std::nullopt;
 std::string answer(n,'_');for(int i=0;i<n;++i){if(common>>i&1)answer[i]='X';else if(possible>>i&1)answer[i]='?';}
 return answer;
}
void compare(const std::string& row,const C& clues,const A& expected){
 const auto before=row;const auto cb=clues;auto got=call(row,clues);need(got==expected,"direct block-start placement oracle");need(row==before&&clues==cb,"read-only API views");mix(bool(got));if(got)for(char ch:*got)mix(static_cast<unsigned char>(ch));
}
void case_for(const std::string& row,const C& clues){
 ++base_cases;auto expected=oracle(row,clues);compare(row,clues,expected);if(!expected)++contradictions;
 std::string outer="X_"+row+"_X";C outer_clues{1};outer_clues.insert(outer_clues.end(),clues.begin(),clues.end());outer_clues.push_back(1);
 A outer_expected;if(expected)outer_expected="X_"+*expected+"_X";
 compare(outer,outer_clues,outer_expected);++framed;
 if(expected&&base_cases%7==0){
  auto pos=expected->find('?');if(pos!=std::string::npos){
   auto a=row,b=row;a[pos]='X';b[pos]='_';auto left=oracle(a,clues),right=oracle(b,clues);
   need(bool(left)&&bool(right),"ambiguous cell has both feasible pin branches");compare(a,clues,left);compare(b,clues,right);
   std::string joined=*left;for(std::size_t i=0;i<joined.size();++i)if((*left)[i]!=(*right)[i])joined[i]='?';
   need(joined==*expected,"two color-pinned completion families join to original forced colors");pinned+=2;
  }
 }
 if(expected&&base_cases%13==0){++api;++adapter_calls;need(solve_puzzle(row,clues)==*expected,"source adapter agrees with independent placement oracle");}
}
void profile(const C& clues){
 int required=clues.empty()?0:int(clues.size())-1;for(int length:clues)required+=length;
 for(int slack=0;slack<=6;++slack){
  ++clue_slack_profiles;const int n=required+slack;std::string exact(n,'_');int at=0;for(int length:clues){for(int i=0;i<length;++i)exact[at+i]='X';at+=length+1;}
  for(int mode=0;mode<8;++mode){
   std::string row(n,'.');
   if(n){if(mode==1)row[0]='X';if(mode==2)row[n-1]='X';if(mode==3)row[0]='_';if(mode==4)row[n-1]='_';}
   if(mode>=5)for(int i=0;i<n;++i)if((i+mode)%3==0)row[i]=mode==6?(exact[i]=='X'?'_':'X'):exact[i];
   case_for(row,clues);
  }
 }
}
void generate(C& clues){if(!clues.empty())profile(clues);if(clues.size()==4)return;for(int length=1;length<=4;++length){clues.push_back(length);generate(clues);clues.pop_back();}}
void random_cases(){
 std::mt19937 rng(2016081604);
 for(int trial=0;trial<700;++trial){
  int k=int(rng()%8);C c(k);int required=k? k-1:0;for(int& x:c){x=1+int(rng()%5);required+=x;}
  const int n=required+int(rng()%9);std::string row(n,'.');
  for(char& ch:row){unsigned v=rng()%7;ch=v==0?'X':v==1?'_':'.';}case_for(row,c);
 }
}
void allocation_tests(){
 const std::string row(1024,'.');const C clues(20,3);const auto expected=call(row,clues);need(bool(expected),"allocation baseline feasible");
 const auto original=row;const auto old_clues=clues;const auto memory=live_bytes;
 for(int variant=0;variant<2;++variant){
  int observed=0;
  for(long point=0;point<32;++point){
   bool caught=false;A result;countdown=point;
   try{++api;if(variant)result=solve_puzzle(row,clues);else result=run_colors::forced_colors(row,std::span<const int>(clues));}catch(const Marker&){caught=true;}
   countdown=-1;
   if(!caught){need(result==expected,"success after every allocation site");observed=int(point);break;}
   ++faults;need(live_bytes==memory,"exact custom allocation exception unwinds all live bytes");need(row==original&&clues==old_clues,"allocation failures preserve both inputs");
   need(call(row,clues)==expected,"successful reentry after exception");
  }
  need(observed==(variant?8:6),"all tested core and by-value adapter allocation points covered");
 }
 need(live_bytes==memory,"allocation test leaves no persistent state");
}
int main(){
 const auto start=std::chrono::steady_clock::now();C c;profile(c);generate(c);random_cases();allocation_tests();
 need(clue_slack_profiles==2387,"all clue lists lengths1to4 plus zero list times seven slack values");
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api<<",\"baseObservationCases\":"<<base_cases<<",\"clueSlackProfiles\":"<<clue_slack_profiles
          <<",\"directBlockPlacements\":"<<placements<<",\"compatiblePlacements\":"<<accepted<<",\"knownSingletonFrameCases\":"<<framed<<",\"colorPinnedBranchCases\":"<<pinned
          <<",\"sourceAdapterCalls\":"<<adapter_calls<<",\"contradictoryCases\":"<<contradictions<<",\"allocationFailureExceptions\":"<<faults
          <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-paint-independent-')as td:
 source=Path(td)/'check.cpp';binary=Path(td)/'check';source.write_text(cpp[0]+'\n'+test)
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
 if args.sanitize:
  flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
 run=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
 if run.returncode:print(run.stdout,end='');print(run.stderr,end='');run.check_returncode()
 result=json.loads(run.stdout);result.update(cppSha256=cppsha,sanitize=args.sanitize,peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)',run.stderr)[1]));output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if args.output:args.output.write_text(output)
 print(output,end='')
