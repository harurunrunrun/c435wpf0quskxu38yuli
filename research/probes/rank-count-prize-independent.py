#!/usr/bin/env python3
"""Read-only extraction; independent exact completion adversaries and fault tests."""
import argparse,hashlib,json,os,pathlib,re,subprocess,tempfile

HARNESS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <map>
#include <new>
#include <numeric>
#include <set>
#include <string>
#include <sys/resource.h>

struct InjectedAllocation : std::bad_alloc {};
static long fault=-1, allocation_calls=0;
static std::size_t live_bytes=0, peak_bytes=0;
struct alignas(std::max_align_t) AllocationHeader { std::size_t size; };
__attribute__((noinline)) void* operator new(std::size_t n) {
    if(fault>=0 && allocation_calls++==fault) throw InjectedAllocation{};
    auto* p=static_cast<AllocationHeader*>(std::malloc(sizeof(AllocationHeader)+n));
    if(!p) throw std::bad_alloc{};
    p->size=n;live_bytes+=n;peak_bytes=std::max(peak_bytes,live_bytes);
    return p+1;
}
__attribute__((noinline)) void operator delete(void* q) noexcept {
    if(q){auto* p=static_cast<AllocationHeader*>(q)-1;live_bytes-=p->size;std::free(p);}
}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
void operator delete(void* p,std::size_t) noexcept {::operator delete(p);}
void operator delete[](void* p,std::size_t) noexcept {::operator delete(p);}
using Reply=ranked_prizes::Reply;
using Result=ranked_prizes::Result;
using Oracle=ranked_prizes::Oracle;
static std::uint64_t checks=0, checksum=0, comparisons=0, api_calls=0, adaptive_runs=0, candidates=0;
static int worst_queries=0;
static int callback_faults=0,recurrence_states=0;
void need(bool x,const char* s){++checks;if(!x)throw std::runtime_error(s);}
void rec(std::uint64_t x){checksum=checksum*1000003+x;}

// A whole completion is represented exactly by its variable rank-1/rank-2
// positions plus fixed higher types. Everything else has the lowest rank.
struct Completion { unsigned mask; int best; };
struct Adversary {
    int n, variable_count, common, policy;
    std::vector<int> slots, fixed_rank;
    std::vector<std::vector<int>> pref;
    std::vector<Completion> possible;
    std::vector<bool> seen;
    int calls=0;
    Adversary(int len,int variables,int last,int strategy,std::vector<int> positions,
              const std::vector<int>& fixed_counts)
        :n(len),variable_count(variables),common(last),policy(strategy),slots(std::move(positions)),
         fixed_rank(n,common),pref(common+1,std::vector<int>(n+1)),seen(n) {
        need(slots.size()<=20,"small exact variable mask");
        std::vector<bool> occupied(n);for(int x:slots){need(!occupied[x],"distinct slots");occupied[x]=true;}
        int next=1;
        for(int rank=3;rank<common;++rank)for(int j=0;j<fixed_counts[rank];++j){
            while(occupied[next])++next;
            fixed_rank[next]=rank;occupied[next]=true;++next;
        }
        for(int rank=1;rank<=common;++rank)for(int i=0;i<n;++i)
            pref[rank][i+1]=pref[rank][i]+(fixed_rank[i]<rank);
        for(unsigned mask=0;mask<(1u<<slots.size());++mask)if(std::popcount(mask)==variable_count)
            for(int b=0;b<int(slots.size());++b)if(mask>>b&1)possible.push_back({mask,b});
        candidates+=possible.size();
        std::vector<int> counts(common+1);counts[1]=1;counts[2]=variable_count-1;
        for(int rank=3;rank<common;++rank)counts[rank]=fixed_counts[rank];
        counts[common]=n-std::accumulate(counts.begin(),counts.end(),0);
        for(int rank=2;rank<=common;++rank)need(std::int64_t(counts[rank])>std::int64_t(counts[rank-1])*counts[rank-1],"entire family legal");
    }
    Reply reply(const Completion& c,int index) const {
        int before=int(std::lower_bound(slots.begin(),slots.end(),index)-slots.begin());
        int rank=fixed_rank[index];
        if(before<int(slots.size())&&slots[before]==index&&(c.mask>>before&1))rank=before==c.best?1:2;
        if(rank==1)return {0,0};
        if(rank==2)return {slots[c.best]<index,slots[c.best]>index};
        int left=std::popcount(c.mask&((1u<<before)-1));
        return {pref[rank][index]+left,pref[rank][n]-pref[rank][index]+variable_count-left};
    }
    Reply operator()(int index) {
        need(index>=0&&index<n&&!seen[index],"valid uncached external ask");seen[index]=true;++calls;
        std::map<Reply,std::vector<Completion>> buckets;
        for(const auto& c:possible){++comparisons;buckets[reply(c,index)].push_back(c);}
        auto score=[&](const auto& entry){
            unsigned bests=0;for(const auto& c:entry.second)bests|=1u<<c.best;
            int distinct=std::popcount(bests),width=0;
            if(bests)width=int(std::bit_width(bests))-std::countr_zero(bests);
            int alive=entry.first[0]+entry.first[1]>0;
            if(policy==0)return std::array<long long,4>{alive,distinct,(long long)entry.second.size(),width};
            if(policy==1)return std::array<long long,4>{alive,(long long)entry.second.size(),distinct,width};
            return std::array<long long,4>{alive,width,distinct,(long long)entry.second.size()};
        };
        auto selected=buckets.begin();for(auto it=buckets.begin();it!=buckets.end();++it)if(score(*it)>score(*selected))selected=it;
        Reply result=selected->first;possible=std::move(selected->second);
        need(!possible.empty(),"nonempty legal transcript completions");return result;
    }
    void run(){
        ++api_calls;++adaptive_runs;
        auto out=ranked_prizes::find_unique_best(n,[&](int i){return (*this)(i);});
        need(out.queries==calls&&out.queries<=ranked_prizes::query_upper_bound(n),"adaptive budget/counters");
        need(out.maximum_pending<=18,"pending bound");
        for(const auto& c:possible)need(out.index==slots[c.best],"best in every final completion");
        worst_queries=std::max(worst_queries,out.queries);rec(out.queries);rec(out.index);rec(possible.size());
    }
};

// Independent exact worst-visit recurrence: enumerate every right scan length
// and every capacity-feasible left/right marked split, rather than balancing it.
void exact_visit_dp(){
    std::vector<std::vector<int>> cost(256);
    cost[0]={0};
    for(int n=1;n<=255;++n){
        cost[n].resize(n+1);int left=(n-1)/2,right=n-left;
        for(int k=1;k<=n;++k){
            ++recurrence_states;
            int value=k<=right?k:0;
            if(k>=right&&k-right<=left)value=std::max(value,right+cost[left][k-right]);
            for(int scanned=0;scanned<std::min(right,k);++scanned){
                int rem=k-scanned,rr=right-scanned-1;
                for(int a=std::max(0,rem-rr);a<=std::min(left,rem);++a)
                    value=std::max(value,scanned+1+cost[left][a]+cost[rr][rem-a]);
            }
            cost[n][k]=value;
            int d=0,h=std::bit_width(unsigned(n));for(int j=0;j<h;++j)d+=std::min(1<<j,k);
            need(value<=d,"all split exact visit potential");rec(value);
        }
    }
}
void fault_tests(){
    const int n=200000;
    std::vector<int> rank(n,5);rank[n-1]=1;
    for(int i=0;i<4;++i)rank[190000+i]=2;
    for(int i=0;i<21;++i)rank[180000+i]=3;
    for(int i=0;i<446;++i)rank[500+i*397]=4;
    std::vector<Reply> answers(n);int count[6]={};
    for(int x:rank)++count[x];
    int left[6]={};
    for(int i=0;i<n;++i){for(int t=1;t<rank[i];++t){answers[i][0]+=left[t];answers[i][1]+=count[t]-left[t];}++left[rank[i]];}
    int calls=0;Oracle oracle=[&](int i){++calls;return answers[i];};
    auto memory_base=live_bytes;
    for(int point=0;point<2;++point){
        calls=0;fault=point;allocation_calls=0;bool caught=false;
        try{++api_calls;(void)ranked_prizes::find_unique_best(n,oracle);}catch(const InjectedAllocation&){caught=true;}
        fault=-1;need(caught,"exact injected allocation exception propagation");
        need((point==0&&calls==0)||(point==1&&calls>0),"cache versus stack allocation timing");
        need(live_bytes==memory_base,"allocation exception leak freedom");rec(calls);
        calls=0;++api_calls;auto out=ranked_prizes::find_unique_best(n,oracle);
        need(out.index==n-1&&out.queries==calls,"reentrant recovery after allocation fault");rec(calls);
    }
    // Freeze all allocations only after the first search-stage ask. No further
    // allocation is needed because the pending vector has sufficient capacity.
    {
        calls=0;bool locked=false;Oracle locked_oracle=[&](int i){++calls;if(calls==2){fault=0;allocation_calls=0;locked=true;}return answers[i];};
        ++api_calls;auto out=ranked_prizes::find_unique_best(n,locked_oracle);fault=-1;
        need(locked&&out.index==n-1&&calls==out.queries&&allocation_calls==0,"search after reserve allocates nothing");
        rec(out.queries);
    }
    // Every callback point propagates the identical thrown object pointer.
    struct Marker{} marker;int full_calls=calls;
    for(int stop=0;stop<full_calls;++stop){
        ++callback_faults;
        calls=0;Oracle throwing=[&](int i)->Reply{if(calls++==stop)throw &marker;return answers[i];};
        bool caught=false;try{++api_calls;(void)ranked_prizes::find_unique_best(n,throwing);}catch(Marker* p){caught=p==&marker;}
        need(caught&&calls==stop+1,"identical callback exception no further ask");
    }
    need(live_bytes==memory_base+0,"fault tests no persistent core state");
}
int main(){
    auto start=std::chrono::steady_clock::now();
    exact_visit_dp();
    for(int policy=0;policy<3;++policy){
        for(int n:{80,200000}){
            std::vector<int> slots;for(int j=0;j<20;++j)slots.push_back(n==80?j*4:(j*199999)/19);
            Adversary(n,3,3,policy,slots,std::vector<int>(4)).run();
        }
        {
            std::vector<int> slots;for(int j=0;j<20;++j)slots.push_back((j*199999)/19);
            std::vector<int> fixed(6);fixed[3]=5;fixed[4]=26;
            Adversary(200000,3,5,policy,slots,fixed).run();
        }
        {
            std::vector<int> slots;for(int j=0;j<15;++j)slots.push_back((j*199999)/14);
            std::vector<int> fixed(6);fixed[3]=21;fixed[4]=446;
            Adversary(200000,5,5,policy,slots,fixed).run();
        }
    }
    fault_tests();
    rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"adaptiveRuns\":"<<adaptive_runs
      <<",\"initialLegalCompletionOccurrences\":"<<candidates<<",\"candidateReplyComparisons\":"<<comparisons
      <<",\"maximumAdaptiveQueries\":"<<worst_queries<<",\"allocationFaults\":2,\"callbackFaults\":"<<callback_faults
      <<",\"exactRecurrenceLengths\":255,\"exactRecurrenceStates\":"<<recurrence_states
      <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
      <<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sanitize',action='store_true');args=ap.parse_args()
    path=pathlib.Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/rank-count-oracle-equal-level-interval-pruning.mdx';raw=path.read_bytes()
    cpp=re.findall(r'^```cpp\n(.*?)^```',raw.decode(),re.M|re.S)
    assert len(cpp)==1
    sha=hashlib.sha256(cpp[0].encode()).hexdigest();assert sha=='af538cebe18119d7f93b645d56ee74ff3432d7225dcffe630f4d5bcff6a1947b'
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-prize-independent-') as td:
        src=pathlib.Path(td)/'extra.cpp';exe=pathlib.Path(td)/'extra'
        src.write_text('#include <cstddef>\n#include <cstdint>\n'+cpp[0]+HARNESS)
        subprocess.run(['g++',*flags,str(src),'-o',str(exe)],check=True)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(exe)],capture_output=True,text=True,env=env)
        if run.returncode:raise RuntimeError(run.stderr or run.stdout)
        result={'articleSha256':hashlib.sha256(raw).hexdigest(),'cppSha256':sha,'sanitize':args.sanitize,'result':json.loads(run.stdout)}
        print(json.dumps(result,indent=2))
if __name__=='__main__':main()
