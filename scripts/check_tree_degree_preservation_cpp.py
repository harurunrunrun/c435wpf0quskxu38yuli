#!/usr/bin/env python3
"""Compile the article's sole visible C++20 fence and check its public APIs."""
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
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <sys/resource.h>

using degree_tree::Edge;
using degree_tree::Result;
using Degrees = std::vector<std::int64_t>;
using Edges = std::vector<Edge>;
std::uint64_t checks=0, checksum=0, api_calls=0, degree_vectors=0, graph_cases=0;
std::uint64_t complete_graph_edge_subsets=0, labeled_trees=0, literal_tree_vector_comparisons=0;
std::uint64_t random_cases=0, metamorphic=0, invalid_calls=0, dp_states=0;
void require(bool condition,const char* message){++checks;if(!condition)throw std::runtime_error(message);}
void record(std::uint64_t value){checksum=checksum*1000003ULL+value;}
bool same(const Result&a,const Result&b){return a.changed_vertices==b.changed_vertices&&a.degree==b.degree&&a.edges==b.edges;}
Result core(const Degrees&d){++api_calls;return degree_tree::closest_tree_degrees(d);}
Result graph(int n,const Edges&e){++api_calls;return degree_tree::rebuild_tree_preserving_degrees(n,e);}
Degrees input_degrees(int n,const Edges&e){Degrees d(n,0);for(auto[a,b]:e){++d[a];++d[b];}return d;}
bool connected(int n,const Edges&e){
    std::vector<std::vector<int>> adjacency(n);
    for(auto[a,b]:e){adjacency[a].push_back(b);adjacency[b].push_back(a);}
    std::vector<bool> seen(n,false);std::vector<int> pending{0};seen[0]=true;
    for(std::size_t i=0;i<pending.size();++i)for(int v:adjacency[pending[i]])if(!seen[v]){seen[v]=true;pending.push_back(v);}
    return int(pending.size())==n;
}
void verify(const Degrees&d,const Result&r,int expected=-1){
    const int n=int(d.size());
    require(int(r.degree.size())==n,"returned degree length");
    require(int(r.edges.size())==n-1,"tree must have N-1 edges");
    std::set<Edge> unique;Degrees actual(n,0);
    for(auto[a,b]:r.edges){require(a>=0&&a<n&&b>=0&&b<n&&a!=b,"output endpoint or self loop");
        require(unique.insert(std::minmax(a,b)).second,"output parallel edge");++actual[a];++actual[b];}
    require(connected(n,r.edges),"output tree disconnected");
    int changed=0;for(int v=0;v<n;++v){require(actual[v]==r.degree[v],"returned degree disagrees with actual edges");changed+=actual[v]!=d[v];}
    require(changed==r.changed_vertices,"changed count disagrees with literal degree comparison");
    if(expected>=0)require(changed==expected,"not optimal against independent oracle");
    record(r.changed_vertices);for(auto[a,b]:r.edges){record(a);record(b);}
}
struct TreeOracle {std::uint64_t trees=0;std::vector<std::vector<int>> degrees;};
std::array<TreeOracle,8> oracles;
// Enumerate EVERY subset of N-1 edges of the complete simple graph. This oracle
// does not decode a Pruefer word and does not select degrees with a budget.
void prepare_oracle(int n){
    Edges possible;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)possible.push_back({a,b});
    Edges chosen;std::set<std::vector<int>> unique;
    auto enumerate=[&](auto&&self,int position,int needed)->void{
        if(needed==0){++complete_graph_edge_subsets;if(!connected(n,chosen))return;
            ++oracles[n].trees;++labeled_trees;Degrees d=input_degrees(n,chosen);unique.emplace(d.begin(),d.end());return;}
        for(int j=position;j<=int(possible.size())-needed;++j){chosen.push_back(possible[j]);self(self,j+1,needed-1);chosen.pop_back();}
    };
    enumerate(enumerate,0,n-1);oracles[n].degrees.assign(unique.begin(),unique.end());
    std::uint64_t cayley=1;for(int j=0;j<n-2;++j)cayley*=n;
    require(oracles[n].trees==cayley,"edge-subset enumeration matches Cayley count");
}
int optimum(const Degrees&original){
    int best=int(original.size());
    for(const auto&d:oracles[original.size()].degrees){++literal_tree_vector_comparisons;
        int value=0;for(std::size_t v=0;v<d.size();++v)value+=d[v]!=original[v];best=std::min(best,value);}
    return best;
}
void exhaustive_degrees(){
    verify({0},core({0}),0);
    for(int n=2;n<=7;++n){const int largest=n<=6?n+1:4;Degrees d(n,1);
        auto enumerate=[&](auto&&self,int v,std::int64_t sum)->void{
            if(v==n){if(sum<2*n-2)return;const Degrees before=d;const int expected=optimum(d);auto r=core(d);verify(d,r,expected);
                require(d==before,"core input unchanged");++degree_vectors;return;}
            for(int x=1;x<=largest;++x){d[v]=x;self(self,v+1,sum+x);}
        };enumerate(enumerate,0,0);
    }
}
void exhaustive_multigraphs(){
    for(int n=2;n<=5;++n){Edges possible;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)possible.push_back({a,b});Edges e;
        const int multiplicity=n<=4?3:2;
        auto enumerate=[&](auto&&self,int v)->void{
            if(v==int(possible.size())){if(!connected(n,e))return;const Edges before=e;const Degrees d=input_degrees(n,e);auto r=graph(n,e);verify(d,r,optimum(d));
                require(e==before,"graph input unchanged");require(same(r,core(d)),"graph result depends on more than degrees");++graph_cases;return;}
            self(self,v+1);for(int count=1;count<=multiplicity;++count){e.push_back(possible[v]);self(self,v+1);}for(int count=0;count<multiplicity;++count)e.pop_back();
        };enumerate(enumerate,0);
    }
}
// Independently choose the new degree of EVERY vertex, imposing only the exact
// tree degree sum. No cheap-item sort or preserved-set selection is used.
int full_degree_assignment_dp(const Degrees&d){
    const int n=int(d.size()),sum=2*n-2,inf=n+1;std::vector<int> dp(sum+1,inf);dp[0]=0;
    for(std::int64_t original:d){std::vector<int> next(sum+1,inf);
        for(int used=0;used<=sum;++used)if(dp[used]<inf)for(int target=1;target<n&&used+target<=sum;++target){++dp_states;
            next[used+target]=std::min(next[used+target],dp[used]+(target!=original));}dp.swap(next);}
    return dp[sum];
}
void random_and_metamorphic(){std::mt19937_64 rng(20180419);
    for(int test=0;test<1000;++test){const int n=2+int(rng()%35);Edges e;for(int v=1;v<n;++v)e.push_back({v,int(rng()%v)});
        const int extra=int(rng()%250);for(int j=0;j<extra;++j){int a=int(rng()%n),b=int(rng()%(n-1));if(b>=a)++b;e.push_back({a,b});}
        const Degrees d=input_degrees(n,e);const int expected=full_degree_assignment_dp(d);auto r=graph(n,e);verify(d,r,expected);++random_cases;
        if(test<200){if(n<=7)require(expected==optimum(d),"degree assignment DP versus literal all trees");
            std::shuffle(e.begin(),e.end(),rng);for(Edge&edge:e)if(rng()&1)std::swap(edge.first,edge.second);
            require(same(r,graph(n,e)),"edge order and orientation invariant");++metamorphic;
            std::vector<int> permutation(n);std::iota(permutation.begin(),permutation.end(),0);std::shuffle(permutation.begin(),permutation.end(),rng);
            for(auto&[a,b]:e){a=permutation[a];b=permutation[b];}verify(input_degrees(n,e),graph(n,e),expected);++metamorphic;
        }
        Degrees arbitrary(n);std::int64_t total=0;for(auto&x:arbitrary){x=1+std::int64_t(rng()%(3*n));total+=x;}
        if(total>=2*n-2){verify(arbitrary,core(arbitrary),full_degree_assignment_dp(arbitrary));++random_cases;}
    }
}
void writer_check(int n,const Edges&e,int expected){
    std::ostringstream output;degree_tree::write_rebuilt_tree(output,n,e);++api_calls;
    std::istringstream input(output.str());int changed=-1,vertices=-1,count=-1;
    require(bool(input>>changed>>vertices>>count),"writer header");require(vertices==n&&count==n-1,"writer exact original format");
    Result r{changed,std::vector<int>(n,0),{}};for(int i=0;i<count;++i){int a,b;require(bool(input>>a>>b),"writer edge tokens");
        require(a>=0&&a<n&&b>=0&&b<n,"writer endpoint range");r.edges.push_back({a,b});++r.degree[a];++r.degree[b];}
    std::string extra;require(!(input>>extra),"writer no extra token");verify(input_degrees(n,e),r,expected);
}
void api_tests(){
    verify({0},graph(1,{}),0);writer_check(1,{},0);
    Edges first{{0,1},{0,2},{0,5},{0,6},{1,3},{2,4},{1,2},{1,2},{1,5},{2,6},{5,6}};
    writer_check(7,first,3);writer_check(4,{{0,1},{2,1},{2,3}},0);
    writer_check(2,{{0,1}},0);writer_check(2,{{0,1},{1,0}},2);
    // The original star is the ONLY spanning tree allowed if old-edge restriction
    // is imposed; it changes the hub and two leaves. A new path keeps both 2s and the 1.
    Edges new_edge_witness{{0,1},{0,1},{0,2},{0,2},{0,3}};
    auto r=graph(4,new_edge_witness);verify(input_degrees(4,new_edge_witness),r,1);
    std::set<Edge> old;for(auto[a,b]:new_edge_witness)old.insert(std::minmax(a,b));bool novel=false;
    for(auto[a,b]:r.edges){novel|=!old.contains(std::minmax(a,b));}require(novel,"new edges may be essential");
    require(r.changed_vertices<3,"old-edge restriction has strictly worse objective");
    const Edges only_old_tree{{0,1},{0,2},{0,3}};const Degrees its_degrees=input_degrees(4,only_old_tree);
    verify(input_degrees(4,new_edge_witness),Result{3,std::vector<int>(its_degrees.begin(),its_degrees.end()),only_old_tree},3);
    const std::int64_t big=std::numeric_limits<std::int64_t>::max();
    for(const Degrees&d:std::vector<Degrees>{{big,big},{1,big},{big,1,1},{big,big,big,big},{1,2},{1,3,3,3,4},{2,2,2},{1,1}}){verify(d,core(d),optimum(d));}
    auto original=core({1,3,3,3,4});Result copied=original;copied.degree[0]=99;copied.edges.clear();
    require(original.degree[0]==1&&!original.edges.empty(),"returned result owns copied vectors");Result moved=std::move(copied);require(moved.degree[0]==99,"returned result movable");
    require(same(original,core({1,3,3,3,4})),"independent calls after result mutation");
    auto reject_core=[&](const Degrees&d){bool rejected=false;const Degrees before=d;try{(void)core(d);}catch(const std::invalid_argument&){rejected=true;}
        require(rejected&&d==before,"invalid core call");++invalid_calls;verify({1,1},core({1,1}),0);};
    reject_core({});reject_core(Degrees(10001,1));reject_core({1});reject_core({-1});reject_core({big});reject_core({std::numeric_limits<std::int64_t>::min()});
    reject_core({0,1});reject_core({1,0});reject_core({-1,3});reject_core({std::numeric_limits<std::int64_t>::min(),big});reject_core({1,1,1});reject_core({1,1,1,1});
    auto reject_graph=[&](int n,const Edges&e){bool rejected=false;const Edges before=e;try{(void)graph(n,e);}catch(const std::invalid_argument&){rejected=true;}
        require(rejected&&e==before,"invalid graph call");++invalid_calls;std::ostringstream output;rejected=false;
        try{degree_tree::write_rebuilt_tree(output,n,e);++api_calls;}catch(const std::invalid_argument&){rejected=true;}
        require(rejected&&output.str().empty(),"writer must reject before output");verify({1,1},graph(2,{{0,1}}),0);};
    reject_graph(0,{});reject_graph(-1,{});reject_graph(10001,{});reject_graph(INT_MIN,{});reject_graph(INT_MAX,{});
    reject_graph(2,Edges(100001,{0,1}));reject_graph(2,{});reject_graph(3,{{0,1}});reject_graph(4,{{0,1},{2,3}});
    reject_graph(1,{{0,0}});reject_graph(2,{{0,0},{0,1}});reject_graph(2,{{0,1},{1,1}});
    reject_graph(2,{{-1,1}});reject_graph(2,{{0,-1}});reject_graph(2,{{0,2}});reject_graph(2,{{2,1}});
    reject_graph(2,{{INT_MIN,1}});reject_graph(2,{{0,INT_MAX}});reject_graph(1,{{0,1}});
    for(int call=0;call<100;++call){verify({0},graph(1,{}),0);verify({2,2},graph(2,{{0,1},{1,0}}),2);}
}
struct MaxRecord{std::string name;int n,m,changed;};std::vector<MaxRecord> max_records;
void certificate(const Degrees&d,const Result&r){
    const int n=int(d.size()),kept=n-r.changed_vertices;std::vector<std::int64_t> costs;for(auto x:d)costs.push_back(x-1);
    if(kept<n){std::nth_element(costs.begin(),costs.begin()+kept,costs.end());std::int64_t sum=0;
        for(int i=0;i<=kept;++i){sum+=std::min<std::int64_t>(costs[i],2*n);}
        require(sum>n-2,"independent next-cardinality infeasibility certificate");}
}
void max_case(const std::string&name,int n,const Edges&e,int expected=-1){
    const Edges before=e;auto r=graph(n,e);const Degrees d=input_degrees(n,e);verify(d,r,expected);certificate(d,r);
    require(e==before,"maximum graph unchanged");require(same(r,core(d)),"maximum graph versus degree API");
    max_records.push_back({name,n,int(e.size()),r.changed_vertices});
}
void maximum(){const int n=10000;Edges e;
    max_case("two vertices,100000 parallel links",2,Edges(100000,{0,1}),2);
    for(int v=1;v<n;++v){e.push_back({v-1,v});}max_case("maximum path",n,e,0);
    e.clear();for(int v=1;v<n;++v)e.push_back({0,v});max_case("maximum star",n,e,0);
    while(e.size()<100000){e.push_back({0,1});}max_case("maximum star with parallel hub pair",n,e,2);
    e.clear();for(int v=0;v<n;++v)e.push_back({v,(v+1)%n});max_case("maximum cycle",n,e,2);
    std::mt19937_64 rng(314159);for(int mode=0;mode<3;++mode){e.clear();for(int v=1;v<n;++v)e.push_back({v-1,v});
        while(e.size()<100000){int a=mode==0?int(rng()%n):mode==1?0:int(e.size()%(n-1));int b=mode==0?int(rng()%(n-1)):mode==1?1:int(e.size()%(n-1))+1;
            if(mode==0&&b>=a){++b;}e.push_back({a,b});}max_case("maximum100000edge family"+std::to_string(mode),n,e);}
    Degrees d(n,std::numeric_limits<std::int64_t>::max());auto r=core(d);verify(d,r,n);certificate(d,r);max_records.push_back({"10000 maximal int64 desired degrees",n,-1,r.changed_vertices});
    d.assign(n,1);d[0]=std::numeric_limits<std::int64_t>::max();r=core(d);verify(d,r,1);certificate(d,r);max_records.push_back({"one maximal int64 desired degree",n,-1,r.changed_vertices});
}
int main(){try{const auto start=std::chrono::steady_clock::now();for(int n=2;n<=7;++n)prepare_oracle(n);api_tests();exhaustive_degrees();exhaustive_multigraphs();random_and_metamorphic();maximum();
    rusage usage{};getrusage(RUSAGE_SELF,&usage);std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"completeGraphEdgeSubsets\":"<<complete_graph_edge_subsets
      <<",\"labeledTrees\":"<<labeled_trees<<",\"degreeVectors\":"<<degree_vectors<<",\"literalTreeVectorComparisons\":"<<literal_tree_vector_comparisons<<",\"connectedMultigraphs\":"<<graph_cases
      <<",\"randomCases\":"<<random_cases<<",\"fullDegreeAssignmentDPStates\":"<<dp_states<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCalls\":"<<invalid_calls
      <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
    bool comma=false;for(const auto&x:max_records){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<x.name<<"\",\"n\":"<<x.n<<",\"m\":"<<x.m<<",\"changed\":"<<x.changed<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/tree-degree-preservation-budget-construction.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    assert '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-degree-tree-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
        source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:
            env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    result=json.loads(run.stdout)
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':args.sanitize,'compilerFlags':flags,**result},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
