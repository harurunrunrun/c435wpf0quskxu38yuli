#!/usr/bin/env python3
"""Independent review: unit lattice edges + BFS, not intersection contraction."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ARTICLE = Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/skywalk-endpoint-sparse-shortest-path.mdx'
HARNESS = r'''
#include <iostream>
#include <queue>
#include <random>
#include <string>
#include <sys/resource.h>

struct Input { std::vector<int>x,h,l,r,y; };
std::uint64_t checks=0, checksum=0, instances=0, bfs_queries=0;
std::uint64_t raster_vertices=0, raster_edges=0, height_checks=0, insertion_checks=0;
void check(bool yes,const char*why) {++checks;if(!yes)throw std::runtime_error(why);}
void record(long long d){checksum=checksum*1000003ULL+std::uint64_t(d+2);}
long long call(const Input&a,int s,int g){return skywalk_shortest_distance(a.x,a.h,a.l,a.r,a.y,s,g);}

// The exact union of all unit-length lattice edges, including roof dead ends.
// No building/skywalk intersection enumeration and no weighted shortest path.
std::vector<std::vector<int>> raster(const Input&a) {
    const int n=int(a.x.size()), w=a.x.back()+1;
    const int h=*std::max_element(a.h.begin(),a.h.end())+1;
    std::vector<std::vector<int>> adj(w*h);
    auto id=[&](int x,int y){return y*w+x;};
    auto edge=[&](int u,int v){adj[u].push_back(v);adj[v].push_back(u);++raster_edges;};
    for(int i=0;i<n;++i)for(int z=0;z<a.h[i];++z)edge(id(a.x[i],z),id(a.x[i],z+1));
    for(std::size_t j=0;j<a.l.size();++j)
        for(int x=a.x[a.l[j]];x<a.x[a.r[j]];++x)edge(id(x,a.y[j]),id(x+1,a.y[j]));
    raster_vertices+=adj.size();
    std::vector<std::vector<int>> answer(n,std::vector<int>(n));
    for(int s=0;s<n;++s) {
        ++bfs_queries;
        std::vector<int>d(adj.size(),-1);std::queue<int> q;
        d[id(a.x[s],0)]=0;q.push(id(a.x[s],0));
        while(!q.empty()) {
            int u=q.front();q.pop();
            for(int v:adj[u])if(d[v]<0){d[v]=d[u]+1;q.push(v);}
        }
        for(int g=0;g<n;++g)answer[s][g]=d[id(a.x[g],0)];
    }
    return answer;
}
bool can_add(const Input&a,int l,int r,int y) {
    for(std::size_t j=0;j<a.l.size();++j)
        if(a.y[j]==y&&std::max(l,a.l[j])<std::min(r,a.r[j]))return false;
    return true;
}
void verify(const Input&a,bool transformations) {
    ++instances;
    const int n=int(a.x.size());
    const auto want=raster(a);
    for(int s=0;s<n;++s)for(int g=0;g<n;++g){auto d=call(a,s,g);record(d);check(d==want[s][g],"unit lattice BFS");}
    if(!transformations)return;
    // Remove all roof tails, or extend each roof without reaching a new walk.
    for(int mode=0;mode<2;++mode) {
        Input b=a;
        for(int i=0;i<n;++i) {
            int highest=1, next=100;
            for(std::size_t j=0;j<a.l.size();++j)if(a.l[j]<=i&&i<=a.r[j]) {
                if(a.y[j]<=a.h[i])highest=std::max(highest,a.y[j]);
                else next=std::min(next,a.y[j]);
            }
            b.h[i]=mode==0?highest:next-1;
        }
        for(int s=0;s<n;++s)for(int g=0;g<n;++g) {
            ++height_checks;auto d=call(b,s,g);record(d);check(d==want[s][g],"roof tail invariance");
        }
    }
    // Add a fresh building in an existing gap. Its roof reaches only the
    // lowest crossing walk, so it adds one connected dead-end vertical tail.
    int k=1;while(k<n&&a.x[k]-a.x[k-1]<2)++k;
    if(k==n)return;
    const int fresh_x=a.x[k-1]+1;
    int roof=100;
    for(std::size_t j=0;j<a.l.size();++j)
        if(a.l[j]<k&&k<=a.r[j])roof=std::min(roof,a.y[j]);
    if(roof==100)roof=1;
    Input b=a;b.x.insert(b.x.begin()+k,fresh_x);b.h.insert(b.h.begin()+k,roof);
    for(int&v:b.l)if(v>=k)++v;
    for(int&v:b.r)if(v>=k)++v;
    for(int s=0;s<n;++s)for(int g=0;g<n;++g) {
        ++insertion_checks;auto d=call(b,s+(s>=k),g+(g>=k));record(d);
        check(d==want[s][g],"one-contact building insertion");
    }
    // Also independently simulate the changed geometry, not just its API.
    const auto changed=raster(b);
    for(int s=0;s<n;++s)for(int g=0;g<n;++g)
        check(changed[s+(s>=k)][g+(g>=k)]==want[s][g],"insertion oracle invariance");
}
int main() {
    // Exhaust all compatible walk sets on five columns of height two.
    // This goes beyond the author's exhaustive N<=4 scope.
    for(int gaps=0;gaps<4;++gaps) {
        Input a{{0,1,2,3,4},{2,2,2,2,2},{},{},{}};
        for(int i=1;i<5;++i)a.x[i]=a.x[i-1]+1+((gaps>>(i%2))&1);
        std::vector<std::array<int,3>> choices;
        for(int l=0;l<5;++l)for(int r=l+1;r<5;++r)for(int y=1;y<=2;++y)choices.push_back({l,r,y});
        auto recurse=[&](auto&&self,int at)->void {
            if(at==int(choices.size())){verify(a,false);return;}
            self(self,at+1);
            auto [l,r,y]=choices[at];
            if(can_add(a,l,r,y)) {
                a.l.push_back(l);a.r.push_back(r);a.y.push_back(y);
                self(self,at+1);a.l.pop_back();a.r.pop_back();a.y.pop_back();
            }
        };
        recurse(recurse,0);
    }
    std::mt19937 rng(914704221U);
    for(int tc=0;tc<6000;++tc) {
        Input a;int n=1+int(rng()%12);
        for(int i=0;i<n;++i){a.x.push_back(i?a.x.back()+1+int(rng()%3):int(rng()%4));a.h.push_back(1+int(rng()%12));}
        for(int step=0;step<120&&n>1;++step) {
            int l=int(rng()%n),r=int(rng()%n);if(l>r)std::swap(l,r);if(l==r)continue;
            int y=1+int(rng()%std::min(a.h[l],a.h[r]));
            if(can_add(a,l,r,y)){a.l.push_back(l);a.r.push_back(r);a.y.push_back(y);}
        }
        verify(a,true);
    }
    struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"checks\":"<<checks<<",\"instances\":"<<instances
        <<",\"bfsQueries\":"<<bfs_queries<<",\"rasterVertices\":"<<raster_vertices
        <<",\"rasterUndirectedEdges\":"<<raster_edges<<",\"heightInvarianceChecks\":"<<height_checks
        <<",\"buildingInsertionChecks\":"<<insertion_checks<<",\"checksum\":\""<<checksum
        <<"\",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
}
'''

def main():
    text=ARTICLE.read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',text,re.M|re.S)
    assert len(fences)==1
    cpp=fences[0]
    with tempfile.TemporaryDirectory(prefix='flowchartcp-skywalk-independent-') as tmp:
        src=Path(tmp)/'review.cpp'; binary=Path(tmp)/'review'
        src.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True)
        output=json.loads(subprocess.check_output([str(binary)],text=True))
    output.update(cppSha256=hashlib.sha256(cpp.encode()).hexdigest(),oracle='Unit-length raster graph BFS, no intersection compression or weighted Dijkstra',seed=914704221)
    print(json.dumps(output,ensure_ascii=False))

if __name__=='__main__':main()
