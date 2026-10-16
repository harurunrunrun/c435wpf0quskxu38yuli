"""Exercise the eight actual graph extension article implementations."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
HELPERS=r'''
using namespace std;
vector<char> model_reach(const vector<vector<int>>& g,int source){vector<char> seen(g.size());vector<int> queue{source};seen[source]=1;for(int i=0;i<int(queue.size());++i)for(int u:g[queue[i]])if(!seen[u]){seen[u]=1;queue.push_back(u);}return seen;}
bool model_connected(int n,const vector<pair<int,int>>& edges,int removed=-1){vector<vector<int>> g(n);for(int i=0;i<int(edges.size());++i)if(i!=removed){auto [u,v]=edges[i];g[u].push_back(v);g[v].push_back(u);}auto reach=model_reach(g,0);return find(reach.begin(),reach.end(),0)==reach.end();}
int model_unit_distance(int n,const vector<pair<int,int>>& edges,int source,int target,int removed){vector<int>d(n,-1),queue{source};d[source]=0;for(int i=0;i<int(queue.size());++i)for(int e=0;e<int(edges.size());++e)if(e!=removed && edges[e].first==queue[i] && d[edges[e].second]<0){d[edges[e].second]=d[queue[i]]+1;queue.push_back(edges[e].second);}return d[target];}
vector<vector<long long>> model_floyd(int n,const vector<tuple<int,int,long long>>& edges){const long long LARGE=1000000000000000LL;vector<vector<long long>> d(n,vector<long long>(n,LARGE));for(int i=0;i<n;++i)d[i][i]=0;for(auto [a,b,w]:edges)d[a][b]=d[b][a]=min(d[a][b],w);for(int k=0;k<n;++k)for(int i=0;i<n;++i)for(int j=0;j<n;++j)d[i][j]=min(d[i][j],d[i][k]+d[k][j]);return d;}
int main(){using namespace tested;mt19937_64 rng(213816861599);
'''
CASES={
'dag-reachable-bitsets':r'''
    auto check=[](const vector<vector<int>>& g){auto actual=reachable_node_counts(g);for(int v=0;v<int(g.size());++v){auto seen=model_reach(g,v);assert(actual[v]==count(seen.begin(),seen.end(),char(1)));}};
    for(unsigned mask=0;mask<(1u<<10);++mask){vector<vector<int>> g(5);int bit=0;for(int a=0;a<5;++a)for(int b=a+1;b<5;++b){if(mask>>bit&1)g[a].push_back(b);++bit;}check(g);}
    for(int trial=0;trial<400;++trial){int n=1+rng()%90;vector<int> order(n);iota(order.begin(),order.end(),0);shuffle(order.begin(),order.end(),rng);vector<vector<int>> g(n);for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)if(rng()%9==0){g[order[a]].push_back(order[b]);if(rng()%5==0)g[order[a]].push_back(order[b]);}check(g);}
    bool thrown=false;try{reachable_node_counts({{1},{0}});}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=50000;vector<vector<int>> g(n);for(int v=0;v+1<n;++v)g[v].push_back(v+1);auto answer=reachable_node_counts(g);for(int v=0;v<n;++v)assert(answer[v]==n-v);
''',
'scc-collect-once-reward':r'''
    auto check=[](const vector<vector<int>>& g,const vector<long long>& reward){int n=g.size();vector<char> seen(n*(1<<n));vector<pair<int,int>> queue;for(int v=0;v<n;++v){seen[(1<<v)*n+v]=1;queue.push_back({1<<v,v});}long long best=0;
        for(int i=0;i<int(queue.size());++i){auto [mask,v]=queue[i];long long sum=0;for(int u=0;u<n;++u)if(mask>>u&1)sum+=reward[u];best=max(best,sum);for(int u:g[v]){int next=mask|(1<<u);if(!seen[next*n+u]){seen[next*n+u]=1;queue.push_back({next,u});}}}assert(maximum_once_reward(g,reward)==best);};
    for(unsigned mask=0;mask<(1u<<12);++mask){vector<vector<int>> g(4);int bit=0;for(int a=0;a<4;++a)for(int b=0;b<4;++b)if(a!=b){if(mask>>bit&1)g[a].push_back(b);++bit;}check(g,{1,0,3,2});}
    for(int trial=0;trial<900;++trial){int n=1+rng()%8;vector<vector<int>> g(n);vector<long long> reward(n);for(auto& x:reward)x=rng()%10;for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(rng()%4==0)g[a].push_back(b);check(g,reward);}
    assert(maximum_once_reward({{1},{0}},{LLONG_MAX,LLONG_MAX})==(__int128)LLONG_MAX*2);
    bool thrown=false;try{maximum_once_reward({{}},{-1});}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=200000;vector<vector<int>> g(n);for(int v=0;v+1<n;++v)g[v].push_back(v+1);assert(maximum_once_reward(g,vector<long long>(n,1000000000))==(__int128)n*1000000000);g.back().push_back(0);assert(maximum_once_reward(g,vector<long long>(n,5))==5LL*n);
''',
'unweighted-edge-removal-shortest':r'''
    auto check=[](int n,const vector<pair<int,int>>& edges,int s,int t){auto actual=distances_after_each_edge_removal(n,edges,s,t);assert(actual.size()==edges.size());for(int e=0;e<int(edges.size());++e)assert(actual[e]==model_unit_distance(n,edges,s,t,e));};
    for(unsigned mask=0;mask<(1u<<12);++mask){vector<pair<int,int>> edges;int bit=0;for(int a=0;a<4;++a)for(int b=0;b<4;++b)if(a!=b){if(mask>>bit&1)edges.push_back({a,b});++bit;}check(4,edges,0,3);}
    for(int trial=0;trial<1400;++trial){int n=1+rng()%20,m=rng()%70;vector<pair<int,int>> edges;for(int e=0;e<m;++e)edges.push_back({int(rng()%n),int(rng()%n)});check(n,edges,rng()%n,rng()%n);}
    int n=400;vector<pair<int,int>> edges;for(int v=0;v+1<n;++v)edges.push_back({v,v+1});auto actual=distances_after_each_edge_removal(n,edges,0,n-1);for(auto x:actual)assert(x==-1);
    edges.clear();for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(a!=b)edges.push_back({a,b});actual=distances_after_each_edge_removal(n,edges,0,n-1);for(int e=0;e<int(edges.size());++e)assert(actual[e]==(edges[e]==pair<int,int>{0,n-1}?2:1));
''',
'k-shortest-walk-prefix-cap':r'''
    for(int trial=0;trial<1800;++trial){int n=1+rng()%7,k=1+rng()%4,s=rng()%n,t=rng()%n;vector<vector<WeightedArc>> g(n);for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(rng()%4==0){g[a].push_back({b,1+static_cast<long long>(rng()%4)});if(rng()%5==0)g[a].push_back(g[a].back());}
        vector<vector<int>> dp(201,vector<int>(n));dp[0][s]=1;vector<long long> expected;for(int cost=0;cost<=200;++cost){for(int copies=0;copies<dp[cost][t] && int(expected.size())<k;++copies)expected.push_back(cost);for(int v=0;v<n;++v)for(auto e:g[v])if(cost+e.cost<=200)dp[cost+e.cost][e.to]=min(k,dp[cost+e.cost][e.to]+dp[cost][v]);}assert(k_shortest_walk_costs(g,s,t,k)==expected);
    }
    assert(k_shortest_walk_costs({{{0,3}}},0,0,4)==vector<long long>({0,3,6,9}));
    bool thrown=false;try{k_shortest_walk_costs({{{0,0}}},0,0,1);}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=100000;vector<vector<WeightedArc>> g(n);for(int v=0;v+1<n;++v)g[v].push_back({v+1,1000000000});g.back().push_back({n-1,1});auto answer=k_shortest_walk_costs(g,0,n-1,10);for(int i=0;i<10;++i)assert(answer[i]==1LL*(n-1)*1000000000+i);
''',
'shortest-lexicographic-label-frontier':r'''
    auto check=[](int n,const vector<LabeledEdge>& edges,int s,int t){vector<vector<pair<int,int>>> g(n);vector<vector<int>> plain(n);for(auto e:edges){g[e.a].push_back({e.b,e.label});g[e.b].push_back({e.a,e.label});plain[e.a].push_back(e.b);plain[e.b].push_back(e.a);}vector<int> d(n,-1),q{t};d[t]=0;for(int i=0;i<int(q.size());++i)for(int u:plain[q[i]])if(d[u]<0){d[u]=d[q[i]]+1;q.push_back(u);}optional<vector<int>> expected;vector<int> labels;function<void(int)> walk=[&](int v){if(v==t){if(!expected || labels<*expected)expected=labels;return;}for(auto [u,label]:g[v])if(d[u]==d[v]-1){labels.push_back(label);walk(u);labels.pop_back();}};if(d[s]>=0)walk(s);assert(shortest_lexicographic_labels(n,edges,s,t)==expected);};
    for(int mask=0;mask<729;++mask){int code=mask;vector<LabeledEdge> edges;for(int a=0;a<4;++a)for(int b=a+1;b<4;++b){int type=code%3;code/=3;if(type)edges.push_back({a,b,type});}check(4,edges,0,3);}
    for(int trial=0;trial<1300;++trial){int n=1+rng()%9,m=rng()%25;vector<LabeledEdge> edges;for(int i=0;i<m;++i)edges.push_back({int(rng()%n),int(rng()%n),int(rng()%11)-5});check(n,edges,rng()%n,rng()%n);}
    assert(shortest_lexicographic_labels(4,{{0,1,1},{0,2,1},{1,3,9},{2,3,2}},0,3)==optional<vector<int>>({1,2}));assert(shortest_lexicographic_labels(2,{{0,1,INT_MAX}},0,1)==optional<vector<int>>({INT_MAX}));
    int n=200000;vector<LabeledEdge> edges;for(int v=0;v+1<n;++v)edges.push_back({v,v+1,v%17});auto answer=shortest_lexicographic_labels(n,edges,0,n-1);assert(answer && answer->size()==size_t(n-1));for(int v=0;v+1<n;++v)assert((*answer)[v]==v%17);
''',
'bridgeless-strong-orientation':r'''
    auto verify=[](int n,const vector<pair<int,int>>& original,const vector<pair<int,int>>& directed){assert(original.size()==directed.size());vector<vector<int>> g(n),reverse_graph(n);for(int i=0;i<int(original.size());++i){auto [a,b]=directed[i];assert((directed[i]==original[i] || directed[i]==pair<int,int>{original[i].second,original[i].first}));g[a].push_back(b);reverse_graph[b].push_back(a);}auto f=model_reach(g,0),r=model_reach(reverse_graph,0);assert(find(f.begin(),f.end(),0)==f.end() && find(r.begin(),r.end(),0)==r.end());};
    for(unsigned mask=0;mask<(1u<<10);++mask){vector<pair<int,int>> edges;int bit=0;for(int a=0;a<5;++a)for(int b=a+1;b<5;++b){if(mask>>bit&1)edges.push_back({a,b});++bit;}bool possible=false;for(unsigned direction=0;direction<(1u<<edges.size());++direction){vector<vector<int>> g(5),r(5);for(int e=0;e<int(edges.size());++e){auto [a,b]=edges[e];if(direction>>e&1)swap(a,b);g[a].push_back(b);r[b].push_back(a);}auto f=model_reach(g,0),back=model_reach(r,0);if(find(f.begin(),f.end(),0)==f.end() && find(back.begin(),back.end(),0)==back.end()){possible=true;break;}}auto answer=strong_orientation(5,edges);assert(bool(answer)==possible);if(answer)verify(5,edges,*answer);}
    for(int trial=0;trial<1100;++trial){int n=1+rng()%12,m=rng()%30;vector<pair<int,int>> edges;for(int e=0;e<m;++e)edges.push_back({int(rng()%n),int(rng()%n)});bool possible=model_connected(n,edges);for(int e=0;e<m && possible;++e)possible=model_connected(n,edges,e);auto answer=strong_orientation(n,edges);assert(bool(answer)==possible);if(answer)verify(n,edges,*answer);}
    assert(strong_orientation(1,{}));assert(strong_orientation(2,{{0,1},{0,1}}));
    int n=200000;vector<pair<int,int>> edges;for(int v=0;v+1<n;++v)edges.push_back({v,v+1});assert(!strong_orientation(n,edges));edges.push_back({n-1,0});auto answer=strong_orientation(n,edges);assert(answer);verify(n,edges,*answer);
''',
'distance-matrix-essential-edges':r'''
    auto check=[](const vector<vector<long long>>& d){int n=d.size();vector<tuple<int,int,long long>> candidates;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)candidates.push_back({a,b,d[a][b]});long long best=LLONG_MAX;for(unsigned mask=0;mask<(1u<<candidates.size());++mask){vector<tuple<int,int,long long>> edges;long long sum=0;for(int e=0;e<int(candidates.size());++e)if(mask>>e&1){edges.push_back(candidates[e]);sum+=get<2>(candidates[e]);}if(sum<best && model_floyd(n,edges)==d)best=sum;}auto answer=restore_minimum_roads(d);assert(answer && answer->total==best && model_floyd(n,answer->edges)==d);};
    for(int encoded=0;encoded<4096;++encoded){int code=encoded;vector<tuple<int,int,long long>> edges;for(int a=0;a<4;++a)for(int b=a+1;b<4;++b){int weight=code%4;code/=4;if(weight)edges.push_back({a,b,weight});}auto d=model_floyd(4,edges);if(d[0][1]<1000000000000000LL && d[0][2]<1000000000000000LL && d[0][3]<1000000000000000LL)check(d);}
    for(int trial=0;trial<100;++trial){vector<tuple<int,int,long long>> edges;for(int a=0;a<5;++a)for(int b=a+1;b<5;++b)edges.push_back({a,b,1+static_cast<long long>(rng()%20)});check(model_floyd(5,edges));}
    assert(!restore_minimum_roads({{0,1,3},{1,0,1},{3,1,0}}));assert(!restore_minimum_roads({{0,0},{0,0}}));assert(!restore_minimum_roads({{1}}));assert(!restore_minimum_roads({{0,1},{2,0}}));
    auto huge=restore_minimum_roads({{0,LLONG_MAX,LLONG_MAX},{LLONG_MAX,0,LLONG_MAX},{LLONG_MAX,LLONG_MAX,0}});assert(huge && huge->total==(__int128)LLONG_MAX*3);
    int n=300;vector<vector<long long>> d(n,vector<long long>(n));for(int a=0;a<n;++a)for(int b=0;b<n;++b)d[a][b]=1LL*abs(a-b)*1000000000;auto answer=restore_minimum_roads(d);assert(answer && answer->total==1LL*(n-1)*1000000000 && answer->edges.size()==size_t(n-1));
''',
'capital-reachability-scc-sources':r'''
    auto check=[](const vector<vector<int>>& g,int source){int n=g.size();vector<pair<int,int>> missing;for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(a!=b && find(g[a].begin(),g[a].end(),b)==g[a].end())missing.push_back({a,b});int best=n;for(unsigned mask=0;mask<(1u<<missing.size());++mask){int count=popcount(mask);if(count>=best)continue;auto next=g;for(int e=0;e<int(missing.size());++e)if(mask>>e&1)next[missing[e].first].push_back(missing[e].second);auto reach=model_reach(next,source);if(find(reach.begin(),reach.end(),0)==reach.end())best=count;}auto extra=minimum_edges_from_start(g,source);assert(int(extra.size())==best);auto next=g;for(auto [a,b]:extra){assert(a==source);next[a].push_back(b);}auto reach=model_reach(next,source);assert(find(reach.begin(),reach.end(),0)==reach.end());};
    for(unsigned mask=0;mask<(1u<<6);++mask){vector<vector<int>> g(3);int bit=0;for(int a=0;a<3;++a)for(int b=0;b<3;++b)if(a!=b){if(mask>>bit&1)g[a].push_back(b);++bit;}for(int s=0;s<3;++s)check(g,s);}
    for(int trial=0;trial<450;++trial){vector<vector<int>> g(4);for(int a=0;a<4;++a)for(int b=0;b<4;++b)if(rng()%3==0)g[a].push_back(b);check(g,rng()%4);}
    int n=200000;vector<vector<int>> g(n);for(int v=0;v+1<n;++v)g[v].push_back(v+1);assert(minimum_edges_from_start(g,0).empty());auto extra=minimum_edges_from_start(g,n-1);assert((extra==vector<pair<int,int>>({{n-1,0}})));g.assign(n,{});extra=minimum_edges_from_start(g,0);assert(extra.size()==size_t(n-1));
'''
}
def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='graph-extension-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr
if __name__=='__main__':
    rows=json.loads((ROOT/'data/graph-extension-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
