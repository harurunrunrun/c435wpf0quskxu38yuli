#!/usr/bin/env python3
"""Extract the visible C++20; exhaustive two-form BFS and independent path-RMQ oracle."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/two-threshold-component-merge-trees-rectangle-intersection.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one visible complete C++20 fence')
TESTS=r'''
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <set>
using Edge=std::pair<int,int>;
using Query=ThresholdIntersectionQuery;
using U=std::uint64_t;
U checks=0,checksum=0,small_graphs=0,source_graphs=0,source_queries=0,all_small_queries=0;
U random_graphs=0,random_queries=0,maximum_cases=0,maximum_queries=0,invalid_cases=0;
void need(bool ok,const char* why){++checks;if(!ok){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(U x){checksum=checksum*1000003+x+1;}
std::vector<std::vector<int>> adjacency(int n,const std::vector<Edge>& edges){
    std::vector<std::vector<int>> g(n);for(auto [a,b]:edges){g[a].push_back(b);g[b].push_back(a);}return g;
}
bool connected(const std::vector<std::vector<int>>& graph){
    std::vector<bool> seen(graph.size());std::vector<int> todo{0};seen[0]=true;
    for(std::size_t at=0;at<todo.size();++at)for(int w:graph[todo[at]])if(!seen[w]){seen[w]=true;todo.push_back(w);}
    return todo.size()==graph.size();
}
// Direct simulation of the original rules. Edges move within the current form;
// the only form-changing arc is human(v)->wolf(v). No component lemma is used.
bool two_form_bfs(const std::vector<std::vector<int>>& graph,Query query){
    const int n=int(graph.size());std::vector<bool> seen(2*n);std::vector<int> todo{2*query.start};seen[todo[0]]=true;
    for(std::size_t at=0;at<todo.size();++at){
        const int state=todo[at],v=state/2,form=state%2;
        if(state==2*query.goal+1)return true;
        auto visit=[&](int next){if(!seen[next]){seen[next]=true;todo.push_back(next);}};
        for(int w:graph[v])if(form==0?w>=query.lower:w<=query.upper)visit(2*w+form);
        if(form==0&&v<=query.upper)visit(2*v+1);
    }
    return false;
}
int component_intersection_bfs(const std::vector<std::vector<int>>& graph,Query query){
    const int n=int(graph.size());
    auto reach=[&](int start,int low,int high){
        std::vector<bool> seen(n);std::vector<int> todo{start};seen[start]=true;
        for(std::size_t at=0;at<todo.size();++at)for(int w:graph[todo[at]])
            if(low<=w&&w<=high&&!seen[w]){seen[w]=true;todo.push_back(w);}
        return seen;
    };
    auto a=reach(query.start,query.lower,n-1),b=reach(query.goal,0,query.upper);int count=0;
    for(int v=0;v<n;++v)count+=a[v]&&b[v];
    return count;
}
U query_hash(const std::vector<Query>& queries){
    U value=0;for(auto q:queries)for(int x:{q.start,q.goal,q.lower,q.upper})value=value*1000003+x+1;return value;
}
void verify_batch(int n,const std::vector<Edge>& edges,const std::vector<Query>& queries,bool small){
    const auto before_edges=edges;const U before_queries=query_hash(queries);const auto graph=adjacency(n,edges);
    auto counts=threshold_component_intersection_counts(n,edges,queries);
    auto flags=threshold_switch_reachability(n,edges,queries);
    need(counts.size()==queries.size()&&flags.size()==queries.size(),"output size and input ordering");
    for(std::size_t i=0;i<queries.size();++i){
        const int expected=component_intersection_bfs(graph,queries[i]);
        const bool feasible=two_form_bfs(graph,queries[i]);
        need(counts[i]==expected,"intersection count equals two direct restricted BFS sets");
        need(flags[i]==int(feasible),"0/1 answer equals original direct two-form BFS");
        need((counts[i]>0)==feasible,"independently check reduction to nonempty intersection");
        absorb(counts[i]);absorb(flags[i]);
        if(small){++all_small_queries;source_queries+=n>=2&&queries[i].start!=queries[i].goal;}
        else ++random_queries;
    }
    need(edges==before_edges&&query_hash(queries)==before_queries,"both APIs preserve inputs");
}
std::vector<Query> all_queries(int n){
    std::vector<Query> out;
    for(int s=0;s<n;++s)for(int e=0;e<n;++e)for(int l=0;l<=s;++l)for(int r=e;r<n;++r)
        if(l<=r)out.push_back({s,e,l,r});
    return out;
}
void exhaustive(){
    for(int n=1;n<=6;++n){
        std::vector<Edge> possible;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)possible.push_back({a,b});
        auto queries=all_queries(n);
        for(unsigned mask=0;mask<(1U<<possible.size());++mask){
            std::vector<Edge> edges;for(unsigned i=0;i<possible.size();++i)if(mask>>i&1)edges.push_back(possible[i]);
            if(!connected(adjacency(n,edges)))continue;
            verify_batch(n,edges,queries,true);++small_graphs;source_graphs+=n>=2;
        }
    }
    need(source_graphs==27475&&source_queries==8527158,"ALL connected simple graphs N2..6 and ALL valid source queries");
}
void randomized(){
    std::mt19937 rng(20180903);
    for(int test=0;test<300;++test){
        const int n=2+int(rng()%199);std::vector<Edge> edges;std::set<Edge> used;
        auto add=[&](int a,int b){if(a>b)std::swap(a,b);if(a!=b&&used.emplace(a,b).second)edges.emplace_back(a,b);};
        for(int v=1;v<n;++v)add(v,int(rng()%v));
        for(int edge=0;edge<3*n;++edge)add(int(rng()%n),int(rng()%n));
        std::vector<Query> queries;
        for(int i=0;i<400;++i){
            int l=int(rng()%n),r=l+int(rng()%(n-l));queries.push_back({l+int(rng()%(n-l)),int(rng()%(r+1)),l,r});
        }
        std::shuffle(edges.begin(),edges.end(),rng);for(auto& [a,b]:edges)if(rng()%2)std::swap(a,b);
        verify_batch(n,edges,queries,false);
        const auto original=threshold_component_intersection_counts(n,edges,queries);
        std::reverse(edges.begin(),edges.end());for(auto& [a,b]:edges)std::swap(a,b);
        need(threshold_component_intersection_counts(n,edges,queries)==original,"different neighbour orders and edge orientations preserve point correspondence");
        std::reverse(queries.begin(),queries.end());auto reversed=original;std::reverse(reversed.begin(),reversed.end());
        need(threshold_component_intersection_counts(n,edges,queries)==reversed,"query permutations and repeated thresholds preserve order");
        ++random_graphs;
    }
}
// Maximum-size shuffled line oracle: independent static RMQ, then binary search
// the contiguous path positions whose labels satisfy each form's restriction.
struct PathOracle {
    int n;std::vector<int> position,logs;std::vector<std::vector<int>> low,high;
    explicit PathOracle(const std::vector<int>& line):n(int(line.size())),position(n),logs(n+1),low(1,line),high(1,line){
        for(int i=0;i<n;++i)position[line[i]]=i;
        for(int i=2;i<=n;++i)logs[i]=logs[i/2]+1;
        for(int level=1;(1<<level)<=n;++level){
            int length=n-(1<<level)+1,half=1<<(level-1);low.emplace_back(length);high.emplace_back(length);
            for(int i=0;i<length;++i){low[level][i]=std::min(low[level-1][i],low[level-1][i+half]);high[level][i]=std::max(high[level-1][i],high[level-1][i+half]);}
        }
    }
    bool allowed(int first,int last,int threshold,bool lower)const{
        int level=logs[last-first],second=last-(1<<level);
        return lower?std::min(low[level][first],low[level][second])>=threshold:
                     std::max(high[level][first],high[level][second])<=threshold;
    }
    std::pair<int,int> component(int vertex,int threshold,bool lower)const{
        int p=position[vertex],lo=0,hi=p;
        while(lo<hi){int mid=(lo+hi)/2;if(allowed(mid,p+1,threshold,lower))hi=mid;else lo=mid+1;}
        int first=lo;lo=p+1;hi=n;
        while(lo<hi){int mid=lo+(hi-lo+1)/2;if(allowed(p,mid,threshold,lower))lo=mid;else hi=mid-1;}
        return {first,lo};
    }
    int answer(Query q)const{
        auto a=component(q.start,q.lower,true),b=component(q.goal,q.upper,false);
        return std::max(0,std::min(a.second,b.second)-std::max(a.first,b.first));
    }
};
void maximum(){
    constexpr int n=200000;std::mt19937 rng(1232018);
    std::vector<Query> queries;queries.reserve(n);
    for(int i=0;i<n;++i){
        int l=int(rng()%n),r=l+int(rng()%(n-l)),s=l+int(rng()%(n-l)),e=int(rng()%(r+1));
        if(i%8==0){l=0;r=n-1;} // every endpoint and full inclusion
        if(i%8==1){l=int(rng()%n);r=l;s=l+int(rng()%(n-l));e=int(rng()%(l+1));}
        if(i%8==2){l=0;r=0;s=n-1;e=0;}
        if(i%8==3){l=n-1;r=n-1;s=n-1;e=0;}
        if(i%8==4)s=l;
        if(i%8==5)e=r;
        if(i%8==6){l=0;r=n-1;s=n-1;e=0;}
        if(s==e){if(s+1<n)++s;else if(e>0)--e;}
        queries.push_back({s,e,l,r});
    }
    for(int kind=0;kind<5;++kind){
        std::vector<Edge> edges;std::vector<int> line;
        if(kind==0||kind==3||kind==4){
            line.resize(n);std::iota(line.begin(),line.end(),0);if(kind==4)std::shuffle(line.begin(),line.end(),rng);
            for(int i=1;i<n;++i)edges.push_back({line[i-1],line[i]});
            if(kind==3){for(int i=2;i<n;++i)edges.push_back({i-2,i});for(int i=0;i<3;++i)edges.push_back({i,i+3});}
        }else {int center=kind==1?0:n-1;for(int v=0;v<n;++v)if(v!=center)edges.emplace_back(center,v);}
        need(edges.size()==std::size_t(kind==3?400000:n-1),"maximum original N/M executed");
        auto counts=threshold_component_intersection_counts(n,edges,queries);
        auto flags=threshold_switch_reachability(n,edges,queries);
        std::vector<int> expected;
        if(kind==4){PathOracle independent(line);expected.reserve(n);for(auto q:queries)expected.push_back(independent.answer(q));}
        for(int i=0;i<n;++i){const auto q=queries[i];int want;
            if(kind==0||kind==3)want=q.upper-q.lower+1;
            else if(kind==1)want=q.lower==0?q.upper+1:int(q.start<=q.upper);
            else if(kind==2)want=q.upper==n-1?n-q.lower:int(q.goal>=q.lower);
            else want=expected[i];
            need(counts[i]==want&&flags[i]==int(want>0),"maximum source queries match closed form or independent line RMQ");
            absorb(counts[i]);++maximum_queries;
        }
        ++maximum_cases;
    }
    // RMQ path oracle is itself checked against direct two-form / component BFS.
    for(int test=0;test<30;++test){
        std::vector<int> line(2+int(rng()%35));std::iota(line.begin(),line.end(),0);std::shuffle(line.begin(),line.end(),rng);
        std::vector<Edge> edges;for(int i=1;i<int(line.size());++i)edges.emplace_back(line[i-1],line[i]);
        PathOracle oracle(line);auto graph=adjacency(int(line.size()),edges);
        for(auto q:all_queries(int(line.size()))){need(oracle.answer(q)==component_intersection_bfs(graph,q),"RMQ oracle separately matches literal BFS");}
    }
}
void reject(int n,const std::vector<Edge>& edges,const std::vector<Query>& queries){
    for(int api=0;api<2;++api){bool caught=false;
        try{if(api==0)(void)threshold_component_intersection_counts(n,edges,queries);else(void)threshold_switch_reachability(n,edges,queries);}
        catch(const std::invalid_argument&){caught=true;}
        need(caught,"invalid public API input rejected");++invalid_cases;
    }
}
void boundaries(){
    const std::vector<Edge> example={{5,1},{1,2},{1,3},{3,4},{3,0},{5,2}};
    const std::vector<Query> example_queries={{4,2,1,2},{4,2,2,2},{5,4,3,4}};
    need(threshold_switch_reachability(6,example,example_queries)==std::vector<int>({1,0,0}),"original example");
    verify_batch(6,example,example_queries,false);
    need(threshold_component_intersection_counts(1,{},{{0,0,0,0}})==std::vector<int>{1},"N1 singleton zero-edge switch extension");
    need(threshold_switch_reachability(1,{},{}).empty(),"empty batch on valid singleton");
    need(threshold_component_intersection_counts(2,{{0,1}},{}).empty(),"empty batch still validates connected graph");
    for(int n:{INT_MIN,-1,0,200001,INT_MAX})reject(n,{},{});
    std::vector<Edge> too_many_edges;
    for(int i=1;i<200000;++i)too_many_edges.emplace_back(i-1,i);
    for(int i=2;i<200000;++i)too_many_edges.emplace_back(i-2,i);
    for(int i=0;i<4;++i)too_many_edges.emplace_back(i,i+3);
    reject(200000,too_many_edges,{}); // simple connected, only M exceeds the contract
    reject(1,{},std::vector<Query>(200001,{0,0,0,0}));
    for(auto edge:std::vector<Edge>{{0,0},{-1,0},{0,-1},{2,0},{0,2},{INT_MIN,0},{INT_MAX,0}})reject(2,{edge},{});
    reject(2,{{0,1},{0,1}},{});reject(2,{{0,1},{1,0}},{});
    reject(2,{},{});reject(3,{{0,1}},{{0,1,0,1}});
    const std::vector<Edge> path={{0,1},{1,2}};
    for(auto q:std::vector<Query>{{0,1,-1,2},{0,1,0,3},{0,1,2,1},{-1,1,0,2},{3,1,0,2},{0,-1,0,2},{0,3,0,2},{0,1,1,2},{2,2,0,1},{0,1,INT_MIN,2},{0,1,0,INT_MAX},{0,1,INT_MAX,2},{0,1,0,INT_MIN}})reject(3,path,{q});
    const auto a=threshold_component_intersection_counts(6,example,example_queries);
    for(int round=0;round<50;++round){
        need(threshold_component_intersection_counts(2,{{0,1}},{{1,0,0,1}})==std::vector<int>{2},"fresh graph state");
        need(threshold_component_intersection_counts(6,example,example_queries)==a,"repeated batch has no persistent activation or sweep state");
    }
}
int main(){
    const auto start=std::chrono::steady_clock::now();exhaustive();randomized();boundaries();maximum();
    need(maximum_cases==5&&maximum_queries==1000000,"all maximum scales executed");
    std::cout<<"{\"checks\":"<<checks<<",\"smallGraphs\":"<<small_graphs<<",\"sourceGraphs\":"<<source_graphs
      <<",\"sourceQueries\":"<<source_queries<<",\"allSmallQueries\":"<<all_small_queries
      <<",\"randomGraphs\":"<<random_graphs<<",\"randomQueries\":"<<random_queries
      <<",\"maximumCases\":"<<maximum_cases<<",\"maximumQueries\":"<<maximum_queries
      <<",\"invalidCases\":"<<invalid_cases<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
      <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-werewolf-build-') as tmp:
    source=Path(tmp)/'test.cpp';binary=Path(tmp)/'test';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)]
    if Path('/usr/bin/time').exists():command=['/usr/bin/time','-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout)
    match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();report['sanitized']='--sanitize' in sys.argv
    print(json.dumps(report,ensure_ascii=False))
