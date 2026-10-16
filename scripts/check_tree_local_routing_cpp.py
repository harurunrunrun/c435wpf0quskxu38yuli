#!/usr/bin/env python3
"""Compile the visible MDX fence; test BFS routes and an isolated router process."""
from pathlib import Path
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile

HARNESS = r'''
#include <chrono>
#include <climits>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <string>
std::uint64_t checks=0, tree_count=0, labelings=0, route_hops=0, invalid_cases=0, checksum=0;
void require(bool ok,const char* message) {
    if(!ok) {std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}++checks;
}
void equal(int actual,int expected,const char* message) {
    require(actual==expected,message);checksum=checksum*1000003+std::uint64_t(actual);
}
template<class Action> void rejects(Action action) {
    bool caught=false;try{action();}catch(const std::invalid_argument&){caught=true;}
    require(caught,"expected invalid_argument");++invalid_cases;
}
using Edges=std::vector<std::pair<int,int>>;
std::vector<std::vector<int>> adjacency(int n,const Edges& edges) {
    std::vector<std::vector<int>> result(n);
    for(auto [a,b]:edges){result[a].push_back(b);result[b].push_back(a);}return result;
}
// Independent oracle: BFS from every destination chooses its parent toward it.
std::vector<std::vector<int>> bfs_steps(const std::vector<std::vector<int>>& g) {
    int n=int(g.size());std::vector<std::vector<int>> step(n,std::vector<int>(n,-1));
    for(int target=0;target<n;++target) {
        std::queue<int> pending;pending.push(target);step[target][target]=target;
        while(!pending.empty()) {
            int v=pending.front();pending.pop();
            for(int child:g[v]) if(step[child][target]<0){step[child][target]=v;pending.push(child);}
        }
    }
    return step;
}
std::vector<std::vector<int>> neighbor_labels(const std::vector<std::vector<int>>& g,const std::vector<int>& labels) {
    std::vector<std::vector<int>> result(g.size());
    for(int v=0;v<int(g.size());++v){for(int child:g[v])result[v].push_back(labels[child]);std::sort(result[v].begin(),result[v].end());}
    return result;
}
void check_small(int n,const Edges& edges,int root) {
    auto g=adjacency(n,edges),step=bfs_steps(g);
    auto labels=alternating_tree_labels(n,edges,root);
    std::vector<int> sorted=labels;std::sort(sorted.begin(),sorted.end());
    for(int i=0;i<n;++i)equal(sorted[i],i,"labels are exactly 0..n-1");
    auto neighbors=neighbor_labels(g,labels);
    std::vector<int> inverse(n),mapped(n);
    for(int v=0;v<n;++v){inverse[labels[v]]=v;int x=n-1-labels[v];mapped[v]=INT_MAX-10000*x-x*x;}
    auto spaced=neighbor_labels(g,mapped);
    for(int v=0;v<n;++v) {
        rejects([&]{next_tree_label_sorted(labels[v],labels[v],neighbors[v]);});
        if(!neighbors[v].empty())require(labels[v]<neighbors[v].front()||labels[v]>neighbors[v].back(),"label is a strict local extreme");
        for(int target=0;target<n;++target)if(target!=v) {
            int wanted=step[v][target];
            equal(find_next_station(labels[v],labels[target],neighbors[v]),labels[wanted],"BFS first adjacent step");
            auto reversed=neighbors[v];std::reverse(reversed.begin(),reversed.end());
            equal(next_tree_label(labels[v],labels[target],reversed),labels[wanted],"unordered-neighbor adapter");
            equal(next_tree_label_sorted(mapped[v],mapped[target],spaced[v]),mapped[wanted],"shared nonlinear increasing remap and INT_MAX");
            int current=v,hops=0;
            while(current!=target) {
                require(hops<n,"actual routing terminates");
                int result=next_tree_label_sorted(labels[current],labels[target],neighbors[current]);
                equal(result,labels[step[current][target]],"every actual routing step follows BFS");
                current=inverse[result];++hops;++route_hops;
            }
        }
    }
    ++labelings;
}
Edges prufer_tree(int n,int code) {
    if(n==1)return {};
    std::vector<int> sequence(std::max(0,n-2)),degree(n,1);
    for(int& v:sequence){v=code%n;code/=n;++degree[v];}
    Edges result;
    for(int v:sequence){int leaf=0;while(degree[leaf]!=1)++leaf;result.push_back({leaf,v});--degree[leaf];--degree[v];}
    int a=0;while(degree[a]!=1)++a;int b=a+1;while(degree[b]!=1)++b;
    result.push_back({a,b});return result;
}
void exhaustive() {
    for(int n=1;n<=7;++n) {
        int limit=1;for(int i=0;i<n-2;++i)limit*=n;
        for(int code=0;code<limit;++code) {
            auto edges=prufer_tree(n,code);++tree_count;
            for(int root=0;root<n;++root){if(root%2)std::reverse(edges.begin(),edges.end());check_small(n,edges,root);}
        }
    }
    std::mt19937 rng(20200919);
    for(int trial=0;trial<1000;++trial) {
        int n=1+int(rng()%50);std::vector<int> permutation(n);std::iota(permutation.begin(),permutation.end(),0);
        std::shuffle(permutation.begin(),permutation.end(),rng);Edges edges;
        for(int v=1;v<n;++v)edges.push_back({permutation[v],permutation[rng()%unsigned(v)]});
        std::shuffle(edges.begin(),edges.end(),rng);for(auto& e:edges)if(rng()%2)std::swap(e.first,e.second);
        check_small(n,edges,int(rng()%unsigned(n)));
    }
}
void maximum_shapes() {
    const int n=200000;Edges edges;
    for(int v=1;v<n;++v)edges.push_back({v-1,v});
    for(int root:{0,n/2}) {
        auto labels=alternating_tree_labels(n,edges,root);auto g=adjacency(n,edges);auto c=neighbor_labels(g,labels);
        for(auto [source,target]:Edges{{0,n-1},{n-1,0},{n/3,n-1},{n/2,0}}) {
            int current=source;
            while(current!=target){int next=current+(target>current?1:-1);equal(next_tree_label_sorted(labels[current],labels[target],c[current]),labels[next],"maximum chain full route");current=next;++route_hops;}
        }
        equal(*std::max_element(labels.begin(),labels.end()),n-1,"maximum generated label");
    }
    edges.clear();const int center=n/3;for(int v=0;v<n;++v)if(v!=center)edges.push_back({center,v});
    std::mt19937 rng(1000);
    for(int root:{0,center}) {
        auto labels=alternating_tree_labels(n,edges,root);auto g=adjacency(n,edges);auto c=neighbor_labels(g,labels);
        for(int v=0;v<n;++v)if(v!=center){int t=int(rng()%unsigned(n));if(t==v)t=center;equal(next_tree_label_sorted(labels[v],labels[t],c[v]),labels[center],"maximum star leaf step");}
        for(int i=0;i<40;++i){int t=int(rng()%unsigned(n));if(t==center)t=0;equal(next_tree_label_sorted(labels[center],labels[t],c[center]),labels[t],"maximum star high degree boundary");}
        auto map=[&](int x){return INT_MAX-4*(n-1-x);};
        for(int& x:c[center])x=map(x);
        equal(next_tree_label_sorted(map(labels[center]),map(labels[0]),c[center]),map(labels[0]),"maximum sparse integer label and high degree");
    }
    edges.clear();std::vector<int> parent(n,-1),depth(n,0);
    for(int v=1;v<n;++v){parent[v]=(v-1)/2;depth[v]=depth[parent[v]]+1;edges.push_back({parent[v],v});}
    auto labels=alternating_tree_labels(n,edges);auto g=adjacency(n,edges);auto c=neighbor_labels(g,labels);
    for(int i=0;i<200000;++i) {
        int s=int(rng()%unsigned(n)),t=int(rng()%unsigned(n));if(s==t)t=(t+1)%n;
        int a=s,b=t;while(depth[a]>depth[b])a=parent[a];while(depth[b]>depth[a])b=parent[b];while(a!=b){a=parent[a];b=parent[b];}
        int wanted=parent[s];if(a==s){wanted=t;while(parent[wanted]!=s)wanted=parent[wanted];}
        equal(next_tree_label_sorted(labels[s],labels[t],c[s]),labels[wanted],"maximum equal-degree balanced tree / independent LCA step");
    }
    std::vector<int> u,v;for(int i=1;i<1000;++i){u.push_back(i-1);v.push_back(i);}
    auto official=label(1000,999,u,v);equal(*std::max_element(official.begin(),official.end()),999,"original maximum n and minimum k");
    require(label(1000,1000000000,u,v)==official,"larger k does not change the scheme");
    equal(find_next_station(9,6,{2,7}),2,"official routing example one");
    equal(find_next_station(2,3,{3,6,9}),3,"official routing example two");
}
void invalid() {
    for(int n:{0,-1,200001,INT_MIN,INT_MAX})rejects([&]{alternating_tree_labels(n,{});});
    rejects([]{alternating_tree_labels(2,{},0);});
    rejects([]{alternating_tree_labels(2,{{0,1}},-1);});rejects([]{alternating_tree_labels(2,{{0,1}},2);});
    for(auto edge:Edges{{-1,1},{0,2},{0,0},{INT_MIN,1},{0,INT_MAX}})rejects([&]{alternating_tree_labels(2,{edge});});
    rejects([]{alternating_tree_labels(3,{{0,1},{0,1}});});
    rejects([]{alternating_tree_labels(4,{{0,1},{1,2},{2,0}});});
    rejects([]{alternating_tree_labels(4,{{0,1},{1,2},{2,0}},3);});
    rejects([]{label(2,0,{0},{1});});rejects([]{label(2,1,{0},{});});
    rejects([]{label(INT_MIN,0,{},{});});rejects([]{label(1,-1,{},{});});
    for(auto [s,t]:Edges{{-1,1},{0,-1},{INT_MIN,1},{1,INT_MIN},{1,1}})rejects([&]{next_tree_label_sorted(s,t,{2});});
    rejects([]{next_tree_label_sorted(0,1,{});});
    rejects([]{next_tree_label_sorted(0,1,std::vector<int>(200000,2));});
    for(auto c:std::vector<std::vector<int>>{{-1},{2},{2,2},{3,2},{1,3}})rejects([&]{next_tree_label_sorted(2,0,c);});
    rejects([]{next_tree_label_sorted(0,1,{3,2});});
    rejects([]{next_tree_label(2,0,{3,1});});rejects([]{next_tree_label(0,3,{2,2});});
    require(alternating_tree_labels(1,{})==std::vector<int>{0},"single vertex extension");
    require(label(1,0,{},{})==std::vector<int>{0},"single vertex IOI adapter extension");
}
void emit(const char* filename) {
    std::ofstream out(filename);std::mt19937 rng(20200919);
    for(int scenario=0;scenario<40;++scenario) {
        int n=2+int(rng()%65);Edges edges;for(int v=1;v<n;++v)edges.push_back({int(rng()%unsigned(v)),v});
        std::shuffle(edges.begin(),edges.end(),rng);auto labels=alternating_tree_labels(n,edges,int(rng()%unsigned(n)));
        for(int& x:labels){int z=n-1-x;x=INT_MAX-10000*z-z*z;}
        auto g=adjacency(n,edges),step=bfs_steps(g),c=neighbor_labels(g,labels);
        for(int s=0;s<n;++s)for(int t=0;t<n;++t)if(s!=t) {
            out<<labels[s]<<' '<<labels[t]<<' '<<c[s].size()<<' '<<labels[step[s][t]];
            for(int value:c[s]) out<<' '<<value;
            out<<'\n';
        }
    }
}
int main(int argc,char** argv) {
    if(argc==3 && std::string(argv[1])=="--emit"){emit(argv[2]);return 0;}
    auto started=std::chrono::steady_clock::now();exhaustive();maximum_shapes();invalid();
    std::cout<<"{\"checks\":"<<checks<<",\"trees\":"<<tree_count<<",\"labelings\":"<<labelings
             <<",\"routeHops\":"<<route_hops<<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum
             <<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";
}
'''

ROUTER_MAIN = r'''
#include <fstream>
#include <iostream>
int main(int argc,char** argv) {
    if(argc!=2) return 2;
    std::ifstream in(argv[1]);int s,t,degree,expected;long long checks=0;
    while(in>>s>>t>>degree>>expected) {
        std::vector<int> c(degree);for(int& x:c)in>>x;
        if(find_next_station(s,t,c)!=expected){std::cerr<<"isolated process route mismatch\n";return 1;}
        ++checks;
    }
    std::cout<<checks<<'\n';
}
'''

args = [arg for arg in sys.argv[1:] if arg != '--sanitize']
article = Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/tree-local-routing-alternating-dfs-labels.mdx'
blocks = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
if len(blocks) != 1:
    raise RuntimeError('expected exactly one complete visible C++ fence')
code = blocks[0]
with tempfile.TemporaryDirectory(prefix='flowchartcp-stations-') as directory:
    folder = Path(directory)
    full, router = folder/'check.cpp', folder/'router.cpp'
    full.write_text(code + '\n' + HARNESS)
    includes = '\n'.join(re.findall(r'^#include .+$', code, re.M))
    tail = code.split('// Routing phase: no tree or labeler state is available.', 1)[1]
    router.write_text(includes + '\n// Routing phase: no tree or labeler state is available.' + tail + '\n' + ROUTER_MAIN)
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
    environment = os.environ.copy()
    sanitized = '--sanitize' in sys.argv
    if sanitized:
        flags += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS'] = 'detect_leaks=0'
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    for source, binary in [(full, folder/'check'), (router, folder/'router')]:
        subprocess.run([compiler, *flags, str(source), '-o', str(binary)], check=True, timeout=120)
    timer = Path('/usr/bin/time')
    command = [str(timer), '-f', 'peak_rss_kib=%M', str(folder/'check')] if timer.exists() and sys.platform.startswith('linux') else [str(folder/'check')]
    result = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=180)
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    report = json.loads(result.stdout)
    records = folder/'routes.txt'
    subprocess.run([str(folder/'check'), '--emit', str(records)], check=True, env=environment, timeout=180)
    isolated = subprocess.run([str(folder/'router'), str(records)], check=True, text=True, capture_output=True, env=environment, timeout=180)
    report.update(article=str(article), sanitized=sanitized, isolatedRouterChecks=int(isolated.stdout), routerCompiledWithoutLabeler=True)
    match = re.search(r'^peak_rss_kib=(\d+)$', result.stderr, re.M)
    if match:
        report['peakRSSKiB'] = int(match[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
