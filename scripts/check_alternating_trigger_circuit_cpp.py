#!/usr/bin/env python3
"""Extract the visible builder; execute its returned serial-number circuit literally."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/alternating-switch-bit-reversal-pruned-router.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one complete always-visible C++20 fence')
TESTS=r'''
#include <algorithm>
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <set>
using Circuit=AlternatingTriggerCircuit;
using U=std::uint64_t;
U checks=0,checksum=0,small_cases=0,binary_extra=0,single_lengths=0,boundary_cases=0,random_cases=0,max_cases=0;
U periods=0,outputs=0,inversions=0,all_length_budgets=0,invalid_builder_calls=0;
int largest_n=0,largest_m=0,largest_switches=0;U maximum_changes=0;
void need(bool good,const char* why){++checks;if(!good){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(U value){checksum=checksum*1000003+value+1;}
std::pair<int,U> geometric_counts(int n){
    int h=0,p=1;while(p<n+1){p*=2;++h;}
    int switches=0;U changes=0;
    for(int block=2;block<=p;block*=2){int count=(n+1+block-1)/block;switches+=count;changes+=U(block)*count;}
    return {switches,changes};
}
// No bit reversal, tree shape, pruning rule or formula is used to execute a circuit.
// Its only rules are encoded destinations and choose-current-exit, THEN toggle.
struct LiteralMachine {
    const Circuit& circuit;int m;std::vector<unsigned char> state;
    LiteralMachine(const Circuit& c,int count):circuit(c),m(count),state(c.x.size()){
        need(c.trigger_exit.size()==std::size_t(m+1)&&c.x.size()==c.y.size(),"original output array dimensions");
        auto valid=[&](int p){return p>=-int(c.x.size())&&p<=m;};
        for(int p:c.trigger_exit)need(valid(p),"every origin/trigger destination is a valid serial");
        for(int p:c.x)need(valid(p),"every X destination is a valid serial");
        for(int p:c.y)need(valid(p),"every Y destination is a valid serial");
    }
    U run(const std::vector<int>& expected){
        std::vector<int> visits(state.size());std::size_t emitted=0;U changes=0;
        int serial=circuit.trigger_exit[0];
        while(serial!=0){
            if(serial>0){
                need(emitted<expected.size()&&serial==expected[emitted],"literal output equals each requested trigger before FIRST origin return");
                ++emitted;serial=circuit.trigger_exit[serial];
            }else{
                const int index=-serial-1;
                serial=state[index]?circuit.y[index]:circuit.x[index];
                state[index]^=1;++visits[index];++changes;
                if(changes>20000000)need(false,"first origin return within hard state-change budget");
            }
        }
        need(emitted==expected.size(),"first origin return occurs after exactly N triggers");
        for(std::size_t i=0;i<state.size();++i){
            need(state[i]==0,"ALL switches return to initial X, including every allocated switch");
            need(visits[i]>=2&&visits[i]%2==0,"all retained switches visited positive even number of times");
        }
        ++periods;outputs+=emitted;inversions+=changes;maximum_changes=std::max(maximum_changes,changes);absorb(changes);
        return changes;
    }
};
void verify(int m,const std::vector<int>& sequence){
    const auto unchanged=sequence;auto c=build_alternating_trigger_circuit(m,sequence);
    need(sequence==unchanged,"builder preserves input");
    auto [switches,changes]=geometric_counts(int(sequence.size()));
    need(c.x.size()==std::size_t(switches),"constructed switch count equals independent geometric block count");
    need(c.x.size()<=400000,"hard switch count");
    const int n=int(sequence.size()),h=int(std::bit_width(static_cast<unsigned>(n)));
    need(switches<=n+h-1,"integer full-score bound N+floor(log2N)");
    for(int next:c.trigger_exit)need(next==-1,"origin and ALL triggers, including unused ones, share root-1");
    int zeros=0;for(int p:c.x)zeros+=p==0;for(int p:c.y)zeros+=p==0;
    need(zeros==1,"origin has exactly one incoming router port");
    LiteralMachine machine(c,m);
    for(int cycle=0;cycle<2;++cycle){ // continue from the actual previous final states
        U actual=machine.run(sequence);
        need(actual==changes,"actual total inversions equals geometric exact formula");
        need(actual<=U(1U<<h)*h&&actual<=20000000,"all state-change budgets");
    }
    absorb(c.x.size());for(int p:c.x)absorb(U(p+int(c.x.size())));for(int p:c.y)absorb(U(p+int(c.x.size())));
    largest_n=std::max(largest_n,n);largest_m=std::max(largest_m,m);largest_switches=std::max(largest_switches,switches);
}
void exhaustive(){
    for(int m=1;m<=4;++m)for(int n=1;n<=8;++n){
        std::vector<int> sequence(n,1);
        auto all=[&](auto&& self,int at)->void{
            if(at==n){verify(m,sequence);++small_cases;return;}
            for(int symbol=1;symbol<=m;++symbol){sequence[at]=symbol;self(self,at+1);}
        };all(all,0);
    }
    for(int n=9;n<=16;++n)for(unsigned mask=0;mask<(1U<<n);++mask){
        std::vector<int> sequence(n);for(int i=0;i<n;++i)sequence[i]=1+int(mask>>i&1);
        verify(2,sequence);++binary_extra;
    }
    need(small_cases==97738&&binary_extra==130560,"every small trigger sequence, not a sample of patterns");
}
void lengths_and_boundaries(){
    for(int n=1;n<=200000;++n){
        auto [switches,changes]=geometric_counts(n);
        int h=int(std::bit_width(static_cast<unsigned>(n))),pop=std::popcount(static_cast<unsigned>(n));
        need(switches==n-pop+h,"ALL N: independent level counts equal integer popcount identity");
        need(switches<=n+h-1&&switches<=400000,"ALL N: full score and hard switch bound");
        need(changes<=U(1U<<h)*h&&changes<=20000000,"ALL N: exact inversion count obeys both bounds");
        ++all_length_budgets;
    }
    for(int n=1;n<=2048;++n){verify(1,std::vector<int>(n,1));++single_lengths;}
    std::set<int> sizes;
    for(int power=1;power<=262144;power*=2)for(int delta=-2;delta<=2;++delta)
        if(1<=power+delta&&power+delta<=200000)sizes.insert(power+delta);
    for(int n:sizes){
        std::vector<int> sequence(n);for(int i=0;i<n;++i)sequence[i]=1+int((U(i)*971)%100000);
        verify(100000,sequence);++boundary_cases;
    }
}
void randomized_and_maximum(){
    std::mt19937 rng(20180905);
    for(int test=0;test<300;++test){
        int m=1+int(rng()%100000),n=1+int(rng()%5000);std::vector<int> sequence(n);
        for(int i=0;i<n;++i)sequence[i]=test%3==0?m:test%3==1?1+i%m:1+int(rng()%m);
        verify(m,sequence);++random_cases;
    }
    for(int style=0;style<4;++style){
        int m=style==0?1:100000;std::vector<int> sequence(200000);
        for(int i=0;i<200000;++i)sequence[i]=style==0?1:style==1?1+i%m:style==2?m-i%m:1+int(rng()%m);
        verify(m,sequence);++max_cases;
    }
    need(largest_n==200000&&largest_m==100000&&largest_switches==200012,"original maximum N/M constructed and simulated");
    need(maximum_changes==3836286,"maximum executed inversion count independently simulated");
}
void reject(int m,const std::vector<int>& sequence){
    bool caught=false;try{(void)build_alternating_trigger_circuit(m,sequence);}catch(const std::invalid_argument&){caught=true;}
    need(caught,"invalid construction API input rejected");++invalid_builder_calls;
}
void api_and_initial_state(){
    for(int m:{INT_MIN,-1,0,100001,INT_MAX})reject(m,{1});
    reject(1,{});reject(1,std::vector<int>(200001,1));
    for(int bad:{INT_MIN,-1,0,2,INT_MAX})reject(1,{1,bad,1});
    const auto first=build_alternating_trigger_circuit(4,{1,2,1,3});
    for(int round=0;round<50;++round){
        auto other=build_alternating_trigger_circuit(1,{1});need(other.x.size()==1&&other.y[0]==0,"separate fresh router");
        auto again=build_alternating_trigger_circuit(4,{1,2,1,3});
        need(first.trigger_exit==again.trigger_exit&&first.x==again.x&&first.y==again.y,"no state or numbering persists across calls");
    }
    verify(4,{1,2,1,3});verify(100000,{100000});
    // The builder has no input execution state. Demonstrate why the stated all-X
    // contract is essential: the singleton router started in Y returns to0 before1.
    auto singleton=build_alternating_trigger_circuit(1,{1});
    need(singleton.x[0]==1&&singleton.y[0]==0,"arbitrary initial Y is outside the reconstruction guarantee");
    // Ordinary copies are independent value objects, with no hidden simulator state.
    auto copy=first;copy.x[0]=0;need(first.x[0]!=copy.x[0],"returned circuit is independently owned");
}
int main(){
    auto start=std::chrono::steady_clock::now();exhaustive();lengths_and_boundaries();randomized_and_maximum();api_and_initial_state();
    std::cout<<"{\"checks\":"<<checks<<",\"smallCases\":"<<small_cases<<",\"binaryExtra\":"<<binary_extra
      <<",\"singleLengths\":"<<single_lengths<<",\"boundaryCases\":"<<boundary_cases<<",\"randomCases\":"<<random_cases
      <<",\"maximumCases\":"<<max_cases<<",\"allLengthBudgets\":"<<all_length_budgets<<",\"periods\":"<<periods
      <<",\"outputs\":"<<outputs<<",\"inversions\":"<<inversions<<",\"maximumN\":"<<largest_n
      <<",\"maximumM\":"<<largest_m<<",\"maximumSwitches\":"<<largest_switches<<",\"maximumChanges\":"<<maximum_changes
      <<",\"invalidBuilderCalls\":"<<invalid_builder_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
      <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-doll-build-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)]
    if Path('/usr/bin/time').exists():command=['/usr/bin/time','-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest(),sanitized='--sanitize' in sys.argv)
    print(json.dumps(report,ensure_ascii=False))
