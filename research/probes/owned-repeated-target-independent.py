#!/usr/bin/env python3
"""Independent finite-battery safety game and allocation-failure checks of actual MDX."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile,time
args=argparse.ArgumentParser();args.add_argument('--sanitize',action='store_true');a=args.parse_args()
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/buchi-owned-graph-repeated-target-attractor-elimination.mdx').read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1;cpp=fences[0]
assert hashlib.sha256(cpp.encode()).hexdigest()=='e8f17727cc378089486222a8168e5fa42abb26e79e4b56faee4410a70f0627c1'
harness=r'''
#include <cstddef>
#include <cstdint>
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
using V=std::vector<int>;using Arcs=std::vector<repeated_target::Arc>;using Graph=std::vector<V>;
std::uint64_t checks=0,checksum=0,inputs=0,full_graphs=0,exhaustive_inputs=0,random_inputs=0,safety_games=0,states_examined=0,finite_iterations=0,faults=0,body_faults=0,adapter_faults=0,strategy_starts=0,capacity_controls=0;
void require(bool b,const char*message){++checks;if(!b)throw std::runtime_error(message);}
void record(std::uint64_t x){checksum=checksum*1000003ULL+x;}
// This is a finite safety game on (vertex,remaining energy), not a repeated
// target attractor / SCC / first-visit-policy oracle. At a charger only the
// canonical fully charged state is live. Noncharger energy0 dies before the
// next edge; arrival at a charger first resets the energy to capacity.
V battery_safety(const V&owner,const V&target,const Graph&graph,int capacity,int fixed_player,const V&move){
 ++safety_games;int n=int(owner.size()),stride=capacity+1;V losing(n*stride,0);auto id=[&](int v,int e){return v*stride+e;};
 for(int v=0;v<n;++v)if(!target[v])losing[id(v,0)]=1;
 bool changed=true;
 while(changed){changed=false;++finite_iterations;V next=losing;
  for(int v=0;v<n;++v)for(int e=target[v]?capacity:1;e<=capacity;++e){int here=id(v,e);if(losing[here])continue;++states_examined;
   bool any=false,all=true;for(int w:graph[v]){if(owner[v]==fixed_player&&w!=move[v])continue;bool bad=losing[id(w,target[w]?capacity:e-1)];any|=bad;all&=bad;}
   if(owner[v]?all:any){next[here]=1;changed=true;}
  }losing.swap(next);
 }
 V result(n);for(int v=0;v<n;++v){result[v]=!losing[id(v,capacity)];record(result[v]);}
 // More initially available charge cannot make a safety-winning state lose.
 for(int v=0;v<n;++v)if(!target[v])for(int e=1;e<=capacity;++e)require(losing[id(v,e-1)]||!losing[id(v,e)],"energy monotonicity");
 return result;
}
void compare(const V&owner,const V&target,const Arcs&edges){
 ++inputs;int n=int(owner.size());Graph g(n);for(auto[u,v]:edges)g[u].push_back(v);
 const auto old_owner=owner,old_target=target;const auto old_edges=edges;
 const auto answer=repeated_target::solve_repeated_target_game(owner,target,edges);
 for(int v=0;v<n;++v)require(std::find(g[v].begin(),g[v].end(),answer.move[v])!=g[v].end(),"legal returned policy");
 const V all=battery_safety(owner,target,g,n,-1,answer.move);
 require(all==answer.winning,"finite safety versus source full-charge winners");
 // Restrict only one player's policy, leaving the opponent choices adaptive
 // and dependent on energy/history. Both full vectors must stay unchanged.
 const V fixed_a=battery_safety(owner,target,g,n,1,answer.move);
 const V fixed_b=battery_safety(owner,target,g,n,0,answer.move);
 require(fixed_a==all,"returned fixed A policy versus adaptive B");
 require(fixed_b==all,"returned fixed B policy versus adaptive A");strategy_starts+=2*n;
 require(owner==old_owner&&target==old_target&&edges==old_edges,"input mutation");
}
void exhaustive(){for(int n=1;n<=3;++n){Arcs edges;auto rows=[&](auto&&self,int u)->void{
 if(u==n){++full_graphs;for(int am=0;am<(1<<n);++am)for(int rm=0;rm<(1<<n);++rm){V owner(n),target(n);for(int v=0;v<n;++v){owner[v]=(am>>v)&1;target[v]=(rm>>v)&1;}compare(owner,target,edges);++exhaustive_inputs;}return;}
 for(int mask=1;mask<(1<<n);++mask){auto size=edges.size();for(int v=0;v<n;++v)if(mask>>v&1)edges.emplace_back(u,v);self(self,u+1);edges.resize(size);}
 };rows(rows,0);}}
void random_cases(){std::mt19937_64 rng(201707301001ULL);for(int trial=0;trial<1500;++trial){int n=4+int(rng()%61);V owner(n),target(n);for(int v=0;v<n;++v){owner[v]=rng()&1;target[v]=rng()%(2+trial%29)==0;}
 if(trial%11==0)std::fill(target.begin(),target.end(),0);if(trial%13==0)std::fill(target.begin(),target.end(),1);
 if(trial%17==0)std::fill(owner.begin(),owner.end(),0);if(trial%19==0)std::fill(owner.begin(),owner.end(),1);
 Arcs edges;V dest(n);std::iota(dest.begin(),dest.end(),0);for(int u=0;u<n;++u){std::shuffle(dest.begin(),dest.end(),rng);int degree=1+int(rng()%std::min(n,12));for(int j=0;j<degree;++j)edges.emplace_back(u,dest[j]);}
 compare(owner,target,edges);++random_inputs;
 }}
void boundary_capacity(){for(int n=2;n<=64;++n){V owner(n,0),target(n,0);target[0]=1;Graph g(n);V move(n);Arcs edges;for(int v=0;v<n;++v){move[v]=(v+1)%n;g[v].push_back(move[v]);edges.emplace_back(v,move[v]);}
 auto exact=battery_safety(owner,target,g,n,-1,move),shorter=battery_safety(owner,target,g,n-1,-1,move);
 require(exact==V(n,1),"capacity N must traverse exact charging gap N");require(shorter==V(n,0),"capacity N-1 must stop before exact N-gap recharge");++capacity_controls;
 }}
void fault_injection(){const V owner{0,0,1,0,1,0,1,1},target{0,1,0,1,0,1,0,1};const Arcs edges{{0,0},{1,0},{2,1},{2,2},{3,2},{4,3},{4,4},{5,4},{6,5},{6,6},{7,7}};V u,v;for(auto[x,y]:edges){u.push_back(x);v.push_back(y);}const V expected{0,0,0,0,0,0,0,1};
 const auto original_owner=owner,original_target=target,original_u=u,original_v=v;const auto original_edges=edges;
 for(int adapter=0;adapter<2;++adapter){bool done=false;for(int at=0;at<2000;++at){fail_after=at;counting=true;
  try{{if(adapter){auto result=who_wins(owner,target,u,v);fail_after=-1;require(result==expected,"adapter after allocation recovery");}else{auto result=repeated_target::solve_repeated_target_game(owner,target,edges);fail_after=-1;require(result.winning==expected&&result.deletion_rounds==4,"body after allocation recovery");}}counting=false;require(live==0,"successful API leaves no tracked payload");done=true;break;}
  catch(const std::bad_alloc&){fail_after=-1;counting=false;++faults;if(adapter)++adapter_faults;else ++body_faults;}
  require(live==0,"allocation failure unwinds all API state");require(owner==original_owner&&target==original_target&&edges==original_edges&&u==original_u&&v==original_v,"allocation failure changes caller inputs");
  auto recovery=repeated_target::solve_repeated_target_game(owner,target,edges);require(recovery.winning==expected&&recovery.deletion_rounds==4,"fresh API call after allocation failure");
 }require(done,"allocation failure enumeration terminates");}
}
std::size_t measure_maximum(int adapter){int n=5000,k=2499;V owner(n,1),target(n,0);Arcs edges{{0,0},{n-1,n-1}};
 for(int i=1;i<=k;++i){int c=2*i-1,x=2*i;target[c]=1;edges.emplace_back(c,i==1?0:2*(i-1));edges.emplace_back(x,x);edges.emplace_back(x,c);}
 for(int i=1;i<=k&&edges.size()<20000;++i)for(int j=1;j<i&&edges.size()<20000;++j)edges.emplace_back(2*i,2*j);
 V u,v;for(auto[x,y]:edges){u.push_back(x);v.push_back(y);}const V expected(n,0);peak=0;require(live==0,"begin max memory window");counting=true;
 {if(adapter){auto result=who_wins(owner,target,u,v);require(result==expected,"maximum callback output");}else{auto result=repeated_target::solve_repeated_target_game(owner,target,edges);require(result.winning==expected&&result.deletion_rounds==2500,"maximum rounds body output");}}
 counting=false;require(live==0,"maximum API payload not retained");return peak;
}
int main(){exhaustive();random_cases();boundary_capacity();fault_injection();auto body_bytes=measure_maximum(0),adapter_bytes=measure_maximum(1);
 std::cout<<"{\"checks\":"<<checks<<",\"inputs\":"<<inputs<<",\"exhaustiveTotalGraphs\":"<<full_graphs<<",\"exhaustiveOwnerAndTargetAssignmentsIncludingEmpty\":"<<exhaustive_inputs<<",\"randomInputs\":"<<random_inputs<<",\"finiteBatterySafetyGames\":"<<safety_games<<",\"finiteSafetyIterations\":"<<finite_iterations<<",\"energyStateInspections\":"<<states_examined<<",\"returnedPolicyAdaptiveOpponentInitialPositions\":"<<strategy_starts<<",\"exactCapacityBoundaryControls\":"<<capacity_controls<<",\"allocationFailureExceptions\":"<<faults<<",\"bodyAllocationFailures\":"<<body_faults<<",\"adapterAllocationFailures\":"<<adapter_faults<<",\"maximum2500RoundBodyRequestedPayloadBytes\":"<<body_bytes<<",\"maximum2500RoundAdapterRequestedPayloadBytes\":"<<adapter_bytes<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
start=time.monotonic()
flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-mismatched-new-delete']
if a.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
with tempfile.TemporaryDirectory(prefix='flowchartcp-train-battery-oracle-')as td:
 src=Path(td)/'probe.cpp';exe=Path(td)/'probe';src.write_text(cpp+'\n'+harness)
 subprocess.run(['g++',*flags,str(src),'-o',str(exe)],check=True)
 env=os.environ.copy()
 if a.sanitize:
  env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
  env['UBSAN_OPTIONS']='halt_on_error=1'
 result=json.loads(subprocess.check_output([str(exe)],text=True,env=env))
result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'secondsIncludingCompilation':time.monotonic()-start,'sanitize':a.sanitize,'compilerFlags':flags,'sanitizerEnvironment':{'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'} if a.sanitize else {},'oracle':'Literal finite battery states (v,e),0<=e<=N; chargers reset immediately to N, noncharger energy0 dies before attempting the next edge. A state loses if every next state loses at an A-owned vertex, or any next state loses at a B-owned vertex. A synchronous finite safety fixed point is computed on the expanded graph. This uses neither repeated Buchi-region elimination, SCC cycle certificates, nor first-visit/fixed-policy enumeration. Run unrestricted, then with just returned A moves fixed, then just returned B moves fixed; both opponents remain adaptive and may depend on remaining energy.','sourceVsExpandedProof':'The independently reviewed positional A strategy has no reachable target-free cycle even against adaptive B, so any charge gap is <=N. The independently reviewed positional B strategy forces only finitely many charges even against adaptive A, and thus eventually battery exhaustion. Therefore the capacity-N finite safety classifications must equal the original first-visit source classifications. The independent oracle also explicitly distinguishes capacity N from N-1 on every single-charger N-cycle for N=2..64.','memoryScope':'Live requested allocation payload only, excluding allocator/header/ASan overhead, caller preexisting arguments, compiler, oracle graphs. Only API-created storage is allocated in the measurement window; expected answers are constructed beforehand. Only the tested N5000/M20000/2500-deletion-round construction is measured, not a universal maximum-byte claim.','sharedOrAuthorArtifactsModified':False})
print(json.dumps(result,ensure_ascii=False,indent=2))
