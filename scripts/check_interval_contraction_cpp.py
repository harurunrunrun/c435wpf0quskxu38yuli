#!/usr/bin/env python3
"""Extract the published C++20 implementation and compare with an xy oracle.

Relocatable: pass an article path explicitly, or place beside the article.
No repository modules, build output, or downloaded data are required.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

TESTS = r'''
static uint64_t checked_cases=0,complete_sequences=0;
vector<pair<int,int>> direct(int n,vector<pair<int,int>> points,const vector<SweepEvent>& events) {
    vector<pair<int,int>> out;
    for(auto e:events) {
        if(e.kind==1) out.push_back(points.at(e.first));
        else if(e.kind==2) {
            for(auto& [x,y]:points) if(x<n-e.first && y<=e.first) x=n-e.first;
        } else if(e.kind==3) {
            for(auto& [x,y]:points) if(x<=e.first && y<n-e.first) y=n-e.first;
        } else points.emplace_back(e.first,e.second);
    }
    return out;
}
void check_case(int n,const vector<pair<int,int>>& initial,vector<SweepEvent> events) {
    int points=int(initial.size());
    for(auto e:events) points+=e.kind==4;
    for(int id=0;id<points;++id) events.push_back({1,id});
    auto expected=direct(n,initial,events);
    auto result=sweep_triangle_points(n,initial,events);
    assert(result.positions==expected);
    const auto& s=result.statistics;
    assert(s.levels_descended<=uint64_t(points)*s.tree_height);
    assert(s.point_moves<=s.levels_descended);
    assert(s.path_nodes<=uint64_t(events.size())*s.tree_height);
    ++checked_cases;
}
template<class F> void rejects(F f) {
    bool caught=false;
    try {f();} catch(const invalid_argument&) {caught=true;}
    assert(caught);
}
void exhaustive(int n,int depth,const vector<pair<int,int>>& initial,
                vector<SweepEvent>& prefix,int existing,
                const vector<pair<int,int>>& board) {
    if(depth==0) {check_case(n,initial,prefix);++complete_sequences;return;}
    for(int width=0;width<n;++width) for(int kind:{2,3}) {
        prefix.push_back({kind,width});
        exhaustive(n,depth-1,initial,prefix,existing,board);prefix.pop_back();
    }
    for(auto [x,y]:board) {
        prefix.push_back({4,x,y});
        exhaustive(n,depth-1,initial,prefix,existing+1,board);prefix.pop_back();
    }
    for(int id=0;id<existing;++id) {
        prefix.push_back({1,id});
        exhaustive(n,depth-1,initial,prefix,existing,board);prefix.pop_back();
    }
}
void small_tests() {
    for(int n=1;n<=3;++n) {
        vector<pair<int,int>> board;
        for(int x=0;x<=n;++x) for(int y=0;x+y<=n;++y) board.emplace_back(x,y);
        vector<SweepEvent> prefix;
        int depth=n==1?5:(n==2?4:3);
        exhaustive(n,depth,{},prefix,0,board);
        for(auto point:board) exhaustive(n,depth,{point},prefix,1,board);
    }
    mt19937 random(20201015);
    for(int trial=0;trial<15000;++trial) {
        int n=1+random()%18;
        auto point=[&]() {int x=random()%(n+1);return pair(x,int(random()%(n-x+1)));};
        vector<pair<int,int>> initial;
        int count=1+random()%20;
        for(int i=0;i<count;++i) initial.push_back(trial%5==0?pair(0,0):point());
        vector<SweepEvent> events;
        for(int step=0;step<100;++step) {
            int kind=1+random()%4;
            if(kind==1) events.push_back({1,int(random()%count)});
            else if(kind==4) {auto [x,y]=point();events.push_back({4,x,y});++count;}
            else events.push_back({kind,int(random()%n)});
        }
        check_case(n,initial,events);
    }
    // Every lattice point simultaneously, repeated cuts, widths 0 and N-1,
    // duplicate coordinates, and fresh points after old contractions.
    for(int n=1;n<=12;++n) {
        vector<pair<int,int>> initial;
        for(int x=0;x<=n;++x) for(int y=0;x+y<=n;++y) initial.emplace_back(x,y);
        auto duplicates=vector<pair<int,int>>(initial.begin(),initial.begin()+3);
        initial.insert(initial.end(),duplicates.begin(),duplicates.end());
        vector<SweepEvent> events;
        for(int repeat=0;repeat<4;++repeat) for(int w=0;w<n;++w) {
            events.push_back({2,w});events.push_back({2,w});
            events.push_back({3,n-1-w});events.push_back({4,0,0});
        }
        check_case(n,initial,events);
    }
    // Published sample 1 (IDs converted once to zero-based).
    vector<pair<int,int>> initial={{1,1},{4,0}};
    vector<SweepEvent> events={{4,2,3},{3,3},{1,0},{4,1,2},{2,3},{2,0},
                              {1,3},{3,2},{1,2},{1,1}};
    assert((sweep_triangle_points(6,initial,events).positions==
            vector<pair<int,int>>{{1,3},{3,2},{3,3},{6,0}}));
    check_case(1000000000,{{0,0},{1000000000,0},{0,1000000000},{500000000,500000000}},
               {{2,999999999},{3,999999999},{4,0,0},{2,0},{3,0},{1,0},{1,4}});
    check_case(1,{},{});
    rejects([]{sweep_triangle_points(0,{},{});});
    rejects([]{sweep_triangle_points(1000000001,{},{});});
    rejects([]{sweep_triangle_points(5,{{-1,0}},{});});
    rejects([]{sweep_triangle_points(5,{{INT_MAX,INT_MAX}},{});});
    rejects([]{sweep_triangle_points(5,{},{{4,0,-1}});});
    rejects([]{sweep_triangle_points(5,{},{{4,3,3}});});
    rejects([]{sweep_triangle_points(5,{},{{1,0},{4,0,0}});});
    rejects([]{sweep_triangle_points(5,{{0,0}},{{1,-1}});});
    rejects([]{sweep_triangle_points(5,{{0,0}},{{1,1}});});
    rejects([]{sweep_triangle_points(5,{},{{2,-1}});});
    rejects([]{sweep_triangle_points(5,{},{{3,5}});});
    rejects([]{sweep_triangle_points(5,{},{{0,0}});});
    rejects([]{sweep_triangle_points(5,vector<pair<int,int>>(500001,{0,0}),{});});
    rejects([]{sweep_triangle_points(5,{},vector<SweepEvent>(1000001,{2,0}));});
    rejects([]{ContractingIntervals({},0);});
    rejects([]{ContractingIntervals({0},-1);});
    rejects([]{ContractingIntervals({0},INT_MAX);});
    ContractingIntervals kernel({INT_MIN,0,INT_MAX},2);
    assert(kernel.add(INT_MIN,INT_MAX)==0);
    kernel.contract_right(0);kernel.contract_left(INT_MIN);
    assert((kernel.interval(0)==pair(INT_MIN,0)));
    rejects([&]{kernel.add(1,0);});
    rejects([&]{kernel.add(INT_MIN,1);});
    rejects([&]{kernel.contract_right(1);});
    assert(kernel.add(0,0)==1);
    rejects([&]{kernel.add(0,0);});
    rejects([&]{kernel.interval(-1);});
    rejects([&]{kernel.interval(2);});
    assert((kernel.interval(0)==pair(INT_MIN,0)));
    cout<<"PASS small: "<<complete_sequences<<" complete operation sequences, "
        <<checked_cases<<" direct-simulation comparisons, 15000 random histories.\n";
}
void maximum_population() {
    const int n=1000000000,m=500000,q=1000000;
    vector<pair<int,int>> initial;initial.reserve(m);
    for(int i=0;i<m;++i) initial.emplace_back(i,i);
    vector<SweepEvent> events;events.reserve(q);
    for(int i=0;i<q-1;++i) events.push_back({4,m+i,m+i});
    events.push_back({1,m+q-2});
    auto result=sweep_triangle_points(n,initial,events);
    assert((result.positions==vector<pair<int,int>>{{1499998,1499998}}));
    assert(result.statistics.point_moves==0);
    cout<<"PASS maximum population: N=1000000000, M=500000, Q=1000000, K=1499999, C="
        <<result.statistics.coordinate_count<<", height="<<result.statistics.tree_height<<".\n";
}
void maximum_movement() {
    const int n=1000000000,m=500000,q=1000000;
    vector<pair<int,int>> initial;initial.reserve(m);
    for(int i=0;i<m;++i) initial.emplace_back(i,i);
    vector<SweepEvent> events;events.reserve(q);
    for(int i=0;i<q-1;++i) {
        int width=(i%3==0?0:(i%3==1?n-1:int((uint64_t(i)*48271)%n)));
        events.push_back({i%2==0?2:3,width});
    }
    events.push_back({1,m-1});
    auto result=sweep_triangle_points(n,initial,events);
    vector<pair<int,int>> one={{m-1,m-1}};
    auto oracle_events=events;oracle_events.back().first=0;
    assert(result.positions==direct(n,one,oracle_events));
    const auto& s=result.statistics;
    assert(s.point_moves<=s.levels_descended);
    assert(s.levels_descended<=uint64_t(m)*s.tree_height);
    assert(s.path_nodes==uint64_t(q-1)*s.tree_height);
    cout<<"PASS maximum movement: M=500000, Q=1000000, C="<<s.coordinate_count
        <<", height="<<s.tree_height<<", moves="<<s.point_moves
        <<", descended="<<s.levels_descended<<", relabels="<<s.member_relabels
        <<", path_nodes="<<s.path_nodes<<".\n";
}
void depth_adversary() {
    const int n=1<<18,points=500000;
    vector<int> coords(n+1);iota(coords.begin(),coords.end(),0);
    ContractingIntervals intervals(move(coords),points);
    for(int id=0;id<points;++id) assert(intervals.add(0,n)==id);
    for(int p=n/2;p;p/=2) intervals.contract_right(p);
    for(int id:{0,249999,499999}) assert(intervals.interval(id)==pair(0,1));
    const auto s=intervals.statistics();
    assert(s.levels_descended<=uint64_t(points)*s.tree_height);
    assert(s.point_moves==uint64_t(points)*18);
    cout<<"PASS descending groups: moves="<<s.point_moves<<", descended="<<s.levels_descended
        <<", height="<<s.tree_height<<".\n";
}
int main(int argc,char** argv) {
    string mode=argc>1?argv[1]:"small";
    if(mode=="small") small_tests();
    else if(mode=="population") maximum_population();
    else if(mode=="movement") maximum_movement();
    else if(mode=="depth") depth_adversary();
    else assert(false);
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article', nargs='?', type=Path)
    parser.add_argument('--modes', default='small,population,movement,depth')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    candidates = [
        Path(__file__).with_name('flowchartcp-sweeping-article.mdx'),
        Path(__file__).resolve().parent.parent / 'src/content/docs/techniques/interval-stabbing-endpoint-contraction-dsu.mdx',
    ]
    article = args.article or next((p for p in candidates if p.is_file()), None)
    if article is None:
        parser.error('pass the article path explicitly')
    modes = args.modes.split(',')
    if not modes or any(m not in {'small','population','movement','depth'} for m in modes):
        parser.error('unknown test mode')
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
    if len(fences) != 1:
        raise ValueError('Expected exactly one complete published C++ fence')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-sweeping-check-') as folder:
        source = Path(folder) / 'check.cpp'
        binary = Path(folder) / 'check'
        source.write_text(fences[0] + TESTS)
        flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
        if args.sanitize:
            flags = ['-std=c++20', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                     '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run([compiler, *flags, str(source), '-o', str(binary)],
                       check=True, timeout=120)
        run_env = os.environ.copy()
        if args.sanitize:
            # LeakSanitizer cannot operate in the sandbox's ptrace environment.
            run_env['ASAN_OPTIONS'] = run_env.get('ASAN_OPTIONS', '') + ':detect_leaks=0'
        for mode in modes:
            started = time.perf_counter()
            command = [str(binary), mode]
            if Path('/usr/bin/time').is_file():
                command = ['/usr/bin/time', '-f', 'peak_rss=%M KiB', *command]
            subprocess.run(command, check=True, timeout=240, env=run_env)
            print(f'{mode}: elapsed={time.perf_counter()-started:.3f}s', flush=True)

if __name__ == '__main__':
    main()
