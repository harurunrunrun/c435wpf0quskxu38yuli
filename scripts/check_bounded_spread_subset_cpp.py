#!/usr/bin/env python3
"""Extract the sole visible article fence; compile and verify both public layers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS = r'''

#include <array>
#include <bit>
#include <chrono>
#include <climits>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <string>
#include <type_traits>
#include <tuple>
#include <sys/resource.h>
using I=std::int64_t;
using Answer=std::optional<std::vector<int>>;
using Weights=std::vector<I>;
std::uint64_t checks=0,api_calls=0,checksum=0,ordered_arrays=0,literal_assignments=0,range_cases=0,adapter_calls=0,random_cases=0,metamorphic=0,invalid_calls=0;
void require(bool x,const char* message){++checks;if(!x)throw std::runtime_error(message);}
void record(std::uint64_t x){checksum=checksum*1000003ULL+x;}
Answer core(const Weights&w,I lower,I upper){++api_calls;return subset_window::find_subset_in_range(lower,upper,std::span<const I>(w));}
void verify(const Weights&w,I lower,I upper,const Answer&r,bool expected){
    require(bool(r)==expected,"literal subset existence");record(bool(r));
    if(!r)return;
    require(!r->empty(),"positive lower bound forbids an empty successful witness");
    std::uint64_t mask=0;std::vector<unsigned char> used(w.size()>64?w.size():0);I total=0;
    for(int v:*r){require(v>=0&&std::size_t(v)<w.size(),"original index range");
        if(w.size()<=64){require(!(mask>>v&1),"distinct original index");mask|=1ULL<<v;}
        else{require(!used[v],"distinct large index");used[v]=1;}
        total+=w[v];
    }
    require(lower<=total&&total<=upper,"sum of actual original weights");record(total);record(r->size());
}
std::vector<I> literal_sums(const Weights&w){
    require(w.size()<=20,"small literal oracle bound");std::vector<I>sums(std::size_t(1)<<w.size());
    for(std::size_t mask=0;mask<sums.size();++mask){I sum=0;for(std::size_t i=0;i<w.size();++i)if(mask>>i&1)sum+=w[i];sums[mask]=sum;++literal_assignments;}
    return sums;
}
bool possible(const std::vector<I>&sums,I lower,I upper){return std::any_of(sums.begin(),sums.end(),[&](I s){return lower<=s&&s<=upper;});}
Answer adapter_result(std::vector<int> value){if(value.empty())return std::nullopt;return value;}
void adapters(const Weights&w,I lower,I upper,bool expected){
    const std::vector<int> input(w.begin(),w.end());
    ++adapter_calls;++api_calls;auto a=solve(int(lower),int(upper),input);verify(w,lower,upper,adapter_result(a),expected);
    ++adapter_calls;++api_calls;auto b=find_subset(int(lower),int(upper),input);verify(w,lower,upper,adapter_result(b),expected);
    require(a==b,"two source edition adapters share the same algorithm");require(std::equal(input.begin(),input.end(),w.begin()),"adapter caller input retained");
}
void exhaustive(){
    for(int n=1;n<=7;++n){std::uint64_t count=1ULL<<(2*n);
        for(std::uint64_t code=0;code<count;++code){Weights w(n);auto c=code;for(I&x:w){x=I(c%4)+1;c/=4;}++ordered_arrays;
            const auto sums=literal_sums(w);const int total=int(std::accumulate(w.begin(),w.end(),I{})),limit=total+2;
            std::vector<int> prefix(limit+1);for(I x:sums)if(x<=limit)prefix[std::size_t(x)]=1;
            for(int i=1;i<=limit;++i){prefix[i]+=prefix[i-1];}const auto [small,large]=std::minmax_element(w.begin(),w.end());
            for(int lower=1;lower<=limit;++lower)for(int upper=lower;upper<=limit;++upper)if(upper-lower>=*large-*small){
                const bool expected=prefix[upper]>prefix[lower-1];auto answer=core(w,lower,upper);verify(w,lower,upper,answer,expected);++range_cases;
                if(n<=4)adapters(w,lower,upper,expected);
            }
        }
    }
}
template<class F>void invalid(F function){++invalid_calls;bool caught=false;try{function();}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid API rejected distinctly from no solution");}
template<class T>concept Supported=requires(std::span<const T>s){subset_window::find_subset_in_range(1,2,s);};
static_assert(Supported<signed char>&&Supported<short>&&Supported<int>&&Supported<I>);
static_assert(!Supported<unsigned>&&!Supported<double>);
static_assert(std::is_same_v<decltype(&solve),std::vector<int>(*)(int,int,std::vector<int>)>);
static_assert(std::is_same_v<decltype(&find_subset),std::vector<int>(*)(int,int,std::vector<int>)>);
void api_tests(){
    require(!core({},1,1),"empty generic input has no positive-sum solution");adapters({},1,1,false);
    const Weights one{1};const I high=subset_window::max_value;
    for(const auto range:std::vector<std::pair<I,I>>{{0,1},{-1,1},{1,0},{2,1},{1,high+1},{LLONG_MIN,LLONG_MAX},{LLONG_MAX,LLONG_MAX},{1,LLONG_MIN}})
        invalid([&]{core(one,range.first,range.second);});
    for(I value:{I(0),I(-1),high+1,I(LLONG_MIN),I(LLONG_MAX)})invalid([&]{core({1,value},1,high);});
    invalid([&]{core({},0,0);});invalid([&]{core({2,3,7},9,9);});
    const Weights too_many(200001,1);invalid([&]{core(too_many,1,1);});
    invalid([&]{++adapter_calls;++api_calls;solve(1,1,{1,0});});invalid([&]{++adapter_calls;++api_calls;find_subset(1,1,{1,-1});});
    invalid([&]{++adapter_calls;++api_calls;solve(0,1,{1});});invalid([&]{++adapter_calls;++api_calls;find_subset(2,1,{1});});
    invalid([&]{++adapter_calls;++api_calls;solve(9,9,{2,3,7});});invalid([&]{++adapter_calls;++api_calls;find_subset(9,9,{2,3,7});});
    const std::vector<int> too_many_int(200001,1);invalid([&]{++adapter_calls;++api_calls;solve(1,1,too_many_int);});invalid([&]{++adapter_calls;++api_calls;find_subset(1,1,too_many_int);});
    for(int mode=0;mode<2;++mode){Weights w{I(2147483646),I(2147483646)};auto a=core(w,high,high);verify(w,high,high,a,false);adapters(w,high,high,false);}
    const std::array<short,3>w16{2,3,4};++api_calls;verify({2,3,4},6,8,subset_window::find_subset_in_range(6,8,std::span<const short>(w16)),true);
    const std::array<signed char,3>w8{2,3,4};++api_calls;verify({2,3,4},6,8,subset_window::find_subset_in_range(6,8,std::span<const signed char>(w8)),true);
    for(const auto&[w,l,u]:std::vector<std::tuple<Weights,I,I>>{{{2147483647},2147483647,2147483647},{{2147483647},1,1},{{1},1,1},{{1,1},2,2},{{1,1},3,3},{{6,8,8,7},15,17},{{5,5,6,6},14,15},{{15,17,16,18},10,20}}){
        const auto before=w;bool expected=possible(literal_sums(w),l,u);verify(w,l,u,core(w,l,u),expected);adapters(w,l,u,expected);require(w==before,"read-only generic input");}
    const auto baseline=core({6,8,8,7},15,17);invalid([&]{core({0},1,1);});core({},1,1);require(core({6,8,8,7},15,17)==baseline,"state isolation after success,empty and exception");
}
void random_checks(){
    std::mt19937_64 rng(20160814);
    for(int trial=0;trial<1200;++trial){int n=int(rng()%16)+1;Weights w(n);for(I&x:w)x=trial<800?I(rng()%3000)+1:I(1073741800+rng()%47);
        const auto sums=literal_sums(w);const auto [low,high]=std::minmax_element(w.begin(),w.end());I spread=*high-*low;
        I lower=trial<800?I(rng()%50000)+1:2147483647-spread;I upper=lower+spread+(trial<800?I(rng()%100):0);
        auto answer=core(w,lower,upper);const bool expected=possible(sums,lower,upper);verify(w,lower,upper,answer,expected);++random_cases;
        auto reverse=w;std::reverse(reverse.begin(),reverse.end());verify(reverse,lower,upper,core(reverse,lower,upper),expected);++metamorphic;
        if(trial<800){auto scaled=w;for(I&x:scaled)x*=17;verify(scaled,17*lower,17*upper,core(scaled,17*lower,17*upper),expected);++metamorphic;}
        auto shuffled=w;std::shuffle(shuffled.begin(),shuffled.end(),rng);verify(shuffled,lower,upper,core(shuffled,lower,upper),expected);++metamorphic;
        adapters(w,lower,upper,expected);
    }
}
struct Maximum{std::string name;int n;bool exists;std::size_t witness;double seconds;};std::vector<Maximum>max_cases;
void max_case(const std::string&name,Weights w,I lower,I upper,bool expected){
    const auto before=w;const auto start=std::chrono::steady_clock::now();auto a=core(w,lower,upper);const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    verify(w,lower,upper,a,expected);adapters(w,lower,upper,expected);require(w==before,"maximum input unchanged");
    max_cases.push_back({name,int(w.size()),expected,a?a->size():0,seconds});
    require(core({1},1,1)==Answer(std::vector<int>{0}),"maximum call does not leak state");
}
void maximum(){
    const int n=200000;const I hi=subset_window::max_value;
    max_case("all one,all indices required",Weights(n,1),n,n,true);
    max_case("all one,unreachable upper value",Weights(n,1),hi,hi,false);
    max_case("all maximal weight,one witness",Weights(n,hi),hi,hi,true);
    max_case("all maximal minus one,32bit intermediate overflow trap",Weights(n,hi-1),hi,hi,false);
    max_case("all10000,all200000 indices required",Weights(n,10000),2000000000,2000000000,true);
    Weights w(n);std::iota(w.begin(),w.end(),I(4000));I lower=0;for(int i=0;i<20000;++i)lower+=w[i];std::reverse(w.begin(),w.end());
    max_case("descending arithmetic progression,known20000item witness",w,lower,lower+n-1,true);
    std::mt19937_64 rng(314159);for(I&x:w)x=I(rng()%2147483647)+1;max_case("full integer domain,loose range",w,1,hi,true);
    for(I&x:w){x=1073741824+I(rng()%47);}max_case("near half intmax,no cardinality can fit",w,hi-46,hi,false);
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_tests();exhaustive();random_checks();maximum();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"orderedWeightArrays\":"<<ordered_arrays<<",\"literalSubsetAssignments\":"<<literal_assignments<<",\"allValidSmallRangeCases\":"<<range_cases
 <<",\"adapterCalls\":"<<adapter_calls<<",\"randomInputs\":"<<random_cases<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
 bool comma=false;for(const auto&r:max_cases){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<r.name<<"\",\"n\":"<<r.n<<",\"exists\":"<<(r.exists?"true":"false")<<",\"witnessSize\":"<<r.witness<<",\"coreSeconds\":"<<r.seconds<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/bounded-spread-subset-sum-sorted-window-witness.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    assert '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-molecules-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
        source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(binary)],check=False,text=True,capture_output=True,env=env)
        if run.returncode:raise RuntimeError(run.stderr or run.stdout or f'native exit {run.returncode}')
    result=json.loads(run.stdout)
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':args.sanitize,'compilerFlags':flags,**result},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
