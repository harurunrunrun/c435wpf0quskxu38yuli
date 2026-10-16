#!/usr/bin/env python3
"""Extract the public C++20 fence and compare it with independent prefix oracles."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,time
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/unique-first-symbol-prefix-oracle-multiplexing.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one always-visible complete C++20 fence')
TESTS=r'''
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <numeric>
#include <random>
#include <utility>
#include <vector>
using Symbols=std::array<char,4>;
const Symbols base={'A','B','X','Y'};
std::uint64_t checks=0,checksum=0,small_cases=0,renamed_cases=0,binary_cases=0;
std::uint64_t adaptive_nodes=0,adaptive_leaves=0,adaptive_partitions=0;
std::uint64_t maximum_cases=0,total_queries=0,total_query_chars=0,invalid_cases=0;
void require(bool good,const char* message) {
    ++checks;if(!good){std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}
}
void absorb(std::uint64_t x){checksum=checksum*1000003+x+1;}
// Deliberately literal: enumerate all secret prefix lengths and use substring search.
// No first-symbol observation or block-decision formula is used by this oracle.
int literal(const std::string& secret,const std::string& query) {
    int answer=0;
    for(int len=1;len<=int(secret.size())&&len<=int(query.size());++len)
        if(query.find(secret.substr(0,len))!=std::string::npos)answer=len;
    return answer;
}
// Independent linear oracle for long cases: match a KNOWN pattern with KMP.
// This computes the actual answer over all query positions, not a decoder branch.
struct KmpOracle {
    std::string secret;std::vector<int> failure;
    explicit KmpOracle(std::string s):secret(std::move(s)),failure(secret.size()) {
        for(int i=1,j=0;i<int(secret.size());++i){
            while(j&&secret[i]!=secret[j])j=failure[j-1];
            if(secret[i]==secret[j])++j;
            failure[i]=j;
        }
    }
    int operator()(const std::string& query) const {
        int answer=0,j=0;
        for(char symbol:query){
            while(j&&secret[j]!=symbol)j=failure[j-1];
            if(secret[j]==symbol)++j;
            answer=std::max(answer,j);
            if(j==int(secret.size()))return j;
        }
        return answer;
    }
};
struct Stats {int calls=0;std::uint64_t chars=0;std::size_t longest=0;};
void check_query(const std::string& query,int n,Symbols alphabet,Stats& stats) {
    ++stats.calls;stats.chars+=query.size();stats.longest=std::max(stats.longest,query.size());
    require(!query.empty(),"no empty query");
    require(query.size()<=std::size_t(4*n),"source length budget");
    require(stats.calls<=n+2&&stats.calls<=8000,"full score and hard query budgets");
    require(std::all_of(query.begin(),query.end(),[&](char c){
        return std::find(alphabet.begin(),alphabet.end(),c)!=alphabet.end();
    }),"query alphabet");
}
template<class Oracle>
Stats verify(const std::string& secret,Symbols alphabet,Oracle&& oracle) {
    const int n=int(secret.size());Stats stats;
    require(n>=1&&n<=2000,"test secret length");
    require(std::count(secret.begin(),secret.end(),secret[0])==1,"test secret contract");
    auto callback=[&](const std::string& q)->int {check_query(q,n,alphabet,stats);return oracle(q);};
    auto got=recover_unique_initial_sequence(n,callback,alphabet);
    require(got==secret,"reconstruction equals independently hidden sequence");
    const std::uint64_t bound=n==1?3:2ULL*n*n+3*n-7;
    require(stats.chars<=bound,"total query character formula");
    require(n==1?stats.calls==2:(stats.calls==n+1||stats.calls==n+2),"exact possible query counts");
    require(stats.longest==std::size_t(n>=3?4*n-1:2),"maximum query length formula");
    total_queries+=stats.calls;total_query_chars+=stats.chars;
    absorb(stats.calls);absorb(stats.chars);
    for(unsigned char c:got)absorb(c);
    return stats;
}
std::vector<std::string> all_legal(int n,Symbols alphabet=base) {
    std::vector<std::string> out;
    auto generate=[&](auto&& self,std::string& s)->void {
        if(int(s.size())==n){out.push_back(s);return;}
        for(char c:alphabet)if(c!=s[0]){s+=c;self(self,s);s.pop_back();}
    };
    for(char first:alphabet){std::string s(1,first);generate(generate,s);}
    return out;
}
void exhaustive_small() {
    for(int n=1;n<=10;++n)for(const auto& s:all_legal(n)){
        verify(s,base,[&](const std::string& q){return literal(s,q);});++small_cases;
    }
    // Every bijection of four labels, on every legal short sequence.
    std::array<int,4> order={0,1,2,3};
    do {
        Symbols renamed{};for(int i=0;i<4;++i)renamed[i]=base[order[i]];
        for(int n=1;n<=7;++n)for(const auto& s:all_legal(n)) {
            std::string hidden;for(char c:s){auto pos=std::find(base.begin(),base.end(),c)-base.begin();hidden+=renamed[pos];}
            verify(hidden,renamed,[&](const std::string& q){return literal(hidden,q);});++renamed_cases;
        }
    } while(std::next_permutation(order.begin(),order.end()));
    const Symbols binary={'\0',static_cast<char>(0xff),static_cast<char>(0x80),' '};
    for(int n=1;n<=6;++n)for(const auto& s:all_legal(n,binary)){
        verify(s,binary,[&](const std::string& q){return literal(s,q);});++binary_cases;
    }
    // KMP is also cross-checked against direct substring search on unrelated words.
    std::mt19937 random(20180903);
    for(int iteration=0;iteration<3000;++iteration){
        std::string s(1+random()%15,'A'),q(random()%50,'A');
        for(char& c:s)c=base[random()%4];
        for(char& c:q)c=base[random()%4];
        require(KmpOracle(s)(q)==literal(s,q),"KMP oracle independently agrees with literal search");
    }
}
struct Answer {std::string query;int reply;};
struct Branch {std::string query;std::map<int,std::vector<std::string>> groups;};
// The responder may choose ANY reply that leaves at least one legal fixed secret.
// We rerun the real API along every such adaptive reply branch, retaining the pool.
void adaptive_dfs(int n,const std::vector<std::string>& candidates,std::vector<Answer>& history) {
    ++adaptive_nodes;require(!candidates.empty(),"adaptive branch consistent with a fixed secret");
    std::size_t step=0;
    try {
        auto callback=[&](const std::string& q)->int {
            require(q.size()<=std::size_t(4*n),"adaptive query length budget");
            require(step<std::size_t(n+2),"adaptive query count budget");
            if(step<history.size()){
                require(q==history[step].query,"deterministic query under replayed replies");
                return history[step++].reply;
            }
            Branch branch{q,{}};
            for(const auto& s:candidates)branch.groups[literal(s,q)].push_back(s);
            require(!branch.groups.empty(),"all attainable adaptive answers enumerated");
            adaptive_partitions+=branch.groups.size();throw branch;
        };
        auto result=recover_unique_initial_sequence(n,callback);
        require(step==history.size(),"adaptive terminal consumes recorded reply history");
        require(candidates.size()==1&&candidates[0]==result,"all surviving fixed secrets equal answer");
        ++adaptive_leaves;absorb(history.size());
    } catch(const Branch& branch) {
        for(const auto& [reply,pool]:branch.groups){
            history.push_back({branch.query,reply});adaptive_dfs(n,pool,history);history.pop_back();
        }
    }
}
void adaptive_all() {
    std::vector<Answer> history;
    for(int n=1;n<=6;++n){
        auto pool=all_legal(n);const auto before=adaptive_leaves;
        adaptive_dfs(n,pool,history);
        require(adaptive_leaves-before==pool.size(),"every legal secret occurs in adaptive response tree");
    }
}
void maximum_length() {
    std::mt19937 random(0x20180903);
    for(int n:{1999,2000})for(int first=0;first<4;++first)for(int style=0;style<4;++style){
        std::string s(1,base[first]);std::array<char,3> rest{};int k=0;
        for(char c:base)if(c!=s[0])rest[k++]=c;
        for(int i=1;i<n;++i)s+=rest[style==0?0:style==1?2:style==2?(i-1)%3:random()%3];
        KmpOracle oracle(s);auto stats=verify(s,base,oracle);++maximum_cases;
        if(style==1){
            require(stats.calls==n+2,"max query count attained");
            require(stats.chars==2ULL*n*n+3*n-7,"max total character bound attained");
            require(stats.longest==std::size_t(4*n-1),"max single query bound attained");
        }
    }
    const Symbols binary={'\0',static_cast<char>(0xfe),'Q','\n'};
    std::string s(1,binary[0]);for(int i=1;i<2000;++i)s+=binary[1+random()%3];
    KmpOracle oracle(s);verify(s,binary,oracle);++maximum_cases;
}
template<class Work> void invalid_argument_case(Work&& work,int& calls) {
    calls=0;bool caught=false;try{work();}catch(const std::invalid_argument&){caught=true;}
    require(caught&&calls==0,"invalid public argument rejected before callback");++invalid_cases;
}
void scripted_logic(int n,std::vector<int> replies) {
    std::size_t used=0;bool caught=false;
    try {
        recover_unique_initial_sequence(n,[&](const std::string&)->int {
            require(used<replies.size(),"invalid script stops at expected point");return replies[used++];
        });
    } catch(const std::logic_error&) {caught=true;}
    require(caught&&used==replies.size(),"impossible oracle reply rejected");++invalid_cases;
}
struct ReusableOracle {
    std::string secret;int calls=0;
    ReusableOracle()=default;ReusableOracle(const ReusableOracle&)=delete;
    int operator()(const std::string& query){++calls;return literal(secret,query);}
};
void invalid_and_state() {
    int called=0;auto callback=[&](const std::string&)->int{++called;return 0;};
    for(int n:{INT_MIN,-1,0,2001,INT_MAX})
        invalid_argument_case([&]{recover_unique_initial_sequence(n,callback);},called);
    for(int i=0;i<4;++i)for(int j=0;j<i;++j){
        auto symbols=base;symbols[i]=symbols[j];
        invalid_argument_case([&]{recover_unique_initial_sequence(5,callback,symbols);},called);
    }
    Symbols duplicate_null={'\0','A','\0','B'};
    invalid_argument_case([&]{recover_unique_initial_sequence(1,callback,duplicate_null);},called);
    for(int value:{INT_MIN,-1,3,INT_MAX})scripted_logic(5,{value});
    scripted_logic(1,{2});
    scripted_logic(5,{2,0});
    scripted_logic(6,{1,1,0});scripted_logic(6,{1,1,4});
    scripted_logic(2,{1,1,0});scripted_logic(2,{1,1,1,0});
    struct ExternalFailure {};
    bool caught=false;
    try{recover_unique_initial_sequence(5,[](const std::string&)->int{throw ExternalFailure{};});}
    catch(const ExternalFailure&){caught=true;}
    require(caught,"callback exception propagates unchanged");
    // No static state: reuse a noncopyable callback, including after an exception.
    ReusableOracle reusable;
    for(int iteration=0;iteration<200;++iteration){
        const int n=1+iteration%8;auto all=all_legal(n);reusable.secret=all[iteration%all.size()];reusable.calls=0;
        require(recover_unique_initial_sequence(n,reusable)==reusable.secret,"reused noncopyable callback");
        require(reusable.calls<=n+2,"call budget reset between invocations");
    }
    auto unique=std::make_unique<std::string>("ABXY");
    auto move_only=[hidden=std::move(unique)](const std::string& q)->int{return literal(*hidden,q);};
    require(recover_unique_initial_sequence(4,std::move(move_only))=="ABXY","move-only rvalue callback");
    // Outside the secret contract, the method need not work. A first-repeat word
    // yields a wrong answer or a rejected reply; do not claim the API verifies S.
    bool counterexample=false;
    for(const std::string hidden:{"AAAA","ABAB","AXBAX"}) {
        try{auto got=recover_unique_initial_sequence(int(hidden.size()),[&](const std::string& q){return literal(hidden,q);});
            counterexample|=got!=hidden;
        }catch(const std::logic_error&){counterexample=true;}
    }
    require(counterexample,"first-symbol promise is necessary for this implementation");
}
int main(){
    const auto start=std::chrono::steady_clock::now();
    exhaustive_small();adaptive_all();maximum_length();invalid_and_state();
    require(small_cases==118096,"all legal sequences length one through ten");
    require(renamed_cases==104928,"24 renamings times every legal sequence through seven");
    require(binary_cases==1456&&adaptive_leaves==1456,"binary alphabet and adaptive all-small coverage");
    std::cout<<"{\"checks\":"<<checks<<",\"smallCases\":"<<small_cases
      <<",\"renamedCases\":"<<renamed_cases<<",\"binaryCases\":"<<binary_cases
      <<",\"adaptiveNodes\":"<<adaptive_nodes<<",\"adaptiveLeaves\":"<<adaptive_leaves
      <<",\"adaptivePartitions\":"<<adaptive_partitions<<",\"maximumCases\":"<<maximum_cases
      <<",\"queries\":"<<total_queries<<",\"queryCharacters\":"<<total_query_chars
      <<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum<<"\",\"nativeSeconds\":"
      <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-combo-build-') as tmp:
    source=Path(tmp)/'test.cpp';binary=Path(tmp)/'test'
    source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-Wall','-Wextra','-Werror','-O2']
    if '--sanitize' in sys.argv:flags=['-std=c++20','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
    env=dict(os.environ)
    if '--sanitize' in sys.argv:env['ASAN_OPTIONS']='detect_leaks=0';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    result=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    if result.stderr:print(result.stderr,file=sys.stderr,end='')
    report=json.loads(result.stdout)
    report['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest()
    report['sanitized']='--sanitize' in sys.argv
    print(json.dumps(report,ensure_ascii=False))
