#!/usr/bin/env python3
"""Compile visible C++20; answer EVERY actual weighting by an independent Dijkstra."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

TESTS=r'''
#include <bit>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <string>
using I=std::int64_t;using U=std::uint64_t;
U checks=0,graphs=0,exhaustive_cases=0,random_cases=0,oracle_queries=0,relaxations=0,checksum=0;
U maximum_cases=0,maximum_oracle_queries=0;int maximum_n=0,maximum_m=0,largest_query_count=0;
I largest_reply=0;double maximum_case_seconds=0;
void require(bool condition,const char* why){++checks;if(!condition){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(U value){checksum=checksum*1000003+value+2;}
int ceil_log(int value){return int(std::bit_width(unsigned(value-1)));}
int split_bound(int n){int answer=0;for(int p=1;p<n;++p)answer=std::max(answer,ceil_log(p)+ceil_log(n-p));return answer;}
struct Graph{
    int n;std::vector<int> from,to;std::vector<std::vector<std::pair<int,int>>> adjacent;
    Graph(int size,std::vector<std::pair<int,int>> edges):n(size),adjacent(size){
        for(auto [u,v]:edges){const int index=int(from.size());from.push_back(u);to.push_back(v);adjacent[u].push_back({v,index});adjacent[v].push_back({u,index});}
    }
    bool connected()const{
        std::vector<bool> seen(n);std::vector<int> queue{0};seen[0]=true;
        for(std::size_t head=0;head<queue.size();++head)for(auto [y,edge]:adjacent[queue[head]]){(void)edge;if(!seen[y]){seen[y]=true;queue.push_back(y);}}
        return int(queue.size())==n;
    }
    I distance(int s,int t,I a,I b,const std::vector<int>& weight)const{
        const I infinity=std::numeric_limits<I>::max()/4;
        std::vector<I> dist(n,infinity);dist[s]=0;
        std::priority_queue<std::pair<I,int>,std::vector<std::pair<I,int>>,std::greater<>> heap;heap.push({0,s});
        while(!heap.empty()){
            const auto [d,x]=heap.top();heap.pop();if(d!=dist[x])continue;if(x==t)return d;
            for(auto [y,edge]:adjacent[x]){++relaxations;const I next=d+(weight[edge]?b:a);if(next<dist[y]){dist[y]=next;heap.push({next,y});}}
        }
        return infinity;
    }
};
struct Oracle{
    const Graph& graph;const int s,t;const I a,b;int calls=0;bool maximum=false;
    Oracle(const Graph& g,int x,int y,I low,I high,bool large=false):graph(g),s(x),t(y),a(low),b(high),maximum(large){}
    Oracle(const Oracle&)=delete;Oracle& operator=(const Oracle&)=delete;
    I operator()(const std::vector<int>& weight){
        ++calls;++oracle_queries;if(maximum)++maximum_oracle_queries;
        require(calls<=50,"EVERY individual run respects full-score50 BEFORE invoking distance oracle");
        require(weight.size()==graph.from.size(),"EVERY weighting uses original M edge terminals");
        for(int bit:weight)require(bit==0||bit==1,"EVERY terminal assigns exactly A or B");
        const I reply=graph.distance(s,t,a,b,weight);largest_reply=std::max(largest_reply,reply);return reply;
    }
};
void solve_case(const Graph& graph,int s,int t,I a,I b,bool maximum=false){
    Oracle oracle(graph,s,t,a,b,maximum);const auto from_before=graph.from,to_before=graph.to;
    const auto begin=std::chrono::steady_clock::now();
    const auto answer=find_binary_weight_hidden_pair(graph.n,graph.from,graph.to,a,b,oracle);
    if(maximum)maximum_case_seconds=std::max(maximum_case_seconds,std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count());
    require((answer.first==s&&answer.second==t)||(answer.first==t&&answer.second==s),"returned unordered pair equals the SAME fixed hidden pair used by every Dijkstra");
    require(answer.queries==oracle.calls&&answer.queries<=50,"reported query count equals observed callback calls");
    require(graph.from==from_before&&graph.to==to_before,"local validation/order never modifies edge arrays");
    largest_query_count=std::max(largest_query_count,answer.queries);
    absorb(U(std::min(answer.first,answer.second))*90000+U(std::max(answer.first,answer.second)));absorb(U(answer.queries));
    if(maximum){++maximum_cases;maximum_n=std::max(maximum_n,graph.n);maximum_m=std::max(maximum_m,int(graph.from.size()));}
}
void exhaustive(){
    const std::array<std::pair<I,I>,5> tolls{{{1,2},{3,4},{1,1000000000},{999999999,1000000000},{6,12}}};
    for(int n=2;n<=6;++n){
        std::vector<std::pair<int,int>> possible;for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)possible.push_back({u,v});
        const unsigned limit=1U<<possible.size();
        for(unsigned mask=0;mask<limit;++mask){
            if(std::popcount(mask)<n-1)continue;
            std::vector<std::pair<int,int>> edges;for(int i=0;i<int(possible.size());++i)if(mask>>i&1U)edges.push_back(possible[i]);
            Graph graph(n,edges);if(!graph.connected())continue;++graphs;
            for(int s=0;s<n;++s)for(int t=s+1;t<n;++t)for(auto [a,b]:tolls){solve_case(graph,s,t,a,b);++exhaustive_cases;}
        }
    }
    require(graphs==27475&&exhaustive_cases==2040405,"ALL connected simple graphsN2..6, ALL unordered pairs, FIVE arbitrary toll settings");
}
void randomized(){
    std::mt19937 rng(20180905);
    for(int test=0;test<3000;++test){
        const int n=2+int(rng()%119);std::set<std::pair<int,int>> unique;
        for(int x=1;x<n;++x)unique.insert({int(rng()%x),x});
        for(int q=0;q<3*n;++q){int x=int(rng()%n),y=int(rng()%n);if(x==y)continue;if(x>y)std::swap(x,y);unique.insert({x,y});}
        std::vector<std::pair<int,int>> edges(unique.begin(),unique.end());std::shuffle(edges.begin(),edges.end(),rng);
        for(auto& edge:edges)if(rng()%2)std::swap(edge.first,edge.second);
        Graph graph(n,edges);int s=int(rng()%n),t=int(rng()%(n-1));if(t>=s)++t;
        const I a=1+I(rng()%999999999),b=a+1+I(rng()%U(1000000000-a));solve_case(graph,s,t,a,b);++random_cases;
    }
}
struct FloatReply{double operator()(const std::vector<int>&){return 1.;}};
struct UnsignedReply{U operator()(const std::vector<int>&){return 1;}};
struct BoolReply{bool operator()(const std::vector<int>&){return true;}};
struct WrongArgument{I operator()(int){return 1;}};
static_assert(!SignedDistanceOracle<FloatReply> && !SignedDistanceOracle<UnsignedReply> && !SignedDistanceOracle<BoolReply> && !SignedDistanceOracle<WrongArgument>);
static_assert(SignedDistanceOracle<Oracle&>);
void rejects(int n,const std::vector<int>& from,const std::vector<int>& to,I a,I b){
    int calls=0;bool threw=false;auto never=[&](const std::vector<int>&)->I{++calls;return 1;};
    try{(void)find_binary_weight_hidden_pair(n,from,to,a,b,never);}catch(const std::invalid_argument&){threw=true;}
    require(threw&&calls==0,"ALL malformed graph/toll inputs rejected before ANY external call");
}
void boundaries(){
    Graph sample(4,{{0,1},{0,2},{0,3},{1,2}});std::vector<int> weight(4);
    require(sample.distance(1,3,1,3,{0,0,0,0})==2&&sample.distance(1,3,1,3,{0,1,1,0})==4&&
            sample.distance(1,3,1,3,{1,0,1,0})==5&&sample.distance(1,3,1,3,{1,1,1,1})==6,"official sample weighting/reply table");
    solve_case(sample,1,3,1,3);
    Graph diamond(4,{{0,1},{1,2},{2,3},{3,0}});
    for(int edge=0;edge<4;++edge){weight.assign(4,0);weight[edge]=1;require(diamond.distance(0,2,6,12,weight)==12,"NO edge belongs to ALL original shortest paths; pivot need not be universal");}
    solve_case(diamond,0,2,6,12);solve_case(diamond,2,0,999999999,1000000000);
    Graph one(2,{{1,0}});solve_case(one,0,1,999999999,1000000000);
    Oracle single_oracle(one,1,0,1,2);const auto smallest=find_binary_weight_hidden_pair(2,one.from,one.to,1,2,single_oracle);
    require(smallest.queries==1,"one edge: root endpoints, empty binary searches, baseline only");
    rejects(0,{}, {},1,2);rejects(1,{}, {},1,2);rejects(90001,{0},{1},1,2);rejects(std::numeric_limits<int>::max(),{0},{1},1,2);
    rejects(2,{}, {},1,2);rejects(2,{0},{},1,2);rejects(3,{0},{1},1,2);rejects(2,std::vector<int>(130001),std::vector<int>(130001),1,2);
    rejects(2,{-1},{1},1,2);rejects(2,{0},{2},1,2);rejects(2,{0},{0},1,2);
    rejects(3,{0,1},{1,0},1,2);rejects(4,{0,1,0},{1,2,2},1,2);
    for(auto [a,b]:std::vector<std::pair<I,I>>{{0,1},{-1,2},{1,1},{2,1},{1,1000000001},{std::numeric_limits<I>::min(),std::numeric_limits<I>::max()}})rejects(2,{0},{1},a,b);
    for(I reply:std::vector<I>{-1,0,4,9,std::numeric_limits<I>::max()}){
        bool threw=false;int calls=0;auto bad=[&](const std::vector<int>&)->I{++calls;return reply;};
        try{(void)find_binary_weight_hidden_pair(3,{0,1},{1,2},3,7,bad);}catch(const std::runtime_error&){threw=true;}
        require(threw&&calls==1,"malformed all-low response, divisibility/bounds/negative checked");
    }
    for(I bad_reply:std::vector<I>{1,15}){
        bool threw=false;int calls=0;auto bad=[&](const std::vector<int>&)->I{return ++calls==1?6:bad_reply;};
        try{(void)find_binary_weight_hidden_pair(3,{0,1},{1,2},3,7,bad);}catch(const std::runtime_error&){threw=true;}
        require(threw&&calls==2,"later distance belowbaseline or aboved*B rejected on first occurrence");
    }
    {
        bool threw=false;auto bad=[](const std::vector<int>&)->I{return 6;};
        try{(void)find_binary_weight_hidden_pair(3,{0,1},{1,2},3,7,bad);}catch(const std::runtime_error&){threw=true;}
        require(threw,"recovered pair inconsistent with all-low hop count is rejected without an extra oracle question");
    }
    struct Marker{int value;};
    Oracle reference(sample,1,3,1,3);const auto reference_result=find_binary_weight_hidden_pair(4,sample.from,sample.to,1,3,reference);
    for(int fail=1;fail<=reference_result.queries;++fail){
        int calls=0;bool threw=false;auto interrupted=[&](const std::vector<int>& w)->I{if(++calls==fail)throw Marker{fail};return sample.distance(1,3,1,3,w);};
        try{(void)find_binary_weight_hidden_pair(4,sample.from,sample.to,1,3,interrupted);}catch(const Marker& marker){threw=marker.value==fail;}
        require(threw&&calls==fail,"callback exceptions propagate unchanged, no retry/extra queries");
        solve_case(sample,1,3,1,3); // A subsequent fresh invocation has no residual solver state.
    }
    {
        int outer_calls=0;auto reentrant=[&](const std::vector<int>& w)->I{
            if(++outer_calls==1){
                int inner_calls=0;auto inner=[&](const std::vector<int>& z)->I{++inner_calls;require(z==std::vector<int>{0},"nested baseline weighting");return 42;};
                const auto nested=find_binary_weight_hidden_pair(2,{0},{1},42,43,inner);
                require(nested.queries==1&&inner_calls==1&&nested.first!=nested.second,"reentrant solver has separate local state");
            }
            return sample.distance(1,3,1,3,w);
        };
        const auto answer=find_binary_weight_hidden_pair(4,sample.from,sample.to,1,3,reentrant);
        require(answer.queries==outer_calls&&std::min(answer.first,answer.second)==1&&std::max(answer.first,answer.second)==3,"nested callback does not corrupt outer run");
    }
    require(split_bound(90000)==32&&1+ceil_log(130000)+split_bound(90000)==50,"exact ceiling-log bound enumerated over EVERY split p+q=90000");
    require(ceil_log(32769)+ceil_log(65537)==33&&32769+65537>90000,"rounding boundary33 requires98306 total vertices");
}
void maximum(){
    {
        constexpr int n=90000;std::vector<std::pair<int,int>> edges;edges.reserve(130000);
        edges.push_back({0,45000});
        for(int x=1;x<45000;++x)edges.push_back({0,x});
        for(int x=45001;x<n;++x)edges.push_back({45000,x});
        for(int x=1;edges.size()<130000;++x)edges.push_back({x,x+1});
        Graph graph(n,std::move(edges));
        for(auto [a,b]:std::array<std::pair<I,I>,3>{{{1,2},{999999999,1000000000},{1,1000000000}}}){
            Oracle oracle(graph,0,45000,a,b,true);const auto begin=std::chrono::steady_clock::now();
            const auto answer=find_binary_weight_hidden_pair(graph.n,graph.from,graph.to,a,b,oracle);
            maximum_case_seconds=std::max(maximum_case_seconds,std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count());
            require(answer.queries==50&&oracle.calls==50,"N90000/M130000 balanced sides attain EXACT50 queries for roots on pivot edge");
            require((answer.first==0&&answer.second==45000)||(answer.first==45000&&answer.second==0),"exact50 maximum case pair");
            absorb(U(answer.first)*90000+U(answer.second));absorb(U(answer.queries));
            ++maximum_cases;maximum_n=n;maximum_m=130000;largest_query_count=50;
        }
    }
    {
        constexpr int n=90000;std::vector<std::pair<int,int>> edges;for(int x=1;x<n;++x)edges.push_back({x-1,x});
        Graph path(n,std::move(edges));solve_case(path,0,n-1,999999999,1000000000,true);solve_case(path,n-1,0,1,1000000000,true);
    }
    {
        constexpr int n=90000;std::set<std::pair<int,int>> edges;std::mt19937 rng(130000);
        for(int x=1;x<n;++x)edges.insert({int(rng()%x),x});
        while(edges.size()<130000){int x=int(rng()%n),y=int(rng()%n);if(x==y)continue;if(x>y)std::swap(x,y);edges.insert({x,y});}
        std::vector<std::pair<int,int>> shuffled(edges.begin(),edges.end());std::shuffle(shuffled.begin(),shuffled.end(),rng);
        Graph graph(n,std::move(shuffled));solve_case(graph,89999,71234,999999999,1000000000,true);
    }
    require(maximum_n==90000&&maximum_m==130000&&largest_query_count==50&&largest_reply>89998000000000LL,"maximum graph/query/64bit distance boundaries really executed");
}
int main(){
    const auto begin=std::chrono::steady_clock::now();boundaries();exhaustive();randomized();maximum();
    std::cout<<"{\"checks\":"<<checks<<",\"allConnectedSimpleGraphs\":"<<graphs<<",\"allPairsTimesFiveTolls\":"<<exhaustive_cases
             <<",\"randomCases\":"<<random_cases<<",\"oracleQueries\":"<<oracle_queries<<",\"dijkstraRelaxations\":"<<relaxations
             <<",\"maximumCases\":"<<maximum_cases<<",\"maximumOracleQueries\":"<<maximum_oracle_queries<<",\"maximumN\":"<<maximum_n
             <<",\"maximumM\":"<<maximum_m<<",\"largestQueryCount\":"<<largest_query_count<<",\"largestReply\":"<<largest_reply
             <<",\"maximumCaseSeconds\":"<<maximum_case_seconds<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
             <<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''

args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/binary-weight-distance-oracle-edge-split-endpoint-search.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-highway-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)];timer=Path('/usr/bin/time')
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=environment,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
