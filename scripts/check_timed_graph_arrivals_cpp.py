#!/usr/bin/env python3
"""Compile the actual MDX fence; compare with physical events and source walks."""
from pathlib import Path
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile

HARNESS = r'''
#include <array>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <random>
#include <string>
using I = std::int64_t;
using W = ArrivalCount;
std::uint64_t checks=0, checksum=0, graph_cases=0, circle_cases=0, random_cases=0, invalid_cases=0;
std::string decimal(W x) {
    if(!x) return "0";
    std::string s; while(x) {s+=char('0'+x%10);x/=10;}
    std::reverse(s.begin(),s.end());return s;
}
void equal(W actual,W expected,const char* message) {
    if(actual!=expected) {
        std::cerr<<message<<": "<<decimal(actual)<<" != "<<decimal(expected)<<'\n';std::exit(1);
    }
    ++checks;
    auto bits=static_cast<__uint128_t>(actual);
    checksum=checksum*1000003+static_cast<std::uint64_t>(bits)+static_cast<std::uint64_t>(bits>>64);
}
template<class Action> void rejects(Action action) {
    bool caught=false;try {action();} catch(const std::invalid_argument&) {caught=true;}
    if(!caught) {std::cerr<<"missing invalid_argument\n";std::exit(1);}
    ++invalid_cases;
}
// Original coordinates: step every worker one meter each second. A tree has
// a ready-time, initialized to zero and changed only when physically harvested.
std::vector<std::vector<I>> physical(int length,int cooldown,const std::vector<I>& workers,
                                     const std::vector<I>& trees,int horizon) {
    std::vector<int> tree_at(length,-1),ready(trees.size(),0);
    for(int j=0;j<int(trees.size());++j) tree_at[trees[j]]=j;
    std::vector<std::vector<I>> count(workers.size(),std::vector<I>(horizon+1,0));
    for(int t=1;t<=horizon;++t) for(int worker=0;worker<int(workers.size());++worker) {
        count[worker][t]=count[worker][t-1];
        int j=tree_at[(workers[worker]+t)%length];
        if(j>=0 && ready[j]<=t) {++count[worker][t];ready[j]=t+cooldown;}
    }
    return count;
}
void small_circle(int length,int cooldown,const std::vector<I>& workers,const std::vector<I>& trees) {
    int horizon=3*length+2*cooldown+3;
    auto expected=physical(length,cooldown,workers,trees,horizon);
    std::vector<HarvestQuery> queries;
    for(int t=horizon;t>=0;--t) for(int v=int(workers.size())-1;v>=0;--v) queries.push_back({v,t});
    queries.push_back(queries.front());queries.push_back({0,0});
    auto actual=circular_harvest_counts(length,cooldown,workers,trees,queries);
    for(std::size_t i=0;i<queries.size();++i) equal(actual[i],expected[queries[i].worker][queries[i].time],"physical circle events");
    ++circle_cases;
}
void exhaustive_circles() {
    for(int length=2;length<=8;++length) {
        int layouts=1;for(int i=0;i<length;++i) layouts*=3;
        for(int encoded=0;encoded<layouts;++encoded) {
            int value=encoded;std::vector<I> workers,trees;
            for(int p=0;p<length;++p) {int kind=value%3;value/=3;if(kind==1) workers.push_back(p);if(kind==2) trees.push_back(p);}
            if(workers.empty()||trees.empty()) continue;
            for(int cooldown=1;cooldown<=2*length+2;++cooldown) small_circle(length,cooldown,workers,trees);
        }
    }
}
// Independent small graph oracle: follow every source, recording every event.
void small_graph(const std::vector<int>& next,const std::vector<I>& weight) {
    int n=int(next.size());constexpr int H=30;
    std::vector<TimedSource> sources;
    for(int v=0;v<n;++v) {sources.push_back({v,0});sources.push_back({v,1});}
    sources.push_back({0,0});
    std::vector<std::vector<W>> count(n,std::vector<W>(H+1,0));
    for(const auto& source:sources) {
        int v=source.vertex;I t=source.first_time;
        while(t<=H) {++count[v][t];t+=weight[v];v=next[v];}
    }
    for(auto& row:count) for(int t=1;t<=H;++t) row[t]+=row[t-1];
    std::vector<ArrivalQuery> queries;
    for(int t=H;t>=0;--t) for(int v=n-1;v>=0;--v) queries.push_back({v,t});
    queries.push_back({0,0});
    auto actual=functional_graph_arrival_counts(next,weight,sources,queries);
    for(std::size_t i=0;i<queries.size();++i) equal(actual[i],count[queries[i].vertex][queries[i].time],"individual source events");
    ++graph_cases;
}
void exhaustive_graphs() {
    for(int n=1;n<=4;++n) {
        int targets=1,weights=1;for(int i=0;i<n;++i) {targets*=n;weights*=3;}
        for(int encoded=0;encoded<targets;++encoded) {
            std::vector<int> next(n);int value=encoded;for(int& v:next) {v=value%n;value/=n;}
            for(int w=0;w<weights;++w) {
                std::vector<I> travel(n);value=w;for(I& x:travel) {x=1+value%3;value/=3;}
                small_graph(next,travel);
            }
        }
    }
}
// For large times, trace the path of each source separately until its first
// repeated vertex. Each target occurs once in its tail or once per source cycle.
std::vector<W> source_cycle_oracle(const std::vector<int>& next,const std::vector<I>& weight,
                                  const std::vector<TimedSource>& sources,const std::vector<ArrivalQuery>& queries) {
    std::vector<W> answer(queries.size(),0);
    for(const auto& source:sources) {
        std::vector<int> seen(next.size(),-1),path;std::vector<I> times;
        int v=source.vertex;I elapsed=0;
        while(seen[v]<0) {seen[v]=int(path.size());path.push_back(v);times.push_back(elapsed);elapsed+=weight[v];v=next[v];}
        int cycle_begin=seen[v];I period=elapsed-times[cycle_begin];
        for(std::size_t i=0;i<queries.size();++i) {
            int at=seen[queries[i].vertex];
            if(at<0) continue;
            I first=source.first_time+times[at];
            if(first>queries[i].time) continue;
            answer[i]+=at<cycle_begin?W(1):W((queries[i].time-first)/period+1);
        }
    }
    return answer;
}
void random_and_boundaries() {
    std::mt19937_64 rng(20200322);
    for(int trial=0;trial<2500;++trial) {
        int n=1+int(rng()%25),s=int(rng()%35);
        std::vector<int> next(n);std::vector<I> weight(n);
        for(int v=0;v<n;++v) {next[v]=int(rng()%n);weight[v]=1+I(rng()%(trial%2?2000000000:17));}
        std::vector<TimedSource> sources;for(int i=0;i<s;++i) sources.push_back({int(rng()%n),I(rng()%(trial%3?1000000000000000001ULL:90))});
        std::vector<ArrivalQuery> queries;
        for(int i=0;i<120;++i) queries.push_back({int(rng()%n),i%5==0?0:i%5==1?1000000000000000000LL:I(rng()%1000000000000000001ULL)});
        for(const auto& source:sources) {
            queries.push_back({source.vertex,source.first_time});
            if(source.first_time) queries.push_back({source.vertex,source.first_time-1});
            if(source.first_time<1000000000000000000LL) queries.push_back({source.vertex,source.first_time+1});
        }
        auto actual=functional_graph_arrival_counts(next,weight,sources,queries);
        auto expected=source_cycle_oracle(next,weight,sources,queries);
        for(std::size_t i=0;i<queries.size();++i) equal(actual[i],expected[i],"source-local cycles and large times");
        ++random_cases;
    }
    // Exact cooldown equality, multiples of a lap, wraparound, and simultaneous
    // harvests at distinct trees. Physical oracle uses no graph reduction.
    for(int c:{1,2,3,6,7,8,14,15,100}) small_circle(7,c,{1,4,6},{0,5});
    for(int c:{1,2,7,8,9,16,17,50}) small_circle(8,c,{0,2,4,6},{1,3,5,7});
    for(int trial=0;trial<1200;++trial) {
        int l=2+int(rng()%55);std::vector<I> a,b;
        for(int p=0;p<l;++p) {int type=int(rng()%3);if(type==1)a.push_back(p);if(type==2)b.push_back(p);}
        if(a.empty()||b.empty()) {--trial;continue;}
        small_circle(l,1+int(rng()%180),a,b);
    }
}
void official() {
    auto sample=[&](I l,I c,std::vector<I> a,std::vector<I> b,std::vector<HarvestQuery> q,std::vector<I> expected) {
        auto actual=circular_harvest_counts(l,c,a,b,q);
        for(std::size_t i=0;i<q.size();++i) equal(actual[i],expected[i],"official sample");
    };
    sample(7,3,{1,4,6},{0,5},{{0,7},{1,3},{2,8}},{2,1,1});
    sample(20,6,{0,4,8,12,16},{2,11,14},{{3,1932},{1,93787},{0,89},{4,98124798},{0,2684},{0,137598},{2,2},{2,8375},{3,237}},
           {146,7035,7,7359360,202,10320,0,628,18});
    sample(217,33608,{0,12,71,96,111,128,152,206},{4,34,42,67,76,81,85,104,110,117,122,148,166,170,212},
           {{1,223544052420046341},{2,86357593875941375},{3,892813012303440034},{0,517156961659770735},
            {6,415536186438473633},{5,322175014520330760},{6,557706040951533058},{5,640041274241532527},
            {4,286263974600593111},{7,349405886653104871},{0,987277313830536091},{4,989137777159975413},
            {1,50689028127994215},{6,445686748471896881}},
           {33230868503053,3,5,1,123542793648997,8,165811220737767,8,7,1,1,7,7535161012043,132506837660717});
}
void maximum_cases() {
    constexpr int N=200000;constexpr I T=1000000000000000000LL,WGT=2000000000;
    std::mt19937_64 rng(1000000000);
    std::vector<ArrivalQuery> q;for(int i=0;i<N;++i) q.push_back({0,i%3==0?0:i%3==1?T:I(rng()%1000000000000000001ULL)});
    auto a=functional_graph_arrival_counts({0},{1},std::vector<TimedSource>(N,{0,0}),q);
    for(int i=0;i<N;++i) equal(a[i],W(N)*(q[i].time+1),"maximum duplicate sources and wide answer");
    std::vector<int> next(N);std::vector<I> weight(N,WGT);std::vector<TimedSource> sources;
    for(int v=0;v<N;++v) {next[v]=std::min(v+1,N-1);sources.push_back({v,0});q[v].vertex=v;}
    a=functional_graph_arrival_counts(next,weight,sources,q);
    for(int i=0;i<N;++i) {
        I k=q[i].time/WGT;
        if(i<N-1) equal(a[i],std::min<I>(i+1,k+1),"maximum long tail and depth");
        else {I count=std::min<I>(N,k+1);equal(a[i],W(count)*(k+1)-W(count)*(count-1)/2,"tail enters self loop");}
    }
    for(int v=0;v<N;++v) next[v]=(v+1)%N;
    a=functional_graph_arrival_counts(next,weight,sources,q);
    for(int i=0;i<N;++i) equal(a[i],q[i].time/WGT+1,"maximum single weighted cycle");
    for(int v=0;v<N;++v) {next[v]=v;weight[v]=1+I(rng()%2000000000);sources[v].first_time=I(rng()%1000000000000000001ULL);}
    a=functional_graph_arrival_counts(next,weight,sources,q);
    for(int i=0;i<N;++i) equal(a[i],q[i].time<sources[i].first_time?0:(q[i].time-sources[i].first_time)/weight[i]+1,"maximum components and source activation");
    std::vector<I> workers,trees;std::vector<HarvestQuery> hq;
    for(int i=0;i<N;++i) {workers.push_back(2*i);trees.push_back(2*i+1);hq.push_back({i,q[i].time});}
    auto harvest=circular_harvest_counts(2*N,1,workers,trees,hq);
    for(int i=0;i<N;++i) equal(harvest[i],(hq[i].time+1)/2,"maximum alternating circle");
    harvest=circular_harvest_counts(2*N,1000000000,workers,trees,hq);
    for(int i=0;i<N;++i) equal(harvest[i],hq[i].time?((hq[i].time-1)/1000000000+1):0,"cooldown includes 2500 complete laps");
    for(int i=0;i<N;++i) {workers[i]=i;trees[i]=N+i;}
    harvest=circular_harvest_counts(1000000000,1,workers,trees,hq);
    for(int i=0;i<N;++i) equal(harvest[i],W(N)*(hq[i].time/1000000000)+std::clamp<I>(hq[i].time%1000000000-(N-i)+1,0,N),"large circle unequal arrival gaps");
    workers={0};for(int i=0;i<N;++i) {trees[i]=i+1;hq[i].worker=0;}
    harvest=circular_harvest_counts(1000000000,999999999,workers,trees,hq);
    for(int i=0;i<N;++i) equal(harvest[i],W(N)*(hq[i].time/1000000000)+std::min<I>(N,hq[i].time%1000000000),"one worker and near-lap cooldown");
}
void invalid_inputs() {
    const I LOW=std::numeric_limits<I>::min(),HIGH=std::numeric_limits<I>::max(),BIG=1000000000000000001LL;
    rejects([&]{functional_graph_arrival_counts({}, {}, {}, {});});
    rejects([&]{functional_graph_arrival_counts({0}, {}, {}, {});});
    rejects([&]{functional_graph_arrival_counts(std::vector<int>(200001,0),std::vector<I>(200001,1),{},{});});
    for(int endpoint:{-1,1,std::numeric_limits<int>::max()}) rejects([&]{functional_graph_arrival_counts({endpoint},{1},{},{});});
    for(I w:std::array<I,5>{0,-1,2000000001,LOW,HIGH}) rejects([&]{functional_graph_arrival_counts({0},{w},{},{});});
    for(TimedSource s:std::vector<TimedSource>{{-1,0},{1,0},{0,-1},{0,BIG},{0,LOW},{0,HIGH}})
        rejects([&]{functional_graph_arrival_counts({0},{1},{s},{});});
    for(ArrivalQuery q:std::vector<ArrivalQuery>{{-1,0},{1,0},{0,-1},{0,BIG},{0,LOW},{0,HIGH}})
        rejects([&]{functional_graph_arrival_counts({0},{1},{},{q});});
    rejects([&]{functional_graph_arrival_counts({0},{1},std::vector<TimedSource>(200001,{0,0}),{});});
    rejects([&]{functional_graph_arrival_counts({0},{1},{},std::vector<ArrivalQuery>(200001,{0,0}));});
    for(I l:std::array<I,6>{0,-1,1,1000000001,LOW,HIGH}) rejects([&]{circular_harvest_counts(l,1,{0},{1},{});});
    for(I c:std::array<I,5>{0,-1,1000000001,LOW,HIGH}) rejects([&]{circular_harvest_counts(2,c,{0},{1},{});});
    rejects([&]{circular_harvest_counts(3,1,{}, {1},{});});
    rejects([&]{circular_harvest_counts(3,1,{0}, {},{});});
    for(const auto& positions:std::vector<std::vector<I>>{{-1},{3},{1,0},{0,0},{LOW},{HIGH}}) {
        rejects([&]{circular_harvest_counts(3,1,positions,{2},{});});
        rejects([&]{circular_harvest_counts(3,1,{2},positions,{});});
    }
    rejects([&]{circular_harvest_counts(3,1,{1},{1},{});});
    rejects([&]{circular_harvest_counts(1000000000,1,std::vector<I>(200001,0),{2},{});});
    rejects([&]{circular_harvest_counts(1000000000,1,{0},std::vector<I>(200001,1),{});});
    rejects([&]{circular_harvest_counts(3,1,{0},{1},std::vector<HarvestQuery>(200001,{0,0}));});
    for(HarvestQuery q:std::vector<HarvestQuery>{{-1,0},{1,0},{0,-1},{0,BIG},{0,LOW},{0,HIGH}})
        rejects([&]{circular_harvest_counts(3,1,{0},{1},{q});});
    equal(functional_graph_arrival_counts({0},{1},{},{{0,100}})[0],0,"empty source list");
    equal(functional_graph_arrival_counts({0},{1},{{0,0}},{}).size(),0,"empty generic queries");
    equal(circular_harvest_counts(2,1,{0},{1},{}).size(),0,"empty harvest queries");
}
int main() {
    auto started=std::chrono::steady_clock::now();
    official();exhaustive_graphs();exhaustive_circles();random_and_boundaries();maximum_cases();invalid_inputs();
    double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::cout<<"{\"checks\":"<<checks<<",\"graphCases\":"<<graph_cases<<",\"circleCases\":"<<circle_cases
             <<",\"randomCases\":"<<random_cases<<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum
             <<"\",\"seconds\":"<<seconds<<"}\n";
}
'''

args = [arg for arg in sys.argv[1:] if arg != '--sanitize']
article = Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/functional-graph-timed-arrivals-offline.mdx'
blocks = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
if len(blocks) != 1:
    raise RuntimeError('expected one complete visible C++ fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-harvest-') as directory:
    source, executable = Path(directory)/'check.cpp', Path(directory)/'check'
    source.write_text(blocks[0] + '\n' + HARNESS)
    sanitized = '--sanitize' in sys.argv
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
    environment = os.environ.copy()
    if sanitized:
        flags += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS'] = 'detect_leaks=0'
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler, *flags, str(source), '-o', str(executable)], check=True, timeout=120)
    timer = Path('/usr/bin/time')
    command = [str(timer), '-f', 'peak_rss_kib=%M', str(executable)] if timer.exists() and sys.platform.startswith('linux') else [str(executable)]
    result = subprocess.run(command, check=True, text=True, capture_output=True, env=environment, timeout=180)
    report = json.loads(result.stdout)
    report.update(article=str(article), sanitized=sanitized)
    match = re.search(r'^peak_rss_kib=(\d+)$', result.stderr, re.M)
    if match:
        report['peakRSSKiB'] = int(match[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
