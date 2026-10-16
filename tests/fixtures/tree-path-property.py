"""Compare the ten published tree/path snippets with independent small models."""
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
vector<vector<int>> random_tree(int n,mt19937_64& rng){vector<vector<int>> g(n);for(int v=1;v<n;++v){int p=rng()%v;g[v].push_back(p);g[p].push_back(v);}return g;}
vector<vector<int>> chain_tree(int n){vector<vector<int>> g(n);for(int v=1;v<n;++v){g[v].push_back(v-1);g[v-1].push_back(v);}return g;}
vector<int> model_parent(const vector<vector<int>>& g,int root){vector<int> p(g.size(),-1),q{root};p[root]=root;for(int i=0;i<int(q.size());++i)for(int u:g[q[i]])if(p[u]==-1){p[u]=q[i];q.push_back(u);}return p;}
vector<int> model_path(const vector<vector<int>>& g,int a,int b){auto p=model_parent(g,a);vector<int> out{b};while(out.back()!=a)out.push_back(p[out.back()]);reverse(out.begin(),out.end());return out;}
bool model_ancestor(const vector<int>& p,int v,int x){while(x!=v && x!=p[x])x=p[x];return x==v;}
int model_lca(const vector<int>& p,int a,int b){vector<char> seen(p.size());while(true){seen[a]=1;if(a==p[a])break;a=p[a];}while(!seen[b])b=p[b];return b;}
int main(){using namespace tested;mt19937_64 rng(342600916);
'''
CASES={
 'tree-path-edge-difference':r'''
    for(int trial=0;trial<700;++trial){int n=1+rng()%35,root=rng()%n;auto g=random_tree(n,rng);auto parent=model_parent(g,root);vector<tuple<int,int,long long>> paths;vector<long long> expected(n);
        for(int q=0;q<200;++q){int a=rng()%n,b=rng()%n;long long w=int(rng()%15)-7;paths.push_back({a,b,w});auto path=model_path(g,a,b);for(int j=1;j<int(path.size());++j){int u=path[j-1],v=path[j];int child=parent[u]==v?u:v;expected[child]+=w;}}
        assert(edge_path_totals(g,paths,root)==expected);
        assert(edge_path_totals(g,{},root)==vector<long long>(n));
    }
    int n=200000;auto g=chain_tree(n);auto answer=edge_path_totals(g,{{0,n-1,1000000000},{n-1,0,-2},{n/2,n/2,99}});assert(answer[0]==0);for(int v=1;v<n;++v)assert(answer[v]==999999998);
 ''',
 'tree-path-vertex-difference':r'''
    for(int trial=0;trial<700;++trial){int n=1+rng()%35,root=rng()%n;auto g=random_tree(n,rng);vector<tuple<int,int,long long>> paths;vector<long long> expected(n);
        for(int q=0;q<200;++q){int a=rng()%n,b=rng()%n;long long w=int(rng()%15)-7;paths.push_back({a,b,w});for(int v:model_path(g,a,b))expected[v]+=w;}
        assert(vertex_path_totals(g,paths,root)==expected);
        assert(vertex_path_totals(g,{},root)==vector<long long>(n));
    }
    int n=200000;auto g=chain_tree(n);auto answer=vertex_path_totals(g,{{0,n-1,1000000000},{n-1,0,-2},{n/2,n/2,99}});for(int v=0;v<n;++v)assert(answer[v]==999999998+(v==n/2?99:0));
 ''',
 'tree-path-kth-persistent':r'''
    for(int trial=0;trial<200;++trial){int n=1+rng()%24,root=rng()%n;auto g=random_tree(n,rng);vector<long long> value(n);for(auto& v:value)v=int(rng()%13)-6;PathKth query(g,value,root);
        for(int a=0;a<n;++a)for(int b=0;b<n;++b){vector<long long> list;for(int v:model_path(g,a,b))list.push_back(value[v]);sort(list.begin(),list.end());for(int k=1;k<=int(list.size());++k)assert(query.kth(a,b,k)==list[k-1]);}
        bool thrown=false;try{query.kth(0,0,2);}catch(const out_of_range&){thrown=true;}assert(thrown);
        thrown=false;try{query.kth(0,0,0);}catch(const out_of_range&){thrown=true;}assert(thrown);
    }
    int n=200000;auto g=chain_tree(n);vector<long long> values(n);iota(values.begin(),values.end(),-100000LL);PathKth query(g,values,n-1);assert(query.kth(0,n-1,1)==-100000 && query.kth(0,n-1,n)==99999 && query.kth(100000,100001,2)==1);
    PathKth equal({{}},{LLONG_MIN});assert(equal.kth(0,0,1)==LLONG_MIN);
 ''',
 'centroid-nearest-marked':r'''
    for(int trial=0;trial<350;++trial){int n=1+rng()%80;auto g=random_tree(n,rng);NearestMarked query(g);vector<char> marked(n);assert(query.query(rng()%n)==-1);
        for(int q=0;q<300;++q){int v=rng()%n;if(rng()%3==0){query.mark(v);query.mark(v);marked[v]=1;}else{int best=n+1;for(int u=0;u<n;++u)if(marked[u])best=min(best,int(model_path(g,v,u).size())-1);assert(query.query(v)==(best==n+1?-1:best));}}
    }
    int n=200000;NearestMarked query(chain_tree(n));assert(query.query(0)==-1);query.mark(0);assert(query.query(n-1)==n-1);query.mark(n-1);for(int v=0;v<n;v+=997)assert(query.query(v)==min(v,n-1-v));query.mark(n/2);assert(query.query(n/2)==0);
 ''',
 'subtree-mode-sack':r'''
    for(int trial=0;trial<1000;++trial){int n=1+rng()%80;auto g=random_tree(n,rng);auto parent=model_parent(g,0);vector<long long> color(n),expected(n);for(auto& c:color)c=int(rng()%17)-8;
        for(int v=0;v<n;++v){map<long long,int> frequency;int maximum=0;for(int u=0;u<n;++u)if(model_ancestor(parent,v,u))maximum=max(maximum,++frequency[color[u]]);for(auto [c,f]:frequency)if(f==maximum)expected[v]+=c;}
        assert(subtree_mode_sums(g,color)==expected);
    }
    int n=200000;auto answer=subtree_mode_sums(chain_tree(n),vector<long long>(n,-7));for(auto x:answer)assert(x==-7);
    vector<vector<int>> star(n);vector<long long> colors(n);for(int v=0;v<n;++v)colors[v]=v+1;for(int v=1;v<n;++v){star[0].push_back(v);star[v].push_back(0);}answer=subtree_mode_sums(star,colors);assert(answer[0]==1LL*n*(n+1)/2);for(int v=1;v<n;++v)assert(answer[v]==v+1);
 ''',
 'tree-path-directed-composition':r'''
    for(int trial=0;trial<500;++trial){int n=1+rng()%70;auto g=random_tree(n,rng);vector<Affine> functions(n);for(auto& f:functions)f={static_cast<long long>(rng()%MOD),static_cast<long long>(rng()%MOD)};PathComposition query(g,functions);
        for(int q=0;q<300;++q){if(rng()%4==0){int v=rng()%n;functions[v]={static_cast<long long>(rng()%MOD),static_cast<long long>(rng()%MOD)};query.set(v,functions[v]);}else{int a=rng()%n,b=rng()%n;long long x=rng()%MOD,expected=x;for(int v:model_path(g,a,b))expected=functions[v].apply(expected);assert(query.path(a,b).apply(x)==expected);}}
    }
    PathComposition small(chain_tree(2),{{2,1},{3,4}});assert(small.path(0,1).apply(7)==49 && small.path(1,0).apply(7)==51);
    int n=200000;PathComposition query(chain_tree(n),vector<Affine>(n,{1,1}));assert(query.path(0,n-1).apply(0)==n && query.path(n-1,0).apply(1)==n+1);query.set(0,{0,0});assert(query.path(n-1,0).apply(123)==0 && query.path(0,n-1).apply(123)==n-1);
 ''',
 'reroot-subtree-complement':r'''
    for(int trial=0;trial<300;++trial){int n=1+rng()%40;auto g=random_tree(n,rng);vector<long long> values(n);for(auto& x:values)x=int(rng()%51)-25;RootChangingSubtree query(g,values);int root=0;
        for(int q=0;q<300;++q){int type=rng()%4,v=rng()%n;if(type==0){root=v;query.set_root(root);}auto p=model_parent(g,root);if(type==1){long long x=int(rng()%21)-10;query.add_subtree(v,x);for(int u=0;u<n;++u)if(model_ancestor(p,v,u))values[u]+=x;}else if(type==2){int u=rng()%n;long long x=int(rng()%21)-10;int c=model_lca(p,u,v);assert(query.current_lca(u,v)==c);query.add_cover(u,v,x);for(int w=0;w<n;++w)if(model_ancestor(p,c,w))values[w]+=x;}else {__int128 expected=0;vector<char> present(n);for(int u=0;u<n;++u)if(model_ancestor(p,v,u)){expected+=values[u];present[u]=1;}assert(query.sum_subtree(v)==expected);auto fixed=model_parent(g,0);vector<int> dfs;function<void(int)> visit=[&](int a){dfs.push_back(a);for(int b:g[a])if(fixed[b]==a && b!=a)visit(b);};visit(0);vector<char> actual(n);for(auto [l,r]:query.intervals(v))for(int i=l;i<r;++i)actual[dfs[i]]=1;assert(actual==present);}}
    }
    int n=200000;RootChangingSubtree query(chain_tree(n),vector<long long>(n,100000000000000LL));assert(query.sum_subtree(0)==(__int128)n*100000000000000LL);query.set_root(n-1);assert(query.sum_subtree(0)==100000000000000LL);query.add_subtree(n/2,3);assert(query.sum_subtree(n-1)==(__int128)n*100000000000000LL+3LL*(n/2+1));assert(query.current_lca(0,n/2)==n/2);
 ''',
 'subtree-path-last-write':r'''
    for(int trial=0;trial<700;++trial){int n=1+rng()%60;auto g=random_tree(n,rng);auto parent=model_parent(g,0);WaterTree query(g);vector<char> value(n);
        for(int q=0;q<300;++q){int v=rng()%n;if(rng()%2){query.fill(v);for(int u=0;u<n;++u)if(model_ancestor(parent,v,u))value[u]=1;}else{query.empty_ancestors(v);for(int u:model_path(g,0,v))value[u]=0;}for(int u=0;u<n;++u)assert(query.value(u)==bool(value[u]));}
    }
    int n=500000;WaterTree query(chain_tree(n));query.fill(0);query.empty_ancestors(n/2);assert(!query.value(0) && !query.value(n/2) && query.value(n/2+1) && query.value(n-1));query.fill(n-1);query.empty_ancestors(n-1);assert(!query.value(n-1));query.fill(0);for(int v=0;v<n;v+=999)assert(query.value(v));
 ''',
 'shortest-tight-dag-statistics':r'''
    for(int trial=0;trial<1800;++trial){int n=1+rng()%8,s=rng()%n;vector<vector<Edge>> g(n);for(int e=0;e<int(rng()%28);++e)g[rng()%n].push_back({int(rng()%n),1+static_cast<long long>(rng()%8)});long long mod=2+rng()%19;auto actual=shortest_statistics(g,s,mod);vector<long long> dist(n,INF),ways(n);vector<int> minimum(n,INT_MAX),maximum(n,-1);vector<char> seen(n);
        function<void(int,long long,int)> walk=[&](int v,long long d,int k){if(d<dist[v]){dist[v]=d;ways[v]=1;minimum[v]=maximum[v]=k;}else if(d==dist[v]){ways[v]=(ways[v]+1)%mod;minimum[v]=min(minimum[v],k);maximum[v]=max(maximum[v],k);}seen[v]=1;for(auto e:g[v])if(!seen[e.to])walk(e.to,d+e.weight,k+1);seen[v]=0;};walk(s,0,0);assert(actual.distance==dist && actual.ways==ways && actual.fewest==minimum && actual.most==maximum);
    }
    bool thrown=false;try{shortest_statistics({{{0,0}}},0);}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=100000;vector<vector<Edge>> g(n);long long ways=1;for(int v=0;v+1<n;++v){g[v]={{v+1,1000000000},{v+1,1000000000}};ways=ways*2%1000000007;}auto a=shortest_statistics(g,0);assert(a.distance.back()==1LL*(n-1)*1000000000 && a.ways.back()==ways && a.fewest.back()==n-1 && a.most.back()==n-1);
 ''',
 'shortest-one-edge-discount':r'''
    for(int trial=0;trial<3000;++trial){int n=1+rng()%9,s=rng()%n,t=rng()%n;vector<Flight> edges;for(int e=0;e<int(rng()%35);++e)edges.push_back({int(rng()%n),int(rng()%n),static_cast<long long>(rng()%11)});vector<long long> d(2*n,INF);d[s]=0;
        for(int k=0;k<2*n;++k){bool changed=false;auto relax=[&](int u,int v,long long w){if(d[u]!=INF && d[u]+w<d[v]){d[v]=d[u]+w;changed=true;}};for(auto e:edges){relax(e.from,e.to,e.cost);relax(e.from,n+e.to,e.cost/2);relax(n+e.from,n+e.to,e.cost);}if(!changed)break;}
        auto answer=one_discount(n,edges,s,t);assert(bool(answer)==(d[n+t]!=INF));if(answer)assert(*answer==d[n+t]);
    }
    assert(!one_discount(1,{},0,0));assert(one_discount(1,{{0,0,9}},0,0)==optional<long long>(4));assert(one_discount(2,{{0,1,0}},0,1)==optional<long long>(0));
    bool thrown=false;try{one_discount(1,{{0,0,-1}},0,0);}catch(const invalid_argument&){thrown=true;}assert(thrown);
    int n=100000;vector<Flight> edges;for(int v=0;v+1<n;++v)edges.push_back({v,v+1,1000000000});assert(one_discount(n,edges,0,n-1)==optional<long long>(1LL*(n-1)*1000000000-500000000));
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
    with tempfile.TemporaryDirectory(prefix='tree-path-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=45)
        return slug,executed.returncode==0,executed.stderr
if __name__=='__main__':
    rows=json.loads((ROOT/'data/tree-path-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
