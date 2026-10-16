#!/usr/bin/env python3
"""Extract the actual visible fence; use literal transformed string sets as the oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ORACLE = r'''
#include <array>
#include <chrono>
#include <climits>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <set>
#include <sys/resource.h>
using P=std::vector<int>;
std::uint64_t checks=0,api_calls=0,checksum=0,writes=0,reads=0,compiles=0,characters=0;
void require(bool good,const char*message){++checks;if(!good)throw std::runtime_error(message);}
void record(std::uint64_t value){checksum=checksum*1000003ULL+value;}
struct Oracle{
    P p;int w,r,written=0,asked=0,compiled=0;std::set<std::string> before,after;std::string transcript;
    Oracle(P permutation,int max_w,int max_r):p(std::move(permutation)),w(max_w),r(max_r){
        P sorted=p;std::sort(sorted.begin(),sorted.end());for(std::size_t i=0;i<sorted.size();++i)if(sorted[i]!=int(i))throw std::invalid_argument("hidden permutation");
    }
    void format(const std::string&x){require(x.size()==p.size(),"all callback string lengths");for(char ch:x)require(ch=='0'||ch=='1',"all callback strings binary");characters+=x.size();}
    void add(const std::string&x){if(compiled||written>=w)throw std::runtime_error("illegal write phase/budget");format(x);++written;++writes;before.insert(x);}
    void compile(){if(compiled)throw std::runtime_error("compile exactly once");++compiled;++compiles;
        for(const auto&x:before){std::string y(x.size(),'0');for(std::size_t i=0;i<p.size();++i)y[i]=x[p[i]];after.insert(y);}
        require(before.size()==after.size(),"literal permutation preserves set size");
    }
    bool check(const std::string&x){if(compiled!=1||asked>=r)throw std::runtime_error("illegal read phase/budget");format(x);++asked;++reads;bool yes=after.contains(x);transcript+=yes?'1':'0';return yes;}
};
P run(Oracle&o){++api_calls;auto answer=partition_membership::restore(int(o.p.size()),o.w,o.r,[&](const std::string&x){o.add(x);},[&]{o.compile();},[&](const std::string&x){return o.check(x);});
    require(answer==o.p,"literal output bit i equals old bit p[i],not inverse");auto need=partition_membership::required_budget(int(o.p.size()));require(o.written==need.writes&&o.asked==need.reads&&o.compiled==1,"exact fixed call counts and phases");require(o.before.size()==std::size_t(need.writes),"no accidental duplicate write signatures");for(int x:answer)record(x);return answer;}
P identity(int n){P p(n);std::iota(p.begin(),p.end(),0);return p;}
'''
CORE = r'''
std::uint64_t permutations=0,transcript_cases=0,compatible_transcripts=0,invalid_calls=0,oracle_guards=0,callback_failures=0,nested_calls=0,random_cases=0,source_cases=0,extension_cases=0;
void all_permutations(){
    for(int n:{1,2,4,8}){P p=identity(n);std::set<std::string> transcripts;do{const auto need=partition_membership::required_budget(n);Oracle o(p,n==8?256:need.writes,n==8?256:need.reads);run(o);require(transcripts.insert(o.transcript).second,"every small hidden permutation has a distinct complete transcript");++permutations;}while(std::next_permutation(p.begin(),p.end()));
        require(transcripts.size()==(n==1?1U:n==2?2U:n==4?24U:40320U),"all small permutations/transcripts counted");
    }
}
void every_transcript(){
    for(int n:{1,2,4}){const auto need=partition_membership::required_budget(n);for(unsigned bits=0;bits<(1U<<need.reads);++bits){++transcript_cases;bool compiled=false,failed=false;int used=0;std::vector<std::string> added;std::vector<std::pair<std::string,bool>> observed;P answer;
        ++api_calls;try{answer=partition_membership::restore(n,need.writes,need.reads,[&](const std::string&x){require(!compiled,"script writes only before compile");added.push_back(x);},[&]{require(!compiled,"script single compile");compiled=true;},[&](const std::string&x){require(compiled&&used<need.reads,"script reads after compile within budget");bool value=bits>>used&1U;++used;observed.push_back({x,value});return value;});}catch(const std::runtime_error&){failed=true;}
        int compatible=0;P witness,p=identity(n);do{std::set<std::string> contents;for(const auto&x:added){std::string y(n,'0');for(int i=0;i<n;++i)y[i]=x[p[i]];contents.insert(y);}bool fits=true;for(const auto&[x,value]:observed)if(contents.contains(x)!=value)fits=false;if(fits){++compatible;witness=p;}}while(std::next_permutation(p.begin(),p.end()));
        require(compiled,"all scripts reach compile once");require(compatible<=1,"every accepted complete or rejected partial transcript has at most one compatible permutation");require(failed==(compatible==0),"inconsistent scripts rejected,all compatible scripts accepted");if(!failed){require(answer==witness&&used==need.reads,"literal compatible-transcript answer");++compatible_transcripts;}record(compatible);
    }}
}
template<class F>void invalid(F f){++invalid_calls;bool caught=false;try{f();}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid argument before callbacks");}
struct VoidAdd{void operator()(const std::string&){};};struct VoidCompile{void operator()(){};};struct BoolCheck{bool operator()(const std::string&){return true;}};struct IntCheck{int operator()(const std::string&){return 1;}};
template<class T>concept SupportedCheck=requires(T x){partition_membership::restore(1,0,0,VoidAdd{},VoidCompile{},x);};
static_assert(SupportedCheck<BoolCheck> && !SupportedCheck<IntCheck>);
void api_tests(){
    int calls=0;auto add=[&](const std::string&){++calls;};auto compile=[&]{++calls;};auto check=[&](const std::string&){++calls;return false;};
    for(int n:{INT_MIN,-1,0,3,5,127,129,256,INT_MAX}){invalid([&]{++api_calls;partition_membership::restore(n,INT_MAX,INT_MAX,add,compile,check);});require(calls==0,"invalid length has zero external calls");}
    for(int n:{1,2,4,8,16,32,64,128}){auto need=partition_membership::required_budget(n);for(const auto [w,r]:std::vector<std::pair<int,int>>{{-1,need.reads},{need.writes,-1}}){invalid([&]{++api_calls;partition_membership::restore(n,w,r,add,compile,check);});require(calls==0,"negative budget has zero callbacks");}
        if(n>1){invalid([&]{++api_calls;partition_membership::restore(n,need.writes-1,INT_MAX,add,compile,check);});invalid([&]{++api_calls;partition_membership::restore(n,INT_MAX,need.reads-1,add,compile,check);});require(calls==0,"insufficient fixed-method budget has zero callbacks");}
        Oracle o(identity(n),need.writes,need.reads);run(o);if(n!=8&&n!=32&&n!=128)++extension_cases;
    }
    Oracle one({0},0,0);run(one);require(one.written==0&&one.asked==0&&one.compiled==1,"singleton still compiles exactly once");
    Oracle huge(identity(128),INT_MAX,INT_MAX);run(huge);
    auto illegal=[&](auto action){++oracle_guards;bool caught=false;try{action();}catch(const std::runtime_error&){caught=true;}require(caught,"literal simulator detects illegal phase or budget");};
    Oracle a({1,0},1,1);illegal([&]{a.check("01");});a.add("01");illegal([&]{a.add("10");});a.compile();illegal([&]{a.compile();});illegal([&]{a.add("01");});a.check("10");illegal([&]{a.check("10");});
    Oracle duplicates({1,0},2,2);duplicates.add("01");duplicates.add("01");duplicates.compile();require(duplicates.before.size()==1&&duplicates.check("10")&&!duplicates.check("01"),"duplicate insertion uses set semantics but consumes calls");
}
struct CallbackFailure{};
void exceptions_and_nested(){
    const P p{2,1,3,0,7,5,4,6};auto need=partition_membership::required_budget(8);
    for(const auto [phase,at]:std::vector<std::pair<int,int>>{{0,0},{0,6},{0,11},{1,0},{2,0},{2,12},{2,23}}){Oracle o(p,need.writes,need.reads);int index=0;bool caught=false;
        ++api_calls;try{partition_membership::restore(8,need.writes,need.reads,[&](const std::string&x){if(phase==0&&index++==at)throw CallbackFailure{};o.add(x);},[&]{if(phase==1)throw CallbackFailure{};o.compile();},[&](const std::string&x){if(phase==2&&index++==at)throw CallbackFailure{};return o.check(x);});}catch(const CallbackFailure&){caught=true;}
        require(caught,"callback exception propagates unchanged");++callback_failures;Oracle fresh(p,need.writes,need.reads);run(fresh);
    }
    Oracle outer(p,need.writes,need.reads);bool invoked=false;++api_calls;P answer=partition_membership::restore(8,need.writes,need.reads,[&](const std::string&x){if(!invoked){invoked=true;Oracle inner({2,0,3,1},4,8);run(inner);++nested_calls;}outer.add(x);},[&]{outer.compile();},[&](const std::string&x){return outer.check(x);});require(answer==p&&invoked,"nested independent oracle retains outer call state");
    struct MoveOnlyAdd{std::unique_ptr<int> state;Oracle* o;void operator()(const std::string&x){++*state;o->add(x);}};Oracle moved({1,3,0,2},4,8);MoveOnlyAdd callback{std::make_unique<int>(0),&moved};++api_calls;auto q=partition_membership::restore(4,4,8,std::move(callback),[&]{moved.compile();},[&](const std::string&x){return moved.check(x);});require(q==moved.p&&*callback.state==4,"move-only callback is invoked by reference without hidden copies");
}
struct Maximum{int n,w,r,writes,reads;double seconds;};std::vector<Maximum> maxima;
void source_and_random(){
    std::mt19937_64 rng(20160816);
    for(const auto [n,w,r]:std::vector<std::array<int,3>>{{8,256,256},{32,320,1024},{32,1024,320},{128,1792,1792},{128,896,896}}){
        for(int mode=0;mode<6;++mode){P p=identity(n);if(mode==1)std::reverse(p.begin(),p.end());if(mode==2)std::rotate(p.begin(),p.begin()+1,p.end());if(mode==3)for(int i=0;i<n;i+=2)std::swap(p[i],p[i+1]);if(mode==4){int h=int(std::bit_width(unsigned(n)))-1;for(int i=0;i<n;++i){int x=i,y=0;for(int j=0;j<h;++j){y=2*y+(x&1);x>>=1;}p[i]=y;}}if(mode==5)std::shuffle(p.begin(),p.end(),rng);
            // The first scored subtask permits only identity or one transposition.
            if(n==8&&mode!=0){p=identity(n);std::swap(p[mode-1],p[mode]);}
            Oracle o(p,w,r);auto start=std::chrono::steady_clock::now();run(o);double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();maxima.push_back({n,w,r,o.written,o.asked,elapsed});++source_cases;
        }
        for(int trial=0;trial<160;++trial){P p=identity(n);if(n==8){int a=int(rng()%n),b=int(rng()%n);std::swap(p[a],p[b]);}else std::shuffle(p.begin(),p.end(),rng);Oracle o(p,w,r);run(o);++random_cases;++source_cases;}
    }
    for(int n:{16,64})for(int trial=0;trial<100;++trial){auto need=partition_membership::required_budget(n);P p=identity(n);std::shuffle(p.begin(),p.end(),rng);Oracle o(p,need.writes,need.reads);run(o);++extension_cases;++random_cases;}
    Oracle orientation({2,1,3,0},16,16);run(orientation);require(orientation.p!=P({3,1,0,2}),"non-involution example distinguishes permutation direction");
}
int main(){try{auto start=std::chrono::steady_clock::now();api_tests();all_permutations();every_transcript();exceptions_and_nested();source_and_random();rusage usage{};getrusage(RUSAGE_SELF,&usage);
std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"allSmallPermutations\":"<<permutations<<",\"allSmallReplyBitstrings\":"<<transcript_cases<<",\"compatibleCompleteTranscripts\":"<<compatible_transcripts<<",\"sourceBudgetCases\":"<<source_cases<<",\"extensionCases\":"<<extension_cases<<",\"randomCases\":"<<random_cases<<",\"invalidApiCalls\":"<<invalid_calls<<",\"oracleGuardTests\":"<<oracle_guards<<",\"callbackFailures\":"<<callback_failures<<",\"nestedCalls\":"<<nested_calls<<",\"writes\":"<<writes<<",\"compiles\":"<<compiles<<",\"reads\":"<<reads<<",\"callbackCharacters\":"<<characters<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"sourceStructuredCases\":[";
bool comma=false;for(const auto&x:maxima){if(comma)std::cout<<',';comma=true;std::cout<<"{\"n\":"<<x.n<<",\"w\":"<<x.w<<",\"r\":"<<x.r<<",\"actualWrites\":"<<x.writes<<",\"actualReads\":"<<x.reads<<",\"coreAndOracleSeconds\":"<<x.seconds<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''
ADAPTER = r'''
Oracle* active_oracle=nullptr;
#ifdef SYNTHETIC_MUTABLE_REFERENCE
void add_element(std::string&x){active_oracle->add(x);std::fill(x.begin(),x.end(),'0');}
bool check_element(std::string&x){bool value=active_oracle->check(x);std::fill(x.begin(),x.end(),'1');return value;}
#elif defined(SYNTHETIC_CONST_REFERENCE)
void add_element(const std::string&x){active_oracle->add(x);}
bool check_element(const std::string&x){return active_oracle->check(x);}
#else
void add_element(std::string x){active_oracle->add(x);}
bool check_element(std::string x){return active_oracle->check(x);}
#endif
void compile_set(){active_oracle->compile();}
static_assert(std::is_same_v<decltype(&restore_permutation),std::vector<int>(*)(int,int,int)>);
int main(){try{auto start=std::chrono::steady_clock::now();std::uint64_t cases=0;std::mt19937_64 rng(12832);
for(const auto [n,w,r]:std::vector<std::array<int,3>>{{1,0,0},{4,16,16},{8,256,256},{32,320,1024},{32,1024,320},{128,1792,1792},{128,896,896}}){
 for(int trial=0;trial<(n==4?24:16);++trial){P p=identity(n);if(n==4){for(int j=0;j<trial;++j)std::next_permutation(p.begin(),p.end());}else if(n==8){if(trial)std::swap(p[(trial-1)%n],p[trial%n]);}else std::shuffle(p.begin(),p.end(),rng);
 Oracle o(p,w,r);active_oracle=&o;++api_calls;auto answer=restore_permutation(n,w,r);require(answer==p,"synthetic header linked original-name adapter");auto need=partition_membership::required_budget(n);require(o.compiled==1&&o.written==need.writes&&o.asked==need.reads,"adapter exact call counts");for(int v:answer)record(v);++cases;
 }}
Oracle unused(identity(8),256,256);active_oracle=&unused;for(const auto [n,w,r]:std::vector<std::array<int,3>>{{0,1,1},{3,100,100},{8,11,24},{8,12,23},{8,-1,24}}){bool caught=false;++api_calls;try{restore_permutation(n,w,r);}catch(const std::invalid_argument&){caught=true;}require(caught&&unused.written==0&&unused.asked==0&&unused.compiled==0,"adapter invalid preflight has zero callbacks");}
rusage usage{};getrusage(RUSAGE_SELF,&usage);std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"validCases\":"<<cases<<",\"invalidPreflight\":5,\"writes\":"<<writes<<",\"compiles\":"<<compiles<<",\"reads\":"<<reads<<",\"callbackCharacters\":"<<characters<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/precompiled-permutation-partition-signature-membership.mdx'))
    args=parser.parse_args();article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    env=os.environ.copy()
    if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-messy-cpp-') as directory:
        directory=Path(directory)
        def execute(name,extra,adapter=False,reference=0):
            source=directory/(name+'.cpp');binary=directory/name
            source.write_text(cpp+'\n'+ORACLE+extra)
            options=flags+(['-DPARTITION_MEMBERSHIP_USE_GRADER'] if adapter else [])+(['-DSYNTHETIC_CONST_REFERENCE'] if reference==1 else ['-DSYNTHETIC_MUTABLE_REFERENCE'] if reference==2 else [])
            subprocess.run(['g++',*options,str(source),'-o',str(binary)],check=True)
            run=subprocess.run([str(binary)],check=False,text=True,capture_output=True,env=env)
            if run.returncode:raise RuntimeError(run.stderr or run.stdout or f'native exit {run.returncode}')
            return json.loads(run.stdout)
        generic=execute('generic',CORE)
        adapters=[]
        for reference in [0,1,2]:
            string_type=['std::string','const std::string&','std::string&'][reference]
            (directory/'messy.h').write_text('#pragma once\n#include <string>\n#include <vector>\nvoid add_element('+string_type+');\nvoid compile_set();\nbool check_element('+string_type+');\nstd::vector<int> restore_permutation(int,int,int);\n')
            result=execute(['adapter-value','adapter-const-ref','adapter-mutable-ref'][reference],ADAPTER,True,reference)
            adapters.append({'syntheticHeaderKind':['Notice-derived string value','const string reference','mutable string reference with argument modification'][reference],'actualOriginalHeaderRetrieved':False,**result})
    result={'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':args.sanitize,'compilerFlags':flags,'genericWithoutGraderStub':generic,'syntheticHeaderAdapters':adapters,'checks':generic['checks']+sum(x['checks'] for x in adapters),'apiCalls':generic['apiCalls']+sum(x['apiCalls'] for x in adapters)}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
