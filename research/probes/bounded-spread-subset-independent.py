#!/usr/bin/env python3
"""Cardinality-generating polynomial, fixed-cardinality offset, allocation faults.

This is a new independent check. It does not execute or import the author harness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--sanitize', action='store_true')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
article = Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/bounded-spread-subset-sum-sorted-window-witness.mdx'
cpp = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
assert len(cpp) == 1
cpp_sha = hashlib.sha256(cpp[0].encode()).hexdigest()
assert cpp_sha == 'af88cbae982b487fc8b3055c91139f50b558f5f4a28a11076c993fa3b2fbf106'
tests = r'''
#include <array>
#include <bitset>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <new>
#include <numeric>
#include <random>
using I=std::int64_t;
using U=std::uint64_t;
using W=std::vector<I>;
using A=std::optional<std::vector<int>>;
U checks=0,api=0,profiles=0,cardinality_ranges=0,range_calls=0,offsets=0,reversed=0,allocation_failures=0,width_rejections=0,checksum=0;
long long allocation_remaining=-1;
struct AllocationMarker:std::bad_alloc{};
void* operator new(std::size_t size){
    if(allocation_remaining==0)throw AllocationMarker{};
    if(allocation_remaining>0)--allocation_remaining;
    if(void* p=std::malloc(size?size:1))return p;
    throw std::bad_alloc{};
}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void* operator new[](std::size_t size){return ::operator new(size);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete[](void* p,std::size_t)noexcept{std::free(p);}
void need(bool good,const char* text){++checks;if(!good){std::cerr<<"FAIL "<<text<<'\n';std::exit(1);}}
void mix(U value){checksum=checksum*1000003+value;}
A call(const W& w,I l,I u){++api;return subset_window::find_subset_in_range(l,u,std::span<const I>(w));}
void witness(const W& w,I l,I u,const A& answer,bool expected){
    need(bool(answer)==expected,"generating-polynomial existence matches API");mix(bool(answer));
    if(!answer)return;
    need(!answer->empty(),"positive bound requires nonempty witness");
    std::vector<bool> used(w.size());I sum=0;
    for(int index:*answer){need(index>=0&&std::size_t(index)<w.size(),"returned original index in range");need(!used[index],"returned original indices distinct");used[index]=true;sum+=w[index];}
    need(l<=sum&&sum<=u,"original-index witness has requested sum");mix(U(sum));mix(answer->size());
}
bool in_range(const std::bitset<128>& coefficients,int l,int u){
    for(int sum=l;sum<=u;++sum)if(coefficients[sum])return true;
    return false;
}
void profile(const W& w){
    ++profiles;const int n=int(w.size()),total=int(std::accumulate(w.begin(),w.end(),I{})),spread=int(w.back()-w.front());
    // Boolean coefficients of product_i (1+y*z^w_i), retaining cardinality y.
    std::array<std::bitset<128>,10> polynomial{};polynomial[0].set(0);
    int seen=0;for(I x:w){++seen;for(int k=seen;k>0;--k)polynomial[k]|=polynomial[k-1]<<std::size_t(x);}
    std::vector<int> prefix(n+1);for(int j=0;j<n;++j)prefix[j+1]=prefix[j]+int(w[j]);
    for(int l=1;l<=total+2;++l){
        const int u=l+spread;bool any=false;
        for(int k=1;k<=n;++k){
            const bool expected=in_range(polynomial[k],l,u);bool window=false;
            for(int first=0;first+k<=n;++first){const int sum=prefix[first+k]-prefix[first];window|=l<=sum&&sum<=u;}
            need(window==expected,"every cardinality: exact minimal-width range iff sorted k-window exists");any|=expected;++cardinality_ranges;
        }
        witness(w,l,u,call(w,l,u),any);++range_calls;
    }
    if(profiles%113==0){
        for(int k=1;k<=n;++k){
            const int l=1+(k*13+int(profiles%71))%(total+2),u=l+spread;
            const I offset=200000000;
            W lifted=w;for(I& x:lifted)x+=offset;
            // The offset exceeds all small sums. No cardinality other than k
            // can meet [k*offset+l,k*offset+u]. Values stay inside source limits.
            std::reverse(lifted.begin(),lifted.end());
            auto answer=call(lifted,k*offset+l,k*offset+u);
            const bool expected=in_range(polynomial[k],l,u);
            witness(lifted,k*offset+l,k*offset+u,answer,expected);
            if(answer)need(int(answer->size())==k,"large offset forces exact cardinality");
            ++offsets;
        }
    }
    if(profiles%97==0){
        W input=w;std::reverse(input.begin(),input.end());
        const int l=total/2+1,u=l+spread;bool expected=false;
        for(int k=1;k<=n;++k)expected|=in_range(polynomial[k],l,u);
        witness(input,l,u,call(input,l,u),expected);++reversed;
    }
}
void generate(W& w,int next){
    if(!w.empty())profile(w);
    if(w.size()==9)return;
    for(int x=next;x<=8;++x){w.push_back(x);generate(w,x);w.pop_back();}
}
void guard_counterexamples(){
    for(const W& w:std::vector<W>{{1,2,4},{2,3,7},{3,4,9},{4,7,13}}){
        const I target=w.front()+w.back();
        bool consecutive=false;
        for(std::size_t i=0;i<w.size();++i){I sum=0;for(std::size_t j=i;j<w.size();++j){sum+=w[j];consecutive|=sum==target;}}
        need(!consecutive,"positive weights with width removed can require nonconsecutive subset");
        need(w.front()+w.back()==target,"explicit nonconsecutive witness exists");
        bool caught=false;try{(void)call(w,target,target);}catch(const std::invalid_argument&){caught=true;}
        need(caught,"public API rejects the violated width instead of false no-solution");++width_rejections;
    }
}
void allocation_tests(){
    for(int maximum=0;maximum<2;++maximum){
        W input=maximum?W(200000,1):W{6,8,8,7};const W original=input;
        const I l=maximum?200000:15,u=maximum?200000:17;
        const auto expected=call(input,l,u);need(bool(expected),"allocation case has answer");
        std::vector<int> adapter(input.begin(),input.end());const auto old_adapter=adapter;
        for(int budget=0;budget<=2;++budget){
            bool caught=false;A result;allocation_remaining=budget;
            try{++api;result=subset_window::find_subset_in_range(l,u,std::span<const I>(input));}catch(const AllocationMarker&){caught=true;}
            allocation_remaining=-1;
            need(caught==(budget<2),"both core allocation points throw exact custom bad_alloc subtype");need(input==original,"core input unchanged through allocation failure");
            if(caught)++allocation_failures;else need(result==expected,"core recovers after both allocations available");
        }
        for(int variant=0;variant<2;++variant)for(int budget=0;budget<=3;++budget){
            bool caught=false;std::vector<int> result;allocation_remaining=budget;
            try{++api;result=variant?find_subset(int(l),int(u),adapter):solve(int(l),int(u),adapter);}catch(const AllocationMarker&){caught=true;}
            allocation_remaining=-1;
            need(caught==(budget<3),"each by-value adapter copy/core/witness allocation propagates exact exception subtype");need(adapter==old_adapter,"adapter input unchanged through every allocation failure");
            if(caught)++allocation_failures;else need(result==*expected,"adapter recovers with all three allocations");
        }
        need(call(input,l,u)==expected,"new call after allocation failures is isolated");
        auto result=call(input,l,u);result->clear();need(call(input,l,u)==expected,"mutating returned value does not affect future result");
    }
    const W empty;allocation_remaining=0;bool failed=false;A result;
    try{++api;result=subset_window::find_subset_in_range(1,1,std::span<const I>(empty));}catch(...){failed=true;}
    allocation_remaining=-1;need(!failed&&!result,"empty generic domain needs no allocation and no positive witness");
}
int main(){
    const auto start=std::chrono::steady_clock::now();
    guard_counterexamples();W w;generate(w,1);allocation_tests();
    std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api<<",\"sortedMultisetsWeights1to8Length1to9\":"<<profiles
             <<",\"cardinalityMinimalWidthRangeComparisons\":"<<cardinality_ranges<<",\"minimumWidthApiCases\":"<<range_calls
             <<",\"largeOffsetFixedCardinalityCases\":"<<offsets<<",\"reverseIndexCases\":"<<reversed
             <<",\"allocationFailureExceptions\":"<<allocation_failures<<",\"widthViolationCounterexamples\":"<<width_rejections
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
             <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-molecules-independent-') as tmp:
    source = Path(tmp) / 'probe.cpp'
    binary = Path(tmp) / 'probe'
    source.write_text(cpp[0] + '\n' + tests)
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-mismatched-new-delete']
    env = dict(os.environ)
    if args.sanitize:
        flags = ['-std=c++20', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                 '-Wno-mismatched-new-delete', '-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++', *flags, str(source), '-o', str(binary)], check=True, timeout=120)
    run = subprocess.run(['/usr/bin/time', '-f', 'peak_rss_kib=%M', str(binary)],
                         capture_output=True, text=True, env=env, timeout=300)
    if run.returncode:
        print(run.stdout, end='')
        print(run.stderr, end='')
        run.check_returncode()
    result = json.loads(run.stdout)
    result.update(cppSha256=cpp_sha, sanitize=args.sanitize,
                  peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)', run.stderr)[1]))
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output, end='')
