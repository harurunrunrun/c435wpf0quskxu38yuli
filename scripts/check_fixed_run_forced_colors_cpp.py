#!/usr/bin/env python3
"""Verify the actual visible C++ fence against independently enumerated full rows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS = r'''
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <new>
#include <random>
#include <set>
#include <type_traits>
#include <tuple>
#include <sys/resource.h>
namespace fail_alloc { long countdown=-1; std::uint64_t attempts=0; }
[[gnu::noinline]] void* operator new(std::size_t n) {
    ++fail_alloc::attempts;
    if (fail_alloc::countdown==0) throw std::bad_alloc();
    if (fail_alloc::countdown>0) --fail_alloc::countdown;
    if (void* p=std::malloc(n?n:1)) return p;
    throw std::bad_alloc();
}
[[gnu::noinline]] void* operator new[](std::size_t n) { return ::operator new(n); }
[[gnu::noinline]] void operator delete(void* p) noexcept { std::free(p); }
[[gnu::noinline]] void operator delete[](void* p) noexcept { std::free(p); }
[[gnu::noinline]] void operator delete(void* p,std::size_t) noexcept { std::free(p); }
[[gnu::noinline]] void operator delete[](void* p,std::size_t) noexcept { std::free(p); }
using Clues=std::vector<int>;
using Answer=std::optional<std::string>;
std::uint64_t checks=0,api_calls=0,checksum=0,partial_rows=0,literal_pairs=0,exhaustive_pairs=0,source_samples=0,consistent_groups=0,source_groups=0,zero_groups=0,contradictions=0,adapter_calls=0,random_cases=0,metamorphic=0,invalid_calls=0,faults=0;
void require(bool good,const char* message){++checks;if(!good)throw std::runtime_error(message);}
void record(std::uint64_t value){checksum=checksum*1000003ULL+value;}
Answer core(std::string_view row,const Clues& clues){++api_calls;return run_colors::forced_colors(row,std::span<const int>(clues));}
void verify(std::string_view row,const Clues& clues,const Answer& actual,const Answer& expected){
    require(actual==expected,"literal all-completion color intersection/union");record(bool(actual));
    if(actual){require(actual->size()==row.size(),"output length");for(std::size_t v=0;v<row.size();++v){char ch=(*actual)[v];require(ch=='X'||ch=='_'||ch=='?',"output alphabet");if(row[v]!='.')require(ch==row[v],"known input color remains forced");record(static_cast<unsigned char>(ch));}}
    require(clues.size()<=row.size(),"test within declared clue count bound");
}
Clues literal_runs(int n,std::uint32_t mask){
    Clues result;int length=0;
    for(int v=0;v<n;++v){if(mask>>v&1U)++length;else if(length){result.push_back(length);length=0;}}
    if(length)result.push_back(length);
    return result;
}
struct Aggregate{std::uint32_t common=~0U,possible=0;};
Answer forced(int n,const Aggregate& group){
    std::string result(n,'_');for(int v=0;v<n;++v)if(group.common>>v&1U)result[v]='X';else if(group.possible>>v&1U)result[v]='?';return result;
}
void adapter(std::string row,Clues clues,const std::string& expected){
    const auto saved_row=row;const auto saved_clues=clues;++adapter_calls;++api_calls;
    auto actual=solve_puzzle(row,clues);require(actual==expected,"Notice-derived source adapter matches literal oracle");
    require(row==saved_row&&clues==saved_clues,"adapter caller input retained");record(actual.size());
}
void exhaustive(){
    for(int n=0;n<=10;++n){
        const std::uint32_t limit=1U<<n;std::vector<Clues> all_runs(limit);std::set<Clues> all_clues;
        for(std::uint32_t mask=0;mask<limit;++mask){all_runs[mask]=literal_runs(n,mask);all_clues.insert(all_runs[mask]);}
        std::uint32_t observations=1;for(int i=0;i<n;++i)observations*=3;
        for(std::uint32_t code=0;code<observations;++code){
            auto value=code;std::string row(n,'.');std::uint32_t black=0,white=0;
            for(int v=0;v<n;++v){const auto digit=value%3;value/=3;if(digit==1){row[v]='_';white|=1U<<v;}else if(digit==2){row[v]='X';black|=1U<<v;}}
            ++partial_rows;std::map<Clues,Aggregate> groups;
            for(std::uint32_t mask=0;mask<limit;++mask)if((mask&black)==black&&!(mask&white)){
                ++literal_pairs;++exhaustive_pairs;auto& group=groups[all_runs[mask]];group.common&=mask;group.possible|=mask;
            }
            for(const auto& [clues,group]:groups){
                const auto expected=forced(n,group);verify(row,clues,core(row,clues),expected);++consistent_groups;
                if(clues.empty())++zero_groups;else ++source_groups;
                if(n<=5)adapter(row,clues,*expected);
            }
            if(n<=7)for(const auto& clues:all_clues)if(!groups.contains(clues)){
                verify(row,clues,core(row,clues),std::nullopt);++contradictions;
            }
        }
    }
}
Answer literal_oracle(std::string_view row,const Clues& clues){
    require(row.size()<=19,"independent full binary assignment oracle bound");Aggregate group;bool exists=false;
    for(std::uint32_t mask=0;mask<(1U<<row.size());++mask){
        ++literal_pairs;bool fits=true;for(std::size_t v=0;v<row.size();++v)if((row[v]=='X'&&!(mask>>v&1U))||(row[v]=='_'&&(mask>>v&1U)))fits=false;
        if(fits&&literal_runs(int(row.size()),mask)==clues){exists=true;group.common&=mask;group.possible|=mask;}
    }
    return exists?forced(int(row.size()),group):std::nullopt;
}
template<class F>void invalid(F function){++invalid_calls;bool caught=false;try{function();}catch(const std::invalid_argument&){caught=true;}require(caught,"malformed input distinguished from well-formed contradiction");}
static_assert(std::is_same_v<decltype(&solve_puzzle),std::string(*)(std::string,std::vector<int>)>);
static_assert(std::is_same_v<decltype(run_colors::forced_colors(std::string_view{},std::span<const int>{})),Answer>);
void api_tests(){
    verify("",{},core("",{}),std::string{});adapter("",{},"");
    verify("...",{},core("...",{}),std::string("___"));adapter("...",{},"___");
    verify("X",{},core("X",{}),std::nullopt);
    verify("..",{1,1},core("..",{1,1}),std::nullopt);
    verify("X_X",{2},core("X_X",{2}),std::nullopt);
    verify("_",{1},core("_",{1}),std::nullopt);
    for(const auto& row:std::vector<std::string>{"?","x"," ","\n",std::string(".\0.",3),"X?X"})invalid([&]{core(row,{1});});
    invalid([&]{core("",{1});});invalid([&]{core(".",{1,1});});
    for(int length:{0,-1,2,std::numeric_limits<int>::min(),std::numeric_limits<int>::max()})invalid([&]{core(".",{length});});
    invalid([&]{core(std::string(200001,'.'),{1});});invalid([&]{core(std::string(300,'.'),Clues(101,1));});
    invalid([&]{core("..?",{1,1});}); // invalid color checked even when runs cannot fit
    invalid([&]{core("..",{2,0});}); // invalid clue checked before minimum-length rejection
    invalid([&]{++api_calls;++adapter_calls;solve_puzzle("_",{1});});
    invalid([&]{++api_calls;++adapter_calls;solve_puzzle("?",{1});});
    invalid([&]{++api_calls;++adapter_calls;solve_puzzle(".",{0});});
    for(const auto& [row,clues]:std::vector<std::pair<std::string,Clues>>{{"..........",{3,2}},{"_..X.._",{3}},{"XX_XX",{2,2}},{"...",{3}},{"_X_",{1}},{"X.X",{1,1}},{"X.X",{3}},{"X_X",{1,1}}}){
        const auto before=row;const auto before_clues=clues;auto expected=literal_oracle(row,clues);verify(row,clues,core(row,clues),expected);require(row==before&&clues==before_clues,"generic input read only");if(expected)adapter(row,clues,*expected);
    }
    require(core("...",{1})==Answer("???"),"state isolation before exception");invalid([&]{core("?",{});});
    core("X",{});core("",{});require(core("...",{1})==Answer("???"),"state isolation after failure,empty,exception");
}
void samples(){
    for(const auto& [row,clues,expected]:std::vector<std::tuple<std::string,Clues,std::string>>{{"..........",{3,4},"??X???XX??"},{"........",{3,4},"XXX_XXXX"},{"..._._....",{3},"???___????"},{".X........",{3},"?XX?______"}}){
        require(literal_oracle(row,clues)==Answer(expected),"primary sample independently rederived");verify(row,clues,core(row,clues),expected);adapter(row,clues,expected);++source_samples;
    }
}
void random_checks(){
    std::mt19937_64 rng(20160816);
    for(int trial=0;trial<1800;++trial){const int n=int(rng()%18)+1;std::uint32_t mask=std::uint32_t(rng()&((1ULL<<n)-1));Clues clues=literal_runs(n,mask);std::string row(n,'.');
        for(int v=0;v<n;++v)if(rng()%3==0)row[v]=mask>>v&1U?'X':'_';
        if(trial%4==0&&n>1){const int v=int(rng()%n);row[v]=row[v]=='X'?'_':'X';}
        auto expected=literal_oracle(row,clues);auto answer=core(row,clues);verify(row,clues,answer,expected);++random_cases;
        auto reverse_row=row;auto reverse_clues=clues;std::reverse(reverse_row.begin(),reverse_row.end());std::reverse(reverse_clues.begin(),reverse_clues.end());auto reverse_expected=expected;if(reverse_expected)std::reverse(reverse_expected->begin(),reverse_expected->end());
        verify(reverse_row,reverse_clues,core(reverse_row,reverse_clues),reverse_expected);++metamorphic;
        if(expected){adapter(row,clues,*expected);for(int v=0;v<n;++v)if((*expected)[v]!='?')row[v]=(*expected)[v];verify(row,clues,core(row,clues),expected);++metamorphic;}
        // Fixed white padding cannot create/remove a block; it shifts every completion.
        auto padded=std::string("__")+row+"___";auto padded_expected=expected;if(padded_expected)*padded_expected="__"+*padded_expected+"___";
        verify(padded,clues,core(padded,clues),padded_expected);++metamorphic;
    }
}
struct Maximum{std::string name;int n,k;bool exists;double seconds;};std::vector<Maximum> maxima;
void max_case(std::string name,const std::string& row,const Clues& clues,const Answer& expected){
    const auto before=row;const auto before_clues=clues;const auto start=std::chrono::steady_clock::now();auto answer=core(row,clues);double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();verify(row,clues,answer,expected);
    require(row==before&&clues==before_clues,"maximum input unchanged");if(expected)adapter(row,clues,*expected);maxima.push_back({std::move(name),int(row.size()),int(clues.size()),bool(answer),seconds});
    require(core("...",{1})==Answer("???"),"maximum call does not leak state");
}
void maximum(){
    constexpr int n=200000;
    max_case("full length single run",std::string(n,'.'),{n},std::string(n,'X'));
    max_case("single run length199999 overlaps",std::string(n,'.'),{n-1},"?"+std::string(n-2,'X')+"?");
    max_case("100 singleton runs,all positions ambiguous",std::string(n,'.'),Clues(100,1),std::string(n,'?'));
    Clues clues(100,1999);clues.back()=2000;std::string exact;for(int t=0;t<100;++t){if(t)exact+='_';exact+=std::string(clues[t],'X');}
    require(exact.size()==n,"maximum exact tight construction size");
    max_case("100 tight runs,no slack",std::string(n,'.'),clues,exact);
    max_case("all exact known cells",exact,clues,exact);
    auto contradiction=exact;contradiction[0]='_';max_case("known white in unique tight run",contradiction,clues,std::nullopt);
    max_case("100 runs each2000 cannot fit separators",std::string(n,'.'),Clues(100,2000),std::nullopt);
    std::string singleton_row(n,'.'),singleton_expected(n,'_');for(int t=0;t<100;++t){const int v=1999*t;singleton_row[v]='X';singleton_expected[v]='X';}
    max_case("100 separated mandatory singleton positions",singleton_row,Clues(100,1),singleton_expected);
    std::string blocked(n,'_');for(int i=50000;i<150000;++i)blocked[i]='.';std::string blocked_expected(n,'_');for(int i=50000;i<150000;++i)blocked_expected[i]='?';
    max_case("100 singleton runs inside known white margins",blocked,Clues(100,1),blocked_expected);
    max_case("zero run extension",std::string(n,'.'),{},std::string(n,'_'));
}
void allocation_tests(){
    const std::string row(1000,'.');const Clues clues(20,3);const auto expected=core(row,clues);require(bool(expected),"allocation baseline solvable");
    bool completed=false;
    for(long position=0;position<32;++position){
        bool failed=false;Answer answer;fail_alloc::countdown=position;
        try{++api_calls;answer=run_colors::forced_colors(row,std::span<const int>(clues));}catch(const std::bad_alloc&){failed=true;}
        fail_alloc::countdown=-1;
        if(!failed){require(answer==expected,"success after all allocation sites covered");completed=true;break;}
        ++faults;require(core(row,clues)==expected,"bad_alloc propagation and subsequent successful reentry");
    }
    require(completed&&faults>=6,"all successive core allocation points injected");
    require(row==std::string(1000,'.')&&clues==Clues(20,3),"allocation failures retain input");
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_tests();exhaustive();samples();random_checks();maximum();allocation_tests();rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"partialRows\":"<<partial_rows<<",\"literalFullAssignmentPairs\":"<<literal_pairs<<",\"exhaustiveCompletionRevealPairs\":"<<exhaustive_pairs<<",\"primarySamples\":"<<source_samples<<",\"consistentObservationClueGroups\":"<<consistent_groups<<",\"originalDomainGroups\":"<<source_groups<<",\"zeroRunExtensionGroups\":"<<zero_groups<<",\"contradictoryObservationClueCases\":"<<contradictions<<",\"adapterCalls\":"<<adapter_calls<<",\"randomInputs\":"<<random_cases<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCalls\":"<<invalid_calls<<",\"allocationFaults\":"<<faults<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
    bool comma=false;for(const auto& c:maxima){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<c.name<<"\",\"n\":"<<c.n<<",\"k\":"<<c.k<<",\"exists\":"<<(c.exists?"true":"false")<<",\"coreSeconds\":"<<c.seconds<<'}';}std::cout<<"]}\n";
}catch(const std::exception& e){fail_alloc::countdown=-1;std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/fixed-run-row-prefix-suffix-feasibility-forced-colors.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    assert '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-paint-cpp-') as directory:
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
