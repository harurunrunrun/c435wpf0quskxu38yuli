#!/usr/bin/env python3
"""Exhaustive degree-feasible connector counts -> Euler circuit -> physical order.

No cut-balance formula, component contraction, DSU, or MST is used by this oracle.
Every physical ordering supplies <=N+1 monotone connectors through each boundary,
so the finite count cap N+1 includes an optimum. Search prunes only an already
completed vertex's direct outdegree-minus-indegree equation.
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
article = Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/directed-line-balance-euler-augmentation-mst.mdx'
cpp = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
assert len(cpp) == 1
cpp_sha = hashlib.sha256(cpp[0].encode()).hexdigest()
assert cpp_sha == '0f96903e638b431fec50f4261e87e6b30738a0a5ccb741757fbd2a90baae9529'
tests = r'''
#include <array>
#include <chrono>
#include <iostream>
#include <numeric>
#include <random>
using I=std::int64_t;
using U=std::uint64_t;
using Sections=std::vector<std::pair<int,int>>;
U checks=0,profiles3=0,profiles4=0,random_profiles=0,enumeration_states=0,balanced=0,connected_flows=0,api_calls=0,euler_witnesses=0,euler_edges=0,physical_sections=0,checksum=0;
void need(bool ok,const char* why){++checks;if(!ok){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void mix(U x){checksum=checksum*1000003+x;}
struct Counts{std::array<int,3> up{},down{};};
struct Oracle {
    Sections source;
    int m,n,cap;
    std::array<int,4> delta{};
    std::array<unsigned,4> base_neighbors{};
    unsigned active=0;
    Counts current;
    std::array<Counts,4> optimum;
    std::array<I,4> best;
    std::array<std::vector<int>,4> coordinate;
    Oracle(const Sections& input,int count):source(input),m(count),n(int(input.size())),cap(n+1){
        if(m==3)coordinate={std::vector<int>{1,2,3},std::vector<int>{1,2,1000000000},std::vector<int>{1,999999999,1000000000},std::vector<int>{1,400000000,600000001}};
        else coordinate={std::vector<int>{1,2,3,4},std::vector<int>{1,2,3,1000000000},std::vector<int>{1,2,999999999,1000000000},std::vector<int>{1,400000000,600000000,1000000000}};
        best.fill(I{1}<<60);
        auto required=[&](int a,int b){++delta[a];--delta[b];base_neighbors[a]|=1U<<b;base_neighbors[b]|=1U<<a;active|=(1U<<a)|(1U<<b);};
        for(auto [a,b]:source)required(a,b);
        required(m-1,0); // A legal U->1 auxiliary, U may exceed actual endpoints.
    }
    bool connected()const{
        auto adjacency=base_neighbors;unsigned nonzero=active;
        for(int j=0;j<m-1;++j)if(current.up[j]||current.down[j]){adjacency[j]|=1U<<(j+1);adjacency[j+1]|=1U<<j;nonzero|=(1U<<j)|(1U<<(j+1));}
        unsigned seen=1,frontier=1;
        while(frontier){unsigned next=0;for(int j=0;j<m;++j)if(frontier>>j&1)next|=adjacency[j];next&=~seen;seen|=next;frontier=next;}
        return (seen&nonzero)==nonzero;
    }
    void search(int vertex){
        if(vertex==m-1){
            if(delta[vertex])return;
            ++balanced;
            if(!connected())return;
            ++connected_flows;
            for(int variant=0;variant<4;++variant){
                I cost=0;
                for(int j=0;j<m-1;++j)cost+=I(current.down[j])*(coordinate[variant][j+1]-coordinate[variant][j]);
                if(cost<best[variant]){best[variant]=cost;optimum[variant]=current;}
            }
            return;
        }
        for(int up=0;up<=cap;++up)for(int down=0;down<=cap;++down){
            ++enumeration_states;
            delta[vertex]+=up-down;delta[vertex+1]+=down-up;
            if(delta[vertex]==0){current.up[vertex]=up;current.down[vertex]=down;search(vertex+1);}
            delta[vertex]-=up-down;delta[vertex+1]-=down-up;
        }
    }
    void construct(int variant){
        struct Edge{int from,to,section;};std::vector<Edge> edges;std::vector<std::vector<int>> outgoing(m);
        std::array<int,4> incoming{},outdegree{};
        auto add=[&](int a,int b,int id){outgoing[a].push_back(int(edges.size()));edges.push_back({a,b,id});++incoming[b];++outdegree[a];};
        for(int id=0;id<n;++id)add(source[id].first,source[id].second,id);
        add(m-1,0,n);
        for(int j=0;j<m-1;++j){for(int k=0;k<optimum[variant].up[j];++k)add(j,j+1,-1);for(int k=0;k<optimum[variant].down[j];++k)add(j+1,j,-1);}
        need(incoming==outdegree,"every constructed vertex balanced directly");
        std::vector<int> vertices{0},arrival{-1},circuit;
        std::array<std::size_t,4> next{};
        while(!vertices.empty()){
            int v=vertices.back();
            if(next[v]<outgoing[v].size()){
                int edge=outgoing[v][next[v]++];vertices.push_back(edges[edge].to);arrival.push_back(edge);
            }else{
                if(arrival.back()!=-1)circuit.push_back(arrival.back());
                vertices.pop_back();arrival.pop_back();
            }
        }
        std::reverse(circuit.begin(),circuit.end());need(circuit.size()==edges.size(),"Hierholzer consumes every connector and required arc");
        int at=0,aux=-1;I expanded_cost=0;std::vector<bool> used(edges.size());
        for(int i=0;i<int(circuit.size());++i){
            int id=circuit[i];need(!used[id],"each Euler edge once");used[id]=true;const auto e=edges[id];
            need(e.from==at,"Euler arc incidence");at=e.to;
            if(e.section==n){need(aux==-1,"exactly one auxiliary");aux=i;}
            if(e.section==-1)expanded_cost+=std::max(0,coordinate[variant][e.from]-coordinate[variant][e.to]);
        }
        need(at==0&&aux>=0,"Euler circuit closes and contains auxiliary");need(expanded_cost==best[variant],"expanded connector distance equals enumerated optimum");
        Sections mapped;for(auto [a,b]:source)mapped.emplace_back(coordinate[variant][a],coordinate[variant][b]);
        I physical_cost=0;int speed=1;std::vector<bool> section_used(n);int selected=0;
        for(int offset=1;offset<int(circuit.size());++offset){
            const auto e=edges[circuit[(aux+offset)%circuit.size()]];
            if(e.section<0)continue;
            need(e.section<n&&!section_used[e.section],"cut after auxiliary gives each original section once");section_used[e.section]=true;++selected;
            auto [entry,exit]=mapped[e.section];const int length=std::max(0,speed-entry);physical_cost+=length;speed-=length;
            need(speed>=1&&speed<=entry,"compressed order respects entry limit and strictly positive real speed");speed=exit;
        }
        need(selected==n,"all source sections restored to physical order");need(physical_cost==best[variant],"Euler-to-physical compression attains the minimum,without virtual acceleration");
        const I published=minimum_section_connection_length(mapped);++api_calls;need(published==best[variant],"actual fence equals enumerated degree/connected-flow optimum");
        mix(U(published));++euler_witnesses;euler_edges+=edges.size();physical_sections+=n;
    }
    void run(){search(0);for(int i=0;i<4;++i){need(best[i]<(I{1}<<60),"bounded connector enumeration has a feasible circuit");construct(i);}}
};
void enumerate(Sections& a,int m,int last,int max_n){
    if(a.size()>=2){Oracle(a,m).run();if(m==3)++profiles3;else ++profiles4;}
    if(int(a.size())==max_n)return;
    for(int type=last;type<m*m;++type){a.emplace_back(type/m,type%m);enumerate(a,m,type,max_n);a.pop_back();}
}
int main(){
    auto start=std::chrono::steady_clock::now();
    Sections a;enumerate(a,3,0,7);enumerate(a,4,0,4);
    std::mt19937 rng(2016081402);
    for(int i=0;i<512;++i){
        int n=5+int(rng()%6);Sections b(n);for(auto&[x,y]:b){x=int(rng()%4);y=int(rng()%4);}
        Oracle(b,4).run();++random_profiles;
    }
    // The quotient graph is a triangle here: the outer endpoints are joined by
    // required arcs while two self-loop components need two of three gaps.
    Oracle triangle({{0,3},{1,1},{2,2}},4);triangle.run();
    need(profiles3==11430&&profiles4==4828,"complete multiset enumeration cardinalities");
    std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"allThreeSpeedMultisetsN2to7\":"<<profiles3
             <<",\"allFourSpeedMultisetsN2to4\":"<<profiles4<<",\"randomFourSpeedMultisetsN5to10\":"<<random_profiles
             <<",\"connectorCountSearchStates\":"<<enumeration_states<<",\"balancedConnectorConfigurations\":"<<balanced<<",\"connectedBalancedConfigurations\":"<<connected_flows
             <<",\"constructedEulerWitnesses\":"<<euler_witnesses<<",\"constructedEulerEdges\":"<<euler_edges<<",\"restoredPhysicalSections\":"<<physical_sections
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-railroad-independent-') as tmp:
    source = Path(tmp) / 'probe.cpp'
    binary = Path(tmp) / 'probe'
    source.write_text(cpp[0] + '\n' + tests)
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
    env = dict(os.environ)
    if args.sanitize:
        flags = ['-std=c++20', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                 '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
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
    result.update(cppSha256=cpp_sha, sanitized=args.sanitize,
                  peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)', run.stderr)[1]))
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output, end='')
