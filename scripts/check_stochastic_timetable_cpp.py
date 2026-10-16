#!/usr/bin/env python3
"""Compile the visible MDX C++20 fence; independently enumerate policies and Bernoulli worlds."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

HARNESS=r'''
#include <array>
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <random>
#include <string>
using I=std::int64_t;
using U=std::uint64_t;
using Trips=std::vector<ScheduledTrip>;
U checks=0,oracle_cases=0,policies=0,world_evaluations=0,forward_decisions=0,checksum=0;
std::size_t max_trips=0;int max_stations=0;long double maximum_absolute_error=0;
double maximum_single_call_seconds=0;
void require(bool good,const char* why){++checks;if(!good){std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);}}
double run(int n,const Trips& trips,int start,int goal,I deadline){
    const auto before=std::chrono::steady_clock::now();
    const double value=maximum_timetable_success(n,trips,start,goal,deadline);
    maximum_single_call_seconds=std::max(maximum_single_call_seconds,
        std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count());
    require(std::isfinite(value)&&value>=0&&value<=1,"probability stays finite in [0,1]");
    max_trips=std::max(max_trips,trips.size());max_stations=std::max(max_stations,n);
    checksum=checksum*1000003+std::bit_cast<U>(value);return value;
}
void near(double actual,long double expected,long double tolerance,const char* why){
    const long double error=std::fabs(static_cast<long double>(actual)-expected);
    maximum_absolute_error=std::max(maximum_absolute_error,error);require(error<=tolerance,why);
}
struct Group{int station;I departure;std::vector<int> buses;};
// An oracle policy picks no bus or ONE indexed bus at every (station,departure).
// For each complete policy, enumerate every independent run/cancel world, then
// simulate FORWARD. The decision cannot inspect untried world bits. No reverse
// event order, arrival cache, Bellman recurrence or same-time update is used.
std::pair<U,U> all_policy_worlds(int n,const Trips& trips,int start,int goal,
                               const std::vector<int>& probability_numerator){
    (void)n;++oracle_cases;const int m=int(trips.size());
    require(m<=8&&int(probability_numerator.size())==m,"bounded exhaustive oracle");
    std::map<std::pair<int,I>,std::vector<int>> by_event;
    for(int b=0;b<m;++b)by_event[{trips[b].from,trips[b].departure}].push_back(b);
    std::vector<Group> groups;
    for(const auto& [key,buses]:by_event)groups.push_back({key.first,key.second,buses});
    std::vector<U> weight(U{1}<<m,1);U denominator=1;
    for(int b=0;b<m;++b)denominator*=4;
    for(U world=0;world<weight.size();++world)for(int b=0;b<m;++b)
        weight[world]*=U((world>>b)&1?probability_numerator[b]:4-probability_numerator[b]);
    std::vector<int> choice(groups.size(),-1);U optimum=0;
    auto enumerate=[&](auto&& self,std::size_t at)->void{
        if(at<groups.size()){
            choice[at]=-1;self(self,at+1);
            for(int bus:groups[at].buses){choice[at]=bus;self(self,at+1);}return;
        }
        ++policies;U success_mass=0;
        for(U world=0;world<weight.size();++world){
            if (weight[world] == 0) continue;
            ++world_evaluations;
            int station=start;I ready=-1;bool success=false;
            for(int step=0;step<=m;++step){
                if(station==goal){success=true;break;}
                int next=-1;I next_time=std::numeric_limits<I>::max();
                for(std::size_t g=0;g<groups.size();++g)
                    if(groups[g].station==station&&groups[g].departure>ready&&groups[g].departure<next_time){next=int(g);next_time=groups[g].departure;}
                if(next<0)break;
                ++forward_decisions;ready=next_time;const int bus=choice[next];
                if(bus>=0&&((world>>bus)&1)){station=trips[bus].to;ready=trips[bus].arrival;}
            }
            if(success)success_mass+=weight[world];
        }
        optimum=std::max(optimum,success_mass);
    };enumerate(enumerate,0);return {optimum,denominator};
}
void compare(int n,const Trips& trips,const std::vector<int>& nums,I deadline=8){
    const auto [num,den]=all_policy_worlds(n,trips,0,1,nums);
    const double value=run(n,trips,0,1,deadline);
    // All oracle probabilities are dyadic with <=16 fractional bits, so these
    // small candidate values are represented exactly in binary64.
    require(value==double(num)/double(den),"reverse DP equals maximum over all deterministic state policies and all run worlds");
}
std::vector<ScheduledTrip> catalog(int n,int time_points){
    Trips out;
    for(int from=0;from<n;++from)for(int to=0;to<n;++to)if(from!=to)
        for(int s=0;s<time_points;++s)for(int e=s+1;e<time_points;++e)
            for(double p:{0.0,0.5,1.0})out.push_back({from,to,s,e,p});
    return out;
}
void exhaustive(){
    const auto two=catalog(2,3);require(two.size()==18,"all two-station trip types");
    for(int length=0;length<=3;++length){
        Trips selected;std::vector<int> nums;
        auto choose=[&](auto&& self,int remaining)->void{
            if(!remaining){compare(2,selected,nums,2);return;}
            for(const auto& trip:two){selected.push_back(trip);nums.push_back(int(trip.run_probability*4));self(self,remaining-1);selected.pop_back();nums.pop_back();}
        };choose(choose,length);
    }
    require(oracle_cases==6175,"every ordered list of at most three two-station trips, with duplicates");
    const auto three=catalog(3,4);require(three.size()==108,"all three-station trip types");
    compare(3,{}, {},3);
    for(const auto& a:three){compare(3,{a},{int(a.run_probability*4)},3);
        for(const auto& b:three)compare(3,{a,b},{int(a.run_probability*4),int(b.run_probability*4)},3);}
    require(oracle_cases==17948,"all two- and three-station schedules in the fixed exhaustive domains");
    std::mt19937_64 rng(20180419);
    for(int trial=0;trial<1500;++trial){
        const int n=2+int(rng()%4),m=1+int(rng()%6);Trips trips;std::vector<int> nums;
        for(int b=0;b<m;++b){int a=int(rng()%n),dest=int(rng()%(n-1));if(dest>=a)++dest;
            const I s=I(rng()%8),e=s+1+I(rng()%(8-s));const int p=int(rng()%5);
            trips.push_back({a,dest,s,e,double(p)/4});nums.push_back(p);}
        compare(n,trips,nums);
        const double original=run(n,trips,0,1,8);std::reverse(trips.begin(),trips.end());
        require(run(n,trips,0,1,8)==original,"reordering input trips preserves all choices and tie groups");
    }
}
void rejects(int n,const Trips& trips,int start,int goal,I deadline){
    bool threw=false;try{(void)maximum_timetable_success(n,trips,start,goal,deadline);}catch(const std::invalid_argument&){threw=true;}
    require(threw,"invalid arguments rejected before scheduling");
}
void boundaries(){
    near(run(4,{{0,1,0,900,.2},{0,2,100,500,1},{2,1,500,700,1},{2,1,501,701,.1},
        {0,3,200,400,.5},{3,1,500,800,.1},{3,0,550,650,.9},{0,1,700,900,.1}},0,1,1000),.3124L,1e-14L,"official example 1");
    near(run(2,{{0,1,0,1,.5},{0,1,0,1,.5},{0,1,1,2,.4},{0,1,1,2,.2}},0,1,2),.7L,1e-14L,"official example 2");
    require(run(3,{{0,2,0,1,1},{2,1,1,2,1}},0,1,2)==0,"arrival equal to next departure cannot transfer");
    require(run(3,{{0,2,0,1,1},{2,1,2,3,1}},0,1,3)==1,"strictly later departure can transfer");
    require(run(2,{{0,1,0,1,.5},{0,1,0,1,.5}},0,1,1)==.5,"cannot try both simultaneous independent buses");
    near(run(2,{{0,1,0,3,.5},{0,1,1,2,.6}},0,1,3),.8L,1e-14L,"failed departure preserves the later waiting choice");
    near(run(3,{{0,2,0,4,1},{0,1,1,3,.8}},0,1,4),.8L,1e-14L,"waiting can beat a certainly running dead end");
    require(run(3,{{0,1,0,1,1},{1,2,2,3,1}},0,1,3)==1,"destination is absorbing despite outgoing buses");
    require(run(3,{{0,2,0,1,1}},0,1,1)==0,"unreachable destination");
    near(run(3,{{2,0,0,1,.4}},2,0,1),.4L,1e-14L,"arbitrary start and destination labels");
    require(run(2,{{0,1,0,1,0}},0,1,1)==0,"probability zero");
    require(run(2,{{0,1,0,1,1}},0,1,1)==1,"departure zero and arrival exactly at deadline");
    require(run(1,{},0,0,0)==1,"already at destination with zero deadline and no trips");
    require(run(2,{},0,1,0)==0,"empty timetable");
    constexpr I top=1000000000000000000LL;
    require(run(2,{{0,1,top-1,top,1}},0,1,top)==1,"largest source time without arithmetic rounding");
    rejects(0,{},0,0,0);rejects(1000001,{},0,1,0);rejects(INT_MAX,{},0,1,0);
    rejects(2,{},-1,1,0);rejects(2,{},0,2,0);rejects(2,{},0,1,-1);rejects(2,{},0,1,top+1);
    rejects(2,{{0,0,0,1,.5}},0,1,1);rejects(2,{{-1,1,0,1,.5}},0,1,1);rejects(2,{{0,2,0,1,.5}},0,1,1);
    rejects(2,{{0,1,-1,1,.5}},0,1,1);rejects(2,{{0,1,1,1,.5}},0,1,1);rejects(2,{{0,1,2,1,.5}},0,1,2);
    rejects(2,{{0,1,0,2,.5}},0,1,1);rejects(2,{{0,1,LLONG_MIN,LLONG_MAX,.5}},0,1,1);
    for(double p:{-.1,1.1,std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){
        rejects(2,{{0,1,0,1,p}},0,1,1);rejects(2,{{0,1,0,1,p}},0,0,1);
    }
    rejects(2,{{0,0,0,1,.5}},0,0,1); // Validate every trip before the goal shortcut.
    Trips too_many(1000001,{0,1,0,1,1});rejects(2,too_many,0,0,1);
}
void maximum_scale(){
    constexpr int count=1000000;constexpr I deadline=1000000000000000000LL;
    {
        Trips trips;trips.reserve(count);const I base=deadline-2*I(count-1);
        for(int i=0;i<count-1;++i){const int a=i==0?0:i+1,b=i==count-2?1:i+2;
            trips.push_back({a,b,base+2*I(i),base+2*I(i)+1,i==count/2?.5:1.0});}
        trips.push_back({0,2,base,base+1,0});
        require(run(count,trips,0,1,deadline)==.5,"one million stations and trips, long causal chain and same-time alternative");
        for(int i=0;i<count-1;++i)trips[i].run_probability=.9999999999;
        const double actual=run(count,trips,0,1,deadline);
        const long double represented=static_cast<long double>(trips[0].run_probability);
        near(actual,std::pow(represented,count-1),4e-10L,"million-depth numerical error versus long-double product");
        near(actual,std::pow(1.0L-1e-10L,count-1),1e-9L,"million-depth result also matches original ten-digit decimal probability");
    }
    {
        Trips trips(count,{0,1,0,deadline,.5});trips.back().run_probability=.75;
        require(run(count,trips,0,1,deadline)==.75,"one million simultaneous alternatives still permit just one attempt");
    }
    {
        Trips trips;trips.reserve(count);const double p=.000001;
        for(int i=0;i<count;++i)trips.push_back({0,1,i,I(count)+i,p});
        near(run(2,trips,0,1,deadline),-std::expm1(I(count)*std::log1p(-static_cast<long double>(p))),4e-10L,
             "million waiting opportunities versus stable long-double complement product");
    }
}
int main(){
    const auto start=std::chrono::steady_clock::now();
    exhaustive();boundaries();maximum_scale();
    require(max_trips==1000000&&max_stations==1000000,"both original maximum dimensions executed");
    std::cout<<"{\"checks\":"<<checks<<",\"oracleCases\":"<<oracle_cases<<",\"completePolicies\":"<<policies
             <<",\"nonzeroWorldEvaluations\":"<<world_evaluations<<",\"forwardDecisions\":"<<forward_decisions
             <<",\"maximumTrips\":"<<max_trips<<",\"maximumStations\":"<<max_stations
             <<",\"sizeofTrip\":"<<sizeof(ScheduledTrip)<<",\"sizeofEvent\":"<<sizeof(timetable_detail::Event)
             <<",\"maximumAbsoluteError\":"<<static_cast<double>(maximum_absolute_error)
             <<",\"maximumSingleCallSeconds\":"<<maximum_single_call_seconds<<",\"checksum\":\""<<checksum
             <<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/stochastic-timetable-reverse-event-dp.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-timetable-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+HARNESS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'];environment['ASAN_OPTIONS']='detect_leaks=0'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    timer=Path('/usr/bin/time');command=[str(binary)]
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,check=True,text=True,capture_output=True,env=environment,timeout=180)
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
