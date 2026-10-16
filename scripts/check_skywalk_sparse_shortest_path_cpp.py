#!/usr/bin/env python3
"""Compile the single visible MDX fence; compare against all intersections."""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path

HARNESS = r'''
#include <chrono>
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <queue>
#include <random>
#include <string>
#include <sys/resource.h>

using I64 = long long;
std::uint64_t checks=0, checksum=0, instances=0, literal_nodes=0, literal_arcs=0;
std::uint64_t exhaustive_instances=0, exhaustive_terminal_pairs=0, random_instances=0;
std::uint64_t metamorphic_checks=0, invalid_calls=0;
void require(bool ok,const std::string& message) {
    ++checks;
    if (!ok) throw std::runtime_error(message);
}
void record(I64 value) { checksum=checksum*1000003ULL+std::uint64_t(value+2); }
struct Input { std::vector<int>x,h,l,r,y; };
using EdgeList = std::vector<std::vector<std::pair<int,int>>>;
std::vector<std::vector<I64>> literal(const Input& a) {
    const int n=int(a.x.size()),m=int(a.l.size());
    std::vector<std::vector<int>> levels(n,std::vector<int>{0});
    for(int j=0;j<m;++j) for(int i=a.l[j];i<=a.r[j];++i)
        if(a.h[i]>=a.y[j]) levels[i].push_back(a.y[j]);
    std::vector<int> offset(n+1);
    for(int i=0;i<n;++i) {
        auto& row=levels[i];std::sort(row.begin(),row.end());
        row.erase(std::unique(row.begin(),row.end()),row.end());
        offset[i+1]=offset[i]+int(row.size());
    }
    EdgeList graph(offset[n]);
    auto add=[&](int u,int v,int w){graph[u].push_back({v,w});graph[v].push_back({u,w});};
    for(int i=0;i<n;++i) for(int k=1;k<int(levels[i].size());++k)
        add(offset[i]+k-1,offset[i]+k,levels[i][k]-levels[i][k-1]);
    for(int j=0;j<m;++j) {
        int previous=-1,previous_building=-1;
        for(int i=a.l[j];i<=a.r[j];++i) if(a.h[i]>=a.y[j]) {
            const int at=offset[i]+int(std::lower_bound(levels[i].begin(),levels[i].end(),a.y[j])-levels[i].begin());
            if(previous!=-1) add(previous,at,a.x[i]-a.x[previous_building]);
            previous=at;previous_building=i;
        }
    }
    literal_nodes+=graph.size();for(const auto& row:graph)literal_arcs+=row.size();
    const I64 inf=LLONG_MAX/4;
    std::vector<std::vector<I64>> result(n,std::vector<I64>(n,-1));
    for(int s=0;s<n;++s) {
        std::vector<I64>d(graph.size(),inf);
        std::priority_queue<std::pair<I64,int>,std::vector<std::pair<I64,int>>,std::greater<std::pair<I64,int>>>q;
        d[offset[s]]=0;q.push({0,offset[s]});
        while(!q.empty()) {
            const auto [du,u]=q.top();q.pop();if(du!=d[u])continue;
            for(const auto& [v,w]:graph[u])if(du+w<d[v]){d[v]=du+w;q.push({d[v],v});}
        }
        for(int t=0;t<n;++t)if(d[offset[t]]!=inf)result[s][t]=d[offset[t]];
    }
    return result;
}
I64 call(const Input&a,int s,int g) {
    return skywalk_shortest_distance(a.x,a.h,a.l,a.r,a.y,s,g);
}
void all_pairs(const Input& a,bool original_adapter=false) {
    ++instances;
    const auto expected=literal(a);
    const Input before=a;
    const int n=int(a.x.size());
    for(int s=0;s<n;++s)for(int g=0;g<n;++g) {
        const I64 got=call(a,s,g);record(got);
        require(got==expected[s][g],"literal all-pairs mismatch");
    }
    if(original_adapter)require(min_distance(a.x,a.h,a.l,a.r,a.y,0,n-1)==expected[0][n-1],"original adapter");
    require(a.x==before.x&&a.h==before.h&&a.l==before.l&&a.r==before.r&&a.y==before.y,"inputs unchanged");
}
bool can_add(const Input&a,int l,int r,int y) {
    for(std::size_t j=0;j<a.l.size();++j)
        if(a.y[j]==y&&std::max(l,a.l[j])<std::min(r,a.r[j]))return false;
    return true;
}
void exhaustive() {
    for(int n=1;n<=4;++n) {
        int profiles=1;for(int i=0;i<n;++i)profiles*=3;
        for(int profile=0;profile<profiles;++profile)for(int gaps=0;gaps<(1<<(n-1));++gaps) {
            Input a;int digits=profile;
            for(int i=0;i<n;++i){a.x.push_back(i==0?0:a.x.back()+1+((gaps>>(i-1))&1));a.h.push_back(1+digits%3);digits/=3;}
            std::vector<std::array<int,3>> candidates;
            for(int l=0;l<n;++l)for(int r=l+1;r<n;++r)for(int y=1;y<=std::min(a.h[l],a.h[r]);++y)
                candidates.push_back({l,r,y});
            std::function<void(int)> enumerate=[&](int at) {
                if(at==int(candidates.size())) {
                    ++exhaustive_instances;exhaustive_terminal_pairs+=std::uint64_t(n)*n;
                    all_pairs(a,exhaustive_instances%97==0);return;
                }
                enumerate(at+1);
                const auto [l,r,y]=candidates[at];
                if(can_add(a,l,r,y)){
                    a.l.push_back(l);a.r.push_back(r);a.y.push_back(y);
                    enumerate(at+1);a.l.pop_back();a.r.pop_back();a.y.pop_back();
                }
            };
            enumerate(0);
        }
    }
}
Input reflected(const Input&a) {
    Input b=a;const int n=int(a.x.size());
    for(int i=0;i<n;++i){b.x[i]=a.x.back()-a.x[n-1-i];b.h[i]=a.h[n-1-i];}
    for(std::size_t j=0;j<a.l.size();++j){b.l[j]=n-1-a.r[j];b.r[j]=n-1-a.l[j];}
    return b;
}
void randomized() {
    std::mt19937 rng(6827491);
    for(int rep=0;rep<4000;++rep) {
        const int n=2+int(rng()%11);Input a;
        for(int i=0;i<n;++i){a.x.push_back(i==0?int(rng()%7):a.x.back()+1+int(rng()%11));a.h.push_back(1+int(rng()%9));}
        for(int k=0;k<80;++k){int l=int(rng()%n),r=int(rng()%n);if(l>r)std::swap(l,r);if(l==r)continue;
            const int y=1+int(rng()%std::min(a.h[l],a.h[r]));
            if(can_add(a,l,r,y)){a.l.push_back(l);a.r.push_back(r);a.y.push_back(y);}}
        ++random_instances;all_pairs(a,rep%11==0);
        const auto expected=literal(a);const int s=int(rng()%n),g=int(rng()%n);
        const Input b=reflected(a);require(call(b,n-1-s,n-1-g)==expected[s][g],"reflection");++metamorphic_checks;
        Input c=a;for(int&v:c.x)v=17+v*13;for(int&v:c.h)v*=13;for(int&v:c.y)v*=13;
        const I64 scaled=expected[s][g]<0?-1:13*expected[s][g];
        require(call(c,s,g)==scaled,"translation/scaling");++metamorphic_checks;
        std::reverse(c.l.begin(),c.l.end());std::reverse(c.r.begin(),c.r.end());std::reverse(c.y.begin(),c.y.end());
        require(call(c,s,g)==scaled,"input ordering");++metamorphic_checks;
        bool split=false;
        for(std::size_t j=0;j<a.l.size()&&!split;++j)for(int i=a.l[j]+1;i<a.r[j];++i)if(a.h[i]>=a.y[j]) {
            Input d=a;d.r[j]=i;d.l.push_back(i);d.r.push_back(a.r[j]);d.y.push_back(a.y[j]);
            require(call(d,s,g)==expected[s][g],"geometry-preserving skywalk split");++metamorphic_checks;split=true;break;
        }
    }
}
void examples_and_boundaries() {
    Input a{{0,3,5,7,10,12,14},{8,7,9,7,6,6,9},{0,0,0,2,2,3,4},{1,2,6,3,6,4,6},{1,6,8,1,7,2,5}};
    require(call(a,1,5)==27,"official example 1");all_pairs(a,true);
    Input b{{0,4,5,6,9},{6,6,6,6,6},{3,1,0},{4,3,2},{1,3,6}};
    require(call(b,0,4)==21,"official example 2");all_pairs(b,true);
    // Without the cut at building 2, the upper-middle vertical edge vanishes.
    Input c{{0,1,2,3,4},{10,1,10,1,10},{0,1},{4,3},{10,1}};
    require(call(c,1,0)==23,"short source below a spanning high skywalk");all_pairs(c,true);
    Input d{{0,1,2,3,4,5,6},{10,10,1,10,1,10,10},{0,1,4},{6,2,5},{10,1,1}};
    require(call(d,2,4)==26,"both terminals need outward excursions");all_pairs(d,true);
    Input e{{0,1,2,3},{1,1,1,1},{0,1,2},{1,2,3},{1,1,1}};all_pairs(e,true);
    Input f{{0,1000000000},{1000000000,1000000000},{0},{1},{1000000000}};
    require(call(f,0,1)==3000000000LL,"64-bit distance");all_pairs(f,true);
    Input one{{1000000000},{1},{},{},{}};all_pairs(one,true);
    Input none{{0,1},{1,1},{},{},{}};all_pairs(none,true);
    for(int repeat=0;repeat<30;++repeat){require(call(a,1,5)==27,"repeated independent call");require(call(one,0,0)==0,"single terminal extension");}
}
void invalid() {
    const Input base{{0,2,5},{10,10,10},{0},{2},{3}};
    auto reject=[&](Input a,int s=0,int g=2){bool caught=false;try{(void)call(a,s,g);}catch(const std::invalid_argument&){caught=true;}
        require(caught,"invalid input accepted");++invalid_calls;require(call(base,0,2)==11,"state after invalid");};
    Input a=base;a.x.clear();a.h.clear();reject(a);
    a=base;a.h.pop_back();reject(a);
    a=base;a.r.clear();reject(a);a=base;a.y.push_back(4);reject(a);
    a=base;a.x[1]=0;reject(a);a=base;a.x[1]=6;reject(a);
    a=base;a.x[0]=-1;reject(a);a=base;a.x[2]=1000000001;reject(a);
    a=base;a.h[2]=0;reject(a);a=base;a.h[0]=1000000001;reject(a);
    a=base;a.l[0]=-1;reject(a);a=base;a.r[0]=3;reject(a);
    a=base;a.l[0]=2;reject(a);a=base;a.l[0]=2;a.r[0]=1;reject(a);
    a=base;a.y[0]=0;reject(a);a=base;a.y[0]=11;reject(a);
    a=base;a.l.push_back(0);a.r.push_back(1);a.y.push_back(3);reject(a);
    a=base;a.l.push_back(0);a.r.push_back(2);a.y.push_back(3);reject(a);
    reject(base,-1,2);reject(base,0,3);reject(base,INT_MIN,INT_MAX);
    a=base;a.y[0]=11;reject(a,0,0);
    a=base;a.x.resize(100001);a.h.resize(100001,1);reject(a);
    a=base;a.l.resize(100001,0);a.r.resize(100001,1);a.y.resize(100001,1);reject(a);
}
std::vector<std::tuple<std::string,std::size_t,std::size_t,I64,double>> maximum_results;
void maximum_case(const std::string&name,const Input&a,int s,int g,I64 expected,bool adapter=false) {
    const auto before=std::chrono::steady_clock::now();
    const I64 got=adapter?min_distance(a.x,a.h,a.l,a.r,a.y,s,g):call(a,s,g);
    require(got==expected,"maximum "+name);record(got);
    require(call(a,g,s)==expected,"maximum reversed terminals "+name);
    auto graph=skywalk_detail::build_validated(a.x,a.h,a.l,a.r,a.y,s,g);
    require(graph.head.size()<=12*a.l.size()+2,"sparse vertex bound");
    require(graph.arcs.size()<=36*a.l.size(),"sparse edge bound");
    for(const auto&e:graph.arcs)require(e.to>=0&&std::size_t(e.to)<graph.head.size()&&e.weight>0&&e.weight<=1000000000,"maximum edge bounds");
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count();
    maximum_results.emplace_back(name,graph.head.size(),graph.arcs.size()/2,got,seconds);
}
void maximum() {
    const int n=100000,m=100000,s=n/3,g=2*n/3;
    Input a;for(int i=0;i<n;++i){a.x.push_back(i*10000);a.h.push_back(1000000000);}
    for(int j=0;j<m;++j){a.l.push_back(0);a.r.push_back(n-1);a.y.push_back(j+1);}
    maximum_case("all full spans",a,s,g,I64(a.x[g])-a.x[s]+2);
    for(int j=0;j<m;++j)a.y[j]=999900001+j;
    maximum_case("all high full spans",a,s,g,I64(a.x[g])-a.x[s]+2LL*999900001,true);
    a.l.clear();a.r.clear();a.y.clear();
    I64 vertical=0;int previous=0;
    for(int j=0;j<n-1;++j){const int y=j%2?1000000000:1;a.l.push_back(j);a.r.push_back(j+1);a.y.push_back(y);vertical+=std::llabs(I64(y)-previous);previous=y;}
    vertical+=previous;a.l.push_back(0);a.r.push_back(1);a.y.push_back(2);
    maximum_case("alternating serial chain",a,0,n-1,vertical+a.x.back());
    a.l.clear();a.r.clear();a.y.clear();
    for(int j=0;j<m;++j){const bool right=j>=m/2;a.l.push_back(right?n/2:0);a.r.push_back(right?n-1:n/2-1);a.y.push_back(j%(m/2)+1);}
    maximum_case("disconnected halves",a,0,n-1,-1);
    a.l.clear();a.r.clear();a.y.clear();std::fill(a.h.begin(),a.h.end(),1);
    a.h[0]=a.h[n-1]=a.h[s+1]=1000000000;
    a.l.push_back(s);a.r.push_back(s+1);a.y.push_back(1);
    for(int j=1;j<m;++j){a.l.push_back(0);a.r.push_back(n-1);a.y.push_back(999900001+j);}
    maximum_case("short source under high spans",a,s,n-1,I64(a.x.back())-a.x[s]+2LL*999900002);
    a.l.clear();a.r.clear();a.y.clear();std::fill(a.h.begin(),a.h.end(),1);
    a.h[0]=a.h[n-1]=a.h[s-1]=a.h[s+1]=a.h[g-1]=a.h[g+1]=1000000000;
    a.l={s-1,g};a.r={s,g+1};a.y={1,1};
    for(int j=2;j<m;++j){a.l.push_back(0);a.r.push_back(n-1);a.y.push_back(999900000+j);}
    maximum_case("both short terminal detours",a,s,g,I64(a.x[g])-a.x[s]+40000+2LL*999900002);
    a.l.clear();a.r.clear();a.y.clear();std::fill(a.h.begin(),a.h.end(),1000000000);
    for(int j=0;j<n-1;++j){a.l.push_back(j);a.r.push_back(j+1);a.y.push_back(700000000);}
    a.l.push_back(0);a.r.push_back(1);a.y.push_back(1);
    maximum_case("same-height endpoint chain",a,0,n-1,I64(a.x.back())+1400000000);
}
int main(){
    try {
        const auto start=std::chrono::steady_clock::now();
        examples_and_boundaries();exhaustive();randomized();invalid();maximum();
        rusage usage{};getrusage(RUSAGE_SELF,&usage);
        std::cout<<"{\"checks\":"<<checks<<",\"instances\":"<<instances<<",\"exhaustiveInstances\":"<<exhaustive_instances
          <<",\"exhaustiveTerminalPairs\":"<<exhaustive_terminal_pairs<<",\"randomInstances\":"<<random_instances
          <<",\"literalGraphNodes\":"<<literal_nodes<<",\"literalGraphDirectedEdges\":"<<literal_arcs
          <<",\"metamorphicChecks\":"<<metamorphic_checks<<",\"invalidCalls\":"<<invalid_calls
          <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
          <<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
        bool comma=false;for(const auto&[name,v,e,d,seconds]:maximum_results){if(comma)std::cout<<',';comma=true;
            std::cout<<"{\"name\":\""<<name<<"\",\"vertices\":"<<v<<",\"undirectedEdges\":"<<e<<",\"distance\":"<<d<<",\"seconds\":"<<seconds<<'}';}
        std::cout<<"]}\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/skywalk-endpoint-sparse-shortest-path.mdx'))
    args=parser.parse_args()
    article=Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1,'one complete visible C++ fence required'
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0]
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-skywalk-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
        source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        environment=os.environ.copy()
        if args.sanitize:environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
        completed=subprocess.run([str(binary)],text=True,capture_output=True,env=environment,check=True)
        result=json.loads(completed.stdout)
        result.update({'sanitized':args.sanitize,'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'article':args.article})
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
