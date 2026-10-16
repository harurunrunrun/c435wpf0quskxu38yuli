"""Extract published code, then compare it with independent tree/graph models."""
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
vector<pair<int,int>> random_tree(int n,mt19937_64& rng){vector<pair<int,int>> e;for(int v=1;v<n;++v)e.push_back({v,int(rng()%v)});shuffle(e.begin(),e.end(),rng);return e;}
vector<vector<int>> adjacency(int n,const vector<pair<int,int>>& edges){vector<vector<int>>g(n);for(auto [u,v]:edges){g[u].push_back(v);g[v].push_back(u);}return g;}
vector<vector<long long>> all_distances(int n,const vector<tuple<int,int,long long>>& edges){vector<vector<pair<int,long long>>>g(n);for(auto[u,v,w]:edges){g[u].push_back({v,w});g[v].push_back({u,w});}vector<vector<long long>>d(n,vector<long long>(n));for(int s=0;s<n;++s){vector<int>seen(n),queue{s};seen[s]=1;for(size_t i=0;i<queue.size();++i){int v=queue[i];for(auto[u,w]:g[v])if(!seen[u]){seen[u]=1;d[s][u]=d[s][v]+w;queue.push_back(u);}}}return d;}
int brute_separation(const vector<vector<int>>&g,const vector<int>&selected){int n=g.size();unsigned mark=0;for(int v:selected)mark|=1u<<v;int best=n+1;for(unsigned removed=0;removed<(1u<<n);++removed){if(removed&mark)continue;int cost=popcount(removed);if(cost>=best)continue;unsigned seen=removed;bool good=true;for(int s=0;s<n;++s)if(!(seen>>s&1)){vector<int> queue{s};seen|=1u<<s;int count=0;for(size_t i=0;i<queue.size();++i){int v=queue[i];count+=(mark>>v)&1;for(int u:g[v])if(!(seen>>u&1)){seen|=1u<<u;queue.push_back(u);}}if(count>1){good=false;break;}}if(good)best=cost;}return best==n+1?-1:best;}
long long brute_mst_completions(int n,int upper,const vector<tuple<int,int,long long>>&tree){vector<pair<int,int>> pairs;vector<int>weights;long long target=0;for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){pairs.push_back({u,v});int fixed=0;for(auto[a,b,w]:tree)if((a==u&&b==v)||(a==v&&b==u))fixed=w;weights.push_back(fixed);target+=fixed;}vector<int>free;for(int i=0;i<int(pairs.size());++i)if(weights[i]==0)free.push_back(i);long long count=0;auto evaluate=[&](){long long minimum=LLONG_MAX;int ways=0;for(unsigned mask=0;mask<(1u<<pairs.size());++mask)if(popcount(mask)==n-1){vector<int>parent(n);iota(parent.begin(),parent.end(),0);auto find=[&](int v){while(parent[v]!=v)v=parent[v];return v;};bool valid=true;long long sum=0;for(int i=0;i<int(pairs.size());++i)if(mask>>i&1){if(weights[i]==0){valid=false;break;}auto[u,v]=pairs[i];u=find(u);v=find(v);if(u==v){valid=false;break;}parent[u]=v;sum+=weights[i];}if(valid){if(sum<minimum){minimum=sum;ways=1;}else if(sum==minimum)++ways;}}if(minimum==target&&ways==1)++count;};auto assign=[&](auto&&self,int k)->void{if(k==int(free.size())){evaluate();return;}for(int w=0;w<=upper;++w){weights[free[k]]=w;self(self,k+1);}};assign(assign,0);return count;}
uint64_t brute_colorings(int n,const vector<pair<int,int>>&edges,const vector<pair<int,int>>&paths){vector<vector<pair<int,int>>>g(n);for(int i=0;i<n-1;++i){auto[u,v]=edges[i];g[u].push_back({v,i});g[v].push_back({u,i});}vector<vector<int>>requirements;for(auto[s,t]:paths){vector<int>prev(n,-1),via(n,-1),queue{s};prev[s]=s;for(size_t i=0;i<queue.size();++i)for(auto[u,e]:g[queue[i]])if(prev[u]==-1){prev[u]=queue[i];via[u]=e;queue.push_back(u);}vector<int>path;for(int v=t;v!=s;v=prev[v])path.push_back(via[v]);requirements.push_back(path);}uint64_t count=0;for(unsigned color=0;color<(1u<<(n-1));++color){bool valid=true;for(const auto&path:requirements){bool black=false;for(int e:path)black|=(color>>e)&1;if(!black){valid=false;break;}}count+=valid;}return count;}
int main(){using namespace tested;mt19937_64 rng(6131857348152201);
'''
CASES={
'virtual-tree-marked-vertex-separation':r'''
    for(int trial=0;trial<55;++trial){int n=1+rng()%8;auto g=adjacency(n,random_tree(n,rng));MarkedSeparation solver(g,rng()%n);for(unsigned mask=0;mask<(1u<<n);++mask){vector<int>selected;for(int v=0;v<n;++v)if(mask>>v&1)selected.push_back(v);assert(solver.minimum_deletions(selected)==brute_separation(g,selected));if(!selected.empty()){selected.push_back(selected[0]);shuffle(selected.begin(),selected.end(),rng);assert(solver.minimum_deletions(selected)==brute_separation(g,selected));}assert(solver.minimum_deletions({})==0);}}
    for(int trial=0;trial<700;++trial){int n=1+rng()%12;auto g=adjacency(n,random_tree(n,rng));vector<int>selected;for(int v=0;v<n;++v)if(rng()%3==0)selected.push_back(v);MarkedSeparation solver(g);assert(solver.minimum_deletions(selected)==brute_separation(g,selected));}
    int n=100000;vector<pair<int,int>>edges;for(int i=1;i<n;++i)edges.push_back({0,i});auto g=adjacency(n,edges);MarkedSeparation star(g);vector<int>leaves(n-1);iota(leaves.begin(),leaves.end(),1);assert(star.minimum_deletions(leaves)==1);assert(star.minimum_deletions({0,1})==-1);assert(star.minimum_deletions({1})==0);
    edges.clear();for(int i=1;i<n;++i)edges.push_back({i-1,i});MarkedSeparation path(adjacency(n,edges));assert(path.minimum_deletions({0,n-1})==1);assert(path.minimum_deletions({0,1})==-1);assert(path.minimum_deletions({0,n/2,n-1})==2);for(int i=0;i<20000;++i)assert(path.minimum_deletions({i,i+2})==1);
''',
'unique-mst-completion-count':r'''
    assert(count_unique_mst_completions(1,1,{})==1);
    for(int trial=0;trial<160;++trial){int n=2+rng()%3,upper=1+rng()%3;vector<tuple<int,int,long long>>tree;for(auto[u,v]:random_tree(n,rng))tree.push_back({u,v,1+rng()%upper});assert(count_unique_mst_completions(n,upper,tree)==brute_mst_completions(n,upper,tree));reverse(tree.begin(),tree.end());assert(count_unique_mst_completions(n,upper,tree)==brute_mst_completions(n,upper,tree));}
    for(int trial=0;trial<5;++trial){int n=5,upper=2;vector<tuple<int,int,long long>>tree;for(auto[u,v]:random_tree(n,rng))tree.push_back({u,v,1+rng()%upper});assert(count_unique_mst_completions(n,upper,tree)==brute_mst_completions(n,upper,tree));}
    int n=200000;vector<tuple<int,int,long long>>tree;for(int v=1;v<n;++v)tree.push_back({v-1,v,1000000000});assert(count_unique_mst_completions(n,1000000000,tree)==1);for(auto&edge:tree)get<2>(edge)=1;long long exponent=1LL*n*(n-1)/2-(n-1),base=1000000000,result=1,mod=998244353;while(exponent){if(exponent&1)result=result*base%mod;base=base*base%mod;exponent>>=1;}assert(count_unique_mst_completions(n,1000000000,tree)==result);
''',
'weighted-tree-distance-reroot':r'''
    for(int trial=0;trial<1300;++trial){int n=1+rng()%55;vector<tuple<int,int,long long>>edges;for(auto[u,v]:random_tree(n,rng))edges.push_back({u,v,rng()%25});vector<long long>demand(n);for(auto&x:demand)x=rng()%31;auto result=weighted_tree_distance_sums(demand,edges,rng()%n);auto d=all_distances(n,edges);for(int s=0;s<n;++s){__int128 expected=0;for(int t=0;t<n;++t)expected+=(__int128)d[s][t]*demand[t];assert(result[s]==expected);}}
    int n=200000;vector<tuple<int,int,long long>>edges;for(int v=1;v<n;++v)edges.push_back({v-1,v,1000000000});auto result=weighted_tree_distance_sums(vector<long long>(n,1000000000),edges,n/2);for(int v:{0,1,n/2,n-2,n-1}){__int128 sum=((__int128)v*(v+1)+(__int128)(n-1-v)*(n-v))/2;assert(result[v]==sum*1000000000*1000000000);}assert(result[0]>(__int128)LLONG_MAX);
''',
 'tree-path-hitting-inclusion-exclusion':r'''
    for(int trial=0;trial<1300;++trial){int n=1+rng()%10;auto edges=random_tree(n,rng);vector<pair<int,int>>paths;for(int q=rng()%11;q>0;--q)paths.push_back({int(rng()%n),int(rng()%n)});assert(count_path_hit_colorings(n,edges,paths)==brute_colorings(n,edges,paths));}
    int n=64;vector<pair<int,int>>edges,paths;for(int v=1;v<n;++v)edges.push_back({v-1,v});assert(count_path_hit_colorings(n,edges,{})==(uint64_t(1)<<63));for(int v=0;v<20;++v)paths.push_back({v,v+1});assert(count_path_hit_colorings(n,edges,paths)==(uint64_t(1)<<43));fill(paths.begin(),paths.end(),pair{0,63});assert(count_path_hit_colorings(n,edges,paths)==(uint64_t(1)<<63)-1);paths[0]={5,5};assert(count_path_hit_colorings(n,edges,paths)==0);
''',
 'tree-xor-pair-bit-contribution':r'''
    for(int trial=0;trial<1400;++trial){int n=1+rng()%40;vector<tuple<int,int,uint64_t>>edges;vector<vector<pair<int,uint64_t>>>g(n);for(auto[u,v]:random_tree(n,rng)){uint64_t w=rng();edges.push_back({u,v,w});g[u].push_back({v,w});g[v].push_back({u,w});}uint64_t mod=trial%4==0?1:trial%4==1?1000:1000000007;__uint128_t expected=0;for(int s=0;s<n;++s){vector<int>seen(n),queue{s};seen[s]=1;vector<uint64_t>value(n);for(size_t i=0;i<queue.size();++i){int v=queue[i];for(auto[u,w]:g[v])if(!seen[u]){seen[u]=1;value[u]=value[v]^w;queue.push_back(u);}}for(int t=s+1;t<n;++t)expected+=value[t];}assert(tree_xor_pair_sum(n,edges,mod)==expected%mod);}
    assert(tree_xor_pair_sum(2,{{0,1,UINT64_MAX}})==UINT64_MAX%1000000007);int n=200000;vector<tuple<int,int,uint64_t>>edges;for(int v=1;v<n;++v)edges.push_back({0,v,UINT64_MAX});assert(tree_xor_pair_sum(n,edges)==uint64_t((__uint128_t)(n-1)*(UINT64_MAX%1000000007)%1000000007));
''',
 'rooted-tree-leaf-interval-labels':r'''
    for(int trial=0;trial<1300;++trial){int n=1+rng()%65,root=rng()%n;auto g=adjacency(n,random_tree(n,rng));for(auto&adj:g)shuffle(adj.begin(),adj.end(),rng);auto result=leaf_interval_labels(g,root);vector<int>parent(n,-1),queue{root};parent[root]=root;for(size_t i=0;i<queue.size();++i)for(int u:g[queue[i]])if(parent[u]==-1){parent[u]=queue[i];queue.push_back(u);}auto ancestor=[&](int a,int b){while(b!=a&&b!=root)b=parent[b];return a==b;};int leaves=0;for(int v=0;v<n;++v){int children=0;for(int u:g[v])children+=parent[u]==v&&u!=v;leaves+=children==0;assert(1<=result[v].first&&result[v].first<=result[v].second);}int maximum=0;for(auto[l,r]:result){(void)l;maximum=max(maximum,r);}assert(maximum==leaves);for(int a=0;a<n;++a)for(int b=0;b<n;++b){if(ancestor(a,b))assert(result[a].first<=result[b].first&&result[b].second<=result[a].second);if(!ancestor(a,b)&&!ancestor(b,a))assert(result[a].second<result[b].first||result[b].second<result[a].first);}}
    int n=200000;vector<pair<int,int>>edges;for(int v=1;v<n;++v)edges.push_back({v-1,v});auto result=leaf_interval_labels(adjacency(n,edges));for(auto item:result)assert(item==pair(1,1));edges.clear();for(int v=1;v<n;++v)edges.push_back({0,v});result=leaf_interval_labels(adjacency(n,edges));assert(result[0]==pair(1,n-1));set<int>labels;for(int v=1;v<n;++v){assert(result[v].first==result[v].second);labels.insert(result[v].first);}assert(int(labels.size())==n-1);
''',
 'tree-eccentricity-diameter-endpoints':r'''
    for(int trial=0;trial<1700;++trial){int n=1+rng()%65;vector<tuple<int,int,long long>>edges;for(auto[u,v]:random_tree(n,rng))edges.push_back({u,v,rng()%30});auto d=all_distances(n,edges);auto result=tree_eccentricities(n,edges);for(int v=0;v<n;++v)assert(result[v]==*max_element(d[v].begin(),d[v].end()));}
    int n=200000;vector<tuple<int,int,long long>>edges;for(int v=1;v<n;++v)edges.push_back({v-1,v,1000000000});auto result=tree_eccentricities(n,edges);for(int v=0;v<n;++v)assert(result[v]==1000000000LL*max(v,n-1-v));for(auto&edge:edges)get<2>(edge)=0;result=tree_eccentricities(n,edges);for(long long x:result)assert(x==0);
''',
 'tree-target-bonus-excluding-self':r'''
    for(int trial=0;trial<1700;++trial){int n=1+rng()%65;vector<tuple<int,int,long long>>edges;for(auto[u,v]:random_tree(n,rng))edges.push_back({u,v,rng()%30});vector<long long>bonus(n);for(auto&x:bonus)x=int(rng()%101)-50;auto d=all_distances(n,edges);auto result=farthest_target_bonuses(bonus,edges);for(int s=0;s<n;++s){optional<long long> expected;for(int t=0;t<n;++t)if(s!=t){long long value=d[s][t]+bonus[t];if(!expected||value>*expected)expected=value;}assert(result[s]==expected);}}
    assert(farthest_target_bonuses({1000000000,-1000000000},{{0,1,0}})==vector<optional<long long>>({-1000000000,1000000000}));int n=200000;vector<tuple<int,int,long long>>edges;for(int v=1;v<n;++v)edges.push_back({0,v,1000000000});vector<long long>bonus(n,1000000000);auto result=farthest_target_bonuses(bonus,edges);assert(result[0]==optional<long long>(2000000000LL));for(int v=1;v<n;++v)assert(result[v]==optional<long long>(3000000000LL));edges.clear();for(int v=1;v<n;++v)edges.push_back({v-1,v,1000000000});fill(bonus.begin(),bonus.end(),-1000000000);result=farthest_target_bonuses(bonus,edges);for(int v=0;v<n;++v)assert(result[v]==optional<long long>(1000000000LL*max(v,n-1-v)-1000000000));
'''
}
def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='tree-pattern-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr
if __name__=='__main__':
    rows=json.loads((ROOT/'data/tree-pattern-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
