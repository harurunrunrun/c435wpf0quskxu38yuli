"""Compile the actual article snippets, then compare to independent small models."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
IDS = [
    'bridge-edge-failure', 'block-cut-path', 'bipartite-parity-constraints',
    'two-sat-forbidden-pairs', 'dsu-potential-differences', 'dijkstra-expanded-resource',
    'dijkstra-range-edges', 'dijkstra-potential-reweight', 'functional-graph-cycle-tail',
    'mst-replacement-edge', 'euler-degree-connectivity', 'zero-one-bfs-supernodes',
]

FIXTURE = r'''
std::mt19937_64 rng(20261014);
constexpr long long INF=std::numeric_limits<long long>::max()/4;
std::vector<int> reached(int n,const std::vector<std::pair<int,int>>& edges,int start,int forbidden=-1,int ignored=-1) {
    std::vector<std::vector<int>> g(n);
    for(int i=0;i<int(edges.size());++i) if(i!=ignored) {
        auto [a,b]=edges[i];if(a==forbidden||b==forbidden) continue;
        g[a].push_back(b);g[b].push_back(a);
    }
    std::vector<int> seen(n);if(start==forbidden) return seen;
    std::vector<int> q{start};seen[start]=1;
    for(int at=0;at<int(q.size());++at) for(int u:g[q[at]]) if(!seen[u]) {seen[u]=1;q.push_back(u);}
    return seen;
}
int components(int n,const std::vector<std::pair<int,int>>& edges,int ignored) {
    std::vector<int> seen(n);int count=0;
    for(int v=0;v<n;++v) if(!seen[v]) {++count;auto x=reached(n,edges,v,-1,ignored);for(int u=0;u<n;++u) seen[u]|=x[u];}
    return count;
}
std::optional<long long> direct_difference(const std::vector<std::vector<std::pair<int,long long>>>& g,int a,int b) {
    std::vector<int> seen(g.size());std::vector<long long> value(g.size());std::vector<int> q{a};seen[a]=1;
    for(int at=0;at<int(q.size());++at) {
        int v=q[at];for(auto [u,w]:g[v]) if(!seen[u]) {seen[u]=1;value[u]=value[v]+w;q.push_back(u);}
    }
    if(!seen[b]) return std::nullopt;
    return value[b];
}
std::vector<long long> explicit_resource(const std::vector<std::vector<t5::ResourceEdge>>& g,int start,long long initial,
    const std::vector<int>& gain,const std::vector<long long>& times,int cap) {
    int n=int(g.size());std::vector<long long> d(n*(cap+1),INF);d[start*(cap+1)+std::min<long long>(initial,cap)]=0;
    for(int pass=0;pass<n*(cap+1);++pass) {
        bool changed=false;
        for(int v=0;v<n;++v) for(int c=0;c<=cap;++c) {
            int from=v*(cap+1)+c;if(d[from]==INF) continue;
            auto relax=[&](int to,long long w) {if(d[to]>d[from]+w) {d[to]=d[from]+w;changed=true;}};
            relax(v*(cap+1)+std::min(cap,c+gain[v]),times[v]);
            for(auto e:g[v]) if(c>=e.consume) relax(e.to*(cap+1)+c-e.consume,e.time);
        }
        if(!changed) break;
    }
    std::vector<long long> answer(n,INF);
    for(int v=0;v<n;++v) for(int c=0;c<=cap;++c) answer[v]=std::min(answer[v],d[v*(cap+1)+c]);
    return answer;
}
std::optional<__int128> exhaustive_tree(int n,const std::vector<std::tuple<int,int,long long>>& edges,int required=-1) {
    std::optional<__int128> best;
    for(int mask=0;mask<(1<<edges.size());++mask) {
        if(std::popcount(static_cast<unsigned>(mask))!=n-1||(required>=0&&!((mask>>required)&1))) continue;
        std::vector<int> p(n);std::iota(p.begin(),p.end(),0);
        auto root=[&](int v) {while(p[v]!=v) v=p[v];return v;};
        bool okay=true;__int128 sum=0;
        for(int i=0;i<int(edges.size());++i) if((mask>>i)&1) {
            auto [a,b,w]=edges[i];a=root(a);b=root(b);if(a==b) {okay=false;break;}
            p[a]=b;sum+=w;
        }
        if(okay&&(!best||sum<*best)) best=sum;
    }
    return best;
}
int main() {
    // Bridge and forbidden-vertex queries: remove the actual edge/vertex and search.
    for(int n=1;n<=8;++n) for(int trial=0;trial<90;++trial) {
        std::vector<std::pair<int,int>> e;int m=int(rng()%20);
        for(int i=0;i<m;++i) e.push_back({rng()%n,rng()%n});
        auto bridge=t0::bridge_flags(n,e);int original=components(n,e,-1);
        for(int i=0;i<m;++i) assert(bridge[i]==(components(n,e,i)>original));
        t1::ForbiddenVertexPaths queries(n,e);
        for(int c=0;c<n;++c) for(int a=0;a<n;++a) {
            auto possible=reached(n,e,a,c);
            for(int b=0;b<n;++b) assert(queries.reachable_without(a,b,c)==bool(possible[b]));
        }
    }
    // Iterative lowlink handles a long chain without requiring the call stack.
    {
        int n=20000;std::vector<std::pair<int,int>> e;
        for(int i=1;i<n;++i) e.push_back({i-1,i});
        auto flags=t0::bridge_flags(n,e);assert(std::all_of(flags.begin(),flags.end(),[](bool b){return b;}));
        t1::ForbiddenVertexPaths q(n,e);assert(!q.reachable_without(0,n-1,n/2));assert(q.reachable_without(1,n-1,0));
    }
    // All two-valued assignments, including self constraints and disconnected parts.
    for(int n=0;n<=8;++n) for(int trial=0;trial<120;++trial) {
        std::vector<std::tuple<int,int,int>> parity;
        std::vector<std::tuple<int,int,int,int>> forbidden;
        t3::ForbiddenPairs sat(n);
        if(n) for(int i=0;i<30;++i) {
            int a=rng()%n,b=rng()%n,x=rng()%2,y=rng()%2;
            int p=x;
            if(trial%2==0) {
                // Preserve the explicit witness color[v]=v%2 in half of the tests.
                p=(a&1)^(b&1);
                if(x==(a&1)&&y==(b&1)) y^=1;
            }
            parity.push_back({a,b,p});forbidden.push_back({a,x,b,y});sat.forbid(a,x,b,y);
        }
        bool parity_ok=false,sat_ok=false;
        for(int mask=0;mask<(1<<n);++mask) {
            bool a=true,b=true;
            for(auto [u,v,p]:parity) if((((mask>>u)^(mask>>v))&1)!=p) a=false;
            for(auto [u,x,v,y]:forbidden) if(((mask>>u)&1)==x&&((mask>>v)&1)==y) b=false;
            parity_ok|=a;sat_ok|=b;
        }
        auto pa=t2::parity_assignment(n,parity);auto assignment=sat.solve();
        assert(bool(pa)==parity_ok);assert(bool(assignment)==sat_ok);
        if(pa) for(auto [u,v,p]:parity) assert(((*pa)[u]^(*pa)[v])==p);
        if(assignment) for(auto [u,x,v,y]:forbidden) assert((*assignment)[u]!=x||(*assignment)[v]!=y);
    }
    // Difference DSU agrees with the graph of accepted equalities, in both signs.
    for(int n=1;n<=12;++n) for(int trial=0;trial<50;++trial) {
        t4::DifferenceDSU dsu(n);std::vector<std::vector<std::pair<int,long long>>> g(n);
        for(int step=0;step<60;++step) {
            int a=rng()%n,b=rng()%n;long long w=static_cast<long long>(rng()%101)-50;
            auto before=direct_difference(g,a,b);bool okay=!before||*before==w;
            assert(dsu.add_constraint(a,b,w)==okay);
            if(okay) {g[a].push_back({b,w});g[b].push_back({a,-w});}
            for(int u=0;u<n;++u) for(int v=0;v<n;++v) assert(dsu.difference(u,v)==direct_difference(g,u,v));
        }
    }
    {
        t4::DifferenceDSU d(4);assert(d.add_constraint(0,1,1000000000000LL));
        assert(d.add_constraint(2,3,-1000000000000LL));assert(d.add_constraint(1,2,7));
        assert(d.difference(0,3)==std::optional<long long>(7));assert(!d.add_constraint(3,0,8));
    }
    // Resource cap: compare to explicit relaxation with a much larger resource range.
    for(int n=1;n<=4;++n) for(int trial=0;trial<100;++trial) {
        std::vector<std::vector<t5::ResourceEdge>> g(n);int a=0;
        for(int i=0;i<12;++i) {
            int u=rng()%n,v=rng()%n,c=rng()%4;long long time=rng()%7;
            g[u].push_back({v,c,time});a=std::max(a,c);
        }
        std::vector<int> gain(n);std::vector<long long> times(n);
        for(int i=0;i<n;++i) {gain[i]=rng()%6;times[i]=rng()%7;}
        long long initial=trial%4==0?1000000000LL:rng()%9;int start=rng()%n;
        auto got=t5::resource_shortest_times(g,start,initial,gain,times);
        auto want=explicit_resource(g,start,initial,gain,times,3*(n-1)*a+12);
        assert(got==want);
    }
    // Range-edge compression versus all actual edges and Floyd-Warshall.
    for(int n=1;n<=8;++n) for(int trial=0;trial<80;++trial) {
        t6::RangeEdgeGraph rg(n);std::vector<std::vector<long long>> d(n,std::vector<long long>(n,INF));
        for(int i=0;i<n;++i) d[i][i]=0;
        for(int step=0;step<35;++step) {
            int type=rng()%3,v=rng()%n,u=rng()%n,l=rng()%(n+1),r=rng()%(n+1);if(l>r) std::swap(l,r);
            long long w=rng()%21;
            if(type==0) {rg.add_edge(v,u,w);d[v][u]=std::min(d[v][u],w);}
            if(type==1) {rg.point_to_range(v,l,r,w);for(int x=l;x<r;++x) d[v][x]=std::min(d[v][x],w);}
            if(type==2) {rg.range_to_point(l,r,v,w);for(int x=l;x<r;++x) d[x][v]=std::min(d[x][v],w);}
        }
        for(int k=0;k<n;++k) for(int i=0;i<n;++i) for(int j=0;j<n;++j)
            if(d[i][k]!=INF&&d[k][j]!=INF) d[i][j]=std::min(d[i][j],d[i][k]+d[k][j]);
        for(int s=0;s<n;++s) assert(rg.distances(s)==d[s]);
    }
    // Negative weights, unreachable negative cycles, loops, and repeated edges.
    for(int n=1;n<=7;++n) for(int trial=0;trial<200;++trial) {
        std::vector<std::tuple<int,int,long long>> e;
        std::vector<std::vector<__int128>> d(n,std::vector<__int128>(n,t7::JOHNSON_INF));
        for(int i=0;i<n;++i) d[i][i]=0;
        int m=rng()%18;
        for(int i=0;i<m;++i) {
            int a=rng()%n,b=rng()%n;long long w=static_cast<long long>(rng()%15)-7;
            e.push_back({a,b,w});d[a][b]=std::min(d[a][b],__int128(w));
        }
        for(int k=0;k<n;++k) for(int i=0;i<n;++i) for(int j=0;j<n;++j)
            if(d[i][k]!=t7::JOHNSON_INF&&d[k][j]!=t7::JOHNSON_INF) d[i][j]=std::min(d[i][j],d[i][k]+d[k][j]);
        bool negative=false;for(int i=0;i<n;++i) negative|=d[i][i]<0;
        auto got=t7::johnson_all_pairs(n,e);assert(bool(got)==!negative);if(got) assert(*got==d);
    }
    {
        auto wide=t7::johnson_all_pairs(3,{{0,1,-8000000000000000000LL},{1,2,-8000000000000000000LL}});
        assert(wide&&(*wide)[0][2]==-__int128(8000000000000000000LL)*2);
        assert(!t7::johnson_all_pairs(3,{{1,2,-2},{2,1,1}}));
    }
    // Every function on up to five vertices, then 64-bit extreme K via doubling.
    for(int n=1;n<=5;++n) {
        int total=1;for(int i=0;i<n;++i) total*=n;
        for(int code=0;code<total;++code) {
            int rest=code;std::vector<int> next(n);for(int i=0;i<n;++i) {next[i]=rest%n;rest/=n;}
            for(int s=0;s<n;++s) {t8::FixedStartWalk walk(next,s);int v=s;for(int k=0;k<=40;++k) {assert(walk.at(k)==v);v=next[v];}}
        }
    }
    for(int trial=0;trial<100;++trial) {
        int n=1+rng()%40;std::vector<int> next(n);for(int& v:next) v=rng()%n;
        std::vector<std::vector<int>> jump(64,next);for(int k=1;k<64;++k) for(int v=0;v<n;++v) jump[k][v]=jump[k-1][jump[k-1][v]];
        for(int s=0;s<n;++s) {
            t8::FixedStartWalk walk(next,s);
            for(std::uint64_t k:{std::uint64_t(0),std::uint64_t(1),std::uint64_t(1000000000000000000ULL),std::numeric_limits<std::uint64_t>::max()}) {
                int v=s;for(int b=0;b<64;++b) if((k>>b)&1) v=jump[b][v];assert(walk.at(k)==v);
            }
        }
    }
    // Force the new edge in every candidate spanning tree, including equal/negative weights.
    for(int n=1;n<=5;++n) for(int trial=0;trial<120;++trial) {
        int m=rng()%9;std::vector<std::tuple<int,int,long long>> e;
        for(int i=0;i<m;++i) e.push_back({rng()%n,rng()%n,static_cast<long long>(rng()%15)-7});
        t9::ForcedEdgeMST mst(n,e);auto base=exhaustive_tree(n,e);assert(mst.connected==bool(base));if(base) assert(mst.total==*base);
        for(int query=0;query<12;++query) {
            int a=rng()%n,b=rng()%n;long long w=static_cast<long long>(rng()%15)-7;
            auto bigger=e;bigger.push_back({a,b,w});auto want=exhaustive_tree(n,bigger,m);
            auto got=mst.forced_cost(a,b,w);
            if(base) assert(got==want);else assert(!got);
        }
    }
    {
        t9::ForcedEdgeMST m(2,{{0,1,std::numeric_limits<long long>::lowest()}});
        auto forced=m.forced_cost(0,1,4);assert(forced&&*forced==4);
        t9::ForcedEdgeMST wide(3,{{0,1,8000000000000000000LL},{1,2,8000000000000000000LL}});
        assert(wide.total==__int128(8000000000000000000LL)*2);
    }
    // A subset DP enumerates all edge-use orders; validate every produced edge occurrence.
    for(int n=1;n<=4;++n) for(int trial=0;trial<120;++trial) {
        int m=rng()%8;std::vector<std::pair<int,int>> e;
        for(int i=0;i<m;++i) e.push_back({rng()%n,rng()%n});
        for(int s=0;s<n;++s) {
            std::vector<std::vector<bool>> dp(1<<m,std::vector<bool>(n));dp[0][s]=true;
            for(int mask=0;mask<(1<<m);++mask) for(int v=0;v<n;++v) if(dp[mask][v])
                for(int i=0;i<m;++i) if(!((mask>>i)&1)&&e[i].first==v) dp[mask|(1<<i)][e[i].second]=true;
            for(int t=0;t<n;++t) {
                auto path=t10::directed_euler_path(n,e,s,t);assert(bool(path)==dp.back()[t]);
                if(path) {
                    assert(path->front()==s&&path->back()==t&&path->size()==e.size()+1);
                    std::vector<bool> used(m);
                    for(int j=0;j<m;++j) {
                        int id=-1;for(int i=0;i<m;++i) if(!used[i]&&e[i]==std::make_pair((*path)[j],(*path)[j+1])) {id=i;break;}
                        assert(id>=0);used[id]=true;
                    }
                }
            }
        }
    }
    assert(!t10::directed_euler_path(4,{{0,1},{2,3},{3,2}},0,1));
    assert(t10::directed_euler_path(1,{{0,0},{0,0}},0,0));
    for(int trial=0;trial<200;++trial) {
        int n=6,start=rng()%n,v=start;std::vector<std::pair<int,int>> e;
        for(int i=0;i<40;++i) {int u=rng()%n;e.push_back({v,u});v=u;}
        std::shuffle(e.begin(),e.end(),rng);
        auto path=t10::directed_euler_path(n,e,start,v);assert(path&&path->size()==e.size()+1);
    }
    // Every pair of members is explicitly linked in the reference graph.
    for(int n=1;n<=9;++n) for(int trial=0;trial<100;++trial) {
        int k=rng()%10;std::vector<std::vector<int>> groups(k);
        std::vector<std::vector<int>> d(n,std::vector<int>(n,t11::GROUP_INF));for(int i=0;i<n;++i) d[i][i]=0;
        for(auto& group:groups) {
            int size=rng()%(n+2);for(int i=0;i<size;++i) group.push_back(rng()%n);
            for(int a:group) for(int b:group) if(a!=b) d[a][b]=1;
        }
        for(int mid=0;mid<n;++mid) for(int i=0;i<n;++i) for(int j=0;j<n;++j) d[i][j]=std::min(d[i][j],d[i][mid]+d[mid][j]);
        for(int s=0;s<n;++s) assert(t11::group_move_distances(n,groups,s)==d[s]);
    }
    std::cout << "graph coverage properties verified: 12 published implementations\n";
}
'''


def main():
    includes = {'#include <random>', '#include <iostream>', '#include <numeric>',
                '#include <bit>', '#include <cstdint>', '#include <cassert>'}
    snippets = []
    for index, identifier in enumerate(IDS):
        content = (ROOT / 'src/content/docs/techniques' / f'{identifier}.mdx').read_text()
        match = re.search(r'^```cpp\s*\n(.*?)^```', content, re.M | re.S)
        if match is None:
            raise AssertionError(f'{identifier}: standalone C++ implementation missing')
        code = match.group(1)
        includes.update(re.findall(r'^#include[^\n]+', code, re.M))
        code = re.sub(r'^#include[^\n]+\n?', '', code, flags=re.M)
        snippets.append(f'namespace t{index} {{\n{code}\n}}')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-graph-coverage-') as directory:
        source = Path(directory) / 'test.cpp'
        binary = Path(directory) / 'test'
        source.write_text('\n'.join(sorted(includes)) + '\n' + '\n'.join(snippets) + '\n' + FIXTURE)
        subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=90)


if __name__ == '__main__':
    main()
